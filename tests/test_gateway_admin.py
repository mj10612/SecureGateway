"""Durable metadata, route attribution and authenticated dashboard contracts."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sqlite3
from threading import Thread
import time
import urllib.error
import urllib.request

from click.testing import CliRunner
import pytest

from secure_gateway.cli import main
from secure_gateway.gateway import PrivacyGateway
from secure_gateway.gateway_audit import AuditStore


@pytest.fixture
def admin_gateway(tmp_path):
    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            self.server.received.append(self.rfile.read(int(self.headers["Content-Length"])))
            body = b'{"content":[]}' if self.server.status == 200 else b'{"error":{"message":"private-provider-error"}}'
            self.send_response(self.server.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    upstream.received, upstream.status = [], 200
    worker = Thread(target=upstream.serve_forever, daemon=True)
    worker.start()
    origin = f"http://127.0.0.1:{upstream.server_port}"
    gateway = PrivacyGateway(
        ("127.0.0.1", 0), "local-private-token", upstreams={"claude": origin, "codex": origin},
        api_upstreams={"xai": origin}, audit_path=tmp_path / "logs.sqlite3",
    )
    thread = Thread(target=gateway.serve_forever, daemon=True)
    thread.start()
    try:
        yield gateway, upstream
    finally:
        gateway.shutdown()
        thread.join(2)
        gateway.server_close()
        upstream.shutdown()
        worker.join(2)
        upstream.server_close()


def call(gateway, path, data=None, headers=None):
    request = urllib.request.Request(
        f"http://127.0.0.1:{gateway.server_port}" + path, data=data,
        headers=headers if headers is not None else {"X-SecureGateway-Token": gateway.token},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, exc.read(), exc.headers


def ledger(gateway, count):
    deadline = time.monotonic() + 3
    while True:
        result = gateway.audit.query({})
        if len(result["rows"]) == count and all(row["status"] is not None for row in result["rows"]):
            return result
        if time.monotonic() > deadline:
            raise AssertionError(result)
        time.sleep(.01)


def test_durable_routing_metadata_without_payloads_or_credentials(admin_gateway):
    gateway, upstream = admin_gateway
    payload = json.dumps({"model": "fixture-model", "input": [{"role": "user", "content": "Review alice@example.com privateCompany."}]}).encode()
    headers = {"X-SecureGateway-Token": gateway.token, "Authorization": "Bearer eyJ-private-oauth",
               "chatgpt-account-id": "private-account-id"}
    assert call(gateway, "/codex/responses?beta=true", payload, headers)[0] == 200
    row = ledger(gateway, 1)["rows"][0]
    assert (row["agent"], row["provider"], row["subscription"]) == ("Codex", "codex", "chatgpt_subscription")
    assert row["status"] == 200 and row["outcome"] == "completed"
    assert row["upstream_attempted"] == 1 and row["duration_ms"] >= 0
    assert row["input_bytes"] == len(payload) and row["masked_bytes"] > 0
    assert row["new_aliases"] > 0 and row["account_ref"] and row["credential_ref"]
    assert row["endpoint"] == "/codex/responses" and row["model"] == "fixture-model"
    assert b"alice@example.com" not in upstream.received[0]
    reopened = AuditStore(gateway.audit.path)
    assert reopened.query({})["rows"][0] == row
    serialized = json.dumps(row) + repr(gateway.audit.path.read_bytes())
    for secret in ("alice@example.com", "privateCompany", "private-oauth", "private-account-id", gateway.token):
        assert secret not in serialized


def test_failures_identify_before_and_after_upstream(admin_gateway):
    gateway, upstream = admin_gateway
    payload = b'{"messages":[]}'
    assert call(gateway, "/claude/v1/messages", payload, {})[0] == 401
    first = ledger(gateway, 1)["rows"][0]
    assert not first["upstream_attempted"] and first["outcome"] == "blocked"
    assert first["credential_ref"] is None and upstream.received == []
    upstream.status = 429
    headers = {"X-SecureGateway-Token": gateway.token, "Authorization": "Bearer sk-ant-oat-private"}
    assert call(gateway, "/claude/v1/messages", payload, headers)[0] == 429
    row = ledger(gateway, 2)["rows"][0]
    assert row["subscription"] == "claude_subscription" and row["account_ref"] is None
    assert row["outcome"] == "upstream_rejected" and row["upstream_attempted"] == 1
    assert "private-provider-error" not in json.dumps(row)
    assert call(gateway, "/claude/v1/messages", b'not JSON', headers)[0] == 400
    assert not ledger(gateway, 3)["rows"][0]["upstream_attempted"]


def test_dashboard_auth_origin_assets_and_filters(admin_gateway):
    gateway, _ = admin_gateway
    for path in ("/admin", "/admin/", "/admin/app.js", "/admin/style.css", "/admin/favicon.svg"):
        status, body, headers = call(gateway, path, headers={})
        assert status == 200 and body
        assert headers["Cache-Control"] == "no-store"
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
        assert gateway.token.encode() not in body
    assert call(gateway, "/admin/api/logs", headers={})[0] == 401
    for path in ("/admin/api/logs", "/admin/api/logs?"):
        status, body, _ = call(gateway, path)
        assert status == 200 and json.loads(body)["rows"] == []
    assert call(gateway, "/admin/api/logs", headers={"X-SecureGateway-Token": "한글".encode().decode("latin1")})[0] == 401
    assert call(gateway, "/admin/api/logs", headers={"Host": "attacker.example", "X-SecureGateway-Token": gateway.token})[0] == 403
    assert call(gateway, "/admin/api/logs", headers={"Origin": "https://attacker.example", "X-SecureGateway-Token": gateway.token})[0] == 403
    assert call(gateway, "/admin/api/logs?limit=0")[0] == 400
    assert call(gateway, "/admin/api/logs?limit=5&limit=10")[0] == 400
    assert call(gateway, "/admin/api/logs?unknown=secret")[0] == 400
    assert call(gateway, "/admin/api/logs?since=2026-01-01")[0] == 400
    assert call(gateway, "/admin/api/logs?result=other")[0] == 400
    payload = b'{"input":[]}'
    headers = {"X-SecureGateway-Token": gateway.token, "Authorization": "Bearer eyJ-private"}
    assert call(gateway, "/codex/responses", payload, headers)[0] == 200
    ledger(gateway, 1)
    status, body, _ = call(gateway, "/admin/api/logs?provider=codex&result=success&limit=1")
    data = json.loads(body)
    assert status == 200 and data["summary"]["total"] == 1 and len(data["rows"]) == 1
    assert json.loads(call(gateway, "/admin/api/logs?provider=claude")[1])["rows"] == []
    assert json.loads(call(gateway, "/admin/api/logs?account_ref=%27%20OR%201%3D1--")[1])["rows"] == []
    assert json.loads(call(gateway, "/admin/api/logs?offset=1")[1])["rows"] == []


def test_bounded_admin_export_excludes_sensitive_metadata(admin_gateway):
    gateway, _ = admin_gateway
    base = "/admin/api/logs/export?since=2026-01-01T00%3A00%3A00Z&until=2026-01-02T00%3A00%3A00Z"
    assert call(gateway, base, headers={})[0] == 401
    assert call(gateway, "/admin/api/logs/export")[0] == 400
    assert call(gateway, base.replace("2026-01-02", "2026-02-02"))[0] == 400
    assert call(gateway, base + "&limit=2000")[0] == 400
    with gateway.audit.connect() as db:
        db.executemany(
            "INSERT INTO requests(request_id,started_at,agent,provider,subscription,endpoint,"
            "destination,account_ref,credential_ref,status) VALUES (?, ?, 'Codex', 'codex',"
            "'chatgpt_subscription', '/codex/responses', 'private-destination',"
            "'private-account', 'private-credential', 200)",
            ((str(index), "2026-01-01T12:00:00+00:00") for index in range(1001)),
        )
    status, body, headers = call(gateway, base + "&provider=codex")
    data = json.loads(body)
    assert status == 200 and headers["Content-Disposition"].startswith("attachment;")
    assert data["count"] == data["limit"] == 1000 and data["truncated"] is True
    assert len(data["rows"]) == 1000
    for value in (b"private-destination", b"private-account", b"private-credential"):
        assert value not in body
    assert json.loads(call(gateway, base + "&provider=claude")[1])["rows"] == []


def test_logging_failure_refuses_forwarding(admin_gateway, monkeypatch):
    gateway, upstream = admin_gateway
    def fail(*args):
        raise sqlite3.OperationalError("private-database-path")
    monkeypatch.setattr(gateway.audit, "begin", fail)
    headers = {"X-SecureGateway-Token": gateway.token, "Authorization": "Bearer eyJ-test"}
    status, body, _ = call(gateway, "/codex/responses", b'{"input":[]}', headers)
    assert status == 503 and b"private-database-path" not in body
    assert upstream.received == [] and gateway.audit_write_errors == 1


def test_completion_write_failure_stays_visible(admin_gateway, monkeypatch):
    gateway, _ = admin_gateway
    def fail(*args):
        raise sqlite3.OperationalError("private-database-path")
    monkeypatch.setattr(gateway.audit, "finish", fail)
    headers = {"X-SecureGateway-Token": gateway.token, "Authorization": "Bearer eyJ-test"}
    assert call(gateway, "/codex/responses", b'{"input":[]}', headers)[0] == 200
    deadline = time.monotonic() + 3
    while not gateway.audit_write_errors and time.monotonic() < deadline:
        time.sleep(.01)
    assert gateway.audit_write_errors == 1
    data = json.loads(call(gateway, "/admin/api/logs")[1])
    assert data["audit_write_errors"] == 1 and data["rows"][0]["status"] is None


def test_concurrent_requests_are_durable_and_separately_attributed(admin_gateway):
    gateway, _ = admin_gateway
    def request(index):
        headers = {"X-SecureGateway-Token": gateway.token, "Authorization": "Bearer eyJ-shared",
                   "chatgpt-account-id": "account-" + str(index % 2)}
        return call(gateway, "/codex/responses", b'{"input":[]}', headers)[0]
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(request, range(12))) == [200] * 12
    result = ledger(gateway, 12)
    assert len({row["request_id"] for row in result["rows"]}) == 12
    accounts = {row["account_ref"] for row in result["rows"]}
    assert len(accounts) == 2
    assert all(gateway.audit.query({"account_ref": account})["summary"]["total"] == 6 for account in accounts)


def test_api_mode_is_distinct_from_subscription_and_records_sdk_source(admin_gateway):
    gateway, _ = admin_gateway
    headers = {"X-SecureGateway-Token": gateway.token, "Authorization": "Bearer xai-private",
               "X-SecureGateway-Agent": "Antigravity SDK"}
    assert call(gateway, "/xai/v1/responses", b'{"input":[]}', headers)[0] == 200
    row = ledger(gateway, 1)["rows"][0]
    assert (row["agent"], row["provider"], row["subscription"]) == ("Antigravity SDK", "xai", "api_key")
    assert row["account_ref"] is None


def test_admin_command_never_prints_token(tmp_path, monkeypatch):
    from secure_gateway import gateway_install
    config = tmp_path / "config.json"
    token = "sensitive-config-token" * 2
    config.write_text(json.dumps({"port": 38117, "token": token}))
    monkeypatch.setattr(gateway_install, "healthy", lambda _: True)
    result = CliRunner().invoke(main, ["gateway", "admin", "--config", str(config), "--no-open"])
    assert result.exit_code == 0 and "http://127.0.0.1:38117/admin" in result.output
    assert token not in result.output


def test_unknown_database_version_is_not_modified(tmp_path):
    path = tmp_path / "logs.sqlite3"
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("PRAGMA user_version=99")
    with pytest.raises(ValueError, match="version"):
        AuditStore(path)
    with closing(sqlite3.connect(path)) as db, db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 99


def test_time_filters_normalize_timezones_and_preserve_incomplete_records(tmp_path):
    store = AuditStore(tmp_path / "logs.sqlite3")
    store.begin("Codex", "codex", "chatgpt_subscription", "/codex/responses", "https://chatgpt.com/backend-api/codex")
    result = store.query({"result": "incomplete", "since": "2000-01-01T09:00:00+09:00",
                          "until": "2099-01-01T00:00:00Z"})
    assert result["summary"]["total"] == 1 and result["rows"][0]["outcome"] == "incomplete"
    assert store.query({"until": "2000-01-01T00:00:00Z"})["rows"] == []


@pytest.mark.parametrize("limit,offset", [(-1, 0), (0, 0), (201, 0), (True, 0),
                                           (1, -1), (1, True), (1, 2**63)])
def test_audit_store_query_rejects_invalid_pagination(tmp_path, limit, offset):
    store = AuditStore(tmp_path / "logs.sqlite3")
    with pytest.raises(ValueError, match="Invalid audit pagination"):
        store.query({}, limit=limit, offset=offset)
    store.close()


def test_audit_store_query_accepts_pagination_boundaries(tmp_path):
    store = AuditStore(tmp_path / "logs.sqlite3")
    assert store.query({}, limit=200, offset=2**63 - 1)["rows"] == []
    store.close()


def test_retention_discards_oldest_requests(tmp_path):
    store = AuditStore(tmp_path / "logs.sqlite3")
    with store.connect() as db:
        db.executemany(
            "INSERT INTO requests(request_id,started_at,agent,provider,subscription,endpoint,destination,status) "
            "VALUES (?, '2026-01-01T00:00:00+00:00', 'Codex', 'codex', 'chatgpt_subscription', '/codex/responses', 'fixture',200)",
            ((str(index),) for index in range(100001)),
        )
    store.begin("Codex", "codex", "chatgpt_subscription", "/codex/responses", "fixture")
    assert store.query({})["summary"]["total"] == 100001
    with store.connect() as db:
        assert db.execute("SELECT request_id FROM requests ORDER BY id LIMIT 1").fetchone()[0] == "1"
