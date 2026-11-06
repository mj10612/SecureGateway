from secure_gateway.gateway import GatewaySession
import pytest


def test_korean_requests_retain_action_and_public_context():
    session = GatewaySession()
    first = session.mask("SecureMCP 삭제해줘")
    assert "SecureMCP" not in first
    assert "삭제해줘" in first
    second = session.mask("그럼, github에서 리파지토리를 찾아 줄 수 있어?")
    for word in ("github에서", "리파지토리를", "찾아", "줄", "수", "있어"):
        assert word in second
    assert session.restore(first) == "SecureMCP 삭제해줘"


def test_korean_request_words_do_not_expose_private_values_or_code():
    session = GatewaySession()
    text = "비밀고객의 파일을 찾아서 수정해줘 alice@example.com"
    masked = session.mask(text)
    assert "비밀고객" not in masked
    assert "alice@example.com" not in masked
    assert "찾아서" in masked and "수정해줘" in masked
    assert session.restore(masked) == text
    assert "삭제해줘" not in session.mask("삭제해줘", code=True)


def test_forced_partial_word_restores_without_exposing_other_aliases():
    session = GatewaySession()
    session.forced_rules = lambda: ("ile",)
    masked = session.mask("files Zorvexa")
    assert "ile" not in masked
    assert masked.startswith("f⟦private_symbol_")
    assert session.restore(masked) == "files Zorvexa"


def test_unknown_alias_in_adjacent_run_fails_closed():
    session = GatewaySession()
    first = session.mask("Zorvexa")
    with pytest.raises(ValueError, match="Unrecognized"):
        session.restore(first + "private_symbol_999999")


@pytest.mark.parametrize("rules", [(), ("삭제",)])
def test_literal_partial_alias_delimiters_survive_roundtrip(rules):
    session = GatewaySession()
    session.forced_rules = lambda: rules
    session.mask("Zorvexa")
    text = "⟦private_symbol_1⟧ and ⟦secret⟧"
    assert session.restore(session.mask(text)) == text


def test_partial_alias_expansion_respects_output_limit():
    session = GatewaySession(max_input_bytes=30)
    with pytest.raises(ValueError, match="size limit"):
        session.mask("⟦" * 2)


def test_foreign_task_word_does_not_expose_english_proper_name():
    session = GatewaySession(natural_language="en")
    assert "Ara" not in session.mask("Ara")
    assert "Sil" not in session.mask("Sil")
    assert "Delete" not in session.mask("Delete")


def test_forced_rule_matches_canonical_unicode_equivalents():
    session = GatewaySession(natural_language="fr")
    session.forced_rules = lambda: ("e\u0301",)
    masked = session.mask("vérifie")
    assert "é" not in masked
    assert session.restore(masked) == "vérifie"


def test_forced_rules_block_leaks_in_protocol_fields_and_numbers():
    session = GatewaySession()
    session.forced_rules = lambda: ("private_symbol_1",)
    with pytest.raises(ValueError, match="protocol field"):
        session.request({"model": "private_symbol_1", "input": []})
    session.forced_rules = lambda: ("123",)
    with pytest.raises(ValueError, match="protocol field"):
        session.request({"model": "m", "input": [], "max_output_tokens": 123})


# Small task-focused examples, not a representative privacy or fluency benchmark.
@pytest.mark.parametrize("language,action,technical", [
    ("en", "please review", "pharmacokinetics"),
    ("ko", "확인해줘", "약물동태학"),
    ("es", "revisa", "farmacocinética"),
    ("fr", "vérifie", "pharmacocinétique"),
    ("pt", "verifique", "farmacocinética"),
    ("de", "prüfe", "Pharmakokinetik"),
    ("id", "periksa", "farmakokinetik"),
    ("tr", "kontrol et", "farmakokinetik"),
    ("ru", "проверь", "фармакокинетика"),
    ("hi", "जाँचें", "फार्माकोकाइनेटिक्स"),
    ("mr", "तपासा", "फार्माकोकाइनेटिक्स"),
    ("bn", "পরীক্ষা করুন", "ফার্মাকোকিনেটিক্স"),
    ("ur", "جانچ کریں", "فارماکوکینیٹکس"),
    ("te", "తనిఖీ చేయండి", "ఫార్మకోకైనెటిక్స్"),
    ("ar", "تحقق", "الحركيةالدوائية"),
    ("zh", "检查", "药代动力学"),
    ("ja", "確認", "薬物動態学"),
])
def test_supported_languages_keep_task_words_and_mask_private_terms(language, action, technical):
    session = GatewaySession(natural_language=language)
    text = f"{action} Zorvexa {technical} test@example.com"
    masked = session.mask(text)
    assert action in masked
    assert "Zorvexa" not in masked
    assert technical not in masked
    assert "test@example.com" not in masked
    assert session.restore(masked) == text
