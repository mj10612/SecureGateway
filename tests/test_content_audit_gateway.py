from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import urllib.error
import urllib.request

import pytest

from secure_gateway.content_audit import ContentAuditStore
from secure_gateway.content_audit_capture import ContentAuditCapture, extract_content
from secure_gateway.content_audit_writer import ContentAuditWriter
from secure_gateway.gateway import PrivacyGateway


@contextmanager
def running_gateway(tmp_path, *, enabled=True, policy="continue", locked=False):
    observations = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            observations.append((payload, self.headers.get("X-SecureGateway-Audit")))
            text = payload["messages"][0]["content"]
            if payload.get("stream"):
                midpoint = len(text) // 2
                events = [{"type": "content_block_delta", "index": 0,
                           "delta": {"type": "text_delta", "text": part}}
                          for part in (text[:midpoint], text[midpoint:])]
                events.append({"type": "message_stop"})
                body = "".join("data: " + json.dumps(event) + "\n\n" for event in events).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            body = json.dumps({"content": [{"type": "text", "text": text}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with ThreadingHTTPServer(("127.0.0.1", 0), Provider) as upstream:
        upstream_thread = Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        origin = f"http://127.0.0.1:{upstream.server_port}"
        with PrivacyGateway(("127.0.0.1", 0), "local-token", upstreams={"claude": origin},
                            audit_path=tmp_path / "logs.sqlite3") as gateway:
            store = ContentAuditStore(tmp_path / "content-audit.sqlite3")
            store.initialize("audit-passphrase")
            if locked:
                store.lock()
            writer = ContentAuditWriter(store)
            gateway.content_audit = ContentAuditCapture(writer, enabled=enabled, policy=policy,
                                                        kinds={"input", "sent", "response"})
            thread = Thread(target=gateway.serve_forever, daemon=True)
            thread.start()
            try:
                yield gateway, store, writer, observations
            finally:
                gateway.shutdown()
                thread.join(5)
                writer.close()
                store.close()
                upstream.shutdown()
                upstream_thread.join(5)


def request(gateway, *, excluded=False, stream=False):
    headers = {"X-SecureGateway-Token": "local-token", "Authorization": "Bearer sk-ant-oat-test"}
    if excluded:
        headers["X-SecureGateway-Audit"] = "off"
    payload = {"model": "fixture", "messages": [{"role": "user", "content": "PrivateCustomer hello"}]}
    if stream:
        payload["stream"] = True
    req = urllib.request.Request(f"http://127.0.0.1:{gateway.server_port}/claude/v1/messages",
                                 data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        body = response.read()
        return body if stream else json.loads(body)


def test_real_gateway_captures_only_selected_fields(tmp_path):
    with running_gateway(tmp_path) as (gateway, store, writer, observations):
        response = request(gateway)
        writer.drain()
        with store._connect() as db:
            request_id = db.execute("SELECT request_id FROM requests").fetchone()[0]
        events = store.read(request_id)
        assert events[0][0] == "opened"
        assert "PrivateCustomer hello" in json.dumps(events[0][1])
        assert any(kind == "sent" and payload["content"]["phase"] == "sent" for kind, payload in events)
        assert any(kind == "response" for kind, payload in events)
        assert events[-1][0] == "finished"
        assert "PrivateCustomer hello" in json.dumps(response)
        assert "PrivateCustomer" not in json.dumps(observations[0][0])
        assert observations[0][1] is None


@pytest.mark.parametrize("enabled,excluded", [(False, False), (True, True)])
def test_disabled_or_excluded_requests_do_not_capture(tmp_path, enabled, excluded):
    with running_gateway(tmp_path, enabled=enabled) as (gateway, store, writer, observations):
        request(gateway, excluded=excluded)
        writer.drain()
        with store._connect() as db:
            assert db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
        assert len(observations) == 1
        assert observations[0][1] is None


def test_blocked_locked_store_never_calls_upstream(tmp_path):
    with running_gateway(tmp_path, policy="block", locked=True) as (gateway, store, writer, observations):
        with pytest.raises(urllib.error.HTTPError) as caught:
            request(gateway)
        assert caught.value.code == 503
        caught.value.close()
        assert not observations


def test_real_split_sse_records_received_and_displayed_text(tmp_path):
    with running_gateway(tmp_path) as (gateway, store, writer, observations):
        body = request(gateway, stream=True)
        assert b"PrivateCustomer" in body
        writer.drain()
        with store._connect() as db:
            request_id = db.execute("SELECT request_id FROM requests").fetchone()[0]
        events = store.read(request_id)
        responses = [payload["content"] for kind, payload in events if kind == "response"]
        assert {response["phase"] for response in responses} == {"received", "displayed"}
        assert "PrivateCustomer" not in json.dumps(responses[0])
        assert "PrivateCustomer" in json.dumps(responses[1])
        assert events[-1][1]["partial"] is False
        assert len(observations) == 1


def test_split_sse_credential_is_redacted_before_queue(tmp_path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3")
    store.initialize("passphrase")
    writer = ContentAuditWriter(store)
    capture = ContentAuditCapture(writer, enabled=True, kinds={"response"})
    assert capture.begin("one", {})
    capture.observe_sse("one", json.dumps({"type": "response.output_text.delta", "delta": "sk-abcdefghi"}), "received")
    capture.observe_sse("one", json.dumps({"type": "response.output_text.delta", "delta": "jklMNOP123456789"}), "received")
    capture.finish("one", uncertain=False, interrupted=False)
    writer.drain()
    serialized = json.dumps(store.read("one"))
    assert "sk-abcdefghijklMNOP123456789" not in serialized
    assert "[credential removed]" in serialized
    writer.close()
    store.close()


def test_tool_argument_json_discards_structural_credentials(tmp_path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3")
    store.initialize("passphrase")
    writer = ContentAuditWriter(store)
    capture = ContentAuditCapture(writer, enabled=True, kinds={"tool_args"})
    assert capture.begin("one", {})
    capture.observe("one", "tool_args", {"type": "function_call", "arguments": '{"password":"synthetic-canary"}'}, "masked")
    capture.finish("one", uncertain=False, interrupted=False)
    writer.drain()
    assert "synthetic-canary" not in json.dumps(store.read("one"))
    writer.close()
    store.close()


def test_pause_stops_capture_for_an_active_request(tmp_path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3")
    store.initialize("passphrase")
    writer = ContentAuditWriter(store)
    capture = ContentAuditCapture(writer, enabled=True, kinds={"response"})
    assert capture.begin("one", {})
    capture.paused = True
    capture.observe("one", "response", {"content": "not retained"}, "received")
    capture.paused = False
    capture.finish("one", uncertain=False, interrupted=False)
    writer.drain()
    events = store.read("one")
    assert "not retained" not in json.dumps(events)
    assert events[-1][1]["partial"] is True
    writer.close()
    store.close()


def test_capture_failure_does_not_interrupt_request(tmp_path, monkeypatch):
    with running_gateway(tmp_path) as (gateway, store, writer, observations):
        def fail_capture(*args, **kwargs):
            raise RuntimeError("sensitive failure text")

        monkeypatch.setattr(writer, "capture", fail_capture)
        response = request(gateway)
        writer.drain()
        assert "PrivateCustomer hello" in json.dumps(response)
        assert len(observations) == 1
        with store._connect() as db:
            request_id = db.execute("SELECT request_id FROM requests").fetchone()[0]
        assert writer.status(request_id)["state"] == "기록 실패"


@pytest.mark.parametrize("policy,expected_status,expected_calls", [("continue", 200, 1), ("block", 503, 0)])
def test_disk_failure_respects_policy_without_duplicate_inference(tmp_path, monkeypatch, capsys,
                                                                policy, expected_status, expected_calls):
    with running_gateway(tmp_path, policy=policy) as (gateway, store, writer, observations):
        def fail_write(*args, **kwargs):
            raise OSError("synthetic-sensitive-error-canary")

        monkeypatch.setattr(store, "append", fail_write)
        if expected_status == 200:
            assert "PrivateCustomer hello" in json.dumps(request(gateway))
        else:
            with pytest.raises(urllib.error.HTTPError) as caught:
                request(gateway)
            assert caught.value.code == expected_status
            assert b"synthetic-sensitive-error-canary" not in caught.value.read()
            caught.value.close()
        writer.drain()
        assert len(observations) == expected_calls
        assert "synthetic-sensitive-error-canary" not in capsys.readouterr().err
        with gateway.audit.connect() as db:
            request_id, attempted = db.execute("SELECT request_id, upstream_attempted FROM requests").fetchone()
        assert attempted == expected_calls
        assert store.request_status(request_id)["state"] == "기록 실패"


def test_claude_stream_tool_arguments_are_redacted_after_reassembly(tmp_path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3")
    store.initialize("passphrase")
    writer = ContentAuditWriter(store)
    capture = ContentAuditCapture(writer, enabled=True, kinds={"tool_args"})
    assert capture.begin("one", {})
    for part in ('{"password":', '"synthetic-canary", "safe": 1}'):
        event = {"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": part}}
        capture.observe_sse("one", json.dumps(event), "received")
    capture.finish("one", uncertain=False, interrupted=False)
    writer.drain()
    output = json.dumps(store.read("one"))
    assert "synthetic-canary" not in output
    assert '"safe": 1' in output
    writer.close()
    store.close()


def test_selected_kinds_do_not_include_other_kinds():
    envelope = {"messages": [{"role": "user", "content": "plain-input"},
                             {"role": "user", "content": [{"type": "tool_result", "content": "result-canary"}]},
                             {"role": "assistant", "content": [{"type": "tool_use", "input": {"x": "args-canary"}}]}]}
    assert extract_content(envelope, "input") == ["plain-input"]
    assert extract_content(envelope, "tool_result") == ["result-canary"]
    assert extract_content(envelope, "tool_args") == [{"x": "args-canary"}]


def test_admin_enables_real_capture_and_records_selection_intent(tmp_path):
    with running_gateway(tmp_path) as (gateway, store, writer, observations):
        gateway.content_audit = None

        def admin(endpoint, payload=None, method=None):
            data = None if payload is None else json.dumps(payload).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{gateway.server_port}/admin/api/content-audit/{endpoint}",
                                         data=data, method=method, headers={"X-SecureGateway-Token": "local-token"})
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read())

        admin("unlock", {"passphrase": "audit-passphrase"})
        settings = admin("settings")
        settings["enabled"] = True
        settings["providers"]["claude"] = True
        settings["kinds"]["input"] = True
        admin("settings", {"settings": settings, "confirm_sensitive_content": True}, "PUT")
        request(gateway)
        request(gateway, excluded=True)
        gateway.content_admin.writer.drain()
        with gateway.audit.connect() as db:
            rows = db.execute("SELECT request_id, content_audit FROM requests ORDER BY id").fetchall()
        assert [row[1] for row in rows] == ["capture", "excluded"]
        records = gateway.content_admin.store.read(rows[0][0])
        assert [kind for kind, _ in records] == ["opened", "finished"]
        assert gateway.content_admin.store.read(rows[1][0]) == []
        assert len(observations) == 2
