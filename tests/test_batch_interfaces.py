"""Exercise release features through their public local interfaces."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sys
from threading import Thread
import urllib.error
import urllib.request

from click.testing import CliRunner
import pytest

from secure_gateway.antigravity_sdk import antigravity_endpoint
from secure_gateway.cli import main
from secure_gateway.gateway import PrivacyGateway
from secure_gateway.hooks import configure


def test_utf8_stdin_and_file_roundtrip(tmp_path):
    runner = CliRunner()
    text = "비밀고객 ConfidentialCustomer\r\n"
    source = tmp_path / "input.txt"
    source.write_bytes(text.encode())
    snapshot = tmp_path / "snapshot.enc"
    args = ["--session-file", str(snapshot), "--session-password", "fixture-password", "--json-output"]
    masked = runner.invoke(main, ["mask", "--input-file", str(source), *args])
    assert masked.exit_code == 0, masked.output
    alias = json.loads(masked.output)["masked_text"]
    restored = runner.invoke(main, ["unmask", *args], input=alias)
    assert restored.exit_code == 0, restored.output
    assert json.loads(restored.output)["unmasked_text"] == text


def test_cli_rejects_conflicting_inputs_and_invalid_utf8(tmp_path):
    source = tmp_path / "input.txt"
    source.write_bytes(b"\xff")
    runner = CliRunner()
    result = runner.invoke(main, ["mask", "--input-file", str(source)])
    assert result.exit_code != 0 and "UTF-8" in result.output
    result = runner.invoke(main, ["mask", "text", "--input-file", str(source)])
    assert result.exit_code != 0 and "multiple inputs" in result.output


@pytest.mark.parametrize("code, options", [
    ("import sys;sys.stdout.buffer.write(b'\\xff')", []),
    ("import time;time.sleep(10)", ["--timeout", "0.1"]),
    ("print('private-secret-output')", ["--max-output-bytes", "4"]),
])
def test_exec_failure_emits_no_child_output(tmp_path, code, options):
    state = tmp_path / "state"
    configure(tmp_path / "hooks.json", state, True)
    result = CliRunner().invoke(main, ["exec", "--state-dir", str(state),
        "--session-id", "fixture", *options, "--", sys.executable, "-c", code])
    assert result.exit_code == 1
    assert "Local execution/masking failed" in result.output
    assert "private-secret-output" not in result.output and "Traceback" not in result.output


@contextmanager
def running_gateway(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "fixture-token", upstreams={},
                        audit_path=tmp_path / "logs.sqlite3") as gateway:
        worker = Thread(target=gateway.serve_forever)
        worker.start()
        try:
            yield gateway
        finally:
            gateway.shutdown()
            worker.join(2)


def test_session_diagnostics_and_credential_filter_are_authenticated(tmp_path):
    with running_gateway(tmp_path) as gateway:
        url = f"http://127.0.0.1:{gateway.server_port}"
        with pytest.raises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(url + "/admin/api/sessions")
        assert denied.value.code == 401
        denied.value.close()
        for credential in ["credential-one", "credential-two"]:
            request_id = gateway.audit.begin("Claude Code", "claude", "claude_subscription", "/claude/v1/messages", "fixture")
            meta = {"agent": "Claude Code", "account_ref": None, "credential_ref": credential,
                    "model": None, "status": 200, "outcome": "completed", "upstream_attempted": 1,
                    "duration_ms": 1, "input_bytes": 0, "masked_bytes": 0, "output_bytes": 0, "new_aliases": 0}
            gateway.audit.finish(request_id, meta)
        for path in ["/admin/api/sessions", "/admin/api/logs?credential_ref=credential-one"]:
            request = urllib.request.Request(url + path, headers={"X-SecureGateway-Token": gateway.token})
            with urllib.request.urlopen(request) as response:
                data = json.load(response)
            if "logs" in path:
                assert data["summary"]["total"] == 1
                assert data["rows"][0]["credential_ref"] == "credential-one"
            else:
                assert data["active_requests"] == 0 and data["max_active_requests"] == 32
                assert "fixture-token" not in json.dumps(data)


@pytest.mark.parametrize("status", [200, 429])
def test_sdk_preserves_retry_headers_without_private_headers(status):
    class LocalGateway(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            body = b'{"choices":[]}'
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Retry-After", "3")
            self.send_header("x-ratelimit-remaining", "0")
            self.send_header("X-Private-Header", "secret")
            self.end_headers()
            self.wfile.write(body)
    with ThreadingHTTPServer(("127.0.0.1", 0), LocalGateway) as gateway:
        worker = Thread(target=gateway.serve_forever)
        worker.start()
        try:
            with antigravity_endpoint(f"http://127.0.0.1:{gateway.server_port}", "t" * 32, "xai-fixture") as endpoint:
                request = urllib.request.Request(endpoint + "/chat/completions", b'{"messages":[]}', {"Content-Type": "application/json"})
                try:
                    response = urllib.request.urlopen(request)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    assert response.headers["Retry-After"] == "3"
                    assert response.headers["x-ratelimit-remaining"] == "0"
                    assert response.headers.get("X-Private-Header") is None
        finally:
            gateway.shutdown()
            worker.join(2)
