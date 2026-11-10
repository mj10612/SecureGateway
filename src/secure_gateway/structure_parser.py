"""Linear-pass, offset-preserving parser for Markdown tables and forms (#317).

Exposes `cells(text) -> [(row, field_name, start, end)]` mapped to original offsets
without rewriting, reordering, or summarizing text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata

from secure_gateway.gateway_source import looks_like_source, markdown_code_spans

MAX_INPUT_BYTES: int = 1024 * 1024
MAX_TABLE_ROWS: int = 1000
MAX_TABLE_COLS: int = 64
MAX_VALUE_CHARS: int = 4096
_QUOTES = {'"': '"', "'": "'", "‘": "’", "“": "”", "「": "」", "『": "』"}

_FIELD_PATTERN = re.compile(
    r"(?:[\n;{,]|^)\s*[\"']?(?P<label>[\w가-힣][\w가-힣 \t-]{0,63})[\"']?\s*[:：]\s*"
)

# Reviewed public field names that are recognized as legitimate table/form structure headers
REVIEWED_PUBLIC_FIELDS: frozenset[str] = frozenset(
    re.sub(r"[\s_-]+", "", s.casefold())
    for s in (
        "project", "project name", "company", "company name", "customer", "customer name",
        "product", "product name", "person", "person name", "state", "status", "next action",
        "action", "date", "due", "due date", "site", "location", "notes", "description",
        "role", "reviewer", "document", "category", "item", "quantity", "unit", "price",
        "total", "device", "device serial", "serial number", "customer id", "account id",
        "retry count", "version", "firmware", "firmware version",
        "프로젝트", "프로젝트명", "프로젝트 이름", "회사", "회사명", "고객", "고객명", "고객사", "고객사 이름",
        "제품명", "이름", "상태", "검토상태", "검토 상태", "다음행동", "다음 행동", "금지사항", "금지 사항",
        "일정", "납기", "지역", "장소", "비고", "설명", "역할", "담당자", "검토문서", "받는사람",
        "항목", "수량", "단위", "단가", "합계", "금액", "장비", "장비번호", "일련번호", "고객번호",
        "계정번호", "재시도횟수", "버전", "요청",
    )
)


@dataclass
class StructureParseResult:
    """Parsed document structure containing cells, header spans, and table/form counts."""

    cells: list[tuple[int, str, int, int]] = field(default_factory=list)
    header_spans: list[tuple[str, int, int]] = field(default_factory=list)
    fallback_count: int = 0
    tables_count: int = 0
    forms_count: int = 0


def _normalize_label(label: str) -> str:
    return re.sub(r"[\s_-]+", "", unicodedata.normalize("NFC", label).casefold())


def _split_table_line(line: str, offset: int) -> list[tuple[int, int]]:
    """Split a markdown table row by unescaped pipes, returning (start, end) offsets."""
    if "|" not in line:
        return []
    cuts: list[int] = []
    escaped = False
    for index, char in enumerate(line):
        if char == "|" and not escaped:
            cuts.append(index)
        escaped = char == "\\" and not escaped
    if not cuts:
        return []
    borders = [-1, *cuts, len(line)]
    cell_spans: list[tuple[int, int]] = []
    for left, right in zip(borders, borders[1:]):
        start, end = left + 1, right
        while start < end and line[start].isspace():
            start += 1
        while end > start and line[end - 1].isspace():
            end -= 1
        cell_spans.append((offset + start, offset + end))
    # Remove leading/trailing empty cells from outer pipes: | cell | cell |
    if not line[:cuts[0]].strip() and cell_spans:
        cell_spans.pop(0)
    if not line[cuts[-1] + 1:].strip() and cell_spans:
        cell_spans.pop()
    return cell_spans


def _value_at(text: str, position: int, scope_end: int) -> tuple[int, int] | None:
    """Find bounds of a form value starting at position up to scope_end."""
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


def parse_structure(text: str) -> StructureParseResult:
    """Linear-pass, offset-preserving parser for Markdown tables and forms.

    Returns header/field-name spans and cell value spans mapped to original offsets;
    never rewrites, reorders, or summarises text.
    Broken/ambiguous tables fall back to the existing path and are counted.
    """
    if not isinstance(text, str):
        raise ValueError("Structure parser input must be text")
    if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("Structure parser input budget exceeded")

    result = StructureParseResult()

    try:
        code_spans = markdown_code_spans(text)
    except ValueError:
        result.fallback_count += 1
        return result

    # Source code boundaries take precedence
    if looks_like_source(text[:4096]) and not any("|" in line for line in text[:4096].splitlines()):
        result.fallback_count += 1
        return result

    # 1. Parse Markdown tables
    lines: list[tuple[str, int]] = []
    offset = 0
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        lines.append((line, offset))
        offset += len(raw)

    line_index = 0
    table_row_count = 0
    in_table_line_indices: set[int] = set()

    while line_index + 1 < len(lines):
        line_str, line_off = lines[line_index]
        # Skip lines inside code blocks
        if any(start <= line_off < end for start, end in code_spans):
            line_index += 1
            continue

        if "|" not in line_str:
            line_index += 1
            continue

        header_cells = _split_table_line(line_str, line_off)
        delim_str, delim_off = lines[line_index + 1]
        delim_cells = _split_table_line(delim_str, delim_off)

        raw_headers = [text[a:b] for a, b in header_cells]
        norm_headers = [_normalize_label(h) for h in raw_headers]

        is_delimiter = (
            len(header_cells) > 0
            and len(header_cells) <= MAX_TABLE_COLS
            and len(header_cells) == len(delim_cells)
            and all(re.fullmatch(r":?-{3,}:?", text[a:b]) for a, b in delim_cells)
        )

        if not is_delimiter:
            line_index += 1
            continue

        # Ambiguous column headers (duplicates) -> fall back and count
        if len(set(norm_headers)) != len(norm_headers) or not all(raw_headers):
            result.fallback_count += 1
            line_index += 2
            continue

        in_table_line_indices.add(line_index)
        in_table_line_indices.add(line_index + 1)
        for h_str, (h_start, h_end) in zip(raw_headers, header_cells):
            result.header_spans.append((h_str, h_start, h_end))

        line_index += 2
        pending_cells: list[tuple[int, str, int, int]] = []
        table_valid = True
        row_in_table = 0

        while line_index < len(lines) and "|" in lines[line_index][0]:
            r_str, r_off = lines[line_index]
            if any(start <= r_off < end for start, end in code_spans):
                break
            cells = _split_table_line(r_str, r_off)
            if len(cells) != len(header_cells):
                # Column count mismatch -> broken table, fall back
                table_valid = False
                break
            if row_in_table >= MAX_TABLE_ROWS:
                table_valid = False
                break

            in_table_line_indices.add(line_index)
            for col_idx, (c_start, c_end) in enumerate(cells):
                if c_start < c_end and c_end - c_start <= MAX_VALUE_CHARS:
                    # Cell content
                    pending_cells.append((table_row_count + row_in_table, raw_headers[col_idx], c_start, c_end))

            row_in_table += 1
            line_index += 1

        if table_valid and row_in_table > 0:
            result.cells.extend(pending_cells)
            result.tables_count += 1
            table_row_count += row_in_table
        else:
            result.fallback_count += 1

    # 2. Parse consistent form fields (항목: 값) outside tables and code
    pipe_line_spans = [
        (off, off + len(lines[i][0]))
        for i, (_, off) in enumerate(lines)
        if i in in_table_line_indices
    ]

    form_records: list[tuple[str, int, int]] = []
    skip_to = 0
    form_row = table_row_count

    for match in _FIELD_PATTERN.finditer(text):
        m_start = match.start()
        if m_start < skip_to:
            continue
        # Inside code blocks
        if any(c_start <= m_start < c_end for c_start, c_end in code_spans):
            continue
        # Inside table lines
        if any(p_start <= m_start < p_end for p_start, p_end in pipe_line_spans):
            continue

        raw_label = match["label"].strip()
        val_span = _value_at(text, match.end(), len(text))
        if val_span:
            form_records.append((raw_label, val_span[0], val_span[1]))
            skip_to = val_span[1] + (1 if text[match.end():match.end() + 1] in _QUOTES else 0)

    # Check for duplicate labels in consistent forms
    norm_form_labels = [_normalize_label(r[0]) for r in form_records]
    if len(norm_form_labels) != len(set(norm_form_labels)):
        # Duplicate form labels make ownership ambiguous -> fall back
        result.fallback_count += 1
    else:
        for raw_label, v_start, v_end in form_records:
            result.cells.append((form_row, raw_label, v_start, v_end))
            form_row += 1
        if form_records:
            result.forms_count += 1

    return result


def cells(text: str) -> list[tuple[int, str, int, int]]:
    """Linear-pass, offset-preserving parser returning [(row, field_name, start, end)]."""
    return parse_structure(text).cells


def doc_structure_spans(
    text: str,
    field_policy: dict[str, str] | None = None,
    always_protect_name_fields: bool = True,
) -> list[tuple[int, int]]:
    """Compute original-offset spans to mask based on document structure.

    Candidate B (`doc_structure`):
      Reviewed public field names stay public, cell values under sensitive fields
      go through protection.
    Candidate C (`doc_structure_policy`):
      A local policy maps field names -> 'always_mask'. Those cell values are
      unconditionally protected.
    """
    parsed = parse_structure(text)
    spans: list[tuple[int, int]] = []

    normalized_policy = (
        {_normalize_label(k): v for k, v in field_policy.items()}
        if field_policy
        else {}
    )

    for _, field_name, start, end in parsed.cells:
        norm = _normalize_label(field_name)

        # Candidate C policy check
        if norm in normalized_policy:
            policy_action = normalized_policy[norm]
            if policy_action in {"always_mask", "mask", "protect"}:
                spans.append((start, end))
                continue

        # Candidate B behavior
        if always_protect_name_fields:
            from secure_gateway.experiment_context import _NAME_FIELDS
            if norm in _NAME_FIELDS:
                spans.append((start, end))

    # Merge overlapping or adjacent spans
    if not spans:
        return []
    spans.sort()
    merged: list[tuple[int, int]] = [spans[0]]
    for cur_start, cur_end in spans[1:]:
        last_start, last_end = merged[-1]
        if cur_start <= last_end:
            merged[-1] = (last_start, max(last_end, cur_end))
        else:
            merged.append((cur_start, cur_end))
    return merged
