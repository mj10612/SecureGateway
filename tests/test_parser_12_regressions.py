"""Regressions for contextual and escaped source identifiers."""

import pytest

from secure_gateway.engine.code_parser import CodeParser
from secure_gateway.models import TokenType


@pytest.mark.parametrize("language", ["javascript", "typescript"])
@pytest.mark.parametrize("name", [r"private\u004eame", r"\u{70}rivateName", "$privateName"])
def test_javascript_escaped_identifiers_are_single_raw_tokens(language, name):
    source = f"const {name} = 1; console.log({name});"
    tokens = CodeParser.tokenize(source, language)
    assert "".join(raw for raw, _, _ in tokens) == source
    assert [(raw, kind) for raw, token_type, kind in tokens if raw == name] == [
        (name, "identifier"), (name, "identifier")
    ]
    assert all(token_type == TokenType.IDENTIFIER for raw, token_type, _ in tokens if raw == name)


@pytest.mark.parametrize("name", [r"\u{110000}name", r"\u0020name", r"\uZZZZ"])
def test_invalid_identifier_escapes_fail_closed(name):
    with pytest.raises(ValueError, match="identifier"):
        CodeParser.tokenize(f"const {name} = 1;", "javascript")


@pytest.mark.parametrize("name", ["match", "case"])
def test_python_annotated_soft_keyword_is_an_identifier(name):
    tokens = CodeParser.tokenize(f"{name}: int = 3\nresult = {name}\n", "python")
    occurrences = [(token_type, kind) for raw, token_type, kind in tokens if raw == name]
    assert occurrences == [(TokenType.IDENTIFIER, "identifier")] * 2


def test_python_match_case_grammar_remains_structural():
    tokens = CodeParser.tokenize("match subject:\n    case _:\n        pass\n", "python")
    assert all(kind == "keyword" for raw, _, kind in tokens if raw in {"match", "case", "_"})


def test_rust_raw_identifier_is_a_single_token():
    source = "fn main() { let r#type = 1; let result = r#type; }"
    tokens = CodeParser.tokenize(source, "rust")
    assert "".join(raw for raw, _, _ in tokens) == source
    assert [(token_type, kind) for raw, token_type, kind in tokens if raw == "r#type"] == [
        (TokenType.IDENTIFIER, "identifier")
    ] * 2


@pytest.mark.parametrize("language,name", [
    ("python", "cafe\u0301"), ("rust", "cafe\u0301"),
    ("rust", "r#cafe\u0301"), ("javascript", "cafe\u0301"),
])
def test_combining_identifier_continuations_remain_in_the_name(language, name):
    source = f"{name} = 1"
    tokens = CodeParser.tokenize(source, language)
    assert tokens[0] == (name, TokenType.IDENTIFIER, "identifier")
    assert "".join(raw for raw, _, _ in tokens) == source


def test_semicolon_free_javascript_and_module_context():
    tokens = CodeParser.tokenize("var privateName = 1\n" * 4000, "javascript")
    assert sum(raw == "privateName" for raw, _, _ in tokens) == 4000
    tokens = CodeParser.tokenize('import { value as renamed } from "module"; const from = 1;', "javascript")
    assert [(raw, kind) for raw, _, kind in tokens if raw in {"as", "from"}] == [
        ("as", "keyword"), ("from", "keyword"), ("from", "identifier")
    ]
