"""Current native CLI envelopes preserve public controls while masking content."""
import json
import pytest
from secure_gateway.gateway import GatewaySession
from secure_gateway.gateway_validation import validate_request


def test_claude_midconversation_system_effort_is_public_and_content_is_masked():
    session = GatewaySession()
    payload = {"messages": [{"role": "user", "content": "Review privateFunction"},
               {"role": "system", "content": "privateCompany", "output_config": {"effort": "medium"}}]}
    masked = session.request(payload)
    assert masked["messages"][1]["role"] == "system"
    assert masked["messages"][1]["output_config"] == {"effort": "medium"}
    assert "privateCompany" not in json.dumps(masked)


@pytest.mark.parametrize("control", [{"effort": "privateCompany"}, {"privateCompany": "medium"}, []])
def test_inline_output_rejects_private_or_malformed_controls(control):
    with pytest.raises(ValueError):
        GatewaySession().request({"messages": [{"role": "system", "content": "hello", "output_config": control}]})


def test_codex_additional_tools_namespace_and_replay_status():
    session = GatewaySession()
    payload = {"reasoning": {"effort": "low", "context": "all_turns"}, "input": [
        {"type": "additional_tools", "role": "developer", "id": "at_fixture", "tools": [
            {"type": "namespace", "name": "functions", "description": "privateCompany", "tools": [
                {"type": "function", "name": "exec_command", "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}}}}]}]},
        {"type": "custom_tool_call", "id": "ct_fixture", "call_id": "call_fixture", "name": "exec", "input": "privateFunction()", "status": "completed"}]}
    masked = session.request(payload)
    tools = masked["input"][0]
    assert tools["type"] == "additional_tools" and tools["role"] == "developer" and tools["id"] == "at_fixture"
    assert tools["tools"][0]["type"] == "namespace"
    assert tools["tools"][0]["name"] == "functions"
    assert masked["reasoning"]["context"] == "all_turns"
    assert masked["input"][1]["status"] == "completed"
    assert "privateCompany" not in json.dumps(masked) and "privateFunction" not in json.dumps(masked)


@pytest.mark.parametrize("context", ["auto", "current_turn", "all_turns"])
def test_reasoning_context_public_enum(context):
    validate_request({"input": [], "reasoning": {"context": context}}, "codex")


@pytest.mark.parametrize("item", [
    {"type": "additional_tools", "role": "user", "tools": []},
    {"type": "additional_tools", "role": "developer", "tools": ["private"]},
])
def test_invalid_additional_tools_rejected(item):
    with pytest.raises(ValueError):
        GatewaySession().request({"input": [item]})


def test_private_reasoning_context_and_status_fail_closed():
    with pytest.raises(ValueError):
        GatewaySession().request({"input": [], "reasoning": {"context": "privateCompany"}})
    with pytest.raises(ValueError):
        GatewaySession().request({"input": [{"type": "custom_tool_call", "name": "exec", "input": "x", "status": "privateCompany"}]})


def test_codex_tool_result_id_is_preserved_but_result_data_is_masked():
    session = GatewaySession()
    result = session.request({"input": [{"type": "custom_tool_call_output", "id": "cto_fixture", "call_id": "call_fixture", "output": "privateCompany"}]})
    assert result["input"][0]["id"] == "cto_fixture"
    assert "privateCompany" not in json.dumps(result)


@pytest.mark.parametrize("status", [[], {}, 1, None])
def test_malformed_input_item_status_is_validation_error(status):
    with pytest.raises(ValueError, match="status"):
        GatewaySession().request({"input": [{"type": "custom_tool_call", "name": "exec", "input": "privateCompany", "status": status}]})
