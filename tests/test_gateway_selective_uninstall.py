"""Uninstall removes gateway ownership while retaining live host edits."""

import json
import shutil

import pytest
import tomlkit
from click.testing import CliRunner

from secure_gateway import gateway_install as g
from secure_gateway.cli import main


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(g.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    monkeypatch.delenv("ORCA_CODEX_HOME", raising=False)
    monkeypatch.setattr(g, "stop_gateway", lambda _: False)
    codex, claude = tmp_path / ".codex", tmp_path / ".claude"
    codex.mkdir()
    claude.mkdir()
    (codex / "config.toml").write_text('model_provider = "openai"\nforced_login_method = "api"\n')
    (claude / "settings.json").write_text(json.dumps({"env": {
        "ANTHROPIC_BASE_URL": "https://previous.example",
        "ANTHROPIC_CUSTOM_HEADERS": "Other: original",
    }}))
    config = tmp_path / "state/config.json"
    g.install_gateway(config, startup_path=tmp_path / "startup")
    return config, codex / "config.toml", claude / "settings.json"


def test_uninstall_retains_runtime_settings_and_headers(setup):
    config, codex, claude = setup
    codex.write_text(codex.read_text() + '\n[hooks]\nstate = "new"\n[projects."D:/work"]\ntrust_level = "trusted"\n')
    value = json.loads(claude.read_text())
    value["theme"] = "dark"
    value["env"]["ANTHROPIC_CUSTOM_HEADERS"] += "\nAdded: later"
    claude.write_text(json.dumps(value))
    assert g.uninstall_gateway(config)
    restored = tomlkit.parse(codex.read_text())
    assert restored["model_provider"] == "openai"
    assert restored["forced_login_method"] == "api"
    assert restored["hooks"]["state"] == "new"
    assert restored["projects"]["D:/work"]["trust_level"] == "trusted"
    assert "secure_gateway_subscription" not in restored.get("model_providers", {})
    value = json.loads(claude.read_text())
    assert value["theme"] == "dark"
    assert value["env"]["ANTHROPIC_BASE_URL"] == "https://previous.example"
    assert value["env"]["ANTHROPIC_CUSTOM_HEADERS"] == "Other: original\nAdded: later"


def test_uninstall_preserves_user_replaced_owned_values(setup):
    config, codex, claude = setup
    codex.write_text(codex.read_text().replace('model_provider = "secure_gateway_subscription"', 'model_provider = "other"').replace('forced_login_method = "chatgpt"', 'forced_login_method = "api"'))
    value = json.loads(claude.read_text())
    value["env"]["ANTHROPIC_BASE_URL"] = "https://new.example"
    claude.write_text(json.dumps(value))
    g.uninstall_gateway(config)
    assert tomlkit.parse(codex.read_text())["model_provider"] == "other"
    assert json.loads(claude.read_text())["env"]["ANTHROPIC_BASE_URL"] == "https://new.example"


def test_uninstall_cleans_all_synced_orca_accounts(setup, tmp_path):
    config, codex, _ = setup
    paths = []
    for root in (tmp_path / "AppData/orca", tmp_path / "orca"):
        for account in ("one", "two"):
            target = root / "codex-accounts" / account / "home/config.toml"
            target.parent.mkdir(parents=True)
            shutil.copyfile(codex, target)
            target.write_text('model_context_window = 12345\n' + target.read_text())
            paths.append(target)
    g.uninstall_gateway(config)
    for target in paths:
        value = tomlkit.parse(target.read_text())
        assert "model_provider" not in value
        assert "secure_gateway_subscription" not in value.get("model_providers", {})
        assert value["model_context_window"] == 12345


@pytest.mark.parametrize("lose_config", [False, True])
def test_force_clean_without_installation_record(setup, lose_config):
    config, codex, claude = setup
    g.installation_path(config).unlink()
    if lose_config:
        config.unlink()
    result = CliRunner().invoke(main, ["gateway", "uninstall", "--config", str(config), "--force-clean"])
    assert result.exit_code == 0, result.output
    assert "secure_gateway_subscription" not in codex.read_text()
    assert "X-SecureGateway-Token" not in claude.read_text()
    assert "Other: original" in claude.read_text()
    assert CliRunner().invoke(main, ["gateway", "uninstall", "--config", str(config), "--force-clean"]).exit_code == 0


def test_legacy_manifest_still_merges_user_edits(setup):
    config, codex, _ = setup
    manifest = g.installation_path(config)
    value = json.loads(manifest.read_text())
    for record in value["files"].values():
        assert "original_hex" in record and "installed_sha256" in record
    manifest.write_text(json.dumps(value))
    codex.write_text('model = "later"\n' + codex.read_text())
    g.uninstall_gateway(config)
    value = tomlkit.parse(codex.read_text())
    assert value["model"] == "later"
    assert value["model_provider"] == "openai"


def test_other_gateway_instance_is_not_adopted(setup, tmp_path):
    config, codex, _ = setup
    other = tmp_path / "AppData/orca/codex-accounts/foreign/home/config.toml"
    other.parent.mkdir(parents=True)
    other.write_text(codex.read_text().replace("38117", "39118"))
    before = other.read_bytes()
    g.uninstall_gateway(config)
    assert other.read_bytes() == before


def test_merge_failure_validates_all_files_before_changes(setup):
    config, codex, claude = setup
    codex.write_text('model = "later"\n' + codex.read_text())
    claude.write_text('{"env":')
    before = codex.read_bytes(), claude.read_bytes(), g.installation_path(config).read_bytes()
    with pytest.raises(ValueError):
        g.uninstall_gateway(config)
    assert (codex.read_bytes(), claude.read_bytes(), g.installation_path(config).read_bytes()) == before


def test_interrupted_selective_restore_can_retry(setup, monkeypatch):
    config, codex, claude = setup
    codex.write_text('model = "later"\n' + codex.read_text())
    value = json.loads(claude.read_text())
    value["theme"] = "dark"
    claude.write_text(json.dumps(value))
    write = g.atomic_bytes

    def fail_codex(path, data):
        if path == codex:
            raise OSError("interrupted merge")
        return write(path, data)

    with monkeypatch.context() as patch:
        patch.setattr(g, "atomic_bytes", fail_codex)
        with pytest.raises(OSError, match="interrupted merge"):
            g.uninstall_gateway(config)
    assert json.loads(g.installation_path(config).read_text())["uninstall_started"]
    assert g.uninstall_gateway(config)
    assert tomlkit.parse(codex.read_text())["model"] == "later"
    assert json.loads(claude.read_text())["theme"] == "dark"
