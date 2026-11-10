"""Tests for Korean conjugation/condition/negation/request split (issue #309).

Candidate ko_conjugation_split:
- Bounded, rule-based ending table (conditional -면/-으면, sequence -기 전에/-ㄴ 뒤에,
  negation/prohibition -지 말고/-지 마, request -세요/-해줘, adnominal -ㄴ/-은/-된)
- Stem is judged by existing policy; grammatical ending is kept public.
- Stem that is a forced rule / dictionary term / existing mapping stays masked
  (stem masked, ending kept).
- When split is uncertain, fall back to today's behavior.
- Evaluated on unseen stems/endings/spacing.
- Default is OFF; output is byte-identical with toggle off.
"""

from secure_gateway import gateway
from secure_gateway.experiment_profiles import candidate_profile
from secure_gateway.engine.grammar_ko import (
    KOREAN_CONJUGATION_ENDINGS,
)


def test_toggle_off_byte_identical_korean():
    """Verify that with the toggle off, output is byte-identical to baseline."""
    sentences = [
        "선반 높이를 모르면 먼저 물어보세요.",
        "전시 계획 새솔Qzx를 검토해줘.",
        "표지가 손상된 책은 제외하고 접착식 표지는 붙이자는 제안을 하지 마세요.",
        "프로젝트 별무리Qzx를 검토하되 승인되기 전에는 배포하지 마세요.",
        "준비 여부를 모르면 먼저 확인 질문 하나만 해주세요.",
        "루미노바를 확인해 주세요.",
    ]
    for text in sentences:
        baseline = gateway.GatewaySession(natural_language="ko").mask(text)
        # Inside no profile or non-309 profile, must match baseline exactly
        with candidate_profile(310):
            assert gateway.GatewaySession(natural_language="ko").mask(text) == baseline
        assert gateway.GatewaySession(natural_language="ko").mask(text) == baseline


def test_conjugation_ending_table_contents():
    """Check that bounded ending table includes required categories."""
    endings = set(KOREAN_CONJUGATION_ENDINGS)
    # Conditional
    assert "면" in endings and "으면" in endings
    # Sequence
    assert any(e in endings for e in ["기전에", "기전", "ㄴ뒤에", "은뒤에", "ㄴ뒤", "은뒤"])
    # Negation / Prohibition
    assert any(e in endings for e in ["지말고", "지마", "지마세요", "지마십시오", "지않고"])
    # Request
    assert any(e in endings for e in ["세요", "으세요", "해줘", "해주세요", "해주십시오"])
    # Adnominal
    assert any(e in endings for e in ["된", "한", "는", "은", "ㄴ"])


def test_conjugation_split_forced_stem_masked_ending_kept():
    """Forced rule / sensitive term has its stem masked while ending is kept public."""
    with candidate_profile(309):
        session = gateway.GatewaySession(natural_language="ko")
        session.forced_rules = lambda: ("루미노바",)

        # Conditional -면
        m_cond = session.mask("루미노바면 즉시 중단하세요.")
        assert "루미노바" not in m_cond
        assert "면" in m_cond
        assert session.restore(m_cond) == "루미노바면 즉시 중단하세요."

        # Request -해줘
        m_req = session.mask("루미노바해줘.")
        assert "루미노바" not in m_req
        assert "해줘" in m_req
        assert session.restore(m_req) == "루미노바해줘."

        # Adnominal -된
        m_adn = session.mask("루미노바된 문서를 확인하세요.")
        assert "루미노바" not in m_adn
        assert "된" in m_adn
        assert session.restore(m_adn) == "루미노바된 문서를 확인하세요."

        # Sequence -하기 전에
        m_seq = session.mask("루미노바하기 전에 질문해 주세요.")
        assert "루미노바" not in m_seq
        assert "전에" in m_seq
        assert session.restore(m_seq) == "루미노바하기 전에 질문해 주세요."

        # Negation -하지 말고
        m_neg = session.mask("루미노바하지 말고 다른 작업을 하세요.")
        assert "루미노바" not in m_neg
        assert "말고" in m_neg
        assert session.restore(m_neg) == "루미노바하지 말고 다른 작업을 하세요."


def test_conjugation_split_unseen_stems():
    """Evaluate on unseen synthetic stems and endings."""
    with candidate_profile(309):
        session = gateway.GatewaySession(natural_language="ko")
        session.forced_rules = lambda: ("별매듭", "노을상자")

        # Unseen stem 1 with -된
        text1 = "별매듭된 보관함을 점검하세요."
        m1 = session.mask(text1)
        assert "별매듭" not in m1
        assert "된" in m1
        assert session.restore(m1) == text1

        # Unseen stem 2 with -하지마세요
        text2 = "노을상자하지마세요."
        m2 = session.mask(text2)
        assert "노을상자" not in m2
        assert session.restore(m2) == text2

        # Unseen stem with spacing: -한 뒤에
        text3 = "별매듭한 뒤에 연락하세요."
        m3 = session.mask(text3)
        assert "별매듭" not in m3
        assert "뒤에" in m3
        assert session.restore(m3) == text3


def test_conjugation_split_latin_alphanumeric_stem():
    """Latin/alphanumeric stems like EmberQzx keep attached Korean endings."""
    with candidate_profile(309):
        session = gateway.GatewaySession(natural_language="ko")
        session.forced_rules = lambda: ("EmberQzx",)

        text = "EmberQzx면 먼저 확인하고 EmberQzx해줘."
        masked = session.mask(text)
        assert "EmberQzx" not in masked
        assert "면" in masked and "해줘" in masked
        assert session.restore(masked) == text


def test_uncertain_split_falls_back_to_current_behavior():
    """When split is uncertain (not valid ending or empty stem), falls back to today's behavior."""
    with candidate_profile(309):
        session = gateway.GatewaySession(natural_language="ko")
        # Single syllable words should not split arbitrarily
        single = "면"
        assert session.mask(single) == gateway.GatewaySession(natural_language="ko").mask(single)


def test_no_protection_regression_all_stem_types_all_ending_classes():
    """Prove no protection regression across forced rules, domain terms, code mappings, and public forced stems."""
    ending_classes = {
        "conditional": ["면", "으면"],
        "sequence": ["기 전에", "기전에", "ㄴ 뒤에", "은 뒤에"],
        "negation": ["지 말고", "지말고", "지 마", "지마"],
        "request": ["세요", "해줘", "으세요", "해주세요"],
        "adnominal": ["ㄴ", "은", "된"],
    }

    with candidate_profile(309):
        # 1. Stem is a forced rule
        for cls_name, endings in ending_classes.items():
            for ending in endings:
                session = gateway.GatewaySession(natural_language="ko")
                session.forced_rules = lambda: ("비공개엔진",)
                text = f"비공개엔진{ending} 확인하세요."
                masked = session.mask(text)
                assert "비공개엔진" not in masked, f"Forced stem leaked: {masked}"
                assert ending in masked, f"Ending '{ending}' not in '{masked}'"
                assert session.restore(masked) == text, f"Restore mismatch: {masked}"

        # 2. Stem is a domain-dictionary term
        for cls_name, endings in ending_classes.items():
            for ending in endings:
                session = gateway.GatewaySession(natural_language="ko")
                text = f"전기도금{ending} 확인하세요."
                masked = session.mask(text)
                assert "전기도금" not in masked, f"Domain stem leaked: {masked}"
                assert ending in masked, f"Ending '{ending}' not in '{masked}'"
                assert session.restore(masked) == text, f"Restore mismatch: {masked}"

        # 3. Stem is an existing code/tool mapping
        for cls_name, endings in ending_classes.items():
            for ending in endings:
                session = gateway.GatewaySession(natural_language="ko")
                session.mask("def AlphaCore(): pass", code=True, language="python")
                text = f"AlphaCore{ending} 확인하세요."
                masked = session.mask(text)
                assert "AlphaCore" not in masked, f"Code mapping stem leaked: {masked}"
                assert ending in masked, f"Ending '{ending}' not in '{masked}'"
                assert session.restore(masked) == text, f"Restore mismatch: {masked}"

        # 4. Stem is both a public word and a forced rule
        for cls_name, endings in ending_classes.items():
            for ending in endings:
                session = gateway.GatewaySession(natural_language="ko")
                session.forced_rules = lambda: ("검토",)
                text = f"검토{ending} 확인하세요."
                masked = session.mask(text)
                assert "검토" not in masked, f"Public forced stem leaked: {masked}"
                assert ending in masked, f"Ending '{ending}' not in '{masked}'"
                assert session.restore(masked) == text, f"Restore mismatch: {masked}"
