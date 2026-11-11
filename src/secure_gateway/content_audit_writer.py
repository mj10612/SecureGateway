"""Isolated asynchronous content-audit writer."""

from __future__ import annotations

import json
import queue
import re
import threading
from collections import deque
from typing import Any, Protocol

from secure_gateway.content_audit import LockedError, redact_credentials
from secure_gateway.logging_config import get_logger

_logger = get_logger("content_audit")

_CREDENTIAL_FIELDS = frozenset({
    "authorization", "proxyauthorization", "cookie", "setcookie", "apikey", "xapikey",
    "xsecuregatewaytoken", "accesstoken", "refreshtoken", "oauthtoken", "clientsecret",
    "token", "idtoken", "password", "passwd", "privatekey", "credential", "credentials", "secret",
})
_KINDS = frozenset({"input", "sent", "response", "tool_args", "tool_result"})


class AuditSink(Protocol):
    """The synchronous durable append operation used by the writer."""

    def append(self, request_id: str, kind: str, payload: Any) -> None:
        """Append an encrypted event or raise if it could not be written."""
        ...


def _sanitize(value: Any) -> tuple[Any, int]:
    if isinstance(value, str):
        return redact_credentials(value)
    if isinstance(value, list):
        output = []
        removed = 0
        for item in value:
            clean, count = _sanitize(item)
            output.append(clean)
            removed += count
        return output, removed
    if isinstance(value, dict):
        output_dict = {}
        removed = 0
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("Invalid audit content")
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if normalized in _CREDENTIAL_FIELDS:
                removed += 1
                continue
            clean_key, key_count = redact_credentials(key)
            clean, count = _sanitize(item)
            if clean_key in output_dict:
                raise ValueError("Invalid audit content")
            output_dict[clean_key] = clean
            removed += count + key_count
        return output_dict, removed
    if value is None or type(value) in (bool, int, float):
        return value, 0
    raise ValueError("Invalid audit content")


class ContentAuditWriter:
    """Bounded single-worker queue for selected, pre-extracted audit content."""

    def __init__(self, store: AuditSink, *, queue_size: int = 256,
                 kind_limit: int = 1024 * 1024, stream_limit: int = 2000):
        if any(type(v) is not int or v < 1 for v in (queue_size, kind_limit, stream_limit)):
            raise ValueError("Invalid content audit limits")
        self.store = store
        self.kind_limit, self.stream_limit = kind_limit, stream_limit
        self._queue: queue.Queue[tuple[str, str, Any] | None] = queue.Queue(maxsize=queue_size)
        self._lock = threading.Lock()
        self._requests: dict[str, dict[str, Any]] = {}
        self._pending_states: set[str] = set()
        self._release_pending: set[str] = set()
        self._completed: deque[str] = deque()
        self._wake_pending = False
        self._closed = False
        self._worker = threading.Thread(target=self._run, name="content-audit-writer", daemon=True)
        self._worker.start()

    def begin(self, request_id: str, policy: str, content: Any) -> bool:
        """Begin a request, durably synchronising admission only in block mode."""
        if policy not in {"continue", "block"} or not isinstance(request_id, str) or not request_id:
            raise ValueError("Invalid content audit admission")
        with self._lock:
            if self._closed or request_id in self._requests:
                raise ValueError("Invalid content audit admission")
            self._requests[request_id] = {
                "state": "부분", "omitted_bytes": 0, "omitted_events": 0,
                "sizes": {}, "stream_events": 0, "failed": False, "partial": False, "finished": False,
                "failure_reported": False,
            }
        protect = getattr(self.store, "protect", None)
        if callable(protect):
            protect(request_id)
        try:
            clean, count = _sanitize(content)
            size = len(json.dumps(clean, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        except (ValueError, TypeError, RecursionError, UnicodeError):
            self._fail(request_id)
            return policy == "continue"
        if size > self.kind_limit:
            with self._lock:
                state = self._requests[request_id]
                state["omitted_bytes"] += size
                state["partial"] = True
                self._dirty_locked(request_id)
            clean = None
            size = 0
        with self._lock:
            self._requests[request_id]["sizes"]["input"] = size
        payload = {"input": clean, "redactions": count}
        with self._lock:
            omitted_bytes = self._requests[request_id]["omitted_bytes"]
        if omitted_bytes:
            payload["omitted_bytes"] = omitted_bytes
        if policy == "block":
            try:
                self.store.append(request_id, "opened", payload)
            except Exception as exc:
                self._fail(request_id, isinstance(exc, LockedError))
                return False
            return True
        self._enqueue(request_id, "opened", payload)
        return True

    def capture(self, request_id: str, kind: str, content: Any, *, stream: bool = False) -> bool:
        """Queue a redacted event without waiting for disk or queue space."""
        if kind not in _KINDS:
            raise ValueError("Invalid audit kind")
        try:
            clean, count = _sanitize(content)
            size = len(json.dumps(clean, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        except (ValueError, TypeError, RecursionError, UnicodeError):
            self._fail(request_id)
            return False
        with self._lock:
            state = self._requests[request_id]
            if state["finished"] or self._closed:
                return False
            if stream and state["stream_events"] >= self.stream_limit:
                state["partial"] = True
                state["omitted_events"] += 1
                self._dirty_locked(request_id)
                return False
            if stream:
                state["stream_events"] += 1
            used = state["sizes"].get(kind, 0)
            if used + size > self.kind_limit:
                state["partial"] = True
                state["omitted_bytes"] += size
                self._dirty_locked(request_id)
                return False
            state["sizes"][kind] = used + size
            return self._enqueue_locked(request_id, kind, {"content": clean, "redactions": count})

    def finish(self, request_id: str, *, uncertain: bool = False, interrupted: bool = False) -> bool:
        """Queue an authenticated completion marker after all observed events."""
        with self._lock:
            state = self._requests[request_id]
            if state["finished"] or self._closed:
                return False
            state["finished"] = True
            self._release_pending.add(request_id)
            state["partial"] = state["partial"] or interrupted
            state["uncertain"] = uncertain
            marker = {"partial": state["partial"], "omitted_bytes": state["omitted_bytes"],
                      "omitted_events": state["omitted_events"], "failed": state["failed"],
                      "uncertain": uncertain}
            return self._enqueue_locked(request_id, "finished", marker)

    def omit(self, request_id: str, *, byte_count: int = 0, event_count: int = 0) -> None:
        """Mark content omitted before it entered the queue."""
        with self._lock:
            state = self._requests[request_id]
            state["partial"] = True
            state["omitted_bytes"] += byte_count
            state["omitted_events"] += event_count
            self._dirty_locked(request_id)

    def status(self, request_id: str) -> dict[str, Any]:
        """Return content-free in-memory state for one request."""
        with self._lock:
            state = self._requests[request_id]
            return {key: state[key] for key in ("state", "omitted_bytes", "omitted_events")}

    def _fail(self, request_id: str, locked: bool = False) -> None:
        with self._lock:
            state = self._requests[request_id]
            state["failed"] = True
            state["state"] = "기록 실패 (잠김)" if locked else "기록 실패"
            self._dirty_locked(request_id)

    def _dirty_locked(self, request_id: str) -> None:
        self._pending_states.add(request_id)
        if not self._wake_pending and not self._closed:
            try:
                self._queue.put_nowait(("", "$status", None))
            except queue.Full:
                # intentional: wake-up marker dropped because queue is full; pending states will be drained
                pass
            else:
                self._wake_pending = True

    def fail(self, request_id: str) -> None:
        """Mark a request as missing audit data without recording exception text."""
        self._fail(request_id)

    def _enqueue(self, request_id: str, kind: str, payload: Any) -> bool:
        with self._lock:
            return self._enqueue_locked(request_id, kind, payload)

    def _enqueue_locked(self, request_id: str, kind: str, payload: Any) -> bool:
        if self._closed:
            return False
        try:
            self._queue.put_nowait((request_id, kind, payload))
        except queue.Full:
            state = self._requests[request_id]
            state["failed"] = True
            state["state"] = "기록 실패"
            self._dirty_locked(request_id)
            return False
        return True

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    self._flush_states()
                    return
                request_id, kind, payload = item
                if kind == "$status":
                    with self._lock:
                        self._wake_pending = False
                    self._flush_states()
                    self._release_finished_if_drained()
                    continue
                if kind == "finished":
                    with self._lock:
                        payload["failed"] = self._requests[request_id]["failed"]
                try:
                    self.store.append(request_id, kind, payload)
                except Exception as exc:
                    self._fail(request_id, isinstance(exc, LockedError))
                else:
                    if kind == "finished":
                        with self._lock:
                            state = self._requests[request_id]
                            if not state["failed"]:
                                state["state"] = ("전송 여부 불확실" if state["uncertain"]
                                                  else "부분" if state["partial"] else "완료")
                            self._pending_states.add(request_id)
                self._flush_states()
                if kind == "finished":
                    release = getattr(self.store, "release", None)
                    if callable(release):
                        release(request_id)
                    with self._lock:
                        self._release_pending.discard(request_id)
                    self._retire(request_id)
                self._release_finished_if_drained()
            finally:
                self._queue.task_done()

    def _release_finished_if_drained(self) -> None:
        release = getattr(self.store, "release", None)
        if not callable(release):
            return
        with self._lock:
            if not self._queue.empty():
                return
            finished = list(self._release_pending)
            self._release_pending.clear()
        for request_id in finished:
            release(request_id)
            self._retire(request_id)

    def _retire(self, request_id: str) -> None:
        with self._lock:
            state = self._requests.get(request_id)
            if state is None or state.get("retired"):
                return
            state["retired"] = True
            self._completed.append(request_id)
            while len(self._completed) > 1000:
                old = self._completed.popleft()
                self._pending_states.discard(old)
                self._requests.pop(old, None)

    def _flush_states(self) -> None:
        mark = getattr(self.store, "mark_status", None)
        if not callable(mark):
            return
        with self._lock:
            pending = [(request_id, self._requests[request_id]["state"],
                        self._requests[request_id]["omitted_bytes"], self._requests[request_id]["omitted_events"])
                       for request_id in self._pending_states]
        for request_id, state, byte_count, event_count in pending:
            with self._lock:
                report_failure = self._requests[request_id]["failed"] and not self._requests[request_id]["failure_reported"]
                if report_failure:
                    self._requests[request_id]["failure_reported"] = True
            if report_failure:
                try:
                    _logger.warning("content_audit_write_failure")
                except Exception:
                    # intentional: logging must never raise into caller or recurse
                    pass
            try:
                mark(request_id, state, byte_count, event_count)
            except Exception:
                try:
                    _logger.warning("content_audit_write_failure")
                except Exception:
                    # intentional: logging must never raise into caller or recurse
                    pass
                continue
            with self._lock:
                current = self._requests[request_id]
                if (current["state"], current["omitted_bytes"], current["omitted_events"]) == (state, byte_count, event_count):
                    self._pending_states.discard(request_id)

    def drain(self) -> None:
        """Wait for previously queued writes; never call from the request path."""
        self._queue.join()

    def close(self) -> None:
        """Stop after draining queued events; never call from the request path."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._queue.put(None)
        self._worker.join()
        release = getattr(self.store, "release", None)
        if callable(release):
            for request_id in self._requests:
                release(request_id)
