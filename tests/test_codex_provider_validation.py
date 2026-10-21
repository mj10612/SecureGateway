"""Reject malformed provider tables without changing host installation files."""

import json

from click.testing import CliRunner
import pytest
import tomlkit

from secure_gateway import gateway_install
from secure_gateway.cli import main


@pytest.fixture
def installation(tmp_path, monkeypatch):
    home = tmp_path / "codex"
    home.mkdir()
    claude = tmp_path / "claude"
    claude.mkdir()
    (claude / "settings.json").write_text('{"env":{"KEEP":"unchanged"}}')
    startup = tmp_path / "startup"
    startup.write_bytes(b"existing startup")
    config = tmp_path / "state" / "config.json"
    monkeypatch.setattr(gateway_install, "codex_settings_homes", lambda _: [home])
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude))
    registration = gateway_install.startup_registration
    monkeypatch.setattr(
        gateway_install,
        "startup_registration",
        lambda arguments, startup_path=None: registration(arguments, startup),
    )
    monkeypatch.setattr(gateway_install, "stop_gateway", lambda path: False)
    ensured = []
    monkeypatch.setattr(
        gateway_install, "ensure_gateway", lambda path: ensured.append(path)
    )
    return home, claude, startup, config, ensured


@pytest.mark.parametrize(
    "value", ["1", "false", '"text"', "[]", '[{ name = "wrong" }]']
)
@pytest.mark.parametrize("agent", ["codex", "both"])
@pytest.mark.parametrize("interface", ["function", "cli"])
def test_invalid_provider_table_fails_without_writing(
    installation, value, agent, interface
):
    home, claude, startup, config, ensured = installation
    settings = home / "config.toml"
    settings.write_text(f"model_providers = {value}\n# preserve this file\n")
    auth = home / "auth.json"
    auth.write_text('{"fixture":"keep"}')
    before = {
        path: path.read_bytes()
        for path in [settings, auth, claude / "settings.json", startup]
    }
    message = "Codex model_providers must be a table; no settings were overwritten."
    if interface == "function":
        with pytest.raises(ValueError, match=message):
            gateway_install.install_gateway(config, agent=agent)
    else:
        result = CliRunner().invoke(
            main,
            [
                "gateway",
                "install",
                "--agent",
                agent,
                "--config",
                str(config),
            ],
        )
        assert result.exit_code == 1
        assert result.output == f"Error: {message}\n"
        assert isinstance(result.exception, SystemExit)
    assert {path: path.read_bytes() for path in before} == before
    assert not config.exists()
    assert not (config.parent / "installation.json").exists()
    assert not ensured


@pytest.mark.parametrize(
    "providers",
    [
        "",
        "[model_providers]\n",
        '[model_providers.existing]\nname = "Keep"\nbase_url = "https://example.test/v1"\n',
        'model_providers = { existing = { name = "Keep" } }\n',
    ],
)
def test_valid_provider_tables_install_and_uninstall_preserving_settings(
    installation, providers
):
    home, claude, startup, config, ensured = installation
    settings = home / "config.toml"
    original = '# user comment\nmodel = "fixture-model"\n' + providers
    settings.write_text(original)
    auth = home / "auth.json"
    auth.write_bytes(b'{"fixture":"keep"}')
    result = CliRunner().invoke(
        main,
        [
            "gateway",
            "install",
            "--agent",
            "codex",
            "--config",
            str(config),
        ],
    )
    assert result.exit_code == 0, result.output
    assert ensured == [config]
    installed = tomlkit.parse(settings.read_text())
    assert installed["model"] == "fixture-model"
    assert installed["model_provider"] == "secure_gateway_subscription"
    provider = installed["model_providers"]["secure_gateway_subscription"]
    assert provider["wire_api"] == "responses"
    assert (
        provider["http_headers"]["X-SecureGateway-Token"]
        == json.loads(config.read_text())["token"]
    )
    previous = tomlkit.parse(original).get("model_providers", {})
    if "existing" in previous:
        assert installed["model_providers"]["existing"] == previous["existing"]
    assert auth.read_bytes() == b'{"fixture":"keep"}'
    assert gateway_install.uninstall_gateway(config)
    assert settings.read_text() == original
    assert startup.read_bytes() == b"existing startup"
