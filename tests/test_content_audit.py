from pathlib import Path
import sqlite3
from contextlib import closing

import pytest

from secure_gateway.content_audit import ContentAuditStore, IntegrityError, LockedError


def test_lock_reopen_wrong_passphrase_and_rewrap(tmp_path: Path):
    path = tmp_path / "audit.sqlite3"
    store = ContentAuditStore(path)
    store.initialize("old passphrase")
    store.append("req1", "input", {"text": "synthetic content"})
    store.lock()
    with pytest.raises(LockedError):
        store.read("req1")
    with pytest.raises(ValueError):
        store.unlock("wrong passphrase")
    store.unlock("old passphrase")
    store.change_passphrase("new passphrase")
    store.close()
    store = ContentAuditStore(path)
    with pytest.raises(ValueError):
        store.unlock("old passphrase")
    store.unlock("new passphrase")
    assert store.read("req1") == [("input", {"text": "synthetic content"})]
    assert b"synthetic content" not in path.read_bytes()
    store.close()


def test_rotation_keeps_old_keys_and_chains(tmp_path: Path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3")
    store.initialize("passphrase")
    store.append("req1", "input", {"text": "one"})
    store.rotate_key()
    store.append("req1", "sent", {"text": "two"})
    store.lock()
    store.unlock("passphrase")
    assert store.read("req1") == [("input", {"text": "one"}), ("sent", {"text": "two"})]
    store.close()


@pytest.mark.parametrize("mutation", ["ciphertext", "kind", "gap", "swap"])
def test_tampering_is_detected(tmp_path: Path, mutation: str):
    path = tmp_path / "audit.sqlite3"
    store = ContentAuditStore(path)
    store.initialize("passphrase")
    store.append("req1", "input", {"text": "one"})
    store.append("req1", "sent", {"text": "two"})
    with closing(sqlite3.connect(path)) as db, db:
        if mutation == "ciphertext":
            db.execute("UPDATE events SET ciphertext = zeroblob(length(ciphertext)) WHERE seq=0")
        elif mutation == "kind":
            db.execute("UPDATE events SET kind='response' WHERE seq=0")
        elif mutation == "gap":
            db.execute("DELETE FROM events WHERE seq=0")
        else:
            rows = db.execute("SELECT ciphertext FROM events ORDER BY seq").fetchall()
            db.execute("UPDATE events SET ciphertext=? WHERE seq=0", rows[1])
            db.execute("UPDATE events SET ciphertext=? WHERE seq=1", rows[0])
    with pytest.raises(IntegrityError):
        store.read("req1")
    store.close()


def test_idle_lock(tmp_path: Path, monkeypatch):
    clock = [10.0]
    monkeypatch.setattr("secure_gateway.content_audit.time.monotonic", lambda: clock[0])
    store = ContentAuditStore(tmp_path / "audit.sqlite3")
    store.initialize("passphrase")
    clock[0] += 601
    with pytest.raises(LockedError):
        store.append("req1", "input", {})
    store.close()


def test_background_capture_does_not_extend_admin_idle_timeout(tmp_path: Path, monkeypatch):
    clock = [10.0]
    monkeypatch.setattr("secure_gateway.content_audit.time.monotonic", lambda: clock[0])
    store = ContentAuditStore(tmp_path / "audit.sqlite3")
    store.initialize("passphrase")
    clock[0] += 599
    store.append("req1", "input", {})
    clock[0] += 2
    assert store.locked()
    with pytest.raises(LockedError):
        store.append("req1", "sent", {})
    store.close()


def test_retention_and_delete(tmp_path: Path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3", max_requests=2)
    store.initialize("passphrase")
    store.append("req1", "input", "one")
    store.append("req2", "input", "two")
    store.append("req3", "input", "three")
    assert store.read("req1") == []
    assert store.read("req2") == [("input", "two")]
    assert store.delete(["req2", "absent"]) == 1
    assert store.read("req2") == []
    assert store.delete_all() == 1
    store.close()


def test_byte_limit_refuses_oversize_request(tmp_path: Path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3", max_bytes=256 * 1024)
    store.initialize("passphrase")
    store.append("previous", "input", "preserved")
    with pytest.raises(ValueError):
        store.append("req1", "input", "x" * (300 * 1024))
    assert store.read("req1") == []
    assert store.read("previous") == [("input", "preserved")]
    store.close()


def test_credential_redaction_in_code_and_pem():
    from secure_gateway.content_audit import redact_credentials

    secret = "sk-abcdefghijklMNOP123456789"
    pem = "-----BEGIN PRIVATE KEY-----\nSYNTHETIC_TEST_KEY\n-----END PRIVATE KEY-----"
    text, count = redact_credentials(f"```{secret}```\n{pem}")
    assert secret not in text
    assert pem not in text
    assert count == 2
    assert text.count("[credential removed]") == 2


def test_urls_are_not_kept_in_selected_text():
    from secure_gateway.content_audit import redact_credentials

    text, count = redact_credentials("see https://example.invalid/private?token=synthetic")
    assert "example.invalid" not in text
    assert count == 1


def test_metadata_upgrade_preserves_old_rows_and_export(tmp_path):
    from secure_gateway.gateway_audit import AuditStore

    path = tmp_path / "logs.sqlite3"
    old = AuditStore(path)
    request_id = old.begin("Codex", "codex", "subscription", "/codex/responses", "fixture")
    before = old.export_metadata({})
    old.close()
    with closing(sqlite3.connect(path)) as db, db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(requests)")}
        if "content_audit" in columns:
            db.execute("ALTER TABLE requests DROP COLUMN content_audit")
        db.execute("PRAGMA user_version=2")
    upgraded = AuditStore(path)
    with upgraded.connect() as db:
        assert db.execute("SELECT content_audit FROM requests WHERE request_id=?", (request_id,)).fetchone()[0] is None
    assert upgraded.export_metadata({}) == before
    assert "content_audit" not in upgraded.query({})["rows"][0]
    upgraded.close()


def test_legacy_scrypt_store_unlocks_and_rewraps_with_new_parameters(tmp_path):
    import os
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    path = tmp_path / 'legacy.sqlite3'
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('CREATE TABLE config (key TEXT PRIMARY KEY, value BLOB NOT NULL)')
        db.execute('CREATE TABLE keys (id INTEGER PRIMARY KEY, nonce BLOB NOT NULL, wrapped BLOB NOT NULL)')
    store = ContentAuditStore(path)
    salt, nonce, data_key = os.urandom(16), os.urandom(12), os.urandom(32)
    old_key = Scrypt(salt=salt, length=32, n=16384, r=8, p=1).derive(b'old passphrase')
    wrapped = AESGCM(old_key).encrypt(nonce, data_key, b'content-audit-key:1')
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("INSERT INTO config VALUES ('salt', ?)", (salt,))
        db.execute("INSERT INTO config VALUES ('scrypt', ?)", (b'n=16384,r=8,p=1',))
        db.execute('INSERT INTO keys(id, nonce, wrapped) VALUES (1, ?, ?)', (nonce, wrapped))
    store.unlock('old passphrase')
    store.append('legacy', 'input', {'text': 'synthetic'})
    store.rotate_key()
    store.lock()
    store.unlock('old passphrase')
    store.change_passphrase('new passphrase')
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('SELECT kdf_n, kdf_r, kdf_p FROM keys ORDER BY id').fetchall() == [(131072, 8, 1)] * 2
    store.close()
    store = ContentAuditStore(path)
    with pytest.raises(ValueError):
        store.unlock('old passphrase')
    store.unlock('new passphrase')
    assert store.read('legacy') == [('input', {'text': 'synthetic'})]
    store.close()
