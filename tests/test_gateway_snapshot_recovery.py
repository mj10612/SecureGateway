"""Issue #338: recover corrupt snapshot/provenance state without availability loss."""

import http.client
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from secure_gateway.encrypted_session import save_session
from threading import Thread

import pytest

from secure_gateway.gateway import PrivacyGateway


def _conversation_key(gateway: PrivacyGateway, agent: str, conversation: str) -> str:
    session = gateway.get_session(agent, conversation)
    key = session.storage_key
    assert key
    return key


def test_corrupt_encrypted_snapshot_recovers_on_reload(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        session = gateway.get_session("codex", "conv1")
        session.mask("secret-value", code=True)
        gateway.save("codex", session)
        key = session.storage_key
        gateway.sessions.clear()
        (tmp_path / f"{key}-symbols-v2.enc").write_bytes(b"not-an-authenticated-snapshot")

        recovered = gateway.get_session("codex", "conv1")

        assert recovered is not session
        assert recovered.session.forward_store == {}
        assert not (tmp_path / f"{key}-symbols-v2.enc").exists()
        assert (tmp_path / f"{key}-symbols-v2.enc.quarantined").exists()
        assert b"secret-value" not in (tmp_path / f"{key}-symbols-v2.enc.quarantined").read_bytes()


def test_invalid_opaque_json_recovers_safely_and_blocks_old_opaque_replay(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        session = gateway.get_session("codex", "conv1")
        alias = session.mask("secret-value", code=True)
        provider = {
            "type": "reasoning",
            "summary": [{"type": "summary_text", "text": alias}],
            "encrypted_content": "ciphertext",
        }
        restored = session.walk(provider, restore=True)
        gateway.save("codex", session)
        key = session.storage_key
        gateway.sessions.clear()
        (tmp_path / f"{key}-symbols-v2.opaque.json").write_text("{not json", encoding="utf-8")

        recovered = gateway.get_session("codex", "conv1")

        assert recovered.restore(alias) == "secret-value"
        assert recovered.opaque == set()
        assert (tmp_path / f"{key}-symbols-v2.enc").exists()
        assert (tmp_path / f"{key}-symbols-v2.opaque.json.quarantined").exists()
        with pytest.raises(ValueError, match="Unrecognized"):
            recovered.walk(restored)


@pytest.mark.parametrize("contents", [
    "[]bad",
    '{"digest":"a"}',
    json.dumps(["not-a-hex-digest"]),
    json.dumps([123]),
    "null",
])
def test_invalid_opaque_shapes_are_quarantined(tmp_path, contents):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        session = gateway.get_session("codex", "conv1")
        alias = session.mask("secret-value", code=True)
        session.opaque.add("a" * 64)
        gateway.save("codex", session)
        key = session.storage_key
        gateway.sessions.clear()
        (tmp_path / f"{key}-symbols-v2.opaque.json").write_text(contents, encoding="utf-8")

        recovered = gateway.get_session("codex", "conv1")

        assert recovered.restore(alias) == "secret-value"
        assert recovered.opaque == set()
        assert (tmp_path / f"{key}-symbols-v2.opaque.json.quarantined").exists()


@pytest.mark.parametrize("damaged", ["enc", "opaque.json"])
def test_corrupt_snapshot_http_path_recovers_without_400(tmp_path, damaged):
    received = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            received.append(self.rfile.read(int(self.headers["Content-Length"])))
            body = b'{"output": []}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    gateway = PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path,
                             upstreams={"codex": f"http://127.0.0.1:{provider.server_port}"})
    threads = [Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
               for server in (provider, gateway)]
    for thread in threads:
        thread.start()
    try:
        session = gateway.get_session("codex", "\0conv1")
        session.mask("old-secret@example.com", code=True)
        gateway.save("codex", session)
        key = session.storage_key
        gateway.sessions.clear()
        (tmp_path / f"{key}-symbols-v2.{damaged}").write_bytes(b"corrupt")
        client = http.client.HTTPConnection("127.0.0.1", gateway.server_port, timeout=5)
        client.request("POST", "/codex/responses",
                       json.dumps({"model": "fixture", "input": [{"role": "user", "content": "alice@example.com"}]}),
                       {"X-SecureGateway-Token": "local-token", "Authorization": "Bearer eyJfixture",
                        "Content-Type": "application/json", "X-SecureGateway-Session": "conv1"})
        response = client.getresponse()
        body = response.read()
        client.close()
        assert response.status == 200
        assert len(received) == 1 and b"alice@example.com" not in received[0]
        assert b"local-token" not in body and b"old-secret@example.com" not in body
        assert (tmp_path / f"{key}-symbols-v2.{damaged}.quarantined").exists()
        assert (tmp_path / f"{key}-symbols-v2.enc").exists()
        gateway.sessions.clear()
        assert gateway.get_session("codex", "\0conv1").session.forward_store
    finally:
        for server in (gateway, provider):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(3)


def test_other_conversations_keep_mappings_after_corrupt_recovery(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        good = gateway.get_session("codex", "good")
        good_alias = good.mask("good-secret", code=True)
        bad = gateway.get_session("codex", "bad")
        bad.mask("bad-secret", code=True)
        gateway.save("codex", good)
        gateway.save("codex", bad)
        bad_key = bad.storage_key
        gateway.sessions.clear()
        (tmp_path / f"{bad_key}-symbols-v2.enc").write_bytes(b"corrupt")

        recovered_bad = gateway.get_session("codex", "bad")
        recovered_good = gateway.get_session("codex", "good")

        assert recovered_bad.session.forward_store == {}
        assert recovered_good.restore(good_alias) == "good-secret"


def test_transient_snapshot_read_oserror_is_not_quarantined(tmp_path, monkeypatch):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        session = gateway.get_session("codex", "conv1")
        alias = session.mask("secret-value", code=True)
        gateway.save("codex", session)
        key = session.storage_key
        enc = tmp_path / f"{key}-symbols-v2.enc"
        gateway.sessions.clear()

        def fail(*args, **kwargs):
            raise OSError("transient")

        monkeypatch.setattr("secure_gateway.gateway.load_session", fail)

        with pytest.raises(OSError):
            gateway.get_session("codex", "conv1")

        assert enc.exists()
        assert not enc.with_name(enc.name + ".quarantined").exists()
        monkeypatch.undo()
        recovered = gateway.get_session("codex", "conv1")
        assert recovered.restore(alias) == "secret-value"


def test_quarantine_replaces_symlink_without_following_target(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        session = gateway.get_session("codex", "conv1")
        session.mask("secret-value", code=True)
        gateway.save("codex", session)
        key = session.storage_key
        gateway.sessions.clear()
        enc = tmp_path / f"{key}-symbols-v2.enc"
        outside = tmp_path.parent / f"outside-{key}.enc"
        outside.write_bytes(b"outside-target")
        enc.unlink()
        try:
            enc.symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not supported")
        with pytest.raises(OSError, match="Snapshot"):
            gateway.get_session("codex", "conv1")
        assert outside.read_bytes() == b"outside-target"


def test_quarantine_failure_fails_safely_without_leaking_details(tmp_path, monkeypatch):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        session = gateway.get_session("codex", "conv1")
        session.mask("secret-value", code=True)
        gateway.save("codex", session)
        key = session.storage_key
        gateway.sessions.clear()
        (tmp_path / f"{key}-symbols-v2.enc").write_bytes(b"corrupt")

        original_replace = Path.replace

        def fail_replace(self, target):
            if str(self).endswith("-symbols-v2.enc"):
                raise OSError("private-path-detail")
            return original_replace(self, target)

        monkeypatch.setattr(Path, "replace", fail_replace)

        with pytest.raises(OSError) as exc:
            gateway.get_session("codex", "conv1")
        assert "private-path-detail" not in str(exc.value)
        assert "secret-value" not in str(exc.value)
        assert "local-token" not in str(exc.value)


def test_wrong_password_snapshot_is_quarantined_before_fresh_session(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        session = gateway.get_session("codex", "conv1")
        session.mask("secret-value", code=True)
        path = tmp_path / f"{session.storage_key}-symbols-v2.enc"
        save_session(path, session.session, "different-password")
        original = path.read_bytes()
        gateway.sessions.clear()
        recovered = gateway.get_session("codex", "conv1")
        assert not path.exists()
        quarantined = path.with_name(path.name + ".quarantined")
        assert quarantined.read_bytes() == original
        gateway.save("codex", recovered)
        assert path.exists()
        assert quarantined.read_bytes() == original


def test_existing_quarantine_is_not_overwritten(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        session = gateway.get_session("codex", "conv1")
        path = tmp_path / f"{session.storage_key}-symbols-v2.enc"
        path.write_bytes(b"corrupt-current")
        quarantined = path.with_name(path.name + ".quarantined")
        quarantined.write_bytes(b"older-recovery")
        gateway.sessions.clear()
        with pytest.raises(OSError, match="Snapshot recovery failed"):
            gateway.get_session("codex", "conv1")
        assert path.read_bytes() == b"corrupt-current"
        assert quarantined.read_bytes() == b"older-recovery"


def test_quarantine_chmod_failure_fails_safely(tmp_path, monkeypatch):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        session = gateway.get_session("codex", "conv1")
        path = tmp_path / f"{session.storage_key}-symbols-v2.enc"
        path.write_bytes(b"corrupt")
        gateway.sessions.clear()
        def fail(self, *args, **kwargs):
            raise OSError("private-detail")
        monkeypatch.setattr(Path, "chmod", fail)
        with pytest.raises(OSError, match="Snapshot recovery failed") as exc:
            gateway.get_session("codex", "conv1")
        assert "private-detail" not in str(exc.value)


@pytest.mark.parametrize("extension", ["enc", "opaque.json"])
def test_snapshot_symlink_is_rejected_before_read(tmp_path, monkeypatch, extension):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        session = gateway.get_session("codex", "conv1")
        gateway.save("codex", session)
        key = session.storage_key
        gateway.sessions.clear()
        original = Path.is_symlink
        def is_symlink(path):
            return path.name == f"{key}-symbols-v2.{extension}" or original(path)
        monkeypatch.setattr(Path, "is_symlink", is_symlink)
        with pytest.raises(OSError, match="Snapshot path is unsafe"):
            gateway.get_session("codex", "conv1")
