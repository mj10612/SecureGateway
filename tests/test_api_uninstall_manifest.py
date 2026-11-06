"""API uninstall recovers its own manifest even after config loss."""
from click.testing import CliRunner
import pytest

from secure_gateway.cli import main
from secure_gateway import gateway_install
from secure_gateway.gateway_install import installation_path
from secure_gateway.xai_install import install_api


@pytest.mark.parametrize("filename", ["config.json", "custom.json"])
@pytest.mark.parametrize("original", [None, b'# original settings\ndefault_model = "personal"\n'])
def test_missing_config_restores_own_manifest(tmp_path, monkeypatch, filename, original):
    home = tmp_path / "Grok home"
    home.mkdir()
    settings = home / "config.toml"
    login = home / "auth.json"
    login.write_bytes(b'{"token":"synthetic-login"}')
    if original is not None:
        settings.write_bytes(original)
    config = tmp_path / "state with spaces" / filename
    install_api(config, "grok-fixture", grok_dir=home)
    manifest = installation_path(config)
    other = config.parent / "unrelated.json.installation.json"
    other.write_bytes(b"unrelated manifest")
    config.unlink()
    calls = []
    stop = gateway_install.stop_gateway
    def record_stop(path):
        calls.append(path)
        return stop(path)
    monkeypatch.setattr(gateway_install, "stop_gateway", record_stop)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["gateway", "api-uninstall", "--config", str(config.relative_to(tmp_path))])
    assert result.exit_code == 0, result.output
    assert "Grok settings restored" in result.output
    assert "Configuration is missing" in result.output
    assert "API gateway stopped" not in result.output
    assert calls == [config.resolve()]
    assert not manifest.exists() and not config.exists()
    if original is None:
        assert not settings.exists()
    else:
        assert settings.read_bytes() == original
    assert other.read_bytes() == b"unrelated manifest"
    assert login.read_bytes() == b'{"token":"synthetic-login"}'


@pytest.mark.parametrize("filename", ["config.json", "custom.json"])
def test_no_config_or_manifest_is_nonmutating_noop(tmp_path, filename):
    config = tmp_path / filename
    before = set(tmp_path.iterdir())
    result = CliRunner().invoke(main, ["gateway", "api-uninstall", "--config", str(config)])
    assert result.exit_code == 0 and "No active gateway installation" in result.output
    assert set(tmp_path.iterdir()) == before


def test_custom_config_with_user_edits_is_not_overwritten(tmp_path):
    home = tmp_path / "grok"
    home.mkdir()
    config = tmp_path / "custom.json"
    install_api(config, "grok-fixture", grok_dir=home)
    settings = home / "config.toml"
    edited = settings.read_bytes() + b"\n# user edit\n"
    settings.write_bytes(edited)
    config.unlink()
    result = CliRunner().invoke(main, ["gateway", "api-uninstall", "--config", str(config)])
    assert result.exit_code != 0 and "refusing to overwrite" in result.output
    assert settings.read_bytes() == edited
    assert installation_path(config).exists()

@pytest.mark.parametrize("filename", ["config.json", "custom.json"])
def test_existing_config_still_restores_settings(tmp_path, monkeypatch, filename):
    home = tmp_path / "grok"
    home.mkdir()
    config = tmp_path / filename
    install_api(config, "grok-fixture", grok_dir=home)
    stopped = []
    monkeypatch.setattr(gateway_install, "stop_gateway", lambda path: stopped.append(path) or True)
    result = CliRunner().invoke(main, ["gateway", "api-uninstall", "--config", str(config)])
    assert result.exit_code == 0, result.output
    assert stopped == [config.resolve()]
    assert "API gateway stopped" in result.output
    assert not (home / "config.toml").exists()
    assert not installation_path(config).exists()


def test_missing_config_rejects_malformed_custom_manifest(tmp_path):
    config = tmp_path / "custom.json"
    manifest = installation_path(config)
    manifest.write_bytes(b"{broken")
    result = CliRunner().invoke(main, ["gateway", "api-uninstall", "--config", str(config)])
    assert result.exit_code != 0 and "Invalid installation manifest" in result.output
    assert manifest.read_bytes() == b"{broken"


@pytest.mark.parametrize("filename", ["config.json", "custom.json"])
@pytest.mark.parametrize("missing_config", [False, True])
@pytest.mark.parametrize("original", [None, b'# original settings\ndefault_model = "personal"\n'])
def test_deleted_host_settings_are_not_resurrected(tmp_path, monkeypatch, filename, missing_config, original):
    home = tmp_path / "Grok home"
    home.mkdir()
    settings = home / "config.toml"
    if original is not None:
        settings.write_bytes(original)
    login = home / "auth.json"
    login.write_bytes(b'{"token":"synthetic-login"}')
    unrelated_host = home / "other.toml"
    unrelated_host.write_bytes(b'# user settings\n')
    config = tmp_path / "state" / filename
    install_api(config, "grok-fixture", grok_dir=home)
    config_bytes = config.read_bytes()
    settings.unlink()
    if missing_config:
        config.unlink()
    manifest = installation_path(config)
    unrelated_manifest = config.parent / "unrelated.json.installation.json"
    unrelated_manifest.write_bytes(b"unrelated manifest")
    stopped = []
    monkeypatch.setattr(gateway_install, "stop_gateway", lambda path: stopped.append(path) or True)

    command = ["gateway", "api-uninstall", "--config", str(config)]
    result = CliRunner().invoke(main, command)
    assert result.exit_code == 0, result.output
    assert not settings.exists()
    assert not manifest.exists()
    assert stopped == [config.resolve()]
    if missing_config:
        assert not config.exists()
    else:
        assert config.read_bytes() == config_bytes
    assert login.read_bytes() == b'{"token":"synthetic-login"}'
    assert unrelated_host.read_bytes() == b'# user settings\n'
    assert unrelated_manifest.read_bytes() == b"unrelated manifest"

    repeated = CliRunner().invoke(main, command)
    assert repeated.exit_code == 0, repeated.output
    assert "No active gateway installation" in repeated.output
    assert stopped == [config.resolve()]
    assert not settings.exists() and not manifest.exists()


@pytest.mark.parametrize("missing_config", [False, True])
def test_deleted_host_does_not_bypass_manifest_validation(tmp_path, monkeypatch, missing_config):
    home = tmp_path / "grok"
    config = tmp_path / "custom.json"
    install_api(config, "grok-fixture", grok_dir=home)
    settings = home / "config.toml"
    settings.unlink()
    if missing_config:
        config.unlink()
    manifest = installation_path(config)
    manifest.write_bytes(b"{broken")
    stopped = []
    monkeypatch.setattr(gateway_install, "stop_gateway", lambda path: stopped.append(path) or True)
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    result = CliRunner().invoke(main, ["gateway", "api-uninstall", "--config", str(config)])
    assert result.exit_code != 0
    assert "Invalid installation manifest" in result.output
    assert not stopped
    assert not settings.exists()
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


def test_force_clean_api_install_with_deleted_host_does_not_restore_backup(tmp_path, monkeypatch):
    home = tmp_path / "grok"
    home.mkdir()
    settings = home / "config.toml"
    settings.write_bytes(b'default_model = "personal"\n')
    config = tmp_path / "custom.json"
    install_api(config, "grok-fixture", grok_dir=home)
    settings.unlink()
    monkeypatch.setattr(gateway_install, "stop_gateway", lambda path: True)
    result = CliRunner().invoke(main, ["gateway", "uninstall", "--force-clean", "--config", str(config)])
    assert result.exit_code == 0, result.output
    assert not settings.exists()
    assert not installation_path(config).exists()


def test_deleted_host_cleanup_can_retry_after_manifest_removal_failure(tmp_path, monkeypatch):
    from pathlib import Path

    home = tmp_path / "grok"
    home.mkdir()
    settings = home / "config.toml"
    settings.write_bytes(b'default_model = "personal"\n')
    config = tmp_path / "custom.json"
    install_api(config, "grok-fixture", grok_dir=home)
    settings.unlink()
    manifest = installation_path(config)
    monkeypatch.setattr(gateway_install, "stop_gateway", lambda path: True)
    unlink = Path.unlink

    def fail_manifest(path, *args, **kwargs):
        if path == manifest:
            raise OSError("manifest removal interrupted")
        return unlink(path, *args, **kwargs)

    command = ["gateway", "api-uninstall", "--config", str(config)]
    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", fail_manifest)
        result = CliRunner().invoke(main, command)
    assert result.exit_code != 0 and "manifest removal interrupted" in result.output
    assert manifest.exists() and not settings.exists()
    repeated = CliRunner().invoke(main, command)
    assert repeated.exit_code == 0, repeated.output
    assert not manifest.exists() and not settings.exists()
