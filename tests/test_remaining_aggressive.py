"""Aggressive mode must differ from content_words for new lexical adapters."""
import pytest

from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import MaskMode, SurrogateStrategy, TokenType
from secure_gateway.session import PrivacySession


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("language,word,connective", [
    ("es", "la", "y"), ("fr", "le", "et"), ("pt", "o", "e"),
    ("de", "die", "und"), ("id", "adalah", "dan"), ("tr", "gibi", "ve"),
    ("ru", "в", "и"), ("hi", "है", "और"), ("mr", "आहे", "आणि"),
    ("bn", "হয়", "এবং"), ("ur", "ہے", "اور"), ("ar", "في", "أو"),
    ("te", "ఉంది", "మరియు"), ("zh", "的", "和"), ("ja", "の", "と"),
])
def test_aggressive_masks_broader_grammar_but_keeps_connectives(strategy, language, word, connective):
    source = word + " " + connective
    engine = MaskingEngine()
    ordinary = PrivacySession("ordinary", strategy=strategy)
    content = engine.mask_text(source, ordinary.session_id, ordinary.generator,
                               ordinary.forward_store, ordinary.reverse_store, language=language)
    assert content.masked_text == source
    stronger = PrivacySession("stronger", strategy=strategy)
    aggressive = engine.mask_text(source, stronger.session_id, stronger.generator,
                                  stronger.forward_store, stronger.reverse_store,
                                  language=language, mode=MaskMode.AGGRESSIVE)
    assert aggressive.masked_text != source
    assert aggressive.masked_text.endswith(" " + connective)
    assert len(stronger.forward_store) == 1
    assert next(iter(stronger.forward_store.values())).original == word
    assert engine.unmask(aggressive.masked_text, stronger.session_id, stronger.reverse_store,
                         strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_aggressive_preserve_and_sensitive_overrides(strategy):
    engine = MaskingEngine()
    session = PrivacySession("overrides", strategy=strategy)
    result = engine.mask_text("adalah dan", session.session_id, session.generator,
                              session.forward_store, session.reverse_store,
                              language="id", mode=MaskMode.AGGRESSIVE,
                              custom_preserve={"adalah", "dan"}, sensitive_terms={"dan"})
    assert result.masked_text.startswith("adalah ")
    mapping = next(iter(session.forward_store.values()))
    assert mapping.original == "dan" and mapping.token_type == TokenType.ENTITY
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == "adalah dan"
