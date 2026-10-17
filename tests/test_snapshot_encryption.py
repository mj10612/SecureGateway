"""An owner may derive once while every saved ciphertext remains independent."""

import json
import math
import sys
import time

import pytest
from click.testing import CliRunner

from secure_mcp.cli import main
from secure_mcp import encrypted_session
from secure_mcp.encrypted_session import (
    SessionExpiredError,
    SnapshotEncryption,
    load_session,
    save_session,
)
from secure_mcp.session import PrivacySession


def test_encryption_context_derives_once_and_snapshots_decrypt_after_restart(
    tmp_path, monkeypatch
):
    original_cipher = encrypted_session._cipher
    derivations = []

    def derive(password, salt):
        derivations.append(salt)
        return original_cipher(password, salt)

    monkeypatch.setattr(encrypted_session, "_cipher", derive)
    context = SnapshotEncryption("offline-snapshot-password")
    session = PrivacySession("owner")
    path = tmp_path / "owner.enc"
    save_session(path, session, "offline-snapshot-password", encryption=context)
    first = path.read_bytes()
    save_session(path, session, "offline-snapshot-password", encryption=context)
    assert len(derivations) == 1
    assert path.read_bytes() != first
    assert (
        load_session(path, "offline-snapshot-password", "owner").session_id == "owner"
    )


def test_separate_owners_and_default_writes_have_independent_salts(
    tmp_path, monkeypatch
):
    original_cipher = encrypted_session._cipher
    derivations = []

    def derive(password, salt):
        derivations.append(salt)
        return original_cipher(password, salt)

    monkeypatch.setattr(encrypted_session, "_cipher", derive)
    first = SnapshotEncryption("offline-snapshot-password")
    second = SnapshotEncryption("offline-snapshot-password")
    session = PrivacySession("owner")
    path = tmp_path / "owner.enc"
    for context in (first, second, None, None):
        save_session(path, session, "offline-snapshot-password", encryption=context)
    assert len(derivations) == len(set(derivations)) == 4


@pytest.fixture
def snapshot_payload():
    now = time.time()
    return {
        "version": 2,
        "session_id": "numeric-validation",
        "mode": "content_words",
        "strategy": "bracket",
        "ttl_seconds": 3600,
        "created_at": now,
        "last_accessed": now,
        "total_mask_calls": 0,
        "total_unmask_calls": 0,
        "salt": "offline-numeric-fixture",
        "counters": {},
        "mappings": [],
    }


@pytest.fixture
def write_snapshot(tmp_path):
    password = "offline-snapshot-password"
    encryption = SnapshotEncryption(password)
    path = tmp_path / "numeric.enc"

    def write(payload):
        path.write_bytes(encryption.encrypt(json.dumps(payload).encode()))
        return path, password

    return write


@pytest.mark.parametrize("field", ["created_at", "last_accessed", "ttl_seconds"])
@pytest.mark.parametrize(
    "value",
    [10**1000, -(10**1000), math.nan, math.inf, -math.inf, True, False],
    ids=[
        "huge",
        "negative-huge",
        "nan",
        "infinity",
        "negative-infinity",
        "true",
        "false",
    ],
)
def test_invalid_snapshot_numbers_are_payload_errors(
    snapshot_payload, write_snapshot, field, value
):
    snapshot_payload[field] = value
    path, password = write_snapshot(snapshot_payload)
    with pytest.raises(ValueError, match=r"^Invalid encrypted session payload\.$"):
        load_session(path, password)


@pytest.mark.parametrize("field", ["created_at", "last_accessed", "ttl_seconds"])
def test_cli_handles_oversized_snapshot_numbers(
    snapshot_payload, write_snapshot, field
):
    snapshot_payload[field] = 10**1000
    path, password = write_snapshot(snapshot_payload)
    original = path.read_bytes()
    result = CliRunner().invoke(
        main,
        [
            "unmask",
            "x",
            "--session-id",
            snapshot_payload["session_id"],
            "--session-file",
            str(path),
            "--session-password",
            password,
            "--json-output",
        ],
    )
    assert result.exit_code == 1
    assert result.output == "Error: Invalid encrypted session payload.\n"
    assert isinstance(result.exception, SystemExit)
    assert path.read_bytes() == original


@pytest.mark.parametrize("ttl", [math.nextafter(0.0, 1.0), 86400])
def test_snapshot_ttl_boundaries_remain_valid(
    snapshot_payload, write_snapshot, monkeypatch, ttl
):
    snapshot_payload["ttl_seconds"] = ttl
    monkeypatch.setattr(
        "secure_mcp.session.time.time", lambda: snapshot_payload["last_accessed"]
    )
    path, password = write_snapshot(snapshot_payload)
    assert load_session(path, password).ttl_seconds == ttl


@pytest.mark.parametrize("value", [0, sys.float_info.max, int(sys.float_info.max)])
def test_finite_timestamp_boundaries_remain_valid(
    snapshot_payload, write_snapshot, monkeypatch, value
):
    snapshot_payload["created_at"] = value
    snapshot_payload["last_accessed"] = value
    path, password = write_snapshot(snapshot_payload)
    monkeypatch.setattr("secure_mcp.session.time.time", lambda: value)
    assert load_session(path, password).created_at == value


def test_expired_snapshot_keeps_specific_error(snapshot_payload, write_snapshot):
    snapshot_payload["last_accessed"] = time.time() - 86401
    path, password = write_snapshot(snapshot_payload)
    with pytest.raises(SessionExpiredError, match="Session file has expired"):
        load_session(path, password)
