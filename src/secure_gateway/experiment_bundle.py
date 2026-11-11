"""Additional row-scoped bundle proposals using the existing table cell parser."""

from __future__ import annotations

from secure_gateway.experiment_context import _check, _finish, _label, bundle_spans as form_spans
from secure_gateway.structure_parser import cells


def bundle_spans(text: str, policy: dict) -> list[tuple[int, int]]:
    """Protect form values and table values only when a single row satisfies policy."""
    spans = form_spans(text, policy)  # validates document identity, scope and policy
    required = {_label(value) for value in policy["required_fields"]}
    protected = {_label(value) for value in policy["protect_fields"]}
    low, high = policy["scope"]
    rows: dict[int, list[tuple[str, int, int]]] = {}
    for row, label, start, end in cells(text):
        if low <= start < end <= high:
            rows.setdefault(row, []).append((_label(label), start, end))
    for row_cells in rows.values():
        labels = {label for label, _, _ in row_cells}
        if len(labels) == len(row_cells) and (required | protected).issubset(labels):
            spans.extend((start, end) for label, start, end in row_cells if label in protected)
    return _finish(spans, _check(text))
