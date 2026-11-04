"""Installation rejects settings links without damaging dotfile ownership."""
from pathlib import Path
import pytest
from secure_gateway.gateway_install import install_gateway, installation_path
from secure_gateway.xai_install import install_api


def link(path, target):
    try:
        path.symlink_to(target)
    except OSError:
        pytest.skip("Symlink creation unavailable")


@pytest.mark.parametrize("mode", ["claude", "codex", "api"])
@pytest.mark.parametrize("dangling", [False, True])
def test_linked_host_settings_rejected_without_writes(tmp_path, mode, dangling):
    home = tmp_path / "home"
    home.mkdir()
    target = tmp_path / "dotfile"
    raw = b'{"theme":"dark"}\n' if mode == "claude" else b'# personal\n'
    if not dangling:
        target.write_bytes(raw)
    settings = home / ("settings.json" if mode == "claude" else "config.toml")
    link(settings, target)
    config = tmp_path / "state" / "custom.json"
    with pytest.raises(ValueError, match="symbolic link"):
        if mode == "api":
            install_api(config, "grok-fixture", grok_dir=home)
        else:
            install_gateway(config, agent=mode, claude_dir=home, codex_dir=home, startup_path=tmp_path / "startup")
    assert settings.is_symlink()
    assert not config.exists() and not installation_path(config).exists()
    assert not (tmp_path / "startup").exists()
    if not dangling:
        assert target.read_bytes() == raw
    else:
        assert not target.exists()


@pytest.mark.parametrize("mode", ["claude", "codex", "api"])
def test_symbolic_link_policy_before_transaction_writes_on_all_platforms(tmp_path, monkeypatch, mode):
    # Portable policy proof; the native tests above cover actual symlink objects.
    home = tmp_path / "home"
    home.mkdir()
    settings = home / ("settings.json" if mode == "claude" else "config.toml")
    raw = b'{"theme":"dark"}\n' if mode == "claude" else b'# personal\n'
    settings.write_bytes(raw)
    config = tmp_path / "state" / "custom.json"
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == settings or original(path))
    with pytest.raises(ValueError, match="symbolic link"):
        if mode == "api":
            install_api(config, "grok-fixture", grok_dir=home)
        else:
            install_gateway(config, agent=mode, claude_dir=home, codex_dir=home, startup_path=tmp_path / "startup")
    assert settings.read_bytes() == raw
    assert not config.exists() and not installation_path(config).exists()
    assert not (tmp_path / "startup").exists()


def test_uninstall_refuses_link_replacement_before_any_restoration(tmp_path, monkeypatch):
    from secure_gateway import gateway_install
    home = tmp_path / "home"
    home.mkdir()
    config = tmp_path / "custom.json"
    install_api(config, "grok-fixture", grok_dir=home)
    settings = home / "config.toml"
    installed = settings.read_bytes()
    manifest = installation_path(config)
    before = manifest.read_bytes()
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == settings or original(path))
    with pytest.raises(ValueError, match="refusing to overwrite"):
        gateway_install.uninstall_gateway(config)
    assert settings.read_bytes() == installed and manifest.read_bytes() == before


def test_recovery_refuses_link_replacement_before_any_restoration(tmp_path, monkeypatch):
    from hashlib import sha256
    import json
    from secure_gateway import gateway_install
    settings = tmp_path / "settings.json"
    settings.write_bytes(b"installed")
    config = tmp_path / "custom.json"
    journal = installation_path(config, pending=True)
    data = {"files": {str(settings): {"before_hex":b"original".hex(), "after_sha256":sha256(b"installed").hexdigest()}}}
    journal.write_text(json.dumps(data), encoding="utf-8")
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == settings or original(path))
    with pytest.raises(ValueError, match="Interrupted installation settings changed"):
        gateway_install._recover_install(config)
    assert settings.read_bytes() == b"installed" and journal.exists()
