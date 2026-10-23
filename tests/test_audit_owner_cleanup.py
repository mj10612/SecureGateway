"""Bounded SQLite retention settings and conservative orphan lock maintenance."""
from contextlib import closing
import json
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest

from secure_gateway.gateway_audit import AuditStore


@pytest.mark.parametrize("value", [2**63, 10**100, True, 0, -1, 1.5])
def test_record_limit_rejected_before_filesystem(tmp_path, value):
    path = tmp_path / "absent" / "audit.db"
    with pytest.raises(ValueError, match="max_records"):
        AuditStore(path, max_records=value)
    assert not path.parent.exists()


def test_largest_sqlite_record_limit_works(tmp_path):
    store = AuditStore(tmp_path / "audit.db", max_records=2**63 - 1)
    try:
        assert store.retention(apply=True)["removed"] == 0
        request = store.begin("a", "p", "s", "e", "d")
        with store.connect() as db:
            db.execute("UPDATE requests SET status=200 WHERE request_id=?", (request,))
        assert store.retention(apply=True)["removed"] == 0
    finally:
        store.close()


def snapshot(root):
    return {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def test_crashed_owners_dry_run_apply_and_repeat(tmp_path):
    path = tmp_path / "audit.db"
    script = ("from secure_gateway.gateway_audit import AuditStore; "
              "from pathlib import Path; import os,sys; "
              "s=AuditStore(Path(sys.argv[1])); os._exit(0)")
    for _ in range(3):
        subprocess.run([sys.executable, "-c", script, str(path)], check=True, timeout=30)
    owners = path.with_name(path.name + ".owners")
    assert len(list(owners.iterdir())) == 3
    before = snapshot(tmp_path)
    reader = AuditStore(path, read_only=True)
    assert reader.cleanup_owners() == {"candidates": 3, "removed": 0, "dry_run": True}
    assert snapshot(tmp_path) == before
    with pytest.raises(ValueError, match="read-only"):
        reader.cleanup_owners(apply=True)
    writer = AuditStore(path)
    try:
        assert writer.cleanup_owners(apply=True) == {"candidates": 3, "removed": 3, "dry_run": False}
        assert writer.cleanup_owners(apply=True)["removed"] == 0
        assert list(owners.iterdir()) == [writer._owner_path]
    finally:
        writer.close()


def test_live_referenced_invalid_empty_and_uncertain_files_protected(tmp_path, monkeypatch):
    path = tmp_path / "audit.db"
    writer = AuditStore(path)
    observer = AuditStore(path)
    owners = writer._owner_path.parent
    referenced = owners / uuid4().hex
    referenced.write_bytes(b"1")
    invalid = owners / "not-a-uuid"
    invalid.write_bytes(b"1")
    empty = owners / uuid4().hex
    empty.touch()
    request = writer.begin("a", "p", "s", "e", "d")
    with writer.connect() as db:
        db.execute("UPDATE requests SET owner=?, status=200 WHERE request_id=?", (referenced.name, request))
    try:
        assert observer.cleanup_owners(apply=True)["removed"] == 0
        assert referenced.exists() and invalid.exists() and empty.exists()
        uncertain = owners / uuid4().hex
        uncertain.write_bytes(b"1")
        monkeypatch.setattr(observer, "_lock", lambda handle: (_ for _ in ()).throw(PermissionError()))
        assert observer.cleanup_owners(apply=True)["removed"] == 0
        assert uncertain.exists()
    finally:
        writer.close()
        observer.close()


def test_legacy_requests_protect_unreferenced_files(tmp_path):
    store = AuditStore(tmp_path / "audit.db")
    stale = store._owner_path.parent / uuid4().hex
    stale.write_bytes(b"1")
    request = store.begin("a", "p", "s", "e", "d")
    try:
        with store.connect() as db:
            db.execute("UPDATE requests SET owner=NULL WHERE request_id=?", (request,))
        assert store.cleanup_owners(apply=True)["removed"] == 0
        assert stale.exists()
    finally:
        store.close()


def test_legacy_schema_and_missing_database_are_noop(tmp_path):
    path = tmp_path / "missing" / "audit.db"
    assert AuditStore(path, read_only=True).cleanup_owners()["candidates"] == 0
    assert not path.parent.exists()
    path.parent.mkdir()
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE requests(id INTEGER)")
    owners = path.with_name(path.name + ".owners")
    owners.mkdir()
    stale = owners / uuid4().hex
    stale.write_bytes(b"1")
    before = snapshot(tmp_path)
    assert AuditStore(path, read_only=True).cleanup_owners()["candidates"] == 0
    assert before == snapshot(tmp_path)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows symlinks require special privileges")
def test_symlink_owner_is_never_followed(tmp_path):
    store = AuditStore(tmp_path / "audit.db")
    target = tmp_path / "target"
    target.write_bytes(b"1")
    link = store._owner_path.parent / uuid4().hex
    link.symlink_to(target)
    try:
        assert store.cleanup_owners(apply=True)["removed"] == 0
        assert link.is_symlink() and target.read_bytes() == b"1"
    finally:
        store.close()


def test_cli_owner_cleanup_missing_state_is_nonmutating(tmp_path):
    from click.testing import CliRunner
    from secure_gateway.cli import main
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"port": 38117, "token": "t" * 32}), encoding="utf-8")
    before = snapshot(tmp_path)
    result = CliRunner().invoke(main, ["gateway", "audit-gc", "--config", str(config), "--cleanup-owners"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["owners"] == {"candidates": 0, "removed": 0, "dry_run": True}
    assert snapshot(tmp_path) == before


def test_owner_creation_holds_database_write_transaction(tmp_path, monkeypatch):
    """Cleanup cannot acquire its write transaction before creation locks owner."""
    path = tmp_path / "audit.db"
    initial = AuditStore(path)
    initial.close()
    original = AuditStore._lock
    checked = []

    def check_lock(handle):
        with closing(sqlite3.connect(path, timeout=0)) as db:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                db.execute("BEGIN IMMEDIATE")
        checked.append(True)
        original(handle)

    monkeypatch.setattr(AuditStore, "_lock", staticmethod(check_lock))
    store = AuditStore(path)
    try:
        assert checked == [True]
    finally:
        store.close()


def test_cleanup_waits_for_starting_process_to_lock_owner(tmp_path):
    path = tmp_path / "audit.db"
    initial = AuditStore(path)
    initial.close()
    writer_script = """
import sys
from pathlib import Path
from secure_gateway.gateway_audit import AuditStore
original = AuditStore._lock
def pause(handle):
    print('creating', flush=True)
    sys.stdin.readline()
    original(handle)
AuditStore._lock = staticmethod(pause)
store = AuditStore(Path(sys.argv[1]))
print('locked', flush=True)
sys.stdin.readline()
store.close()
"""
    cleanup_script = """
import sys,json
from pathlib import Path
from secure_gateway.gateway_audit import AuditStore
store = AuditStore(Path(sys.argv[1]), read_only=True)
# Exercise the write-maintenance operation without another owner creation.
store.read_only = False
print('cleaning', flush=True)
print(json.dumps(store.cleanup_owners(apply=True)), flush=True)
"""
    writer = subprocess.Popen([sys.executable, "-c", writer_script, str(path)],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True)
    cleaner = None
    try:
        assert writer.stdout.readline().strip() == "creating"
        # The not-yet-locked owner's empty file must be invisible to dry-run:
        # obtaining its lock here would make the starting writer fail.
        reader = AuditStore(path, read_only=True)
        assert reader.cleanup_owners()["candidates"] == 0
        cleaner = subprocess.Popen([sys.executable, "-c", cleanup_script, str(path)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert cleaner.stdout.readline().strip() == "cleaning"
        with pytest.raises(subprocess.TimeoutExpired):
            cleaner.communicate(timeout=0.25)
        writer.stdin.write("continue\n")
        writer.stdin.flush()
        assert writer.stdout.readline().strip() == "locked"
        output, errors = cleaner.communicate(timeout=10)
        assert cleaner.returncode == 0, errors
        assert json.loads(output)["removed"] == 0
        writer.stdin.write("close\n")
        writer.stdin.flush()
        writer.communicate(timeout=10)
        assert writer.returncode == 0
    finally:
        for process in (writer, cleaner):
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=10)


def test_cli_apply_removes_stale_owner_and_repeat_is_noop(tmp_path):
    from click.testing import CliRunner
    from secure_gateway.cli import main
    from secure_gateway.gateway_install import runtime_directory
    config = tmp_path / "custom.json"
    config.write_text(json.dumps({"port": 38117, "token": "t" * 32}), encoding="utf-8")
    path = runtime_directory(config.resolve()) / "logs.sqlite3"
    initial = AuditStore(path)
    stale = initial._owner_path.parent / uuid4().hex
    stale.write_bytes(b"1")
    initial.close()
    args = ["gateway", "audit-gc", "--config", str(config), "--cleanup-owners"]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["owners"]["candidates"] == 1
    assert stale.exists()
    result = CliRunner().invoke(main, [*args, "--apply"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["owners"]["removed"] == 1
    assert not stale.exists()
    result = CliRunner().invoke(main, [*args, "--apply"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["owners"]["removed"] == 0
