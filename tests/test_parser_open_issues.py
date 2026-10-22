"""Regression coverage for the remaining source lexer issues."""

import pytest

from secure_gateway.engine.code_parser import CodeParser
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import MaskMode, SurrogateStrategy, TokenType
from secure_gateway.session import PrivacySession


@pytest.mark.parametrize("language,prefix", [("python", "#"), ("javascript", "//"), ("typescript", "//"), ("c", "//"), ("cpp", "//"), ("sql", "--")])
@pytest.mark.parametrize("newline", ["\n", "\r", "\r\n"])
def test_line_comments_stop_at_physical_line_end(language, prefix, newline):
    source = prefix + ' private "' + newline + "privateName"
    tokens = CodeParser.tokenize(source, language)
    assert tokens[0][0] == prefix + ' private "'
    assert tokens[-1] == ("privateName", TokenType.IDENTIFIER, "identifier")
    assert "".join(token[0] for token in tokens) == source


@pytest.mark.parametrize("language", ["c", "cpp"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_c_spliced_line_comment_includes_next_physical_line(language, newline):
    source = '// private\\' + newline + 'still "comment' + newline + "int privateName;"
    tokens = CodeParser.tokenize(source, language)
    assert tokens[0][0] == '// private\\' + newline + 'still "comment'
    assert any(raw == "privateName" and kind == "identifier" for raw, _, kind in tokens)
    assert "".join(token[0] for token in tokens) == source


@pytest.mark.parametrize("source", [
    "const ratio = function() {} / 2;",
    "const ratio = function privateName() {} / 2;",
    "const ratio = class {} / 2;",
    "const ratio = class privateName {} / 2;",
    "const ratio = (() => {}) / 2;",
    "const ratio = {} / 2;",
])
@pytest.mark.parametrize("language", ["javascript", "typescript"])
def test_javascript_expression_bodies_allow_division(source, language):
    tokens = CodeParser.tokenize(source, language)
    assert ("/", TokenType.GRAMMAR, "syntax") in tokens


@pytest.mark.parametrize("source", ["function privateName() {} /private/.test('value');", "class PrivateName {} /private/.test('value');", "if (privateName) {} /private/.test('value');"])
def test_javascript_declaration_blocks_still_allow_regex(source):
    assert any(kind == "regex" for _, _, kind in CodeParser.tokenize(source, "javascript"))


@pytest.mark.parametrize("word,source", [
    ("static", "class Private { static privateMethod() {} }"),
    ("get", "const privateName = { get privateValue() {} };"),
    ("set", "const privateName = { set privateValue(input) {} };"),
    ("of", "for (const privateItem of privateItems) {}"),
    ("from", 'import privateName from "private-module";'),
    ("as", 'import { privateName as renamedName } from "private-module";'),
    ("as", "const privateName = 1; export { privateName as renamedName };"),
    ("async", "async function privateName() {}"),
    ("async", "const privateName = async (input) => input;"),
])
@pytest.mark.parametrize("language", ["javascript", "typescript"])
def test_javascript_context_words_preserve_only_structure(word, source, language):
    tokens = CodeParser.tokenize(source, language)
    assert (word, TokenType.GRAMMAR, "keyword") in tokens
    control = CodeParser.tokenize(f"const {word} = 1; privateName.{word};", language)
    assert all(kind == "identifier" for raw, _, kind in control if raw == word)


@pytest.mark.parametrize("quote,end", [('"', '"'), ("`", "`"), ("[", "]")])
def test_sql_quoted_names_are_identifiers(quote, end):
    source = f"SELECT {quote}privateName{end} FROM privateTable WHERE privateName = 'privateValue';"
    tokens = CodeParser.tokenize(source, "sql")
    assert (f"{quote}privateName{end}", TokenType.IDENTIFIER, "quoted_identifier") in tokens
    assert ("'privateValue'", TokenType.LITERAL, "string") in tokens


@pytest.mark.parametrize("source", ['"private""Name"', '`private``Name`', '[private]]Name]'])
def test_sql_quoted_identifier_escapes_stay_inside_one_token(source):
    assert CodeParser.tokenize(source, "sql") == [(source, TokenType.IDENTIFIER, "quoted_identifier")]


def test_typescript_as_type_assertion_is_preserved():
    tokens = CodeParser.tokenize("const privateName = privateInput as PrivateType;", "typescript")
    assert ("as", TokenType.GRAMMAR, "keyword") in tokens


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("existing", [False, True])
def test_literal_code_alias_in_prose_roundtrips_even_when_previously_allocated(strategy, existing):
    session = PrivacySession("literal-alias", strategy=strategy)
    engine = MaskingEngine()
    args = (session.session_id, session.generator, session.forward_store, session.reverse_store)
    if existing:
        alias = engine.mask_code("privateName", *args, language="python").masked_text
    else:
        alias = "smcp_ID_1"
    result = engine.mask_text(alias, *args, mode=MaskMode.ENTITIES_ONLY)
    assert result.masked_text != alias
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store, strategy, strict=True).unmasked_text == alias
    with pytest.raises(ValueError, match="Unrecognized"):
        engine.unmask("smcp_ID_999999", session.session_id, session.reverse_store, strategy, strict=True)


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_literal_text_alias_in_prose_is_not_double_restored(strategy):
    session = PrivacySession("literal-text-alias", strategy=strategy)
    engine = MaskingEngine()
    args = (session.session_id, session.generator, session.forward_store, session.reverse_store)
    alias = engine.mask_text("PrivateCustomer", *args, mode=MaskMode.ENTITIES_ONLY, sensitive_terms={"PrivateCustomer"}).masked_text
    result = engine.mask_text(alias, *args, mode=MaskMode.ENTITIES_ONLY)
    assert result.masked_text != alias
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store, strategy, strict=True).unmasked_text == alias


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("quote,end", [('"', '"'), ("`", "`"), ("[", "]")])
def test_sql_quoted_and_unquoted_names_share_mapping(strategy, quote, end):
    import sqlite3
    from contextlib import closing

    session = PrivacySession("sql-quoted", strategy=strategy)
    engine = MaskingEngine()
    source = f"CREATE TABLE {quote}privateTable{end} ({quote}privateColumn{end} INTEGER); INSERT INTO privateTable (privateColumn) VALUES (1); SELECT privateColumn FROM privateTable;"
    result = engine.mask_code(source, session.session_id, session.generator, session.forward_store, session.reverse_store, language="sql")
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.executescript(result.masked_text)
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store, strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize("source", ['SELECT "private""Name";', 'SELECT `private``Name`;', 'SELECT [private]]Name];'])
def test_sql_escaped_quoted_identifier_roundtrip(source):
    session = PrivacySession("sql-escaped")
    engine = MaskingEngine()
    result = engine.mask_code(source, session.session_id, session.generator, session.forward_store, session.reverse_store, language="sql")
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store, strict=True).unmasked_text == source
