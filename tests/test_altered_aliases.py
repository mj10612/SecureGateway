"""Restore issued alias derivatives without guessing unknown bindings."""

import pytest

from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.gateway import GatewaySession
from secure_gateway.models import TokenMapping, TokenType


@pytest.mark.parametrize("base", ["private_symbol_1", "smcp_ID_1", "smcp_LIT_1", "smcp_NUM_1"])
@pytest.mark.parametrize("template", ["{}_backup", "{}s", "prefix_{}", "a{}b"])
def test_strict_restores_issued_alias_in_derived_identifier(base, template):
    engine = MaskingEngine()
    mappings = {base: TokenMapping(original="private-value", surrogate=base,
                                  token_type=TokenType.IDENTIFIER)}
    derived = template.format(base)
    result = engine.unmask(derived, "fixture", mappings, strict=True)
    assert result.unmasked_text == template.format("private-value")
    assert result.unmatched_surrogates == []
    assert result.restored_tokens_count == 1


@pytest.mark.parametrize("source", ["test_private_symbol_99", "private_symbol_10_v2", "aSMCP_ID_99b", "1private_symbol_1"])
def test_strict_derivative_restoration_still_rejects_unknown_or_numeric_affixes(source):
    mapping = TokenMapping(original="private-value", surrogate="private_symbol_1",
                           token_type=TokenType.IDENTIFIER)
    with pytest.raises(ValueError, match="surrogate tokens"):
        MaskingEngine().unmask(source, "fixture", {mapping.surrogate: mapping}, strict=True)


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


def test_registered_nonstandard_identifier_wins_over_its_embedded_issued_alias():
    mappings = {alias: TokenMapping(original=original, surrogate=alias,
                                    token_type=TokenType.IDENTIFIER)
                for alias, original in [("private_symbol_1", "inner"),
                                        ("private_symbol_1_backup", "complete_original")]}
    assert MaskingEngine().unmask("private_symbol_1_backup", "fixture", mappings,
                                  strict=True).unmasked_text == "complete_original"


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
    assert MaskingEngine().unmask("test_private_symbol_10_v2", "fixture", mappings,
                                  strict=True).unmasked_text == "test_tenth_v2"
    # The received spelling cannot distinguish an issued alias 10 from a model
    # appending digit 0 to alias 1. Honor only the exact full issued binding.


def test_adjacent_and_wrapped_aliases_keep_existing_single_pass_semantics():
    mappings = {alias: TokenMapping(original=original, surrogate=alias,
                                    token_type=TokenType.IDENTIFIER)
                for alias, original in [("private_symbol_1", "private_symbol_7_backup"), ("private_symbol_2", "second")]}
    engine = MaskingEngine()
    result = engine.unmask("private_symbol_1private_symbol_2 ⟦private_symbol_1⟧", "fixture", mappings, strict=True)
    assert result.unmasked_text == "private_symbol_7_backupsecond private_symbol_7_backup"
