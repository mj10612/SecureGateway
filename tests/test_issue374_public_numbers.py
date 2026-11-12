"""#374: numbers and dates are public by default in prose and code.

Synthetic values only. Plain numbers, dates, times, versions and quantities
with units are forwarded byte-for-byte. Forced rules (#363), existing private
mappings and clear sensitive numeric patterns stay protected, each sensitive
value as one whole alias. ``mask_numbers=True`` masks text numbers as well as
code numbers and restores them exactly. Saved numeric aliases keep restoring.
"""
import json
import re

import pytest

from secure_gateway.engine import numbers
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.engine.strategies import StrategyGenerator
from secure_gateway.gateway import GatewaySession
from secure_gateway.gateway_features import GatewayFeatures
from secure_gateway.models import MaskMode, SurrogateStrategy

ALIAS = re.compile(r"⟦?private_symbol_\d+⟧?|(?<![A-Za-z0-9_])(?:732846\d{12})+(?![A-Za-z0-9_])")

PROSE = [
    "Order 4 boxes for 12500 won by 2026-11-20, invoice 7730.",
    "Release v2.17.0 shipped at 14:30 on 2026/11/13; timeout 30s, 5kg, $12.50, -3.5, 0042, 1.5e-3, 99%.",
    "Ship 1,250 units on 2026-11-20T09:30:00Z (UTC+09:00 is 18:30), 3rd attempt at 3pm, 2.5GB, 10-20 items.",
    "회의는 2026년 11월 20일 오후 3시 30분에 시작하고 재고는 1,250개, 할인은 15%입니다.",
    "버전 2.18.0은 3개월 뒤, 12500원으로 5명이 2시간 동안 사용합니다. 0.5초 간격, 7번째 단계까지.",
]


def plain(session_kwargs=None):
    return GatewaySession(natural_language="auto", **(session_kwargs or {}))


def outbound(session, text):
    return session.request({"model": "m", "input": [{"role": "user", "content": text}]})["input"][0]["content"]


def numeric_spellings(text):
    return re.findall(r"\d[\d,.:/T-]*\d|\d", text)


@pytest.mark.parametrize("text", PROSE)
def test_prose_numbers_dates_and_units_are_forwarded_byte_for_byte(text):
    session = plain()
    masked = outbound(session, text)
    stripped = ALIAS.sub(" ", masked)
    for spelling in numeric_spellings(text):
        assert spelling in stripped, spelling
    assert "732846" not in masked
    assert session.restore(masked) == text


def test_ordinary_number_sentence_is_unchanged():
    text = "Order 4 boxes for 12500 won by 2026-11-20, invoice 7730."
    assert outbound(plain(), text) == text


@pytest.mark.parametrize("text", [
    "Use `retry(3)` with `timeout=30`.",
    "```python\nlimit = 25\nprint(limit * 2, 0x1F, 1_000, 2.5e-3)\n```",
    "- step 1: wait 5 minutes\n- step 2: retry 3 times\n\n| id | qty |\n|---|---|\n| a | 12 |",
    '{"count": 12, "due": "2026-11-20", "ratio": 0.25, "version": "1.4.2"}',
])
def test_markdown_code_and_json_text_keep_numbers(text):
    session = plain()
    masked = outbound(session, text)
    stripped = ALIAS.sub(" ", masked)
    for spelling in numeric_spellings(text):
        assert spelling in stripped, spelling
    assert session.restore(masked) == text


def test_tool_arguments_and_results_keep_numbers_and_restore():
    session = plain()
    arguments = {"quantity": 4, "qty_text": "4", "due": "2026-11-20", "at": "2026-11-20T09:30:00Z",
                 "price": "12.50", "version": "2.18.0", "ratio": 0.25, "rows": [1, "2", 3]}
    item = {"type": "function_call", "call_id": "call_a", "name": "order", "arguments": json.dumps(arguments)}
    output = {"type": "function_call_output", "call_id": "call_a",
              "output": "Shipped 12 units, total 12500 won, ETA 2026-11-21 09:00."}
    payload = session.request({"model": "m", "input": [item, output]})
    masked_arguments = json.loads(payload["input"][0]["arguments"])
    assert sorted(masked_arguments.values(), key=str) == sorted(arguments.values(), key=str)
    for spelling in ("12", "12500", "2026-11-21", "09:00"):
        assert spelling in payload["input"][1]["output"]
    restored = session.walk(payload["input"], restore=True)
    assert json.loads(restored[0]["arguments"]) == arguments
    assert restored[1]["output"] == output["output"]


def test_sensitive_tool_argument_fields_keep_whole_literal_aliases():
    session = plain()
    arguments = {"account_number": "91000101", "phone": "0212345678", "card": "4111 1111 1111 1111",
                 "pin": "4321", "count": "3"}
    item = {"type": "function_call", "call_id": "call_b", "name": "pay", "arguments": json.dumps(arguments)}
    masked = json.loads(session.request({"model": "m", "input": [item]})["input"][0]["arguments"])
    values = list(masked.values())
    for value in ("91000101", "0212345678", "4111 1111 1111 1111", "4321"):
        assert value not in values
    assert "3" in values
    restored = json.loads(session.walk([{**item, "arguments": json.dumps(masked)}], restore=True)[0]["arguments"])
    assert restored == arguments


def sse(events):
    return "".join("data: " + json.dumps(event, ensure_ascii=False) + "\n\n" for event in events).encode()


@pytest.mark.parametrize("width", [1, 3, 7])
def test_split_sse_keeps_numbers_and_restores_aliases(width):
    session = plain()
    session.forced_rules = lambda: ("2032-02-28",)
    original = "Due 2032-02-28: pack 1,250 units by 2026-11-20 09:30, v2.18.0, 12.5kg, 3시 30분."
    masked = session.mask(original)
    assert "2032-02-28" not in ALIAS.sub("", masked)
    events = [{"type": "response.output_text.delta", "item_id": "m1", "delta": masked[i:i + width]}
              for i in range(0, len(masked), width)]
    body = session.response(sse(events), "text/event-stream").decode()
    text = "".join(json.loads(line[6:])["delta"] for line in body.splitlines() if line.startswith("data: "))
    assert text == original


def test_forced_numbers_still_bind_as_one_alias_next_to_public_numbers():
    session = plain()
    session.forced_rules = lambda: ("7730", "2032-02-28")
    text = "Invoice 7730 is due 2032-02-28; order 4 boxes by 2026-11-20 and repeat 7730."
    masked = session.mask(text)
    aliases = [alias for alias, mapping in session.session.reverse_store.items() if mapping.original == "7730"]
    assert len(aliases) == 1 and masked.count("⟦" + aliases[0] + "⟧") == 2
    stripped = ALIAS.sub(" ", masked)
    assert "7730" not in stripped and "2032" not in stripped
    assert "4 boxes" in masked and "2026-11-20" in masked
    assert session.restore(masked) == text


SENSITIVE = [
    ("card grouped", "Pay with 4111-1111-1111-1111 today.", "4111-1111-1111-1111"),
    ("card spaced", "Pay with 4111 1111 1111 1111 today.", "4111 1111 1111 1111"),
    ("card contiguous luhn", "Pay with 4111111111111111 today.", "4111111111111111"),
    ("resident number", "주민번호 900101-1234567 확인", "900101-1234567"),
    ("business number", "사업자 123-45-67890 입니다", "123-45-67890"),
    ("account groups", "계좌 110-123-456789 로 입금", "110-123-456789"),
    ("phone", "전화 010-1234-5678 로 연락", "010-1234-5678"),
    ("mobile contiguous", "call 01012345678 now", "01012345678"),
    ("e164", "call +821012345678 now", "+821012345678"),
    ("account label", "Please bill account=91000101 for 3 boxes.", "91000101"),
    ("pin label", "pin: 4321 and 5 items", "4321"),
    ("token label", "token=95000101 expires in 30s", "95000101"),
    ("customer label", "customer 92000101 ordered 4 boxes", "92000101"),
    ("korean label", "계좌번호는 3333012345678 입니다", "3333012345678"),
    ("signed label", "Refund account=-1201201 and device=00120120 today.", "-1201201"),
]


@pytest.mark.parametrize("name,text,value", SENSITIVE, ids=[case[0] for case in SENSITIVE])
def test_sensitive_numeric_patterns_stay_protected_as_one_alias(name, text, value):
    session = plain()
    masked = outbound(session, text)
    stripped = ALIAS.sub(" ", masked)
    assert value not in stripped, name
    # The whole value is one alias (no partial group stays visible).
    for group in re.findall(r"\d{3,}", value):
        assert group not in stripped, (name, group)
    assert session.restore(masked) == text


@pytest.mark.parametrize("text", [
    "The device restarted twice and customer satisfaction rose.",
    "The account was closed; the token expired; the card arrived.",
    "device 2 of 5 restarted; customer 3 waited 10 minutes; token count 4096.",
    "고객 3명이 카드 2장을 받았습니다.",
])
def test_sensitive_label_words_alone_or_with_small_counts_are_unaffected(text):
    # Labels only protect a following number (any after ':'/'=', 4+ digits after a space).
    assert numbers.sensitive_number_spans(text) == []
    masked = outbound(plain(), text)
    stripped = ALIAS.sub(" ", masked)
    for spelling in numeric_spellings(text):
        assert spelling in stripped, spelling


def test_public_numbers_next_to_sensitive_ones_stay_visible():
    session = plain()
    text = "count=3; limit=8; version=1.4; delay=7ms.\naccount=91000101; phone=94000101."
    masked = outbound(session, text)
    # Setting names follow the key=value identifier policy; their values are public.
    for value in ("=3;", "=8;", "=1.4;", "=7ms."):
        assert value in masked
    assert "91000101" not in masked and "94000101" not in masked
    assert session.restore(masked) == text


def test_secrets_and_alphanumeric_identifiers_keep_existing_policy():
    session = plain()
    text = "Use sk-abcdefghijklmnop1234 for part ABC-123 and build 7730abc."
    masked = outbound(session, text)
    for value in ("sk-abcdefghijklmnop1234", "ABC-123", "7730abc"):
        assert value not in masked
    assert session.restore(masked) == text


def test_mask_numbers_opt_in_masks_text_and_code_numbers_and_restores():
    session = plain({"mask_numbers": True})
    text = "Order 4 boxes for 12500 won by 2026-11-20.\n```python\nlimit = 25\n```"
    masked = outbound(session, text)
    stripped = ALIAS.sub(" ", masked)
    for value in ("12500", "2026", "25"):
        assert value not in stripped
    assert session.restore(masked) == text


def test_saved_numeric_aliases_restore_after_switching_to_the_default():
    legacy = plain({"mask_numbers": True})
    text = "Order 4 boxes for 12500 won by 2026-11-20, invoice 7730."
    old_masked = outbound(legacy, text)
    assert "12500" not in old_masked
    upgraded = GatewaySession(legacy.session, natural_language="auto")
    assert upgraded.restore(old_masked) == text
    # New requests in the same saved session forward the public numbers.
    assert outbound(upgraded, text) == text
    assert upgraded.restore(old_masked + " / " + text) == text + " / " + text


def test_literal_number_in_alias_range_is_never_restored_as_an_alias():
    session = plain()
    glued = "732846000000000001732846000000000002"
    text = f"Value {glued} stays literal."
    masked = outbound(session, text)
    assert glued in masked
    assert session.restore(masked) == text


@pytest.mark.parametrize("features", [
    GatewayFeatures(),
    GatewayFeatures(contextual_name_spans=True),
    GatewayFeatures(ko_conjugation_split=True, contextual_name_spans=True),
])
def test_feature_flags_keep_the_number_policy(features):
    session = GatewaySession(natural_language="auto", features=features)
    for text in (PROSE[0], PROSE[3]):
        masked = outbound(session, text)
        stripped = ALIAS.sub(" ", masked)
        for spelling in numeric_spellings(text):
            assert spelling in stripped, spelling
        assert session.restore(masked) == text
    masked = outbound(session, "계좌 110-123-456789 로 4개 보내")
    assert "110-123-456789" not in masked and "4개" in masked


def engine_mask(text, **kwargs):
    engine = MaskingEngine()
    generator = StrategyGenerator(SurrogateStrategy.BRACKET)
    forward, reverse = {}, {}
    result = engine.mask_text(text, "s", generator, forward, reverse, mode=MaskMode.CONTENT_WORDS, **kwargs)
    restored = engine.unmask(result.masked_text, "s", reverse, SurrogateStrategy.BRACKET).unmasked_text
    return result.masked_text, restored


def test_library_mask_text_default_and_opt_in():
    text = "Order 4 boxes for $43,000,000 by 2026-11-20 with card 4111-1111-1111-1111."
    masked, restored = engine_mask(text)
    assert " 4 " in masked and "$43,000,000" in masked and "2026-11-20" in masked
    assert "4111" not in masked and restored == text
    masked, restored = engine_mask(text, mask_numbers=True)
    assert "43,000,000" not in masked and "2026" not in masked and restored == text
    with pytest.raises(ValueError):
        engine_mask(text, mask_numbers="yes")


@pytest.mark.parametrize("value,public", [
    ("12", True), ("-3.5", True), ("2026-11-20", True), ("2026-11-20T09:30:00Z", True), ("14:30", True),
    ("v2.18.0", True), ("1,250", True), ("12.5kg", True), ("3개", True),
    ("7730abc", False), ("110-123-456789", False), ("900101-1234567", False), ("", False), ("1" * 70, False),
])
def test_public_number_value_shapes(value, public):
    assert numbers.is_public_number_value(value) is public


def test_number_policy_spans_scale_linearly():
    text = " ".join(f"{index} units by 2026-11-{index % 28 + 1:02d}" for index in range(20000))
    spans = numbers.public_number_spans(text)
    assert len(spans) == 40000
    assert numbers.within(spans, spans[-1][0], spans[-1][1])
    assert not numbers.within(spans, 0, len(text))
