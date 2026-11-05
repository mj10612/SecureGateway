"""Bounded audit completion recovery using real SQLite write locks."""
from contextlib import closing, contextmanager
import json
import sqlite3
import time

import pytest

from secure_gateway.audit_retry import CompletionRetries
from secure_gateway.gateway_audit import AuditStore


def begin(store):
    return store.begin("fixture", "claude", "subscription", "/claude/v1/messages", "local")


def metadata():
    return dict(agent="fixture", status=200, outcome="completed", model="fixture-model",
                upstream_attempted=1, input_bytes=2, masked_bytes=2,
                output_bytes=2, new_aliases=0, duration_ms=1)


def wait_idle(store):
    deadline = time.monotonic() + 5
    while store.completion_retries.diagnostics()["pending"]:
        assert time.monotonic() < deadline, store.completion_retries.diagnostics()
        time.sleep(.01)


@contextmanager
def locked(store, monkeypatch):
    connect = store.connect
    @contextmanager
    def short_connect(**kwargs):
        with connect(**kwargs) as db:
            db.execute("PRAGMA busy_timeout=25")
            yield db
    with closing(sqlite3.connect(store.path, timeout=0)) as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        try:
            with monkeypatch.context() as patch:
                patch.setattr(store, "connect", short_connect)
                yield
        finally:
            blocker.rollback()


def row(store, request_id):
    with store.connect() as db:
        value = db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
        return dict(value) if value is not None else None


def test_real_lock_recovers_snapshot_without_extra_payloads(tmp_path, monkeypatch):
    store = AuditStore(tmp_path / "audit.sqlite")
    try:
        request_id = begin(store)
        completion = metadata()
        completion["prompt"] = "never-queue-this-prompt"
        with locked(store, monkeypatch):
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                store.finish(request_id, completion)
            stats = store.completion_retries.diagnostics()
            assert stats["pending"] == 1 and stats["pending_bytes"] > 0
            pending = store.completion_retries._pending[request_id]
            assert "prompt" not in pending.metadata
            completion["model"] = "changed-after-enqueue"
        wait_idle(store)
        saved = row(store, request_id)
        assert saved["status"] == 200 and saved["model"] == "fixture-model"
        stats = store.completion_retries.diagnostics()
        assert stats["recovered"] == 1 and stats["dropped"] == 0 and stats["pending_bytes"] == 0
        assert "never-queue-this-prompt" not in json.dumps(stats)
    finally:
        store.close()


@pytest.mark.parametrize("change", ["delete", "complete"])
def test_shutdown_flush_does_not_resurrect_or_overwrite_completed_rows(tmp_path, monkeypatch, change):
    monkeypatch.setattr(CompletionRetries, "DELAYS", (30.0,))
    store = AuditStore(tmp_path / "audit.sqlite")
    try:
        request_id = begin(store)
        with locked(store, monkeypatch), pytest.raises(sqlite3.OperationalError):
            store.finish(request_id, metadata())
        if change == "delete":
            with store.connect() as db:
                db.execute("DELETE FROM requests WHERE request_id=?", (request_id,))
        else:
            completion = metadata()
            completion.update(status=500, outcome="blocked")
            store.finish(request_id, completion)
        store.close()
        saved = row(store, request_id)
        assert saved is None if change == "delete" else saved["status"] == 500
        assert store.completion_retries.diagnostics()["pending"] == 0
        assert store.completion_retries.diagnostics()["skipped"] == 1
    finally:
        store.close()


def test_shutdown_flush_retention_keeps_live_requests(tmp_path, monkeypatch):
    monkeypatch.setattr(CompletionRetries, "DELAYS", (30.0,))
    store = AuditStore(tmp_path / "audit.sqlite", max_records=1)
    try:
        old = begin(store)
        with locked(store, monkeypatch), pytest.raises(sqlite3.OperationalError):
            store.finish(old, metadata())
        recent = begin(store)
        store.finish(recent, metadata())
        active = begin(store)
        store.close()
        assert row(store, old) is None
        assert row(store, recent)["status"] == 200
        assert row(store, active)["status"] is None
        assert store.completion_retries.diagnostics()["recovered"] == 1
    finally:
        store.close()


@pytest.mark.parametrize("budget", ["count", "bytes"])
def test_queue_limits_drop_without_retaining_extra_metadata(tmp_path, monkeypatch, budget):
    monkeypatch.setattr(CompletionRetries, "DELAYS", (30.0,))
    if budget == "count":
        monkeypatch.setattr(CompletionRetries, "MAX_PENDING", 1)
    else:
        monkeypatch.setattr(CompletionRetries, "MAX_BYTES", 1)
    store = AuditStore(tmp_path / "audit.sqlite")
    try:
        ids = [begin(store), begin(store)]
        with locked(store, monkeypatch):
            for request_id in ids:
                with pytest.raises(sqlite3.OperationalError):
                    store.finish(request_id, metadata())
        stats = store.completion_retries.diagnostics()
        assert stats["pending"] == (1 if budget == "count" else 0)
        assert stats["dropped"] == (1 if budget == "count" else 2)
        assert stats["pending_bytes"] <= stats["max_bytes"]
    finally:
        store.close()


def test_permanent_lock_exhausts_retries_and_releases_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(CompletionRetries, "DELAYS", (.01, .02, .03))
    store = AuditStore(tmp_path / "audit.sqlite")
    try:
        request_id = begin(store)
        with locked(store, monkeypatch):
            with pytest.raises(sqlite3.OperationalError):
                store.finish(request_id, metadata())
            wait_idle(store)
        stats = store.completion_retries.diagnostics()
        assert stats["attempts"] == stats["max_attempts"] == 3
        assert stats["retry_errors"] == 3 and stats["dropped"] == 1
        assert stats["pending_bytes"] == 0 and row(store, request_id)["status"] is None
    finally:
        store.close()


def test_close_under_lock_is_bounded_and_accounts_for_abandoned_work(tmp_path, monkeypatch):
    monkeypatch.setattr(CompletionRetries, "SHUTDOWN_GRACE", .1)
    store = AuditStore(tmp_path / "audit.sqlite")
    request_id = begin(store)
    try:
        with locked(store, monkeypatch):
            with pytest.raises(sqlite3.OperationalError):
                store.finish(request_id, metadata())
            start = time.monotonic()
            store.close()
            assert time.monotonic() - start < 2
        stats = store.completion_retries.diagnostics()
        assert stats["pending"] == 0 and stats["dropped"] == 1
        assert store._owner_file is None
        with pytest.raises(ValueError, match="closed"):
            store.finish(request_id, metadata())
    finally:
        store.close()


def test_duplicate_queue_entry_uses_first_snapshot_and_worker_can_restart(monkeypatch):
    from threading import Event
    entered, release = Event(), Event()
    class Writer:
        def __init__(self):
            self.saved = []
        def write(self, request_id, completion):
            entered.set()
            assert release.wait(3)
            self.saved.append((request_id, completion))
            return True
    monkeypatch.setattr(CompletionRetries, "DELAYS", (.001,))
    writer = Writer()
    queue = CompletionRetries(writer.write)
    try:
        assert queue.enqueue("first", {"model": "original"})
        assert entered.wait(3)
        before = queue.diagnostics()["pending_bytes"]
        assert queue.enqueue("first", {"model": "different"})
        assert queue.diagnostics()["pending"] == 1
        assert queue.diagnostics()["pending_bytes"] == before
        release.set()
        for index in range(10):
            deadline = time.monotonic() + 3
            while queue.diagnostics()["pending"]:
                assert time.monotonic() < deadline
                time.sleep(.001)
            assert queue.enqueue(str(index), {"model": "next"})
        queue.close()
        assert len(writer.saved) == 11
        assert writer.saved[0] == ("first", {"model": "original"})
    finally:
        release.set()
        queue.close()


def test_queue_does_not_retain_callback_owner(monkeypatch):
    import gc
    import weakref
    class Writer:
        def write(self, request_id, completion):
            return True
    monkeypatch.setattr(CompletionRetries, "DELAYS", (30.0,))
    writer = Writer()
    reference = weakref.ref(writer)
    queue = CompletionRetries(writer.write)
    assert queue.enqueue("id", {"model": "fixture"})
    del writer
    gc.collect()
    assert reference() is None
    queue.close()
    assert queue.diagnostics()["dropped"] == 1
    assert queue.diagnostics()["pending"] == 0


def test_worker_start_failure_releases_queue_budget(monkeypatch):
    from secure_gateway import audit_retry
    class Writer:
        def write(self, request_id, completion):
            return True
    def unavailable(*args):
        raise RuntimeError("thread unavailable")
    writer = Writer()
    queue = CompletionRetries(writer.write)
    monkeypatch.setattr(audit_retry.Thread, "start", unavailable)
    assert not queue.enqueue("id", {"model": "fixture"})
    assert queue.diagnostics()["pending_bytes"] == 0
    assert queue.diagnostics()["pending"] == 0
    assert queue.diagnostics()["dropped"] == 1
    queue.close()


def test_interrupted_maintenance_cannot_rollback_recovered_completion(tmp_path, monkeypatch):
    monkeypatch.setattr(CompletionRetries, "DELAYS", (30.0,))
    store = AuditStore(tmp_path / "audit.sqlite")
    try:
        request_id = begin(store)
        with locked(store, monkeypatch), pytest.raises(sqlite3.OperationalError):
            store.finish(request_id, metadata())
        def interrupted(db, apply):
            db.set_progress_handler(lambda: 1, 1)
            db.execute("SELECT COUNT(*) FROM requests")
        monkeypatch.setattr(store, "_retention_in_transaction", interrupted)
        store.close()
        assert row(store, request_id)["status"] == 200
        stats = store.completion_retries.diagnostics()
        assert stats["recovered"] == 1 and stats["retry_errors"] == 0
        assert stats["maintenance_errors"] == 1
    finally:
        store.close()


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), {"nested": "payload"}])
def test_invalid_queue_metadata_is_not_retained(invalid):
    class Writer:
        def write(self, request_id, completion):
            return True
    writer = Writer()
    queue = CompletionRetries(writer.write)
    try:
        assert not queue.enqueue("id", {"value": invalid})
        stats = queue.diagnostics()
        assert stats["pending"] == stats["pending_bytes"] == 0
        assert stats["dropped"] == 1
    finally:
        queue.close()


def test_retry_cannot_finish_another_live_owner_request(tmp_path):
    path = tmp_path / "audit.sqlite"
    first = AuditStore(path)
    second = AuditStore(path)
    try:
        active = begin(second)
        assert first._retry_completion(active, metadata()) is False
        assert row(second, active)["status"] is None
        assert second.recover_incomplete(apply=True)["candidates"] == 0
    finally:
        first.close()
        second.close()
