"""Adding sensitive terms must never split an already protected token (#270)."""

import pytest

from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import MaskMode, SurrogateStrategy
from secure_gateway.session import PrivacySession


@pytest.mark.parametrize('strategy', list(SurrogateStrategy))
@pytest.mark.parametrize('mode', [MaskMode.ENTITIES_ONLY, MaskMode.CONTENT_WORDS, MaskMode.UNCOMMON_WORDS])
@pytest.mark.parametrize('source,terms', [
    ('https://private.example/token', {'private'}),
    ('alice@example.com', {'alice'}),
    ('`private hidden`', {'private'}),
    ('```text\nprivate hidden\n```', {'private'}),
    ('sk-privateABC1234567890', {'sk'}),
    ('https://private.example/token', {'private', 'example', 'token'}),
    ('alice@example.com', {'alice@example.com'}),
    ('https://private.example/token', {'private.example/token'}),
])
def test_forced_terms_keep_whole_opaque_token(strategy, mode, source, terms):
    engine = MaskingEngine()
    for sensitive in (None, terms):
        session = PrivacySession('opaque', strategy=strategy)
        result = engine.mask_text(source, session.session_id, session.generator,
                                  session.forward_store, session.reverse_store,
                                  mode=mode, sensitive_terms=sensitive)
        assert result.masked_tokens == 1
        assert next(iter(session.forward_store.values())).original == source
        assert engine.unmask(result.masked_text, session.session_id, session.reverse_store,
                             strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize('language,source,terms,originals', [
    ('en', 'private privateName public', {'private'}, ['private']),
    ('ko', '민서는 학교에서', {'민서'}, ['민서', '학교에서']),
    ('zh', '这是私人项目', {'私人'}, None),
    ('ja', 'これは秘密です', {'秘密'}, None),
    ('en', 'send https://private.example/token now', {'send https://private'},
     ['send https://private.example/token']),
    ('en', 'alice@example.com and bob@example.com', {'alice', 'bob'},
     ['alice@example.com', 'bob@example.com']),
])
def test_boundaries_particles_and_cross_token_spans(language, source, terms, originals):
    engine = MaskingEngine()
    session = PrivacySession('boundaries')
    result = engine.mask_text(source, session.session_id, session.generator,
                              session.forward_store, session.reverse_store,
                              mode=MaskMode.ENTITIES_ONLY, language=language,
                              sensitive_terms=terms)
    if originals is not None:
        assert [m.original for m in session.forward_store.values()] == originals
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store,
                         strict=True).unmasked_text == source
