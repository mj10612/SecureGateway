import json
import os
import subprocess
import sys
from contextlib import closing
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from secure_gateway.content_audit import ContentAuditStore
from secure_gateway.content_audit_export import decrypt_export, export_requests, restore_export
from secure_gateway.content_audit_capture import ContentAuditCapture
from secure_gateway.content_audit_writer import ContentAuditWriter


def test_encrypted_export_restore_selection_and_tamper(tmp_path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3")
    store.initialize("store-passphrase")
    store.append("one", "input", {"text": "synthetic selected"})
    store.append("one", "response", {"text": "excluded content"})
    store.append("two", "input", {"text": "excluded request"})
    exported = export_requests(store, ["one"], {"input"}, passphrase="export-passphrase")
    assert exported["kdf"]["n"] == 131072
    assert "synthetic selected" not in json.dumps(exported)
    restored = decrypt_export(exported, "export-passphrase")
    assert restored == {"version": 1, "requests": [{"request_id": "one", "state": "부분", "events": [
        {"kind": "input", "content": {"text": "synthetic selected"}}]}]}
    with pytest.raises(ValueError):
        decrypt_export(exported, "wrong-passphrase")
    exported["ciphertext"] = exported["ciphertext"][:-4] + "AAAA"
    with pytest.raises(ValueError):
        decrypt_export(exported, "export-passphrase")
    store.close()


def test_plaintext_export_requires_separate_confirmation(tmp_path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3")
    store.initialize("store-passphrase")
    store.append("one", "input", {"text": "selected", "password": "synthetic-credential"})
    with pytest.raises(ValueError):
        export_requests(store, ["one"], {"input"}, plaintext=True)
    result = export_requests(store, ["one"], {"input"}, plaintext=True, confirm_plaintext=True)
    assert "selected" in json.dumps(result)
    assert "synthetic-credential" not in json.dumps(result)
    store.close()


def test_encrypted_restore_imports_atomically_into_empty_store(tmp_path):
    source = ContentAuditStore(tmp_path / "source.sqlite3")
    source.initialize("source-passphrase")
    source.append("one", "input", {"text": "synthetic restored"})
    exported = export_requests(source, ["one"], {"input"}, passphrase="export-passphrase")
    target = ContentAuditStore(tmp_path / "target.sqlite3")
    target.initialize("target-passphrase")
    with pytest.raises(ValueError):
        restore_export(target, exported, "wrong-passphrase")
    assert target.read("one") == []
    assert restore_export(target, exported, "export-passphrase") == 1
    assert target.read("one")[1] == ("input", {"text": "synthetic restored"})
    assert target.request_status("one")["state"] == "부분"
    with pytest.raises(ValueError):
        restore_export(target, exported, "export-passphrase")
    source.close()
    target.close()


def test_concurrent_retention_keeps_newest_bounded(tmp_path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3", max_requests=10)
    store.initialize("store-passphrase")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda number: store.append(f"r{number}", "input", {"n": number}), range(80)))
    with store._connect() as db:
        assert db.execute("SELECT count(*) FROM requests").fetchone()[0] == 10
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 10
    store.close()


def test_disk_limit_includes_database_and_sidecars(tmp_path):
    path = tmp_path / "audit.sqlite3"
    maximum = 256 * 1024
    store = ContentAuditStore(path, max_requests=1000, max_bytes=maximum)
    store.initialize("store-passphrase")
    for number in range(24):
        store.append(f"r{number}", "input", {"text": "x" * 16384})
        size = sum(item.stat().st_size for item in tmp_path.iterdir() if item.is_file())
        assert size <= maximum
    store.close()


def test_disk_limit_with_reader_holding_wal(tmp_path):
    path = tmp_path / "audit.sqlite3"
    maximum = 256 * 1024
    store = ContentAuditStore(path, max_requests=1000, max_bytes=maximum)
    store.initialize("store-passphrase")
    store.append("first", "input", {"text": "synthetic"})
    with closing(sqlite3.connect(path)) as reader:
        reader.execute("BEGIN")
        reader.execute("SELECT count(*) FROM requests").fetchone()
        refused = False
        for number in range(40):
            try:
                store.append(f"r{number}", "input", {"text": "x" * 16384})
            except ValueError:
                refused = True
            size = sum(item.stat().st_size for item in tmp_path.iterdir() if item.is_file())
            assert size <= maximum
            if refused:
                break
        assert refused
    store.close()


def test_killed_process_leaves_an_incomplete_request(tmp_path):
    path = tmp_path / "audit.sqlite3"
    script = """
import os
from pathlib import Path
from secure_gateway.content_audit import ContentAuditStore
store = ContentAuditStore(Path(os.environ['SYNTHETIC_AUDIT_PATH']))
store.initialize('synthetic-passphrase')
store.append('request1', 'opened', {'input': 'synthetic'})
os._exit(17)
"""
    env = dict(os.environ, SYNTHETIC_AUDIT_PATH=str(path))
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, check=False, timeout=30)
    assert result.returncode == 17
    store = ContentAuditStore(path)
    assert store.request_status("request1")["state"] == "부분"
    store.unlock("synthetic-passphrase")
    assert store.read("request1") == [("opened", {"input": "synthetic"})]
    store.close()


def test_canary_sweep_selected_and_unselected_content(tmp_path, caplog, capsys):
    path = tmp_path / "audit.sqlite3"
    store = ContentAuditStore(path)
    store.initialize("synthetic-passphrase")
    writer = ContentAuditWriter(store)
    capture = ContentAuditCapture(writer, enabled=True, kinds={"input"})
    selected = "SELECTED_CONTENT_CANARY_329"
    credential = "CREDENTIAL_CANARY_852"
    unselected = "UNSELECTED_CONTENT_CANARY_741"
    with closing(sqlite3.connect(path)) as held_reader:
        held_reader.execute("BEGIN")
        held_reader.execute("SELECT count(*) FROM requests").fetchone()
        assert capture.begin("one", {"messages": [{"content": selected}], "authorization": credential})
        capture.observe("one", "response", {"content": unselected}, "received")
        capture.finish("one", uncertain=False, interrupted=False)
        writer.drain()
        encrypted = export_requests(store, ["one"], {"input"}, passphrase="export-passphrase")
        plain = export_requests(store, ["one"], {"input"}, plaintext=True, confirm_plaintext=True)
        assert selected in json.dumps(plain)
        for item in (credential, unselected):
            assert item not in json.dumps(plain)
        for item in (selected, credential, unselected):
            assert item not in json.dumps(encrypted)
            assert item not in caplog.text
            assert item not in capsys.readouterr().err
            for file in tmp_path.iterdir():
                if file.is_file():
                    assert item.encode() not in file.read_bytes()
    writer.close()
    store.close()


def test_legacy_encrypted_export_remains_readable(tmp_path):
    import base64
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    salt, wrapping_nonce, nonce, key = os.urandom(16), os.urandom(12), os.urandom(12), os.urandom(32)
    derived = Scrypt(salt=salt, length=32, n=16384, r=8, p=1).derive(b'legacy passphrase')
    def encode(value):
        return base64.b64encode(value).decode('ascii')
    document = {'version': 1, 'requests': []}
    export = {'format': 'secure-gateway-content-audit-v1',
              'kdf': {'name': 'scrypt', 'n': 16384, 'r': 8, 'p': 1, 'salt': encode(salt)},
              'wrapping_nonce': encode(wrapping_nonce),
              'wrapped_key': encode(AESGCM(derived).encrypt(wrapping_nonce, key, b'content-audit-export-key-v1')),
              'nonce': encode(nonce),
              'ciphertext': encode(AESGCM(key).encrypt(nonce, json.dumps(document).encode(),
                                                       b'content-audit-export-data-v1'))}
    assert decrypt_export(export, 'legacy passphrase') == document
