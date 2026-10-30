"""Ruby constant syntax and bindings survive allocation and snapshot reload."""

import os
import re

import pytest

from secure_gateway.encrypted_session import load_session, save_session
from secure_gateway.engine.code_identifiers import valid_identifier_alias
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.engine.strategies import StrategyGenerator
from secure_gateway.gateway import SharedEngine
from secure_gateway.models import SurrogateStrategy, TokenMapping, TokenType
from secure_gateway.session import PrivacySession


SOURCE = """module PrivateModule
  PrivateValue = 7
  class PrivateClass
    def private_method
      private_local = PrivateModule::PrivateValue
      private_local
    end
  end
end
private_instance = PrivateModule::PrivateClass.new
"""


def mask(engine, session, source, language="ruby"):
    return engine.mask_code(source, session.session_id, session.generator,
                            session.forward_store, session.reverse_store,
                            language=language).masked_text


def restore(engine, session, text):
    return engine.unmask(text, session.session_id, session.reverse_store,
                         session.strategy, strict=True).unmasked_text


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("engine_type", [MaskingEngine, SharedEngine])
def test_ruby_constants_bind_and_snapshot_continues(strategy, engine_type, tmp_path):
    engine = engine_type()
    session = PrivacySession("ruby-constants", strategy=strategy)
    masked = mask(engine, session, SOURCE)
    assert restore(engine, session, masked) == SOURCE
    for item in session.reverse_store.values():
        if item.token_type != TokenType.IDENTIFIER:
            continue
        assert item.surrogate[0].isupper() == item.original[0].isupper()
        assert valid_identifier_alias(item)
        assert masked.count(item.surrogate) == SOURCE.count(item.original)
    assert re.search(r"module [A-Z]\w*", masked)
    assert re.search(r"class [A-Z]\w*", masked)
    path = tmp_path / "ruby.enc"
    save_session(path, session, "synthetic-ruby-password")
    loaded = load_session(path, "synthetic-ruby-password", session.session_id)
    assert restore(engine, loaded, masked) == SOURCE
    assert mask(engine, loaded, SOURCE) == masked
    before = set(loaded.reverse_store)
    source = "class AnotherPrivateClass\nend\n"
    following = mask(engine, loaded, source)
    assert restore(engine, loaded, following) == source
    assert set(loaded.reverse_store) - before
    assert not any(alias in following for alias in before)


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("engine_type", [MaskingEngine, SharedEngine])
def test_existing_other_language_mapping_is_not_rewritten(strategy, engine_type):
    engine = engine_type()
    session = PrivacySession("ruby-cross-language", strategy=strategy)
    python_source = "PrivateClass = 7"
    first = mask(engine, session, python_source, "python")
    ruby_source = "class PrivateClass\nend\n"
    second = mask(engine, session, ruby_source)
    assert restore(engine, session, first) == python_source
    assert restore(engine, session, second) == ruby_source
    assert re.search(r"class [A-Z]\w*", second)
    assert mask(engine, session, ruby_source) == second


@pytest.mark.parametrize("engine_type,original", [(MaskingEngine, "Smcp_ID_1"),
                                                   (SharedEngine, "Private_symbol_1")])
def test_ruby_constant_cannot_allocate_its_own_literal_spelling(engine_type, original, tmp_path):
    engine = engine_type()
    session = PrivacySession("ruby-alias-collision")
    source = f"class {original}\nend\n"
    masked = mask(engine, session, source)
    assert original not in masked
    assert restore(engine, session, masked) == source
    path = tmp_path / "collision.enc"
    save_session(path, session, "synthetic-collision-password")
    loaded = load_session(path, "synthetic-collision-password", session.session_id)
    assert restore(engine, loaded, masked) == source
    assert mask(engine, loaded, source) == masked


@pytest.mark.parametrize("prefix", ["Smcp_ID", "Private_symbol"])
def test_constant_prefix_restores_counter_and_candidate_detection(prefix):
    generator = StrategyGenerator(SurrogateStrategy.BRACKET)
    alias = f"{prefix}_29"
    generator.restore_state([alias])
    assert generator._code_index == 29
    assert generator.get_pattern(generator.strategy).fullmatch(alias)
    assert generator.generate(TokenType.IDENTIFIER, "another", code=True).endswith("_30")


@pytest.mark.parametrize("language,original", [("python", "PrivateClass"), ("ruby", "private_local")])
def test_uppercase_snapshot_prefix_is_restricted_to_ruby_constants(language, original):
    mapping = TokenMapping(original=original, surrogate="Smcp_ID_1",
                           token_type=TokenType.IDENTIFIER, context="code",
                           identifier_base="Smcp_ID_1", identifier_language=language,
                           identifier_key=original)
    assert not valid_identifier_alias(mapping)


@pytest.mark.skipif(os.environ.get("SECURE_GATEWAY_NATIVE_PARSERS") != "1",
                    reason="Enable the explicit independent grammar gate")
@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_ruby_independent_grammar_accepts_constant_aliases(strategy):
    import tree_sitter_language_pack

    parser = tree_sitter_language_pack.get_parser("ruby")
    session = PrivacySession("ruby-grammar", strategy=strategy)
    masked = mask(MaskingEngine(), session, SOURCE)
    assert not parser.parse(SOURCE.encode()).root_node.has_error
    assert not parser.parse(masked.encode()).root_node.has_error
