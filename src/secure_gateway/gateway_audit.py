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
    def __init__(self, path: Path, max_records=100_000, max_age_days=None):
        if type(max_records) is not int or max_records < 1:
            raise ValueError("Audit max_records must be a positive integer.")
        if max_age_days is not None and (type(max_age_days) is not int or max_age_days < 1):
            raise ValueError("Audit max_age_days must be a positive integer.")
        self.max_records = max_records
        self.max_age_days = max_age_days
        self.path = path
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not path.exists():
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in {0, 1}:
                raise ValueError("Unsupported gateway audit database version.")
            db.execute("PRAGMA journal_mode=WAL")
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
                PRAGMA user_version=1;
            """)
        path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def begin(self, agent, provider, subscription, endpoint, destination):
        request_id = uuid4().hex
        with self.connect() as db:
            db.execute(
                "INSERT INTO requests(request_id, started_at, agent, provider, "
                "subscription, endpoint, destination) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (request_id, datetime.now(timezone.utc).isoformat(), agent,
                 provider, subscription, endpoint, destination),
            )
        self.retention(apply=True)
        return request_id

    def finish(self, request_id, metadata):
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
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
            where = ("status IS NOT NULL AND (id IN (SELECT id FROM requests "
                     "WHERE status IS NOT NULL ORDER BY id DESC LIMIT -1 OFFSET ?)"
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
            clauses.append("status IS NULL")
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
