"""Trusted-user introduction candidates for the opt-in name experiment."""
from __future__ import annotations

import re

from secure_gateway.experiment_context import _INTRO, _RELEASE, name_spans

_QUOTED = re.compile(r'"[^"\r\n]*"|“[^”\r\n]*”|‘[^’\r\n]*’|「[^」\r\n]*」|『[^』\r\n]*』')


def trusted_name_spans(text: str) -> list[tuple[int, int]]:
    """Discard quoted third-party assertions, keeping direct quoted names."""
    quoted = list(_QUOTED.finditer(text))
    result = []
    candidates = name_spans(text)
    if len(candidates) > 128:
        return []
    for start, end in candidates:
        line_start = text.rfind("\n", 0, start) + 1
        if text[line_start:start].lstrip().startswith(">"):
            continue
        container = next((m for m in quoted if m.start() < start and end <= m.end()), None)
        if container:
            prefix = text[:container.start()]
            direct = start == container.start() + 1 and any(
                any(m.end() in {len(prefix), len(prefix.rstrip())} for m in pattern.finditer(prefix)) for pattern in (_INTRO, _RELEASE)
            )
            if not direct:
                continue
        word = text[start:end]
        if re.fullmatch(r"[\uac00-\ud7a3]+", word):
            for suffix in ("\uc785\ub2c8\ub2e4", "\uc774\uc5d0\uc694", "\uc608\uc694"):
                if word.endswith(suffix) and len(word) > len(suffix):
                    end -= len(suffix)
                    break
        result.append((start, end))
    return result


def user_texts(payload: dict) -> list[str]:
    """Extract only direct user prose, never tool outputs or protocol fields."""
    messages = payload.get("messages", payload.get("input", []))
    if isinstance(messages, str):
        return [messages]
    if not isinstance(messages, list):
        return []
    result = []
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            result.append(content)
        elif isinstance(content, list):
            result.extend(item["text"] for item in content if isinstance(item, dict)
                          and item.get("type") in {"text", "input_text"} and isinstance(item.get("text"), str))
    return result


def role_declarations(text: str, pattern: re.Pattern) -> list:
    """Inspect at most 64 introductions after a single quote/source scan."""
    from secure_gateway.gateway_source import looks_like_source, markdown_code_spans

    if len(text.encode("utf-8")) > 1024 * 1024 or looks_like_source(text[:4096]):
        return []
    try:
        blocked = [(match.start(), match.end()) for match in _QUOTED.finditer(text)]
        blocked.extend(markdown_code_spans(text))
    except ValueError:
        return []
    merged: list[tuple[int, int]] = []
    for start, end in sorted(blocked):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    result = []
    index = 0
    for count, match in enumerate(pattern.finditer(text)):
        if count >= 64:
            break
        start, end = match.span()
        while index < len(merged) and merged[index][1] <= start:
            index += 1
        if index < len(merged) and merged[index][0] < end:
            continue
        line = text.rfind("\n", 0, start) + 1
        if text[line:start].lstrip().startswith(">"):
            continue
        result.append(match)
    return result
