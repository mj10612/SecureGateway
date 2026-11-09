"""Digit-leading path segments must stay one word and round-trip through tool calls.

Before the NUMBER boundary fix, ``89_8lzey`` tokenized as NUMBER ``89`` plus
WORD ``_8lzey``. Their aliases were emitted with no separator, strict restore
rejected the glued alias, and the gateway answered 502 for the tool call.
"""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
import urllib.request

import pytest

from secure_gateway.engine.tokenizer import TOKEN_SPLIT_REGEX
from secure_gateway.gateway import PrivacyGateway

DIGIT_SEGMENTS = ["89_8lzey", "2024_report", "3d_models", "9aaa9a_9", "12ab34cd", "3é4x", "3é_x",
                  "5km²", "१२_अ", "٣_ب"]
CONTROL_SEGMENTS = ["k3vqzpwa", "v2", "2024", "१२", "release_2024"]
PATHS = ([rf"C:\Users\fixture\AppData\Local\Temp\securegateway-package-{segment}\private\Report.py"
          for segment in ("89_8lzey", "k3vqzpwa")]
         + [f"/home/fixture/{segment}/notes.md" for segment in DIGIT_SEGMENTS + CONTROL_SEGMENTS]
         + [r"D:\work\2024_report\notes.md", "/srv/3d_models/a.obj", "/srv/2024年报告/a.txt"])


def chunks(text):
    return [(match.lastgroup, match[0]) for match in TOKEN_SPLIT_REGEX.finditer(text)
            if match.lastgroup not in {"WHITESPACE", "OTHER"}]


@pytest.mark.parametrize("segment", DIGIT_SEGMENTS + ["release_2024"])
def test_digit_word_segment_is_one_word(segment):
    assert chunks(segment) == [("WORD", segment)]


@pytest.mark.parametrize("text,expected", [
    ("2024", [("NUMBER", "2024")]),
    ("१२", [("NUMBER", "१२")]),
    ("$5,000.00", [("NUMBER", "$5,000.00")]),
    ("₩1,000", [("NUMBER", "₩1,000")]),
    ("100%", [("NUMBER", "100%")]),
    ("5kg", [("NUMBER", "5kg")]),
    ("3.5x", [("NUMBER", "3.5x")]),
    ("paid 100% of 5kg, (12)", [("WORD", "paid"), ("NUMBER", "100%"), ("WORD", "of"),
                                ("NUMBER", "5kg"), ("NUMBER", "12")]),
    ("100%abc", [("NUMBER", "100%abc")]),
    ("3개", [("HANGUL_WORD", "3개")]),
    ("owner@example.invalid", [("EMAIL", "owner@example.invalid")]),
    ("call 555-010-0199", [("WORD", "call"), ("PHONE", "555-010-0199")]),
    ("10.0.0.1", [("IP", "10.0.0.1")]),
    ("123e4567-e89b-12d3-a456-426614174000", [("UUID", "123e4567-e89b-12d3-a456-426614174000")]),
])
def test_standalone_numbers_and_sensitive_formats_keep_their_kind(text, expected):
    assert chunks(text) == expected


@pytest.fixture
def gateway(tmp_path):
    server = PrivacyGateway(("127.0.0.1", 0), "fixture-token", {"codex": "http://127.0.0.1:9"},
                            state_dir=tmp_path / "sessions")
    try:
        yield server
    finally:
        server.server_close()


def tool_payload(path):
    return {"model": "fixture", "input": [{"role": "user", "content": "Review the report."}],
            "tools": [{"type": "function", "name": "read_file", "parameters": {
                "type": "object", "properties": {"file_path": {"type": "string", "default": path}},
                "required": ["file_path"]}}]}


@pytest.mark.parametrize("path", PATHS)
def test_gateway_session_tool_default_path_request_response_roundtrip(gateway, path):
    session = gateway.get_session("codex")
    masked = session.request(tool_payload(path))
    tool = masked["tools"][0]
    alias_path = tool["parameters"]["properties"]["file_path"]["default"]
    assert alias_path != path
    body = json.dumps({"output": [{"type": "function_call", "call_id": "call_digit", "name": tool["name"],
                                   "arguments": json.dumps({"file_path": alias_path})}]}).encode()
    restored = json.loads(session.response(body, "application/json"))["output"][0]
    assert restored["name"] == "read_file"
    assert json.loads(restored["arguments"]) == {"file_path": path}
    assert session.restore(session.mask(f"Open {path} now.")) == f"Open {path} now."


@contextmanager
def serving(*servers):
    threads = [Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
               for server in servers]
    for thread in threads:
        thread.start()
    try:
        yield
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(5)


@pytest.mark.parametrize("segment", ["89_8lzey", "2024_report", "3d_models", "k3vqzpwa"])
def test_fake_http_tool_call_and_output_replay_restore_digit_paths(tmp_path, segment):
    private_file = tmp_path / segment / "private" / "Report.py"
    private_file.parent.mkdir(parents=True)
    private_file.write_text("fixture report body", encoding="utf-8")
    seen = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(json.dumps(payload))
            item = payload["input"][-1]
            if item.get("type") != "function_call_output":
                tool = payload["tools"][0]
                key = next(iter(tool["parameters"]["properties"]))
                default = tool["parameters"]["properties"][key]["default"]
                result = {"output": [{"type": "function_call", "call_id": "call_digit", "name": tool["name"],
                                      "arguments": json.dumps({key: default})}]}
            else:
                result = {"output": [{"type": "message", "role": "assistant",
                                      "content": [{"type": "output_text", "text": item["output"]}]}]}
            data = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    gateway = PrivacyGateway(("127.0.0.1", 0), "fixture-token",
                             {"codex": f"http://127.0.0.1:{provider.server_port}"},
                             state_dir=tmp_path / "sessions")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def send(value):
        request = urllib.request.Request(
            f"http://127.0.0.1:{gateway.server_port}/codex/responses", data=json.dumps(value).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer eyJ-offline-fixture-only",
                     "X-SecureGateway-Token": "fixture-token"})
        with opener.open(request, timeout=20) as response:
            return json.load(response)

    with serving(provider, gateway):
        payload = tool_payload(str(private_file))
        call = send(payload)["output"][0]
        actual = Path(json.loads(call["arguments"])["file_path"])
        assert actual == private_file
        output = actual.read_text(encoding="utf-8")
        payload["input"].extend([call, {"type": "function_call_output", "call_id": "call_digit", "output": output}])
        result = send(payload)
    assert result["output"][0]["content"][0]["text"] == output
    assert len(seen) == 2
    assert all(segment not in request and str(private_file) not in request for request in seen)
