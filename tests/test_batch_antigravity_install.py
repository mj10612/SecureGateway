"""Owned MCP registration interrupted transaction recovery."""

import json

import pytest

from secure_gateway import antigravity_install as a


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("operation", [True, False])
def test_install_interruption_retries_without_stranding_record(
    tmp_path, monkeypatch, exists, operation
):
    path = tmp_path / "mcp.json"
    original = b'{"mcpServers":{"other":{"command":"keep"}}}\n'
    if exists:
        path.write_bytes(original)
    write = a._atomic_json

    def interrupt(target, value):
        if target == path:
            raise KeyboardInterrupt()
        write(target, value)

    with monkeypatch.context() as patch:
        patch.setattr(a, "_atomic_json", interrupt)
        with pytest.raises(KeyboardInterrupt):
            a.configure_antigravity(path)
    a.configure_antigravity(path, operation)
    if operation:
        assert a.antigravity_status(path)["ready"]
        a.configure_antigravity(path, False)
    if exists:
        assert json.loads(path.read_bytes())["mcpServers"] == {
            "other": {"command": "keep"}
        }
        assert path.with_name(path.name + ".secure-gateway.bak").read_bytes() == original
    else:
        assert not path.exists() or json.loads(path.read_bytes())["mcpServers"] == {}
    assert not path.with_name(path.name + ".secure-gateway.json").exists()
    assert not path.with_name(path.name + ".secure-gateway.pending.json").exists()


def test_interrupted_registration_refuses_user_edit_before_any_restore(
    tmp_path, monkeypatch
):
    path = tmp_path / "mcp.json"
    path.write_text('{"mcpServers":{}}')
    write = a._atomic_json

    def interrupt(target, value):
        if target == path:
            raise KeyboardInterrupt()
        write(target, value)

    with monkeypatch.context() as patch:
        patch.setattr(a, "_atomic_json", interrupt)
        with pytest.raises(KeyboardInterrupt):
            a.configure_antigravity(path)
    path.write_text('{"mcpServers":{"new":{"command":"user"}}}')
    record = path.with_name(path.name + ".secure-gateway.json")
    before = [path.read_bytes(), record.read_bytes()]
    for install in (True, False):
        with pytest.raises(ValueError, match="changed"):
            a.configure_antigravity(path, install)
        assert [path.read_bytes(), record.read_bytes()] == before


@pytest.mark.parametrize("boundary", ["settings", "record_removal"])
def test_uninstall_interruption_recovers_owned_entry_and_other_servers(
    tmp_path, monkeypatch, boundary
):
    path = tmp_path / "mcp.json"
    a.configure_antigravity(path)
    settings = json.loads(path.read_bytes())
    settings["mcpServers"]["later"] = {"command": "retain"}
    path.write_text(json.dumps(settings))
    record = path.with_name(path.name + ".secure-gateway.json")
    if boundary == "settings":
        write = a._atomic_json

        def interrupt(target, value):
            if target == path:
                raise KeyboardInterrupt()
            write(target, value)

        with monkeypatch.context() as patch:
            patch.setattr(a, "_atomic_json", interrupt)
            with pytest.raises(KeyboardInterrupt):
                a.configure_antigravity(path, False)
    else:
        unlink = type(path).unlink

        def interrupt(target, *args, **kwargs):
            if target == record:
                raise KeyboardInterrupt()
            return unlink(target, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(type(path), "unlink", interrupt)
            with pytest.raises(KeyboardInterrupt):
                a.configure_antigravity(path, False)
    a.configure_antigravity(path, False)
    assert json.loads(path.read_bytes())["mcpServers"] == {
        "later": {"command": "retain"}
    }


def test_reinstall_recovery_preserves_existing_record_and_backup(tmp_path, monkeypatch):
    path = tmp_path / "mcp.json"
    raw = b'{"mcpServers":{"secure-gateway":{"command":"previous"}}}\n'
    path.write_bytes(raw)
    a.configure_antigravity(path)
    record = path.with_name(path.name + ".secure-gateway.json")
    backup = path.with_name(path.name + ".secure-gateway.bak")
    before = [path.read_bytes(), record.read_bytes(), backup.read_bytes()]
    write = a._atomic_json

    def interrupt(target, value):
        if target == path:
            raise KeyboardInterrupt()
        write(target, value)

    with monkeypatch.context() as patch:
        patch.setattr(a, "_atomic_json", interrupt)
        with pytest.raises(KeyboardInterrupt):
            a.configure_antigravity(path)
    a.configure_antigravity(path)
    assert [path.read_bytes(), record.read_bytes(), backup.read_bytes()] == before
    a.configure_antigravity(path, False)
    assert json.loads(path.read_bytes())["mcpServers"]["secure-gateway"] == {
        "command": "previous"
    }


def test_recovery_can_itself_be_interrupted(tmp_path, monkeypatch):
    path = tmp_path / "mcp.json"
    path.write_bytes(b'{"mcpServers":{}}\n')
    record = path.with_name(path.name + ".secure-gateway.json")
    write = a._atomic_json

    def interrupt_write(target, value):
        if target == path:
            raise KeyboardInterrupt()
        write(target, value)

    with monkeypatch.context() as patch:
        patch.setattr(a, "_atomic_json", interrupt_write)
        with pytest.raises(KeyboardInterrupt):
            a.configure_antigravity(path)
    unlink = type(path).unlink

    def interrupt_restore(target, *args, **kwargs):
        if target == record:
            raise KeyboardInterrupt()
        return unlink(target, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(type(path), "unlink", interrupt_restore)
        with pytest.raises(KeyboardInterrupt):
            a.configure_antigravity(path)
    a.configure_antigravity(path)
    assert a.antigravity_status(path)["ready"]
