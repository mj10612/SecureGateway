"""Defense dictionary coverage for representative reported Korean terms."""
from secure_gateway.domain_dictionaries import catalog


def test_reported_defense_terms_are_matched_when_enabled():
    enabled = {'defense': True, 'automotive': False, 'semiconductor': False}
    disabled = dict.fromkeys(enabled, False)
    for term in ('현무', 'THAAD', '합동참모본부', '방위사업청', '국방과학연구소',
                 'LIG넥스원', '한화에어로스페이스', 'SIGINT', '신호정보',
                 '사격통제장치', '레이더탐색기', '고체로켓모터', '탄두', '해궁',
                 'Joint Chiefs', 'Lockheed Martin', 'Raytheon', 'Patriot', 'Aegis', 'DARPA',
                 '현대로템', 'KAI', '추진체', '유도항법', 'IMINT', 'MASINT', 'OSINT'):
        assert catalog().spans(term, enabled), term
        assert not catalog().spans(term, disabled), term


def test_defense_terms_are_masked_and_restore_in_gateway():
    from secure_gateway.gateway import PrivacyGateway

    terms = ('현무', 'THAAD', '합동참모본부', '방위사업청', '국방과학연구소',
             'LIG넥스원', '한화에어로스페이스', 'SIGINT', '신호정보',
             '사격통제장치', '레이더탐색기', '고체로켓모터', '탄두', '해궁',
             'Joint Chiefs', 'Lockheed Martin', 'Raytheon', 'Patriot', 'Aegis', 'DARPA',
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


def test_fuze_is_protected_only_with_defense_context_and_restores():
    from secure_gateway.gateway import PrivacyGateway

    with PrivacyGateway(('127.0.0.1', 0), 'fixture') as gateway:
        for text in ('현무의 신관을 점검해줘', '신관과 현무의 작동을 검토해줘'):
            session = gateway.get_session('codex', text)
            masked = session.mask(text)
            assert '신관' not in masked
            assert session.restore(masked) == text
        for text in ('신관 공사 일정 확인', '2026 신관 공사 일정', '현무를 검토해줘. 신관 공사 일정 확인'):
            session = gateway.get_session('codex', text)
            masked = session.mask(text)
            assert '신관' in masked
            assert session.restore(masked) == text
        gateway.set_domain_policy({'defense': False, 'automotive': False, 'semiconductor': False})
        session = gateway.get_session('codex', 'disabled')
        assert '신관' in session.mask('현무의 신관을 점검해줘')


def test_defense_date_is_protected_when_number_masking_enabled():
    from secure_gateway.gateway import GatewaySession

    session = GatewaySession(natural_language='ko', mask_numbers=True)
    text = '2026년 3월에 배치된다'
    masked = session.mask(text)
    assert '2026' not in masked and '3월' not in masked
    assert session.restore(masked) == text
