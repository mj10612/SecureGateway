"""Regression coverage for the gateway issues in the 0.6 release."""

import json
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
import urllib.parse
from threading import Event, Thread

import pytest

from secure_mcp.gateway import EXEC_GRAMMAR, GatewaySession, PrivacyGateway


@pytest.mark.parametrize("tag", ["type", "permission_mode", "platform", "source"])
def test_safeguards_reject_private_tags(tag):
    with pytest.raises(ValueError):
        GatewaySession().request({"messages": [], "safeguards": {tag: "PrivateCustomer"}})


def test_safeguards_reject_private_keys():
    with pytest.raises(ValueError):
        GatewaySession().request({"messages": [], "safeguards": {"PrivateCustomer": True}})


@pytest.mark.parametrize("kind", ["auto", "none", "any", "tool"])
def test_claude_tool_choice_preserves_tags(kind):
    choice = {"type": kind, "disable_parallel_tool_use": True}
    if kind == "tool":
        choice["name"] = "PrivateTool"
    session = GatewaySession()
    masked = session.request({"messages": [], "tool_choice": choice})["tool_choice"]
    assert masked["type"] == kind
    assert masked["disable_parallel_tool_use"] is True
    if kind == "tool":
        assert session.restore(masked["name"]) == "PrivateTool"


def test_context_editing_preserves_controls_and_masks_tool_names():
    session = GatewaySession()
    value = {"edits": [{"type": "clear_tool_uses_20250919",
                         "trigger": {"type": "input_tokens", "value": 30000},
                         "keep": {"type": "tool_uses", "value": 3},
                         "clear_at_least": {"type": "input_tokens", "value": 5000},
                         "exclude_tools": ["PrivateTool"], "clear_tool_inputs": True}]}
    masked = session.request({"messages": [], "context_management": value})["context_management"]
    edit = masked["edits"][0]
    assert edit["trigger"] == value["edits"][0]["trigger"]
    assert edit["keep"] == value["edits"][0]["keep"]
    assert edit["type"] == "clear_tool_uses_20250919"
    assert session.restore(edit["exclude_tools"][0]) == "PrivateTool"


@pytest.mark.parametrize("extra", [{"syntax": "PrivateCustomer"}, {"secret": "PrivateCustomer"}, {"definition": []}, {"type": ["grammar"]}])
def test_pinned_grammar_rejects_invalid_format_fields(extra):
    format_value = {"type": "grammar", "syntax": "lark", "definition": EXEC_GRAMMAR, **extra}
    with pytest.raises(ValueError, match="grammar"):
        GatewaySession().request({"input": "hi", "tools": [{"type": "custom", "name": "exec", "format": format_value}]})


@pytest.mark.parametrize("constraint", [{"maxLength": 12}, {"minLength": 1}, {"format": "email"}])
def test_schema_rejects_constraints_that_aliases_cannot_preserve(constraint):
    with pytest.raises(ValueError):
        GatewaySession().request({"messages": [], "tools": [{"name": "lookup", "input_schema": {"type": "string", "enum": ["Confidential"], **constraint}}]})


@pytest.mark.parametrize("keyword", ["additionalItems", "unevaluatedItems", "contentSchema"])
def test_schema_validates_every_schema_bearing_keyword(keyword):
    with pytest.raises(ValueError, match="pattern"):
        GatewaySession().request({"messages": [], "tools": [{"name": "lookup", "input_schema": {keyword: {"pattern": "secret.*"}}}]})


def test_refs_follow_structure_and_decode_percent_escapes():
    session = GatewaySession()
    schema = {"properties": {"properties": {"properties": {"Secret Name": {"type": "string"}}}},
              "$ref": "#/properties/properties/properties/Secret%20Name"}
    masked = session.request({"messages": [], "tools": [{"name": "lookup", "input_schema": schema}]})["tools"][0]["input_schema"]
    target = masked
    for name in urllib.parse.unquote(masked["$ref"])[2:].split("/"):
        target = target[name.replace("~1", "/").replace("~0", "~")]
    assert target == {"type": "string"}


@pytest.mark.parametrize("kind", ["response.refusal.delta", "response.reasoning_summary_text.delta"])
def test_split_response_text_aliases_restore(kind):
    session = GatewaySession()
    alias = session.mask("PrivateCustomer", code=True)
    events = [{"type": kind, "item_id": "msg_1", "output_index": 0, "content_index": 0, "summary_index": 0, "delta": part}
              for part in (alias[:7], alias[7:])]
    body = "".join("data: " + json.dumps(event) + "\n\n" for event in events).encode()
    restored = session.response(body, "text/event-stream", dialect="responses").decode()
    assert "PrivateCustomer" in restored
    assert "private_symbol" not in restored


@pytest.mark.parametrize("ending", ["\r", "\n", "\r\n"])
def test_sse_bom_and_all_standard_line_endings(ending):
    session = GatewaySession()
    alias = session.mask("PrivateCustomer", code=True)
    event = {"type": "response.output_text.delta", "item_id": "msg_1", "delta": alias}
    body = ("\ufeffdata: " + json.dumps(event) + ending * 2).encode()
    assert "PrivateCustomer" in session.response(body, "text/event-stream", dialect="responses").decode()


def test_numeric_json_aliases_restore_exactly():
    session = GatewaySession(mask_numbers=True)
    alias = int(session.mask("42", code=True))
    assert session.values({"amount": alias, "ordinary": 7, "bool": True}, restore=True) == {"amount": 42, "ordinary": 7, "bool": True}


def test_numeric_json_alias_rejects_non_json_source_literal():
    session = GatewaySession(mask_numbers=True)
    alias = int(session.mask("0x2A", code=True))
    with pytest.raises(ValueError):
        session.values(alias, restore=True)


def test_upstream_json_requires_object():
    with pytest.raises(ValueError):
        GatewaySession().response(b"[]", "application/json")


@pytest.mark.parametrize("block", [None, []])
def test_malformed_claude_sse_is_controlled(block):
    body = ("data: " + json.dumps({"type": "content_block_start", "index": 0, "content_block": block}) + "\n\n").encode()
    with pytest.raises(ValueError):
        GatewaySession().response(body, "text/event-stream", dialect="claude")


def test_gateway_admission_and_private_diagnostics():
    gateway = PrivacyGateway(("127.0.0.1", 0), "fixture-token", upstreams={"claude": "http://127.0.0.1:1", "codex": "http://127.0.0.1:2"}, max_active_requests=2, max_provider_requests=1)
    try:
        assert gateway.try_admit("claude")
        assert not gateway.try_admit("claude")
        assert gateway.try_admit("codex")
        gateway.release_admission("claude")
        gateway.release_admission("codex")
        session = gateway.get_session("claude")
        session.mask("PrivateCustomer", code=True)
        diagnostics = gateway.session_diagnostics()
        assert diagnostics["providers"]["claude"]["mapping_count"] == 1
        assert "PrivateCustomer" not in json.dumps(diagnostics)
    finally:
        gateway.server_close()


def test_server_close_waits_before_clearing_active_aliases():
    gateway = PrivacyGateway(("127.0.0.1", 0), "fixture-token", upstreams={"claude": "http://127.0.0.1:1"})
    session = gateway.get_session("claude")
    alias = session.mask("PrivateCustomer", code=True)
    assert gateway.try_admit("claude")
    closed = Event()
    thread = Thread(target=lambda: (gateway.server_close(), closed.set()))
    thread.start()
    assert not closed.wait(0.1)
    assert session.restore(alias) == "PrivateCustomer"
    gateway.release_admission("claude")
    thread.join(5)
    assert closed.is_set()


@pytest.fixture
def live_gateway():
    state = SimpleNamespace(body=b"{}", content_type="application/json", requests=[],
                            entered=Event(), release=Event(), hold=False, broken_catalog=False,
                            close_on_stop=False, stopped=Event())

    class Source(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            state.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            state.entered.set()
            if state.hold:
                assert state.release.wait(5)
            self.send_response(200)
            self.send_header("Content-Type", state.content_type)
            self.send_header("Content-Length", str(len(state.body)))
            self.end_headers()
            self.wfile.write(state.body)

        def do_GET(self):
            self.send_response(200)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            self.wfile.write(b"5\r\n{}\r\n")
            self.close_connection = True

    source = ThreadingHTTPServer(("127.0.0.1", 0), Source)
    gateway = PrivacyGateway(("127.0.0.1", 0), "fixture-token",
                             upstreams={"codex": "http://127.0.0.1:" + str(source.server_port),
                                        "claude": "http://127.0.0.1:" + str(source.server_port)},
                             max_active_requests=2, max_provider_requests=1)
    source_thread = Thread(target=source.serve_forever, daemon=True)
    def serve_gateway():
        try:
            gateway.serve_forever()
        finally:
            if state.close_on_stop:
                gateway.server_close()
            state.stopped.set()

    gateway_thread = Thread(target=serve_gateway, daemon=True)
    source_thread.start()
    gateway_thread.start()

    def request(payload=None, *, method="POST", path="/codex/responses", declared_length=None):
        conn = http.client.HTTPConnection("127.0.0.1", gateway.server_port, timeout=3)
        body = json.dumps({"input": "hi"} if payload is None else payload).encode() if method == "POST" else None
        headers = {"X-SecureMCP-Token": "fixture-token", "Authorization": "Bearer eyJ-fixture"}
        if path.startswith("/claude"):
            headers["Authorization"] = "Bearer sk-ant-oat-fixture"
        if declared_length is not None:
            headers["Content-Length"] = str(declared_length)
            body = b""
        try:
            conn.request(method, path, body, headers)
            response = conn.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            conn.close()

    try:
        yield gateway, state, request
    finally:
        state.release.set()
        gateway.shutdown()
        gateway.server_close()
        source.shutdown()
        source.server_close()
        gateway_thread.join(5)
        source_thread.join(5)


@pytest.mark.parametrize("body", [b"not json", b"[]", b"null"])
def test_invalid_upstream_json_returns_502_and_releases_slot(live_gateway, body):
    gateway, state, request = live_gateway
    state.body = body
    assert request()[0] == 502
    with gateway.admission:
        assert gateway.admission.wait_for(lambda: gateway.admitted_requests == 0, timeout=3)
    state.body = b"{}"
    assert request()[0] == 200


def test_catalog_incomplete_chunked_response_returns_502(live_gateway):
    _, _, request = live_gateway
    assert request(method="GET", path="/codex/models")[0] == 502


def test_capacity_rejects_before_body_and_does_not_block_health(live_gateway):
    gateway, state, request = live_gateway
    state.hold = True
    first = []
    worker = Thread(target=lambda: first.append(request()))
    worker.start()
    try:
        assert state.entered.wait(3)
        status, _, headers = request(declared_length=1000)
        assert status == 429
        assert headers["Retry-After"] == "1"
        assert request(method="GET", path="/health")[0] == 200
        assert len(state.requests) == 1
    finally:
        state.release.set()
        worker.join(5)
    assert first[0][0] == 200
    with gateway.admission:
        assert gateway.admission.wait_for(lambda: gateway.admitted_requests == 0, timeout=3)


def test_server_close_preserves_inflight_response(live_gateway):
    gateway, state, request = live_gateway
    state.hold = True
    session = gateway.get_session("codex")
    alias = session.mask("PrivateCustomer", code=True)
    state.body = json.dumps({"output_text": alias}).encode()
    first = []
    worker = Thread(target=lambda: first.append(request()))
    worker.start()
    assert state.entered.wait(3)
    gateway.shutdown()
    closed = Event()
    closing = Thread(target=lambda: (gateway.server_close(), closed.set()))
    closing.start()
    try:
        assert not closed.wait(0.1)
        assert session.restore(alias) == "PrivateCustomer"
    finally:
        state.release.set()
        worker.join(5)
        closing.join(5)
    assert first[0][0] == 200
    assert json.loads(first[0][1])["output_text"] == "PrivateCustomer"


def test_shutdown_ack_keeps_health_alive_until_inference_finishes(live_gateway):
    gateway, state, request = live_gateway
    state.hold = True
    state.close_on_stop = True
    replies = []
    worker = Thread(target=lambda: replies.append(request()))
    worker.start()
    try:
        assert state.entered.wait(3)
        assert request(path="/shutdown")[0] == 200
        assert gateway.closing
        assert request(method="GET", path="/health")[0] == 200
        assert request()[0] == 503
        assert len(state.requests) == 1
        assert not state.stopped.is_set()
    finally:
        state.release.set()
        worker.join(5)
    assert replies[0][0] == 200
    assert state.stopped.wait(3)
    with gateway.admission:
        assert gateway.admission.wait_for(lambda: gateway.admitted_requests == 0, timeout=3)
    conn = http.client.HTTPConnection("127.0.0.1", gateway.server_port, timeout=1)
    try:
        with pytest.raises((OSError, http.client.HTTPException)):
            conn.request("GET", "/health", headers={"X-SecureMCP-Token": "fixture-token"})
            conn.getresponse()
    finally:
        conn.close()


def test_claude_control_fields_are_correct_in_provider_request(live_gateway):
    _, state, request = live_gateway
    payload = {"messages": [], "tool_choice": {"type": "tool", "name": "PrivateTool"},
               "context_management": {"edits": [{"type": "clear_tool_uses_20250919", "exclude_tools": ["PrivateTool"]}]},
               "tools": [{"name": "PrivateTool", "input_schema": {"type": "object"}}]}
    assert request(payload, path="/claude/v1/messages")[0] == 200
    masked = state.requests[0]
    assert masked["tool_choice"]["type"] == "tool"
    assert masked["tool_choice"]["name"] == masked["tools"][0]["name"]
    assert masked["context_management"]["edits"][0]["exclude_tools"] == [masked["tools"][0]["name"]]
    assert "PrivateTool" not in json.dumps(masked)


def test_private_safeguard_rejected_before_provider_request(live_gateway):
    gateway, state, request = live_gateway
    assert request({"messages": [], "safeguards": {"type": "PrivateCustomer"}}, path="/claude/v1/messages")[0] == 400
    assert not state.requests
    with gateway.admission:
        assert gateway.admission.wait_for(lambda: gateway.admitted_requests == 0, timeout=3)


@pytest.mark.parametrize("limits", [{"max_active_requests": 0}, {"max_provider_requests": True}, {"max_active_requests": 1.5}])
def test_admission_limits_validated_before_binding(limits):
    with pytest.raises(ValueError):
        PrivacyGateway(("127.0.0.1", 0), "fixture-token", **limits)


def test_global_admission_limit_applies_across_providers():
    gateway = PrivacyGateway(("127.0.0.1", 0), "fixture-token", upstreams={"claude": "fixture", "codex": "fixture"}, max_active_requests=1, max_provider_requests=2)
    try:
        assert gateway.try_admit("claude")
        assert not gateway.try_admit("codex")
        gateway.release_admission("claude")
        assert gateway.try_admit("codex")
        gateway.release_admission("codex")
    finally:
        gateway.server_close()


def test_malformed_request_releases_admission(live_gateway):
    gateway, state, request = live_gateway
    assert request({"input": "hi", "tools": [{"type": "custom", "name": "exec", "format": {"type": "grammar", "syntax": "lark", "definition": []}}]})[0] == 400
    with gateway.admission:
        assert gateway.admission.wait_for(lambda: gateway.admitted_requests == 0, timeout=3)
    assert not state.requests
    assert request()[0] == 200


def test_numeric_scalar_rounded_or_invented_alias_is_refused():
    session = GatewaySession(mask_numbers=True)
    alias = int(session.mask("42", code=True))
    with pytest.raises(ValueError, match="precision"):
        session.values(float(alias), restore=True)
    with pytest.raises(ValueError):
        session.values(732846000000000000, restore=True)


@pytest.mark.parametrize("edit", [{"type": "PrivateType"}, {"type": "clear_tool_uses_20250919", "trigger": {"type": "PrivateType", "value": 3}}, {"type": "clear_tool_uses_20250919", "keep": {"type": "tool_uses", "value": True}}, {"type": "clear_thinking_20251015", "private": "secret"}])
def test_context_edits_reject_unvalidated_controls(edit):
    with pytest.raises(ValueError):
        GatewaySession().request({"messages": [], "context_management": {"edits": [edit]}})


def test_thinking_context_edit_all_is_preserved():
    value = {"edits": [{"type": "clear_thinking_20251015", "keep": "all"}]}
    assert GatewaySession().request({"messages": [], "context_management": value})["context_management"] == value


@pytest.mark.parametrize("kind", ["responses", "chat_completions"])
def test_api_function_tool_choice_retains_definition_alias(kind):
    session = GatewaySession()
    tool = {"type": "function", "name": "PrivateTool", "parameters": {"type": "object"}}
    choice = {"type": "function", "name": "PrivateTool"}
    payload = {"input": "hi", "tools": [tool], "tool_choice": choice}
    if kind == "chat_completions":
        payload = {"messages": [{"role": "user", "content": "hi"}], "tools": [{"type": "function", "function": tool}], "tool_choice": {"type": "function", "function": {"name": "PrivateTool"}}}
    masked = session.request(payload, dialect=kind)
    if kind == "responses":
        assert masked["tool_choice"]["name"] == masked["tools"][0]["name"]
    else:
        assert masked["tool_choice"]["function"]["name"] == masked["tools"][0]["function"]["name"]
def test_negative_numeric_json_alias_keeps_its_unary_sign():
    from secure_mcp.models import TokenType
    session = GatewaySession(mask_numbers=True)
    session.mask("private_value=-42", code=True)
    mapping = next(mapping for mapping in session.session.forward_store.values()
                   if mapping.token_type == TokenType.NUMBER)
    assert session.values({"value": -int(mapping.surrogate)}, restore=True) == {"value": -42}

@pytest.mark.parametrize('name', [None, 2, True, [], {'private': 'SecretCustomer'}])
@pytest.mark.parametrize('nested', [False, True])
def test_invalid_tool_names_return_400_and_release_admission(live_gateway, name, nested):
    gateway, state, request = live_gateway
    tool = {'type': 'function', 'function': {'name': name}} if nested else {'name': name}
    status, body, _ = request({'input': 'SecretCustomer', 'tools': [tool]})
    assert status == 400
    assert b'SecretCustomer' not in body
    assert b'Traceback' not in body
    assert not state.requests
    with gateway.admission:
        assert gateway.admission.wait_for(lambda: gateway.admitted_requests == 0, timeout=3)
    assert request({'input': 'hi', 'tools': [{'type': 'function', 'name': 'privateTool'}]})[0] == 200
    assert len(state.requests) == 1
    assert state.requests[0]['tools'][0]['name'] != 'privateTool'


@pytest.mark.parametrize('text', [None, 2, True, [], {}])
@pytest.mark.parametrize('method', ['mask_text', 'mask_code'])
def test_masking_engine_rejects_non_text_input(text, method):
    from secure_mcp.engine.masking_engine import MaskingEngine
    from secure_mcp.session import PrivacySession

    session = PrivacySession('invalid-text')
    with pytest.raises(ValueError, match='Input must be text'):
        getattr(MaskingEngine(), method)(text, session.session_id, session.generator,
                                       session.forward_store, session.reverse_store)
    assert not session.forward_store
    assert not session.reverse_store

@pytest.mark.parametrize('mask_numbers', [False, True])
def test_gateway_forwards_source_numeric_policy(live_gateway, mask_numbers):
    gateway, state, request = live_gateway
    gateway.mask_numbers = mask_numbers
    payload = {'input': '```python\nprivateLimit = 42\n```'}
    assert request(payload)[0] == 200
    forwarded = state.requests[0]['input']
    assert (' = 42' in forwarded) is (not mask_numbers)
    assert 'privateLimit' not in forwarded
