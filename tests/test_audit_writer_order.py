"""Audit writers of one store enter SQLite in arrival order (#352)."""
import sqlite3
from threading import Thread
import time

import pytest

from secure_gateway.gateway_audit import AuditStore


def begin(store, agent="agent"):
    return store.begin(agent, "provider", "subscription", "/test", "local")


def wait_for(condition, timeout=5):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline
        time.sleep(0.005)


def test_waiting_admissions_are_written_in_arrival_order(tmp_path):
    store = AuditStore(tmp_path / "audit.sqlite")
    threads = []
    try:
        assert store._writers.acquire(1)
        try:
            for index in range(4):
                issued = store._writers._issued
                thread = Thread(target=begin, args=(store, f"agent-{index}"))
                thread.start()
                threads.append(thread)
                # Each writer holds its ticket before the next one arrives.
                wait_for(lambda: store._writers._issued == issued + 1)
        finally:
            store._writers.release()
        for thread in threads:
            thread.join(5)
            assert not thread.is_alive()
        with store.connect() as db:
            agents = [row[0] for row in db.execute("SELECT agent FROM requests ORDER BY id")]
        assert agents == [f"agent-{index}" for index in range(4)]
    finally:
        store.close()


def test_expired_turn_is_skipped_and_completion_is_retried(tmp_path):
    store = AuditStore(tmp_path / "audit.sqlite")
    try:
        request_id = begin(store)
        assert store._writers.acquire(1)
        try:
            started = time.monotonic()
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                store.finish(request_id, {"agent": "agent", "status": 200, "outcome": "completed",
                                          "upstream_attempted": 1, "input_bytes": 2, "masked_bytes": 2,
                                          "output_bytes": 2, "new_aliases": 0, "duration_ms": 1})
            assert time.monotonic() - started < 1
            assert store.completion_retries.diagnostics()["pending"] == 1
        finally:
            store._writers.release()
        # The abandoned ticket must not block later writers.
        assert begin(store, "later")

        def completed():
            with store.connect() as db:
                return db.execute("SELECT status FROM requests WHERE request_id=?",
                                  (request_id,)).fetchone()[0] == 200
        wait_for(completed)
    finally:
        store.close()
