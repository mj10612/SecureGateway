"""Durable request metadata. Prompts, replies and credentials never enter SQLite."""

from contextlib import contextmanager
import base64
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import hmac
import json
import os
import sys
from pathlib import Path
import sqlite3
import stat
from uuid import uuid4


class AuditStore:
    def __init__(self, path: Path, max_records=100_000, max_age_days=None, *, read_only=False):
        if type(max_records) is not int or not 1 <= max_records <= 2**63 - 1:
            raise ValueError("Audit max_records must be an integer between 1 and 9223372036854775807.")
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
        self._export_key = os.urandom(32)
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
        # Never reuse a published owner path: cleanup can safely remove an unlocked
        # UUID while new writers always create their own, exclusive UUID file.
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._owner_file = self._owner_path.open("x+b")
            # Empty files are ineligible for cleanup: acquire ownership before
            # publishing the marker so even read-only inspection cannot race it.
            self._lock(self._owner_file)
            self._owner_file.write(b"1")
            self._owner_file.flush()

    @staticmethod
    def _lock(handle):
        handle.seek(0)
        if sys.platform == "win32":
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

    def cleanup_owners(self, apply=False):
        """Remove only unlocked UUID files no longer referenced by any request."""
        if apply and self.read_only:
            raise ValueError("Audit store is read-only.")
        result = {"candidates": 0, "removed": 0, "dry_run": not apply}
        owners = self.path.with_name(self.path.name + ".owners")
        if not self.path.exists() or not owners.exists() or owners.is_symlink():
            return result
        # Serialize with request insertion, retention and recovery. UUID paths
        # cannot be reused by a new writer, even after its old owner exits.
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
            columns = {row[1] for row in db.execute("PRAGMA table_info(requests)")}
            if "owner" not in columns:
                return result  # Legacy ownership cannot be established safely.
            referenced = {row[0] for row in db.execute("SELECT DISTINCT owner FROM requests")}
            if None in referenced or "" in referenced:
                return result  # Legacy requests may belong to an unknown writer.
            for path in owners.iterdir():
                name = path.name
                if len(name) != 32 or any(c not in "0123456789abcdef" for c in name):
                    continue
                if name in referenced or name == self.owner:
                    continue
                try:
                    before = path.lstat()
                    if not stat.S_ISREG(before.st_mode) or before.st_size < 1:
                        continue
                    with path.open("rb") as handle:
                        opened = os.fstat(handle.fileno())
                        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                            continue
                        self._lock(handle)
                        result["candidates"] += 1
                        if apply and sys.platform != "win32":
                            path.unlink()
                            result["removed"] += 1
                    if apply and sys.platform == "win32":
                        # Windows requires our lock handle closed before unlink.
                        # Database serialization and exclusive UUID creation
                        # prevent legitimate writers/recovery from reusing it.
                        current = path.lstat()
                        if (current.st_dev, current.st_ino) == (opened.st_dev, opened.st_ino):
                            path.unlink()
                            result["removed"] += 1
                except OSError:
                    continue  # Live, disappeared or uncertain files are protected.
        return result

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

    @staticmethod
    def _query_conditions(filters):
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
        return (" WHERE " + " AND ".join(clauses) if clauses else ""), values

    def query(self, filters, limit=50, offset=0):
        if (type(limit) is not int or not 1 <= limit <= 200
                or type(offset) is not int or not 0 <= offset <= 2**63 - 1):
            raise ValueError("Invalid audit pagination.")
        where, values = self._query_conditions(filters)
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

    def _export_cursor(self, payload):
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signed = data + hmac.digest(self._export_key, data, "sha256")
        return base64.urlsafe_b64encode(signed).decode().rstrip("=")

    def _read_export_cursor(self, cursor, fingerprint, max_rows):
        try:
            if (not isinstance(cursor, str) or not 1 <= len(cursor) <= 1024
                    or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in cursor)):
                raise ValueError("Invalid export cursor.")
            signed = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
            data, signature = signed[:-32], signed[-32:]
            if not hmac.compare_digest(signature, hmac.digest(self._export_key, data, "sha256")):
                raise ValueError("Invalid export cursor.")
            payload = json.loads(data)
            if (not isinstance(payload, dict) or set(payload) != {"v", "f", "u", "a", "r", "n"}
                    or type(payload["v"]) is not int or payload["v"] != 1
                    or payload["f"] != fingerprint or type(payload["n"]) is not int or payload["n"] != max_rows
                    or type(payload["u"]) is not int or type(payload["a"]) is not int
                    or not 1 <= payload["a"] <= payload["u"] <= 2**63 - 1
                    or not isinstance(payload["r"], str)):
                raise ValueError("Invalid export cursor.")
            return payload
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError("Invalid export cursor; restart the export.") from exc

    def export_metadata(self, filters, max_rows=1000, *, cursor=None):
        """Return a bounded keyset page with a fixed insertion watermark."""
        if type(max_rows) is not int or not 1 <= max_rows <= 1000:
            raise ValueError("Invalid audit export limit.")
        where, values = self._query_conditions(filters)
        fingerprint = sha256(json.dumps(filters, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        state = self._read_export_cursor(cursor, fingerprint, max_rows) if cursor is not None else None
        fields = ("request_id", "started_at", "agent", "provider", "subscription",
                  "endpoint", "model", "status", "outcome", "upstream_attempted",
                  "duration_ms", "input_bytes", "masked_bytes", "output_bytes", "new_aliases")
        with self.connect() as db:
            db.execute("BEGIN")
            if state is None:
                anchor = db.execute("SELECT id, request_id FROM requests" + where
                                    + " ORDER BY id DESC LIMIT 1", values).fetchone()
                upper, request_id = (anchor[0], anchor[1]) if anchor else (0, "")
                after = upper
            else:
                upper, after, request_id = state["u"], state["a"], state["r"]
                anchor = db.execute("SELECT request_id FROM requests WHERE id=?", (upper,)).fetchone()
                if anchor is None or anchor[0] != request_id:
                    raise ValueError("Export watermark expired; restart the export.")
            page_where = where + (" AND " if where else " WHERE ") + "id <= ?"
            page_values = values + [upper]
            if state is not None:
                page_where += " AND id < ?"
                page_values.append(after)
            query = db.execute(
                "SELECT id, " + ", ".join(fields) + " FROM requests" + page_where
                + " ORDER BY id DESC LIMIT ?", page_values + [max_rows + 1],
            )
            rows: list[dict[str, object]] = []
            while page := query.fetchmany(200):
                rows.extend(dict(row) for row in page)
        truncated = len(rows) > max_rows
        rows = rows[:max_rows]
        next_cursor = self._export_cursor({"v": 1, "f": fingerprint, "u": upper,
                                          "a": rows[-1]["id"], "r": request_id,
                                          "n": max_rows}) if truncated else None
        for row in rows:
            del row["id"]
        return {"rows": rows, "count": len(rows), "limit": max_rows,
                "truncated": truncated, "next_cursor": next_cursor}


def anonymous_ref(token, kind, value):
    """Stable within this gateway; domain-separated, keyed and non-reversible."""
    if not value:
        return None
    return hmac.new(token.encode(), (kind + ":" + value).encode(), sha256).hexdigest()[:16]
