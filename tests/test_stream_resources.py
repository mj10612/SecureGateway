"""Resource lifetime and cleanup diagnostics for #332 (bounded, no fake FD monitor)."""

from __future__ import annotations

from collections import deque
from io import BytesIO
import json
import logging
import os
from threading import Event, Lock, Thread
from types import SimpleNamespace

import pytest

from secure_gateway.gateway import GatewaySession
from secure_gateway.gateway_stream import relay_stream


def _frame(event):
    return "data: " + json.dumps(event, ensure_ascii=False)


def _text_event(text):
    return {"type": "response.output_text.delta", "item_id": "message", "delta": text}


def _handler(output=None):
    return SimpleNamespace(
        wfile=BytesIO() if output is None else output,
        audit_metadata={},
        send_response=lambda *_: None,
        send_header=lambda *_: None,
        end_headers=lambda: None,
    )


class _ChunkedUpstream:
    def __init__(self, chunks):
        self.chunks = deque(chunks)
        self.closed = 0

    def read1(self, _):
        return self.chunks.popleft() if self.chunks else b""

    def close(self):
        self.closed += 1


class _RaisingCloseUpstream(_ChunkedUpstream):
    def close(self):
        self.closed += 1
        raise OSError("synthetic close failure")


class _ExplodingReaderUpstream:
    def __init__(self):
        self.closed = 0

    def read1(self, _):
        raise RuntimeError("reader boom")

    def close(self):
        self.closed += 1


def _messages(caplog):
    return [record.getMessage() for record in caplog.records]


def test_cleanup_diagnostics_are_fixed_category_only(caplog):
    upstream = _RaisingCloseUpstream([(_frame(_text_event("ok")) + "\n\ndata: [DONE]\n\n").encode()])
    with caplog.at_level(logging.WARNING, logger="secure_gateway.gateway_stream"):
        with pytest.raises(OSError, match="synthetic close failure"):
            relay_stream(_handler(), upstream, GatewaySession(), heartbeat=0.05)
    messages = _messages(caplog)
    assert any("upstream_close_failed" in message for message in messages)
    assert all("synthetic close failure" not in message for message in messages)
    assert all("alice@" not in message and "Authorization" not in message for message in messages)
    assert upstream.closed == 1


def test_close_failure_does_not_hide_primary_stream_failure(caplog):
    class _Disconnecting(BytesIO):
        def write(self, body):
            if b"gateway connected" in body:
                raise BrokenPipeError("gone")
            return super().write(body)

    upstream = _RaisingCloseUpstream([b"data: [DONE]\n\n"])
    with caplog.at_level(logging.WARNING, logger="secure_gateway.gateway_stream"):
        with pytest.raises(BrokenPipeError, match="gone"):
            relay_stream(_handler(_Disconnecting()), upstream, GatewaySession(), heartbeat=0.05)
    assert any("upstream_close_failed" in m for m in _messages(caplog))
    assert upstream.closed == 1


def test_upstream_closed_exactly_once_on_eof():
    upstream = _ChunkedUpstream([(_frame(_text_event("done")) + "\n\ndata: [DONE]\n\n").encode()])
    relay_stream(_handler(), upstream, GatewaySession(), heartbeat=0.05)
    assert upstream.closed == 1


def test_upstream_closed_exactly_once_on_reader_exception():
    upstream = _ExplodingReaderUpstream()
    with pytest.raises(RuntimeError, match="reader boom"):
        relay_stream(_handler(), upstream, GatewaySession(), heartbeat=0.05)
    assert upstream.closed == 1


def test_upstream_closed_exactly_once_on_client_disconnect():
    class _Disconnecting(BytesIO):
        def write(self, body):
            if b"gateway connected" in body:
                raise BrokenPipeError("gone")
            return super().write(body)

    upstream = _ChunkedUpstream([b": keepalive\n\n", b"data: [DONE]\n\n"])
    with pytest.raises(BrokenPipeError):
        relay_stream(_handler(_Disconnecting()), upstream, GatewaySession(), heartbeat=0.05)
    assert upstream.closed == 1


def test_upstream_closed_exactly_once_on_output_budget():
    upstream = _ChunkedUpstream([b"data: [DONE]\n\n"])
    with pytest.raises(ValueError, match="SSE output budget exceeded"):
        relay_stream(_handler(), upstream, GatewaySession(), heartbeat=0.05, limit=25)
    assert upstream.closed == 1


def test_detached_reader_owned_file_closed_exactly_once_and_owner_does_not_block(caplog):
    in_read, disconnected, unblock = Event(), Event(), Event()

    class _Raw:
        def __init__(self):
            self._sock = SimpleNamespace(shutdown=lambda *_: None)
            self.closed = 0

        def close(self):
            self.closed += 1

    class _OwnedFile:
        def __init__(self):
            self.lock = Lock()
            self.raw = _Raw()
            self.closed = 0

        def read1(self, _):
            with self.lock:
                in_read.set()
                unblock.wait(5)
                return b""

        def close(self):
            with self.lock:
                self.closed += 1

    owned_file = _OwnedFile()

    class _Response:
        def __init__(self):
            self.fp = owned_file
            self.closed = 0

        def read1(self, size):
            fp = self.fp
            return b"" if fp is None else fp.read1(size)

        def close(self):
            self.closed += 1
            fp, self.fp = self.fp, None
            if fp is not None:
                fp.close()

    class _Disconnecting(BytesIO):
        def write(self, body):
            if b"gateway waiting" in body and in_read.is_set():
                disconnected.set()
                raise BrokenPipeError("disconnect")
            return super().write(body)

    upstream = _Response()
    relay_done, owner_closed = Event(), Event()
    with caplog.at_level(logging.WARNING, logger="secure_gateway.gateway_stream"):

        def run_relay():
            try:
                relay_stream(_handler(_Disconnecting()), upstream, GatewaySession(), heartbeat=0.01)
            except BrokenPipeError:
                pass
            finally:
                relay_done.set()

        def owner_exit():
            upstream.close()
            owner_closed.set()

        Thread(target=run_relay, daemon=True).start()
        assert in_read.wait(5) and disconnected.wait(5)
        assert relay_done.wait(5), "relay blocked on detached reader-owned file"
        Thread(target=owner_exit, daemon=True).start()
        assert owner_closed.wait(5), "owner close blocked on detached reader-owned file"
        assert upstream.fp is None
        assert owned_file.closed == 0, "detached file closed before reader ownership handoff completed"
    unblock.set()
    for _ in range(100):
        if owned_file.closed == 1:
            break
        Event().wait(0.05)
    assert owned_file.closed == 1
    assert all("disconnect" not in m and "Authorization" not in m for m in _messages(caplog))


def test_wakeable_client_disconnect_completes_with_bounded_worker_join():
    entered = Event()

    class _Upstream:
        def __init__(self):
            self.closed = 0

        def read1(self, _):
            entered.set()
            return b""

        def close(self):
            self.closed += 1

    class _Disconnecting(BytesIO):
        def write(self, body):
            if b"gateway connected" in body and entered.wait(2):
                raise BrokenPipeError("gone")
            return super().write(body)

    upstream = _Upstream()
    relay_done = Event()

    def run_relay():
        try:
            relay_stream(_handler(_Disconnecting()), upstream, GatewaySession(), heartbeat=0.05)
        except BrokenPipeError:
            pass
        finally:
            relay_done.set()

    Thread(target=run_relay, daemon=True).start()
    assert relay_done.wait(5)
    assert upstream.closed == 1


def test_reader_owned_file_close_failure_logs_fixed_category_without_exception_text(caplog):
    in_read, disconnected, unblock = Event(), Event(), Event()

    class _Raw:
        _sock = SimpleNamespace(shutdown=lambda *_: None)

        def close(self):
            pass

    class _File:
        def __init__(self):
            self.lock = Lock()
            self.raw = _Raw()

        def read1(self, _):
            with self.lock:
                in_read.set()
                unblock.wait(5)
                return b""

        def close(self):
            raise ValueError("hidden buffered close detail")

    class _Response:
        def __init__(self):
            self.fp = _File()

        def read1(self, size):
            return self.fp.read1(size)

        def close(self):
            self.fp = None

    class _Disconnecting(BytesIO):
        def write(self, body):
            if b"gateway waiting" in body and in_read.is_set():
                disconnected.set()
                raise BrokenPipeError("disconnect")
            return super().write(body)

    upstream = _Response()
    relay_done = Event()
    with caplog.at_level(logging.WARNING, logger="secure_gateway.gateway_stream"):

        def run_relay():
            try:
                relay_stream(_handler(_Disconnecting()), upstream, GatewaySession(), heartbeat=0.01)
            except BrokenPipeError:
                pass
            finally:
                relay_done.set()

        Thread(target=run_relay, daemon=True).start()
        assert in_read.wait(5) and disconnected.wait(5)
        assert relay_done.wait(5)
        unblock.set()
        for _ in range(100):
            if any("reader_owned_file_close_failed" in r.getMessage() for r in caplog.records):
                break
            Event().wait(0.05)
    messages = _messages(caplog)
    assert any("reader_owned_file_close_failed" in message for message in messages)
    assert all("hidden buffered close detail" not in message for message in messages)


def test_bounded_os_pipe_lifetime_releases_actual_descriptors():
    """Use real OS pipes/files; no process-wide FD threshold is claimed as proof."""
    errors = []

    def run_once():
        read_fd, write_fd = os.pipe()
        read_file = os.fdopen(read_fd, "rb", closefd=True)
        try:
            os.write(write_fd, b"data: [DONE]\n\n")
        finally:
            os.close(write_fd)

        class _PipeUpstream:
            def __init__(self, fp):
                self.fp = fp
                self.closed = 0

            def read1(self, n):
                return self.fp.read1(n)

            def read(self, n=-1):
                return self.fp.read(n)

            def close(self):
                self.closed += 1
                try:
                    self.fp.close()
                except OSError:
                    pass

        upstream = _PipeUpstream(read_file)
        relay_stream(_handler(), upstream, GatewaySession(), heartbeat=0.05)
        if upstream.closed != 1:
            errors.append("close-count")
            return
        try:
            os.fstat(read_fd)
        except OSError:
            return
        errors.append("fd-still-open")

    for _ in range(40):
        run_once()
    assert not errors
