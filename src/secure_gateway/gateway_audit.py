"""Durable request metadata. Prompts, replies and credentials never enter SQLite."""

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import os
from pathlib import Path
import sqlite3
from uuid import uuid4


class AuditStore:
    def __init__(self, path: Path):
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
            # Bound local storage to the latest 100,000 requests.
            db.execute("DELETE FROM requests WHERE id <= "
                       "(SELECT id FROM requests ORDER BY id DESC LIMIT 1 OFFSET 100000)")
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
        return {"summary": totals, "rows": rows, "limit": limit, "offset": offset}


def anonymous_ref(token, kind, value):
    """Stable within this gateway; domain-separated, keyed and non-reversible."""
    if not value:
        return None
    return hmac.new(token.encode(), (kind + ":" + value).encode(), sha256).hexdigest()[:16]
