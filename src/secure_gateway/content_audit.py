"""Experimental encrypted content-audit storage primitives."""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
import re
import sqlite3
import threading
import time
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from secure_gateway.engine.tokenizer import SECRET_PATTERN

_SECRET = re.compile(SECRET_PATTERN)
_PRIVATE_KEY = re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----[\s\S]*?"
                          r"-----END (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")
_URL = re.compile(r"(?:https?|s3|ftp)://[^\s<>\"'{}|\\^`]+", re.IGNORECASE)


def redact_credentials(text: str) -> tuple[str, int]:
    """Remove known credential shapes from selected text, including code blocks."""
    text, blocks = _PRIVATE_KEY.subn("[credential removed]", text)
    text, urls = _URL.subn("[credential removed]", text)
    text, secrets = _SECRET.subn("[credential removed]", text)
    return text, blocks + urls + secrets


class LockedError(ValueError):
    """The content store is locked."""


class IntegrityError(ValueError):
    """An encrypted event cannot be authenticated."""


class DeletionMaintenanceError(OSError):
    """Records were deleted but SQLite compaction did not complete."""

    def __init__(self, request_ids: list[str]):
        super().__init__("Content audit deletion maintenance failed")
        self.request_ids = request_ids


_CURRENT_KDF = (131072, 8, 1)
_LEGACY_KDF = (16384, 8, 1)


def _derive(passphrase: str, salt: bytes, params: tuple[int, int, int] = _CURRENT_KDF) -> bytes:
    if not isinstance(passphrase, str) or not passphrase:
        raise ValueError("A nonempty passphrase is required")
    if params not in (_LEGACY_KDF, _CURRENT_KDF):
        raise ValueError("Unsupported scrypt parameters")
    n, r, p = params
    return Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(passphrase.encode("utf-8"))


def _aad(request_id: str, seq: int, kind: str, previous_tag: bytes) -> bytes:
    return json.dumps([1, request_id, seq, kind, previous_tag.hex()],
                      ensure_ascii=True, separators=(",", ":")).encode("ascii")


class ContentAuditStore:
    """Separate authenticated-encryption store, locked by default after opening."""

    def __init__(self, path: Path, *, max_requests: int = 1000,
                 max_bytes: int = 256 * 1024 * 1024, max_age_days: int = 7):
        if any(type(value) is not int or value < 1 for value in (max_requests, max_bytes, max_age_days)):
            raise ValueError("Invalid retention limit")
        if max_bytes < 256 * 1024:
            raise ValueError("Content audit capacity is too small")
        self.path = path
        self.max_requests, self.max_bytes, self.max_age_days = max_requests, max_bytes, max_age_days
        self._mutex = threading.RLock()
        self._active_lock = threading.Lock()
        self._active_ids: set[str] = set()
        self._keys: dict[int, bytes] = {}
        self._wrapping_key: bytes | None = None
        self._kdf_params: tuple[int, int, int] | None = None
        self._last_use = 0.0
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            # intentional: audit store database file may already exist
            pass
        else:
            os.close(fd)
        path.chmod(0o600)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS keys (id INTEGER PRIMARY KEY, nonce BLOB NOT NULL, wrapped BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL UNIQUE,
                    created REAL NOT NULL, state TEXT NOT NULL DEFAULT '부분',
                    omitted_bytes INTEGER NOT NULL DEFAULT 0, omitted_events INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS events (
                    request_id TEXT NOT NULL, seq INTEGER NOT NULL, kind TEXT NOT NULL,
                    key_id INTEGER NOT NULL, nonce BLOB NOT NULL, ciphertext BLOB NOT NULL,
                    PRIMARY KEY (request_id, seq)
                );
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(requests)")}
            for name, definition in (("state", "TEXT NOT NULL DEFAULT '부분'"),
                                     ("omitted_bytes", "INTEGER NOT NULL DEFAULT 0"),
                                     ("omitted_events", "INTEGER NOT NULL DEFAULT 0")):
                if name not in columns:
                    db.execute(f"ALTER TABLE requests ADD COLUMN {name} {definition}")
            key_columns = {row[1] for row in db.execute("PRAGMA table_info(keys)")}
            for name in ("kdf_n", "kdf_r", "kdf_p"):
                if name not in key_columns:
                    db.execute(f"ALTER TABLE keys ADD COLUMN {name} INTEGER")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA secure_delete=ON")
            db.execute("PRAGMA cache_spill=OFF")
            with db:
                yield db
        finally:
            db.close()

    def initialize(self, passphrase: str) -> None:
        """Create the first wrapped key; never replace existing key material."""
        with self._mutex, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM config WHERE key='salt'").fetchone():
                raise ValueError("Store is already initialized")
            salt, key = os.urandom(16), os.urandom(32)
            wrapping = _derive(passphrase, salt)
            nonce = os.urandom(12)
            wrapped = AESGCM(wrapping).encrypt(nonce, key, b"content-audit-key:1")
            db.execute("INSERT INTO config VALUES ('salt', ?)", (salt,))
            db.execute("INSERT INTO config VALUES ('scrypt', ?)", (b'n=131072,r=8,p=1',))
            db.execute("INSERT INTO keys(id, nonce, wrapped, kdf_n, kdf_r, kdf_p) VALUES (1, ?, ?, ?, ?, ?)",
                       (nonce, wrapped, *_CURRENT_KDF))
        with self._mutex:
            self._keys = {1: key}
            self._wrapping_key = wrapping
            self._kdf_params = _CURRENT_KDF
            self._last_use = time.monotonic()

    def lock(self) -> None:
        """Release references to all unwrapped keys."""
        with self._mutex:
            self._keys.clear()
            self._wrapping_key = None
            self._kdf_params = None
            self._last_use = 0.0

    def close(self) -> None:
        """Lock this store."""
        self.lock()

    def protect(self, request_id: str) -> None:
        """Protect an in-flight request from retention without performing I/O."""
        with self._active_lock:
            self._active_ids.add(request_id)

    def release(self, request_id: str) -> None:
        """Allow retention to remove a completed request."""
        with self._active_lock:
            self._active_ids.discard(request_id)

    def _protected(self, request_id: str) -> set[str]:
        with self._active_lock:
            return self._active_ids | {request_id}

    def initialized(self) -> bool:
        """Return whether the store has a wrapped key."""
        with self._mutex, self._connect() as db:
            return db.execute("SELECT 1 FROM config WHERE key='salt'").fetchone() is not None

    def locked(self) -> bool:
        """Return lock state without extending the idle deadline."""
        with self._mutex:
            if self._wrapping_key is not None and time.monotonic() - self._last_use >= 600:
                self.lock()
            return self._wrapping_key is None

    def unlock(self, passphrase: str) -> None:
        """Unwrap every retained key, or leave the store locked on failure."""
        with self._mutex:
            self.lock()
            with self._connect() as db:
                row = db.execute("SELECT value FROM config WHERE key='salt'").fetchone()
                if row is None:
                    raise ValueError("Store is not initialized")
                legacy = db.execute("SELECT value FROM config WHERE key='scrypt'").fetchone()
                legacy_profiles = {b'n=16384,r=8,p=1': _LEGACY_KDF, b'n=131072,r=8,p=1': _CURRENT_KDF}
                keys = {}
                derived = {}
                try:
                    for key_id, nonce, wrapped, n, r, p in db.execute(
                            "SELECT id, nonce, wrapped, kdf_n, kdf_r, kdf_p FROM keys ORDER BY id"):
                        params = legacy_profiles.get(legacy[0]) if (n, r, p) == (None, None, None) and legacy else (n, r, p)
                        if params not in (_LEGACY_KDF, _CURRENT_KDF):
                            raise ValueError("Unsupported scrypt parameters")
                        if params not in derived:
                            derived[params] = _derive(passphrase, row[0], params)
                        wrapping = derived[params]
                        keys[key_id] = AESGCM(wrapping).decrypt(
                            nonce, wrapped, f"content-audit-key:{key_id}".encode("ascii"))
                except InvalidTag:
                    raise ValueError("Incorrect passphrase or damaged store") from None
                if not keys or any(len(key) != 32 for key in keys.values()):
                    raise ValueError("Incorrect passphrase or damaged store")
                self._keys, self._wrapping_key = keys, wrapping
                self._kdf_params = params
                self._last_use = time.monotonic()

    def _require_unlocked(self, *, touch: bool = True) -> None:
        if self._wrapping_key is not None and time.monotonic() - self._last_use >= 600:
            self.lock()
        if self._wrapping_key is None:
            raise LockedError("Content audit is locked")
        if touch:
            self._last_use = time.monotonic()

    def change_passphrase(self, passphrase: str) -> None:
        """Atomically rewrap every key using a fresh salt."""
        with self._mutex:
            self._require_unlocked()
            salt = os.urandom(16)
            wrapping = _derive(passphrase, salt)
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                for key_id, key in self._keys.items():
                    nonce = os.urandom(12)
                    wrapped = AESGCM(wrapping).encrypt(nonce, key, f"content-audit-key:{key_id}".encode("ascii"))
                    db.execute("UPDATE keys SET nonce=?, wrapped=?, kdf_n=?, kdf_r=?, kdf_p=? WHERE id=?",
                               (nonce, wrapped, *_CURRENT_KDF, key_id))
                db.execute("UPDATE config SET value=? WHERE key='salt'", (salt,))
                db.execute("UPDATE config SET value=? WHERE key='scrypt'", (b'n=131072,r=8,p=1',))
            self._wrapping_key = wrapping
            self._kdf_params = _CURRENT_KDF

    def rotate_key(self) -> None:
        """Add a new data key while keeping old keys for reading."""
        with self._mutex:
            self._require_unlocked()
            wrapping = self._wrapping_key
            assert wrapping is not None  # invariant: guarded by _require_unlocked
            params = self._kdf_params
            assert params is not None  # invariant: guarded by _require_unlocked
            key = os.urandom(32)
            nonce = os.urandom(12)
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                key_id = db.execute("SELECT COALESCE(MAX(id),0)+1 FROM keys").fetchone()[0]
                wrapped = AESGCM(wrapping).encrypt(nonce, key, f"content-audit-key:{key_id}".encode("ascii"))
                db.execute("INSERT INTO keys(id, nonce, wrapped, kdf_n, kdf_r, kdf_p) VALUES (?, ?, ?, ?, ?, ?)",
                           (key_id, nonce, wrapped, *params))
            self._keys[key_id] = key

    def append(self, request_id: str, kind: str, payload: Any) -> None:
        """Append a single encrypted event linked to its predecessor."""
        if not request_id or not kind:
            raise ValueError("Invalid audit event")
        plain = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        with self._mutex:
            self._require_unlocked(touch=False)
            key_id = max(self._keys)
            self._prepare_capacity(len(plain) + 16, request_id)
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                previous = db.execute("SELECT seq, ciphertext FROM events WHERE request_id=? ORDER BY seq DESC LIMIT 1",
                                      (request_id,)).fetchone()
                seq = previous[0] + 1 if previous else 0
                tag = previous[1][-16:] if previous else b""
                nonce = os.urandom(12)
                ciphertext = AESGCM(self._keys[key_id]).encrypt(nonce, plain, _aad(request_id, seq, kind, tag))
                current_size = db.execute("SELECT COALESCE(SUM(length(ciphertext)),0) FROM events WHERE request_id=?",
                                          (request_id,)).fetchone()[0]
                if current_size + len(ciphertext) > self.max_bytes:
                    raise ValueError("Content audit request exceeds storage limit")
                db.execute("INSERT OR IGNORE INTO requests(request_id, created) VALUES (?, ?)",
                           (request_id, time.time()))
                db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
                           (request_id, seq, kind, key_id, nonce, ciphertext))
                self._retain(db, request_id)

    def _physical_size(self) -> tuple[int, int]:
        total = 0
        main = 0
        for suffix in ("", "-wal", "-shm", "-journal"):
            try:
                size = self.path.with_name(self.path.name + suffix).stat().st_size
            except FileNotFoundError:
                continue
            total += size
            if not suffix:
                main = size
        return total, main

    def _prepare_capacity(self, incoming: int, protected: str) -> None:
        """Conservatively reserve room for database and WAL pages before a write."""
        if incoming * 3 + 65536 >= self.max_bytes:
            raise ValueError("Content audit capacity unavailable")
        while True:
            with self._connect() as db:
                db.execute("PRAGMA busy_timeout=0")
                checkpoint = db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                page_size = db.execute("PRAGMA page_size").fetchone()[0]
                count = db.execute("SELECT count(*) FROM requests").fetchone()[0]
                existing = db.execute("SELECT 1 FROM requests WHERE request_id=?", (protected,)).fetchone()
            total, main = self._physical_size()
            # A transaction may rewrite existing pages into WAL. Reserve a copy of
            # the main DB, WAL frame/index overhead, and incoming b-tree pages.
            page_overhead = (main // page_size + 1) * 32 + 32768
            if (total + main + page_overhead + incoming * 3 + 65536 <= self.max_bytes
                    and (existing is not None or count < self.max_requests)):
                return
            if checkpoint[0] != 0:
                raise ValueError("Content audit capacity unavailable")
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                protected_ids = self._protected(protected)
                oldest = next((row for row in db.execute("SELECT request_id FROM requests ORDER BY id")
                               if row[0] not in protected_ids), None)
                if oldest is None:
                    raise ValueError("Content audit capacity unavailable")
                db.execute("DELETE FROM events WHERE request_id=?", (oldest[0],))
                db.execute("DELETE FROM requests WHERE request_id=?", (oldest[0],))
            self._compact()

    def _retain(self, db: sqlite3.Connection, protected: str) -> None:
        cutoff = time.time() - self.max_age_days * 86400
        while True:
            count = db.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
            size = db.execute("SELECT COALESCE(SUM(length(ciphertext)),0) FROM events").fetchone()[0]
            protected_ids = self._protected(protected)
            oldest = next((row for row in db.execute("SELECT request_id, created FROM requests ORDER BY id")
                           if row[0] not in protected_ids), None)
            if oldest is None or (count <= self.max_requests and size <= self.max_bytes and oldest[1] >= cutoff):
                break
            db.execute("DELETE FROM events WHERE request_id=?", (oldest[0],))
            db.execute("DELETE FROM requests WHERE request_id=?", (oldest[0],))

    def mark_status(self, request_id: str, state: str, omitted_bytes: int = 0, omitted_events: int = 0) -> None:
        """Persist content-free gap and lifecycle metadata, including while locked."""
        if state not in {"완료", "부분", "기록 실패", "기록 실패 (잠김)", "전송 여부 불확실"}:
            raise ValueError("Invalid content audit state")
        with self._mutex:
            self._prepare_capacity(1024, request_id)
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("INSERT OR IGNORE INTO requests(request_id, created) VALUES (?, ?)",
                           (request_id, time.time()))
                db.execute("UPDATE requests SET state=?, omitted_bytes=?, omitted_events=? WHERE request_id=?",
                           (state, omitted_bytes, omitted_events, request_id))
                self._retain(db, request_id)

    def request_status(self, request_id: str) -> dict[str, Any] | None:
        """Return safe, unauthenticated-at-rest operational metadata for a request."""
        with self._mutex, self._connect() as db:
            row = db.execute("SELECT state, omitted_bytes, omitted_events FROM requests WHERE request_id=?",
                             (request_id,)).fetchone()
        return None if row is None else {"state": row[0], "omitted_bytes": row[1], "omitted_events": row[2]}

    def delete(self, request_ids: list[str]) -> int:
        """Delete selected requests and compact the encrypted store."""
        return len(self.delete_selected(request_ids))

    def delete_selected(self, request_ids: list[str]) -> list[str]:
        """Return exactly the selected request IDs actually deleted."""
        with self._mutex:
            self._require_unlocked()
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                deleted = []
                protected = self._protected("")
                if any(request_id in protected for request_id in request_ids):
                    raise ValueError("Cannot delete active content audit requests")
                for request_id in dict.fromkeys(request_ids):
                    if not db.execute("SELECT 1 FROM requests WHERE request_id=? AND state!='삭제됨'",
                                      (request_id,)).fetchone():
                        continue
                    db.execute("DELETE FROM events WHERE request_id=?", (request_id,))
                    db.execute("UPDATE requests SET state='삭제됨', omitted_bytes=0, omitted_events=0 "
                               "WHERE request_id=?", (request_id,))
                    deleted.append(request_id)
            self._compact_deleted(deleted)
            return deleted

    def delete_all(self) -> int:
        """Delete all requests and compact the encrypted store."""
        return len(self.delete_range(None, None))

    def delete_range(self, since: float | None, until: float | None) -> list[str]:
        """Delete requests in a half-open time range, or all when both bounds are absent."""
        with self._mutex:
            self._require_unlocked()
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                rows = db.execute("SELECT request_id FROM requests WHERE state!='삭제됨' AND (? IS NULL OR created>=?) "
                                  "AND (? IS NULL OR created<?) ORDER BY id", (since, since, until, until)).fetchall()
                deleted = [row[0] for row in rows]
                protected = self._protected("")
                if any(request_id in protected for request_id in deleted):
                    raise ValueError("Cannot delete active content audit requests")
                db.executemany("DELETE FROM events WHERE request_id=?", rows)
                db.executemany("UPDATE requests SET state='삭제됨', omitted_bytes=0, omitted_events=0 "
                               "WHERE request_id=?", rows)
            self._compact_deleted(deleted)
            return deleted

    def _compact_deleted(self, deleted: list[str]) -> None:
        try:
            self._compact()
        except sqlite3.Error:
            raise DeletionMaintenanceError(deleted) from None

    def _compact(self) -> None:
        with self._connect() as db:
            if db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] != 0:
                raise sqlite3.OperationalError("Content audit checkpoint failed")
            db.execute("VACUUM")
            if db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] != 0:
                raise sqlite3.OperationalError("Content audit checkpoint failed")

    def read(self, request_id: str) -> list[tuple[str, Any]]:
        """Authenticate and return ordered events for an explicitly selected request."""
        with self._mutex:
            self._require_unlocked()
            with self._connect() as db:
                rows = db.execute("SELECT seq, kind, key_id, nonce, ciphertext FROM events "
                                  "WHERE request_id=? ORDER BY seq", (request_id,)).fetchall()
            result: list[tuple[str, Any]] = []
            previous = b""
            try:
                for expected, (seq, kind, key_id, nonce, ciphertext) in enumerate(rows):
                    if seq != expected:
                        raise IntegrityError("Damaged audit sequence")
                    plain = AESGCM(self._keys[key_id]).decrypt(nonce, ciphertext, _aad(request_id, seq, kind, previous))
                    result.append((kind, json.loads(plain)))
                    previous = ciphertext[-16:]
            except (InvalidTag, KeyError, ValueError, TypeError, UnicodeDecodeError):
                raise IntegrityError("Damaged audit sequence") from None
            return result
