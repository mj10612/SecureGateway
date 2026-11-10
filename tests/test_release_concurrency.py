"""Concurrent, isolated tool calls through a loopback provider."""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Barrier, Event, Thread

import pytest

from secure_gateway.gateway import PrivacyGateway


def test_two_conversations_restore_concurrent_tool_arguments():
    barrier = Barrier(2, timeout=30)
    seen = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            seen.append(payload)
            barrier.wait()
            tool = payload['tools'][0]
            key, prop = next(iter(tool['parameters']['properties'].items()))
            body = json.dumps({'output': [{'type': 'function_call', 'call_id': 'call_fixture',
                'name': tool['name'], 'arguments': json.dumps({key: prop['default']})}]}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    gateway = PrivacyGateway(('127.0.0.1', 0), 'fixture-token',
        upstreams={'codex': f'http://127.0.0.1:{provider.server_port}'},
        max_provider_requests=2)
    release_handlers = Event()
    original_release = gateway.release_admission

    def defer_release(agent):
        # The client joins can take up to 90 seconds on a loaded runner.
        # Always release the admission slot even if that bound is exceeded.
        release_handlers.wait(120)
        original_release(agent)

    gateway.release_admission = defer_release
    servers = [provider, gateway]
    server_threads = [Thread(target=server.serve_forever, daemon=True) for server in servers]
    for thread in server_threads:
        thread.start()
    results = {}
    errors = []

    def request(index):
        path = r'C:\PrivateCustomer1\한글 폴더\file.txt' if index == 1 else '/tmp/PrivateCustomer2/한글 폴더/file.txt'
        payload = {'input': f'Read PrivateCustomer{index}', 'tools': [{'type': 'function',
            'name': 'read_file', 'parameters': {'type': 'object', 'properties': {
                'file_path': {'type': 'string', 'default': path}}, 'required': ['file_path']}}]}
        conn = http.client.HTTPConnection('127.0.0.1', gateway.server_port, timeout=40)
        try:
            conn.request('POST', '/codex/responses', json.dumps(payload), {
                'Content-Type': 'application/json', 'X-SecureGateway-Token': 'fixture-token',
                'Authorization': 'Bearer eyJ-fixture', 'session_id': f'conversation-{index}'})
            response = conn.getresponse()
            assert response.status == 200
            result = json.loads(response.read())['output'][0]
            results[index] = json.loads(result['arguments'])['file_path']
        except Exception as exc:
            errors.append(type(exc).__name__)
        finally:
            conn.close()

    clients = [Thread(target=request, args=(index,), daemon=True) for index in (1, 2)]
    try:
        for client in clients:
            client.start()
        for client in clients:
            client.join(45)
        assert all(not client.is_alive() for client in clients)
        assert not errors
        expected = {1: r'C:\PrivateCustomer1\한글 폴더\file.txt',
                    2: '/tmp/PrivateCustomer2/한글 폴더/file.txt'}
        if results != expected:
            pytest.fail('Tool argument restoration mismatch', pytrace=False)
        assert len(seen) == 2
        if 'PrivateCustomer' in json.dumps(seen):
            pytest.fail('Provider request was not masked', pytrace=False)
        with gateway.admission:
            assert gateway.admitted_requests == 2
            release_handlers.set()
            assert gateway.admission.wait_for(lambda: gateway.admitted_requests == 0, timeout=30)
    finally:
        release_handlers.set()
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in server_threads:
            thread.join(10)


def test_silent_stream_keeps_connection_open_until_restored_event():
    import time
    from threading import Event

    release = Event()

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            self.wfile.flush()
            release.wait(30)
            event = {'type': 'response.output_text.delta', 'item_id': 'message', 'delta': 'ready '}
            self.wfile.write(('data: ' + json.dumps(event) + '\n\ndata: [DONE]\n\n').encode())
            self.wfile.flush()

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    gateway = PrivacyGateway(('127.0.0.1', 0), 'fixture-token',
        upstreams={'codex': f'http://127.0.0.1:{provider.server_port}'})
    servers = [provider, gateway]
    workers = [Thread(target=server.serve_forever, daemon=True) for server in servers]
    for worker in workers:
        worker.start()
    conn = http.client.HTTPConnection('127.0.0.1', gateway.server_port, timeout=30)
    try:
        started = time.monotonic()
        conn.request('POST', '/codex/responses', b'{"input":"hello","stream":true}', {
            'Content-Type': 'application/json', 'X-SecureGateway-Token': 'fixture-token',
            'Authorization': 'Bearer eyJ-fixture'})
        response = conn.getresponse()
        header_at = time.monotonic()
        assert response.status == 200
        chunks = []
        first_event_at = None
        for line in response:
            chunks.append(line)
            if b'gateway waiting' in line:
                assert gateway.admitted_requests == 1
                release.set()
            if line.startswith(b'data: ') and b'[DONE]' not in line and first_event_at is None:
                first_event_at = time.monotonic()
        completed_at = time.monotonic()
        body = b''.join(chunks)
        assert b'gateway connected' in body and b'gateway waiting' in body
        assert b'ready ' in body and b'[DONE]' in body
        assert first_event_at is not None
        assert header_at <= first_event_at <= completed_at
        assert first_event_at - started >= 5
        with gateway.admission:
            assert gateway.admission.wait_for(lambda: gateway.admitted_requests == 0, timeout=10)
            assert 'mask_lock_wait_ms' in gateway.recent_timings[-1]
    finally:
        release.set()
        conn.close()
        for server in servers:
            server.shutdown()
            server.server_close()
        for worker in workers:
            worker.join(10)
