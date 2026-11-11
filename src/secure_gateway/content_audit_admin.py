"""Experimental local administration of the opt-in content audit prototype."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import threading
import time
from typing import Any

from secure_gateway.content_audit import ContentAuditStore, DeletionMaintenanceError, IntegrityError, LockedError, redact_credentials
from secure_gateway.content_audit_capture import ContentAuditCapture
from secure_gateway.content_audit_export import export_requests, verified_state
from secure_gateway.content_audit_writer import ContentAuditWriter
from secure_gateway.encrypted_session import SnapshotEncryption, decrypt_snapshot_bytes
from secure_gateway.gateway_install import atomic_bytes
from secure_gateway.logging_config import get_logger

_logger = get_logger("content_audit")
_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "paused": False,
    "providers": {"claude": False, "codex": False, "xai": False},
    "agents": {"Claude Code": True, "Codex": True, "xAI client": True,
               "Grok Build": True, "Antigravity SDK": True},
    "kinds": {"input": False, "sent": False, "response": False, "tool_args": False, "tool_result": False},
    "failure_policy": "continue",
    "retention": {"max_age_days": 7, "max_requests": 1000, "max_bytes": 256 * 1024 * 1024},
}


class MetadataRequiredError(ValueError):
    """Content audit cannot be enabled without durable metadata admission."""


def _validate_settings(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(_DEFAULTS):
        raise ValueError("Invalid settings")
    for key in ("enabled", "paused"):
        if type(value[key]) is not bool:
            raise ValueError("Invalid settings")
    for key in ("providers", "agents", "kinds"):
        part = value[key]
        if (not isinstance(part, dict) or set(part) != set(_DEFAULTS[key])
                or any(type(item) is not bool for item in part.values())):
            raise ValueError("Invalid settings")
    if value["failure_policy"] not in {"continue", "block"}:
        raise ValueError("Invalid settings")
    retention = value["retention"]
    if not isinstance(retention, dict) or set(retention) != set(_DEFAULTS["retention"]):
        raise ValueError("Invalid settings")
    for key, maximum in (("max_age_days", 3650), ("max_requests", 100000), ("max_bytes", 4 * 1024**3)):
        if type(retention[key]) is not int or not 1 <= retention[key] <= maximum:
            raise ValueError("Invalid settings")
    if retention["max_bytes"] < 256 * 1024:
        raise ValueError("Invalid settings")
    return deepcopy(value)


class ContentAuditAdmin:
    """Own local settings, unlock attempts and the optional writer lifetime."""

    def __init__(self, gateway: Any, root: Path | None, token: str):
        self.gateway, self.root, self._token = gateway, root, token
        self._lock = threading.RLock()
        self.settings: dict[str, Any] = deepcopy(_DEFAULTS)
        self.store: ContentAuditStore | None = None
        self.writer: ContentAuditWriter | None = None
        self.failures = 0
        self.lockout_until = 0.0
        self.settings_path = root / "content-audit-settings.enc" if root else None
        self.store_path = root / "content-audit.sqlite3" if root else None
        if self.settings_path and self.settings_path.exists():
            with self.settings_path.open("rb") as stream:
                encrypted = stream.read(65537)
            if len(encrypted) > 65536:
                raise ValueError("Invalid content audit settings")
            self.settings = _validate_settings(json.loads(decrypt_snapshot_bytes(encrypted, token)))
            if self.settings["enabled"]:
                if self.gateway.audit is None:
                    raise MetadataRequiredError("Content audit requires metadata audit")
                self._ensure_store()
                self._apply()

    def _ensure_store(self) -> ContentAuditStore:
        if self.store is None:
            if self.store_path is None:
                raise ValueError("Content audit storage unavailable")
            limits = self.settings["retention"]
            self.store = ContentAuditStore(self.store_path, **limits)
            self.writer = ContentAuditWriter(self.store)
            self.gateway.content_audit = ContentAuditCapture(self.writer)
            self._apply()
        return self.store

    def _apply(self) -> None:
        capture = self.gateway.content_audit
        if capture is None:
            return
        if not self.settings["enabled"]:
            capture.enabled = False
        capture.paused = self.settings["paused"]
        capture.policy = self.settings["failure_policy"]
        capture.providers = {key for key, enabled in self.settings["providers"].items() if enabled}
        capture.agents = {key for key, enabled in self.settings["agents"].items() if enabled}
        capture.kinds = {key for key, enabled in self.settings["kinds"].items() if enabled}
        capture.enabled = self.settings["enabled"]
        if self.store is not None:
            with self.store._mutex:
                for key, value in self.settings["retention"].items():
                    setattr(self.store, key, value)

    def status(self) -> dict[str, Any]:
        """Return safe state without opening a new store or extending its idle timeout."""
        with self._lock:
            if self.store is None and self.store_path and self.store_path.exists():
                self._ensure_store()
            return {"initialized": self.store.initialized() if self.store else False,
                    "locked": self.store.locked() if self.store else True,
                    "enabled": self.settings["enabled"], "paused": self.settings["paused"],
                    "lockout_seconds": max(0, int(self.lockout_until - time.monotonic() + 0.999))}

    def update_settings(self, value: Any, confirmed: bool) -> dict[str, Any]:
        """Persist an authenticated settings replacement after explicit enablement consent."""
        settings = _validate_settings(value)
        with self._lock:
            if settings["enabled"] and not self.settings["enabled"] and confirmed is not True:
                raise ValueError("Explicit content warning confirmation required")
            if settings["enabled"] and self.gateway.audit is None:
                raise MetadataRequiredError("Content audit requires metadata audit")
            if self.settings_path is None:
                raise ValueError("Content audit storage unavailable")
            if settings["enabled"]:
                self._ensure_store()
            if self.store is not None:
                with self.store._mutex:
                    total, main = self.store._physical_size()
                    # A lowered limit must leave room for a WAL checkpoint and a small write.
                    if settings["retention"]["max_bytes"] < total + main + (main // 512 + 1) * 32 + 100 * 1024:
                        raise ValueError("Content audit capacity is below current use")
            encrypted = SnapshotEncryption(self._token).encrypt(json.dumps(settings).encode("utf-8"))
            atomic_bytes(self.settings_path, encrypted)
            self.settings = settings
            self._apply()
            _logger.warning("content_audit_settings_change")
            return deepcopy(settings)

    def unlock(self, passphrase: str, initialize: bool) -> int:
        """Unlock or explicitly initialize, enforcing the shared failure lockout."""
        with self._lock:
            if time.monotonic() < self.lockout_until:
                return 429
            try:
                store = self._ensure_store()
                if initialize:
                    store.initialize(passphrase)
                else:
                    store.unlock(passphrase)
            except ValueError:
                self.failures += 1
                if self.failures >= 5:
                    self.failures = 0
                    self.lockout_until = time.monotonic() + 60
                _logger.warning("content_audit_unlock_failure")
                return 401
            self.failures = 0
            self.lockout_until = 0.0
            _logger.warning("content_audit_unlock_success")
            return 200

    def lock(self) -> None:
        """Release in-memory keys."""
        with self._lock:
            if self.store:
                self.store.lock()

    def list_requests(self) -> list[dict[str, Any]]:
        """List only safe identifiers and timestamps."""
        with self._lock:
            rows = []
            if self.store is None:
                if self.store_path and self.store_path.exists():
                    self._ensure_store()
            if self.store is not None:
                with self.store._connect() as db:
                    rows = db.execute("SELECT request_id, created, state, omitted_bytes, omitted_events "
                                      "FROM requests ORDER BY id DESC LIMIT 1000").fetchall()
            content = {row[0]: {"request_id": row[0], "created": row[1], "state": row[2],
                                "omitted_bytes": row[3], "omitted_events": row[4], "integrity": "not_verified"}
                       for row in rows}
            results = []
            if self.gateway.audit is not None:
                with self.gateway.audit.connect() as db:
                    metadata = db.execute("SELECT request_id, started_at, content_audit, outcome FROM requests "
                                          "ORDER BY id DESC LIMIT 1000").fetchall()
                for row in metadata:
                    request_id, started_at, intent, outcome = row
                    entry = content.pop(request_id, None)
                    if entry is None:
                        state = ("부분" if outcome == "incomplete" else "기록 실패") if intent == "capture" else {
                            "off": "꺼짐", "paused": "일시 중지", "excluded": "제외", None: "과거 기록 없음"
                        }.get(intent, "기록 실패")
                        entry = {"request_id": request_id, "created": None, "state": state,
                                 "omitted_bytes": 0, "omitted_events": 0, "integrity": "not_verified"}
                    entry.update({"intent": intent, "started_at": started_at})
                    results.append(entry)
            results.extend(content.values())
            _logger.warning("content_audit_access")
            return results[:1000]

    def get_request(self, request_id: str) -> list[dict[str, Any]]:
        """Decrypt one explicitly requested record."""
        if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
            raise ValueError("Invalid request")
        with self._lock:
            store = self._ensure_store()
            events = store.read(request_id)
            if not events:
                raise LookupError("Unknown request")
            _logger.warning("content_audit_access")
            return [{"kind": kind, "content": payload} for kind, payload in events]

    @staticmethod
    def verified_state(events: list[dict[str, Any]]) -> str:
        """Derive completeness only from an authenticated final marker."""
        return verified_state([(event["kind"], event["content"]) for event in events])

    def review(self, request_id: str, status: str, memo: str) -> None:
        """Encrypt a review marker and its credential-redacted memo."""
        if status not in {"정상", "확인 필요"} or not isinstance(memo, str) or len(memo) > 4096:
            raise ValueError("Invalid review")
        with self._lock:
            events = self.get_request(request_id)
            assert self.store is not None  # invariant: initialized by get_request via _ensure_store
            clean, removals = redact_credentials(memo)
            self.store.append(request_id, "review", {"status": status, "memo": clean, "redactions": removals})
            last = events[-1]
            marker = last["content"] if last["kind"] == "finished" else {
                "partial": True, "omitted_bytes": 0, "omitted_events": 0, "failed": False, "uncertain": False}
            self.store.append(request_id, "finished", marker)
            _logger.warning("content_audit_review")

    @staticmethod
    def _range(selection: dict[str, Any]) -> tuple[float, float]:
        def parse(value: Any) -> float:
            if not isinstance(value, str):
                raise ValueError("Invalid range")
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("Invalid range")
            return parsed.astimezone(timezone.utc).timestamp()
        since, until = parse(selection.get("since")), parse(selection.get("until"))
        if since >= until:
            raise ValueError("Invalid range")
        return since, until

    @staticmethod
    def _ids(value: Any) -> list[str]:
        if (not isinstance(value, list) or not value or len(value) > 1000
                or any(not isinstance(item, str) or not _REQUEST_ID.fullmatch(item) for item in value)
                or len(set(value)) != len(value)):
            raise ValueError("Invalid request selection")
        return value

    def export(self, selection: dict[str, Any]) -> dict[str, Any]:
        """Export an explicitly selected set of requests and content kinds."""
        allowed = {"request_ids", "since", "until", "kinds", "passphrase", "plaintext", "confirm_plaintext"}
        if set(selection) - allowed or not isinstance(selection.get("kinds"), list):
            raise ValueError("Invalid selection")
        kinds = selection["kinds"]
        if not kinds or any(not isinstance(kind, str) for kind in kinds) or len(kinds) != len(set(kinds)):
            raise ValueError("Invalid selection")
        plaintext = selection.get("plaintext", False)
        confirmation = selection.get("confirm_plaintext", False)
        if type(plaintext) is not bool or type(confirmation) is not bool:
            raise ValueError("Invalid selection")
        with self._lock:
            store = self._ensure_store()
            if "request_ids" in selection:
                if "since" in selection or "until" in selection:
                    raise ValueError("Invalid selection")
                ids = self._ids(selection["request_ids"])
            else:
                since, until = self._range(selection)
                with store._connect() as db:
                    ids = [row[0] for row in db.execute("SELECT request_id FROM requests WHERE created>=? "
                                                        "AND created<? ORDER BY id LIMIT 1001", (since, until))]
                ids = self._ids(ids)
            result = export_requests(store, ids, set(kinds), passphrase=selection.get("passphrase"),
                                     plaintext=plaintext, confirm_plaintext=confirmation)
            _logger.warning("content_audit_export")
            return result

    def delete(self, selection: dict[str, Any]) -> list[str]:
        """Delete an explicit request selection, range, or confirmed entire store."""
        with self._lock:
            store = self._ensure_store()
            if set(selection) == {"request_ids"}:
                deleted = store.delete_selected(self._ids(selection["request_ids"]))
            elif set(selection) == {"all", "confirm"} and selection["all"] is True and selection["confirm"] is True:
                deleted = store.delete_range(None, None)
            elif set(selection) == {"since", "until", "confirm"} and selection["confirm"] is True:
                since, until = self._range(selection)
                deleted = store.delete_range(since, until)
            else:
                raise ValueError("Invalid selection")
            _logger.warning("content_audit_delete")
            return deleted

    def close(self) -> None:
        """Drain queued work and release keys."""
        with self._lock:
            if self.writer:
                self.writer.close()
            if self.store:
                self.store.close()


def handle_content_admin(handler: Any) -> bool:
    """Handle the bounded, local-token-protected content audit admin API."""
    from urllib.parse import urlsplit

    url = urlsplit(handler.path)
    prefix = "/admin/api/content-audit/"
    if not url.path.startswith(prefix):
        return False
    port = handler.server.server_port
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    origin = handler.headers.get("Origin")
    if handler.headers.get("Host") not in hosts or (origin is not None and origin not in {"http://" + h for h in hosts}):
        _logger.warning("content_audit_access_failure")
        handler.send_body(403, b'{"error":"Local origin required"}')
        return True
    if not handler.authorized():
        _logger.warning("content_audit_access_failure")
        handler.send_body(401, b'{"error":"Unauthorized"}')
        return True
    endpoint = url.path[len(prefix):]
    try:
        if url.query:
            raise ValueError("Invalid request")
        manager: ContentAuditAdmin = handler.server.content_admin
        method = handler.command
        payload: Any = None
        if method in {"POST", "PUT"}:
            if handler.headers.get("Transfer-Encoding") or handler.headers.get("Content-Encoding"):
                raise ValueError("Invalid encoding")
            length = int(handler.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("Invalid request")
            raw = handler.rfile.read(length)
            handler._request_body_consumed = len(raw) == length
            if len(raw) != length:
                raise ValueError("Invalid request")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("Invalid request")
        if method == "GET" and endpoint == "status":
            result, status = manager.status(), 200
        elif method == "GET" and endpoint == "settings":
            result, status = deepcopy(manager.settings), 200
        elif method == "GET" and endpoint == "list":
            result, status = {"requests": manager.list_requests()}, 200
        elif method == "PUT" and endpoint == "settings":
            if set(payload) - {"settings", "confirm_sensitive_content"} or "settings" not in payload:
                raise ValueError("Invalid request")
            result, status = manager.update_settings(payload["settings"], payload.get("confirm_sensitive_content", False)), 200
        elif method == "POST" and endpoint == "unlock":
            if set(payload) - {"passphrase", "initialize"} or not isinstance(payload.get("passphrase"), str):
                raise ValueError("Invalid request")
            if not 1 <= len(payload["passphrase"]) <= 1024 or type(payload.get("initialize", False)) is not bool:
                raise ValueError("Invalid request")
            status = manager.unlock(payload["passphrase"], payload.get("initialize", False))
            result = {"unlocked": True} if status == 200 else {"error": "Unlock failed"}
        elif method == "POST" and endpoint == "lock":
            if payload:
                raise ValueError("Invalid request")
            manager.lock()
            result, status = {"locked": True}, 200
        elif method == "POST" and endpoint == "rotate-key":
            if payload:
                raise ValueError("Invalid request")
            with manager._lock:
                manager._ensure_store().rotate_key()
                _logger.warning("content_audit_key_rotation")
            result, status = {"rotated": True}, 200
        elif method == "POST" and endpoint == "change-passphrase":
            if (set(payload) != {"passphrase", "new_passphrase"}
                    or any(not isinstance(payload[key], str) or not 1 <= len(payload[key]) <= 1024
                           for key in ("passphrase", "new_passphrase"))):
                raise ValueError("Invalid request")
            with manager._lock:
                status = manager.unlock(payload["passphrase"], False)
                if status == 200:
                    manager._ensure_store().change_passphrase(payload["new_passphrase"])
                    _logger.warning("content_audit_passphrase_change")
            result = {"changed": True} if status == 200 else {"error": "Unlock failed"}
        elif method == "POST" and endpoint == "get":
            if set(payload) != {"request_id"}:
                raise ValueError("Invalid request")
            events = manager.get_request(payload["request_id"])
            result, status = {"events": events, "verified_state": manager.verified_state(events)}, 200
        elif method == "POST" and endpoint == "review":
            if set(payload) != {"request_id", "status", "memo"}:
                raise ValueError("Invalid request")
            manager.review(payload["request_id"], payload["status"], payload["memo"])
            result, status = {"saved": True}, 200
        elif method == "POST" and endpoint == "export":
            result, status = manager.export(payload), 200
        elif method == "POST" and endpoint == "delete":
            deleted = manager.delete(payload)
            result, status = {"deleted": len(deleted), "request_ids": deleted}, 200
        else:
            result, status = {"error": "Unknown endpoint"}, 404
        handler.send_body(status, json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except MetadataRequiredError:
        _logger.warning("content_audit_settings_failure")
        handler.send_body(409, b'{"error":"Content audit requires metadata audit"}')
    except DeletionMaintenanceError as exc:
        _logger.warning("content_audit_delete_failure")
        result = {"deleted": len(exc.request_ids), "request_ids": exc.request_ids, "maintenance": "failed"}
        handler.send_body(503, json.dumps(result).encode("utf-8"))
    except LockedError:
        _logger.warning("content_audit_request_failure")
        handler.send_body(423, b'{"error":"Content audit locked"}')
    except LookupError:
        _logger.warning("content_audit_request_failure")
        handler.send_body(404, b'{"error":"Unknown request"}')
    except IntegrityError:
        _logger.warning("content_audit_request_failure")
        handler.send_body(409, b'{"error":"Content audit integrity failure"}')
    except (ValueError, TypeError, UnicodeError, OSError, sqlite3.Error):
        _logger.warning("content_audit_request_failure")
        handler.send_body(400, b'{"error":"Invalid request or storage unavailable"}')
    except Exception:
        _logger.warning("content_audit_request_failure")
        handler.send_body(500, b'{"error":"Content audit unavailable"}')
    return True
