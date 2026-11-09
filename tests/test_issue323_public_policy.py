"""Issue #323 public-word policy controls (generic synthetic text, not evaluation tasks).

Policy: ordinary public words, typed predicates and widely used names are not masked
merely because they appear in a name/domain list or look unfamiliar. Actual private
registrations, forced rules, prior mappings, sensitive formats and identifier/path
contexts still mask, with exact restoration.
"""
import re
import unicodedata

import pytest

from secure_gateway.engine.grammar_ko import KOREAN_FUNCTION_WORDS
from secure_gateway.engine.natural_languages import CLOSED_CLASS_WORDS
from secure_gateway.gateway import GatewaySession, _identifier_shaped, _name_fallback

ALL_LANGUAGES = ('en', 'ko', 'es', 'fr', 'pt', 'de', 'id', 'tr', 'ru', 'hi', 'mr', 'bn', 'ur', 'te', 'ar', 'zh', 'ja')


def roundtrip(language, text, forced=()):
    session = GatewaySession(natural_language=language)
    if forced:
        session.forced_rules = lambda: tuple(forced)
    masked = session.mask(text)
    assert session.restore(masked) == text
    return masked


@pytest.mark.parametrize('language,text', [
    ('en', 'Please ask John Smith and Mary to check the bank report in London before Friday.'),
    ('de', 'Die Materialliste liegt im Raum. Berlin und Deutschland bleiben bekannt. Bitte Müller anrufen.'),
    ('fr', 'Paris est belle. Demandez à Pierre de vérifier la banque demain.'),
    ('es', 'Por favor, José revisa la casa en Madrid mañana.'),
    ('ko', '기록을 만들고 정리해주세요. 서울에서 친구를 만나면 책을 주세요.'),
    ('zh', '请在北京的银行检查清单。'),
    ('ru', 'Пожалуйста, проверьте дом в Москве завтра.'),
])
def test_ordinary_words_common_names_and_places_stay_public(language, text):
    assert roundtrip(language, text) == text


def test_static_domain_words_do_not_remask_ordinary_words():
    # 'bank', 'cancer', 'insulin', 'credit' were static DOMAIN_WORDS entries.
    text = 'The bank checks credit, and the clinic studies cancer and insulin.'
    assert roundtrip('en', text) == text


def test_capitals_and_nfc_nfd_spellings_keep_original_bytes():
    for text in ('JOHN met NASA staff in LONDON.', unicodedata.normalize('NFD', 'Le café de Hélène est près de Lyon.')):
        language = 'fr' if 'café' in unicodedata.normalize('NFC', text) else 'en'
        assert roundtrip(language, text) == text


def test_korean_predicates_inflections_and_german_compounds_stay_public():
    assert roundtrip('ko', '모르면 물어보세요. 하지 않고 기다리면 됩니다.') == '모르면 물어보세요. 하지 않고 기다리면 됩니다.'
    assert roundtrip('de', 'Die Materialliste und die Bücherliste liegen im Raum.') == \
        'Die Materialliste und die Bücherliste liegen im Raum.'


def test_unknown_ordinary_prose_is_kept_and_only_narrow_fallbacks_mask():
    # Absence from the vocabulary is not evidence of privacy.
    assert roundtrip('en', 'Flurbish the report quickly.') == 'Flurbish the report quickly.'
    assert roundtrip('ko', '쿠루룽 보고서를 확인해 주세요.') == '쿠루룽 보고서를 확인해 주세요.'
    assert roundtrip('de', 'Bitte Quarzelband prüfen.') == 'Bitte Quarzelband prüfen.'  # German nouns: no name fallback
    # Narrow name fallback: a non-public mid-sentence Title-case word in a cased script.
    masked = roundtrip('en', 'Please call Zorblax tomorrow.')
    assert 'Zorblax' not in masked and 'call' in masked and 'tomorrow' in masked
    # Identifier shapes: inner capitals and unknown acronyms.
    masked = roundtrip('en', 'Check the KeplerQzx build and the QZXLAB team.')
    assert 'KeplerQzx' not in masked and 'QZXLAB' not in masked and 'build' in masked
    assert _identifier_shaped('KeplerQzx') and _identifier_shaped('QZXLAB') and not _identifier_shaped('Report')
    masked = roundtrip('en', 'Please inspect private_method and account37591 before continuing.')
    assert 'private_method' not in masked and 'account37591' not in masked and 'inspect' in masked
    # Fallback aliases keep possessive grammar, and elision is not a sentence boundary.
    masked = roundtrip('en', "Ask Zorblax's coordinator to confirm.")
    assert 'Zorblax' not in masked and "'s coordinator" in masked
    masked = roundtrip('fr', "Nous avons intégré le module d'Zorvexa hier.")
    assert 'Zorvexa' not in masked and "module d'" in masked
    assert not _name_fallback('Zorblax starts.', 0, 'Zorblax', 'en')  # sentence start is not a name signal


@pytest.mark.parametrize('language,text,word', [
    ('de', 'Berlin und Deutschland bleiben bekannt.', 'Berlin'),
    ('en', 'Please check the bank report.', 'bank'),
    ('en', 'Ask John about the plan.', 'John'),
    ('ko', '서울에서 책을 주세요.', '서울'),
])
def test_same_public_spelling_forced_private_is_masked(language, text, word):
    masked = roundtrip(language, text, forced=(word,))
    assert word not in masked


def test_same_public_spelling_as_registered_identifier_or_path_is_masked():
    session = GatewaySession(natural_language='en')
    assert 'bank' not in session.mask('def bank_report(bank): return bank', code=True)
    masked = session.mask('Check the bank today.')
    assert 'bank' not in masked and session.restore(masked) == 'Check the bank today.'
    masked = roundtrip('en', 'Open src/radar/config.yaml and read the notes.')
    assert 'radar' not in masked and 'config' not in masked and 'notes' in masked
    masked = roundtrip('en', 'Ask @john about it, e.g. the report.')
    assert '@john' not in masked and 'e.g.' in masked
    masked = roundtrip('en', 'x-anthropic-billing-header: cc_version=2; run --dry-run with mode=fast, a well-known option.')
    for value in ('anthropic', 'billing', 'header', 'dry', 'mode', 'fast'):
        assert value not in masked, value
    assert 'well-known option' in masked
    assert roundtrip('en', 'Note: the meeting starts soon.') == 'Note: the meeting starts soon.'


def test_sensitive_formats_remain_masked():
    text = 'Email alice@example.com the token sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUVWX and call 010-1234-5678.'
    masked = roundtrip('en', text)
    for value in ('alice@example.com', 'sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUVWX', '010-1234-5678'):
        assert value not in masked
    assert 'Email' in masked and 'token' in masked


def test_generic_domain_span_does_not_remask_a_single_public_word():
    session = GatewaySession(natural_language='en')
    pattern = re.compile(r'radar|KF-21|Manta Ray')
    session.engine.domain_spans = lambda text: [(m.start(), m.end()) for m in pattern.finditer(text)]
    text = 'Check the radar on the KF-21 and the Manta Ray.'
    masked = session.mask(text)
    assert 'radar' in masked and 'KF-21' not in masked and 'Manta Ray' not in masked
    assert session.restore(masked) == text


@pytest.mark.parametrize('language', ALL_LANGUAGES)
def test_grammar_words_survive_in_every_language(language):
    if language == 'en':
        words = ['if', 'not', 'before', 'and', 'only']
    elif language == 'ko':
        words = sorted(w for w in KOREAN_FUNCTION_WORDS if len(w) > 1)[:5]
    else:
        words = sorted(CLOSED_CLASS_WORDS[language])[:5]
    separator = '' if language in {'zh', 'ja'} else ' '
    text = separator.join(words)
    assert roundtrip(language, text) == text
