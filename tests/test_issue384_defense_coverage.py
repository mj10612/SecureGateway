"""Defense dictionary coverage for representative reported Korean terms."""
from secure_gateway.domain_dictionaries import catalog


def test_reported_defense_terms_are_matched_when_enabled():
    enabled = {'defense': True, 'automotive': False, 'semiconductor': False}
    disabled = dict.fromkeys(enabled, False)
    for term in ('현무', 'THAAD', '합동참모본부', '방위사업청', '국방과학연구소',
                 'LIG넥스원', '한화에어로스페이스', 'SIGINT', '신호정보',
                 '사격통제장치', '레이더탐색기', '고체로켓모터', '탄두', '해궁',
                 'Lockheed Martin', 'Raytheon', 'Patriot', 'Aegis', 'DARPA',
                 '현대로템', 'KAI', '신관', '추진체', '유도항법', 'IMINT', 'MASINT', 'OSINT'):
        assert catalog().spans(term, enabled), term
        assert not catalog().spans(term, disabled), term


def test_defense_terms_are_masked_and_restore_in_gateway():
    from secure_gateway.gateway import PrivacyGateway

    terms = ('현무', 'THAAD', '합동참모본부', '방위사업청', '국방과학연구소',
             'LIG넥스원', '한화에어로스페이스', 'SIGINT', '신호정보',
             '사격통제장치', '레이더탐색기', '고체로켓모터', '탄두', '해궁',
             'Lockheed Martin', 'Raytheon', 'Patriot', 'Aegis', 'DARPA',
             '현대로템', 'KAI', '추진체', '유도항법', 'IMINT', 'MASINT', 'OSINT')
    with PrivacyGateway(('127.0.0.1', 0), 'fixture') as gateway:
        session = gateway.get_session('codex')
        for term in terms:
            masked = session.mask(term)
            assert term not in masked, term
            assert session.restore(masked) == term


def test_ordinary_words_remain_public_with_defense_enabled():
    from secure_gateway.gateway import PrivacyGateway

    with PrivacyGateway(('127.0.0.1', 0), 'fixture') as gateway:
        session = gateway.get_session('codex')
        for sentence in ('The patriot visited the new building.', '신관 공사 일정 확인',
                         'A radar can be used for weather forecasting.'):
            masked = session.mask(sentence)
            for word in ('patriot', '신관', 'radar'):
                if word in sentence:
                    assert word in masked
            assert session.restore(masked) == sentence
