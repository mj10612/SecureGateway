"""Installation and diagnostics share the same settings target (#304)."""

import json
import os
import sys

from click.testing import CliRunner
import pytest

from secure_gateway.antigravity_install import antigravity_status
from secure_gateway.cli import main


@pytest.mark.parametrize('layout', ['regular', 'absolute', 'relative', 'dangling'])
def test_init_doctor_uninstall_use_same_target(tmp_path, monkeypatch, layout):
    home = tmp_path / 'isolated home'
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USERPROFILE', str(home))
    settings = home / '.gemini/config/mcp_config.json'
    settings.parent.mkdir(parents=True)
    target = settings if layout == 'regular' else home / 'dotfiles/antigravity.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    original = {'mcpServers': {'other': {'command': 'other-program'},
                               'secure-gateway': {'command': 'previous-program'}}}
    if layout != 'dangling':
        target.write_text(json.dumps(original), encoding='utf-8')
    if layout != 'regular':
        link_target = os.path.relpath(target, settings.parent) if layout == 'relative' else str(target)
        try:
            settings.symlink_to(link_target)
        except OSError:
            if sys.platform == 'win32':
                pytest.skip('Windows symbolic link creation requires permission')
            raise
        before_link = os.readlink(settings)

    # Read-only diagnosis of a missing target must not create configuration.
    before = {p: p.read_bytes() for p in home.rglob('*') if p.is_file()}
    assert antigravity_status(settings)['ready'] is False
    assert {p: p.read_bytes() for p in home.rglob('*') if p.is_file()} == before

    runner = CliRunner()
    result = runner.invoke(main, ['init', '--agent', 'antigravity'])
    assert result.exit_code == 0, result.output
    record = target.with_name(target.name + '.secure-gateway.json')
    assert record.is_file()
    before = {p: p.read_bytes() for p in home.rglob('*') if p.is_file()}
    diagnosed = runner.invoke(main, ['doctor', '--agent', 'antigravity'])
    assert diagnosed.exit_code == 0, diagnosed.output
    status = json.loads(diagnosed.output)
    assert status['ready'] is True
    assert status['settings'] == str(target.resolve())
    assert status == antigravity_status(target)
    assert {p: p.read_bytes() for p in home.rglob('*') if p.is_file()} == before

    removed = runner.invoke(main, ['uninstall', '--agent', 'antigravity'])
    assert removed.exit_code == 0, removed.output
    assert not record.exists()
    expected = {'mcpServers': {}} if layout == 'dangling' else original
    assert json.loads(target.read_text(encoding='utf-8')) == expected
    assert antigravity_status(settings)['ready'] is False
    if layout != 'regular':
        assert settings.is_symlink() and os.readlink(settings) == before_link
        assert not settings.with_name(settings.name + '.secure-gateway.json').exists()
