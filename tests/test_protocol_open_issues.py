"""Regression coverage for remaining protocol and schema issue contracts."""

import json

import pytest

from secure_gateway.gateway import GatewaySession


@pytest.mark.parametrize("phase", ["commentary", "final_answer"])
def test_responses_assistant_phase_survives_replay(phase):
    session = GatewaySession()
    payload = {"input": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "done"}], "phase": phase}]}
    assert session.request(payload)["input"][0]["phase"] == phase
    assert session.walk_data({"phase": phase}) != {"phase": phase}


@pytest.mark.parametrize("phase", ["private", [], None, 42])
def test_invalid_assistant_phase_is_rejected(phase):
    with pytest.raises(ValueError, match="phase"):
        GatewaySession().request({"input": [{"role": "assistant", "content": "done", "phase": phase}]})


def test_chat_parallel_tool_call_ids_match_results_across_turns():
    session = GatewaySession()
    calls = [{"id": f"call_{i}", "type": "function", "function": {"name": "lookup", "arguments": "{}"}} for i in range(2)]
    messages = [{"role": "assistant", "content": None, "tool_calls": calls}]
    messages.extend({"role": "tool", "tool_call_id": call["id"], "content": "result"} for call in calls)
    masked = session.request({"messages": messages}, dialect="chat_completions")
    assistant = next(item for item in masked["messages"] if item["role"] == "assistant")
    tools = [item for item in masked["messages"] if item["role"] == "tool"]
    assert [call["id"] for call in assistant["tool_calls"]] == [tool["tool_call_id"] for tool in tools]
    assert session.walk_data({"id": "call_0"}) != {"id": "call_0"}


@pytest.mark.parametrize("keyword", ["$ref", "$dynamicRef"])
def test_local_schema_reference_keywords_resolve_after_masking(keyword):
    session = GatewaySession()
    schema = {"$defs": {"Secret": {"type": "string"}}, keyword: "#/$defs/Secret"}
    masked = session.walk(schema)
    assert masked[keyword] == "#/$defs/" + next(iter(masked["$defs"]))
    assert session.walk(masked, restore=True) == schema


@pytest.mark.parametrize("reference", ["#named", "https://example.com/schema", "#/$defs/missing"])
def test_dynamic_schema_refs_reject_unsupported_or_unresolved_forms(reference):
    with pytest.raises(ValueError, match="reference|anchor"):
        GatewaySession().walk({"$dynamicRef": reference})


@pytest.mark.parametrize("name", ["try", "finally", "True", "Secret", "command"])
def test_property_names_constraints_use_same_aliases_as_required_names(name):
    session = GatewaySession()
    schema = {"type": "object", "properties": {name: {"type": "string"}}, "required": [name], "additionalProperties": False, "propertyNames": {"enum": [name], "const": name}}
    masked = session.walk(schema)
    alias = next(iter(masked["properties"]))
    assert masked["required"] == masked["propertyNames"]["enum"] == [alias]
    assert masked["propertyNames"]["const"] == alias
    assert session.walk(masked, restore=True) == schema


@pytest.mark.parametrize("value", ["try", "finally", "True", "Secret"])
def test_tool_data_values_match_schema_enum_and_roundtrip(value):
    session = GatewaySession()
    payload = {"messages": [{"role": "assistant", "content": [{"type": "tool_use", "id": "call", "name": "lookup", "input": {"mode": value}}]}], "tools": [{"name": "lookup", "input_schema": {"type": "object", "properties": {"mode": {"enum": [value]}}}}]}
    masked = session.request(payload)
    schema = masked["tools"][0]["input_schema"]["properties"]
    block = next(item for item in masked["messages"] if item["role"] == "assistant")["content"][0]
    key, candidate = next(iter(block["input"].items()))
    assert candidate in schema[key]["enum"]
    assert session.walk(block, restore=True)["input"] == {"mode": value}


def test_actual_command_source_remains_code_masked():
    session = GatewaySession()
    block = {"type": "tool_use", "id": "call", "name": "exec_command", "input": {"command": "def Secret():\n    return 42"}}
    masked = session.walk(block)
    assert "def " in masked["input"]["command"]
    assert "Secret" not in masked["input"]["command"]
    assert session.walk(masked, restore=True) == block


def test_complete_reasoning_summary_restores_and_replays_with_opaque_provenance():
    session = GatewaySession()
    alias = session.mask("SecretName", code=True)
    block = {"type": "reasoning", "id": "rs_1", "summary": [{"type": "summary_text", "text": alias}], "encrypted_content": "ciphertext"}
    output = json.loads(session.response(json.dumps({"output": [block]}).encode(), "application/json"))["output"][0]
    assert output["summary"][0]["text"] == "SecretName"
    assert output["encrypted_content"] == "ciphertext"
    assert session.walk(output) == block
    altered = {**output, "summary": [{"type": "summary_text", "text": "Injected"}]}
    with pytest.raises(ValueError, match="Unrecognized"):
        session.walk(altered)
    frames = [
        {"type": "response.reasoning_summary_text.delta", "item_id": "rs_1", "summary_index": 0, "delta": alias},
        {"type": "response.completed", "response": {"output": [block]}},
    ]
    stream = "".join("data: " + json.dumps(frame) + "\n\n" for frame in frames).encode()
    events = [json.loads(frame[6:]) for frame in session.response(stream, "text/event-stream").decode().strip().split("\n\n")]
    assert events[0]["delta"] == events[1]["response"]["output"][0]["summary"][0]["text"] == "SecretName"


def test_restored_reasoning_summary_replay_provenance_survives_restart(tmp_path):
    from secure_gateway.gateway import PrivacyGateway

    state = tmp_path / "state"
    first = PrivacyGateway(("127.0.0.1", 0), "fixture-token", state_dir=state)
    try:
        session = first.get_session("codex")
        alias = session.mask("SecretName", code=True)
        provider = {"type": "reasoning", "summary": [{"type": "summary_text", "text": alias}], "encrypted_content": "ciphertext"}
        restored = session.walk(provider, restore=True)
        first.save("codex", session)
    finally:
        first.server_close()
    restarted = PrivacyGateway(("127.0.0.1", 0), "fixture-token", state_dir=state)
    try:
        loaded = restarted.get_session("codex")
        assert loaded.walk(restored) == provider
        with pytest.raises(ValueError, match="Unrecognized"):
            loaded.walk({**restored, "encrypted_content": "changed"})
    finally:
        restarted.server_close()
