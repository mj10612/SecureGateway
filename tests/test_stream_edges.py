"""SSE framing, durability barriers and blocked-reader cancellation regressions."""

from collections import deque
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from threading import Event, Lock, Thread
from types import SimpleNamespace
import urllib.request

import pytest

from secure_gateway.gateway import GatewaySession, PrivacyGateway
from secure_gateway.gateway_stream import EventRestorer, relay_stream
from secure_gateway.models import TokenMapping, TokenType


def frame(event):
    return "data: " + json.dumps(event, ensure_ascii=False)


def text_event(text):
    return {"type": "response.output_text.delta", "item_id": "message", "delta": text}


def text_from(body):
    events = [json.loads(line[6:]) for line in body.decode().splitlines()
              if line.startswith("data: ") and line != "data: [DONE]"]
    return "".join(event.get("delta", "") for event in events
                   if event.get("type") == "response.output_text.delta")


def handler(output=None):
    return SimpleNamespace(wfile=BytesIO() if output is None else output,
                           audit_metadata={}, send_response=lambda _: None,
                           send_header=lambda *_: None, end_headers=lambda: None)


class ChunkedUpstream:
    def __init__(self, chunks):
        self.chunks = deque(chunks)
        self.closed = False

    def read1(self, _):
        return self.chunks.popleft() if self.chunks else b""

    def close(self):
        self.closed = True


def test_upstream_heartbeat_does_not_flush_partial_alias():
    session = GatewaySession()
    alias = session.mask("private-name", code=True)
    stream = EventRestorer(session)
    assert stream.feed(frame(text_event(alias[:8]))) == b""
    assert stream.feed(": upstream ping") == b": upstream ping\n\n"
    output = stream.feed(frame(text_event(alias[8:] + " "))) + stream.finish()
    assert text_from(output) == "private-name "
    assert alias.encode() not in output


@pytest.mark.parametrize("template", ["def test_{}():", "{}_v2 = 1", "see {}s list"])
def test_derived_identifier_restores_across_every_sse_delta_split(template):
    session = GatewaySession()
    alias = session.mask("calculate_invoice_total", code=True)
    source = template.format(alias)
    expected = template.format("calculate_invoice_total")
    for cut in range(1, len(source)):
        stream = EventRestorer(session)
        output = stream.feed(frame(text_event(source[:cut])))
        output += stream.feed(frame(text_event(source[cut:])))
        output += stream.finish()
        assert text_from(output) == expected
        assert alias.encode() not in output


def test_upstream_heartbeat_does_not_flush_partial_tool_json():
    session = GatewaySession()
    alias = session.mask("private/path.txt", code=True)
    stream = EventRestorer(session)
    base = {"type": "response.function_call_arguments.delta", "item_id": "call"}
    assert stream.feed(frame({**base, "delta": '{"path":"' + alias[:6]})) == b""
    assert stream.feed(": ping") == b": ping\n\n"
    assert stream.feed(frame({**base, "delta": alias[6:] + '"}'})) == b""
    output = stream.feed(frame({"type": "response.function_call_arguments.done", "item_id": "call",
                                "arguments": '{"path":"' + alias + '"}'}))
    assert b"private/path.txt" in output and alias.encode() not in output


@pytest.mark.parametrize("ending", ["\n", "\r", "\r\n"])
def test_relay_accepts_sse_newlines_split_at_every_byte(ending):
    # One-byte reads also split every CRLF pair and the UTF-8 spelling of 한글.
    source = ((frame(text_event("한글 ready ")) + "\n\ndata: [DONE]\n\n")
              .replace("\n", ending)).encode()
    upstream = ChunkedUpstream([source[i:i + 1] for i in range(len(source))])
    target = handler()
    relay_stream(target, upstream, GatewaySession(), heartbeat=0.05)
    assert text_from(target.wfile.getvalue()) == "한글 ready "
    assert b"data: [DONE]" in target.wfile.getvalue()
    assert upstream.closed


def test_authorized_whitespace_alias_restores_across_every_delta_split():
    alias = "s\\\nmcp_ID_1"
    for cut in range(1, len(alias)):
        session = GatewaySession()
        session.session.reverse_store[alias] = TokenMapping(
            original="privateName", surrogate=alias, token_type=TokenType.IDENTIFIER,
            context="code", identifier_base="smcp_ID_1", identifier_language="bash",
            identifier_key="privateName")
        stream = EventRestorer(session)
        output = stream.feed(frame(text_event(alias[:cut])))
        output += stream.feed(frame(text_event(alias[cut:] + " ")))
        output += stream.finish()
        assert text_from(output) == "privateName "


@pytest.mark.parametrize("terminal", ["response.completed", "message_stop", "[DONE]"])
def test_snapshot_failure_prevents_stream_completion_event(terminal):
    terminal_frame = "data: [DONE]" if terminal == "[DONE]" else frame({"type": terminal})
    upstream = ChunkedUpstream([(frame(text_event("Visible progress ")) + "\n\n" + terminal_frame + "\n\n").encode()])
    target = handler()
    called = []

    def failed_save():
        called.append(True)
        raise OSError("snapshot write failed")

    with pytest.raises(OSError, match="snapshot write failed"):
        relay_stream(target, upstream, GatewaySession(), heartbeat=0.05, before_complete=failed_save)
    assert called == [True]
    assert terminal.encode() not in target.wfile.getvalue()
    assert text_from(target.wfile.getvalue()) == "Visible progress "
    assert upstream.closed


@contextmanager
def provider_server(server):
    worker = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        worker.join(2)


def test_disconnected_client_releases_admission_before_idle_upstream_finishes():
    release, entered, done = Event(), Event(), Event()
    read_started, disconnected, provider_finished = Event(), Event(), Event()

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.flush()
            entered.set()
            release.wait(5)
            provider_finished.set()

    class DisconnectedClient(BytesIO):
        def write(self, body):
            if b"gateway waiting" in body:
                disconnected.set()
                raise BrokenPipeError("client disconnected")
            return super().write(body)

    errors = []
    with PrivacyGateway(("127.0.0.1", 0), "fixture-token") as gateway:
        # Session/tokenizer construction is setup, not cancellation latency.
        # Starting its timer in the relay thread could fail on a loaded runner
        # before the simulated client had even disconnected.
        session = gateway.get_session("codex")
        with provider_server(ThreadingHTTPServer(("127.0.0.1", 0), Provider)) as provider:
            upstream = urllib.request.urlopen(f"http://127.0.0.1:{provider.server_port}", timeout=5)
            assert entered.wait(1)
            original_read = upstream.read1

            def observed_read(size):
                read_started.set()
                return original_read(size)

            upstream.read1 = observed_read
            assert gateway.try_admit("codex")
            target = handler(DisconnectedClient())

            def relay():
                try:
                    relay_stream(target, upstream, session, heartbeat=0.05)
                except BrokenPipeError:
                    pass
                except Exception as exc:
                    errors.append(exc)
                finally:
                    gateway.release_admission("codex")
                    done.set()

            worker = Thread(target=relay, daemon=True)
            worker.start()
            try:
                assert read_started.wait(1), "upstream reader did not start"
                assert disconnected.wait(1), "relay did not observe client disconnection"
                assert done.wait(1.5), "client cancellation waited for idle upstream read"
                assert not release.is_set()
                assert not provider_finished.is_set(), "upstream ended before cancellation completed"
                assert gateway.admitted_requests == 0
                assert not errors
            finally:
                release.set()
                worker.join(3)
                upstream.close()
            assert not worker.is_alive()


def test_cancellation_does_not_wait_for_reader_buffer_lock_when_socket_wakeup_is_missed():
    """Model a platform where shutdown/close does not wake an in-flight recv.

    http.client closes its BufferedReader under the same lock read1 holds, so a
    cancelled relay must not close that file inline. The reader thread owns the
    final close and the response itself becomes immediately closable.
    """
    in_read, disconnected, unblock, file_closed = Event(), Event(), Event(), Event()

    class UnwakeableSocket:
        def shutdown(self, _how):
            pass  # deliberately ineffective, like a missed kernel wakeup

    class LockedFile:
        def __init__(self):
            self.lock = Lock()
            self.raw = SimpleNamespace(_sock=UnwakeableSocket(), close=lambda: None)

        def read1(self, _size):
            with self.lock:
                in_read.set()
                unblock.wait(10)
                return b""

        def close(self):
            with self.lock:
                file_closed.set()

    class Response:
        def __init__(self):
            self.fp = LockedFile()

        def read1(self, size):
            fp = self.fp
            return b"" if fp is None else fp.read1(size)

        def close(self):
            fp, self.fp = self.fp, None
            if fp is not None:
                fp.close()

    class DisconnectedClient(BytesIO):
        def write(self, body):
            if b"gateway waiting" in body and in_read.is_set():
                disconnected.set()
                raise BrokenPipeError("client disconnected")
            return super().write(body)

    upstream = Response()
    relay_done, owner_closed = Event(), Event()

    def relay():
        try:
            relay_stream(handler(DisconnectedClient()), upstream, GatewaySession(), heartbeat=0.01)
        except BrokenPipeError:
            pass
        finally:
            relay_done.set()

    def owner_exit():
        upstream.close()  # what `with upstream_response:` does after relay_stream
        owner_closed.set()

    worker = Thread(target=relay, daemon=True)
    worker.start()
    try:
        assert in_read.wait(5) and disconnected.wait(5)
        # Before the fix this cannot complete until `unblock`, whatever the timeout.
        assert relay_done.wait(5), "relay waited for the blocked reader's buffer lock"
        closer = Thread(target=owner_exit, daemon=True)
        closer.start()
        assert owner_closed.wait(5), "response close waited for the blocked reader"
        assert not unblock.is_set() and not file_closed.is_set()
    finally:
        unblock.set()
        worker.join(5)
    assert file_closed.wait(5), "reader thread did not close the handed-off file"


def test_capture_errors_and_invalid_display_bytes_do_not_abort_stream(monkeypatch):
    original_feed = EventRestorer.feed

    def feed(self, value):
        if value == ': synthetic':
            return b': invalid \xff\n\n'
        return original_feed(self, value)

    class BrokenCapture:
        def __init__(self):
            self.failures = []

        def observe_sse(self, *_args):
            raise RuntimeError('synthetic capture failure')

        def _failed(self, request_id):
            self.failures.append(request_id)

    monkeypatch.setattr(EventRestorer, 'feed', feed)
    capture = BrokenCapture()
    target = handler()
    target.content_stream_capture = (capture, 'request1')
    upstream = ChunkedUpstream([b': synthetic\n\ndata: [DONE]\n\n'])
    relay_stream(target, upstream, GatewaySession(), heartbeat=0.05)
    assert target.wfile.getvalue() == b': gateway connected\n\n: invalid \xff\n\ndata: [DONE]\n\n'
    assert capture.failures
