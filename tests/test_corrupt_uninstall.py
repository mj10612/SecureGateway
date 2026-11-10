"""A corrupt runtime configuration must not strand owned host settings."""

import json
import logging
from contextlib import contextmanager
from pathlib import Path
from threading import Thread

import pytest
from click.testing import CliRunner

from secure_gateway import gateway_install as g
from secure_gateway.cli import main
from secure_gateway.xai_install import install_api


@contextmanager
def _uninstall_warning():
    class Capture(logging.Handler):
        def __init__(self):
            super().__init__()
            self.events = []

        def emit(self, record):
            self.events.append(record.getMessage())

    handler = Capture()
    logger = logging.getLogger("secure_gateway.gateway_install")
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        assert "invalid_config_uninstall_daemon_not_stopped" in handler.events


BROKEN_CONFIGS = [b'{"port":', b'[]', b'null', b'{"port": 1, "token": "x"}',
                  b'{"port": 38117, "token": 123}', b'\xff']


@pytest.fixture
def installed(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / ".claude"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    config = tmp_path / "state/config.json"
    host = tmp_path / ".claude/settings.json"
    host.parent.mkdir()
    original = b'{"theme":"personal"}\n'
    host.write_bytes(original)
    startup = tmp_path / "startup"
    g.install_gateway(config, agent="claude", claude_dir=host.parent, startup_path=startup)
    return config, host, startup, original


@pytest.mark.parametrize("broken", BROKEN_CONFIGS)
@pytest.mark.parametrize("force_clean", [False, True])
def test_corrupt_config_does_not_block_owned_restore(installed, monkeypatch, broken, force_clean):
    config, host, startup, original = installed
    config.write_bytes(broken)
    monkeypatch.setattr(g, "stop_gateway", lambda _: pytest.fail("Cannot authenticate a corrupt configuration"))
    with _uninstall_warning():
        assert g.uninstall_gateway(config, force_clean=force_clean)
    assert host.read_bytes() == original
    assert not startup.exists() and not g.installation_path(config).exists()
    assert config.read_bytes() == broken


def test_force_clean_corrupt_config_without_manifest(installed):
    config, host, _, _ = installed
    g.installation_path(config).unlink()
    config.write_bytes(b'{"port":')
    with _uninstall_warning():
        assert g.uninstall_gateway(config, force_clean=True)
    assert "ANTHROPIC_BASE_URL" not in host.read_text()
    assert json.loads(host.read_text())["theme"] == "personal"


def test_corrupt_config_does_not_discover_untracked_instances(installed, tmp_path):
    config, _, _, _ = installed
    foreign = tmp_path / ".codex/config.toml"
    g.install_gateway(tmp_path / "foreign/config.json", agent="codex", port=39118,
                      codex_dir=foreign.parent, startup_path=tmp_path / "foreign-startup")
    before = foreign.read_bytes()
    config.write_bytes(b'[]')
    with _uninstall_warning():
        g.uninstall_gateway(config, force_clean=True)
    assert foreign.read_bytes() == before


def test_legacy_corrupt_config_preserves_edits_without_trusted_identity(installed):
    config, host, startup, _ = installed
    manifest = g.installation_path(config)
    value = json.loads(manifest.read_text())
    value.pop("gateway", None)
    manifest.write_text(json.dumps(value))
    host.write_text(host.read_text() + "\n ")
    config.write_bytes(b'[]')
    before = host.read_bytes(), startup.read_bytes(), g.installation_path(config).read_bytes()
    with pytest.raises(ValueError, match="refusing to overwrite"):
        g.uninstall_gateway(config)
    assert before == (host.read_bytes(), startup.read_bytes(), g.installation_path(config).read_bytes())


def test_corrupt_config_merges_edits_with_recorded_identity(installed):
    config, host, _, _ = installed
    value = json.loads(host.read_text())
    value["theme"] = "changed"
    host.write_text(json.dumps(value))
    config.write_bytes(b'[]')
    with _uninstall_warning():
        assert g.uninstall_gateway(config)
    assert json.loads(host.read_text()) == {"theme": "changed"}


def test_corrupt_config_restore_failure_can_retry(installed, monkeypatch):
    config, host, _, original = installed
    config.write_bytes(b'[]')
    write = g.atomic_bytes

    def fail_host(path, data):
        if path == host:
            raise OSError("restore interruption")
        return write(path, data)

    with monkeypatch.context() as patch:
        patch.setattr(g, "atomic_bytes", fail_host)
        with _uninstall_warning(), pytest.raises(OSError, match="restore interruption"):
            g.uninstall_gateway(config)
    with _uninstall_warning():
        assert g.uninstall_gateway(config)
    assert host.read_bytes() == original


def test_corrupt_config_api_manifest_restore_is_scoped(tmp_path):
    config = tmp_path / "api/config.json"
    home = tmp_path / "grok"
    install_api(config, "grok-fixture", grok_dir=home)
    config.write_bytes(b'[]')
    with _uninstall_warning():
        assert g.uninstall_gateway(config)
    assert not (home / "config.toml").exists()


def test_cli_reports_uncertain_daemon_stop(installed):
    config, host, _, _ = installed
    config.write_bytes(b'[]')
    with _uninstall_warning():
        result = CliRunner().invoke(main, ["gateway", "uninstall", "--config", str(config)])
    assert result.exit_code == 0, result.output
    assert "X-SecureGateway-Token" not in host.read_text()


def test_corrupt_config_does_not_kill_running_gateway(tmp_path):
    from secure_gateway.gateway import PrivacyGateway

    token = "synthetic-gateway-token-" + "x" * 32
    server = PrivacyGateway(("127.0.0.1", 0), token)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = tmp_path / "state/config.json"
    host = tmp_path / "claude/settings.json"
    try:
        valid = {"port": server.server_port, "token": token}
        config.parent.mkdir()
        config.write_text(json.dumps(valid))
        g.install_gateway(config, agent="claude", port=server.server_port,
                          claude_dir=host.parent, startup_path=tmp_path / "startup")
        assert g.healthy(valid)
        config.write_bytes(b'{"port":')
        with _uninstall_warning():
            assert g.uninstall_gateway(config)
        assert g.healthy(valid)
        assert not host.exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("identity", [[], {"port": 38117, "token": "x" * 32, "mode": []},
                                      {"port": 1, "token": "x" * 32, "mode": "api"}])
def test_invalid_recorded_identity_blocks_all_writes(installed, identity):
    config, host, startup, _ = installed
    manifest = g.installation_path(config)
    value = json.loads(manifest.read_text())
    value["gateway"] = identity
    manifest.write_text(json.dumps(value))
    config.write_bytes(b'[]')
    before = host.read_bytes(), startup.read_bytes(), manifest.read_bytes()
    with pytest.raises(ValueError, match="Invalid installation manifest"):
        g.uninstall_gateway(config, force_clean=True)
    assert before == (host.read_bytes(), startup.read_bytes(), manifest.read_bytes())
