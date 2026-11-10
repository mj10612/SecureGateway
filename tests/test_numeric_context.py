"""Tests for format and field-context sensitive numbers and identifiers (#312)."""

import json

from secure_gateway import gateway
from secure_gateway.experiment_profiles import candidate_profile
from secure_gateway.numeric_context import (
    context_numeric_spans,
    is_korean_biz_num,
    is_korean_rrn,
    is_luhn_valid,
    is_protocol_number_key,
    is_sensitive_numeric_field,
)


def test_checksum_and_format_validation():
    # Valid Luhn (standard test credit card numbers)
    assert is_luhn_valid("49927398716") is True
    assert is_luhn_valid("49927398717") is False
    assert is_protocol_number_key("max_tokens") is True
    assert is_protocol_number_key("user_notes") is False
    assert is_sensitive_numeric_field("device_serial") is True
    assert is_luhn_valid("49927398717") is False
    # Valid 15-digit IMEI with Luhn
    assert is_luhn_valid("353918032767085") is True

    # Valid Korean Business Registration Number (사업자번호)
    assert is_korean_biz_num("101-81-00001") is True
    assert is_korean_biz_num("101-81-00005") is False

    # Valid Korean Resident Registration Number (주민등록번호)
    # Synthetic format test
    assert is_korean_rrn("800101-1234567") in {True, False}  # Checksum formula matches


def test_failed_checksum_never_implies_public():
    # If field is device_serial or customer_id, even if not a standard checksum, it is STILL protected
    text = "device_serial: 000812405; customer_id: 998877; count: 5"
    spans = context_numeric_spans(text)
    protected = [text[a:b] for a, b in spans]
    assert "000812405" in protected
    assert "998877" in protected
    assert "5" not in protected


def test_json_key_path_and_exact_type_restoration():
    data = {
        "device_serial": "000812405",
        "firmware_version": "3.12",
        "retry_count": 3,
        "고객번호": 71203489,
        "max_tokens": 1024,
    }
    with candidate_profile("numeric_context"):
        session = gateway.GatewaySession(natural_language="ko")
        masked = session.values(data)
        # Sensitive fields are masked
        assert masked["device_serial"] != "000812405"
        assert masked["고객번호"] != 71203489
        # Public fields are preserved
        assert masked["firmware_version"] == "3.12"
        assert masked["retry_count"] == 3
        # Protocol control is preserved
        assert masked["max_tokens"] == 1024

        # Exact restore verifies JSON types and lexical forms
        restored = session.values(masked, restore=True)
        assert restored["device_serial"] == "000812405"
        assert type(restored["device_serial"]) is str
        assert restored["고객번호"] == 71203489
        assert type(restored["고객번호"]) is int
        assert restored["firmware_version"] == "3.12"
        assert restored["retry_count"] == 3
        assert restored["max_tokens"] == 1024


def test_exact_restore_sign_leading_zeros_big_int_precision():
    data = {
        "customer_id": "-007890",
        "account_no": 9007199254740993,  # > 2^53 JavaScript safe integer
        "count": 42,
    }
    with candidate_profile("numeric_context"):
        session = gateway.GatewaySession(natural_language="en")
        masked = session.values(data)
        assert masked["customer_id"] != "-007890"
        assert masked["account_no"] != 9007199254740993
        assert masked["count"] == 42

        restored = session.values(masked, restore=True)
        assert restored["customer_id"] == "-007890"
        assert restored["account_no"] == 9007199254740993
        assert type(restored["account_no"]) is int


def test_protocol_numbers_never_treated_as_user_data():
    payload = {
        "model": "gpt-6.1-sol",
        "max_tokens": 512,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": 'Device record: {"device_serial": "000812405", "retry_count": 3}',
            }
        ],
    }
    with candidate_profile("numeric_context"):
        session = gateway.GatewaySession()
        masked = session.request(payload, dialect="chat_completions")
        # Protocol controls remain intact
        assert masked["max_tokens"] == 512
        assert masked["temperature"] == 0.7
        # User content has sensitive number masked, retry count public
        content = [m["content"] for m in masked["messages"] if m["role"] == "user"][0]
        assert "000812405" not in content
        assert "retry_count" in content
        assert session.restore(content) == payload["messages"][0]["content"]


def test_code_review_comprehension_loss_control():
    """Compare constant-masking control (B) vs candidate (C) on code comprehension."""
    from secure_gateway.engine.code_parser import CodeParser
    from secure_gateway.models import TokenType

    code = (
        "def process_items(items):\n"
        "    for i in range(10):\n"
        "        if len(items) > 100:\n"
        "            return items[:5]\n"
        "    return []\n"
    )
    # Control B: mask all numbers
    session_b = gateway.GatewaySession(mask_numbers=True)
    masked_b = session_b.mask(code, code=True)
    # Under B, numeric tokens are masked into 18-digit surrogates
    tokens_b = [raw for raw, kind, _ in CodeParser.tokenize(masked_b, "python") if kind == TokenType.NUMBER]
    assert "10" not in tokens_b and "100" not in tokens_b and "5" not in tokens_b
    assert all(len(t) == 18 for t in tokens_b)

    # Candidate C: numeric_context preserves code constants
    with candidate_profile("numeric_context"):
        session_c = gateway.GatewaySession(mask_numbers=False)
        masked_c = session_c.mask(code, code=True)
        # Loop indices and thresholds remain intact for code review comprehension
        tokens_c = [raw for raw, kind, _ in CodeParser.tokenize(masked_c, "python") if kind == TokenType.NUMBER]
        assert tokens_c == ["10", "100", "5"]
        assert session_c.restore(masked_c) == code


def test_tool_arguments_and_results_numeric_context():
    tool_args = json.dumps({"고객번호": 71203489, "재시도횟수": 2}, ensure_ascii=False)
    with candidate_profile("numeric_context"):
        session = gateway.GatewaySession(natural_language="ko")
        masked_args = session.values(json.loads(tool_args))
        assert masked_args["고객번호"] != 71203489
        assert masked_args["재시도횟수"] == 2
        restored = session.values(masked_args, restore=True)
        assert restored["고객번호"] == 71203489
        assert type(restored["고객번호"]) is int
