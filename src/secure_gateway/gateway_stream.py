"""Bounded incremental SSE transport; tool JSON is released only when complete."""

from __future__ import annotations

import codecs
import json
import logging
import queue
import re
import socket
import time
from threading import Event, Lock, Thread
from typing import Any

_logger = logging.getLogger(__name__)


def _cleanup_diag(category: str) -> None:
    """Log a fixed-category cleanup diagnostic without sensitive details."""
    _logger.warning("stream cleanup: %s", category)


class EventRestorer:
    """Keep only an unfinished text token or a complete tool/thinking group.

    Text is emitted at whitespace boundaries so split aliases are never
    interpreted before the following character is known. Structured tool calls
    and signed thinking retain the gateway's existing whole-group validator.
    """

    def __init__(self, session, dialect=None, limit=16 * 1024 * 1024):
        self.session, self.dialect, self.limit = session, dialect, limit
        self.pending = ""
        self.text_event = None
        self.text_lines = []
        self.text_key = None
        self.group = []
        self.group_size = 0

    def _emit(self, lines, event):
        body = "\n".join([line for line in lines if not line.startswith("data:")]
                         + ["data: " + json.dumps(event, ensure_ascii=False, allow_nan=False)])
        return (body + "\n\n").encode()

    def _flush_text(self):
        if not self.pending:
            return b""
        event = self.text_event
        if event is None:
            raise ValueError("Missing SSE text envelope")
        with self.session.lock:
            text = self.session.restore(self.pending)
        if event["type"] == "content_block_delta":
            event["delta"]["text"] = text
        else:
            event["delta"] = text
        self.pending = ""
        return self._emit(self.text_lines, event)

    def feed(self, frame):
        lines = frame.split("\n")
        data = "\n".join(line[5:].lstrip() for line in lines if line.startswith("data:"))
        if not data:
            # Upstream comments/heartbeats are not content boundaries.
            return (frame + "\n\n").encode()
        if data == "[DONE]":
            return self.finish() + (frame + "\n\n").encode()
        event = json.loads(data, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid SSE number")))
        if not isinstance(event, dict):
            raise ValueError("Invalid SSE event")
        kind = event.get("type")
        is_text = (kind in {"response.output_text.delta", "response.refusal.delta", "response.reasoning_summary_text.delta"}
                   or kind == "content_block_delta" and isinstance(event.get("delta"), dict)
                   and event["delta"].get("type") == "text_delta")
        output = b""
        if is_text and not self.group:
            key = (kind, event.get("item_id"), event.get("output_index"),
                   event.get("content_index"), event.get("summary_index"), event.get("index"))
            if self.text_key != key:
                output += self._flush_text()
            text = event["delta"]["text"] if kind == "content_block_delta" else event.get("delta")
            if not isinstance(text, str):
                raise ValueError("Invalid SSE text")
            self.text_key, self.text_event, self.text_lines = key, event, lines
            self.pending += text
            if len(self.pending.encode()) > self.limit:
                raise ValueError("SSE token budget exceeded")
            legacy = getattr(self.session.session.reverse_store, "nonstandard_surrogates", ())
            if any(any(char.isspace() for char in alias) for alias in legacy):
                # Bash continuations and other authorized spellings may span
                # whitespace. Preserve the complete text group in that case.
                return output
            # Keep the final token and its preceding whitespace until a later
            # token arrives; this preserves boundary context for strict aliases.
            matches = list(re.finditer(r"\s+", self.pending))
            if matches:
                split = matches[-1].end()
                prefix, self.pending = self.pending[:split], self.pending[split:]
                with self.session.lock:
                    restored = self.session.restore(prefix)
                if kind == "content_block_delta":
                    event["delta"]["text"] = restored
                else:
                    event["delta"] = restored
                output += self._emit(lines, event)
            return output
        output += self._flush_text()
        block = event.get("content_block", {})
        start_group = (self.dialect == "chat_completions"
                       or kind in {"response.function_call_arguments.delta", "response.custom_tool_call_input.delta"}
                       or kind == "content_block_start" and isinstance(block, dict)
                       and block.get("type") in {"tool_use", "thinking", "redacted_thinking"})
        if self.group or start_group:
            self.group.append(frame + "\n\n")
            self.group_size += len(frame.encode()) + 2
            if self.group_size > self.limit:
                raise ValueError("SSE group budget exceeded")
            done = (kind in {"content_block_stop", "response.function_call_arguments.done", "response.custom_tool_call_input.done", "response.output_item.done", "response.completed"}
                    or self.dialect == "chat_completions" and any(choice.get("finish_reason") for choice in event.get("choices", []) if isinstance(choice, dict)))
            if done:
                output += self._flush_group()
            return output
        with self.session.lock:
            return output + self.session.response((frame + "\n\n").encode(), "text/event-stream", dialect=self.dialect)

    def _flush_group(self):
        body = "".join(self.group).encode()
        with self.session.lock:
            output = self.session.response(body, "text/event-stream", dialect=self.dialect)
        self.group.clear()
        self.group_size = 0
        return output

    def finish(self):
        output = self._flush_text()
        if self.group:
            # Preserve whole-group validation, including malformed JSON errors.
            output += self._flush_group()
        return output


def relay_stream(handler, upstream, session, dialect=None, *, limit=16 * 1024 * 1024, heartbeat=5, before_complete=None):
    """Send headers now and safe events as they arrive, with local heartbeats."""
    chunks: queue.Queue = queue.Queue(maxsize=4)
    cancelled = Event()

    def put(item):
        while not cancelled.is_set():
            try:
                chunks.put(item, timeout=0.1)
                return
            except queue.Full:
                continue

    # `reading` is true only while the reader is inside an upstream read. A
    # cancelled relay hands the buffered file to the reader when a read is in
    # flight, because closing it inline waits on the same buffer lock.
    state_lock = Lock()
    reader_state: dict[str, Any] = {"reading": False, "owned_file": None}

    def read():
        try:
            while True:
                with state_lock:
                    if cancelled.is_set():
                        return
                    reader_state["reading"] = True
                try:
                    chunk = upstream.read1(65536) if hasattr(upstream, "read1") else upstream.read(65536)
                finally:
                    with state_lock:
                        reader_state["reading"] = False
                put(chunk)
                if not chunk:
                    return
        except Exception as exc:
            put(exc)
        finally:
            with state_lock:
                owned_file = reader_state["owned_file"]
            if owned_file is not None:
                try:
                    owned_file.close()
                except (OSError, ValueError):
                    _cleanup_diag("reader_owned_file_close_failed")

    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Connection", "close")
    handler.end_headers()
    handler.close_connection = True
    handler._stream_started = True
    if handler.audit_metadata is not None:
        handler.audit_metadata["status"] = 200
    started = time.perf_counter()
    handler.stream_metrics = {"first_event_ms": None, "input_bytes": 0, "output_bytes": 0}
    worker = Thread(target=read, daemon=True)
    worker.start()
    decoder = codecs.getincrementaldecoder("utf-8-sig")()
    buffer, total = "", 0
    restorer = EventRestorer(session, dialect, limit)
    previous_cr = False

    def normalize(text):
        nonlocal previous_cr
        output = []
        for char in text:
            if char == "\n" and previous_cr:
                previous_cr = False
                continue
            output.append("\n" if char == "\r" else char)
            previous_cr = char == "\r"
        return "".join(output)

    def write(body):
        if not body:
            return
        if handler.stream_metrics["output_bytes"] + len(body) > limit:
            raise ValueError("SSE output budget exceeded")
        handler.wfile.write(body)
        handler.wfile.flush()
        handler.stream_metrics["output_bytes"] += len(body)

    primary: BaseException | None = None
    try:
        write(b": gateway connected\n\n")
        while True:
            try:
                chunk = chunks.get(timeout=heartbeat)
            except queue.Empty:
                write(b": gateway waiting\n\n")
                continue
            if isinstance(chunk, Exception):
                raise chunk
            if not chunk:
                buffer += normalize(decoder.decode(b"", final=True))
                break
            total += len(chunk)
            handler.stream_metrics["input_bytes"] = total
            if total > limit:
                raise ValueError("SSE input budget exceeded")
            buffer += normalize(decoder.decode(chunk))
            while "\n\n" in buffer:
                frame, buffer = buffer.split("\n\n", 1)
                body = restorer.feed(frame)
                data = "\n".join(line[5:].lstrip() for line in frame.split("\n") if line.startswith("data:"))
                event = json.loads(data) if data and data != "[DONE]" else {}
                terminal = (data == "[DONE]" or isinstance(event, dict) and
                            event.get("type") in {"response.completed", "message_stop", "content_block_stop",
                                                  "response.output_item.done", "response.function_call_arguments.done",
                                                  "response.custom_tool_call_input.done"})
                if terminal and before_complete is not None:
                    # feed() registers signed provenance; completion stays
                    # buffered until the encrypted state is durable.
                    before_complete()
                if body and handler.stream_metrics["first_event_ms"] is None:
                    handler.stream_metrics["first_event_ms"] = round((time.perf_counter() - started) * 1000, 2)
                write(body)
        write(restorer.finish())
    except BaseException as exc:
        primary = exc
        raise
    finally:
        cancelled.set()
        interrupted_raw = False
        fp = getattr(upstream, "fp", None)
        raw = getattr(fp, "raw", None)
        upstream_socket = getattr(raw, "_sock", None)
        if worker.is_alive():
            # Interrupt read1 before close(): buffered file close may otherwise
            # wait for the reader's lock for the entire upstream socket timeout.
            if upstream_socket is not None and raw is not None:
                try:
                    upstream_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    _cleanup_diag("raw_socket_shutdown_failed")
                # On Windows, shutdown alone need not wake a timed recv's
                # select wait. Release the SocketIO ownership before closing
                # its buffered wrapper, whose lock the reader still holds.
                try:
                    raw.close()
                    interrupted_raw = True
                except OSError:
                    _cleanup_diag("raw_stream_interrupt_close_failed")
        with state_lock:
            # A kernel wakeup is not guaranteed on every platform (observed on
            # macOS runners): a still-blocked read1 keeps the buffer lock. Detach
            # that file so this close and the owner's later close cannot wait for
            # the upstream timeout; the reader closes it once its read returns.
            detached = reader_state["reading"] and fp is not None and upstream_socket is not None
            if detached:
                reader_state["owned_file"] = fp
                upstream.fp = None
        try:
            upstream.close()
        except (OSError, ValueError):
            # HTTPResponse.close flushes its buffered wrapper first; an
            # intentionally interrupted raw stream can already be closed.
            _cleanup_diag("upstream_close_failed")
            if not interrupted_raw and primary is None:
                raise
        if not detached:
            worker.join(timeout=1)
        if handler.audit_metadata is not None:
            handler.audit_metadata["output_bytes"] = handler.stream_metrics["output_bytes"]
