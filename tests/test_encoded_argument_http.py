"""Nonfinite encoded arguments fail at the correct HTTP boundary (#300)."""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread

import pytest

from secure_gateway.gateway import PrivacyGateway


@pytest.mark.parametrize('number', ['NaN', 'Infinity', '-Infinity', '1e400'])
@pytest.mark.parametrize('invalid_request', [True, False])
def test_encoded_argument_errors_have_safe_http_status(tmp_path, number, invalid_request):
    received = []
    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            received.append(self.rfile.read(int(self.headers['Content-Length'])))
            body = json.dumps({'output': [{'type': 'function_call', 'name': 'exec_command',
                               'call_id': 'c', 'arguments': '{"limit":' + number + '}'}]}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    gateway = PrivacyGateway(('127.0.0.1', 0), 'fixture-token',
                             upstreams={'codex': f'http://127.0.0.1:{provider.server_port}'},
                             audit_path=tmp_path / 'audit.sqlite')
    threads = [Thread(target=server.serve_forever) for server in (provider, gateway)]
    for thread in threads:
        thread.start()
    connection = http.client.HTTPConnection('127.0.0.1', gateway.server_port, timeout=10)
    try:
        payload = {'model': 'fixture', 'input': [{'role': 'user', 'content': 'hello'}]}
        if invalid_request:
            payload['input'] = [{'type': 'function_call', 'name': 'exec_command',
                                 'call_id': 'c', 'arguments': '{"limit":' + number + '}'}]
        connection.request('POST', '/codex/responses', json.dumps(payload),
                           {'X-SecureGateway-Token': 'fixture-token',
                            'Authorization': 'Bearer eyJfixture', 'Content-Type': 'application/json'})
        response = connection.getresponse()
        body = response.read()
        assert response.status == (400 if invalid_request else 502)
        assert len(received) == (0 if invalid_request else 1)
        assert number.encode() not in body
    finally:
        connection.close()
        for server in (gateway, provider):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=10)
    with gateway.audit.connect() as db:
        row = db.execute('SELECT status,outcome,upstream_attempted FROM requests').fetchone()
    assert tuple(row) == ((400, 'blocked', 0) if invalid_request else (502, 'restore_error', 1))
