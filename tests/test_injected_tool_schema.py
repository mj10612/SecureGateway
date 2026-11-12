"""The gateway's own injected tool definition is never masked (#371)."""

from decimal import Decimal
from hashlib import sha256
import json

import pytest

from secure_gateway import gateway
from secure_gateway.gateway_features import GatewayFeatures
from secure_gateway.private_arithmetic import LOCAL_ARITHMETIC_TOOL_NAME, get_arithmetic_tool_spec

TEXT = "Values: 24 and 13. Add the two invoice amounts in USD with the local tool."
USER_TOOLS = [{
    "type": "function",
    "function": {
        "name": "lookup_order",
        "description": "Look up the order for Alice Kim and add a refund or cancel note.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["refund", "cancel", "add"],
                           "description": "What to do with the order of Alice Kim."},
                "order_id": {"type": "string"},
            },
            "required": ["action", "order_id"],
        },
    },
}]
# sha256 of the forwarded user tool definitions / whole requests under 2.16.1.
PIN_USER_TOOLS_ON = "b7a791109f445a791338a237d2dce0b971c3e2f39f28691f7807fd8c784ca36b"
PIN_REQUEST_OFF = "d0d33ca28636187858e83cd86f7d74a64d290e079c1b6c887fea4f9b531c28a4"
PIN_USER_TOOLS_OFF = "b7a791109f445a791338a237d2dce0b971c3e2f39f28691f7807fd8c784ca36b"


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def session(enabled=True, forced=("24", "13")):
    s = gateway.GatewaySession(features=GatewayFeatures(local_arithmetic=True) if enabled else None)
    s.forced_rules = lambda: tuple(forced)
    return s


def injected(result):
    tools = [t for t in result.get("tools", [])
             if LOCAL_ARITHMETIC_TOOL_NAME in (t.get("name"), (t.get("function") or {}).get("name"))]
    assert len(tools) == 1
    return tools[0]


@pytest.mark.parametrize(("payload", "dialect", "spec_dialect"), [
    ({"model": "m", "input": [{"role": "user", "content": TEXT}]}, None, "codex"),
    ({"model": "m", "messages": [{"role": "user", "content": TEXT}]}, None, "claude"),
    ({"model": "m", "messages": [{"role": "user", "content": TEXT}]}, "chat_completions", "chat_completions"),
])
def test_injected_schema_is_forwarded_byte_identical(payload, dialect, spec_dialect):
    result = session().request(payload, dialect=dialect)
    tool = injected(result)
    assert json.dumps(tool, sort_keys=True) == json.dumps(get_arithmetic_tool_spec(spec_dialect), sort_keys=True)
    assert "private_symbol" not in json.dumps(tool)
    # The task operands are still masked.
    text = json.dumps(result, ensure_ascii=False)
    assert " 24 " not in text and " 13 " not in text


def test_operation_from_forwarded_schema_executes_and_restores():
    s = session()
    result = s.request({"model": "m", "messages": [{"role": "user", "content": TEXT}]}, dialect="chat_completions")
    operation = injected(result)["function"]["parameters"]["properties"]["operation"]["enum"][0]
    assert operation == "add"
    aliases = {str(v.original): str(v.surrogate) for v in s.session.reverse_store.values()}
    a, b = aliases["24"], aliases["13"]
    s.tool_dispatcher.tool.allowed.update({a: "USD", b: "USD"})
    upstream = {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{
        "id": "call_1", "type": "function",
        "function": {"name": LOCAL_ARITHMETIC_TOOL_NAME,
                     "arguments": json.dumps({"operation": operation, "aliases": [a, b]})}}]}}]}
    body = s.response(json.dumps(upstream).encode(), "application/json", dialect="chat_completions")
    message = json.loads(body)["choices"][0]["message"]
    assert "tool_calls" not in message
    assert Decimal(message["content"]) == Decimal("37")


def test_user_tool_definitions_unchanged_from_2_16_1():
    payload = {"model": "m", "messages": [{"role": "user", "content": TEXT}], "tools": USER_TOOLS}
    on = session().request(payload, dialect="chat_completions")
    assert digest(on["tools"][:-1]) == PIN_USER_TOOLS_ON
    off = session(enabled=False).request(payload, dialect="chat_completions")
    assert digest(off["tools"]) == PIN_USER_TOOLS_OFF


def test_feature_off_request_unchanged_from_2_16_1():
    off = session(enabled=False).request({"model": "m", "input": [{"role": "user", "content": TEXT}]})
    assert "tools" not in off
    assert digest(off) == PIN_REQUEST_OFF


def test_user_tool_name_collision_still_refused():
    payload = {"model": "m", "messages": [{"role": "user", "content": TEXT}],
               "tools": [{"type": "function", "function": {"name": LOCAL_ARITHMETIC_TOOL_NAME}}]}
    with pytest.raises(ValueError, match="collides"):
        session().request(payload)
