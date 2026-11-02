"""Diagnostics must describe the allocator policy after encrypted restart."""
import json
from threading import Thread
import time

from click.testing import CliRunner
import pytest

from secure_gateway.cli import main
from secure_gateway.gateway import PrivacyGateway
from secure_gateway.encrypted_session import save_session

TOKEN = "synthetic-diagnostics-token-" + "x" * 16


def seed_snapshot(path, limit):
    with PrivacyGateway(("127.0.0.1", 0), TOKEN, state_dir=path, mapping_limit=limit) as gateway:
        session = gateway.get_session("codex")
        session._mask_source("privateFirst = 7", "python")
        gateway.save("codex", session)


@pytest.mark.parametrize(("saved", "configured"), [(1, 3), (3, 1), (2, 2)])
def test_restarted_diagnostics_matches_actual_allocation_limit(tmp_path, saved, configured):
    seed_snapshot(tmp_path, saved)
    with PrivacyGateway(("127.0.0.1", 0), TOKEN, state_dir=tmp_path, mapping_limit=configured) as gateway:
        session = gateway.get_session("codex")
        effective = min(saved, configured)
        report = gateway.session_diagnostics()
        assert report["providers"]["codex"]["mapping_limit"] == effective
        assert report["providers"]["codex"]["mapping_count"] == 1
        assert "privateFirst" not in json.dumps(report) and TOKEN not in json.dumps(report)
        for n in range(1, effective):
            session._mask_source(f"privateNext{n} = 7", "python")
        with pytest.raises(ValueError, match="Mapping limit"):
            session._mask_source("privateOverflow = 7", "python")
        assert gateway.session_diagnostics()["providers"]["codex"]["mapping_count"] == effective


@pytest.mark.parametrize("transition", ["reset", "expiry"])
def test_new_session_after_transition_reports_configured_limit(tmp_path, transition):
    seed_snapshot(tmp_path, 1)
    with PrivacyGateway(("127.0.0.1", 0), TOKEN, state_dir=tmp_path, mapping_limit=3) as gateway:
        session = gateway.get_session("codex")
        if transition == "reset":
            gateway.reset("codex")
        else:
            session.session.last_accessed = time.time() - 90000
            save_session(tmp_path / "codex-symbols-v2.enc", session.session, TOKEN)
            assert gateway.session_diagnostics()["providers"]["codex"]["expired"] is True
        fresh = gateway.get_session("codex")
        assert fresh is not session
        report = gateway.session_diagnostics()["providers"]["codex"]
        assert report["mapping_limit"] == 3 and report["mapping_count"] == 0
        assert report["expired"] is False


def test_cli_diagnostics_exposes_effective_limit_over_authenticated_api(tmp_path):
    state = tmp_path / "sessions"
    seed_snapshot(state, 1)
    with PrivacyGateway(("127.0.0.1", 0), TOKEN, state_dir=state, mapping_limit=100000) as gateway:
        # Unloaded providers still report the configured limit for a new session.
        assert gateway.session_diagnostics()["providers"]["codex"]["mapping_limit"] == 100000
        gateway.get_session("codex")
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"port": gateway.server_port, "token": TOKEN}), encoding="utf-8")
        worker = Thread(target=gateway.serve_forever, daemon=True)
        worker.start()
        try:
            result = CliRunner().invoke(main, ["gateway", "diagnostics", "--config", str(config)])
            assert result.exit_code == 0, result.output
            report = json.loads(result.output)
            assert report["providers"]["codex"]["mapping_limit"] == 1
            assert TOKEN not in result.output and "privateFirst" not in result.output
        finally:
            gateway.shutdown()
            worker.join(timeout=5)
