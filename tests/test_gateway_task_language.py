import json
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
    session.forced_rules = lambda: ("비밀고객",)
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


def test_registered_foreign_task_word_does_not_expose_english_proper_name():
    session = GatewaySession(natural_language="en")
    session.forced_rules = lambda: ("Ara", "Sil", "Delete")
    assert "Ara" not in session.mask("Ara")
    assert "Sil" not in session.mask("Sil")
    assert "Delete" not in session.mask("Delete")


def test_sensitive_mapping_and_explicit_rule_override_general_vocabulary():
    session = GatewaySession(natural_language="en")
    source = session.mask("meeting", code=True)
    text = session.mask("meeting")
    assert "meeting" not in text
    assert session.restore(source) == session.restore(text) == "meeting"
    fresh = GatewaySession(natural_language="en")
    fresh.forced_rules = lambda: ("meeting",)
    assert "meeting" not in fresh.mask("meeting")


def test_forced_rules_override_public_skill_language():
    session = GatewaySession(natural_language="en")
    session.forced_rules = lambda: ("SKILL.md", "Read")
    masked = session.mask("Read SKILL.md before using this skill.")
    assert "SKILL.md" not in masked and "Read" not in masked
    assert session.restore(masked) == "Read SKILL.md before using this skill."


@pytest.mark.parametrize("language,text", [
    ("en", "clean the window and prepare breakfast"),
    ("fr", "nettoyer la fenêtre et préparer le petit déjeuner"),
    ("es", "limpiar la ventana y preparar el desayuno"),
    ("de", "fenster reinigen und frühstück vorbereiten"),
    ("id", "membersihkan jendela dan menyiapkan sarapan"),
    ("ru", "помыть окно и приготовить завтрак"),
])
def test_broad_everyday_vocabulary_survives(language, text):
    session = GatewaySession(natural_language=language)
    assert session.mask(text) == text


@pytest.mark.parametrize("language,text", [("mr", "घराच्या"), ("te", "పుస్తకంలో")])
def test_reviewed_indic_words_with_case_suffixes_remain_understandable(language, text):
    session = GatewaySession(natural_language=language)
    assert session.mask(text) == text


def test_frequent_domain_words_are_public_unless_registered_private():
    session = GatewaySession(natural_language="en")
    text = "review cancer credit and bank"
    assert session.mask(text) == text
    session.forced_rules = lambda: ("cancer", "credit", "bank")
    masked = session.mask(text)
    assert all(word not in masked for word in ("cancer", "credit", "bank"))
    assert session.restore(masked) == text


@pytest.mark.parametrize("text", ["cancer's", "bank’s", "banking", "cancers", "password's"])
def test_registered_domain_inflections_do_not_bypass_masking(text):
    session = GatewaySession(natural_language="en")
    session.forced_rules = lambda: (text,)
    masked = session.mask(text)
    assert text not in masked
    assert session.restore(masked) == text


@pytest.mark.parametrize("text", ["ومحمد", "السرطان"])
def test_arabic_prefixes_do_not_expose_registered_names_or_domains(text):
    session = GatewaySession(natural_language="ar")
    session.forced_rules = lambda: (text,)
    masked = session.mask(text)
    assert text not in masked
    assert session.restore(masked) == text


def test_tool_argument_literals_are_private_even_if_common_words():
    session = GatewaySession()
    item = {"type": "function_call", "name": "privateTool", "arguments":
            '{"api_key":"rose","name":"john","procedure":"chemotherapy"}'}
    masked = session.request({"model": "fixture", "input": [item]}, dialect="responses")
    arguments = json.loads(masked["input"][0]["arguments"])
    assert all(value not in arguments.values() for value in ("rose", "john", "chemotherapy"))
    assert session.walk(masked["input"][0], restore=True) == item


def test_existing_code_mapping_takes_precedence_over_skill_filename():
    session = GatewaySession()
    filename = session.mask("SKILL.md", code=True)
    masked = session.mask("Read SKILL.md before using this skill.")
    assert "SKILL.md" not in masked
    assert session.restore(filename) == "SKILL.md"
    assert session.restore(masked) == "Read SKILL.md before using this skill."


@pytest.mark.parametrize("text", ["meeting. tomorrow", "Read SKILL.md before using this skill."])
def test_existing_multiword_secret_is_not_split_by_prose_processing(text):
    session = GatewaySession(natural_language="en")
    session.mask("x = " + repr(text), code=True)
    masked = session.mask(text)
    assert text not in masked
    assert session.restore(masked) == text


def test_existing_multiword_secret_outside_inline_code_remains_private():
    session = GatewaySession(natural_language="en")
    session.mask('x = "meeting. tomorrow"', code=True)
    text = 'Read `SKILL.md`. meeting. tomorrow'
    masked = session.mask(text)
    assert "meeting. tomorrow" not in masked
    assert session.restore(masked) == text


def test_existing_skill_literal_outside_code_does_not_use_public_exception():
    session = GatewaySession()
    session.mask('x = "Read SKILL.md"', code=True)
    text = 'Read SKILL.md and `other`'
    masked = session.mask(text)
    assert "Read SKILL.md" not in masked
    assert session.restore(masked) == text


def test_raw_source_literals_with_backticks_keep_source_protection():
    session = GatewaySession()
    text = 'meeting = "```hello```"; window = "other"'
    masked = session.mask(text)
    assert all(word not in masked for word in ("meeting", "window", "other", "hello"))
    assert session.restore(masked) == text


def test_existing_literal_does_not_bypass_automatic_source_masking():
    session = GatewaySession(natural_language="en")
    session.mask('x = "hello world"', code=True)
    text = 'meeting = "hello world"\nwindow = "other"'
    masked = session.mask(text)
    assert all(word not in masked for word in ("meeting", "window", "other"))
    assert session.restore(masked) == text


@pytest.mark.parametrize("text", ['```python\nmeeting = "other"', 'Review `meeting = "other"'])
def test_unclosed_code_spans_fail_closed(text):
    with pytest.raises(ValueError, match="Unclosed"):
        GatewaySession(natural_language="en").mask(text)


def test_double_backtick_markdown_can_contain_literal_backticks():
    session = GatewaySession(natural_language="en")
    text = 'Choose a keyword (`**`) or inline code/path (`` ` ``).'
    assert session.restore(session.mask(text)) == text
    code = 'Review ``meeting = "other"``'
    masked = session.mask(code)
    assert "meeting" not in masked and "other" not in masked
    assert session.restore(masked) == code


def test_known_literal_does_not_bypass_double_backtick_source():
    session = GatewaySession(natural_language="en")
    session.mask('x = "hello world"', code=True)
    text = 'Review ``meeting = "hello world"; `window` = "other"``'
    masked = session.mask(text)
    assert "window" not in masked and "other" not in masked and "meeting" not in masked
    assert session.restore(masked) == text


def test_nested_different_backtick_runs_share_masking_boundaries():
    session = GatewaySession(natural_language="en")
    text = '``book ```python\nmeeting = "other"\n``` window``'
    masked = session.mask(text)
    assert "other" not in masked and "meeting" not in masked and "window" not in masked
    assert session.restore(masked) == text


def test_markdown_span_inventory_is_bounded():
    with pytest.raises(ValueError, match="Too many"):
        GatewaySession().mask("`x` " * 4097)


def test_skill_filename_inside_url_is_not_split_or_exposed():
    session = GatewaySession()
    text = "https://example.invalid/SKILL.md?token=secret"
    masked = session.mask(text)
    assert "example.invalid" not in masked and "secret" not in masked
    assert session.restore(masked) == text


def test_skill_filename_inside_email_is_never_disclosed():
    session = GatewaySession()
    text = "book@SKILL.md"
    masked = session.mask(text)
    assert text not in masked
    assert session.restore(masked) == text


@pytest.mark.parametrize("text", ["秘密SKILL.md", "SKILL.md秘密", "비밀SKILL.md", "SKILL.md비밀", "a\u1ab0SKILL.md", "a\u05b0SKILL.md"])
def test_skill_filename_adjacent_to_unicode_restores_exactly(text):
    session = GatewaySession()
    assert session.restore(session.mask(text)) == text


def test_capitalized_common_words_can_be_private_names():
    session = GatewaySession(natural_language="en")
    assert session.mask("Meeting acquired Water.") == "Meeting acquired Water."
    session.forced_rules = lambda: ("Meeting", "Water")
    masked = session.mask("Meeting acquired Water.")
    assert "Meeting" not in masked and "Water" not in masked


def test_skill_instruction_keeps_ordinary_read_unless_registered_private():
    session = GatewaySession()
    text = "Read SKILL.md and ask Read for help."
    masked = session.mask(text)
    assert masked.startswith("Read SKILL.md")
    assert "ask Read" in masked
    assert session.restore(masked) == text
    session.forced_rules = lambda: ("Read",)
    assert "Read" not in session.mask(text)


def test_skill_follow_verb_stays_public_unless_registered_private():
    session = GatewaySession()
    text = "Read SKILL.md. Follow its instructions and ask Follow for help."
    masked = session.mask(text)
    assert "SKILL.md." in masked and "Follow its instructions" in masked
    assert "ask Follow" in masked
    assert session.restore(masked) == text
    session.forced_rules = lambda: ("Follow",)
    assert "Follow" not in session.mask(text)


def test_aggressive_mode_does_not_preserve_new_general_words():
    session = GatewaySession(natural_language="en", prose_mode="aggressive")
    masked = session.mask("Meeting Water Book Home")
    assert all(word not in masked for word in ("Meeting", "Water", "Book", "Home"))


def test_aggressive_mode_does_not_enable_skill_exceptions():
    session = GatewaySession(natural_language="en", prose_mode="aggressive")
    masked = session.mask("Read `SKILL.md` before using this skill. Follow its instructions.")
    assert "Read" not in masked and "Follow" not in masked and "SKILL.md" not in masked
    assert all(word not in session.mask("using skill instructions follow")
               for word in ("using", "skill", "instructions", "follow"))
    assert "SKILL.md" not in GatewaySession(prose_mode="aggressive").mask("SKILL.md")


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
    session.forced_rules = lambda: ("Zorvexa", technical)
    text = f"{action} Zorvexa {technical} test@example.com"
    masked = session.mask(text)
    assert action in masked
    assert "Zorvexa" not in masked
    assert technical not in masked
    assert "test@example.com" not in masked
    assert session.restore(masked) == text
