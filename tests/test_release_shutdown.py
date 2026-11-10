"""A stop must wait for an admitted offline inference to finish."""
import http.client
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

import pytest

from secure_gateway.gateway import PrivacyGateway
from secure_gateway.gateway_install import stop_gateway
from release_test_support import startup_failure_category, wait_for_bindable_port


def test_stop_waits_for_active_inference_longer_than_five_seconds(tmp_path):
    entered, release = Event(), Event()

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            entered.set()
            release.wait(20)
            body = b'{"output":[]}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    token = 'synthetic-token-012345678901234567890123456789'
    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    gateway = PrivacyGateway(('127.0.0.1', 0), token,
        upstreams={'codex': f'http://127.0.0.1:{provider.server_port}'})
    threads = [Thread(target=s.serve_forever, daemon=True) for s in (provider, gateway)]
    for thread in threads:
        thread.start()
    results = []

    def request():
        conn = http.client.HTTPConnection('127.0.0.1', gateway.server_port, timeout=20)
        try:
            conn.request('POST', '/codex/responses', b'{"input":"hello"}',
                {'Content-Type': 'application/json', 'X-SecureGateway-Token': token,
                 'Authorization': 'Bearer eyJ-fixture'})
            results.append(conn.getresponse().status)
        finally:
            conn.close()

    worker = Thread(target=request, daemon=True)
    worker.start()
    try:
        assert entered.wait(30)
        config = tmp_path / 'config.json'
        config.write_text(json.dumps({'port': gateway.server_port, 'token': token}))
        timer = Thread(target=lambda: (Event().wait(6.5), release.set()), daemon=True)
        timer.start()
        assert stop_gateway(config)
        worker.join(20)
        assert results == [200]
        assert gateway.admitted_requests == 0
        assert not stop_gateway(config)
    finally:
        release.set()
        worker.join(20)
        gateway.shutdown()
        gateway.server_close()
        provider.shutdown()
        provider.server_close()
        for thread in threads:
            thread.join(20)


@pytest.mark.parametrize("entrypoint", ["module", "console"])
def test_expired_grace_ends_daemon_and_restart_preserves_state(tmp_path, monkeypatch, caplog, entrypoint):
    import os
    from pathlib import Path
    import subprocess
    import sys
    import tempfile
    import time
    import urllib.request

    from secure_gateway import gateway_install as install

    entered, release, hold = Event(), Event(), Event()
    received = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            if hold.is_set():
                entered.set()
                release.wait(30)
            body = b'{"output":[]}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    provider_thread = Thread(target=provider.serve_forever, daemon=True)
    provider_thread.start()
    import socket
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    token = 'synthetic-token-012345678901234567890123456789'
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'port': port, 'token': token}))
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('ANTHROPIC_', 'CLAUDE_', 'OPENAI_', 'CODEX_', 'ORCA_'))}
    home = tmp_path / 'home'
    env.update({'HOME': str(home), 'USERPROFILE': str(home),
                'APPDATA': str(home / 'AppData/Roaming'),
                'LOCALAPPDATA': str(home / 'AppData/Local'),
                'XDG_CONFIG_HOME': str(home / '.config'),
                'CODEX_HOME': str(home / '.codex'),
                'CLAUDE_CONFIG_DIR': str(home / '.claude')})
    env['SG_TEST_PROVIDER'] = f'http://127.0.0.1:{provider.server_port}'
    env['PYTHONPATH'] = str(tmp_path)
    (tmp_path / 'sitecustomize.py').write_text(
        "import os\nimport secure_gateway.gateway as gateway\n"
        "gateway.UPSTREAMS['codex'] = os.environ['SG_TEST_PROVIDER']\n")
    processes = []
    diagnostics = []

    def start(stage):
        wait_for_bindable_port(port)
        executable = Path(sys.executable).parent / ('secure-gateway.exe' if os.name == 'nt' else 'secure-gateway')
        command = [sys.executable, '-m', 'secure_gateway'] if entrypoint == 'module' else [str(executable)]
        diagnostic = tempfile.TemporaryFile()
        diagnostics.append(diagnostic)
        child = subprocess.Popen(command + ['gateway', 'run', '--config', str(config)], cwd=tmp_path, env=env,
                                 stdout=subprocess.DEVNULL, stderr=diagnostic)
        processes.append(child)
        # Apply the same startup contract as the public install/ensure path.
        deadline = time.monotonic() + install._STARTUP_TIMEOUT
        while time.monotonic() < deadline:
            if install.healthy({'port': port, 'token': token}):
                return child
            if child.poll() is not None:
                break
            time.sleep(.05)
        status = child.poll()
        diagnostic.seek(0)
        category = startup_failure_category(diagnostic.read(4096))
        outcome = 'timeout' if status is None else 'exited'
        pytest.fail(f'daemon_{stage}_{outcome} category={category} exit={status}', pytrace=False)

    def call():
        request = urllib.request.Request(f'http://127.0.0.1:{port}/codex/responses',
            data=b'{"input":"Email alice@example.invalid"}', headers={'Content-Type': 'application/json',
            'X-SecureGateway-Token': token, 'Authorization': 'Bearer eyJ-fixture'})
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=20) as response:
            return response.read()

    monkeypatch.setattr(install, '_SHUTDOWN_GRACE_SECONDS', 1)
    errors = []
    try:
        child = start('initial')
        call()
        initial_input = received[-1]['input']
        if 'alice@example.invalid' in json.dumps(initial_input):
            pytest.fail('Provider request was not masked', pytrace=False)
        snapshots = list((tmp_path / 'sessions').glob('*-symbols-v2.enc'))
        assert len(snapshots) == 1
        assert b'alice@example.invalid' not in snapshots[0].read_bytes()
        original_config = config.read_bytes()
        assert (tmp_path / 'logs.sqlite3').exists()
        hold.set()
        def active_request():
            try:
                call()
            except (OSError, http.client.HTTPException) as exc:
                errors.append(type(exc).__name__)
        worker = Thread(target=active_request, daemon=True)
        worker.start()
        assert entered.wait(30)
        assert install.stop_gateway(config)
        child.wait(timeout=10)
        worker.join(10)
        assert child.returncode == 75 and errors and not worker.is_alive()
        assert 'gateway_shutdown forced=true' in caplog.text
        assert not install.stop_gateway(config)
        assert config.read_bytes() == original_config
        hold.clear()
        release.set()
        restarted = start('restart')
        call()
        if received[-1]['input'] != initial_input:
            pytest.fail('Recovered session mapping changed', pytrace=False)
        assert snapshots[0].exists()
        assert not list((tmp_path / 'sessions').glob('*.quarantined'))
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(tmp_path / 'logs.sqlite3')) as db:
            assert db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert install.stop_gateway(config)
        restarted.wait(timeout=10)
    finally:
        release.set()
        for child in processes:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=10)
        for diagnostic in diagnostics:
            diagnostic.close()
        provider.shutdown()
        provider.server_close()
        provider_thread.join(10)


def test_embedded_gateway_never_forces_the_host_process(monkeypatch):
    from secure_gateway import gateway as gateway_module

    forced = []
    monkeypatch.setattr(gateway_module.os, '_exit', lambda code: forced.append(code))
    server = PrivacyGateway(('127.0.0.1', 0), 'fixture-token', upstreams={'codex': 'http://127.0.0.1:1'})
    serving = Thread(target=server.serve_forever, daemon=True)
    serving.start()
    assert server.try_admit('codex')
    draining = Thread(target=server.drain_and_shutdown, kwargs={'grace': .1}, daemon=True)
    draining.start()
    try:
        assert not Event().wait(.25)
        assert draining.is_alive()
        assert not forced
    finally:
        server.release_admission('codex')
        draining.join(10)
        serving.join(10)
        server.server_close()
    assert not draining.is_alive()


def test_forced_stop_diagnostic_failure_does_not_change_success(tmp_path, monkeypatch):
    from secure_gateway import gateway_install as install

    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'port': 12345, 'token': 'x' * 32}))
    states = iter([True, False])
    monkeypatch.setattr(install, 'healthy', lambda _config: next(states))
    from types import SimpleNamespace
    ticks = iter([0, 31])
    monkeypatch.setattr(install, 'time', SimpleNamespace(monotonic=lambda: next(ticks)))

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def read(self):
            return b'{}'

    class Opener:
        def open(self, *_args, **_kwargs):
            return Response()

    def broken_warning(*_args):
        raise RuntimeError('diagnostic failure')

    monkeypatch.setattr(install.urllib.request, 'build_opener', lambda *_args: Opener())
    monkeypatch.setattr(install._LOGGER, 'warning', broken_warning)
    assert install.stop_gateway(config) is True


def test_port_readiness_waits_for_actual_listener_to_release():
    """An occupied port cannot be reported ready before its listener exits."""
    import socket
    from threading import Event, Thread

    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    port = listener.getsockname()[1]
    released = Event()

    def release_listener():
        released.wait(10)
        listener.close()

    thread = Thread(target=release_listener, daemon=True)
    thread.start()
    try:
        with pytest.raises(TimeoutError):
            wait_for_bindable_port(port, timeout=.2)
        released.set()
        wait_for_bindable_port(port, timeout=10)
    finally:
        released.set()
        thread.join(10)
        listener.close()


@pytest.mark.parametrize('content,expected', [
    (b'private fixture Address already in use', 'address_in_use'),
    (b'private fixture Permission denied', 'permission_denied'),
    (b'private fixture ModuleNotFoundError', 'import_failure'),
    (b'private fixture arbitrary value', 'other_or_unavailable'),
])
def test_startup_failure_category_excludes_diagnostic_content(content, expected):
    """Only fixed categories cross the captured-output boundary."""
    assert startup_failure_category(content) == expected
