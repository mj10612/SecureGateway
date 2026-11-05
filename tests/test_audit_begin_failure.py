"""A failed audit admission must never publish an unreachable request row."""
from contextlib import contextmanager, closing
import sqlite3

import pytest

from secure_gateway.gateway_audit import AuditStore


def begin(store):
    return store.begin("fixture", "claude", "subscription", "/claude/v1/messages", "local")


def test_real_lock_between_maintenance_and_insert_leaves_no_orphan_and_retry_is_unique(tmp_path, monkeypatch):
    store = AuditStore(tmp_path / "audit.sqlite", max_records=1)
    connect = store.connect
    armed = True
    with closing(sqlite3.connect(store.path, timeout=0)) as blocker:
        @contextmanager
        def controlled_connect():
            nonlocal armed
            with connect() as db:
                db.execute("PRAGMA busy_timeout=25")
                yield db
            if armed:
                armed = False
                blocker.execute("BEGIN IMMEDIATE")

        try:
            with monkeypatch.context() as patch:
                patch.setattr(store, "connect", controlled_connect)
                with pytest.raises(sqlite3.OperationalError, match="locked"):
                    begin(store)
            blocker.rollback()
            with store.connect() as db:
                assert db.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 0
            assert store.recover_incomplete(apply=True)["candidates"] == 0
            request_id = begin(store)
            with store.connect() as db:
                rows = db.execute("SELECT request_id, status FROM requests").fetchall()
            assert [(row["request_id"], row["status"]) for row in rows] == [(request_id, None)]
            assert store.recover_incomplete(apply=True)["candidates"] == 0
        finally:
            blocker.rollback()
            store.close()


def test_failed_retention_prevents_request_publication(tmp_path, monkeypatch):
    store = AuditStore(tmp_path / "audit.sqlite")
    try:
        def fail(*args, **kwargs):
            raise sqlite3.OperationalError("maintenance failed")
        monkeypatch.setattr(store, "retention", fail)
        with pytest.raises(sqlite3.OperationalError, match="maintenance failed"):
            begin(store)
        with store.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 0
    finally:
        store.close()
