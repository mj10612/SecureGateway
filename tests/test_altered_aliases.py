"""Reject mutated reserved aliases without reinterpreting restored originals."""

import pytest

from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.gateway import GatewaySession
from secure_gateway.models import TokenMapping, TokenType


@pytest.mark.parametrize("base", ["private_symbol_1", "smcp_ID_1", "smcp_LIT_1", "smcp_NUM_1"])
@pytest.mark.parametrize("template", ["{}_backup", "{}s", "prefix_{}", "a{}b"])
def test_strict_rejects_mutated_alias_in_original_input(base, template):
    engine = MaskingEngine()
    mappings = {base: TokenMapping(original="private-value", surrogate=base,
                                  token_type=TokenType.IDENTIFIER)}
    altered = template.format(base)
    result = engine.unmask(altered, "fixture", mappings)
    assert result.unmasked_text == altered
    assert result.unmatched_surrogates == [altered]
    with pytest.raises(ValueError, match="altered"):
        engine.unmask(altered, "fixture", mappings, strict=True)


@pytest.mark.parametrize("source", ["prefix_private_symbol_1", "private_symbol_1_backup", "private_symbol_1s", "smcp_ID_1_backup"])
def test_legitimate_original_reserved_identifier_roundtrips_once(source):
    session = GatewaySession()
    masked = session.mask(source, code=True)
    assert masked != source
    assert session.restore(masked) == source


def test_registered_identifier_spelling_containing_reserved_syntax_is_allowed():
    alias = "r#smcp_ID_1"
    mapping = TokenMapping(original="r#privateName", surrogate=alias,
                           token_type=TokenType.IDENTIFIER, context="code",
                           identifier_base="smcp_ID_1", identifier_language="rust",
                           identifier_key="privateName")
    engine = MaskingEngine()
    assert engine.unmask(alias, "fixture", {alias: mapping}, strict=True).unmasked_text == "r#privateName"


def test_does_not_guess_shorter_alias_for_unknown_numeric_suffix():
    mapping = TokenMapping(original="private-value", surrogate="private_symbol_1",
                           token_type=TokenType.IDENTIFIER)
    with pytest.raises(ValueError, match="private_symbol_10"):
        MaskingEngine().unmask("private_symbol_10", "fixture", {mapping.surrogate: mapping}, strict=True)


def test_exact_longer_alias_is_restored_without_prefix_guessing():
    mappings = {alias: TokenMapping(original=original, surrogate=alias,
                                    token_type=TokenType.IDENTIFIER)
                for alias, original in [("private_symbol_1", "first"), ("private_symbol_10", "tenth")]}
    assert MaskingEngine().unmask("private_symbol_10", "fixture", mappings, strict=True).unmasked_text == "tenth"


def test_adjacent_and_wrapped_aliases_keep_existing_single_pass_semantics():
    mappings = {alias: TokenMapping(original=original, surrogate=alias,
                                    token_type=TokenType.IDENTIFIER)
                for alias, original in [("private_symbol_1", "private_symbol_7_backup"), ("private_symbol_2", "second")]}
    engine = MaskingEngine()
    result = engine.unmask("private_symbol_1private_symbol_2 ⟦private_symbol_1⟧", "fixture", mappings, strict=True)
    assert result.unmasked_text == "private_symbol_7_backupsecond private_symbol_7_backup"
