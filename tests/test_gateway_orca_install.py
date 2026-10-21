"""Canonical config mirroring and truthful gateway installation diagnostics."""

import json
import shutil

from click.testing import CliRunner
import tomlkit

from secure_gateway.cli import main
from secure_gateway import gateway_install


def test_orca_sync_retains_gateway_and_uninstall_restores_both(tmp_path, monkeypatch):
    canonical = tmp_path / ".codex"
    managed = tmp_path / "orca/codex-accounts/account/home"
    canonical.mkdir()
    managed.mkdir(parents=True)
    (managed / ".orca-managed-home").write_text("account")
    raw = b'# personal settings\nmodel = "existing-model"\n'
    for home in (canonical, managed):
        (home / "config.toml").write_bytes(raw)
        (home / "auth.json").write_bytes(b"unchanged-login")
    monkeypatch.setattr(gateway_install.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("CODEX_HOME", str(managed))
    monkeypatch.setenv("ORCA_CODEX_HOME", str(managed))
    monkeypatch.setattr(gateway_install, "stop_gateway", lambda _: False)
    config = tmp_path / "gateway/config.json"
    gateway_install.install_gateway(
        config, agent="codex", startup_path=tmp_path / "startup.vbs",
    )
    # Reproduce Orca's canonical-to-managed config synchronization.
    shutil.copyfile(canonical / "config.toml", managed / "config.toml")
    for home in (canonical, managed):
        value = tomlkit.parse((home / "config.toml").read_text())
        assert value["model_provider"] == "secure_gateway_subscription"
        assert value["model"] == "existing-model"
        assert (home / "auth.json").read_bytes() == b"unchanged-login"
    assert gateway_install.changed_installation_files(config) == []
    gateway_install.uninstall_gateway(config)
    for home in (canonical, managed):
        assert (home / "config.toml").read_bytes() == raw


def test_explicit_or_unmarked_home_does_not_modify_canonical(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setenv("ORCA_CODEX_HOME", str(tmp_path))
    assert gateway_install.codex_settings_homes() == [tmp_path]
    (tmp_path / ".orca-managed-home").write_text("account")
    assert gateway_install.codex_settings_homes(tmp_path) == [tmp_path]
    monkeypatch.setenv("ORCA_CODEX_HOME", str(tmp_path / "different"))
    assert gateway_install.codex_settings_homes() == [tmp_path]


def test_status_detects_overwritten_settings_without_printing_contents(tmp_path, monkeypatch):
    config = tmp_path / "gateway/config.json"
    home = tmp_path / "codex"
    gateway_install.install_gateway(
        config, agent="codex", codex_dir=home,
        startup_path=tmp_path / "startup.vbs",
    )
    monkeypatch.setattr(gateway_install, "healthy", lambda _: True)
    runner = CliRunner()
    result = runner.invoke(main, ["gateway", "status", "--config", str(config)])
    assert result.exit_code == 0
    assert "installed settings verified" in result.output
    assert "does not prove inference" in result.output
    (home / "config.toml").write_text('model = "private-model-name"\n')
    result = runner.invoke(main, ["gateway", "status", "--config", str(config)])
    assert result.exit_code == 1
    assert "routing is unverified" in result.output
    assert "private-model-name" not in result.output
    assert json.loads(config.read_text())["token"] not in result.output


def test_status_distinguishes_untracked_running_daemon(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"port": 38117, "token": "t" * 32}))
    monkeypatch.setattr(gateway_install, "healthy", lambda _: True)
    result = CliRunner().invoke(main, ["gateway", "status", "--config", str(config)])
    assert result.exit_code == 0
    assert "no installation record" in result.output
    assert "installed settings verified" not in result.output


def test_status_refuses_missing_installed_file(tmp_path, monkeypatch):
    config = tmp_path / "gateway/config.json"
    startup = tmp_path / "startup.vbs"
    gateway_install.install_gateway(
        config, agent="codex", codex_dir=tmp_path / "codex", startup_path=startup,
    )
    startup.unlink()
    monkeypatch.setattr(gateway_install, "healthy", lambda _: True)
    result = CliRunner().invoke(main, ["gateway", "status", "--config", str(config)])
    assert result.exit_code == 1
    assert str(startup) in result.output


def test_orca_install_rejects_canonical_user_edits_without_partial_update(tmp_path, monkeypatch):
    canonical = tmp_path / ".codex"
    managed = tmp_path / "account/home"
    canonical.mkdir()
    managed.mkdir(parents=True)
    (managed / ".orca-managed-home").write_text("account")
    monkeypatch.setattr(gateway_install.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("CODEX_HOME", str(managed))
    monkeypatch.setenv("ORCA_CODEX_HOME", str(managed))
    config = tmp_path / "gateway/config.json"
    startup = tmp_path / "startup.vbs"
    gateway_install.install_gateway(config, agent="codex", startup_path=startup)
    (canonical / "config.toml").write_text('model = "new-personal-choice"\n')
    paths = [canonical / "config.toml", managed / "config.toml", config,
             config.parent / "installation.json", startup]
    before = [path.read_bytes() for path in paths]
    import pytest
    with pytest.raises(ValueError, match="settings changed"):
        gateway_install.install_gateway(config, agent="codex", startup_path=startup)
    assert [path.read_bytes() for path in paths] == before
