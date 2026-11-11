"""Ground truth span alignment and verification between original and masked text."""

from __future__ import annotations

import re
from typing import Any, Callable

RESERVED_ALIAS_PATTERN = re.compile(r"(?:smcp_(?:ID|NUM|LIT)|private_symbol)_\d+", re.IGNORECASE)
DELIMITED_ALIAS_PATTERN = re.compile(r"⟦([^⟦⟧]+)⟧")
CREDENTIAL_PLACEHOLDER = "[credential removed]"

_DELIMITED_UNICODE = r"⟦[^⟦⟧\r\n]+⟧"
_DELIMITED_ANGLE = r"⟪[^⟪⟫\r\n]+⟫"
_STRATEGY_BRACKET = r"\[(?:ENT(?:ITY)?|NOUN|VERB|ADJ|NUM(?:BER)?|ID|LIT|SYM)[-_ ]*\d+\]"
_STRATEGY_HASH = r"~h\d+[-_ ]+[a-f0-9]+~"
_CODE_IDENTIFIER = r"(?<![A-Za-z0-9_])(?:smcp_(?:ID|NUM|LIT)|private_symbol)_\d+(?![A-Za-z0-9_])"
_NUMERIC_ALIAS = r"(?<![A-Za-z0-9_])732846\d{12}(?![A-Za-z0-9_])"

_STATIC_ALIAS_PATTERNS = [
    _DELIMITED_UNICODE,
    _DELIMITED_ANGLE,
    _STRATEGY_BRACKET,
    _STRATEGY_HASH,
    _CODE_IDENTIFIER,
    _NUMERIC_ALIAS,
]


def extract_mappings(session_or_mappings: Any) -> tuple[dict[str, str], Callable[[str], str] | None]:
    """Extract a surrogate->original string dictionary and optional restore callable."""
    restore_fn = None
    if hasattr(session_or_mappings, "session") and hasattr(session_or_mappings.session, "reverse_store"):
        reverse_store = session_or_mappings.session.reverse_store
        if hasattr(session_or_mappings, "restore"):
            restore_fn = session_or_mappings.restore
        mapping = {k: (v.original if hasattr(v, "original") else str(v)) for k, v in reverse_store.items()}
        return mapping, restore_fn

    if isinstance(session_or_mappings, dict):
        mapping = {}
        for k, v in session_or_mappings.items():
            orig = v.original if hasattr(v, "original") else str(v)
            mapping[str(k)] = orig
        return mapping, None

    return {}, None


def find_unrestored_aliases(text: str, mapping: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Find unrestored or altered aliases remaining in displayed text."""
    if not text:
        return []

    spans: list[dict[str, Any]] = []
    seen_ranges: set[tuple[int, int]] = set()

    for match in DELIMITED_ALIAS_PATTERN.finditer(text):
        rng = (match.start(), match.end())
        seen_ranges.add(rng)
        spans.append({
            "start": match.start(),
            "end": match.end(),
            "alias": match.group(0),
            "unrestored": True,
        })

    for match in RESERVED_ALIAS_PATTERN.finditer(text):
        rng = (match.start(), match.end())
        if rng not in seen_ranges:
            seen_ranges.add(rng)
            spans.append({
                "start": match.start(),
                "end": match.end(),
                "alias": match.group(0),
                "unrestored": True,
            })

    if mapping:
        for surrogate in mapping:
            if not surrogate:
                continue
            escaped = re.escape(surrogate)
            if surrogate[0].isalnum() and surrogate[-1].isalnum():
                pat = r"(?<![A-Za-z0-9_])" + escaped + r"(?![A-Za-z0-9_])"
            else:
                pat = escaped
            for match in re.finditer(pat, text):
                rng = (match.start(), match.end())
                if rng not in seen_ranges:
                    seen_ranges.add(rng)
                    spans.append({
                        "start": match.start(),
                        "end": match.end(),
                        "alias": match.group(0),
                        "unrestored": True,
                    })

    spans.sort(key=lambda s: s["start"])
    return spans


def _build_alias_pattern(known_bindings: dict[str, str] | None) -> re.Pattern[str]:
    patterns: list[str] = []
    if known_bindings:
        # Sort custom keys by length descending to match most specific first
        for k in sorted(known_bindings.keys(), key=len, reverse=True):
            if not k:
                continue
            esc = re.escape(k)
            if not (k.startswith("⟦") and k.endswith("⟧")):
                patterns.append(r"⟦" + esc + r"⟧")
            if k[0].isalnum() and k[-1].isalnum():
                patterns.append(r"(?<![A-Za-z0-9_])" + esc + r"(?![A-Za-z0-9_])")
            else:
                patterns.append(esc)

    patterns.extend(_STATIC_ALIAS_PATTERNS)
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)


def _lookup_binding(tok: str, bindings: dict[str, str]) -> str | None:
    if tok in bindings:
        return bindings[tok]
    if tok.startswith("⟦") and tok.endswith("⟧"):
        raw = tok[1:-1]
        if raw in bindings:
            return bindings[raw]
    raw = tok.strip("⟦⟧")
    if raw in bindings:
        return bindings[raw]
    wrapped = f"⟦{tok}⟧"
    if wrapped in bindings:
        return bindings[wrapped]
    return None


def _record_binding(tok: str, val: str, bindings: dict[str, str]) -> dict[str, str]:
    updated = dict(bindings)
    updated[tok] = val
    if tok.startswith("⟦") and tok.endswith("⟧"):
        updated[tok[1:-1]] = val
    else:
        updated[f"⟦{tok}⟧"] = val
    return updated


def align_pair(
    original: str,
    masked: str,
    known_bindings: dict[str, str] | None = None,
    restore_fn: Callable[[str], str] | None = None,
) -> tuple[bool, list[dict[str, Any]], dict[str, str]]:
    """Align recorded pair of original and masked text by anchoring on public segments.

    Enforces that every occurrence of the same alias maps to the same original,
    and verifies by exact reconstruction of both texts. If alignment fails or is
    ambiguous, returns (True, [], {}).
    """
    if CREDENTIAL_PLACEHOLDER in original or CREDENTIAL_PLACEHOLDER in masked:
        return True, [], {}

    if not original and not masked:
        return False, [], (dict(known_bindings) if known_bindings else {})

    if not original or not masked:
        return True, [], {}

    if original == masked:
        return False, [], (dict(known_bindings) if known_bindings else {})

    alias_pat = _build_alias_pattern(known_bindings)
    alias_matches: list[tuple[int, int, str]] = [
        (m.start(), m.end(), m.group(0)) for m in alias_pat.finditer(masked)
    ]

    if not alias_matches:
        # Masked text differs from original but contains no recognized alias tokens
        return True, [], {}

    k = len(alias_matches)
    public_segments: list[str] = [masked[0 : alias_matches[0][0]]]
    for i in range(1, k):
        public_segments.append(masked[alias_matches[i - 1][1] : alias_matches[i][0]])
    public_segments.append(masked[alias_matches[k - 1][1] :])

    p0 = public_segments[0]
    pk = public_segments[-1]

    if not original.startswith(p0):
        return True, [], {}
    if not original.endswith(pk):
        return True, [], {}

    pos_start = len(p0)
    pos_end = len(original) - len(pk)
    if pos_start >= pos_end:
        return True, [], {}

    initial_bindings = dict(known_bindings or {})
    valid_solutions: list[tuple[list[dict[str, Any]], dict[str, str]]] = []

    def search(
        idx: int,
        cur_orig_pos: int,
        cur_bindings: dict[str, str],
        cur_spans: list[dict[str, Any]],
    ) -> None:
        if len(valid_solutions) > 1:
            return  # Ambiguity already detected

        m_start, m_end, tok = alias_matches[idx]

        if idx == k - 1:
            orig_val = original[cur_orig_pos:pos_end]
            if not orig_val:
                return
            expected = _lookup_binding(tok, cur_bindings)
            if expected is not None and expected != orig_val:
                return
            new_b = _record_binding(tok, orig_val, cur_bindings)
            span = {
                "index": idx,
                "original_start": cur_orig_pos,
                "original_end": pos_end,
                "masked_start": m_start,
                "masked_end": m_end,
                "alias": tok,
            }
            valid_solutions.append((cur_spans + [span], new_b))
            return

        next_p = public_segments[idx + 1]
        expected = _lookup_binding(tok, cur_bindings)

        if expected is not None:
            orig_val = expected
            orig_end = cur_orig_pos + len(orig_val)
            if orig_end > pos_end:
                return
            if original[cur_orig_pos:orig_end] != orig_val:
                return
            if not original.startswith(next_p, orig_end):
                return
            next_orig_pos = orig_end + len(next_p)
            span = {
                "index": idx,
                "original_start": cur_orig_pos,
                "original_end": orig_end,
                "masked_start": m_start,
                "masked_end": m_end,
                "alias": tok,
            }
            search(idx + 1, next_orig_pos, cur_bindings, cur_spans + [span])
        else:
            min_remaining_orig = k - 1 - idx
            max_orig_end = pos_end - min_remaining_orig

            if len(next_p) == 0:
                for orig_end in range(cur_orig_pos + 1, max_orig_end + 1):
                    orig_val = original[cur_orig_pos:orig_end]
                    new_b = _record_binding(tok, orig_val, cur_bindings)
                    span = {
                        "index": idx,
                        "original_start": cur_orig_pos,
                        "original_end": orig_end,
                        "masked_start": m_start,
                        "masked_end": m_end,
                        "alias": tok,
                    }
                    search(idx + 1, orig_end, new_b, cur_spans + [span])
                    if len(valid_solutions) > 1:
                        return
            else:
                search_start = cur_orig_pos + 1
                while True:
                    found_pos = original.find(next_p, search_start, pos_end + len(next_p))
                    if found_pos == -1 or found_pos > max_orig_end:
                        break
                    orig_end = found_pos
                    orig_val = original[cur_orig_pos:orig_end]
                    new_b = _record_binding(tok, orig_val, cur_bindings)
                    span = {
                        "index": idx,
                        "original_start": cur_orig_pos,
                        "original_end": orig_end,
                        "masked_start": m_start,
                        "masked_end": m_end,
                        "alias": tok,
                    }
                    search(idx + 1, orig_end + len(next_p), new_b, cur_spans + [span])
                    if len(valid_solutions) > 1:
                        return
                    search_start = found_pos + 1

    search(0, pos_start, initial_bindings, [])

    if len(valid_solutions) != 1:
        # 0 solutions means failed alignment; >1 solutions means ambiguous
        return True, [], {}

    sol_spans, sol_bindings = valid_solutions[0]

    # Reconstruct original and masked texts exactly
    recon_o: list[str] = [public_segments[0]]
    recon_m: list[str] = [public_segments[0]]
    for i, s in enumerate(sol_spans):
        recon_o.append(original[s["original_start"] : s["original_end"]])
        recon_o.append(public_segments[i + 1])
        recon_m.append(masked[s["masked_start"] : s["masked_end"]])
        recon_m.append(public_segments[i + 1])

    if "".join(recon_o) != original or "".join(recon_m) != masked:
        return True, [], {}

    for s in sol_spans:
        tok = s["alias"]
        orig_val = original[s["original_start"] : s["original_end"]]
        expected = _lookup_binding(tok, sol_bindings)
        if expected != orig_val:
            return True, [], {}

    if restore_fn is not None:
        try:
            if restore_fn(masked) != original:
                return True, [], {}
        except Exception:
            return True, [], {}

    return False, sol_spans, sol_bindings


def derive_spans(
    session_or_mappings: Any,
    original: str,
    masked: str,
    restore_fn: Callable[[str], str] | None = None,
) -> tuple[bool, list[dict[str, Any]]]:
    """Derive aligned spans between original and masked text grounded in mappings or alignment."""
    mapping, extracted_restore = extract_mappings(session_or_mappings)
    if restore_fn is None:
        restore_fn = extracted_restore
    uncertain, spans, _ = align_pair(original, masked, known_bindings=mapping, restore_fn=restore_fn)
    return uncertain, spans
