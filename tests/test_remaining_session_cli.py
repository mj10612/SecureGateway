"""Resource policies and configuration boundaries from issues 248/257/258."""
import json
import io
import time

import pytest
from click.testing import CliRunner

from secure_gateway import cli
from secure_gateway.encrypted_session import SnapshotEncryption, load_session, save_session
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.gateway import GatewaySession, PrivacyGateway
from secure_gateway.models import SurrogateStrategy
from secure_gateway.session import PrivacySession


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_mapping_limit_survives_snapshot_and_continued_allocation(tmp_path, strategy):
    session = PrivacySession("limited", strategy=strategy, mapping_limit=2)
    engine = MaskingEngine()
    def mask(s, text):
        return engine.mask_text(text, s.session_id, s.generator,
                                s.forward_store, s.reverse_store).masked_text
    first = mask(session, "PrivateOne")
    path = tmp_path / "limited.enc"
    save_session(path, session, "synthetic-password")
    loaded = load_session(path, "synthetic-password")
    assert loaded.generator.max_mappings == 2
    second = mask(loaded, "PrivateTwo")
    for s in [session, loaded]:
        if s is session:
            mask(s, "PrivateTwo")
        with pytest.raises(ValueError, match="Mapping limit"):
            mask(s, "PrivateThree")
    assert engine.unmask(first + " " + second, loaded.session_id,
                         loaded.reverse_store, strategy, strict=True).unmasked_text == "PrivateOne PrivateTwo"
    save_session(path, loaded, "synthetic-password")
    assert load_session(path, "synthetic-password").generator.max_mappings == 2


def snapshot_payload():
    return {"version": 2, "session_id": "limited", "mode": "content_words",
            "strategy": "bracket", "ttl_seconds": 3600, "salt": "synthetic",
            "created_at": time.time(), "last_accessed": time.time(),
            "total_mask_calls": 0, "total_unmask_calls": 0,
            "mappings": [], "counters": {}}


@pytest.mark.parametrize("limit", [True, False, 0, -1, 1.5, "2", None, [], {}])
def test_invalid_snapshot_mapping_limit_rejected(tmp_path, limit):
    payload = snapshot_payload()
    payload["mapping_limit"] = limit
    path = tmp_path / "invalid.enc"
    path.write_bytes(SnapshotEncryption("synthetic-password").encrypt(json.dumps(payload).encode()))
    with pytest.raises(ValueError, match="Invalid encrypted session payload"):
        load_session(path, "synthetic-password")


@pytest.mark.parametrize("version", [1, 2])
def test_legacy_snapshots_keep_documented_default_limit(tmp_path, version):
    payload = snapshot_payload()
    payload["version"] = version
    path = tmp_path / "legacy.enc"
    path.write_bytes(SnapshotEncryption("synthetic-password").encrypt(json.dumps(payload).encode()))
    assert load_session(path, "synthetic-password").generator.max_mappings == 100_000


def test_snapshot_cannot_contain_more_mappings_than_its_limit(tmp_path):
    session = PrivacySession("limited")
    engine = MaskingEngine()
    engine.mask_text("PrivateOne PrivateTwo", session.session_id, session.generator,
                     session.forward_store, session.reverse_store)
    payload = snapshot_payload()
    payload["mapping_limit"] = 1
    payload["mappings"] = [m.model_dump(mode="json") for m in session.forward_store.values()]
    path = tmp_path / "over-limit.enc"
    path.write_bytes(SnapshotEncryption("synthetic-password").encrypt(json.dumps(payload).encode()))
    with pytest.raises(ValueError, match="Invalid encrypted session payload"):
        load_session(path, "synthetic-password")


def test_gateway_cannot_weaken_supplied_snapshot_policy(tmp_path):
    session = PrivacySession("gateway", mapping_limit=1)
    gateway = GatewaySession(session, mapping_limit=2)
    masked = gateway.mask("PrivateOne")
    with pytest.raises(ValueError, match="Mapping limit"):
        gateway.mask("PrivateTwo")
    path = tmp_path / "gateway.enc"
    save_session(path, session, "synthetic-password")
    loaded = load_session(path, "synthetic-password")
    assert loaded.generator.max_mappings == 1
    assert GatewaySession(loaded, mapping_limit=2).restore(masked) == "PrivateOne"


def test_gateway_creates_and_persists_its_configured_session_limit(tmp_path):
    gateway = GatewaySession(mapping_limit=200_000)
    assert gateway.session.generator.max_mappings == 200_000
    masked = gateway.mask("PrivateOne PrivateTwo")
    path = tmp_path / "gateway.enc"
    save_session(path, gateway.session, "synthetic-password")
    loaded = load_session(path, "synthetic-password")
    assert loaded.generator.max_mappings == 200_000
    smaller = GatewaySession(loaded, mapping_limit=1)
    assert smaller.restore(masked) == "PrivateOne PrivateTwo"
    with pytest.raises(ValueError, match="Mapping limit"):
        smaller.mask("PrivateThree")


@pytest.mark.parametrize("stdin", [False, True])
@pytest.mark.parametrize("size", [4, 5])
def test_unmask_input_reader_uses_requested_limit(tmp_path, monkeypatch, stdin, size):
    # Shrink the masking policy to prove the restore policy is independent,
    # without allocating multi-megabyte stdout in every matrix job.
    monkeypatch.setattr(cli.engine, "max_input_bytes", 2)
    path = tmp_path / "input.txt"
    path.write_bytes(b" " * size)
    snapshot = tmp_path / "session.enc"
    save_session(snapshot, PrivacySession("cli_session"), "synthetic-password")
    args = ["unmask", "--restore-input-limit", "4", "--restore-output-limit", "4", "--json-output",
            "--session-file", str(snapshot), "--session-password", "synthetic-password"]
    if not stdin:
        args += ["--input-file", str(path)]
    result = CliRunner().invoke(cli.main, args, input=b" " * size if stdin else None)
    if size == 4:
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["unmasked_text"] == " " * size
    else:
        assert result.exit_code != 0 and "Input size limit" in result.output


@pytest.mark.parametrize("binary", [False, True])
def test_input_reader_does_not_read_past_smaller_restore_limit(monkeypatch, binary):
    calls = []
    class Reader:
        def isatty(self):
            return False
        def read(self, size):
            calls.append(size)
            return b"a" * size if binary else "a" * size
    stream = Reader()
    if binary:
        stream.buffer = stream
    monkeypatch.setattr(cli.sys, "stdin", stream)
    with pytest.raises(cli.click.ClickException, match="Input size"):
        cli._text_input(None, None, max_input_bytes=3)
    assert calls == [4]


def test_huge_restore_budget_uses_bounded_read_sizes(tmp_path):
    class Reader(io.BytesIO):
        def read(self, size=-1):
            assert 0 < size <= 64 * 1024
            return super().read(size)
    assert cli._read_input_bytes(Reader(b"small input"), 2**100) == b"small input"
    path = tmp_path / "input.txt"
    path.write_bytes(b"")
    snapshot = tmp_path / "session.enc"
    save_session(snapshot, PrivacySession("cli_session"), "synthetic-password")
    result = CliRunner().invoke(cli.main, ["unmask", "--input-file", str(path),
        "--restore-input-limit", str(2**100), "--session-file", str(snapshot),
        "--session-password", "synthetic-password", "--json-output"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["unmasked_text"] == ""


@pytest.mark.parametrize("dialect", [[], {}, None, "invalid", 1])
def test_bad_dialect_is_a_configuration_error_without_partial_start(tmp_path, dialect):
    with pytest.raises(ValueError, match="SQL dialect"):
        GatewaySession(sql_dialect=dialect)
    state = tmp_path / "state"
    with pytest.raises(ValueError, match="SQL dialect"):
        PrivacyGateway(("127.0.0.1", 0), "t" * 32, sql_dialect=dialect, state_dir=state)
    assert not state.exists()
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"port": 38167, "token": "t" * 32, "sql_dialect": dialect}), encoding="utf-8")
    result = CliRunner().invoke(cli.main, ["gateway", "run", "--config", str(config)])
    assert result.exit_code == 1
    assert "SQL dialect" in result.output and "Traceback" not in result.output


@pytest.mark.parametrize("dialect", ["sqlite", "standard", "postgresql"])
def test_valid_dialect_still_accepted(dialect):
    assert GatewaySession(sql_dialect=dialect).sql_dialect == dialect
