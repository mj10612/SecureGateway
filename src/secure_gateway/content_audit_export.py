"""Selected content audit export and authenticated offline decoding."""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import time
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from secure_gateway.content_audit import ContentAuditStore, _aad, _derive, _CURRENT_KDF, _LEGACY_KDF
from secure_gateway.content_audit import IntegrityError
from secure_gateway.content_audit_writer import _sanitize

_KINDS = frozenset({"input", "sent", "response", "tool_args", "tool_result", "review"})
_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


def verified_state(records: list[tuple[str, Any]]) -> str:
    """Derive request completeness from authenticated lifecycle markers."""
    if not records or records[0][0] != "opened" or records[-1][0] != "finished":
        return "부분"
    marker = records[-1][1]
    if (not isinstance(marker, dict) or any(type(marker.get(key)) is not bool
                                           for key in ("failed", "uncertain", "partial"))):
        raise IntegrityError("Invalid completion marker")
    return ("기록 실패" if marker["failed"] else "전송 여부 불확실" if marker["uncertain"]
            else "부분" if marker["partial"] else "완료")


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _unb64(value: Any) -> bytes:
    if not isinstance(value, str):
        raise ValueError("Invalid export")
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Invalid export") from None


def export_requests(store: ContentAuditStore, request_ids: list[str], kinds: set[str], *,
                    passphrase: str | None = None, plaintext: bool = False,
                    confirm_plaintext: bool = False) -> dict[str, Any]:
    """Export explicitly selected request IDs and kinds, encrypted by default."""
    if (not request_ids or len(request_ids) > 1000 or len(set(request_ids)) != len(request_ids)
            or any(not isinstance(item, str) or not _REQUEST_ID.fullmatch(item) for item in request_ids)
            or not kinds or not kinds <= _KINDS):
        raise ValueError("Invalid export selection")
    if plaintext and confirm_plaintext is not True:
        raise ValueError("Plaintext export requires confirmation")
    if not plaintext and (not isinstance(passphrase, str) or not 1 <= len(passphrase) <= 1024):
        raise ValueError("Export passphrase required")
    requests = []
    with store._mutex:
        store._require_unlocked()
        for request_id in request_ids:
            records = store.read(request_id)
            if not records:
                raise ValueError("Unknown request")
            events = []
            for kind, payload in records:
                if kind == "opened" and "input" in kinds and isinstance(payload, dict) and payload.get("input") is not None:
                    kind, payload = "input", payload["input"]
                elif kind not in kinds:
                    continue
                sanitized, _ = _sanitize(payload)
                events.append({"kind": kind, "content": sanitized})
            requests.append({"request_id": request_id, "state": verified_state(records), "events": events})
    document = {"version": 1, "requests": requests}
    if plaintext:
        return document
    data = json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    salt, wrapping_nonce, data_nonce, data_key = os.urandom(16), os.urandom(12), os.urandom(12), os.urandom(32)
    assert passphrase is not None  # invariant: validated earlier when not plaintext
    wrapped = AESGCM(_derive(passphrase, salt)).encrypt(wrapping_nonce, data_key, b"content-audit-export-key-v1")
    ciphertext = AESGCM(data_key).encrypt(data_nonce, data, b"content-audit-export-data-v1")
    return {"format": "secure-gateway-content-audit-v1", "kdf": {"name": "scrypt", "n": 131072, "r": 8,
            "p": 1, "salt": _b64(salt)}, "wrapping_nonce": _b64(wrapping_nonce), "wrapped_key": _b64(wrapped),
            "nonce": _b64(data_nonce), "ciphertext": _b64(ciphertext)}


def decrypt_export(value: Any, passphrase: str) -> dict[str, Any]:
    """Authenticate and decode an encrypted export for offline restoration."""
    try:
        if not isinstance(value, dict) or set(value) != {"format", "kdf", "wrapping_nonce", "wrapped_key", "nonce", "ciphertext"}:
            raise ValueError("Invalid export")
        kdf = value["kdf"]
        if (value["format"] != "secure-gateway-content-audit-v1" or not isinstance(kdf, dict)
                or set(kdf) != {"name", "n", "r", "p", "salt"}
                or kdf["name"] != "scrypt"
                or (kdf["n"], kdf["r"], kdf["p"]) not in (_LEGACY_KDF, _CURRENT_KDF)):
            raise ValueError("Invalid export")
        salt = _unb64(kdf["salt"])
        wrapping_nonce, data_nonce = _unb64(value["wrapping_nonce"]), _unb64(value["nonce"])
        if len(salt) != 16 or len(wrapping_nonce) != 12 or len(data_nonce) != 12:
            raise ValueError("Invalid export")
        key = AESGCM(_derive(passphrase, salt, (kdf["n"], kdf["r"], kdf["p"]))).decrypt(wrapping_nonce, _unb64(value["wrapped_key"]),
                                                        b"content-audit-export-key-v1")
        plain = AESGCM(key).decrypt(data_nonce, _unb64(value["ciphertext"]), b"content-audit-export-data-v1")
        data = json.loads(plain)
        if not isinstance(data, dict) or set(data) != {"version", "requests"} or data["version"] != 1:
            raise ValueError("Invalid export")
        return data
    except (InvalidTag, ValueError, TypeError, KeyError, UnicodeError):
        raise ValueError("Invalid passphrase or damaged export") from None


def restore_export(store: ContentAuditStore, value: Any, passphrase: str) -> int:
    """Atomically restore a verified export into an empty, unlocked store."""
    document = decrypt_export(value, passphrase)
    requests = document["requests"]
    if not isinstance(requests, list) or not requests or len(requests) > store.max_requests:
        raise ValueError("Invalid restore selection")
    prepared: list[tuple[str, list[tuple[str, bytes]]]] = []
    ids: set[str] = set()
    total = 0
    for request in requests:
        if not isinstance(request, dict) or set(request) != {"request_id", "state", "events"}:
            raise ValueError("Invalid restore selection")
        request_id, events = request["request_id"], request["events"]
        if (not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id) or request_id in ids
                or not isinstance(request["state"], str)
                or request["state"] not in {"완료", "부분", "기록 실패", "전송 여부 불확실"}
                or not isinstance(events, list) or len(events) > 2000):
            raise ValueError("Invalid restore selection")
        ids.add(request_id)
        total += 1024  # Request row, lifecycle markers and b-tree overhead.
        sizes: dict[str, int] = {}
        event_data: list[tuple[str, bytes]] = []
        for event in events:
            if (not isinstance(event, dict) or set(event) != {"kind", "content"}
                    or not isinstance(event["kind"], str) or event["kind"] not in _KINDS):
                raise ValueError("Invalid restore selection")
            kind = event["kind"]
            clean, _ = _sanitize(event["content"])
            raw = json.dumps(clean, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
            sizes[kind] = sizes.get(kind, 0) + len(raw)
            if sizes[kind] > 1024 * 1024:
                raise ValueError("Invalid restore selection")
            total += len(raw) + 64
            event_data.append((kind, raw))
        prepared.append((request_id, event_data))
    with store._mutex:
        store._require_unlocked()
        with store._connect() as db:
            db.execute("PRAGMA busy_timeout=0")
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            page_size = db.execute("PRAGMA page_size").fetchone()[0]
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM requests LIMIT 1").fetchone():
                raise ValueError("Restore requires an empty store")
            physical, main = store._physical_size()
            if physical + main + (main // page_size + 1) * 32 + 32768 + total * 3 + 65536 > store.max_bytes:
                raise ValueError("Restore exceeds storage limit")
            key_id = max(store._keys)
            key = store._keys[key_id]
            for request_id, events in prepared:
                db.execute("INSERT INTO requests(request_id, created, state) VALUES (?, ?, ?)",
                           (request_id, time.time(), "부분"))
                opened = json.dumps({"input": None, "redactions": 0, "restored_from_export": True}).encode()
                marker = json.dumps({"partial": True, "failed": False, "uncertain": False,
                                     "omitted_bytes": 0, "omitted_events": 0}).encode()
                previous = b""
                for seq, (kind, raw) in enumerate([("opened", opened), *events, ("finished", marker)]):
                    nonce = os.urandom(12)
                    ciphertext = AESGCM(key).encrypt(nonce, raw, _aad(request_id, seq, kind, previous))
                    db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
                               (request_id, seq, kind, key_id, nonce, ciphertext))
                    previous = ciphertext[-16:]
    return len(prepared)
