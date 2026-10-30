"""Offline exports exercise the real CLI and persistent read-only audit path."""
from contextlib import closing
import json
from pathlib import Path
import shutil
import subprocess

from click.testing import CliRunner
import pytest

from secure_gateway.cli import main
from secure_gateway.gateway_audit import AuditStore


@pytest.fixture
def configured(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"port": 38117, "token": "x" * 32}), encoding="utf-8")
    with closing(AuditStore(tmp_path / "logs.sqlite3")) as store:
        with store.connect() as db:
            db.executemany(
                "INSERT INTO requests(request_id,started_at,agent,provider,subscription,endpoint,destination,status,account_ref,credential_ref) "
                "VALUES (?, '2026-01-01T12:00:00+00:00', 'Codex', 'codex', 'chatgpt_subscription', '/codex/responses', 'secret-destination', 200,'secret-account','secret-credential')",
                ((f"request-{n}",) for n in range(1001)),
            )
    return config


def args(config, output):
    return ["gateway", "audit-export", "--config", str(config), "--since", "2026-01-01T00:00:00Z",
            "--until", "2026-01-02T00:00:00Z", "--output", str(output)]


def snapshot(folder):
    return {str(p.relative_to(folder)): (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.rglob("*") if p.is_file()}


def test_offline_cli_pages_read_only_allowlist(configured, tmp_path):
    before = snapshot(tmp_path)
    output = tmp_path / "export.json"
    result = CliRunner().invoke(main, args(configured, output) + ["--provider", "codex"])
    assert result.exit_code == 0, result.output
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["count"] == 1001
    assert [r["request_id"] for r in data["rows"]] == [f"request-{n}" for n in reversed(range(1001))]
    assert "secret-" not in output.read_text(encoding="utf-8")
    output.unlink()
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("extra", [["--max-rows", "1000"], ["--max-bytes", "100"],
                                  ["--since", "2026-01-01"], ["--until", "2026-03-01T00:00:00Z"],
                                  ["--until", "invalid"], ["--result", "unexpected"]])
def test_offline_failures_publish_no_partial_or_mutation(configured, tmp_path, extra):
    before = snapshot(tmp_path)
    output = tmp_path / "export.json"
    result = CliRunner().invoke(main, args(configured, output) + extra)
    assert result.exit_code != 0
    assert not output.exists()
    assert snapshot(tmp_path) == before


def test_existing_file_missing_database_and_output_errors(configured, tmp_path):
    before = configured.read_bytes()
    assert CliRunner().invoke(main, args(configured, configured)).exit_code != 0
    assert configured.read_bytes() == before
    output = tmp_path / "missing" / "export.json"
    assert CliRunner().invoke(main, args(configured, output)).exit_code != 0
    database = tmp_path / "logs.sqlite3"
    database.unlink()
    before_tree = snapshot(tmp_path)
    assert CliRunner().invoke(main, args(configured, tmp_path / "out.json")).exit_code != 0
    assert snapshot(tmp_path) == before_tree


def test_cli_date_recovery_actual_dashboard():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for actual dashboard script")
    result = subprocess.run([node, str(Path(__file__).with_name("test_admin_date_recovery.js"))],
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_failed_publication_leaves_no_file_or_temp(configured, tmp_path, monkeypatch):
    before = snapshot(tmp_path)
    def denied(*args):
        raise PermissionError("Synthetic publication denied")
    monkeypatch.setattr("secure_gateway.cli.os.link", denied)
    result = CliRunner().invoke(main, args(configured, tmp_path / "out.json"))
    assert result.exit_code != 0
    assert "denied" in result.output
    assert snapshot(tmp_path) == before
