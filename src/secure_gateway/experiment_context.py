"""Isolated add-protection proposals for explicit prose/document structures.

No function relaxes baseline masking, rewrites text, changes JSON types or
registers gateway policy. Callers union these original-coordinate spans with
existing forced/private/domain/code protection. These conservative lexical
rules cannot classify all confidential names or infer natural-language scope.
"""

from __future__ import annotations

from hashlib import sha256
import re
import unicodedata

from secure_gateway.engine.tokenizer import MultilingualTokenizer
from secure_gateway.gateway_source import looks_like_source, markdown_code_spans


MAX_INPUT_BYTES = 1024 * 1024
MAX_SPANS = 100_000
MAX_VALUE_CHARS = 256
_QUOTES = {'"': '"', "'": "'", "‘": "’", "“": "”", "「": "」", "『": "』"}
_OPAQUE = frozenset({"EMAIL", "URL", "SECRET", "UUID", "IP", "PHONE", "CODE_BLOCK"})
_FIELD = re.compile(r"(?:\A|(?<=[\n;{,]))[ \t]*[\"']?(?P<label>[\w가-힣][\w가-힣 \t-]{0,63})[\"']?[ \t]*[:：][ \t]*")
_INTRO = re.compile(
    r"(?<!\w)(?:(?:project|company|customer|product|person)(?:[ \t]+name)?[ \t]*[:：]"
    r"|(?:project|company|customer|product|person)[ \t]+named[ \t]+"
    r"|(?:프로젝트명|회사명|고객명|제품명|고객사[ \t]*이름|프로젝트[ \t]*이름|이름)[ \t]*(?:[:：]|은|는))",
    re.IGNORECASE,
)
_RELEASE = re.compile(r"(?<!\w)(?:release|launch)[ \t]+of[ \t]+", re.IGNORECASE)
_KO_SUFFIX = re.compile(r"(?<!\w)([가-힣\u1100-\u11ffA-Za-z][\w\u1100-\u11ff-]{0,63}?)(?:의[ \t]*(?:출시|배포)|[ \t]*프로젝트(?=[은는이가을를와과의\s.,!?]|$))")
_NAME_TOKEN = re.compile(r"[\w\u1100-\u11ff]+(?:[-'][\w\u1100-\u11ff]+)*")
_NON_NAMES = frozenset({"information", "the", "a", "an", "it", "this", "that", "비공개", "공개", "이", "그", "새"})


def _label(value: str) -> str:
    """Return a stable comparison key for a field label.

    Normalizes NFC/casefold and removes spaces, underscores, and hyphens.
    Never returns ``None``.
    """
    return re.sub(r"[\s_-]+", "", unicodedata.normalize("NFC", value).casefold())


_NAME_FIELDS = frozenset(map(_label, (
    "project", "project name", "company", "company name", "customer", "customer name", "product", "product name",
    "person", "person name", "프로젝트", "프로젝트명", "회사", "회사명", "고객", "고객명", "고객사", "고객사 이름", "제품명", "이름",
)))
_NUMERIC_FIELDS = frozenset(map(_label, (
    "device_serial", "serial number", "customer_id", "customer number", "account_id", "account number", "employee_id",
    "고객번호", "고객식별번호", "계좌번호", "계정번호", "장비번호", "장비일련번호", "일련번호", "사번",
)))


def _check(text: str) -> list[tuple[int, int]]:
    """Validate input and compute excluded original-coordinate spans.

    Excludes markdown code spans and opaque tokenizer kinds (email/URL/secret,
    etc.). Returns the whole text as one excluded span when source-like content
    cannot be safely analyzed, or when markdown parsing fails. Never returns
    ``None``.

    Raises:
        ValueError: For non-text input or input exceeding :data:`MAX_INPUT_BYTES`.
    """
    if not isinstance(text, str):
        raise ValueError("Context candidate input must be text")
    if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("Context candidate input budget exceeded")
    try:
        excluded = markdown_code_spans(text)
    except ValueError:
        return [(0, len(text))]
    leading_field = _FIELD.match(text)
    explicit_form = leading_field is not None and _label(leading_field["label"]) in _NAME_FIELDS | _NUMERIC_FIELDS
    if not explicit_form and looks_like_source(text[:4096]):
        return [(0, len(text))]
    offset = 0
    for chunk in MultilingualTokenizer.tokenize(text):
        end = offset + len(chunk.text)
        if chunk.kind in _OPAQUE:
            excluded.append((offset, end))
        offset = end
    return sorted(excluded)


def _finish(spans: list[tuple[int, int]], excluded: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Filter, deduplicate, and merge candidate spans against exclusions.

    Returns sorted non-overlapping ``(start, end)`` spans with excluded regions
    removed. Never returns ``None``.

    Raises:
        ValueError: If ``spans`` exceeds :data:`MAX_SPANS`.
    """
    if len(spans) > MAX_SPANS:
        raise ValueError("Context candidate output budget exceeded")
    output: list[tuple[int, int]] = []
    merged_excluded: list[tuple[int, int]] = []
    for start, end in sorted(excluded):
        if merged_excluded and start < merged_excluded[-1][1]:
            merged_excluded[-1] = (merged_excluded[-1][0], max(end, merged_excluded[-1][1]))
        else:
            merged_excluded.append((start, end))
    excluded_index = 0
    for start, end in sorted(set(spans)):
        while excluded_index < len(merged_excluded) and merged_excluded[excluded_index][1] <= start:
            excluded_index += 1
        if (start >= end or excluded_index < len(merged_excluded)
                and merged_excluded[excluded_index][0] < end):
            continue
        if output and start < output[-1][1]:
            output[-1] = (output[-1][0], max(end, output[-1][1]))
        else:
            output.append((start, end))
    return output


def _name_at(text: str, position: int, *, explicit: bool = False) -> tuple[int, int] | None:
    """Locate a quoted or token name starting at or after ``position``.

    Returns ``(start, end)`` over the name content (excluding quotes) when a
    valid name is found, or ``None`` when no acceptable name is present.
    Non-explicit unquoted names reject common pronoun/placeholders in
    :data:`_NON_NAMES`.
    """
    while position < len(text) and text[position] in " \t":
        position += 1
    if position >= len(text):
        return None
    if text[position] in _QUOTES:
        closer = _QUOTES[text[position]]
        end = text.find(closer, position + 1, position + MAX_VALUE_CHARS + 2)
        if end <= position + 1 or "\n" in text[position + 1:end] or "\r" in text[position + 1:end]:
            return None
        return position + 1, end
    match = _NAME_TOKEN.match(text, position)
    if match is None or not 1 <= len(match[0]) <= 64 or not explicit and match[0].casefold() in _NON_NAMES:
        return None
    return match.span()


def name_spans(text: str) -> list[tuple[int, int]]:
    """Protect explicit introductions/releases; unquoted names are one token."""
    excluded = _check(text)
    spans = []
    for pattern in (_INTRO, _RELEASE):
        for match in pattern.finditer(text):
            span = _name_at(text, match.end(), explicit=pattern is _INTRO)
            if span:
                spans.append(span)
    for match in _KO_SUFFIX.finditer(text):
        if unicodedata.normalize("NFC", match[1]) not in _NON_NAMES:
            spans.append(match.span(1))
    return _finish(spans, excluded)


def _value_at(text: str, position: int, scope_end: int) -> tuple[int, int] | None:
    """Parse a quoted or bare field value starting at ``position``.

    Returns ``(start, end)`` over the value content, or ``None`` when the value
    is absent, malformed, exceeds :data:`MAX_VALUE_CHARS`, or contains unsafe
    line breaks in quoted form.
    """
    if position >= scope_end:
        return None
    if text[position] in _QUOTES:
        closer = _QUOTES[text[position]]
        start, end, escaped = position + 1, position + 1, False
        while end < min(scope_end, start + MAX_VALUE_CHARS + 1):
            char = text[end]
            if char in "\r\n":
                return None
            if char == closer and not escaped:
                return (start, end) if start < end else None
            escaped = char == "\\" and not escaped
            end += 1
        return None
    end = position
    while end < scope_end and text[end] not in "\r\n;,}":
        end += 1
        if end - position > MAX_VALUE_CHARS:
            return None
    while end > position and text[end - 1].isspace():
        end -= 1
    return (position, end) if position < end else None


def _fields(text: str, start: int = 0, end: int | None = None) -> list[tuple[str, int, int]]:
    """Extract ``(normalized_label, value_start, value_end)`` form-field records.

    Scans ``text[start:end]`` for ``label: value`` patterns, skipping pipe-table
    lines and overlapping quoted values. Returns an empty list when no fields are
    found; never returns ``None``.
    """
    end = len(text) if end is None else end
    records = []
    skip_to = start
    pipe_lines = [match.span() for match in re.finditer(r"(?m)^[^\r\n]*\|[^\r\n]*$", text, re.MULTILINE)
                  if match.start() < end and match.end() > start]
    pipe_index = 0
    for match in _FIELD.finditer(text, start, end):
        if match.start() < skip_to:
            continue
        # A table cell is not a free-standing form field.
        while pipe_index < len(pipe_lines) and pipe_lines[pipe_index][1] <= match.start():
            pipe_index += 1
        if pipe_index < len(pipe_lines) and pipe_lines[pipe_index][0] <= match.start():
            continue
        span = _value_at(text, match.end(), end)
        if span:
            records.append((_label(match["label"]), *span))
            skip_to = span[1] + (1 if text[match.end():match.end() + 1] in _QUOTES else 0)
    return records


def _cells(line: str, offset: int) -> list[tuple[int, int]]:
    """Split a markdown table row into trimmed cell ``(start, end)`` spans.

    Respects escaped pipes and drops empty leading/trailing border cells.
    Returns an empty list for non-table lines; never returns ``None``.
    """
    if "|" not in line:
        return []
    cuts, escaped = [], False
    for index, char in enumerate(line):
        if char == "|" and not escaped:
            cuts.append(index)
        escaped = char == "\\" and not escaped
    if not cuts:
        return []
    borders = [-1, *cuts, len(line)]
    cells = []
    for left, right in zip(borders, borders[1:]):
        start, end = left + 1, right
        while start < end and line[start].isspace():
            start += 1
        while end > start and line[end - 1].isspace():
            end -= 1
        cells.append((offset + start, offset + end))
    if not line[:cuts[0]].strip():
        cells.pop(0)
    if not line[cuts[-1] + 1:].strip():
        cells.pop()
    return cells


def _table_fields(text: str) -> list[tuple[str, int, int]]:
    """Extract field records from valid markdown tables.

    Accepts tables with unique headers, matching delimiter rows, and consistent
    row cell counts (up to 64 columns). Returns ``(normalized_label, start, end)``
    records for non-empty, bounded cells; never returns ``None``. Malformed
    tables are skipped without raising.
    """
    lines, offset = [], 0
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        lines.append((line, offset))
        offset += len(raw)
    records = []
    index = 0
    while index + 1 < len(lines):
        header = _cells(*lines[index])
        delimiter = _cells(*lines[index + 1])
        labels = [_label(text[a:b]) for a, b in header]
        if (not header or len(header) > 64 or len(header) != len(delimiter)
                or len(set(labels)) != len(labels)
                or not all(re.fullmatch(r":?-{3,}:?", text[a:b]) for a, b in delimiter)):
            index += 1
            continue
        index += 2
        pending: list[tuple[str, int, int]] = []
        valid = True
        while index < len(lines) and "|" in lines[index][0]:
            cells = _cells(*lines[index])
            if len(cells) != len(header):
                valid = False
            else:
                pending.extend((label, start, end) for label, (start, end) in zip(labels, cells)
                               if start < end and end - start <= MAX_VALUE_CHARS)
            index += 1
        if valid:
            records.extend(pending)
    return records


def structure_spans(text: str) -> list[tuple[int, int]]:
    """Protect name-field values; never promote arbitrary labels to protocol."""
    excluded = _check(text)
    records = _fields(text)
    labels = [record[0] for record in records]
    # Duplicate form labels make row ownership ambiguous. Tables have their own
    # per-header validation and can legitimately repeat values across rows.
    records = [] if len(labels) != len(set(labels)) else records
    records.extend(_table_fields(text))
    return _finish([(start, end) for label, start, end in records if label in _NAME_FIELDS], excluded)


def numeric_spans(text: str) -> list[tuple[int, int]]:
    """Protect identifier fields in source text without numeric conversion."""
    excluded = _check(text)
    records = _fields(text) + _table_fields(text)
    spans = [(start, end) for label, start, end in records if label in _NUMERIC_FIELDS
             and re.fullmatch(r"[+-]?\d+(?:[- ./]\d+)*", text[start:end])]
    return _finish(spans, excluded)


def bundle_spans(text: str, policy: dict) -> list[tuple[int, int]]:
    """Protect co-present form fields in a locally supplied hash-bound scope.

    Policy keys: document_sha256, scope=[start,end], required_fields and
    protect_fields. A caller supplies this trusted local policy; text claiming
    its own project/scope does not establish authority. No generalized category
    is substituted, and missing/duplicate fields add no protection proposals.
    """
    excluded = _check(text)
    if not isinstance(policy, dict) or set(policy) != {"document_sha256", "scope", "required_fields", "protect_fields"}:
        raise ValueError("Invalid bundle policy")
    if policy["document_sha256"] != sha256(text.encode("utf-8")).hexdigest():
        raise ValueError("Bundle document identity mismatch")
    scope = policy["scope"]
    if (not isinstance(scope, (list, tuple)) or len(scope) != 2
            or any(type(value) is not int for value in scope) or not 0 <= scope[0] <= scope[1] <= len(text)):
        raise ValueError("Invalid bundle scope")
    fields = []
    for key in ("required_fields", "protect_fields"):
        values = policy[key]
        if (not isinstance(values, list) or not 1 <= len(values) <= 32
                or any(not isinstance(value, str) or not 1 <= len(value) <= 64 for value in values)):
            raise ValueError("Invalid bundle fields")
        normalized = {_label(value) for value in values}
        if len(normalized) != len(values):
            raise ValueError("Duplicate bundle field policy")
        fields.append(normalized)
    required, protected = fields
    records = _fields(text, *scope)
    labels = [record[0] for record in records]
    if len(set(labels)) != len(labels) or not (required | protected).issubset(labels):
        return []
    return _finish([(start, end) for label, start, end in records if label in protected], excluded)
