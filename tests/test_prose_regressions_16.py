import pytest
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import MaskMode, SurrogateStrategy
from secure_gateway.session import PrivacySession

@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("mode", [MaskMode.CONTENT_WORDS, MaskMode.ENTITIES_ONLY, MaskMode.AGGRESSIVE])
@pytest.mark.parametrize("text", ["a\u0301", "the\u0301", "a\u0301bc"])
def test_combining_word_is_masked(strategy, mode, text):
    engine = MaskingEngine()
    session = PrivacySession("test", strategy=strategy)
    r = engine.mask_text(text, session.session_id, session.generator, session.forward_store, session.reverse_store, mode=mode)
    assert r.masked_text != text
    assert engine.unmask(r.masked_text, session.session_id, session.reverse_store, strategy, strict=True).unmasked_text == text

@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("known", [False, True])
def test_adjacent_literal_alias_is_opaque(strategy, known):
    engine = MaskingEngine()
    session = PrivacySession("test", strategy=strategy)
    r = engine.mask_text("private", session.session_id, session.generator, session.forward_store, session.reverse_store)
    alias = r.masked_text
    if not known:
        session = PrivacySession("fresh", strategy=strategy)
    source = "x" + alias + "y"
    r = engine.mask_text(source, session.session_id, session.generator, session.forward_store, session.reverse_store, custom_preserve={alias[1:-1]})
    assert engine.unmask(r.masked_text, session.session_id, session.reverse_store, strategy, strict=True).unmasked_text == source


def test_failed_identifiers_do_not_publish_empty_groups():
    engine = MaskingEngine()
    session = PrivacySession("test", mapping_limit=1)
    engine.mask_code("private0=1", session.session_id, session.generator, session.forward_store, session.reverse_store)
    for i in range(1, 1001):
        with pytest.raises(ValueError, match="Mapping limit"):
            engine.mask_code(f"private{i}=1", session.session_id, session.generator, session.forward_store, session.reverse_store)
    assert len(session.generator._identifier_groups) == 1
    assert all(session.generator._identifier_groups.values())

@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("template", ["`private {} hidden`", "https://private.example/{}/hidden", "secret{}hidden@example.com"])
def test_alias_in_opaque_span_never_exposes_fragments(strategy, template):
    engine = MaskingEngine()
    session = PrivacySession("opaque", strategy=strategy)
    alias = engine.mask_text("private", session.session_id, session.generator, session.forward_store, session.reverse_store).masked_text
    source = template.format(alias)
    result = engine.mask_text(source, session.session_id, session.generator, session.forward_store, session.reverse_store, mode=MaskMode.ENTITIES_ONLY)
    assert "private" not in result.masked_text and "hidden" not in result.masked_text
    if not source.startswith("secret"):
        assert "secret" not in result.masked_text
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store, strategy, strict=True).unmasked_text == source

@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_explicit_sensitive_phrase_containing_alias_stays_whole(strategy):
    e = MaskingEngine()
    s = PrivacySession("phrase", strategy=strategy)
    alias = e.mask_text("private", s.session_id, s.generator, s.forward_store, s.reverse_store).masked_text
    source = f"sensitive {alias} phrase"
    r = e.mask_text(source, s.session_id, s.generator, s.forward_store, s.reverse_store, mode=MaskMode.ENTITIES_ONLY, sensitive_terms={source})
    assert "sensitive" not in r.masked_text and "phrase" not in r.masked_text
    assert e.unmask(r.masked_text, s.session_id, s.reverse_store, strategy, strict=True).unmasked_text == source

@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("mode", [MaskMode.CONTENT_WORDS, MaskMode.ENTITIES_ONLY, MaskMode.AGGRESSIVE])
def test_nfc_nfd_pairs_and_ascii_grammar_controls(strategy, mode):
    e = MaskingEngine()
    for text, expected in [("a", 0), ("the", 0), ("\u00e1", 1), ("a\u0301", 1), ("th\u00e9", 1), ("the\u0301", 1)]:
        s = PrivacySession("forms", strategy=strategy)
        r = e.mask_text(text, s.session_id, s.generator, s.forward_store, s.reverse_store, mode=mode)
        assert r.masked_tokens == expected
        assert e.unmask(r.masked_text, s.session_id, s.reverse_store, strategy, strict=True).unmasked_text == text
