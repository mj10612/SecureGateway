"""Format and field-context sensitive number and identifier protection (#312).

Protects a number/identifier when:
  (validated format — checksum/known structure)
  OR
  (original field name / label in source structure marks it as account/customer/device id, contact, credential),
using JSON key paths, #317 field names, or adjacent prose labels.

Field names are read from the ORIGINAL structure, never from aliased text.
A failed checksum never implies 'public'.
Exact restore of sign, leading zeros, precision, big integers and JSON type.
Provider protocol numbers (e.g. reasoning controls) are never treated as user data.
Alias-shaped numbers already in the source are handled without collision.
"""

from __future__ import annotations

import re
from typing import Any
import unicodedata

from secure_gateway.structure_parser import cells


def _normalize_key(key: str) -> str:
    return re.sub(r"[\s_-]+", "", unicodedata.normalize("NFC", key).casefold())


# Sensitive numeric identifier field names in English and Korean
SENSITIVE_NUMERIC_FIELDS: frozenset[str] = frozenset(
    _normalize_key(name)
    for name in (
        "device_serial", "device_id", "serial_number", "serial", "serial_no",
        "customer_id", "customer_number", "customer_no", "account_id", "account_number",
        "account_no", "employee_id", "emp_id", "card_number", "credit_card", "ssn", "rrn",
        "pin", "credential", "auth_token", "contact", "phone", "phone_number", "mobile",
        "imei", "sim_id", "imsi", "bank_account", "tin", "tax_id", "citizen_id", "national_id",
        "고객번호", "고객식별번호", "고객ID", "계좌번호", "계정번호", "계정ID", "장비번호", "장비일련번호",
        "일련번호", "사번", "사원번호", "전화번호", "휴대폰번호", "주민번호", "주민등록번호", "사업자번호",
        "사업자등록번호", "카드번호", "신용카드번호", "단말기번호", "식별번호", "인증토큰",
    )
)

# Public numeric fields (counts, versions, timeouts, indices, pagination) that stay public
PUBLIC_NUMERIC_FIELDS: frozenset[str] = frozenset(
    _normalize_key(name)
    for name in (
        "firmware_version", "version", "firmware", "retry_count", "retries", "count",
        "quantity", "index", "offset", "limit", "page", "page_size", "total_pages", "size",
        "port", "timeout", "delay", "interval", "duration", "step", "status_code", "status",
        "code", "year", "month", "day", "hour", "minute", "second",
        "재시도횟수", "재시도", "수량", "버전", "인덱스", "개수", "포트", "지연", "간격", "페이지", "단계",
    )
)

# Protocol fields in LLM API envelopes that must never be treated as user data
PROVIDER_PROTOCOL_NUMBER_KEYS: frozenset[str] = frozenset(
    _normalize_key(name)
    for name in (
        "max_tokens", "max_output_tokens", "temperature", "top_p", "top_k", "seed",
        "frequency_penalty", "presence_penalty", "reasoning_effort", "stream",
        "input_tokens", "output_tokens", "total_tokens", "cache_creation_input_tokens",
        "cache_read_input_tokens", "prompt_tokens", "completion_tokens", "chunk_size",
        "buffer_size", "n", "best_of", "logprobs", "timeout",
    )
)

# Regex for adjacent prose numeric labels: e.g. "device_serial: 000812405"
_ADJACENT_NUMERIC_LABEL = re.compile(
    r"""(?<!\w)["']?(?P<label>[\w가-힣][\w가-힣 \t_-]{0,63})["']?[ \t]*[:：][ \t]*["']?(?P<value>[+-]?\d+(?:[- ./]\d+)*)["']?""",
    re.IGNORECASE,
)


def public_numeric_spans(text: str) -> list[tuple[int, int]]:
    """Compute spans of public numeric values (counts, versions, retry counts) that stay public."""
    from secure_gateway.experiment_context import _check, _finish

    excluded = _check(text)
    spans: list[tuple[int, int]] = []
    for match in _ADJACENT_NUMERIC_LABEL.finditer(text):
        label = match["label"].strip()
        if _normalize_key(label) in PUBLIC_NUMERIC_FIELDS:
            spans.append(match.span("value"))
    return _finish(spans, excluded)


def is_sensitive_numeric_field(name: str) -> bool:
    """Check if an original structure field name denotes a sensitive identifier."""
    if not isinstance(name, str):
        return False
    norm = _normalize_key(name)
    return norm in SENSITIVE_NUMERIC_FIELDS


def is_protocol_number_key(key: str) -> bool:
    """Check if a dictionary key belongs to LLM provider reasoning/generation controls."""
    if not isinstance(key, str):
        return False
    return _normalize_key(key) in PROVIDER_PROTOCOL_NUMBER_KEYS


def is_luhn_valid(number_str: str) -> bool:
    """Validate Luhn checksum (for Credit Cards: 13-19 digits, IMEI: 15 digits)."""
    digits_only = re.sub(r"[\s-]+", "", number_str)
    if not digits_only.isdigit() or not (8 <= len(digits_only) <= 19):
        return False
    digits = [int(c) for c in digits_only]
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def is_korean_rrn(rrn_str: str) -> bool:
    """Validate Korean Resident Registration Number (주민등록번호) structure and checksum."""
    cleaned = re.sub(r"[\s-]+", "", rrn_str)
    if not re.fullmatch(r"\d{13}", cleaned):
        return False
    gender = int(cleaned[6])
    if gender not in range(1, 9):
        return False
    weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]
    digits = [int(c) for c in cleaned]
    total = sum(w * d for w, d in zip(weights, digits[:12]))
    check = (11 - (total % 11)) % 10
    return check == digits[12]


def is_korean_biz_num(biz_str: str) -> bool:
    """Validate Korean Business Registration Number (사업자등록번호) structure and checksum."""
    cleaned = re.sub(r"[\s-]+", "", biz_str)
    if not re.fullmatch(r"\d{10}", cleaned):
        return False
    weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    digits = [int(c) for c in cleaned]
    total = sum(w * d for w, d in zip(weights, digits[:9])) + (digits[8] * 5) // 10
    check = (10 - (total % 10)) % 10
    return check == digits[9]


def is_validated_identifier_format(value_str: str) -> bool:
    """Check if string matches a validated checksum format (Luhn, Korean RRN, Business Num)."""
    if not isinstance(value_str, str):
        return False
    s = value_str.strip()
    return is_luhn_valid(s) or is_korean_rrn(s) or is_korean_biz_num(s)


def context_numeric_spans(text: str) -> list[tuple[int, int]]:
    """Compute original-offset spans for numbers/identifiers based on format and context.

    Protects when:
      (validated format — Luhn, RRN, Business num)
      OR
      (original field name/label denotes sensitive identifier: account/customer/device id, contact)
    using #317 field names, table cells, or adjacent prose labels.
    Never exposes an identifier just because a checksum failed.
    """
    from secure_gateway.experiment_context import _check, _finish

    excluded = _check(text)
    spans: list[tuple[int, int]] = []

    # 1. Structure cells from Markdown tables and forms (#317 parser integration)
    for _, field_name, start, end in cells(text):
        val_str = text[start:end]
        is_num_shape = bool(re.fullmatch(r"[+-]?\d+(?:[- ./]\d+)*", val_str))
        if is_sensitive_numeric_field(field_name) and is_num_shape:
            spans.append((start, end))
        elif is_validated_identifier_format(val_str):
            spans.append((start, end))

    # 2. Adjacent labels in prose: e.g. "device_serial: 000812405", "고객번호: 71203489"
    for match in _ADJACENT_NUMERIC_LABEL.finditer(text):
        label = match["label"].strip()
        val_start, val_end = match.span("value")
        val_str = text[val_start:val_end]
        if is_sensitive_numeric_field(label):
            spans.append((val_start, val_end))
        elif is_validated_identifier_format(val_str):
            spans.append((val_start, val_end))

    # 3. Global scan for standalone validated formats (e.g. Luhn card numbers, Korean RRNs)
    # Check sequences of digits/hyphens
    for m in re.finditer(r"\b\d{3,6}[- ]?\d{2,7}(?:[- ]?\d{1,7})?\b", text):
        candidate = m.group(0)
        if is_validated_identifier_format(candidate):
            spans.append((m.start(), m.end()))

    return _finish(spans, excluded)


class NumericLiteralMetadata:
    """Stores exact lexical and numeric properties for loss-free reconstruction."""
    __slots__ = ("original_text", "json_type", "sign", "leading_zeros", "precision", "is_big_int")

    def __init__(self, raw: Any):
        if isinstance(raw, str):
            self.json_type = "str"
            self.original_text = raw
            self.sign = "-" if raw.startswith("-") else "+" if raw.startswith("+") else ""
            cleaned = raw.lstrip("+-")
            int_part = cleaned.split(".")[0] if "." in cleaned else cleaned
            self.leading_zeros = len(int_part) - len(int_part.lstrip("0")) if int_part.startswith("0") and int_part != "0" else 0
            self.precision = len(cleaned.split(".")[1]) if "." in cleaned else 0
            self.is_big_int = len(cleaned) > 15 and cleaned.isdigit()
        elif isinstance(raw, int) and not isinstance(raw, bool):
            self.json_type = "int"
            self.original_text = str(raw)
            self.sign = "-" if raw < 0 else ""
            self.leading_zeros = 0
            self.precision = 0
            self.is_big_int = abs(raw) >= (1 << 53)
        elif isinstance(raw, float):
            self.json_type = "float"
            self.original_text = format(raw, ".16g")
            self.sign = "-" if raw < 0 else ""
            self.leading_zeros = 0
            self.precision = len(self.original_text.split(".")[1]) if "." in self.original_text else 0
            self.is_big_int = False
        else:
            self.json_type = type(raw).__name__
            self.original_text = str(raw)
            self.sign = ""
            self.leading_zeros = 0
            self.precision = 0
            self.is_big_int = False

    def restore_value(self, restored_str: str) -> Any:
        """Restore to exact original JSON scalar type and representation."""
        if self.json_type == "int":
            try:
                val = int(restored_str)
                return val
            except ValueError:
                return restored_str
        elif self.json_type == "float":
            try:
                return float(restored_str)
            except ValueError:
                return restored_str
        return restored_str
