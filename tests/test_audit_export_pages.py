"""Bounded audit export continuation and dashboard request ownership."""
from contextlib import closing
import shutil
import subprocess
from pathlib import Path

import pytest

from secure_gateway.gateway_audit import AuditStore


FILTERS = {"since": "2026-01-01T00:00:00Z", "until": "2026-01-02T00:00:00Z", "provider": "codex"}


def add_rows(store, count, prefix="initial"):
    with store.connect() as db:
        db.executemany(
            "INSERT INTO requests(request_id,started_at,agent,provider,subscription,endpoint,destination,status) "
            "VALUES (?, '2026-01-01T12:00:00+00:00', 'Codex', 'codex', 'chatgpt_subscription', '/codex/responses', 'private', 200)",
            ((f"{prefix}-{n}",) for n in range(count)),
        )


def test_same_timestamp_pages_exclude_later_inserts(tmp_path):
    with closing(AuditStore(tmp_path / "audit.db")) as store:
        add_rows(store, 2001)
        first = store.export_metadata(FILTERS)
        assert first["count"] == 1000 and first["truncated"]
        assert first["next_cursor"]
        add_rows(store, 7, "later")
        pages = [first]
        while pages[-1]["next_cursor"]:
            pages.append(store.export_metadata(FILTERS, cursor=pages[-1]["next_cursor"]))
        ids = [row["request_id"] for page in pages for row in page["rows"]]
        assert ids == [f"initial-{n}" for n in reversed(range(2001))]
        assert [page["count"] for page in pages] == [1000, 1000, 1]
        assert len(ids) == len(set(ids))
        assert not pages[-1]["truncated"]
        assert all("destination" not in row and "id" not in row for page in pages for row in page["rows"])
        # A cursor is repeatable and does not mutate the database.
        assert store.export_metadata(FILTERS, cursor=first["next_cursor"]) == pages[1]


@pytest.mark.parametrize("cursor", ["", "invalid", "%%%", "a" * 1025, [], {}])
def test_malformed_cursor_rejected(tmp_path, cursor):
    with closing(AuditStore(tmp_path / "audit.db")) as store:
        with pytest.raises(ValueError, match="cursor"):
            store.export_metadata(FILTERS, cursor=cursor)


def test_cursor_binds_filters_limit_store_and_signature(tmp_path):
    with closing(AuditStore(tmp_path / "audit.db")) as store:
        add_rows(store, 4)
        cursor = store.export_metadata(FILTERS, 2)["next_cursor"]
        with pytest.raises(ValueError, match="cursor"):
            store.export_metadata({**FILTERS, "provider": "claude"}, 2, cursor=cursor)
        with pytest.raises(ValueError, match="cursor"):
            store.export_metadata(FILTERS, 3, cursor=cursor)
        altered = ("A" if cursor[0] != "A" else "B") + cursor[1:]
        with pytest.raises(ValueError, match="cursor"):
            store.export_metadata(FILTERS, 2, cursor=altered)
        with closing(AuditStore(store.path, read_only=True)) as other:
            with pytest.raises(ValueError, match="cursor"):
                other.export_metadata(FILTERS, 2, cursor=cursor)


def test_deleted_rows_do_not_duplicate_and_deleted_watermark_requires_restart(tmp_path):
    with closing(AuditStore(tmp_path / "audit.db")) as store:
        add_rows(store, 6)
        first = store.export_metadata(FILTERS, 2)
        with store.connect() as db:
            db.execute("DELETE FROM requests WHERE request_id='initial-2'")
        second = store.export_metadata(FILTERS, 2, cursor=first["next_cursor"])
        third = store.export_metadata(FILTERS, 2, cursor=second["next_cursor"])
        ids = [row["request_id"] for p in (first, second, third) for row in p["rows"]]
        assert ids == ["initial-5", "initial-4", "initial-3", "initial-1", "initial-0"]
        with store.connect() as db:
            db.execute("DELETE FROM requests WHERE request_id='initial-5'")
        with pytest.raises(ValueError, match="watermark"):
            store.export_metadata(FILTERS, 2, cursor=first["next_cursor"])


def test_export_accepts_highest_sqlite_id(tmp_path):
    with closing(AuditStore(tmp_path / "audit.db")) as store:
        add_rows(store, 1)
        with store.connect() as db:
            db.execute("UPDATE requests SET id=?", (2**63 - 1,))
        assert store.export_metadata(FILTERS)["rows"][0]["request_id"] == "initial-0"


def test_dashboard_export_lifecycle_and_pages():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to exercise the actual dashboard JavaScript")
    checked = subprocess.run([node, str(Path(__file__).with_name("test_admin_export.js"))],
                             capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert checked.returncode == 0, checked.stdout + checked.stderr
