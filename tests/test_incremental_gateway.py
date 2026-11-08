"""Actual incremental delivery and conversation-scoped restoration contracts."""

from contextlib import contextmanager
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Event, Thread

import pytest

from secure_gateway.gateway import GatewaySession, PrivacyGateway
from secure_gateway.gateway_stream import EventRestorer


def frame(event):
    return "data: " + json.dumps(event, ensure_ascii=False)


@pytest.mark.parametrize("dialect", ["codex", "claude"])
def test_every_split_of_alias_streams_without_corruption(dialect):
    for cut in range(1, 17):
        session = GatewaySession()
        alias = session.mask("confidential-name", code=True)
        restorer = EventRestorer(session)
        output = b""
        for text in ("Hello " + alias[:cut], alias[cut:] + " next "):
            event = ({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}}
                     if dialect == "claude" else {"type": "response.output_text.delta", "item_id": "msg", "delta": text})
            output += restorer.feed(frame(event))
        output += restorer.finish()
        events = [json.loads(line[6:]) for line in output.decode().splitlines() if line.startswith("data: ")]
        text = "".join(event["delta"]["text"] if dialect == "claude" else event["delta"] for event in events)
        assert text == "Hello confidential-name next "


def test_tool_json_is_not_released_until_validated():
    session = GatewaySession()
    alias = session.mask("D:/private/report.txt")
    restore = EventRestorer(session)
    assert restore.feed(frame({"type": "response.function_call_arguments.delta", "item_id": "a", "delta": '{"file_path":"' + alias[:5]})) == b""
    assert restore.feed(": upstream heartbeat") == b": upstream heartbeat\n\n"
    assert restore.feed(frame({"type": "response.function_call_arguments.delta", "item_id": "a", "delta": alias[5:] + '"}'})) == b""
    output = restore.feed(frame({"type": "response.function_call_arguments.done", "item_id": "a", "arguments": '{"file_path":"' + alias + '"}'}))
    assert b"D:/private/report.txt" in output
    assert alias.encode() not in output


@contextmanager
def serve(server):
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


def test_real_http_first_event_arrives_before_upstream_finishes():
    release = Event()

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write((frame({"type": "response.output_text.delta", "item_id": "msg", "delta": "Ready now "}) + "\n\n").encode())
            self.wfile.flush()
            release.wait(5)
            self.wfile.write(b"data: [DONE]\n\n")

    with serve(ThreadingHTTPServer(("127.0.0.1", 0), Provider)) as provider:
        with serve(PrivacyGateway(("127.0.0.1", 0), "local-token", upstreams={"codex": f"http://127.0.0.1:{provider.server_port}"})) as gateway:
            client = http.client.HTTPConnection("127.0.0.1", gateway.server_port, timeout=2)
            client.request("POST", "/codex/responses", json.dumps({"model": "fixture", "input": [], "stream": True}),
                           {"Content-Type": "application/json", "X-SecureGateway-Token": "local-token", "Authorization": "Bearer eyJfixture"})
            try:
                response = client.getresponse()
                assert response.status == 200
                assert b"gateway connected" in response.readline()
                assert response.readline() == b"\n"
                assert b"Ready now" in response.readline()
                assert not release.is_set()
                release.set()
                response.read()
            finally:
                release.set()
                client.close()


def test_conversation_snapshots_and_provenance_are_isolated(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        a, b = gateway.get_session("codex", "account:a"), gateway.get_session("codex", "account:b")
        assert a is not b
        alias = a.mask("only-conversation-a", code=True)
        a.opaque.add("a" * 64)
        gateway.save("codex", a)
        gateway.save("codex", b)
        with pytest.raises(ValueError):
            b.restore(alias)
        key = a.storage_key
    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        a = gateway.get_session("codex", "account:a")
        assert a.storage_key == key and a.restore(alias) == "only-conversation-a"
        assert "a" * 64 in a.opaque
        assert "a" * 64 not in gateway.get_session("codex", "account:b").opaque
        gateway.reset("codex")
        assert not list(tmp_path.glob("codex*-symbols-v2.enc"))


def test_mask_cache_invalidates_when_protected_rules_change():
    session = GatewaySession()
    first = session.mask("please read the report")
    assert session.mask("please read the report") == first
    session.forced_rules = lambda: ("read",)
    assert "read" not in session.mask("please read the report")
