"""Known echoes must not split opaque spans or escape failure handling."""
import json

from click.testing import CliRunner
import pytest

from secure_gateway.cli import main
from secure_gateway.hooks import handle_hook


def post(state, text, agent):
    result = handle_hook({"hook_event_name": "PostToolUse", "session_id": "review", "tool_response": text}, state, agent)
    return result["stopReason"] if agent == "codex" else result["hookSpecificOutput"]["updatedToolOutput"]


@pytest.mark.parametrize("agent", ["claude", "codex"])
@pytest.mark.parametrize("template", ["`private {} hidden`", "```text\nprivate {} hidden\n```", "https://private.example/{}/hidden"])
def test_known_echo_preserves_whole_opaque_span_and_local_restore(tmp_path, agent, template):
    (tmp_path / "key").write_text("synthetic-password", encoding="ascii")
    alias = post(tmp_path, "Alice", agent)
    assert post(tmp_path, alias, agent) == alias
    source = template.format(alias)
    masked = post(tmp_path, source, agent)
    assert "private" not in masked and "hidden" not in masked
    event = {"hook_event_name": "PreToolUse", "session_id": "review", "tool_name": "Bash", "tool_input": {"command": masked}}
    restored = handle_hook(event, tmp_path, agent)
    assert restored["hookSpecificOutput"]["updatedInput"]["command"] == template.format("Alice")


@pytest.mark.parametrize("agent", ["claude", "codex"])
def test_known_and_unknown_echo_mix(tmp_path, agent):
    (tmp_path / "key").write_text("synthetic-password", encoding="ascii")
    alias = post(tmp_path, "Alice", agent)
    source = alias + " \u27e6ENT_999\u27e7"
    masked = post(tmp_path, source, agent)
    event = {"hook_event_name":"PreToolUse", "session_id":"review", "tool_name":"Bash", "tool_input":{"command":masked}}
    restored = handle_hook(event, tmp_path, agent)
    assert restored["hookSpecificOutput"]["updatedInput"]["command"] == "Alice \u27e6ENT_999\u27e7"


@pytest.mark.parametrize("event", ["PostToolUse", "PreToolUse"])
def test_deep_parsed_hook_returns_sanitized_failure(tmp_path, event):
    (tmp_path / "key").write_text("synthetic-password", encoding="ascii")
    value = "synthetic-private"
    for _ in range(200):
        value = [value]
    payload = {"hook_event_name":event,"session_id":"review","tool_name":"Bash"}
    payload["tool_response" if event == "PostToolUse" else "tool_input"] = value if event == "PostToolUse" else {"command":value}
    result = CliRunner().invoke(main, ["hook","--agent","codex","--state-dir",str(tmp_path)], input=json.dumps(payload))
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    if event == "PostToolUse":
        assert data["continue"] is False
        assert "original output withheld" in data["stopReason"]
    else:
        assert data["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "synthetic-private" not in result.output


def test_depth_guard_is_bounded_and_precedes_session_writes(tmp_path):
    from secure_gateway.hooks import MAX_HOOK_NESTING
    state = tmp_path / "uncreated"
    value = "private"
    for _ in range(MAX_HOOK_NESTING + 1):
        value = [value]
    with pytest.raises(ValueError, match="nesting limit"):
        handle_hook({"hook_event_name":"PostToolUse", "session_id":"review", "tool_response":value}, state)
    assert not state.exists()


def test_depth_guard_accepts_boundary_and_mixed_containers(tmp_path):
    from secure_gateway.hooks import MAX_HOOK_NESTING
    (tmp_path / "key").write_text("synthetic-password", encoding="ascii")
    value = "Alice"
    for depth in range(MAX_HOOK_NESTING):
        value = {"stdout":value} if depth % 2 else [value]
    result = post(tmp_path, value, "claude")
    assert "Alice" not in json.dumps(result)


def test_json_parser_recursion_has_fixed_cli_failure(tmp_path):
    raw = '{"hook_event_name":"PostToolUse","session_id":"review","tool_response":' + '[' * 2000 + '"synthetic-private"' + ']' * 2000 + '}'
    result = CliRunner().invoke(main, ["hook","--agent","codex","--state-dir",str(tmp_path)], input=raw)
    assert result.exit_code == 1
    assert "synthetic-private" not in result.output
    assert "Traceback" not in result.output
    assert "SecureGateway hook failed" in result.output


def test_registered_echo_whose_original_contains_alias_is_expanded_once(tmp_path):
    (tmp_path / "key").write_text("synthetic-password", encoding="ascii")
    literal = "\u27e6ENT_999\u27e7"
    alias = post(tmp_path, literal, "claude")
    echoed = post(tmp_path, alias, "claude")
    event = {"hook_event_name":"PreToolUse", "session_id":"review", "tool_name":"Bash", "tool_input":{"command":echoed}}
    assert handle_hook(event, tmp_path)["hookSpecificOutput"]["updatedInput"]["command"] == literal


def test_hook_backups_remain_unique_when_clock_does_not_advance(tmp_path, monkeypatch):
    from secure_gateway.hooks import configure
    settings = tmp_path / "settings.json"
    original = b'{"theme":"dark"}\n'
    settings.write_bytes(original)
    state = tmp_path / "state"
    monkeypatch.setattr("time.time_ns", lambda: 123)
    first = configure(settings, state, True)
    installed = settings.read_bytes()
    second = configure(settings, state, True)
    assert first != second and first.read_bytes() == original
    assert second.read_bytes() == installed
