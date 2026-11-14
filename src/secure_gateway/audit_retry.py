"""Bounded, memory-only retries of completion metadata; never inference calls."""

from dataclasses import dataclass
import json
import sqlite3
from threading import Condition, Thread, current_thread
import time
from weakref import WeakMethod


@dataclass
class PendingCompletion:
    """A queued completion-metadata retry entry with size, due time, and attempts."""

    metadata: dict
    size: int
    due: float
    attempts: int = 0


class CompletionRetries:
    """Bounded in-memory retry worker for audit completion writes."""
    MAX_PENDING = 256
    MAX_BYTES = 1024 * 1024
    DELAYS = (0.25, 0.5, 1.0, 2.0, 4.0)
    SHUTDOWN_GRACE = 1.0

    def __init__(self, write):
        self._write = WeakMethod(write)
        self._condition = Condition()
        self._pending: dict[str, PendingCompletion] = {}
        self._bytes = 0
        self._thread: Thread | None = None
        self._closing = False
        self._deadline = 0.0
        self._attempts = self._recovered = self._skipped = self._errors = self._dropped = 0
        self._maintenance_errors = 0

    def enqueue(self, request_id, metadata):
        """Handle enqueue."""
        # JSON round-trip gives the worker an independent, scalar-only snapshot.
        try:
            if any(value is not None and type(value) not in (str, int, float)
                   for value in metadata.values()):
                raise ValueError()
            data = json.dumps(metadata, allow_nan=False, ensure_ascii=False).encode("utf-8")
            size = len(data) + len(request_id.encode("utf-8")) + 512
        except (ValueError, TypeError, UnicodeError):
            with self._condition:
                self._dropped += 1
            return False
        with self._condition:
            if request_id in self._pending:
                return True  # One final snapshot per request; do not replace in-flight work.
            if self._closing or len(self._pending) >= self.MAX_PENDING or self._bytes + size > self.MAX_BYTES:
                self._dropped += 1
                return False
            self._pending[request_id] = PendingCompletion(json.loads(data), size, time.monotonic() + self.DELAYS[0])
            self._bytes += size
            if self._thread is None or not self._thread.is_alive():
                self._thread = Thread(target=self._run, name="audit-completion-retry", daemon=True)
                try:
                    self._thread.start()
                except RuntimeError:
                    self._thread = None
                    self._remove(request_id)
                    self._dropped += 1
                    return False
            self._condition.notify_all()
            return True

    def diagnostics(self):
        """Handle diagnostics."""
        with self._condition:
            return {"pending": len(self._pending), "pending_bytes": self._bytes,
                    "attempts": self._attempts, "recovered": self._recovered,
                    "skipped": self._skipped,
                    "retry_errors": self._errors, "dropped": self._dropped,
                    "maintenance_errors": self._maintenance_errors,
                    "max_pending": self.MAX_PENDING, "max_bytes": self.MAX_BYTES,
                    "max_attempts": len(self.DELAYS), "closing": self._closing}

    def _remove(self, request_id):
        self._bytes -= self._pending.pop(request_id).size

    def wait_idle(self, timeout):
        """Wait until no completion is queued or in flight; return whether the queue drained."""
        deadline = time.monotonic() + timeout
        with self._condition:
            while self._pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True

    def maintenance_failed(self):
        """Handle maintenance failed."""
        with self._condition:
            self._maintenance_errors += 1

    def _run(self):
        while True:
            with self._condition:
                if not self._pending:
                    self._thread = None
                    return
                now = time.monotonic()
                if self._closing and now >= self._deadline:
                    self._dropped += len(self._pending)
                    self._pending.clear()
                    self._bytes = 0
                    self._thread = None
                    return
                request_id, item = min(self._pending.items(), key=lambda entry: entry[1].due)
                delay = 0 if self._closing else item.due - now
                if delay > 0:
                    self._condition.wait(delay)
                    continue
                item.attempts += 1
                self._attempts += 1
            success = False
            applied = False
            callback = self._write()
            try:
                if callback is not None:
                    applied = callback(request_id, item.metadata)
                    success = True
            except (sqlite3.Error, ValueError, TypeError, OverflowError, OSError):
                # intentional: retry only the ledger write, without recording private errors
                pass
            finally:
                del callback  # Do not retain the store while sleeping between attempts.
            with self._condition:
                if success:
                    self._recovered += int(applied)
                    self._skipped += int(not applied)
                    self._remove(request_id)
                else:
                    self._errors += 1
                    if item.attempts >= len(self.DELAYS) or self._write() is None:
                        self._dropped += 1
                        self._remove(request_id)
                    else:
                        item.due = time.monotonic() + self.DELAYS[item.attempts]
                self._condition.notify_all()

    def close(self):
        """Handle close."""
        with self._condition:
            if not self._closing:
                self._closing = True
                self._deadline = time.monotonic() + self.SHUTDOWN_GRACE
            worker = self._thread
            self._condition.notify_all()
        if worker is not None and worker is not current_thread():
            worker.join(self.SHUTDOWN_GRACE + 0.2)
