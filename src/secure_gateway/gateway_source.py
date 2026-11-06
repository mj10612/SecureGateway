"""Recognize source context without promoting an embedded prose assignment."""

import ast
import re


_LEADING_COMMENTS = re.compile(
    r"\A\s*(?:(?://[^\n]*(?:\n|$)|--[^\n]*(?:\n|$)|/\*[\s\S]*?\*/|\#[^\n]*(?:\n|$))\s*)+"
)
_DECLARATION = re.compile(
    r"\A(?:"
    r"(?:async\s+)?def\s+\w+\s*\("
    r"|class\s+\w+[^\n]*[:{]"
    r"|(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*\w*\s*\("
    r"|(?:export\s+)?(?:const|let|var)\s+\w+\s*(?:=|:|;)"
    r"|(?:export\s+)?(?:interface|enum|namespace)\s+\w+[^\n]*\{"
    r"|(?:export\s+)?type\s+\w+\s*(?:<[^\n]*>)?\s*="
    r"|import\s+(?:[\"']|[^\n]+\s+from\s+[\"'])"
    r"|package\s+\w+(?:\s|;|$)"
    r"|func\s+(?:\([^\n]+\)\s*)?\w+\s*\("
    r"|(?:pub(?:\([^\n]+\))?\s+)?(?:async\s+)?fn\s+\w+\s*(?:<[^\n]*>)?\s*\("
    r"|use\s+[\w:]+[^\n]*;"
    r"|mod\s+\w+\s*[;{]"
    r"|impl\s+[^\n]+\{"
    r"|\#\s*include\s*[<\"]"
    r"|(?:int|void|char|float|double|bool)\s+\w+\s*\("
    r")"
)
_SQL = re.compile(
    r"\A(?:SELECT\b(?=[\s\S]*\bFROM\b)"
    r"|SELECT\s+(?:\d|[\"'(]|\w+\s*\(|\w+\s*;)"
    r"|INSERT\s+INTO\b|UPDATE\s+\S+\s+SET\b|DELETE\s+FROM\b"
    r"|(?:CREATE|DROP)\s+(?:TABLE|INDEX|VIEW|DATABASE)\b|ALTER\s+TABLE\b)",
    re.IGNORECASE,
)


def looks_like_source(text: str) -> bool:
    """Prefer a complete native Python parse, then explicit leading source syntax.

    A Python-looking assignment embedded in a longer prose message does not
    establish source context for the entire message. Fenced and explicit code
    paths are classified separately by the caller.
    """
    source = text.strip()
    if not source:
        return False
    try:
        statements = ast.parse(source).body
    except (SyntaxError, ValueError, RecursionError):
        statements = []
    if any(
        not isinstance(statement, ast.Expr)
        or isinstance(statement.value, (ast.Call, ast.Subscript, ast.Await))
        for statement in statements
    ):
        return True
    if _DECLARATION.match(source) or _SQL.match(source):
        return True
    source = _LEADING_COMMENTS.sub("", source).lstrip()
    return bool(_DECLARATION.match(source) or _SQL.match(source))


def markdown_code_spans(text: str) -> list[tuple[int, int]]:
    """Find code spans using equal-length backtick delimiters in one scan.

    Runs of another length inside a span are content, as in Markdown's double
    backtick notation for a literal single backtick. The same spans drive both
    validation and masking, including multiline inline code.
    """
    runs = iter(re.finditer(r"`+", text))
    spans = []
    for opener in runs:
        for closer in runs:
            if len(closer.group()) == len(opener.group()):
                spans.append((opener.start(), closer.end()))
                break
        else:
            raise ValueError("Unclosed Markdown code span; close the backticks before sending.")
        if len(spans) > 4096:
            raise ValueError("Too many Markdown code spans; split the request.")
    return spans
