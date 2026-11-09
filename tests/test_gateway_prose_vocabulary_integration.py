"""Generic integration/regression controls, not independent evaluation tasks."""
import unicodedata

import pytest

import secure_gateway.gateway as gateway
from secure_gateway.gateway import GatewaySession
from secure_gateway.gateway_public_vocabulary import PublicLexicon


def test_korean_common_predicates_preserve_connectives_conditionals_and_politeness():
    session = GatewaySession(natural_language='ko')
    text = '\uae30\ub85d\uc744 \ub9cc\ub4e4\uace0 \uc815\ub9ac\ud574\uc8fc\uc138\uc694. \ubaa8\ub974\uba74 \ubb3c\uc5b4\ubcf4\uc138\uc694.'
    masked = session.mask(text)
    for word in ('\ub9cc\ub4e4\uace0', '\uc815\ub9ac\ud574\uc8fc\uc138\uc694', '\ubaa8\ub974\uba74', '\ubb3c\uc5b4\ubcf4\uc138\uc694'):
        assert word in masked
    assert session.restore(masked) == text


def test_german_public_nouns_compounds_and_common_places_stay_public():
    # Issue #323 user policy: common place names are ordinary public words; the
    # obsolete blanket name/place exclusion no longer masks Berlin/Deutschland.
    session = GatewaySession(natural_language='de')
    text = 'Die Materialliste liegt im Raum. Berlin und Deutschland bleiben bekannt.'
    masked = session.mask(text)
    assert masked == text and session.restore(masked) == text


def test_forced_private_berlin_is_still_masked_everywhere():
    session = GatewaySession(natural_language='de')
    session.forced_rules = lambda: ('Berlin',)
    text = 'Die Materialliste liegt im Raum. Berlin und Deutschland bleiben bekannt.'
    masked = session.mask(text)
    assert 'Berlin' not in masked and 'Materialliste' in masked and 'Deutschland' in masked
    assert session.restore(masked) == text


def test_existing_private_identifier_overrides_a_now_ordinary_word():
    session = GatewaySession(natural_language='de')
    alias = session.mask('Feier', code=True)
    assert alias != 'Feier'
    masked = session.mask('Die Feier folgt danach.')
    assert 'Feier' not in masked and session.restore(masked) == 'Die Feier folgt danach.'


def test_registered_private_korean_root_wins_over_light_verb_derivation():
    session = GatewaySession(natural_language='ko')
    root = '\uc815\ub9ac'
    assert session.mask(root, code=True) != root
    text = '\uc815\ub9ac\ud574\uc8fc\uc138\uc694.'
    masked = session.mask(text)
    assert root not in masked and session.restore(masked) == text


def test_decomposed_public_word_keeps_original_bytes_and_registered_names_stay_opaque():
    session = GatewaySession(natural_language='de')
    assert session.mask('Berlin', code=True) != 'Berlin'  # an actual private mapping
    word = unicodedata.normalize('NFD', 'Bücher')
    text = word + ' und Berlin.'
    masked = session.mask(text)
    assert word in masked and 'Berlin' not in masked
    assert session.restore(masked) == text


@pytest.mark.parametrize('language,inflected,public,root', [
    ('ar', 'ومحمد', 'والكتاب', 'محمد'),
    ('mr', 'नोराच्या', 'खुर्चीवर', 'नोरा'),
    ('te', 'నోరాకు', 'పుస్తకాలకు', 'నోరా'),
])
def test_name_evidence_is_no_veto_but_registered_private_roots_mask_inflections(monkeypatch, language, inflected, public, root):
    # Name evidence alone does not make a frequent inflected surface private ...
    lexicon = PublicLexicon(frozenset({inflected, public}), frozenset({root}), 'unit')
    monkeypatch.setattr(gateway, 'ordinary_words', lambda lang: lexicon.words)
    monkeypatch.setattr(gateway, 'lexicon', lambda lang: lexicon)
    text = inflected + ' ' + public
    session = GatewaySession(natural_language=language)
    assert session.mask(text) == text
    # ... but an actual private registration of the root masks its inflection.
    private = GatewaySession(natural_language=language)
    assert private.mask(root, code=True) != root
    masked = private.mask(text)
    assert inflected not in masked and public in masked
    assert private.restore(masked) == text
