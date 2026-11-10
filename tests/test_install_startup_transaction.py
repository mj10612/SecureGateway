"""#298: public CLI activation and rollback with real isolated child processes."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
from threading import Thread

from click.testing import CliRunner
import pytest

from secure_gateway.cli import main
from secure_gateway import gateway_install as g
from release_test_support import startup_failure_category, wait_for_bindable_port


@contextmanager
def occupied_port():
    class NotGateway(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            self.send_response(503)
            self.send_header('Content-Length', '0')
            self.end_headers()

    server = ThreadingHTTPServer(('127.0.0.1', 0), NotGateway)
    thread = Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        thread.join(5)
        server.server_close()


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    claude = tmp_path / 'claude'
    claude.mkdir()
    settings = claude / 'settings.json'
    settings.write_bytes(b'{"permissions":{"defaultMode":"default"}}\n')
    config, startup, codex = tmp_path / 'state/config.json', tmp_path / 'startup', tmp_path / 'codex'
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(claude))
    monkeypatch.setattr(g, 'codex_settings_homes', lambda _=None: [codex])
    registration = g.startup_registration
    monkeypatch.setattr(g, 'startup_registration', lambda args, startup_path=None: registration(args, startup))
    popen = g.subprocess.Popen
    children = []

    def observed_popen(*args, **kwargs):
        child = popen(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(g.subprocess, 'Popen', observed_popen)
    paths = {'settings': settings, 'config': config, 'startup': startup,
             'manifest': g.installation_path(config), 'pending': g.installation_path(config, pending=True),
             'codex': codex, 'children': children}
    try:
        yield paths
    finally:
        if config.exists():
            try:
                g.stop_gateway(config)
            except (ValueError, OSError):
                pass
        for child in children:
            if child.poll() is None:
                child.terminate()
            try:
                child.wait(timeout=10)
            except g.subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)


def install_cli(paths, port, agent='claude'):
    return CliRunner().invoke(main, ['gateway', 'install', '--agent', agent,
                                    '--config', str(paths['config']), '--port', str(port)])


def test_cli_port_conflict_restores_original_and_allows_retry_and_uninstall(setup):
    original = setup['settings'].read_bytes()
    with occupied_port() as port:
        result = install_cli(setup, port)
        assert result.exit_code == 1 and 'could not start' in result.output
        assert setup['settings'].read_bytes() == original
        assert not setup['startup'].exists()
        assert not setup['manifest'].exists()
        assert not setup['config'].exists()
        assert not setup['pending'].exists()
        assert setup['children'] and all(c.poll() is not None for c in setup['children'])
    result = install_cli(setup, free_port())
    assert result.exit_code == 0, result.output
    assert g.healthy(g.load_config(setup['config']))
    assert setup['manifest'].exists() and setup['startup'].exists()
    result = CliRunner().invoke(main, ['gateway', 'uninstall', '--config', str(setup['config'])])
    assert result.exit_code == 0, result.output
    assert setup['settings'].read_bytes() == original
    assert not setup['manifest'].exists() and not setup['startup'].exists()


@pytest.mark.parametrize('failure', ['runtime', 'timeout'])
def test_cli_early_exit_and_timeout_restore_existing_config(setup, monkeypatch, failure):
    port = free_port()
    startup_timeout = g._STARTUP_TIMEOUT
    setup['config'].parent.mkdir()
    config = {'port': port, 'token': 'synthetic-token-must-never-be-printed'}
    if failure == 'runtime':
        config['mapping_limit'] = 0
    else:
        monkeypatch.setattr(g, '_STARTUP_TIMEOUT', 0, raising=False)
    original = json.dumps(config, separators=(',', ':')).encode()
    setup['config'].write_bytes(original)
    host = setup['settings'].read_bytes()
    result = install_cli(setup, port)
    assert result.exit_code == 1, result.output
    assert 'could not start' in result.output
    assert config['token'] not in result.output
    assert setup['config'].read_bytes() == original
    assert setup['settings'].read_bytes() == host
    assert not setup['startup'].exists() and not setup['manifest'].exists()
    assert not setup['pending'].exists()
    assert setup['children'] and all(c.poll() is not None for c in setup['children'])
    # After correcting the fault, the same installation can be retried.
    if failure == 'runtime':
        del config['mapping_limit']
        setup['config'].write_text(json.dumps(config), encoding='utf-8')
    else:
        monkeypatch.setattr(g, '_STARTUP_TIMEOUT', startup_timeout)
    wait_for_bindable_port(port)
    retry = install_cli(setup, port)
    if retry.exit_code:
        category = startup_failure_category(retry.output.encode('utf-8', 'replace'))
        pytest.fail(f'install_retry_failed category={category}', pytrace=False)
    assert g.healthy(g.load_config(setup['config']))
    assert CliRunner().invoke(main, ['gateway', 'uninstall', '--config', str(setup['config'])]).exit_code == 0
    assert setup['settings'].read_bytes() == host


def test_cli_failed_reinstall_preserves_previous_files(setup):
    with occupied_port() as port:
        g.install_gateway(setup['config'], agent='claude', port=port,
                          claude_dir=setup['settings'].parent, startup_path=setup['startup'])
        originals = {key: setup[key].read_bytes() for key in ('config', 'settings', 'startup', 'manifest')}
        result = install_cli(setup, port, agent='both')
        assert result.exit_code == 1, result.output
        for key, data in originals.items():
            assert setup[key].read_bytes() == data, key
        assert not (setup['codex'] / 'config.toml').exists()
        assert not setup['pending'].exists()
        assert all(c.poll() is not None for c in setup['children'])


def test_failed_host_write_stops_new_daemon_and_restores_transaction(setup, monkeypatch):
    original = setup['settings'].read_bytes()
    write = g.atomic_bytes

    def fail_host(path, data):
        if path == setup['settings']:
            raise OSError('synthetic host write failure')
        return write(path, data)

    monkeypatch.setattr(g, 'atomic_bytes', fail_host)
    result = install_cli(setup, free_port())
    assert result.exit_code == 1, result.output
    assert setup['children'], 'Activation must precede host publication.'
    assert all(c.poll() is not None for c in setup['children'])
    assert setup['settings'].read_bytes() == original
    assert not setup['manifest'].exists() and not setup['startup'].exists() and not setup['config'].exists()


def test_failed_extension_keeps_preexisting_healthy_daemon(setup, monkeypatch):
    port = free_port()
    first = install_cli(setup, port)
    assert first.exit_code == 0, first.output
    previous = {key: setup[key].read_bytes() for key in ('config', 'settings', 'startup', 'manifest')}
    child = setup['children'][0]
    write = g.atomic_bytes

    def fail_codex(path, data):
        if path == setup['codex'] / 'config.toml':
            raise OSError('synthetic extension failure')
        return write(path, data)

    monkeypatch.setattr(g, 'atomic_bytes', fail_codex)
    result = install_cli(setup, port, agent='both')
    assert result.exit_code == 1, result.output
    assert len(setup['children']) == 1 and child.poll() is None
    assert g.healthy(g.load_config(setup['config']))
    for key, data in previous.items():
        assert setup[key].read_bytes() == data, key
    assert not (setup['codex'] / 'config.toml').exists()
    assert not setup['pending'].exists()


def test_user_edit_during_activation_is_preserved_and_merge_can_retry(setup, monkeypatch):
    original = setup['settings'].read_bytes()
    edited = b'{"personal":"edited while starting"}\n'
    start = g._start_gateway

    def activate_and_edit(path, config):
        child = start(path, config)
        setup['settings'].write_bytes(edited)
        return child

    with monkeypatch.context() as patch:
        patch.setattr(g, '_start_gateway', activate_and_edit)
        result = install_cli(setup, free_port())
    assert result.exit_code == 1 and 'settings changed' in result.output
    assert setup['settings'].read_bytes() == edited
    assert setup['pending'].exists()
    assert not setup['manifest'].exists() and not setup['startup'].exists()
    assert all(c.poll() is not None for c in setup['children'])
    # Recovery refuses the conflict again and does not overwrite the user's edit.
    again = install_cli(setup, free_port())
    assert again.exit_code == 1 and setup['settings'].read_bytes() == edited
    # Simulate the explicit merge requested by the recovery message.
    setup['settings'].write_bytes(original)
    retry = install_cli(setup, free_port())
    assert retry.exit_code == 0, retry.output
    assert not setup['pending'].exists()


def test_interrupt_after_activation_reaps_owned_child_and_retains_recovery(setup, monkeypatch):
    original = setup['settings'].read_bytes()
    write = g.atomic_bytes

    def interrupt_host(path, data):
        if path == setup['settings']:
            raise KeyboardInterrupt()
        return write(path, data)

    with monkeypatch.context() as patch:
        patch.setattr(g, 'atomic_bytes', interrupt_host)
        result = install_cli(setup, free_port())
    assert result.exit_code != 0
    assert setup['children'] and all(c.poll() is not None for c in setup['children'])
    assert setup['settings'].read_bytes() == original
    assert setup['pending'].exists()
    retry = install_cli(setup, free_port())
    assert retry.exit_code == 0, retry.output
    assert not setup['pending'].exists()


@pytest.mark.parametrize('prefix', [0, 1988])
def test_startup_diagnostics_redact_token_even_at_capture_boundary(setup, monkeypatch, prefix):
    import sys
    port = free_port()
    token = 'synthetic-secret-authentication-token-0123456789'
    setup['config'].parent.mkdir()
    setup['config'].write_text(json.dumps({'port': port, 'token': token}))
    observer = g.subprocess.Popen
    script = 'import os; os.write(2, ' + repr(('x' * prefix + token + '\n').encode()) + '); raise SystemExit(1)'

    def diagnostic_child(_argv, **kwargs):
        return observer([sys.executable, '-c', script], **kwargs)

    monkeypatch.setattr(g.subprocess, 'Popen', diagnostic_child)
    result = install_cli(setup, port)
    assert result.exit_code == 1
    assert token not in result.output and token[:12] not in result.output
    assert '[redacted]' in result.output
