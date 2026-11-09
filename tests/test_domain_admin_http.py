"""Admin policy changes affect actual forwarded HTTP payloads and survive restart."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import urllib.error
import urllib.request

import pytest

from secure_gateway.gateway import PrivacyGateway


@contextmanager
def serving(server):
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": .01})
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


def request(server, path, payload=None, *, token="local-token", origin=None):
    headers = {"X-SecureGateway-Token": token, "Authorization": "Bearer eyJfixture", "Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(f"http://127.0.0.1:{server.server_port}" + path,
                                 json.dumps(payload).encode() if payload is not None else None, headers)
    with urllib.request.urlopen(req, timeout=3) as response:
        return json.load(response)


def test_authenticated_toggle_payload_and_page(tmp_path):
    seen = []
    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(payload)
            body = json.dumps({"content": [{"type": "text", "text": payload["input"][0]["content"]}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    with serving(ThreadingHTTPServer(("127.0.0.1", 0), Provider)) as provider:
        with serving(PrivacyGateway(("127.0.0.1", 0), "local-token", upstreams={"codex": f"http://127.0.0.1:{provider.server_port}"}, state_dir=tmp_path)) as gateway:
            status = request(gateway, "/admin/api/domain-policy")
            assert status["enabled"]["defense"]
            page = request(gateway, "/admin/api/domain-terms?domain=defense&query=radar&limit=2")
            assert len(page["entries"]) <= 2
            policy = {"enabled": {"defense": False, "automotive": True, "semiconductor": True}}
            with pytest.raises(urllib.error.HTTPError) as caught:
                request(gateway, "/admin/api/domain-policy", policy, token="wrong")
            assert caught.value.code == 401
            caught.value.close()
            with pytest.raises(urllib.error.HTTPError) as caught:
                request(gateway, "/admin/api/domain-policy", policy, origin="https://foreign.invalid")
            assert caught.value.code == 403
            caught.value.close()
            request(gateway, "/admin/api/domain-policy", policy)
            text = "Please review the battery management system and atomic layer deposition before approval."
            result = request(gateway, "/codex/responses", {"model": "fixture", "input": [{"role": "user", "content": text}]})
            assert result["content"][0]["text"] == text
            assert "battery management system" not in json.dumps(seen[-1])
            assert "atomic layer deposition" not in json.dumps(seen[-1])
            assert "before approval" in json.dumps(seen[-1])
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=tmp_path) as gateway:
        assert gateway.domain_status()["enabled"] == policy["enabled"]
