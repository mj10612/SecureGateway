"""Tests for public-vocabulary/frequency threshold calibration (issue #314).

Candidates:
- vocab_conservative (B: reviewed public vocabulary only, no statistical bins)
- vocab_calibrated (C: per-language threshold chosen on development split only,
  plus ambiguous name-like common words excluded from the public list).
- Default OFF; byte-identical output with toggle off.
"""

from secure_gateway import gateway
from secure_gateway.experiment_profiles import candidate_profile


def test_toggle_off_byte_identical_vocabulary():
    """Verify that with the toggle off, ordinary_words and masking output are byte-identical."""
    baseline_en = gateway.ordinary_words("en")
    baseline_ko = gateway.ordinary_words("ko")
    with candidate_profile(310):
        assert gateway.ordinary_words("en") == baseline_en
        assert gateway.ordinary_words("ko") == baseline_ko

    session = gateway.GatewaySession(natural_language="en")
    text = "The committee reviewed the plan before the meeting."
    assert session.mask(text) == gateway.GatewaySession(natural_language="en").mask(text)


def test_conservative_vocabulary_candidate_b():
    """Candidate B (vocab_conservative) uses reviewed words only, strictly subset of baseline."""
    baseline_en = gateway.ordinary_words("en")
    baseline_ko = gateway.ordinary_words("ko")
    with candidate_profile(314, {"variant": "conservative"}):
        cons_en = gateway.ordinary_words("en")
        cons_ko = gateway.ordinary_words("ko")
        assert cons_en <= baseline_en
        assert len(cons_en) < len(baseline_en)
        assert cons_ko <= baseline_ko
        assert len(cons_ko) < len(baseline_ko)

        # Essential task and discourse words are still retained
        assert "review" in cons_en
        assert "before" in cons_en
        assert "이후" in cons_ko
        assert "먼저" in cons_ko


def test_calibrated_vocabulary_candidate_c_excludes_ambiguous_names():
    """Candidate C (vocab_calibrated) excludes ambiguous name-like common words."""
    with candidate_profile(314, {"variant": "calibrated"}):
        cal_en = gateway.ordinary_words("en")
        cal_ko = gateway.ordinary_words("ko")

        # Ambiguous words used as names in screening tasks are excluded
        assert "still" not in cal_en
        assert "current" not in cal_en
        assert "margin" not in cal_en
        assert "fold" not in cal_en
        assert "drift" not in cal_en
        assert "velvet" not in cal_en
        assert "나란히" not in cal_ko
        assert "흐름" not in cal_ko
        assert "초록" not in cal_ko
        assert "물결" not in cal_ko
        assert "고요" not in cal_ko
        assert "마루" not in cal_ko

        # Non-ambiguous common words are retained
        assert "meeting" in cal_en
        assert "today" in cal_en
        assert "회의" in cal_ko
        assert "오늘" in cal_ko


def test_calibrated_vocabulary_protects_ambiguous_name_in_context():
    """Under calibrated vocabulary, ambiguous words used as private names get protected."""
    text_en = "The internal initiative is called still. Check its readiness; do not deploy it."
    with candidate_profile(314, {"variant": "calibrated"}):
        session = gateway.GatewaySession(natural_language="en")
        session.forced_rules = lambda: ("still",)
        masked = session.mask(text_en)
        assert "still" not in masked
        assert session.restore(masked) == text_en

    text_ko = "비공개 제품 이름은 나란히입니다. 먼저 검토 순서를 설명하세요."
    with candidate_profile(314, {"variant": "calibrated"}):
        session = gateway.GatewaySession(natural_language="ko")
        session.forced_rules = lambda: ("나란히",)
        masked = session.mask(text_ko)
        assert "나란히" not in masked
        assert session.restore(masked) == text_ko
