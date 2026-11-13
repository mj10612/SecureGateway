"""Text intent and constraints must remain usable with opaque references."""
import json
import re
from pathlib import Path

import pytest
from secure_gateway.gateway import GatewaySession


PARAGRAPHS = [row for name in ("semantic_paragraphs.json", "semantic_holdout.json", "semantic_holdout2.json")
              for row in json.loads((Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8"))]


@pytest.mark.parametrize("row", PARAGRAPHS, ids=lambda row: row["language"])
def test_paragraphs_keep_references_private_and_restore_exactly(row):
    session = GatewaySession()
    session.forced_rules = lambda: tuple(row["references"])
    request = session.request({"model": "fixture", "input": [{"role": "user", "content": row["text"]}]})
    masked = request["input"][0]["content"]
    for reference in row["references"]:
        assert reference not in masked
    assert session.restore(masked) == row["text"]
    # Replaying a request must not make its opaque references public.
    second = session.request({"model": "fixture", "input": [{"role": "user", "content": row["text"]}]})
    assert second["input"][0]["content"] == masked


def test_repeated_reference_codes_use_the_same_alias_from_the_start():
    session = GatewaySession(natural_language="en")
    masked = session.mask("QX-731 / QX-731")
    first, second = masked.split(" / ")
    assert first == second
    assert session.restore(masked) == "QX-731 / QX-731"
    separate = GatewaySession(natural_language="en")
    first = separate.mask("QX-731")
    assert separate.mask("QX-731") == first


@pytest.mark.parametrize("number", ["1_234", "0b1010_0101", "0xFF_FF", "1_234e-4", "0x1F", "1e-3", "42"])
@pytest.mark.parametrize("mask_numbers", [False, True])
def test_source_numeric_spellings_remain_private_and_restore_in_prose(number, mask_numbers):
    session = GatewaySession(natural_language="en", mask_numbers=mask_numbers)
    session.mask("value = " + number, code=True)
    text = "Use " + number + " again."
    masked = session.mask(text)
    # #374: plain decimal numbers are public by default; other source spellings stay private.
    public = not mask_numbers and number in {"1e-3", "42"}
    assert bool(re.search(r"(?<!\w)" + re.escape(number) + r"(?!\w)", masked)) is public
    assert session.restore(masked) == text
    assert session.mask(text) == masked


def test_common_discourse_words_remain_public_in_all_positions():
    session = GatewaySession(natural_language="en")
    text = "First, compare Zorvexa and First. Then, recommend the cheaper option."
    masked = session.mask(text)
    assert masked.startswith("First,")
    assert "Then," in masked
    assert "and First" in masked
    assert "Zorvexa" not in masked
    assert session.restore(masked) == text


def test_private_mapping_and_force_rules_override_discourse_markers():
    session = GatewaySession(natural_language="en")
    session.mask("First", code=True)
    assert not session.mask("First, compare the options.").startswith("First,")
    fresh = GatewaySession(natural_language="en")
    fresh.forced_rules = lambda: ("First",)
    assert "First" not in fresh.mask("First, compare the options.")


def test_aggressive_mode_does_not_enable_discourse_exceptions():
    masked = GatewaySession(natural_language="en", prose_mode="aggressive").mask("First, compare the options.")
    assert not masked.startswith("First,")


@pytest.mark.parametrize("language,text,operators", [
    ("en", "Compare the options. Then summarize the result without guessing.", ("Compare", "summarize", "without")),
    ("de", "Vergleiche die Optionen. Erstelle danach einen Plan.", ("Vergleiche", "Erstelle", "danach")),
    ("ko", "먼저 비교해 주세요. 이름은 제외하고 추측하지 마세요.", ("먼저", "비교해", "제외하고", "마세요")),
])
def test_request_preserves_operations_and_constraints(language, text, operators):
    payload = GatewaySession(natural_language=language).request({"model": "fixture", "input": [{"role": "user", "content": text}]})
    masked = payload["input"][0]["content"]
    assert all(operator in masked for operator in operators)


def test_common_imperative_word_remains_public_in_name_position():
    session = GatewaySession(natural_language="en")
    masked = session.mask("Compare the options and ask Compare.")
    assert masked.startswith("Compare ") and "ask Compare" in masked
    session.forced_rules = lambda: ("Compare",)
    assert "Compare" not in session.mask("Compare the options and ask Compare.")


@pytest.mark.parametrize("text", ["  Compare the options.", "\tCompare two options.", "Compare 2 options."])
def test_instruction_positions_handle_leading_space_and_numeric_counts(text):
    session = GatewaySession(natural_language="en")
    masked = session.mask(text)
    assert masked.lstrip().startswith("Compare ")
    assert session.restore(masked) == text


def test_korean_conditional_selection_and_negative_actions_remain_readable():
    session = GatewaySession(natural_language="ko")
    text = "정보가 부족하면 하나를 고르지 말고 필요한 내용을 알려 주세요. 회의를 예약하거나 메시지를 보내지는 마세요."
    masked = session.mask(text)
    assert all(word in masked for word in ("부족하면", "고르지", "말고", "예약하거나", "보내지는", "마세요"))
    assert session.restore(masked) == text
    strict = GatewaySession(natural_language="ko")
    strict.forced_rules = lambda: ("부족하면", "예약하거나")
    protected = strict.mask(text)
    assert "부족하면" not in protected and "예약하거나" not in protected


@pytest.mark.parametrize("text", ["Compare", "Compare acquired Zorvexa.", "Compare is a private project.",
                                  "Compare works with Zorvexa.", "Reserve offers plans.", "Compare may acquire Zorvexa.",
                                  "Compare matches the code.", "Compare sends reports.", "Contact only sends reports.",
                                  "Reserve only offers plans.", "Reserve first announced Zorvexa.", "First sends reports."])
def test_registered_instruction_word_in_name_position_stays_private(text):
    session = GatewaySession(natural_language="en")
    word = text.split()[0]
    assert word in session.mask(text)
    session.forced_rules = lambda: (word,)
    assert word not in session.mask(text)


@pytest.mark.parametrize("language,text,name", [
    ("de", "Vergleiche arbeitet heute.", "Vergleiche"),
    ("es", "Compara trabaja aquí.", "Compara"),
    ("fr", "Compare travaille ici.", "Compare"),
    ("pt", "Compare trabalha aqui.", "Compare"),
])
def test_other_languages_keep_registered_ambiguous_subjects_private(language, text, name):
    session = GatewaySession(natural_language=language)
    assert name in session.mask(text)
    session.forced_rules = lambda: (name,)
    assert name not in session.mask(text)
