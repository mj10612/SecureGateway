"""Regression coverage for atomic opaque hyphen identifiers."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
from threading import Thread
import urllib.request

import pytest

from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.engine.natural_languages import tokenize as natural_tokenize
from secure_gateway.engine.tokenizer import MultilingualTokenizer
from secure_gateway.engine.strategies import StrategyGenerator
from secure_gateway.gateway import GatewaySession, PrivacyGateway
from secure_gateway.models import MaskMode, SurrogateStrategy, TokenType


PART_NUMBERS = ["TV-592", "ABC-12", "A1-234", "TV-592-7", "TV-592-A"]


@pytest.mark.parametrize("value", PART_NUMBERS)
def test_hyphen_part_number_is_one_text_chunk(value):
    chunks = MultilingualTokenizer.tokenize(value)

    assert [(chunk.kind, chunk.text) for chunk in chunks] == [("PART_NUMBER", value)]
    assert chunks[0].is_word
    assert not chunks[0].is_number


@pytest.mark.parametrize(
    "value",
    [
        "preTV-592x",
        "TV-592x",
        "TV--592",
        "TV_592",
        "TV-",
        "-592",
        "TV-592.1",
    ],
)
def test_hyphen_part_number_requires_identifier_boundaries(value):
    assert not any(
        chunk.kind == "PART_NUMBER" for chunk in MultilingualTokenizer.tokenize(value)
    )


def test_unicode_punctuation_separates_hyphen_part_numbers():
    chunks = MultilingualTokenizer.tokenize("TV-592，ABC-12")

    assert [(chunk.kind, chunk.text) for chunk in chunks] == [
        ("PART_NUMBER", "TV-592"),
        ("OTHER", "，"),
        ("PART_NUMBER", "ABC-12"),
    ]


def test_protected_url_email_secret_and_code_spans_keep_precedence():
    chunks = MultilingualTokenizer.tokenize(
        "https://example.test/TV-592 tv-592@example.test "
        "sk-abcdefghijklmnopqrstuvwxyz `ABC-12`"
    )

    assert [(chunk.kind, chunk.text) for chunk in chunks if chunk.kind in {
        "URL", "EMAIL", "SECRET", "CODE_BLOCK", "PART_NUMBER"
    }] == [
        ("URL", "https://example.test/TV-592"),
        ("EMAIL", "tv-592@example.test"),
        ("SECRET", "sk-abcdefghijklmnopqrstuvwxyz"),
        ("CODE_BLOCK", "`ABC-12`"),
    ]


@pytest.mark.parametrize("language", ["en", "fr", "zh", "ja"])
def test_natural_language_tokenizers_keep_part_number_span(language):
    chunks = natural_tokenize("TV-592", language)

    assert [(chunk.kind, chunk.text) for chunk in chunks] == [("PART_NUMBER", "TV-592")]


@pytest.mark.parametrize("value", ["2024_report", "89_8lzey"])
def test_digit_leading_number_boundary_remains_one_word(value):
    chunks = MultilingualTokenizer.tokenize(value)

    assert [(chunk.kind, chunk.text) for chunk in chunks] == [("WORD", value)]


@pytest.mark.parametrize("value", PART_NUMBERS[:3])
def test_text_mask_uses_one_stable_mapping_for_repeated_part_numbers(value):
    engine = MaskingEngine()
    generator = StrategyGenerator(SurrogateStrategy.BRACKET)
    forward = {}
    reverse = {}
    source = f"Review {value}; then review {value}."

    result = engine.mask_text(
        source,
        "hyphen-text",
        generator,
        forward,
        reverse,
        mode=MaskMode.CONTENT_WORDS,
        language="en",
    )
    part_mapping = next(mapping for mapping in reverse.values() if mapping.original == value)

    assert result.masked_text.count(part_mapping.surrogate) == 2
    assert part_mapping.token_type == TokenType.ENTITY
    assert part_mapping.occurrence_count == 2
    assert not any(mapping.original in {value.split("-", 1)[0], value.rsplit("-", 1)[-1]}
                    for mapping in reverse.values())
    assert engine.unmask(result.masked_text, "hyphen-text", reverse).unmasked_text == source


@pytest.mark.parametrize("mask_numbers", [False, True])
def test_executable_subtraction_is_not_merged_and_number_policy_survives(mask_numbers):
    engine = MaskingEngine()
    generator = StrategyGenerator(SurrogateStrategy.BRACKET)
    forward = {}
    reverse = {}
    source = "x-1\nx - 1\nTV-592"

    result = engine.mask_code(
        source,
        "hyphen-code-subtraction",
        generator,
        forward,
        reverse,
        language="python",
        mask_numbers=mask_numbers,
    )

    assert "-" in result.masked_text
    assert " - " in result.masked_text
    assert not any(mapping.original == "x-1" for mapping in reverse.values())
    assert not any(mapping.original == "TV-592" for mapping in reverse.values())
    assert any(mapping.original == "1" for mapping in reverse.values()) is mask_numbers
    assert engine.unmask(
        result.masked_text,
        "hyphen-code-subtraction",
        reverse,
        strict=True,
    ).unmasked_text == source


@pytest.mark.parametrize("mask_numbers", [False, True])
def test_opaque_code_literals_keep_complete_hyphen_part_numbers(mask_numbers):
    engine = MaskingEngine()
    generator = StrategyGenerator(SurrogateStrategy.BRACKET)
    forward = {}
    reverse = {}
    source = 'part = "TV-592"\n# ABC-12\n'

    result = engine.mask_code(
        source,
        "hyphen-code-opaque",
        generator,
        forward,
        reverse,
        language="python",
        mask_numbers=mask_numbers,
    )

    assert "TV-592" not in result.masked_text
    assert "ABC-12" not in result.masked_text
    assert any(mapping.original == "TV-592" and mapping.token_type == TokenType.LITERAL
               for mapping in reverse.values())
    assert not any(mapping.original in {"TV", "592", "ABC", "12"}
                   for mapping in reverse.values())
    assert engine.unmask(
        result.masked_text,
        "hyphen-code-opaque",
        reverse,
        strict=True,
    ).unmasked_text == source


@pytest.mark.parametrize("mask_numbers", [False, True])
def test_gateway_prose_part_number_alias_replays_with_both_number_settings(mask_numbers):
    gateway = GatewaySession(mask_numbers=mask_numbers)
    source = "Fix TV-592 and then check TV-592."

    masked = gateway.mask(source)
    aliases = [
        mapping.surrogate
        for mapping in gateway.session.reverse_store.values()
        if mapping.original == "TV-592"
    ]

    assert len(aliases) == 1
    assert masked.count(aliases[0]) == 2
    assert gateway.restore(masked) == source


def test_existing_prefix_mapping_does_not_split_later_part_number():
    gateway = GatewaySession()
    gateway.mask("TV")
    masked = gateway.mask("TV-592")

    assert any(mapping.original == "TV-592" for mapping in gateway.session.reverse_store.values())
    assert not any(mapping.original == "592" for mapping in gateway.session.reverse_store.values())
    assert gateway.restore(masked) == "TV-592"


@contextmanager
def serving(*servers):
    threads = [
        Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        for server in servers
    ]
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


def _tool_payload(path):
    return {
        "model": "fixture",
        "input": [{"role": "user", "content": "Review TV-592 now."}],
        "tools": [{
            "type": "function",
            "name": "read_file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "default": path},
                },
                "required": ["file_path"],
            },
        }],
    }


def test_gateway_fake_http_hides_atomic_part_numbers_and_replays_tool_result(tmp_path):
    part_path = tmp_path / "TV-592" / "report.txt"
    part_path.parent.mkdir()
    part_path.write_text("fixture report body", encoding="utf-8")
    captured = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            captured.append(payload)
            item = payload["input"][-1]
            if item.get("type") != "function_call_output":
                tool = payload["tools"][0]
                path_alias = tool["parameters"]["properties"]["file_path"]["default"]
                arguments = json.dumps({
                    "file_path": path_alias,
                    "part": payload["input"][0]["content"].split()[-2],
                    "count": 3,
                    "enabled": True,
                })
                result = {"output": [{
                    "type": "function_call",
                    "call_id": "call_hyphen",
                    "name": tool["name"],
                    "arguments": arguments,
                }]}
            else:
                result = {"output": [{
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": item["output"]}],
                }]}
            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    gateway = PrivacyGateway(
        ("127.0.0.1", 0),
        "fixture-token",
        {"codex": f"http://127.0.0.1:{provider.server_port}"},
        state_dir=tmp_path / "sessions",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def send(payload):
        request = urllib.request.Request(
            f"http://127.0.0.1:{gateway.server_port}/codex/responses",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer eyJ-offline-fixture-only",
                "X-SecureGateway-Token": "fixture-token",
            },
        )
        with opener.open(request, timeout=20) as response:
            return json.load(response)

    output = json.dumps({
        "part": "TV-592",
        "path": str(part_path),
        "count": 3,
        "enabled": True,
    }, separators=(",", ":"))
    try:
        with serving(provider, gateway):
            payload = _tool_payload(str(part_path))
            call = send(payload)["output"][0]
            arguments = json.loads(call["arguments"])
            assert arguments == {
                "file_path": str(part_path),
                "part": "TV-592",
                "count": 3,
                "enabled": True,
            }
            payload["input"].extend([
                call,
                {"type": "function_call_output", "call_id": "call_hyphen", "output": output},
            ])
            result = send(payload)
    finally:
        gateway.server_close()
        provider.server_close()

    assert json.loads(result["output"][0]["content"][0]["text"]) == json.loads(output)
    assert len(captured) == 2
    serialized = json.dumps(captured, ensure_ascii=False)
    assert "TV-592" not in serialized
    assert str(part_path) not in serialized
    assert not re.search(r"(?:private_symbol|smcp_ID)_\d+-732846\d{12}", serialized)
    assert all(
        isinstance(item["input"][0]["content"], str)
        for item in captured
    )
