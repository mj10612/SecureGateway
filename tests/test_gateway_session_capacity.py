"""Bounded session memory retains encrypted idle conversations and request pins."""

import http.client
import json
import os
from threading import Thread
import time

import pytest

from secure_gateway.encrypted_session import save_session
from secure_gateway.gateway import GatewaySession, PrivacyGateway
from secure_gateway.gateway_errors import GatewayRequestError, public_request_error


def fill(gateway, start=0, stop=256):
    for index in range(start, stop):
        gateway.get_session("codex", str(index))


def test_257th_conversation_evicts_idle_and_resumes_exact_mapping(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        first = gateway.get_session("codex", "0")
        alias = first.mask("private-old-conversation", code=True)
        first.opaque.add("a" * 64)
        old_access = time.time() - 100
        first.session.last_accessed = old_access
        key = first.storage_key
        fill(gateway, 1)
        newest = gateway.get_session("codex", "256")
        assert len(gateway.sessions) == 256 and newest.storage_key in gateway.sessions
        assert key not in gateway.sessions and first.session.generator.closed
        assert first.session.last_accessed == old_access  # Eviction cannot renew TTL.
        assert b"private-old-conversation" not in (tmp_path / (key + "-symbols-v2.enc")).read_bytes()
        resumed = gateway.get_session("codex", "0")
        assert resumed is not first and resumed.restore(alias) == "private-old-conversation"
        assert "a" * 64 in resumed.opaque
        assert len(gateway.sessions) == 256


def test_active_request_pin_prevents_eviction_before_masking(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        first = gateway.get_session("codex", "0", pin=True)
        first.session.last_accessed = time.time() - 100
        fill(gateway, 1)
        gateway.get_session("codex", "256")
        assert gateway.sessions[first.storage_key] is first
        assert not first.session.generator.closed and first.active_requests == 1
        first.active_requests -= 1


def test_no_persistence_does_not_discard_unexpired_private_state():
    with PrivacyGateway(("127.0.0.1", 0), "secret") as gateway:
        first = gateway.get_session("codex", "0")
        alias = first.mask("private-state", code=True)
        fill(gateway, 1)
        with pytest.raises(GatewayRequestError) as raised:
            gateway.get_session("codex", "256")
        assert public_request_error(raised.value)["code"] == "conversation_capacity"
        assert first.restore(alias) == "private-state"


def test_all_pinned_sessions_produce_capacity_diagnostic(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        for index in range(256):
            gateway.get_session("codex", str(index), pin=True)
        with pytest.raises(GatewayRequestError) as raised:
            gateway.get_session("codex", "256", pin=True)
        assert raised.value.code == "conversation_capacity"
        assert all(session.active_requests == 1 for session in gateway.sessions.values())
        for session in gateway.sessions.values():
            session.active_requests -= 1


def test_snapshot_failure_keeps_live_session(tmp_path, monkeypatch):
    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        fill(gateway)
        first = gateway.get_session("codex", "0")
        first.session.last_accessed = time.time() - 100
        def fail(*args, **kwargs):
            raise OSError("Synthetic storage failure")
        monkeypatch.setattr("secure_gateway.gateway.save_session", fail)
        with pytest.raises(OSError):
            gateway.get_session("codex", "256")
        assert gateway.sessions[first.storage_key] is first
        assert not first.session.generator.closed and len(gateway.sessions) == 256


def make_snapshot(directory, key, password, *, expired):
    session = GatewaySession()
    session.mask("private-fixture", code=True)
    if expired:
        session.session.last_accessed = time.time() - 90000
    path = directory / (key + "-symbols-v2.enc")
    save_session(path, session.session, password)
    path.with_suffix(".opaque.json").write_text('["' + "a" * 64 + '"]', encoding="utf8")
    old = time.time() - 90000
    os.utime(path, (old, old))
    return path


def test_startup_cleanup_authenticates_expiry_and_preserves_foreign_healthy(tmp_path):
    expired = make_snapshot(tmp_path, "codex-" + "a" * 64, "secret", expired=True)
    healthy = make_snapshot(tmp_path, "codex-" + "b" * 64, "secret", expired=False)
    foreign = make_snapshot(tmp_path, "codex-" + "c" * 64, "other-token", expired=True)
    corrupt = tmp_path / ("codex-" + "d" * 64 + "-symbols-v2.enc")
    corrupt.write_bytes(b"not-an-authenticated-snapshot")
    old = time.time() - 90000
    os.utime(corrupt, (old, old))
    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        # Two decryptions per bounded batch; continue the directory cursor.
        for _ in range(3):
            gateway.cleanup_expired_snapshots()
        assert not expired.exists() and not expired.with_suffix(".opaque.json").exists()
        assert healthy.exists() and foreign.exists() and corrupt.exists()


def test_expired_snapshot_is_deleted_when_requested_even_with_recent_mtime(tmp_path):
    path = make_snapshot(tmp_path, "codex", "secret", expired=True)
    path.touch()
    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        assert not gateway.get_session("codex").session.forward_store
        assert not path.exists() and not path.with_suffix(".opaque.json").exists()


def test_http_mask_failure_releases_session_pin(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("Synthetic invalid request")
    monkeypatch.setattr(GatewaySession, "request", fail)
    gateway = PrivacyGateway(("127.0.0.1", 0), "secret")
    thread = Thread(target=gateway.serve_forever, kwargs={"poll_interval": .01})
    thread.start()
    try:
        client = http.client.HTTPConnection("127.0.0.1", gateway.server_port)
        client.request("POST", "/codex/responses", json.dumps({"model": "fixture", "input": []}),
                       {"X-SecureGateway-Token": "secret", "Authorization": "Bearer eyJfixture", "session_id": "new-conversation"})
        response = client.getresponse()
        assert response.status == 400
        response.read()
        client.close()
        assert len(gateway.sessions) == 1
        session = next(iter(gateway.sessions.values()))
        deadline = time.monotonic() + 3
        while session.active_requests and time.monotonic() < deadline:
            time.sleep(.01)
        assert session.active_requests == 0
    finally:
        gateway.shutdown()
        gateway.server_close()
        thread.join(3)
