"""Regression coverage for the lexer issues in the October issue batch."""

import ast

import pytest

from secure_gateway.engine.code_parser import CodeParser, literal_parts
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import TokenType
from secure_gateway.session import PrivacySession


def mask(code, language):
    session = PrivacySession("batch-parser")
    engine = MaskingEngine()
    result = engine.mask_code(code, session.session_id, session.generator,
                              session.forward_store, session.reverse_store,
                              language=language)
    restored = engine.unmask(result.masked_text, session.session_id,
                             session.reverse_store)
    assert restored.unmasked_text == code
    return result.masked_text


def test_c_keywords_do_not_preserve_cpp_identifier_names():
    result = mask("int private = 1; int namespace = 2; _Atomic int secret;", "c")
    assert "private" not in result and "namespace" not in result
    assert "_Atomic" in result


@pytest.mark.parametrize("code", [
    'const pattern = /["\']/g;',
    r'const pattern = /private\/secret[\/]/gi;',
    'function check(value) { return /private/.test(value); }',
    'if (ready) /private/.test(value);',
])
def test_javascript_regex_literals_are_opaque(code):
    result = mask(code, "javascript")
    assert "private" not in result
    regexes = [raw for raw, _, kind in CodeParser.tokenize(code, "javascript")
               if kind == "regex"]
    assert len(regexes) == 1
    assert literal_parts(regexes[0], "regex")[0] == "/"


def test_javascript_division_is_not_a_regex():
    code = "const answer = left / right / divisor;"
    assert not any(kind == "regex" for _, _, kind in CodeParser.tokenize(code, "javascript"))
    assert mask(code, "javascript").count("/") == 2


@pytest.mark.parametrize("code", [
    "const answer = {} / divisor;",
    "const answer = ({private: 1}) / divisor;",
    "const answer = counter++ / divisor;",
])
def test_javascript_division_after_compound_expressions(code):
    assert not any(kind == "regex" for _, _, kind in CodeParser.tokenize(code, "javascript"))
    assert mask(code, "javascript").count("/") == 1


def test_python_soft_keywords_and_case_wildcard_are_contextual():
    code = "match secret:\n    case [_, bound] if guard:\n        pass\n_ = 1\ntype = 2\n"
    result = mask(code, "python")
    ast.parse(result)
    assert "case [_," in result
    assert "\n_ =" not in result and "\ntype =" not in result
    tokens = CodeParser.tokenize("type Private[T] = list[T]\n", "python")
    assert tokens[0] == ("type", TokenType.GRAMMAR, "keyword")


@pytest.mark.parametrize("language,code", [
    ("javascript", 'const x = `hello {world`;'),
    ("typescript", 'const x = `hello {world`;'),
    ("go", 'package main\nvar x = `secret\\`'),
    ("sql", "SELECT 'secret\\' AS value;"),
    ("javascript", 'const x = `hello ${`${secret}`} world {`;'),
])
def test_language_specific_string_boundaries(language, code):
    result = mask(code, language)
    assert "secret" not in result and "world" not in result


def test_rust_multiple_lifetimes_remain_structural():
    code = "fn borrow<'a, 'b>(x: &'a str, y: &'b str) {}"
    tokens = CodeParser.tokenize(code, "rust")
    assert not any(kind in {"string", "character"} for _, _, kind in tokens)
    result = mask(code, "rust")
    assert result.count("'") == 4 and result.count(",") == 2


def test_rust_nested_comments_are_one_opaque_literal():
    code = '/* outer /* inner */ "secret */ fn main() {}'
    tokens = CodeParser.tokenize(code, "rust")
    assert tokens[0] == ('/* outer /* inner */ "secret */', TokenType.LITERAL, "comment")
    assert "secret" not in mask(code, "rust")


def test_python_fstring_expression_comments_ignore_quotes_and_braces():
    code = 'x = f"{1 # don\'t disclose }\n}"'
    assert "disclose" not in mask(code, "python")


@pytest.mark.parametrize("language,code", [
    ("rust", "let secret = 'x'; let byte = b'\\n';"),
    ("java", "char secret = 'x';"),
    ("c", "char secret = 'x';"),
    ("cpp", "auto secret = L'x';"),
    ("go", "var secret = '\\n'"),
])
def test_character_literals_have_a_distinct_kind(language, code):
    tokens = CodeParser.tokenize(code, language)
    chars = [raw for raw, _, kind in tokens if kind == "character"]
    assert chars
    for raw in chars:
        prefix, suffix = literal_parts(raw, "character")
        assert prefix.endswith("'") and suffix == "'"


@pytest.mark.parametrize("language,code", [
    ("javascript", "const p = /unterminated"),
    ("rust", "/* outer /* inner */"),
    ("go", "var x = `unterminated"),
])
def test_unterminated_language_literals_fail_closed(language, code):
    with pytest.raises(ValueError, match="Unterminated"):
        CodeParser.tokenize(code, language)
