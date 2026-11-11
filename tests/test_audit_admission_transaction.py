"""Audit admission keeps retention exact within one write transaction."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from secure_gateway.gateway_audit import AuditStore


def begin(store):
    return store.begin("agent", "provider", "subscription", "/test", "local")


def test_admission_uses_one_write_transaction(tmp_path, monkeypatch):
    store = AuditStore(tmp_path / "audit.sqlite")
    original_connect = store.connect
    statements = []

    @contextmanager
    def traced_connect(*args, **kwargs):
        with original_connect(*args, **kwargs) as db:
            db.set_trace_callback(statements.append)
            yield db

    try:
        monkeypatch.setattr(store, "connect", traced_connect)
        request_id = begin(store)
        assert request_id
        assert sum(statement.lstrip().upper().startswith("BEGIN") for statement in statements) == 1
    finally:
        store.close()


def test_admission_applies_count_and_age_retention_after_external_write(tmp_path):
    store = AuditStore(tmp_path / "audit.sqlite", max_records=1, max_age_days=1)
    recent = datetime.now(timezone.utc).isoformat()
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    try:
        with store.connect() as db:
            db.executemany(
                "INSERT INTO requests(request_id,started_at,agent,provider,subscription,endpoint,destination,status) "
                "VALUES (?, ?, 'a', 'p', 's', 'e', 'd', 200)",
                [("old", old), ("recent-1", recent), ("recent-2", recent)],
            )
        first = begin(store)
        with store.connect() as db:
            assert {row[0] for row in db.execute("SELECT request_id FROM requests")} == {"recent-2", first}
            db.execute(
                "INSERT INTO requests(request_id,started_at,agent,provider,subscription,endpoint,destination,status) "
                "VALUES ('external-old', ?, 'a', 'p', 's', 'e', 'd', 200)", (old,),
            )
        second = begin(store)
        with store.connect() as db:
            assert {row[0] for row in db.execute("SELECT request_id FROM requests")} == {first, second}
    finally:
        store.close()


def test_admission_runs_maintenance_only_when_due(tmp_path, monkeypatch):
    store = AuditStore(tmp_path / "audit.sqlite", max_records=1)
    original = store.retention
    calls = []

    def observed(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    try:
        monkeypatch.setattr(store, "retention", observed)
        begin(store)
        assert calls == []
        with store.connect() as db:
            db.executemany(
                "INSERT INTO requests(request_id,started_at,agent,provider,subscription,endpoint,destination,status) "
                "VALUES (?, '2026-01-01T00:00:00+00:00', 'a', 'p', 's', 'e', 'd', 200)",
                [("completed-1",), ("completed-2",)],
            )
        begin(store)
        assert len(calls) == 1
        with store.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM requests WHERE status IS NOT NULL").fetchone()[0] == 1
    finally:
        store.close()


def test_admission_enforces_age_limit_below_count_limit(tmp_path):
    store = AuditStore(tmp_path / "audit.sqlite", max_records=100, max_age_days=1)
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    try:
        with store.connect() as db:
            db.execute(
                "INSERT INTO requests(request_id,started_at,agent,provider,subscription,endpoint,destination,status) "
                "VALUES ('expired', ?, 'a', 'p', 's', 'e', 'd', 200)", (old,),
            )
        request_id = begin(store)
        with store.connect() as db:
            assert [row[0] for row in db.execute("SELECT request_id FROM requests")] == [request_id]
    finally:
        store.close()
