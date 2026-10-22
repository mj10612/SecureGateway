"""Durable request metadata. Prompts, replies and credentials never enter SQLite."""

from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import hmac
import os
from pathlib import Path
import sqlite3
from uuid import uuid4


class AuditStore:
    def __init__(self, path: Path, max_records=100_000, max_age_days=None, *, read_only=False):
        if type(max_records) is not int or max_records < 1:
            raise ValueError("Audit max_records must be a positive integer.")
        if max_age_days is not None and (type(max_age_days) is not int or max_age_days < 1):
            raise ValueError("Audit max_age_days must be a positive integer.")
        if max_age_days is not None:
            try:
                datetime.now(timezone.utc) - timedelta(days=max_age_days)
            except OverflowError as exc:
                raise ValueError("Audit max_age_days exceeds the supported date range.") from exc
        self.max_records = max_records
        self.max_age_days = max_age_days
        self.path = path
        self.read_only = read_only
        self.owner = uuid4().hex
        self._owner_file = None
        if read_only:
            if path.exists():
                with path.open("rb") as handle:
                    header = handle.read(20)
                if len(header) >= 20 and header[18:20] != b"\x01\x01":
                    raise ValueError("Read-only audit maintenance requires rollback journal mode; "
                                     "open the gateway normally once to migrate a legacy WAL database.")
            return
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not path.exists():
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass  # Another gateway created the same database concurrently.
            else:
                os.close(fd)
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in {0, 1, 2}:
                raise ValueError("Unsupported gateway audit database version.")
            db.execute("PRAGMA journal_mode=DELETE")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY,
                    request_id TEXT NOT NULL UNIQUE,
                    started_at TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    subscription TEXT NOT NULL,
                    account_ref TEXT,
                    credential_ref TEXT,
                    endpoint TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    model TEXT,
                    status INTEGER,
                    outcome TEXT NOT NULL DEFAULT 'incomplete',
                    upstream_attempted INTEGER NOT NULL DEFAULT 0,
                    duration_ms REAL,
                    input_bytes INTEGER NOT NULL DEFAULT 0,
                    masked_bytes INTEGER NOT NULL DEFAULT 0,
                    output_bytes INTEGER NOT NULL DEFAULT 0,
                    new_aliases INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS requests_started ON requests(started_at);
            """)
            db.execute("BEGIN IMMEDIATE")
            columns = {row[1] for row in db.execute("PRAGMA table_info(requests)")}
            if "owner" not in columns:
                db.execute("ALTER TABLE requests ADD COLUMN owner TEXT")
            db.execute("PRAGMA user_version=2")
        path.chmod(0o600)
        owners = self.path.with_name(self.path.name + ".owners")
        owners.mkdir(mode=0o700, exist_ok=True)
        self._owner_path = owners / self.owner
        self._owner_file = self._owner_path.open("w+b")
        self._owner_file.write(b"1")
        self._owner_file.flush()
        self._lock(self._owner_file)

    @staticmethod
    def _lock(handle):
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]

    def close(self):
        handle = getattr(self, "_owner_file", None)
        if handle is not None:
            handle.close()
            self._owner_file = None
            try:
                self._owner_path.unlink(missing_ok=True)
            except OSError:
                pass

    def __del__(self):
        self.close()

    def _alive(self, owner):
        if not owner:
            return True  # A legacy writer may still own this request.
        if owner == self.owner and self._owner_file is not None:
            return True
        # Only UUIDs written by this store may select a lock file.
        if len(owner) != 32 or any(c not in "0123456789abcdef" for c in owner):
            return True
        path = self.path.with_name(self.path.name + ".owners") / owner
        try:
            with path.open("rb") as handle:
                try:
                    self._lock(handle)
                except OSError:
                    return True
            return False
        except FileNotFoundError:
            return False
        except OSError:
            return True  # Uncertain ownership must protect the request.

    def recover_incomplete(self, apply=False, *, include_legacy=False):
        if apply and self.read_only:
            raise ValueError("Audit store is read-only.")
        if not self.path.exists():
            return {"candidates": 0, "recovered": 0, "dry_run": not apply}
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
            columns = {row[1] for row in db.execute("PRAGMA table_info(requests)")}
            owner_field = "owner" if "owner" in columns else "NULL AS owner"
            rows = db.execute("SELECT request_id, " + owner_field +
                              " FROM requests WHERE status IS NULL AND outcome='incomplete'").fetchall()
            orphaned = [row["request_id"] for row in rows
                        if (include_legacy and not row["owner"]) or not self._alive(row["owner"])]
            if apply:
                db.executemany("UPDATE requests SET outcome='interrupted' WHERE request_id=? "
                               "AND status IS NULL AND outcome='incomplete'", [(value,) for value in orphaned])
        return {"candidates": len(orphaned), "recovered": len(orphaned) if apply else 0,
                "dry_run": not apply}

    @contextmanager
    def connect(self):
        target = self.path.resolve().as_uri() + "?mode=ro" if self.read_only else self.path
        db = sqlite3.connect(target, timeout=5, uri=self.read_only)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def begin(self, agent, provider, subscription, endpoint, destination):
        if self.read_only or self._owner_file is None:
            raise ValueError("Audit store is read-only or closed.")
        request_id = uuid4().hex
        with self.connect() as db:
            db.execute(
                "INSERT INTO requests(request_id, started_at, agent, provider, "
                "subscription, endpoint, destination, owner) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (request_id, datetime.now(timezone.utc).isoformat(), agent,
                 provider, subscription, endpoint, destination, self.owner),
            )
        self.retention(apply=True)
        return request_id

    def finish(self, request_id, metadata):
        if self.read_only:
            raise ValueError("Audit store is read-only.")
        fields = ("agent", "account_ref", "credential_ref", "model", "status",
                  "outcome", "upstream_attempted", "duration_ms", "input_bytes",
                  "masked_bytes", "output_bytes", "new_aliases")
        with self.connect() as db:
            db.execute(
                "UPDATE requests SET " + ", ".join(f"{field}=?" for field in fields)
                + " WHERE request_id=?",
                tuple(metadata.get(field) for field in fields) + (request_id,),
            )
        self.retention(apply=True)

    def retention(self, apply=False):
        """Report candidates by default; only completed requests can be removed."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.max_age_days)).isoformat() if self.max_age_days else None
        if apply and self.read_only:
            raise ValueError("Audit store is read-only.")
        result = {"max_records": self.max_records, "max_age_days": self.max_age_days,
                  "candidates": 0, "removed": 0, "dry_run": not apply}
        if not self.path.exists():
            return result
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
            completed = "(status IS NOT NULL OR outcome='interrupted')"
            where = (completed + " AND (id IN (SELECT id FROM requests "
                     "WHERE " + completed + " ORDER BY id DESC LIMIT -1 OFFSET ?)"
                     + (" OR started_at < ?" if cutoff else "") + ")")
            values = [self.max_records] + ([cutoff] if cutoff else [])
            candidates = db.execute("SELECT COUNT(*) FROM requests WHERE " + where, values).fetchone()[0]
            if apply:
                db.execute("DELETE FROM requests WHERE " + where, values)
        return {"max_records": self.max_records, "max_age_days": self.max_age_days,
                "candidates": candidates, "removed": candidates if apply else 0, "dry_run": not apply}

    def query(self, filters, limit=50, offset=0):
        clauses, values = [], []
        for field in ("agent", "provider", "subscription", "account_ref", "credential_ref"):
            if filters.get(field):
                clauses.append(f"{field}=?")
                values.append(filters[field])
        result = filters.get("result")
        if result == "success":
            clauses.append("status BETWEEN 200 AND 299")
        elif result == "error":
            clauses.append("status >= 400")
        elif result == "incomplete":
            clauses.append("status IS NULL AND outcome != 'interrupted'")
        elif result == "interrupted":
            clauses.append("outcome='interrupted'")
        elif result:
            raise ValueError("Invalid result filter.")
        for field, op in (("since", ">="), ("until", "<=")):
            if filters.get(field):
                value = datetime.fromisoformat(filters[field].replace("Z", "+00:00"))
                if value.tzinfo is None:
                    raise ValueError("Time filters require a timezone.")
                clauses.append(f"started_at {op} ?")
                values.append(value.astimezone(timezone.utc).isoformat())
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.connect() as db:
            db.execute("BEGIN")  # Totals and page rows share one read snapshot.
            totals = dict(db.execute(
                "SELECT COUNT(*) AS total, COALESCE(SUM(status BETWEEN 200 AND 299),0) "
                "AS success, COALESCE(SUM(status >= 400),0) AS errors, "
                "COALESCE(SUM(upstream_attempted),0) AS forwarded, "
                "COALESCE(AVG(duration_ms),0) AS average_ms FROM requests" + where,
                values,
            ).fetchone())
            rows = [dict(row) for row in db.execute(
                "SELECT * FROM requests" + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                values + [limit, offset],
            )]
        return {"summary": totals, "rows": rows, "limit": limit, "offset": offset,
                "retention": self.retention()}


def anonymous_ref(token, kind, value):
    """Stable within this gateway; domain-separated, keyed and non-reversible."""
    if not value:
        return None
    return hmac.new(token.encode(), (kind + ":" + value).encode(), sha256).hexdigest()[:16]
