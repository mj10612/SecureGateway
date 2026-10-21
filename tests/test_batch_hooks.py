"""Windows hook quoting and local encrypted snapshot lifecycle regressions."""

import json
import os
import subprocess
import time

import pytest

from secure_gateway.encrypted_session import save_session, session_file_lock
from secure_gateway.hooks import HookStore, _owned, configure, installation_status
from secure_gateway.hooks import _command_parts, _hook_command
from secure_gateway.session import PrivacySession


def snapshot(store, sid, expired=False):
    session = PrivacySession(sid, ttl_seconds=1 if expired else 3600)
    if expired:
        session.last_accessed = time.time() - 20
    save_session(store.path(sid), session, 'local-test-key')
    return store.path(sid)


@pytest.fixture
def store(tmp_path):
    (tmp_path / 'key').write_text('local-test-key', encoding='ascii')
    return HookStore(tmp_path)


def inventory(directory):
    return {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()}


def test_diagnostics_and_gc_dry_run_do_not_write_or_disclose(store):
    snapshot(store, 'private-valid-session')
    expired = snapshot(store, 'private-expired-session', expired=True)
    with session_file_lock(expired):
        pass
    store.path('private-corrupt-session').write_bytes(b'corrupt-private-data')
    before = inventory(store.directory)
    report = store.snapshot_diagnostics()
    assert report['counts']['valid'] == 1
    assert report['counts']['expired'] == 1
    assert report['counts']['corrupt'] == 1
    assert store.gc()['candidates'] == 1
    assert inventory(store.directory) == before
    output = json.dumps(report)
    assert 'private-' not in output and 'local-test-key' not in output
    assert str(store.directory) not in output
    assert all(path.name not in output for path in store.directory.iterdir())


def test_gc_apply_retires_only_expired_and_preserves_persistent_lock(store):
    expired = snapshot(store, 'old-session', expired=True)
    valid = snapshot(store, 'current-session')
    corrupt = store.path('broken-session')
    corrupt.write_bytes(b'broken')
    report = store.gc(dry_run=False)
    assert report['removed'] == 1
    assert not expired.exists()
    assert expired.with_name(expired.name + '.lock').exists()
    assert expired.with_name(expired.name + '.retired').exists()
    assert valid.exists() and corrupt.exists()
    with pytest.raises(ValueError, match='retired'):
        with store.session('old-session', create=True):
            pytest.fail('Retired host session recreated')
    assert store.snapshot_diagnostics()['counts']['retired'] == 1


def test_active_and_legacy_locked_snapshots_are_never_deleted(store):
    active = snapshot(store, 'active-session', expired=True)
    legacy = snapshot(store, 'legacy-session', expired=True)
    legacy.with_name(legacy.name + '.lock').write_bytes(b'')
    before = inventory(store.directory)
    with session_file_lock(active):
        assert store.snapshot_diagnostics()['counts']['active'] == 1
        assert store.snapshot_diagnostics()['counts']['legacy_lock'] == 1
        assert store.gc(dry_run=False)['removed'] == 0
    # Native lock creation is the only change, not diagnostics/GC.
    after = inventory(store.directory)
    for name, content in before.items():
        assert after[name] == content
    assert active.exists() and legacy.exists()


def test_gc_revalidates_expiry_after_diagnostics(store, monkeypatch):
    path = snapshot(store, 'refreshed-session', expired=True)
    original = store.snapshot_diagnostics

    def refreshed():
        report = original()
        snapshot(store, 'refreshed-session')
        return report

    monkeypatch.setattr(store, 'snapshot_diagnostics', refreshed)
    report = store.gc(dry_run=False)
    assert report['removed'] == 0 and path.exists()
    assert not path.with_name(path.name + '.retired').exists()


def test_missing_directory_diagnostics_never_create_it(tmp_path):
    absent = tmp_path / 'absent'
    store = HookStore(absent)
    assert store.snapshot_diagnostics()['total'] == 0
    assert store.gc()['removed'] == 0
    assert not absent.exists()


def test_gc_tombstone_precedes_snapshot_unlink_and_survives_failure(store, monkeypatch):
    from pathlib import Path

    path = snapshot(store, 'unlink-failed', expired=True)
    original = Path.unlink

    def fail_snapshot_unlink(target, *args, **kwargs):
        if target == path:
            assert path.with_name(path.name + '.retired').exists()
            raise PermissionError('fixture file in use')
        return original(target, *args, **kwargs)

    monkeypatch.setattr(Path, 'unlink', fail_snapshot_unlink)
    assert store.gc(dry_run=False)['removed'] == 0
    assert path.exists()
    with pytest.raises(ValueError, match='retired'):
        with store.session('unlink-failed', create=True):
            pass


@pytest.mark.skipif(os.name != 'nt', reason='Windows shell command generation')
def test_encoded_windows_command_preserves_metachars_and_rejects_appended_script():
    import base64

    args = [r'C:\private&%VARIABLE%\python.exe', '-m', 'secure_gateway', 'hook',
            '--state-dir', r'C:\private|percent%quoted\state', '--agent', 'codex']
    command = _hook_command(args)
    assert _command_parts(command) == args
    assert _owned({'type': 'command', 'command': command}, 'codex')
    prefix, encoded = command.rsplit(' ', 1)
    script = base64.b64decode(encoded).decode('utf-16le') + '; Write-Output forged'
    forged = prefix + ' ' + base64.b64encode(script.encode('utf-16le')).decode('ascii')
    assert not _owned({'type': 'command', 'command': forged}, 'codex')


@pytest.mark.skipif(os.name != 'nt', reason='cmd.exe integration')
def test_windows_metachar_command_runs_and_registration_survives_reinstall(tmp_path):
    settings = tmp_path / 'settings.json'
    state = tmp_path / 'private&%SECURE_GATEWAY_TEST_EXPANSION%state'
    configure(settings, state, True)
    command = json.loads(settings.read_text(encoding='utf-8'))['hooks']['PostToolUse'][0]['hooks'][0]['command']
    assert _owned({'type': 'command', 'command': command}, 'claude')
    assert installation_status(settings, state)['ready']
    env = dict(os.environ, SECURE_GATEWAY_TEST_EXPANSION='EXPANDED_WRONG_PATH')
    result = subprocess.run([os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/c', command],
                            input=json.dumps({'hook_event_name': 'PostToolUse',
                                              'session_id': 'windows-session',
                                              'tool_response': {'stdout': 'Alice'}}),
                            capture_output=True, encoding='utf-8', env=env, timeout=30)
    assert result.returncode == 0, result.stderr
    assert 'Alice' not in result.stdout
    assert HookStore(state).path('windows-session').exists()
    configure(settings, state, True)
    assert len(json.loads(settings.read_text(encoding='utf-8'))['hooks']['PostToolUse']) == 1
    configure(settings, state, False)
    assert json.loads(settings.read_text(encoding='utf-8'))['hooks'] == {}
