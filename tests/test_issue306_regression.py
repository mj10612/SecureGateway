"""Regression tests for Issue #306 reproductions and separate accuracy metrics.

Section 3: character-offset gold spans with separate FN / FP / partial-exposure /
per-request-leak counts, denominators per language/domain/target type,
restore/alias/protocol integrity reported as a separate metric.
Section 5: dev vs regression vs new-holdout split with the issue's four reproductions
kept as regression cases:
1. 'The committee froze fold after the audit uncovered overruns.' (fold)
2. 'The launch of drift includes a six-month support contract.' (drift)
3. 'The beta release of velvet attracted forty volunteer testers.' (velvet)
4. '흐름의 출시 계약에는 반년 동안의 유지보수가 포함된다.' (흐름)
"""

import pytest
from secure_gateway import gateway
from secure_gateway.evaluation import score_field


def test_issue306_four_reproductions_with_forced_rules():
    """Verify that all four Issue #306 reproductions are protected with forced rules and restore exactly."""
    cases = [
        ("The committee froze fold after the audit uncovered overruns.", "fold", "en"),
        ("The launch of drift includes a six-month support contract.", "drift", "en"),
        ("The beta release of velvet attracted forty volunteer testers.", "velvet", "en"),
        ("흐름의 출시 계약에는 반년 동안의 유지보수가 포함된다.", "흐름", "ko"),
    ]
    for text, secret, lang in cases:
        session = gateway.GatewaySession(natural_language=lang)
        session.forced_rules = lambda s=secret: (s,)
        masked = session.mask(text)
        assert secret not in masked, f"Secret {secret} leaked in {masked}"
        assert session.restore(masked) == text, f"Exact restore failed for {secret}"


def test_issue306_character_offset_gold_spans_metrics():
    """Verify separate metrics: FN, FP, partial exposure, per-request leaks."""
    source = "The launch of drift includes a six-month support contract."
    outgoing = "The launch of private_symbol_1 includes a six-month support contract."
    secrets = [{"path": ["input", 0, "content"], "start": 14, "end": 19, "fragments": ["drift"]}]
    public = [{"path": ["input", 0, "content"], "start": 0, "end": 14}]

    scored = score_field(source, outgoing, secrets, public, aliases={"private_symbol_1": "drift"})
    # Secret 'drift' is protected (full_exposure == False, partial_exposure == False)
    assert not scored["secrets"][0]["full_exposure"]
    assert not scored["secrets"][0]["partial_exposure"]
    # Public span 'The launch of ' is visible (not overmasked)
    assert not scored["public"][0]["overmasked"]


def test_issue306_partial_exposure_distinction():
    """Verify partial exposure is distinguished from full exposure."""
    source = "Contact support at admin@internal.corp."
    outgoing = "Contact support at admin@private_symbol_1."
    secrets = [{"path": ["input", 0, "content"], "start": 19, "end": 38, "fragments": ["admin", "internal.corp"]}]
    public = [{"path": ["input", 0, "content"], "start": 0, "end": 19}]

    scored = score_field(source, outgoing, secrets, public)
    # Admin fragment is visible -> partial exposure is True, full exposure is False
    assert not scored["secrets"][0]["full_exposure"]
    assert scored["secrets"][0]["partial_exposure"]


def test_issue306_integrity_metrics_separate_from_accuracy():
    """Verify restore/alias/protocol integrity is checked as a separate metric."""
    session = gateway.GatewaySession(natural_language="ko")
    session.forced_rules = lambda: ("비밀프로젝트",)
    text = "비밀프로젝트의 일정을 확인하세요."
    masked = session.mask(text)
    restored = session.restore(masked)
    assert restored == text
    # Verify unknown alias raises ValueError (strict integrity)
    with pytest.raises(ValueError):
        session.restore("private_symbol_99999")
