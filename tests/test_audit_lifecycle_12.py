"""Audit dry-run, bounded configuration and durable owner recovery regressions."""
from contextlib import closing
import sqlite3
import subprocess
import sys

import pytest

from secure_gateway.gateway_audit import AuditStore


def begin(store):
    return store.begin("agent", "provider", "subscription", "/test", "local")


def test_read_only_missing_database_has_no_side_effects(tmp_path):
    path = tmp_path / "missing" / "logs.sqlite3"
    store = AuditStore(path, read_only=True)
    assert store.retention()["candidates"] == 0
    assert store.recover_incomplete()["candidates"] == 0
    assert not path.parent.exists()
    with pytest.raises(ValueError):
        begin(store)
    with pytest.raises(ValueError):
        store.retention(apply=True)


def test_read_only_existing_database_does_not_mutate_files(tmp_path):
    path = tmp_path / "audit.sqlite3"
    store = AuditStore(path)
    begin(store)
    store.close()
    before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
              for p in tmp_path.rglob("*") if p.is_file()}
    reader = AuditStore(path, read_only=True)
    reader.retention()
    reader.recover_incomplete()
    after = {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
             for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


def test_legacy_wal_dry_run_fails_without_mutating_then_writable_open_migrates(tmp_path):
    path = tmp_path / "audit.sqlite3"
    store = AuditStore(path)
    store.close()
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("PRAGMA journal_mode=WAL")
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="legacy WAL"):
        AuditStore(path, read_only=True)
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    migrated = AuditStore(path)
    reader = AuditStore(path, read_only=True)
    assert reader.retention()["candidates"] == 0
    migrated.close()


@pytest.mark.parametrize("days", [10**100, 1_000_000_000, True, 0, -1])
def test_retention_rejects_unrepresentable_age_before_creating_files(tmp_path, days):
    path = tmp_path / "missing" / "logs.sqlite3"
    with pytest.raises(ValueError):
        AuditStore(path, max_age_days=days)
    assert not path.parent.exists()


def test_live_owner_protected_closed_owner_recovered_and_retained(tmp_path):
    path = tmp_path / "audit.sqlite3"
    owner = AuditStore(path)
    request_id = begin(owner)
    observer = AuditStore(path, max_records=1)
    assert observer.recover_incomplete(apply=True)["recovered"] == 0
    owner.close()
    reader = AuditStore(path, read_only=True)
    assert reader.recover_incomplete() == {"candidates": 1, "recovered": 0, "dry_run": True}
    assert reader.query({"result": "incomplete"})["summary"]["total"] == 1
    assert observer.recover_incomplete(apply=True)["recovered"] == 1
    assert observer.recover_incomplete(apply=True)["recovered"] == 0
    rows = observer.query({"result": "interrupted"})["rows"]
    assert rows[0]["request_id"] == request_id
    assert rows[0]["status"] is None
    assert observer.query({"result": "incomplete"})["rows"] == []
    begin(observer)
    observer.close()
    writer = AuditStore(path, max_records=1)
    assert writer.recover_incomplete(apply=True)["recovered"] == 1
    assert writer.retention(apply=True)["removed"] == 1
    writer.close()


def test_real_process_owner_is_protected_until_abnormal_exit(tmp_path):
    path = tmp_path / "audit.sqlite3"
    script = ("from pathlib import Path; import sys; "
              "from secure_gateway.gateway_audit import AuditStore; "
              "s=AuditStore(Path(sys.argv[1])); "
              "s.begin('a','p','s','e','d'); print('ready', flush=True); "
              "sys.stdin.read()")
    process = subprocess.Popen([sys.executable, "-c", script, str(path)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    try:
        assert process.stdout.readline().strip() == "ready"
        observer = AuditStore(path)
        assert observer.recover_incomplete(apply=True)["recovered"] == 0
        process.kill()
        process.communicate(timeout=10)
        assert observer.recover_incomplete(apply=True)["recovered"] == 1
        observer.close()
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)


def test_version_one_migration_preserves_legacy_metadata(tmp_path):
    path = tmp_path / "audit.sqlite3"
    store = AuditStore(path)
    request_id = begin(store)
    store.close()
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("ALTER TABLE requests DROP COLUMN owner")
        db.execute("PRAGMA user_version=1")
    migrated = AuditStore(path)
    assert migrated.recover_incomplete(apply=True)["recovered"] == 0
    assert migrated.recover_incomplete(apply=True, include_legacy=True)["recovered"] == 1
    assert migrated.query({"result": "interrupted"})["rows"][0]["request_id"] == request_id
    with migrated.connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
    migrated.close()
