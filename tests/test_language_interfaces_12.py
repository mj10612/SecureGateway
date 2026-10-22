"""End-to-end natural-language boundaries and exact restoration contracts."""
import json
import unicodedata
import uuid

import pytest
from click.testing import CliRunner

from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.engine.natural_languages import classify_token, tokenize
from secure_gateway.models import MaskMode, SurrogateStrategy, TokenType
from secure_gateway.session import PrivacySession

# Synthetic names and simple reviewed closed-class words, not NER accuracy data.
CASES = {
    "es": ("Álamo", "para"), "fr": ("Élodie", "avec"),
    "pt": ("Açucena", "para"), "de": ("Weißdorn", "mit"),
    "id": ("Melati", "untuk"), "tr": ("İstanbul", "için"),
    "ru": ("Липа", "для"), "hi": ("नीलम", "के"),
    "mr": ("नीलम", "साठी"), "bn": ("নীলম", "জন্য"),
    "te": ("నీలం", "కోసం"), "ar": ("نَوْر", "في"),
    "ur": ("نیلم", "کے"), "zh": ("北京", "的"), "ja": ("東京", "の"),
}
TEXT_MODES = [MaskMode.CONTENT_WORDS, MaskMode.ENTITIES_ONLY, MaskMode.AGGRESSIVE]


def _mask(text, language, strategy=SurrogateStrategy.BRACKET, mode=MaskMode.CONTENT_WORDS, **options):
    session = PrivacySession("natural-acceptance", strategy=strategy)
    engine = MaskingEngine()
    result = engine.mask_text(text, session.session_id, session.generator,
                              session.forward_store, session.reverse_store,
                              mode=mode, language=language, **options)
    restored = engine.unmask(result.masked_text, session.session_id,
                             session.reverse_store, strategy, strict=True)
    assert restored.unmasked_text == text
    return result, session


@pytest.mark.parametrize("language", CASES)
@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("mode", TEXT_MODES)
def test_all_languages_strategies_modes_have_exact_roundtrip_and_repeated_names(language, strategy, mode):
    name, grammar = CASES[language]
    text = f"{name} {grammar} {name} — test@example.com\n"
    result, session = _mask(text, language, strategy, mode)
    assert result.detected_language == language
    assert name not in result.masked_text
    assert grammar in result.masked_text
    mappings = [m for m in session.forward_store.values() if m.original == name]
    assert len(mappings) == 1
    assert result.masked_text.count(mappings[0].surrogate) == 2
    assert "test@example.com" not in result.masked_text
    # No orthographic mark may leak as an unmapped remnant of a masked name.
    assert not any(unicodedata.category(c)[0] == "M"
                   for c in result.masked_text.replace(grammar, ""))


@pytest.mark.parametrize("language", CASES)
def test_sensitive_terms_override_grammar_and_custom_preserve(language):
    name, grammar = CASES[language]
    text = f"{grammar} Privata {name}"
    result, session = _mask(text, language, custom_preserve={grammar, "Privata"},
                            sensitive_terms={grammar})
    assert "Privata" in result.masked_text
    assert any(m.original == grammar for m in session.forward_store.values())
    assert not any(m.original == "Privata" for m in session.forward_store.values())
    assert name not in result.masked_text


@pytest.mark.parametrize("tag,base", [
    ("zh-Hans", "zh"), ("zh-Hant", "zh"), ("pt-BR", "pt"),
    ("pt-PT", "pt"), ("de-DE", "de"), ("de-AT", "de"), ("de-CH", "de"),
])
def test_library_locale_tags_and_exact_spelling(tag, base):
    name, grammar = CASES[base]
    result, _ = _mask(f"{name} {grammar} cafe\u0301", tag)
    assert result.detected_language == base


@pytest.mark.parametrize("word", ["İÇİN", "için", "I\u0307ÇI\u0307N", "MI", "mı"])
def test_turkish_locale_grammar_key(word):
    assert classify_token(word, "tr") == (TokenType.GRAMMAR, False)
    result, _ = _mask(f"İstanbul {word} İzmir", "tr")
    assert word in result.masked_text


@pytest.mark.parametrize("language,text", [
    ("zh", "北京公司的客户发送秘密文件"),
    ("ja", "東京の会社に顧客情報を送信します"),
])
def test_cjk_masks_multiple_content_words_and_keeps_grammar(language, text):
    result, session = _mask(text, language)
    assert len(session.forward_store) >= 3
    assert any(len(m.original) > 1 for m in session.forward_store.values())
    assert len(tokenize(text, language)) > 3
    assert ("的" if language == "zh" else "の") in result.masked_text


@pytest.mark.parametrize("language", CASES)
def test_cli_language_propagates_and_restores_in_same_local_session(language):
    from secure_gateway.cli import main, vault
    name, grammar = CASES[language]
    sid = "natural-cli-" + uuid.uuid4().hex
    text = f"{name} {grammar} {name}"
    runner = CliRunner()
    try:
        response = runner.invoke(main, ["mask", text, "--language", language,
                                       "--session-id", sid, "--json-output"])
        assert response.exit_code == 0, response.output
        masked = json.loads(response.output)
        assert masked["detected_language"] == language
        assert name not in masked["masked_text"]
        restored = runner.invoke(main, ["unmask", masked["masked_text"],
                                       "--session-id", sid, "--strict", "--json-output"])
        assert restored.exit_code == 0, restored.output
        assert json.loads(restored.output)["unmasked_text"] == text
    finally:
        vault.clear_session(sid)


@pytest.mark.parametrize("language", CASES)
def test_mcp_local_call_propagates_language_and_strict_restore(language):
    from secure_gateway import server
    name, grammar = CASES[language]
    sid = "natural-mcp-" + uuid.uuid4().hex
    text = f"{name} {grammar} {name}"
    try:
        masked = json.loads(server.mask_text(text, session_id=sid, language=language))
        assert masked["detected_language"] == language
        assert name not in masked["masked_text"]
        restored = json.loads(server.unmask_text(masked["masked_text"], session_id=sid, strict=True))
        assert restored["unmasked_text"] == text
    finally:
        server.vault.clear_session(sid)


@pytest.mark.parametrize("language", CASES)
def test_gateway_prose_language_selection_and_exact_restore(language):
    from secure_gateway.gateway import GatewaySession
    name, grammar = CASES[language]
    gateway = GatewaySession(natural_language=language)
    text = f"{name} {grammar} {name}."
    masked = gateway.mask(text)
    assert name not in masked
    assert grammar in masked
    assert gateway.restore(masked) == text


def test_unsupported_language_fails_across_interfaces():
    from secure_gateway import server
    from secure_gateway.cli import main
    from secure_gateway.gateway import GatewaySession
    with pytest.raises(ValueError, match="Unsupported natural language"):
        _mask("private", "xx")
    response = CliRunner().invoke(main, ["mask", "private", "--language", "xx"])
    assert response.exit_code != 0
    assert "Unsupported natural language" in response.output
    with pytest.raises(Exception, match="Unsupported natural language"):
        server.mask_text("private", language="xx")
    with pytest.raises(ValueError, match="Unsupported natural language"):
        GatewaySession(natural_language="xx")
