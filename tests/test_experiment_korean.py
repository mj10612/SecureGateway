"""Isolated Korean grammar candidate; no runtime adoption or quality scores."""

import unicodedata

import pytest

from secure_gateway.experiment_korean import preserve_spans


def selected(text):
    return [text[start:end] for start, end in preserve_spans(text)]


@pytest.mark.parametrize("text,expected", [
    ("높이를 모르면 먼저 물어보고 배치해줘", ["모르면", "물어보고", "배치해줘"]),
    ("손상된 책은 제외하고 붙이자는 제안은 하지 마세요", ["손상된", "제외하고", "붙이자는", "하지", "마세요"]),
    ("준비가 정상인 경우 확인한 뒤에 실행해 주세요", ["정상인", "확인한", "뒤에", "실행해", "주세요"]),
    ("이름을 알 수 없으면 배포하지말고 질문해줘", ["알", "수", "없으면", "배포하지말고", "질문해줘"]),
])
def test_reviewed_roots_preserve_actions_conditions_and_negation(text, expected):
    assert selected(text) == expected


@pytest.mark.parametrize("text", [
    "검토했더라도", "질문하셨으면", "정리하기전에", "배치한뒤에", "삭제하지마세요",
    "손상되었더라도", "물어봤으면", "붙여주세요", "모르겠으면", "알려주셨으면",
])
def test_new_compositions_of_reviewed_roots_and_endings(text):
    # These compositions exercise classes; they are not extra public words.
    assert selected(text) == [text]


def test_unknown_roots_names_and_industrial_actions_do_not_gain_public_suffixes():
    text = "오로라하면 성운모르면 극비프로젝트된 에피택시하면 노광해줘 레이저증착된"
    assert selected(text) == []
    assert selected("private검토해 검토해private 개인_검토해") == []


def test_unknown_names_adjacent_to_grammar_are_not_selected():
    text = "누리안을 검토한뒤에 맑음만 확인하고 여울에게 질문해줘"
    spans = preserve_spans(text)
    assert [text[a:b] for a, b in spans] == ["검토한뒤에", "확인하고", "질문해줘"]
    assert all(not any(secret in text[a:b] for secret in ("누리안", "맑음", "여울")) for a, b in spans)


def test_nfc_nfd_offsets_preserve_original_spelling_and_nonoverlap():
    text = "비공개명을 " + unicodedata.normalize("NFD", "검토하셨으면") + " 먼저 물어보세요."
    spans = preserve_spans(text)
    assert [unicodedata.normalize("NFC", text[a:b]) for a, b in spans] == ["검토하셨으면", "물어보세요"]
    assert all(a < b for a, b in spans)
    assert all(left[1] <= right[0] for left, right in zip(spans, spans[1:]))
    assert "".join(text[a:b] for a, b in spans).startswith(unicodedata.normalize("NFD", "검토하셨으면"))


def test_code_urls_emails_and_unclosed_markup_are_not_public_grammar():
    assert selected('def 검토해():\n    return "물어보세요"') == []
    assert selected("`물어보세요`를 실행하지 마세요") == ["실행하지", "마세요"]
    assert selected("https://private.example/물어보세요 검토해@example.com") == []
    assert selected("`물어보세요") == []


def test_ambiguous_grammar_is_only_returned_with_reviewed_context():
    assert selected("알 수 없으면 먼저 확인해") == ["알", "수", "없으면", "확인해"]
    assert selected("알 수 없는값") == []
    assert selected("알 이름 수 이름") == []


@pytest.mark.parametrize("value", [None, "검토해".encode(), 1])
def test_invalid_input_is_rejected(value):
    with pytest.raises(ValueError):
        preserve_spans(value)


def test_input_and_output_budgets_are_explicit():
    with pytest.raises(ValueError, match="budget"):
        preserve_spans("가" * (1024 * 1024))
    with pytest.raises(ValueError, match="budget"):
        preserve_spans("검토해 " * 100_001)
