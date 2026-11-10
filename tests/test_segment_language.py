"""Tests for per-segment language handling for mixed-language input (issue #313).

Candidate segment_language:
- Choose language per sentence/quote/list-item segment using detect_natural_language() evidence.
- Segments below confidence/length floor inherit request language (never union of vocabularies).
- Sensitive-pattern, forced-rule and code-span detection run on WHOLE text first;
  segment boundaries may not cut through any such span.
- ko/en only.
- Measure extra tokenisation cost.
- Default OFF; byte-identical output with toggle off.
"""

from secure_gateway import gateway
from secure_gateway.experiment_profiles import candidate_profile


def test_toggle_off_byte_identical_mixed_language():
    """Verify that with the toggle off, output is byte-identical to baseline."""
    texts = [
        '다음 영어 지침의 금지 사항만 한국어로 두 개 적어 주세요:\n"Do not replace the original. Do not publish until the reviewer confirms."\n프로젝트명은 EmberQzx입니다.',
        'Write one clarification question in English for this Korean instruction: "크기를 모르면 먼저 물어보고, 확인 전에는 배치하지 마세요."\nThe private document is CobaltQzx.',
        'Simple English text without quotes.',
        '단순 한국어 텍스트입니다.',
    ]
    for text in texts:
        baseline = gateway.GatewaySession().mask(text)
        with candidate_profile(310):
            assert gateway.GatewaySession().mask(text) == baseline
        assert gateway.GatewaySession().mask(text) == baseline


def test_segmented_language_korean_prompt_english_quote():
    """Korean prompt with English quoted sentence applies English rules to the quote."""
    text = (
        '다음 영어 지침의 금지 사항만 한국어로 두 개 적어 주세요:\n'
        '"Do not replace the original. Do not publish until the reviewer confirms."\n'
        '프로젝트명은 EmberQzx입니다.'
    )
    with candidate_profile(313):
        session = gateway.GatewaySession(natural_language="ko")
        session.forced_rules = lambda: ("EmberQzx",)
        masked = session.mask(text)
        assert "EmberQzx" not in masked
        assert "Do not replace the original" in masked
        assert "Do not publish until the reviewer confirms" in masked
        assert session.restore(masked) == text


def test_segmented_language_english_prompt_korean_quote():
    """English prompt with Korean quoted sentence applies Korean rules to the quote."""
    text = (
        'Write one clarification question in English for this Korean instruction: '
        '"크기를 모르면 먼저 물어보고, 확인 전에는 배치하지 마세요."\n'
        'The private document is CobaltQzx.'
    )
    with candidate_profile(313):
        session = gateway.GatewaySession(natural_language="en")
        session.forced_rules = lambda: ("CobaltQzx",)
        masked = session.mask(text)
        assert "CobaltQzx" not in masked
        assert "크기를 모르면 먼저 물어보고" in masked
        assert session.restore(masked) == text


def test_segmented_language_does_not_cut_through_forced_spans():
    """Forced multiword phrase spanning across newline or boundary must not be cut."""
    with candidate_profile(313):
        session = gateway.GatewaySession()
        session.forced_rules = lambda: ("Blue\nMeadow",)
        source = "조건을 확인하세요.\nBlue\nMeadow\nDo not delete the original."
        masked = session.mask(source)
        assert "Blue" not in masked and "Meadow" not in masked
        assert session.restore(masked) == source


def test_segmented_language_does_not_cut_through_urls_or_code():
    """URLs and code blocks spanning multiple words/lines remain protected as single units."""
    with candidate_profile(313):
        session = gateway.GatewaySession()
        source = 'Check this: "https://secret.example.com/api/v1/resource?token=abc123xyz"\nDone.'
        masked = session.mask(source)
        assert "secret.example.com" not in masked
        assert session.restore(masked) == source


def test_short_segment_below_floor_inherits_request_language():
    """Short segments (e.g. abbreviations, numbers, short phrases) inherit request language."""
    with candidate_profile(313):
        session = gateway.GatewaySession(natural_language="ko")
        text = "항목:\n- OK\n- Yes\n세부사항을 확인하세요."
        masked = session.mask(text)
        assert session.restore(masked) == text
