"""#363: forced numeric/date values bind as one alias; protocol settings stay usable.

Synthetic values only. Each forced value must become exactly one alias whose
original is the complete spelling, repeated occurrences must reuse it, and a
protocol setting that happens to equal a forced value must not block the request.
"""
import http.client
import json
import re
from threading import Thread

import pytest

from secure_gateway.gateway import GatewaySession, PrivacyGateway
from secure_gateway.gateway_errors import GatewayRequestError, public_request_error

ALIAS = re.compile(r"private_symbol_\d+|(?<![A-Za-z0-9_])732846\d{12}(?![A-Za-z0-9_])")

# Shapes from the #319 preparation findings: ISO date, decimal/integer (signed,
# trailing and leading zeros) and other character mixes.
SHAPES = ["2032-02-28", "-3.25", "7.20", "4", "007", "03/04/2033", "2037-11-01 01:15", "99.00"]


def session_with(*rules):
    session = GatewaySession(natural_language="auto")
    session.forced_rules = lambda: tuple(rules)
    return session


def bound(session, value):
    """Aliases whose original is exactly ``value``."""
    return [alias for alias, mapping in session.session.reverse_store.items() if mapping.original == value]


def visible(masked, value):
    """Whether ``value`` remains readable outside aliases (whole number span)."""
    stripped = ALIAS.sub("\0", masked)
    return re.search(r"(?<!\d)" + re.escape(value) + r"(?!\d)", stripped) is not None


@pytest.mark.parametrize("value", SHAPES)
def test_prose_forced_value_is_one_alias_and_restores_spelling(value):
    session = session_with(value)
    text = f"Data: {value}; other 12.40 and 1,234. Repeat {value}."
    masked = session.mask(text)
    aliases = bound(session, value)
    assert len(aliases) == 1
    assert masked.count("⟦" + aliases[0] + "⟧") == 2
    assert not visible(masked, value)
    assert session.restore(masked) == text


def test_all_shapes_together_in_one_prompt():
    session = session_with(*SHAPES)
    text = "Data: " + "; ".join(SHAPES) + ".\nCompare " + SHAPES[0] + " with " + SHAPES[5] + "."
    masked = session.mask(text)
    for value in SHAPES:
        assert len(bound(session, value)) == 1, value
        assert not visible(masked, value), value
    assert session.restore(masked) == text


def test_short_numeric_rule_neither_splits_numbers_nor_rewrites_aliases():
    # Before #363, "4" matched digits inside numeric aliases and inside 12.40.
    session = session_with("4", "2")
    text = "Data: 12.40; 4. Rows 2 and 6.25 (total 1,234)."
    masked = session.mask(text)
    assert len(bound(session, "4")) == 1 and len(bound(session, "2")) == 1
    # #374: ordinary numbers are public and stay whole (never split by the rule).
    for other in ("12.40", "6.25", "1,234"):
        assert visible(masked, other)
    assert session.restore(masked) == text


def test_forced_value_in_inline_code_and_source_binds_whole():
    session = session_with("2032-02-28", "-3.25")
    text = "Run `due = '2032-02-28'` and then 2032-02-28 again."
    masked = session.mask(text)
    assert not visible(masked, "2032-02-28")
    assert session.restore(masked) == text
    source = 'when = "2032-02-28"\nprice = -3.25\n'
    masked_source = session.mask(source, code=True)
    assert not visible(masked_source, "2032-02-28") and "3.25" not in ALIAS.sub("", masked_source)
    assert session.restore(masked_source) == source


def test_json_text_values_bind_whole():
    session = session_with("2032-02-28", "-3.25")
    text = '{"due": "2032-02-28", "amount": -3.25}'
    masked = session.mask(text)
    assert not visible(masked, "2032-02-28") and not visible(masked, "3.25")
    assert session.restore(masked) == text


def test_tool_arguments_and_outputs_bind_and_restore():
    session = session_with("2032-02-28", "-3.25", "7.20")
    item = {"type": "function_call", "call_id": "call_a", "name": "exec_command",
            "arguments": json.dumps({"cmd": "echo 2032-02-28", "due": "2032-02-28", "net": -3.25, "price": 7.2})}
    output = {"type": "function_call_output", "call_id": "call_a", "output": "due 2032-02-28 net -3.25"}
    payload = session.request({"model": "m", "input": [item, output]})
    masked_args = payload["input"][0]["arguments"]
    for value in ("2032-02-28", "3.25", "7.2"):
        assert value not in ALIAS.sub("", masked_args)
        assert value not in ALIAS.sub("", payload["input"][1]["output"])
    arguments = json.loads(masked_args)
    # JSON numbers stay JSON numbers (numeric aliases) and restore exactly.
    numbers = [value for value in arguments.values() if isinstance(value, int)]
    assert len(numbers) == 2 and all(732846 * 10**12 <= abs(n) < 732847 * 10**12 for n in numbers)
    restored = session.walk(payload["input"], restore=True)
    assert json.loads(restored[0]["arguments"]) == json.loads(item["arguments"])
    assert restored[1]["output"] == output["output"]


def test_json_data_positions_mask_matching_numbers():
    session = session_with("4", "2032-02-28")
    value = session.walk_data({"rows": [4, 5, "2032-02-28"], "flag": True})
    rows = next(iter(value.values()))
    assert rows[1] == 5 and rows[0] != 4 and "2032-02-28" not in json.dumps(value)
    assert session.walk_data(value, restore=True) == {"rows": [4, 5, "2032-02-28"], "flag": True}


def sse(events):
    return "".join("data: " + json.dumps(event, ensure_ascii=False) + "\n\n" for event in events).encode()


def test_split_sse_restores_whole_forced_values():
    session = session_with("2032-02-28", "-3.25")
    masked = session.mask("Due 2032-02-28, net -3.25.")
    events = [{"type": "response.output_text.delta", "item_id": "m1", "delta": masked[i:i + 3]}
              for i in range(0, len(masked), 3)]
    body = session.response(sse(events), "text/event-stream").decode()
    text = "".join(json.loads(line[6:])["delta"] for line in body.splitlines() if line.startswith("data: "))
    assert text == "Due 2032-02-28, net -3.25."


@pytest.mark.parametrize("rule", ["3", "0.5", "fixture-model", "high"])
def test_protocol_settings_equal_to_forced_value_are_forwarded_untouched(rule):
    session = session_with(rule)
    payload = {"model": "fixture-model", "max_output_tokens": 3, "temperature": 0.5,
               "reasoning": {"effort": "high"}, "prompt_cache_key": "k3",
               "input": [{"role": "user", "content": f"Use {rule} in the plan; total 3, ratio 0.5."}]}
    result = session.request(payload)
    for key in ("model", "max_output_tokens", "temperature", "reasoning"):
        assert result[key] == payload[key]
    assert not visible(result["input"][0]["content"], rule)
    assert session.restore(result["input"][0]["content"]) == payload["input"][0]["content"]


def test_claude_dialect_protocol_collision_is_not_refused():
    session = session_with("1024", "4")
    result = session.request({"model": "fixture-4", "max_tokens": 1024,
                              "messages": [{"role": "user", "content": "Budget 1024, team 4."}]})
    assert result["max_tokens"] == 1024 and result["model"] == "fixture-4"
    content = result["messages"][0]["content"]
    assert not visible(content, "1024") and not visible(content, "4")


def test_identifier_collision_fails_closed_with_fixed_error_and_reason():
    session = session_with("123")
    with pytest.raises(GatewayRequestError) as caught:
        session.request({"model": "m", "input": [
            {"type": "function_call", "call_id": "call-123", "name": "exec_command", "arguments": "{}"}]})
    assert caught.value.code == "forced_rule_protocol_conflict"
    assert caught.value.diagnostic == "forced_rule_protocol_identifier"
    error = public_request_error(caught.value)
    assert error["code"] == "forced_rule_protocol_conflict" and "123" not in json.dumps(error)
    # Random identifiers containing the digits inside a longer token are not the value.
    session.request({"model": "m", "input": [
        {"type": "function_call", "call_id": "call_Ab123Cd", "name": "exec_command", "arguments": "{}"}]})


def test_identifier_refusal_is_counted_without_content(tmp_path, caplog):
    token = "synthetic-local-token"
    gateway = PrivacyGateway(("127.0.0.1", 0), token, state_dir=tmp_path,
                             upstreams={"codex": "http://127.0.0.1:9"})
    gateway.mask_rules = ("98765",)
    thread = Thread(target=gateway.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
    thread.start()
    try:
        body = json.dumps({"model": "m", "input": [
            {"type": "function_call", "call_id": "call-98765", "name": "exec_command", "arguments": "{}"}]})
        connection = http.client.HTTPConnection("127.0.0.1", gateway.server_port, timeout=10)
        try:
            connection.request("POST", "/codex/responses", body, {
                "X-SecureGateway-Token": token, "Authorization": "Bearer eyJ-fixture",
                "Content-Type": "application/json", "X-SecureGateway-Session": "issue363"})
            response = connection.getresponse()
            status, reply = response.status, response.read()
        finally:
            connection.close()
    finally:
        gateway.shutdown()
        gateway.server_close()
        thread.join(5)
    assert status == 400
    assert json.loads(reply)["code"] == "forced_rule_protocol_conflict"
    assert b"98765" not in reply
    counts = gateway.session_diagnostics()["diagnostic_counts"]
    assert counts["forced_rule_protocol_identifier"] == 1
    assert counts["forced_rule_unmasked_content"] == 0
    assert "98765" not in caplog.text
