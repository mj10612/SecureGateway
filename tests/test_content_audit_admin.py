from contextlib import contextmanager
import json
import os
import sqlite3
import subprocess
import sys
from threading import Thread
import urllib.error
import urllib.request

from secure_gateway.gateway import PrivacyGateway


@contextmanager
def gateway_at(root):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=root / "sessions",
                        audit_path=root / "logs.sqlite3") as gateway:
        worker = Thread(target=gateway.serve_forever, daemon=True)
        worker.start()
        try:
            yield gateway
        finally:
            gateway.shutdown()
            worker.join(5)


def api(gateway, endpoint, body=None, *, method=None, token="local-token", origin=None):
    headers = {"X-SecureGateway-Token": token}
    if origin:
        headers["Origin"] = origin
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(f"http://127.0.0.1:{gateway.server_port}/admin/api/content-audit/{endpoint}",
                                     data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read()), response.headers
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read()), exc.headers


def test_admin_initialization_settings_and_restart_lock(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "status", token="wrong")[0] == 401
        assert api(gateway, "status", origin="https://invalid.example")[0] == 403
        code, status, headers = api(gateway, "status")
        assert code == 200 and status["locked"] and not status["initialized"]
        assert headers["Cache-Control"] == "no-store"
        assert not (tmp_path / "content-audit.sqlite3").exists()
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        settings = api(gateway, "settings")[1]
        settings["enabled"] = True
        settings["providers"]["claude"] = True
        settings["kinds"]["input"] = True
        assert api(gateway, "settings", {"settings": settings}, method="PUT")[0] == 400
        assert api(gateway, "settings", {"settings": settings, "confirm_sensitive_content": True}, method="PUT")[0] == 200
        assert gateway.content_audit is not None and gateway.content_audit.enabled
        assert api(gateway, "lock", {})[0] == 200
        assert api(gateway, "status")[1]["locked"]
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase"})[0] == 200
        assert not api(gateway, "status")[1]["locked"]
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "settings")[1]["enabled"] is True
        assert api(gateway, "status")[1]["locked"] is True


def test_admin_unlock_rate_limit_and_no_sensitive_security_events(tmp_path, caplog):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "correct-synthetic", "initialize": True})[0] == 200
        assert api(gateway, "lock", {})[0] == 200
        for _ in range(5):
            assert api(gateway, "unlock", {"passphrase": "wrong-synthetic"})[0] == 401
        assert api(gateway, "unlock", {"passphrase": "correct-synthetic"})[0] == 429
        assert "correct-synthetic" not in caplog.text
        assert "wrong-synthetic" not in caplog.text
        assert "local-token" not in caplog.text
        assert "content_audit_unlock_failure" in caplog.text


def test_admin_list_get_review_require_explicit_unlocked_access(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        store = gateway.content_admin.store
        store.append("request1", "input", {"text": "selected private content"})
        status, result, _ = api(gateway, "list")
        assert status == 200 and result["requests"][0]["request_id"] == "request1"
        assert "selected private content" not in json.dumps(result)
        assert api(gateway, "get", {"request_id": "request1"})[1]["events"][0]["content"]["text"] == "selected private content"
        assert api(gateway, "review", {"request_id": "request1", "status": "정상", "memo": "synthetic memo"})[0] == 200
        assert b"synthetic memo" not in (tmp_path / "content-audit.sqlite3").read_bytes()
        assert api(gateway, "lock", {})[0] == 200
        assert api(gateway, "get", {"request_id": "request1"})[0] == 423


def test_admin_unexpected_failure_has_fixed_response(tmp_path, monkeypatch, capsys):
    with gateway_at(tmp_path) as gateway:
        def fail_status():
            raise RuntimeError("private-diagnostic-canary")

        monkeypatch.setattr(gateway.content_admin, "status", fail_status)
        status, result, _ = api(gateway, "status")
        assert status == 500
        assert "private-diagnostic-canary" not in json.dumps(result)
        assert "private-diagnostic-canary" not in capsys.readouterr().err


def test_admin_export_and_delete_explicit_selection(tmp_path):
    from secure_gateway.content_audit_export import decrypt_export

    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        store = gateway.content_admin.store
        store.append("one", "input", {"text": "synthetic content"})
        store.append("two", "input", {"text": "other content"})
        selection = {"request_ids": ["one"], "kinds": ["input"], "passphrase": "export-passphrase"}
        status, encrypted, _ = api(gateway, "export", selection)
        assert status == 200 and "synthetic content" not in json.dumps(encrypted)
        assert decrypt_export(encrypted, "export-passphrase")["requests"][0]["request_id"] == "one"
        assert api(gateway, "export", {"request_ids": ["one"], "kinds": ["input"], "plaintext": True})[0] == 400
        status, result, _ = api(gateway, "delete", {"request_ids": ["one"]})
        assert status == 200 and result == {"deleted": 1, "request_ids": ["one"]}
        deleted_row = next(row for row in api(gateway, "list")[1]["requests"] if row["request_id"] == "one")
        assert deleted_row["state"] == "삭제됨"
        assert api(gateway, "delete", {"all": True})[0] == 400
        assert api(gateway, "delete", {"all": True, "confirm": True})[1]["deleted"] == 1


def test_range_deletion_and_maintenance_failure_report_actual_scope(tmp_path, monkeypatch, capsys):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        store = gateway.content_admin.store
        store.append("old", "input", {"text": "old"})
        store.append("new", "input", {"text": "new"})
        with store._connect() as db:
            db.execute("UPDATE requests SET created=1000000000 WHERE request_id='old'")
            db.execute("UPDATE requests SET created=1500000000 WHERE request_id='new'")
        selection = {"since": "2001-09-01T00:00:00Z", "until": "2002-01-01T00:00:00Z", "confirm": True}
        assert api(gateway, "delete", selection)[1] == {"deleted": 1, "request_ids": ["old"]}

        def fail_compaction():
            raise sqlite3.OperationalError("sensitive-diagnostic-canary")

        monkeypatch.setattr(store, "_compact", fail_compaction)
        status, result, _ = api(gateway, "delete", {"all": True, "confirm": True})
        assert status == 503
        assert result == {"deleted": 1, "request_ids": ["new"], "maintenance": "failed"}
        assert "sensitive-diagnostic-canary" not in capsys.readouterr().err


def test_get_marks_missing_completion_marker_incomplete(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        store = gateway.content_admin.store
        store.append("one", "opened", {"input": "synthetic"})
        store.append("one", "finished", {"partial": False, "failed": False, "uncertain": False,
                                         "omitted_bytes": 0, "omitted_events": 0})
        assert api(gateway, "get", {"request_id": "one"})[1]["verified_state"] == "완료"
        with store._connect() as db:
            db.execute("DELETE FROM events WHERE request_id='one' AND seq=1")
        assert api(gateway, "get", {"request_id": "one"})[1]["verified_state"] == "부분"


def test_content_audit_requires_metadata_store(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path / "sessions") as gateway:
        worker = Thread(target=gateway.serve_forever, daemon=True)
        worker.start()
        try:
            settings = api(gateway, "settings")[1]
            settings["enabled"] = True
            status, result, _ = api(gateway, "settings", {"settings": settings, "confirm_sensitive_content": True},
                                    method="PUT")
            assert status == 409 and result == {"error": "Content audit requires metadata audit"}
        finally:
            gateway.shutdown()
            worker.join(5)


def test_missing_capture_is_visible_after_restart(tmp_path):
    with gateway_at(tmp_path) as gateway:
        request_id = gateway.audit.begin("Claude Code", "claude", "subscription", "/claude/v1/messages",
                                         "fixture", "capture")
    with gateway_at(tmp_path) as gateway:
        rows = api(gateway, "list")[1]["requests"]
        row = next(item for item in rows if item["request_id"] == request_id)
        assert row["intent"] == "capture"
        assert row["state"] == "기록 실패"
        assert "content_audit" not in gateway.audit.query({})["rows"][0]
        assert "content_audit" not in gateway.audit.export_metadata({})["rows"][0]


def test_kill_before_content_queue_write_recovers_metadata_intent(tmp_path):
    script = """
import os
from pathlib import Path
from secure_gateway.gateway_audit import AuditStore
store = AuditStore(Path(os.environ['SYNTHETIC_METADATA_PATH']))
store.begin('Claude Code', 'claude', 'subscription', '/claude/v1/messages', 'fixture', 'capture')
os._exit(19)
"""
    env = dict(os.environ, SYNTHETIC_METADATA_PATH=str(tmp_path / "logs.sqlite3"))
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, check=False, timeout=30)
    assert result.returncode == 19
    assert not (tmp_path / "content-audit.sqlite3").exists()
    with gateway_at(tmp_path) as gateway:
        rows = api(gateway, "list")[1]["requests"]
        assert len(rows) == 1
        assert rows[0]["intent"] == "capture" and rows[0]["state"] == "기록 실패"


def test_admin_can_rewrap_and_rotate_keys_without_losing_old_records(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "old-passphrase", "initialize": True})[0] == 200
        store = gateway.content_admin.store
        store.append("one", "input", {"text": "old content"})
        assert api(gateway, "rotate-key", {})[0] == 200
        store.append("one", "response", {"text": "new content"})
        assert api(gateway, "change-passphrase", {"passphrase": "old-passphrase",
                                                   "new_passphrase": "new-passphrase"})[0] == 200
        assert api(gateway, "lock", {})[0] == 200
        assert api(gateway, "unlock", {"passphrase": "old-passphrase"})[0] == 401
        assert api(gateway, "unlock", {"passphrase": "new-passphrase"})[0] == 200
        events = api(gateway, "get", {"request_id": "one"})[1]["events"]
        assert [event["content"]["text"] for event in events] == ["old content", "new content"]
