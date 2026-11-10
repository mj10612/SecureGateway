"""#327: bounded useful diagnostics must not become a private-data channel."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import json
import logging
import os
from threading import Event, Thread
import time

import pytest

from secure_gateway import gateway as module
from secure_gateway.gateway import PrivacyGateway

PRIVATE = 'PRIVATE-token-path-body-DO-NOT-LOG'


def old_snapshot(tmp_path):
    path = tmp_path / 'codex-symbols-v2.enc'
    path.write_bytes(PRIVATE.encode())
    old = time.time() - 90000
    os.utime(path, (old, old))
    return path


def test_corrupt_foreign_cleanup_is_preserved_counted_and_quiet(tmp_path, caplog):
    with PrivacyGateway(('127.0.0.1', 0), PRIVATE, state_dir=tmp_path) as gateway:
        path = old_snapshot(tmp_path)
        gateway._snapshot_scan = iter([path])
        with caplog.at_level(logging.WARNING):
            gateway.cleanup_expired_snapshots()
        assert path.read_bytes() == PRIVATE.encode()
        assert not path.with_name(path.name + '.quarantined').exists()
        assert gateway.session_diagnostics()['diagnostic_counts']['snapshot_preserved'] == 1
        assert not caplog.records


def test_cleanup_io_warning_is_fixed_once_and_does_not_delete_file(tmp_path, monkeypatch, caplog):
    with PrivacyGateway(('127.0.0.1', 0), PRIVATE, state_dir=tmp_path) as gateway:
        path = old_snapshot(tmp_path)
        def unreadable(*_args, **_kwargs):
            raise OSError(PRIVATE + str(path))
        monkeypatch.setattr(module, 'load_session', unreadable)
        with caplog.at_level(logging.WARNING):
            for _ in range(2):
                gateway._snapshot_scan = iter([path])
                gateway.cleanup_expired_snapshots()
        assert path.read_bytes() == PRIVATE.encode()
        assert gateway.session_diagnostics()['diagnostic_counts']['snapshot_cleanup_io'] == 2
        assert len(caplog.records) == 1
        assert 'snapshot_cleanup_io' in caplog.text
        assert PRIVATE not in caplog.text and str(tmp_path) not in caplog.text
        assert all(r.exc_info is None for r in caplog.records)


def test_diagnostics_are_instance_scoped_threadsafe_copied_and_bounded(caplog):
    with PrivacyGateway(('127.0.0.1', 0), PRIVATE) as first, PrivacyGateway(('127.0.0.1', 0), 'other-token') as second:
        with caplog.at_level(logging.WARNING):
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda _: first.record_diagnostic('upstream_error_body'), range(80)))
        assert first.session_diagnostics()['diagnostic_counts']['upstream_error_body'] == 80
        assert second.session_diagnostics()['diagnostic_counts']['upstream_error_body'] == 0
        counts = first.session_diagnostics()['diagnostic_counts']
        counts['upstream_error_body'] = 0
        assert first.session_diagnostics()['diagnostic_counts']['upstream_error_body'] == 80
        assert len(caplog.records) == 1
        first._diagnostic_counts['upstream_error_body'] = 2**31 - 2
        first.record_diagnostic('upstream_error_body')
        first.record_diagnostic('upstream_error_body')
        assert first.session_diagnostics()['diagnostic_counts']['upstream_error_body'] == 2**31 - 1
        with pytest.raises(ValueError):
            first.record_diagnostic(PRIVATE)
        assert PRIVATE not in caplog.text


@pytest.fixture
def http_gateway(tmp_path):
    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.server.received.append(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
            body = self.server.body
            self.send_response(self.server.status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Retry-After', '3')
            self.send_header('x-private-header', PRIVATE)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    provider.received, provider.status, provider.body = [], 429, b'not-json-' + PRIVATE.encode()
    gateway = PrivacyGateway(('127.0.0.1', 0), PRIVATE, state_dir=tmp_path,
                             audit_path=tmp_path / 'audit.db',
                             upstreams={'claude': f'http://127.0.0.1:{provider.server_port}'},
                             api_upstreams={'xai': f'http://127.0.0.1:{provider.server_port}'})
    threads = [Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
               for server in (provider, gateway)]
    for thread in threads:
        thread.start()
    try:
        yield gateway, provider
    finally:
        for server in (gateway, provider):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(5)


def call(gateway, path='/claude/v1/messages', *, token=PRIVATE, method='POST', auth='Bearer sk-ant-oat-synthetic'):
    connection = http.client.HTTPConnection('127.0.0.1', gateway.server_port, timeout=10)
    headers = {'X-SecureGateway-Token': token, 'Authorization': auth,
               'Content-Type': 'application/json', 'X-SecureGateway-Session': 'diagnostic-test'}
    body = json.dumps({'model': 'fixture', 'messages': [{'role': 'user', 'content': 'Summarize the report.'}]}) if method == 'POST' else None
    try:
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        return response.status, response.read(), dict(response.headers)
    finally:
        connection.close()


def test_http_malformed_error_remains_retryable_and_auth_diagnostics_are_safe(http_gateway, caplog):
    gateway, provider = http_gateway
    with caplog.at_level(logging.WARNING):
        for _ in range(2):
            status, body, headers = call(gateway)
            assert status == 429 and headers['Retry-After'] == '3'
            assert json.loads(body) == {'error': {'message': 'Upstream rejected the request.'}}
            assert 'x-private-header' not in {key.lower() for key in headers}
    assert len(provider.received) == 2
    assert len(caplog.records) == 1
    assert PRIVATE not in caplog.text
    assert call(gateway, '/admin/api/sessions', token='wrong', method='GET')[0] == 401
    status, body, _ = call(gateway, '/admin/api/sessions', method='GET')
    assert status == 200
    assert json.loads(body)['diagnostic_counts']['upstream_error_body'] == 2
    assert PRIVATE.encode() not in body


@pytest.mark.parametrize('catalog', [False, True])
def test_http_formatter_crash_produces_fixed_response_and_next_request_works(http_gateway, monkeypatch, caplog, catalog):
    gateway, provider = http_gateway
    options = {'path': '/xai/v1/models', 'method': 'GET', 'auth': 'Bearer xai-synthetic'} if catalog else {}
    def broken_formatter(*_args, **_kwargs):
        raise RuntimeError(PRIVATE)
    with monkeypatch.context() as patch:
        patch.setattr(module, 'sanitized_upstream_error', broken_formatter)
        with caplog.at_level(logging.WARNING):
            status, body, headers = call(gateway, **options)
    assert status == 429 and headers['Retry-After'] == '3'
    assert json.loads(body) == {'error': {'message': 'Upstream rejected the request.'}}
    assert PRIVATE.encode() not in body and PRIVATE not in caplog.text
    assert gateway.session_diagnostics()['diagnostic_counts']['upstream_error_format'] == 1
    provider.body = b'{"error":{"type":"rate_limit_error","code":"rate_limit_exceeded"}}'
    status, body, _ = call(gateway, **options)
    assert status == 429 and json.loads(body)['error']['code'] == 'rate_limit_exceeded'
    assert len(provider.received) == 2


@pytest.mark.parametrize('failure', ['encrypted', 'opaque'])
def test_snapshot_load_io_is_observable_and_never_forwards(http_gateway, monkeypatch, caplog, failure):
    gateway, provider = http_gateway
    session = gateway.get_session('claude', '\0diagnostic-test')
    session.mask('synthetic-private-name', code=True)
    gateway.save('claude', session)
    gateway.sessions.clear()
    def unreadable(*_args, **_kwargs):
        raise OSError(PRIVATE)
    if failure == 'encrypted':
        monkeypatch.setattr(module, 'load_session', unreadable)
    else:
        from pathlib import Path
        original = Path.read_text
        def unreadable_opaque(path, *args, **kwargs):
            if path.name.endswith('-symbols-v2.opaque.json'):
                raise OSError(PRIVATE)
            return original(path, *args, **kwargs)
        monkeypatch.setattr(Path, 'read_text', unreadable_opaque)
    with caplog.at_level(logging.WARNING):
        status, body, _ = call(gateway)
    assert status == 500 and PRIVATE.encode() not in body
    assert provider.received == []
    assert gateway.session_diagnostics()['diagnostic_counts']['snapshot_load_failed'] == 1
    assert PRIVATE not in caplog.text


def test_expired_authenticated_snapshot_cleanup_is_quiet(tmp_path, caplog):
    with PrivacyGateway(('127.0.0.1', 0), PRIVATE, state_dir=tmp_path) as gateway:
        session = module.GatewaySession()
        session.session.last_accessed = time.time() - 90000
        path = tmp_path / 'codex-symbols-v2.enc'
        module.save_session(path, session.session, PRIVATE)
        old = time.time() - 90000
        os.utime(path, (old, old))
        gateway._snapshot_scan = iter([path])
        with caplog.at_level(logging.WARNING):
            gateway.cleanup_expired_snapshots()
        assert not path.exists()
        assert not any(gateway.operational_diagnostics().values())
        assert not caplog.records


def test_scan_failure_is_reported_but_missing_candidate_is_quiet(tmp_path, caplog):
    def broken_scan():
        raise OSError(PRIVATE)
        yield  # pragma: no cover
    with PrivacyGateway(('127.0.0.1', 0), PRIVATE, state_dir=tmp_path) as gateway:
        gateway._snapshot_scan = broken_scan()
        with caplog.at_level(logging.WARNING):
            gateway.cleanup_expired_snapshots()
        assert gateway.operational_diagnostics()['snapshot_scan_io'] == 1
        assert PRIVATE not in caplog.text
        caplog.clear()
        gateway._snapshot_scan = iter([tmp_path / 'codex-symbols-v2.enc'])
        with caplog.at_level(logging.WARNING):
            gateway.cleanup_expired_snapshots()
        assert gateway.operational_diagnostics()['snapshot_cleanup_io'] == 0
        assert not caplog.records


def test_active_corruption_recovery_is_observable_without_logging_bytes(tmp_path, caplog):
    with PrivacyGateway(('127.0.0.1', 0), PRIVATE, state_dir=tmp_path) as gateway:
        path = tmp_path / 'codex-symbols-v2.enc'
        path.write_bytes(PRIVATE.encode())
        with caplog.at_level(logging.WARNING):
            session = gateway.get_session('codex')
        assert not session.session.forward_store
        assert path.with_name(path.name + '.quarantined').read_bytes() == PRIVATE.encode()
        assert gateway.operational_diagnostics()['snapshot_recovered'] == 1
        assert len(caplog.records) == 1
        assert PRIVATE not in caplog.text and str(tmp_path) not in caplog.text


@pytest.mark.parametrize('code', [413, 302])
def test_failed_error_stream_close_retains_safe_schema(code, caplog):
    class BrokenError:
        def __init__(self):
            self.code = code
        def read(self, _limit):
            raise OSError(PRIVATE)
        def close(self):
            raise OSError(PRIVATE)
    with PrivacyGateway(('127.0.0.1', 0), PRIVATE) as gateway:
        with caplog.at_level(logging.WARNING):
            status, body = gateway.format_upstream_error(BrokenError())
        assert status == (413 if code == 413 else 502)
        assert set(json.loads(body)) == {'error'}
        assert set(json.loads(body)['error']) == {'message'}
        if code == 413:
            assert 'Prompt is too long' in json.loads(body)['error']['message']
        assert gateway.operational_diagnostics()['upstream_error_stream_close'] == 1
        assert PRIVATE not in caplog.text and PRIVATE.encode() not in body
        assert all(record.exc_info is None for record in caplog.records)


def test_failed_log_delivery_does_not_break_http_or_expose_handler_error(http_gateway, tmp_path, caplog, capfd):
    gateway, _ = http_gateway
    with module.diagnostic_logging(filename=tmp_path / PRIVATE / 'missing.log'):
        with caplog.at_level(logging.WARNING):
            status, body, _ = call(gateway)
        deadline = time.monotonic() + 3
        while not gateway.operational_diagnostics()['log_delivery_failed'] and time.monotonic() < deadline:
            time.sleep(.01)
        assert status == 429 and PRIVATE.encode() not in body and str(tmp_path).encode() not in body
        assert gateway.operational_diagnostics()['log_delivery_failed'] == 1
        assert gateway.operational_diagnostics()['upstream_error_body'] == 1
        assert PRIVATE not in caplog.text and str(tmp_path) not in caplog.text
        stderr = capfd.readouterr().err
        assert PRIVATE not in stderr and str(tmp_path) not in stderr
        assert 'Summarize the report.' not in stderr + caplog.text + body.decode()


def test_failed_log_write_is_counted_and_quiet(http_gateway, tmp_path, caplog, capfd):
    class BrokenStream:
        def write(self, _value):
            raise OSError(PRIVATE + str(tmp_path))

        def flush(self):
            pass

        def close(self):
            pass

    gateway, _ = http_gateway
    with module.diagnostic_logging(stream=BrokenStream()):
        with caplog.at_level(logging.WARNING):
            status, body, _ = call(gateway)
        deadline = time.monotonic() + 3
        while not gateway.operational_diagnostics()['log_delivery_failed'] and time.monotonic() < deadline:
            time.sleep(.01)
        assert status == 429 and PRIVATE.encode() not in body and str(tmp_path).encode() not in body
        assert gateway.operational_diagnostics()['log_delivery_failed'] == 1
        assert PRIVATE not in caplog.text and str(tmp_path) not in caplog.text
        stderr = capfd.readouterr().err
        assert PRIVATE not in stderr and str(tmp_path) not in stderr
        assert 'Summarize the report.' not in stderr + caplog.text + body.decode()


def test_slow_log_destination_does_not_delay_http_response(http_gateway):
    entered, release = Event(), Event()

    class SlowStream:
        def write(self, _value):
            entered.set()
            release.wait(5)

        def flush(self):
            pass

    gateway, _ = http_gateway
    try:
        with module.diagnostic_logging(stream=SlowStream()):
            status, _, _ = call(gateway)
            assert status == 429
            assert entered.wait(1)
    finally:
        release.set()


def test_standalone_sanitizer_survives_failed_warning_delivery(tmp_path):
    from io import BytesIO
    from urllib.error import HTTPError
    handler = logging.FileHandler(tmp_path / PRIVATE / 'missing.log', delay=True)
    stream = BytesIO(b'not json-' + PRIVATE.encode())
    error = HTTPError('https://example.test/' + PRIVATE, 429, PRIVATE, {}, stream)
    module._LOGGER.addHandler(handler)
    try:
        status, body = module.sanitized_upstream_error(error)
        assert status == 429 and PRIVATE.encode() not in body
        assert stream.closed
    finally:
        module._LOGGER.removeHandler(handler)
        handler.close()
        error.close()


@pytest.mark.parametrize('read_fails,close_fails', [(False, True), (True, False), (True, True)])
def test_sanitizer_closes_once_and_preserves_safe_result(read_fails, close_fails, caplog):
    class ErrorStream:
        code = 429
        close_calls = 0

        def read(self, _limit):
            if read_fails:
                raise OSError(PRIVATE)
            return json.dumps({'error': {'type': 'rate_limit_error',
                                         'code': 'rate_limit_exceeded',
                                         'message': PRIVATE}}).encode()

        def close(self):
            self.close_calls += 1
            if close_fails:
                raise OSError(PRIVATE)

    stream = ErrorStream()
    with PrivacyGateway(('127.0.0.1', 0), PRIVATE) as gateway:
        with caplog.at_level(logging.WARNING):
            status, body = gateway.format_upstream_error(stream)
        result = json.loads(body)['error']
        assert status == 429 and stream.close_calls == 1
        assert result['message'] == 'Upstream rejected the request.'
        if read_fails:
            assert set(result) == {'message'}
        else:
            assert result['type'] == 'rate_limit_error'
            assert result['code'] == 'rate_limit_exceeded'
        counts = gateway.operational_diagnostics()
        assert counts['upstream_error_body'] == int(read_fails)
        assert counts['upstream_error_stream_close'] == int(close_fails)
        assert counts['upstream_error_format'] == 0
        assert PRIVATE not in caplog.text and PRIVATE.encode() not in body


def test_logs_endpoint_exposes_authenticated_safe_diagnostics(http_gateway, caplog):
    gateway, _ = http_gateway
    with caplog.at_level(logging.WARNING):
        call(gateway)
    assert call(gateway, '/admin/api/logs', token='wrong', method='GET')[0] == 401
    status, body, _ = call(gateway, '/admin/api/logs', method='GET')
    assert status == 200
    assert json.loads(body)['diagnostic_counts'] == gateway.operational_diagnostics()
    assert json.loads(body)['diagnostic_counts']['upstream_error_body'] == 1
    assert PRIVATE.encode() not in body and PRIVATE not in caplog.text


def test_http_close_failure_keeps_retry_header(http_gateway, monkeypatch, caplog):
    from urllib.error import HTTPError

    gateway, provider = http_gateway
    provider.body = json.dumps({'error': {'type': 'rate_limit_error',
                                          'code': 'rate_limit_exceeded',
                                          'message': PRIVATE}}).encode()
    original_close = HTTPError.close
    def broken_close(error):
        original_close(error)
        raise OSError(PRIVATE)
    monkeypatch.setattr(HTTPError, 'close', broken_close)
    with caplog.at_level(logging.WARNING):
        status, body, headers = call(gateway)
    assert status == 429 and headers['Retry-After'] == '3'
    assert json.loads(body)['error']['code'] == 'rate_limit_exceeded'
    assert gateway.operational_diagnostics()['upstream_error_stream_close'] == 1
    assert PRIVATE.encode() not in body and PRIVATE not in caplog.text


def test_standalone_close_failure_preserves_structured_error(caplog):
    class ErrorStream:
        code = 429
        def read(self, _limit):
            return json.dumps({'error': {'type': 'rate_limit_error', 'message': PRIVATE}}).encode()
        def close(self):
            raise OSError(PRIVATE)
    with caplog.at_level(logging.WARNING):
        status, body = module.sanitized_upstream_error(ErrorStream())
    assert status == 429 and json.loads(body)['error']['type'] == 'rate_limit_error'
    assert PRIVATE.encode() not in body and PRIVATE not in caplog.text
    assert 'upstream_error_stream_close' in caplog.text
