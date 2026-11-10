"""Authenticated local storage for explicitly approved experimental corrections."""
from __future__ import annotations

import json
import math
from pathlib import Path

from secure_gateway.encrypted_session import SnapshotEncryption, decrypt_snapshot_bytes, session_file_lock
from secure_gateway.gateway_install import atomic_bytes
from secure_gateway.mapping_budget import MAX_SNAPSHOT_FILE_BYTES

_FIELDS = {"term", "project", "language", "source", "policy_version", "created_at", "expires_at", "revoked"}


def validate_record(record: dict) -> None:
    """Validate a bounded, versioned local correction record."""
    if (not isinstance(record, dict) or set(record) != _FIELDS
            or not isinstance(record["term"], str) or not 1 <= len(record["term"]) <= 256
            or not isinstance(record["project"], str) or not 1 <= len(record["project"]) <= 256
            or record["language"] not in {"en", "ko"} or record["source"] != "explicit-local-correction"
            or type(record["policy_version"]) is not int or record["policy_version"] < 1
            or type(record["created_at"]) not in {int, float} or not math.isfinite(record["created_at"])
            or type(record["expires_at"]) not in {int, float} or not math.isfinite(record["expires_at"])
            or record["expires_at"] <= record["created_at"] or type(record["revoked"]) is not bool):
        raise ValueError("Invalid correction record")


def _load(path: Path, password: str) -> list[dict]:
    if not path.exists():
        return []
    with path.open("rb") as stream:
        data = stream.read(MAX_SNAPSHOT_FILE_BYTES + 1)
    records = json.loads(decrypt_snapshot_bytes(data, password))
    if not isinstance(records, list) or len(records) > 256:
        raise ValueError("Invalid correction storage")
    for record in records:
        validate_record(record)
    return records


def load_records(path: Path, password: str) -> list[dict]:
    """Load authenticated correction records under the shared file lock."""
    with session_file_lock(path):
        return _load(path, password)


def save_record(path: Path, password: str, record: dict) -> None:
    """Atomically append one approved correction using authenticated encryption."""
    validate_record(record)
    with session_file_lock(path):
        records = _load(path, password)
        if len(records) >= 256:
            raise ValueError("Correction limit reached")
        identity = (record["project"], record["language"], record["term"])
        if any((item["project"], item["language"], item["term"]) == identity for item in records):
            raise ValueError("Correction already exists")
        records.append(record)
        payload = json.dumps(records, ensure_ascii=False).encode("utf-8")
        atomic_bytes(path, SnapshotEncryption(password).encrypt(payload))


def revoke_record(path: Path, password: str, project: str, language: str, term: str) -> None:
    """Revoke an existing rule without removing its audit metadata."""
    with session_file_lock(path):
        records = _load(path, password)
        matches = [record for record in records if (record["project"], record["language"], record["term"])
                   == (project, language, term)]
        if len(matches) != 1:
            raise ValueError("Correction not found")
        matches[0]["revoked"] = True
        atomic_bytes(path, SnapshotEncryption(password).encrypt(json.dumps(records, ensure_ascii=False).encode("utf-8")))
