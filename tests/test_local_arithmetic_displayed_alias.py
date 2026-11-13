"""The local arithmetic tool accepts aliases exactly as the model sees them (#375)."""

from decimal import Decimal
import json
import re

import pytest

from secure_gateway import gateway
from secure_gateway.gateway_features import GatewayFeatures
from secure_gateway.private_arithmetic import (
    ALIASES_DESCRIPTION,
    LOCAL_ARITHMETIC_TOOL_NAME,
    PrivateArithmetic,
    canonical_alias,
    get_arithmetic_tool_spec,
)

TEXT = "Values: 24 and 13. Add the two invoice amounts in USD with the local tool."
DISPLAYED = re.compile(r"⟦private_symbol_[0-9]+⟧")


def wrap(alias):
    return "⟦" + alias + "⟧"


def forced_session():
    s = gateway.GatewaySession(features=GatewayFeatures(local_arithmetic=True))
    s.forced_rules = lambda: ("24", "13")
    return s


def issued(s):
    return {str(m.original): str(m.surrogate) for m in s.session.reverse_store.values()}


def plain_tool():
    s = gateway.GatewaySession(mask_numbers=True)
    a, b = s.values("24"), s.values("13")
    return s, a, b, PrivateArithmetic(s, allowed={a: "USD", b: "USD"})


@pytest.mark.parametrize("form", ["bare", "displayed", "mixed"])
def test_bare_and_displayed_forms_compute_and_restore(form):
    s, a, b, tool = plain_tool()
    operands = {"bare": [a, b], "displayed": [wrap(a), wrap(b)], "mixed": [wrap(a), b]}[form]
    result = tool.call("subtract", operands)["alias"]
    assert result.startswith("private_symbol_") and "⟦" not in result
    assert Decimal(s.restore(result, strict=True)) == Decimal("11")
    # The derived alias is itself accepted in its displayed form.
    chained = tool.call("add", [wrap(result), wrap(b)])["alias"]
    assert Decimal(s.restore(chained, strict=True)) == Decimal("24")


def test_canonical_alias_only_unwraps_the_exact_displayed_form():
    assert canonical_alias(wrap("private_symbol_7")) == "private_symbol_7"
    assert canonical_alias("private_symbol_7") == "private_symbol_7"
    for value in (wrap("732846000000000001"), wrap("smcp_ID_1"), wrap(" private_symbol_7"), 7, None):
        assert canonical_alias(value) == value


@pytest.mark.parametrize("bad", [
    "⟦{a}",                       # unterminated
    "{a}⟧",                       # unopened
    "⟦⟦{a}⟧⟧",     # doubled brackets
    " ⟦{a}⟧",                # leading text
    "⟦{a}⟧ ",                # trailing whitespace
    "⟦{a}⟧.",                # trailing punctuation
    "alias ⟦{a}⟧",           # extra text
    "⟦ {a} ⟧",               # inner padding
    "[{a}]",                           # other brackets
    "⟪{a}⟫",                 # other unicode brackets
    "⟦{a}⟧⟦{b}⟧",  # two aliases in one operand
    "⟦{A}⟧",                 # case changed
    "⟦{a}0⟧",                # corrupted (unissued) number
    "⟦private_symbol_0{n}⟧", # leading zero
    "⟦private_symbol_１⟧",  # fullwidth digit
    "⟦private_symbol⟧",      # partial alias
    "⟦private_symbol_⟧",     # partial alias
    "{a}⟦⟧",                 # bracket debris
])
def test_malformed_displayed_aliases_rejected(bad):
    s, a, b, tool = plain_tool()
    operand = bad.format(a=a, b=b, A=a.upper(), n=a.rsplit("_", 1)[1])
    with pytest.raises(ValueError, match="Unknown or unauthorized"):
        tool.call("add", [operand, b])
    assert tool.calls == 0


def test_wrapped_numeric_alias_is_not_a_displayed_form():
    s = gateway.GatewaySession(mask_numbers=True)
    masked = s.request({"model": "m", "messages": [{"role": "user", "content": "Order 4471 has 12 items."}]})
    n, m = issued(s)["4471"], issued(s)["12"]
    # Numeric aliases are displayed bare, never bracketed.
    text = json.dumps(masked, ensure_ascii=False)
    assert re.fullmatch(r"732846[0-9]{12}", n) and n in text and wrap(n) not in text
    tool = PrivateArithmetic(s, allowed={n: "count", m: "count"})
    assert s.restore(tool.call("add", [n, m])["alias"]) == "4483"
    with pytest.raises(ValueError, match="Unknown or unauthorized"):
        tool.call("add", [wrap(n), m])


def test_foreign_session_displayed_alias_rejected():
    s1, a, _b, _tool = plain_tool()
    s2 = gateway.GatewaySession(mask_numbers=True)
    s2.values("filler-1")
    s2.values("filler-2")
    foreign = s2.values("99")
    assert foreign not in s1.session.reverse_store
    tool = PrivateArithmetic(s1, allowed={a: "USD", foreign: "USD"})
    with pytest.raises(ValueError, match="absent from this session"):
        tool.call("add", [wrap(a), wrap(foreign)])
    # Policy authorization is still required for the displayed form.
    unauthorized = PrivateArithmetic(s1, allowed={a: "USD"})
    with pytest.raises(ValueError, match="Unknown or unauthorized"):
        unauthorized.call("add", [wrap(a), wrap(foreign)])


@pytest.mark.parametrize("dialect", ["claude", "chat_completions", "codex"])
def test_injected_schema_states_accepted_forms(dialect):
    spec = get_arithmetic_tool_spec(dialect)
    schema = spec.get("input_schema") or spec["function"]["parameters"]
    description = schema["properties"]["aliases"]["description"]
    assert description == ALIASES_DESCRIPTION
    assert "⟦alias⟧" in description and "(alias)" in description
    assert "private_symbol" not in json.dumps(spec)


def chat_tool_call(aliases):
    return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{
        "id": "call_1", "type": "function",
        "function": {"name": LOCAL_ARITHMETIC_TOOL_NAME,
                     "arguments": json.dumps({"operation": "add", "aliases": aliases}, ensure_ascii=False)}}]}}]}


def claude_tool_use(aliases):
    return {"role": "assistant", "content": [{
        "type": "tool_use", "id": "toolu_1", "name": LOCAL_ARITHMETIC_TOOL_NAME,
        "input": {"operation": "add", "aliases": aliases}}]}


@pytest.mark.parametrize("dialect", ["chat_completions", "claude"])
def test_alias_copied_verbatim_from_masked_output_executes_end_to_end(dialect):
    s = forced_session()
    request_dialect = "chat_completions" if dialect == "chat_completions" else None
    forwarded = s.request({"model": "m", "messages": [{"role": "user", "content": TEXT}]}, dialect=request_dialect)
    # The injected schema still reaches the provider exactly as defined (#371).
    tool = [t for t in forwarded["tools"]
            if LOCAL_ARITHMETIC_TOOL_NAME in (t.get("name"), (t.get("function") or {}).get("name"))]
    assert len(tool) == 1
    assert json.dumps(tool[0], sort_keys=True) == json.dumps(get_arithmetic_tool_spec(dialect), sort_keys=True)
    # Copy the operands verbatim from what the model actually sees.
    masked = forwarded["messages"][-1]["content"]
    copied = DISPLAYED.findall(masked)
    assert len(copied) == 2 and "24" not in masked and "13" not in masked
    bare = issued(s)
    assert copied == [wrap(bare["24"]), wrap(bare["13"])]
    s.tool_dispatcher.tool.allowed.update({bare["24"]: "USD", bare["13"]: "USD"})

    upstream = chat_tool_call(copied) if dialect == "chat_completions" else claude_tool_use(copied)
    body = s.response(json.dumps(upstream, ensure_ascii=False).encode(), "application/json", dialect=dialect)
    payload = json.loads(body)
    if dialect == "chat_completions":
        message = payload["choices"][0]["message"]
        assert "tool_calls" not in message
        restored = message["content"]
    else:
        assert all(block.get("type") != "tool_use" for block in payload["content"])
        restored = payload["content"][0]["text"]
    assert Decimal(restored) == Decimal("37")
    record = s.tool_dispatcher.executed_calls[-1]
    assert Decimal(s.restore(record["result"]["alias"], strict=True)) == Decimal("37")


@pytest.mark.parametrize("operand", ["⟦{a}", "⟦{a}⟧ and", "⟦{a}9⟧", "[{a}]"])
def test_malformed_alias_from_model_still_fails_end_to_end(operand):
    s = forced_session()
    s.request({"model": "m", "messages": [{"role": "user", "content": TEXT}]}, dialect="chat_completions")
    bare = issued(s)
    s.tool_dispatcher.tool.allowed.update({bare["24"]: "USD", bare["13"]: "USD"})
    upstream = chat_tool_call([operand.format(a=bare["24"]), wrap(bare["13"])])
    with pytest.raises(ValueError, match="Local arithmetic execution failed"):
        s.response(json.dumps(upstream, ensure_ascii=False).encode(), "application/json", dialect="chat_completions")
    assert s.tool_dispatcher.executed_calls == []
