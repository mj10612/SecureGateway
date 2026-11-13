"""Default public-number policy for prose (issue #374).

Plain numbers, dates, times, versions and quantities with units are public by
default and are forwarded with their exact spelling. ``mask_numbers=True`` is
the explicit opt-in that restores the legacy numeric aliases.

Clear sensitive numeric patterns stay protected and take precedence over the
public-number policy: card numbers, Korean resident/business registration
numbers, hyphen-grouped account numbers, phone numbers and values introduced by
a sensitive label (account, card, phone, token, PIN, customer/device ID ...).
Each sensitive value is bound as one whole span so that it receives one alias.
Forced rules and existing private mappings are applied by the callers before
this policy and always win.
"""

from __future__ import annotations

from bisect import bisect_right
import re
import sys
import unicodedata

from secure_gateway.engine.grammar_ko import KOREAN_COPULA_LIST, KOREAN_JOSA_LIST

# Unit spellings that may follow a number directly ("5kg", "30s", "3pm", "2nd").
# Any other letter suffix ("7730abc") is an alphanumeric identifier (#326).
_LATIN_UNITS = (
    "st nd rd th am pm AM PM a.m p.m "
    "ns us µs ms s sec secs second seconds m min mins minute minutes h hr hrs hour hours "
    "d day days w wk wks week weeks mo mos month months y yr yrs year years "
    "k K M B bn mn x X "
    "b B kb kB KB Kb mb MB Mb gb GB Gb tb TB Tb pb PB KiB MiB GiB TiB bps kbps Kbps mbps Mbps gbps Gbps "
    "Hz kHz MHz GHz V mV kV A mA W kW MW Wh kWh MWh mAh "
    "mm cm m km in ft yd mi nm um µm "
    "mg g kg t lb lbs oz "
    "ml mL l L cl dl "
    "px pt em rem vh vw dp sp dpi ppi fps rpm ppm ppb mph kph kmh "
    "C F degC degF"
).split()
_LATIN_UNIT = "|".join(re.escape(unit) for unit in sorted(set(_LATIN_UNITS), key=len, reverse=True))

# Korean counters and units after a number ("2026년", "1,250개", "3시간").
# Address components (동/호/번지) are intentionally absent: they keep the
# existing identifier policy.
_KOREAN_UNITS = (
    "년도 년차 년 개월 월 주일 주년 주 일차 일 시간 시 분 초 밀리초 "
    "개국 개사 개 명 인분 인 원 만원 천원 억원 조원 만 천 백 억 조 달러 엔 유로 위안 "
    "번째 번 회차 회 차례 차 층 권 장 대 건 살 세 점 배 위 등 단계 가지 곳 군데 마리 벌 켤레 "
    "통 팩 봉 알 정 캔 판 톤 평 박 줄 행 열 쪽 페이지 글자 자 바이트 퍼센트 프로 도 "
    "킬로그램 킬로미터 킬로 그램 미터 센티미터 센티 밀리미터 밀리 리터 박스 상자 병 잔 학년 기 분기 주차"
).split()
_KOREAN_UNIT = "|".join(sorted(set(_KOREAN_UNITS), key=len, reverse=True))
_KOREAN_TAIL_WORDS = set(KOREAN_JOSA_LIST) | set(KOREAN_COPULA_LIST) | {
    "간", "째", "씩", "쯤", "경", "가량", "여", "께", "들", "부터", "까지", "동안", "전", "후", "내", "이내", "이상", "이하",
    "미만", "초과", "당", "마다", "짜리", "의", "에", "로", "으로",
}
_KOREAN_TAIL = "|".join(sorted(_KOREAN_TAIL_WORDS, key=len, reverse=True))

_NUM = r"\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][+-]?\d+)?"
# One numeric expression: optional currency/version prefix, numbers joined by
# date/time/range/version separators, optional ISO time zone, percent and unit.
_EXPR = (
    rf"[$€£₩¥]?(?:[vV](?=\d+\.\d))?{_NUM}"
    rf"(?:(?:[-./:~–]|T(?=\d))\d+(?:,\d{{3}})*)*"
    r"(?:Z(?![\w])|[+-]\d{2}:\d{2})?%?"
)
PUBLIC_NUMBER = re.compile(
    rf"(?<![\w.,])(?:{_EXPR})"
    rf"(?:(?:{_LATIN_UNIT})(?![\w])|(?:(?:{_KOREAN_UNIT})(?:{_KOREAN_TAIL}){{0,2}}|(?:{_KOREAN_TAIL}){{1,2}})(?![\w])|(?![\w]))"
)

# Sensitive numeric labels: the existing #312 detector field names plus the
# head nouns of the same categories.
_SENSITIVE_LABEL_WORDS = (
    "account", "account id", "account number", "account no", "bank account", "acct",
    "card", "card number", "card no", "credit card", "cvv", "cvc",
    "phone", "phone number", "mobile", "tel", "telephone", "contact", "fax",
    "token", "auth token", "access token", "api key", "secret", "password", "passcode", "pin", "otp", "credential",
    "ssn", "rrn", "national id", "citizen id", "tax id", "tin", "passport", "passport number",
    "customer", "customer id", "customer number", "customer no",
    "device", "device id", "device serial", "serial", "serial number", "serial no", "imei", "imsi", "sim id",
    "employee", "employee id", "emp id",
    "계좌", "계좌번호", "카드", "카드번호", "신용카드번호", "전화", "전화번호", "휴대폰", "휴대폰번호", "연락처",
    "주민번호", "주민등록번호", "외국인등록번호", "여권번호", "사업자번호", "사업자등록번호", "비밀번호", "인증번호",
    "인증토큰", "토큰", "고객번호", "고객식별번호", "고객ID", "계정번호", "계정ID", "장비번호", "장비일련번호",
    "일련번호", "사번", "사원번호", "단말기번호", "식별번호",
)


def _label_pattern() -> re.Pattern[str]:
    labels = []
    for word in sorted(set(_SENSITIVE_LABEL_WORDS), key=len, reverse=True):
        labels.append(r"[ \t_-]?".join(re.escape(part) for part in word.split()))
    return re.compile(
        r"(?<![\w])[\"']?(?:" + "|".join(labels) + r")[\"']?"
        r"(?:(?P<mark>[ \t]*[:=：#][ \t]*|[ \t]+(?:is|was)[ \t]+)|(?:은|는|이|가)?[ \t]+)[\"']?"
        r"(?P<value>[+-]?\d+(?:[.,]\d+)*(?:[eE][+-]?\d+)?(?:[- ]\d{2,})*)(?![\w]|[.,]\d)",
        re.IGNORECASE,
    )


_SENSITIVE_LABEL = _label_pattern()
_SENSITIVE_SHAPES = (
    # Card numbers grouped 4-4-4-4 or 4-6-5 with one consistent separator.
    re.compile(r"(?<![\w.+-])(?:\d{4}([- ])\d{4}\1\d{4}\1\d{4}|\d{4}([- ])\d{6}\2\d{5})(?![\w]|[-.,]\d)"),
    # Korean resident/foreigner registration numbers (YYMMDD-Gnnnnnn).
    re.compile(r"(?<![\w.+-])\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])-[1-8]\d{6}(?![\w]|[-.,]\d)"),
    # Korean business registration numbers.
    re.compile(r"(?<![\w.+-])\d{3}-\d{2}-\d{5}(?![\w]|[-.,]\d)"),
    # Korean mobile numbers without separators and E.164 numbers.
    re.compile(r"(?<![\w.+-])01[016789]\d{7,8}(?![\w]|[.,]\d)"),
    re.compile(r"(?<![\w+])\+\d{9,15}(?![\w]|[.,]\d)"),
)
_CONTIGUOUS = re.compile(r"(?<![\w.+-])\d{13,19}(?![\w]|[.,]\d)")
# Hyphen-grouped bank/account numbers: three or more groups and 10-20 digits.
# Dates (8 digits), times and short ranges stay public.
_ACCOUNT = re.compile(r"(?<![\w.+-])\d+(?:-\d+){2,}(?![\w]|[-.,]\d)")


def sensitive_number_spans(text: str) -> list[tuple[int, int]]:
    """Return sorted, merged spans of clear sensitive numeric values in ``text``."""
    from secure_gateway.numeric_context import is_korean_rrn, is_luhn_valid

    spans: list[tuple[int, int]] = []
    for pattern in _SENSITIVE_SHAPES:
        spans.extend(match.span() for match in pattern.finditer(text))
    for match in _CONTIGUOUS.finditer(text):
        digits = match.group()
        # Checksum-validated card numbers (15-19 digits) and resident
        # registration numbers written without a separator. 13-digit
        # millisecond timestamps are not cards.
        if ((15 <= len(digits) and is_luhn_valid(digits))
                or (len(digits) == 13 and is_korean_rrn(digits)
                    and 1 <= int(digits[2:4]) <= 12 and 1 <= int(digits[4:6]) <= 31)):
            spans.append(match.span())
    for match in _ACCOUNT.finditer(text):
        if 10 <= sum(char.isdigit() for char in match.group()) <= 20:
            spans.append(match.span())
    for match in _SENSITIVE_LABEL.finditer(text):
        # A label followed only by a space needs an identifier-length value:
        # "device 2 of 5" is a count, "device 93000101" is an identifier.
        if match["mark"] or sum(char.isdigit() for char in match["value"]) >= 4:
            spans.append(match.span("value"))
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def public_number_spans(text: str, sensitive: list[tuple[int, int]] | None = None) -> list[tuple[int, int]]:
    """Return spans of public numeric expressions that do not overlap a sensitive value."""
    if sensitive is None:
        sensitive = sensitive_number_spans(text)
    spans = []
    index = 0
    for match in PUBLIC_NUMBER.finditer(text):
        start, end = match.span()
        while index < len(sensitive) and sensitive[index][1] <= start:
            index += 1
        if index < len(sensitive) and sensitive[index][0] < end:
            continue
        spans.append((start, end))
    return spans


def within(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    """Whether ``[start, end)`` lies inside one of the sorted, disjoint ``spans``."""
    index = bisect_right(spans, (start, sys.maxsize)) - 1
    return index >= 0 and spans[index][0] <= start and end <= spans[index][1]


def is_public_number_value(value: str) -> bool:
    """A whole value (e.g. a JSON string) that is exactly one public numeric expression."""
    if not isinstance(value, str) or not value or len(value) > 64:
        return False
    value = unicodedata.normalize("NFC", value)
    stripped = value[1:] if value[:1] in "+-" else value
    match = PUBLIC_NUMBER.fullmatch(stripped)
    return match is not None and not sensitive_number_spans(value)
