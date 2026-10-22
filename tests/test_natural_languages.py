"""Offline lexical adapter acceptance fixtures; no remote translation calls."""
import unicodedata

import pytest

from secure_gateway.engine.natural_languages import (
    SUPPORTED_LANGUAGES,
    canonical_language,
    classify_token,
    detect_natural_language,
    structural_words,
    tokenize,
)
from secure_gateway.models import TokenType

SAMPLES = {
    "es": ("La empresa Álamo envía datos a Córdoba.", "la", "Álamo"),
    "fr": ("L’entreprise d’Élodie envoie un fichier à Lyon\u202f!", "à", "Élodie"),
    "pt": ("A empresa Açucena envia dados para Évora.", "para", "Açucena"),
    "de": ("Die Firma Weißdorn sendet Daten für München.", "für", "Weißdorn"),
    "id": ("Perusahaan Melati mengirim data untuk Bandung.", "untuk", "Melati"),
    "tr": ("Şirket İstanbul için özel dosyayı gönderdi.", "için", "İstanbul"),
    "ru": ("Компания Липа отправляет данные для Казани.", "для", "Липа"),
    "hi": ("कंपनी नीलम के लिए गोपनीय फ़ाइल भेजती है।", "के", "नीलम"),
    "mr": ("कंपनी नीलम साठी गुप्त माहिती पाठवते आहे.", "साठी", "नीलम"),
    "bn": ("নীলম কোম্পানি এর জন্য গোপন তথ্য পাঠায়।", "জন্য", "নীলম"),
    "te": ("నీలం కంపెనీ కోసం రహస్య సమాచారం ఉంది.", "కోసం", "నీలం"),
    "ar": ("شركة نَوْر في القاهرة ترسل مِلفّاً سرياً.", "في", "نَوْر"),
    "ur": ("نیلم کمپنی کے لیے خفیہ معلومات بھیجتی ہے۔", "کے", "نیلم"),
    "zh": ("北京公司的客户发送秘密文件。", "的", "北京"),
    "ja": ("東京の会社に顧客情報を送信します。", "の", "東京"),
}


@pytest.mark.parametrize("language", SAMPLES)
def test_all_languages_have_lossless_chunks_and_reviewed_grammar(language):
    text, grammar, content = SAMPLES[language]
    chunks = tokenize(text, language)
    assert "".join(chunk.text for chunk in chunks) == text
    assert classify_token(grammar, language) == (TokenType.GRAMMAR, False)
    assert classify_token(content, language) == (TokenType.NOUN, True)
    assert structural_words(language)
    assert any(chunk.is_word for chunk in chunks)
    # Marks, vowel signs and joiners must not be detached into punctuation.
    assert not any(chunk.kind == "OTHER" and
                   any(unicodedata.category(c)[0] == "M" for c in chunk.text)
                   for chunk in chunks)


@pytest.mark.parametrize("tag, expected", [
    ("zh-Hans", "zh"), ("zh-Hant-TW", "zh"), ("pt-BR", "pt"),
    ("pt_PT", "pt"), ("de-DE", "de"), ("de-AT", "de"), ("de-CH", "de"),
    ("es-MX", "es"), ("fr-CA", "fr"), ("ar", "ar"), ("auto", "auto"),
])
def test_locale_aliases(tag, expected):
    assert canonical_language(tag) == expected


@pytest.mark.parametrize("tag", [None, "", "xx", "auto-US", "fr--CA", "fr/CA", "é"])
def test_invalid_language_rejected(tag):
    with pytest.raises(ValueError):
        canonical_language(tag)


@pytest.mark.parametrize("language", SAMPLES)
def test_existing_sensitive_span_precedence_and_mixed_code(language):
    text = SAMPLES[language][0] + " test@example.com https://example.com/a `secret = 1`\n"
    chunks = tokenize(text, language)
    assert "".join(chunk.text for chunk in chunks) == text
    assert [(c.text, c.kind) for c in chunks if c.kind in {"EMAIL", "URL", "CODE_BLOCK"}] == [
        ("test@example.com", "EMAIL"), ("https://example.com/a", "URL"),
        ("`secret = 1`", "CODE_BLOCK"),
    ]


@pytest.mark.parametrize("text,language", [
    ("cafe\u0301", "fr"), ("नमस्\u200dते", "hi"),
    ("مِلفّ", "ar"), ("نی\u200cلم", "ur"), ("ক্ষ্ম", "bn"),
    ("తెలుగు", "te"), ("Straße", "de"), ("İstanbul", "tr"),
])
def test_unicode_word_is_one_raw_span(text, language):
    chunks = tokenize(text, language)
    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].kind == "WORD"


def test_french_elision_keeps_apostrophe_and_content_separate():
    chunks = tokenize("l’entreprise d'Élodie", "fr")
    assert [c.text for c in chunks] == ["l’", "entreprise", " ", "d'", "Élodie"]
    assert classify_token(chunks[0].text, "fr") == (TokenType.GRAMMAR, False)
    assert classify_token(chunks[1].text, "fr") == (TokenType.NOUN, True)


@pytest.mark.parametrize("language,text", [
    ("zh", "北京公司的客户发送秘密文件"),
    ("zh-Hant", "臺北公司的客戶發送秘密文件"),
    ("ja", "東京の会社に顧客情報を送信します"),
])
def test_cjk_models_segment_words_without_normalizing(language, text):
    chunks = tokenize(text, language)
    assert "".join(c.text for c in chunks) == text
    assert len(chunks) > 3
    assert any(len(c.text) > 1 for c in chunks)


def test_auto_detection_avoids_guessing_latin_and_prefers_kana_over_han():
    assert detect_natural_language("la entreprise hello") == "en"
    assert detect_natural_language("東京の会社") == "ja"
    assert detect_natural_language("北京公司") == "zh"
    assert tokenize("北京公司", "auto")
    assert len(SUPPORTED_LANGUAGES) == 18


def test_grammar_lookup_normalizes_without_changing_raw_text():
    word = unicodedata.normalize("NFD", "à")
    assert classify_token(word, "fr") == (TokenType.GRAMMAR, False)
    assert tokenize(word, "fr")[0].text == word
    # English grammar must not be used accidentally for explicit adapters.
    assert classify_token("the", "es") == (TokenType.NOUN, True)
