"""Early HTTP rejection must survive POST bytes arriving after the headers."""

from io import BytesIO
import socket
from threading import Thread
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from secure_gateway import gateway as module
from secure_gateway.gateway import GatewayHandler, LIMIT, PrivacyGateway


@pytest.fixture
def local_gateway():
    gateway = PrivacyGateway(("127.0.0.1", 0), "local-fixture-token")
    thread = Thread(target=gateway.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    try:
        yield gateway
    finally:
        gateway.shutdown()
        gateway.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


@pytest.mark.parametrize("size", [256, 65536, 1024 * 1024])
@pytest.mark.parametrize("headers", [
    "",
    "X-SecureGateway-Token: local-fixture-token\r\n",
    "X-SecureGateway-Token: local-fixture-token\r\n"
    "Authorization: Bearer sk-ant-oat-offline\r\nx-api-key: fixture-key\r\n",
])
def test_delayed_rejected_post_preserves_complete_401(local_gateway, size, headers):
    # urllib sends headers and body separately. Force the scheduling gap that
    # used to abort the response on Windows before the client saw its status.
    with socket.create_connection(("127.0.0.1", local_gateway.server_port), timeout=5) as client:
        client.sendall((
            "POST /claude/v1/messages HTTP/1.1\r\nHost: localhost\r\n"
            f"Content-Length: {size}\r\n{headers}\r\n"
        ).encode())
        time.sleep(0.01)
        client.sendall(b"x" * size)
        response = b""
        while block := client.recv(65536):
            response += block
    head, body = response.split(b"\r\n\r\n", 1)
    assert head.startswith(b"HTTP/1.0 401 ")
    lengths = [line for line in head.split(b"\r\n") if line.lower().startswith(b"content-length:")]
    assert len(body) == int(lengths[0].split(b":", 1)[1])
    assert b"error" in body


def unfinished_handler(headers=None, *, consumed=False):
    handler = GatewayHandler.__new__(GatewayHandler)
    handler.command = "POST"
    handler.headers = headers if headers is not None else {"Content-Length": "256"}
    handler._request_body_consumed = consumed
    handler.connection = Mock()
    handler.wfile = BytesIO(b"response")
    handler.rfile = BytesIO(b"body")
    return handler


@pytest.mark.parametrize("headers,consumed", [
    ({"Content-Length": "256"}, True),
    ({}, False),
    ({"Content-Length": "invalid"}, False),
    ({"Content-Length": "0"}, False),
    ({"Content-Length": "-1"}, False),
    ({"Content-Length": str(LIMIT + 1)}, False),
    ({"Content-Length": "256", "Transfer-Encoding": "chunked"}, False),
])
def test_finish_does_not_drain_consumed_or_unbounded_request(headers, consumed):
    handler = unfinished_handler(headers, consumed=consumed)
    handler.finish()
    handler.connection.shutdown.assert_not_called()
    handler.connection.settimeout.assert_not_called()
    assert handler.rfile.closed and handler.wfile.closed


def test_drain_has_absolute_time_budget_even_while_bytes_keep_arriving(monkeypatch):
    handler = unfinished_handler({"Content-Length": "1000"})
    handler.rfile = Mock()
    handler.rfile.read1.return_value = b"x"
    ticks = iter([0.0, 0.02, 0.08, 0.11])
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    handler.finish()
    assert handler.rfile.read1.call_count == 2
    assert [call.args[0] for call in handler.connection.settimeout.call_args_list] == pytest.approx([0.08, 0.02])
    handler.rfile.close.assert_called_once()
    assert handler.wfile.closed


def test_drain_never_exceeds_declared_size_or_chunk_limit(monkeypatch):
    handler = unfinished_handler({"Content-Length": str(LIMIT)})
    handler.rfile = Mock()
    handler.rfile.read1.side_effect = lambda size: b"x" * size
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: 0.0))
    handler.finish()
    sizes = [call.args[0] for call in handler.rfile.read1.call_args_list]
    assert sum(sizes) == LIMIT
    assert max(sizes) <= 65536
    handler.rfile.close.assert_called_once()


@pytest.mark.parametrize("failure", [TimeoutError(), ConnectionResetError(), ValueError("closed")])
def test_drain_failure_always_closes_streams(failure):
    handler = unfinished_handler()
    handler.rfile = Mock()
    handler.rfile.read1.side_effect = failure
    handler.finish()
    handler.rfile.close.assert_called_once()
    assert handler.wfile.closed


def test_no_headers_after_request_parse_failure_still_closes_streams():
    handler = unfinished_handler()
    del handler.headers
    handler.finish()
    assert handler.rfile.closed and handler.wfile.closed
