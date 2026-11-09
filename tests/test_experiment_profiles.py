"""Isolated candidate activation and privacy precedence; no default adoption."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest

from secure_gateway import gateway


def request(text):
    return {"model": "fixture", "input": [{"role": "user", "content": text}]}


def test_profile_restores_globals_even_after_failure():
    from secure_gateway.experiment_profiles import candidate_profile
    before = gateway.GatewaySession, gateway.SharedEngine, gateway.ordinary_words
    with pytest.raises(RuntimeError):
        with candidate_profile(310):
            assert gateway.GatewaySession is not before[0]
            raise RuntimeError("interrupt")
    assert (gateway.GatewaySession, gateway.SharedEngine, gateway.ordinary_words) == before
    with pytest.raises(ValueError):
        with candidate_profile(999):
            pass


@pytest.mark.parametrize("issue,text,secret", [
    (310, "Project name: margin. Review it before approval.", "margin"),
    (312, "device_serial: 000812405; retry_count: 3", "000812405"),
    (317, "| Project | State |\n|---|---|\n| margin | waiting approval |", "margin"),
])
def test_add_protection_profiles_preserve_original(issue, text, secret):
    from secure_gateway.experiment_profiles import candidate_profile
    with candidate_profile(issue):
        session = gateway.GatewaySession(natural_language="en")
        masked = session.request(request(text))["input"][0]["content"]
        assert secret not in masked
        assert session.restore(masked) == text
        with pytest.raises(ValueError):
            session.restore("private_symbol_999999")


def test_korean_candidate_preserves_known_actions_but_forced_terms_win():
    from secure_gateway.experiment_profiles import candidate_profile
    text = "선반 높이를 모르면 먼저 물어보세요."
    with candidate_profile(309):
        session = gateway.GatewaySession(natural_language="ko")
        masked = session.mask(text)
        assert "모르면" in masked and "물어보세요" in masked
        assert session.restore(masked) == text
        session.forced_rules = lambda: ("물어보세요",)
        masked = session.mask(text)
        assert "물어보세요" not in masked and session.restore(masked) == text


def test_korean_candidate_protects_mapping_and_keeps_ordinary_domain_word_public():
    from secure_gateway.experiment_profiles import candidate_profile
    with candidate_profile(309):
        session = gateway.GatewaySession(natural_language="ko")
        session.mask("물어보세요", code=True)
        assert "물어보세요" not in session.mask("물어보세요")
        other = gateway.GatewaySession(natural_language="ko")
        other.engine.domain_spans = lambda text: [(0, len(text))]
        assert "모르면" in other.mask("모르면")
        other.forced_rules = lambda: ("모르면",)
        assert "모르면" not in other.mask("모르면")


def test_roles_are_opt_in_public_hints_and_never_alias_rewrites():
    from secure_gateway.experiment_profiles import candidate_profile
    payload = request("Reviewer: MirelQzx. Document: AspenQzx. Ask the reviewer to check it.")
    with candidate_profile(311, {"allow_roles": True}):
        session = gateway.GatewaySession(natural_language="en")
        masked = session.request(payload)
        assert "Role hints" in masked["instructions"]
        assert "MirelQzx" not in masked["instructions"] and "AspenQzx" not in masked["instructions"]
        assert session.restore(masked["input"][0]["content"]) == payload["input"][0]["content"]
    with candidate_profile(311, {"allow_roles": True, "confidential_roles": True}):
        assert "Role hints" not in gateway.GatewaySession().request(payload)["instructions"]


def test_segmented_language_keeps_cross_line_forced_phrase_private():
    from secure_gateway.experiment_profiles import candidate_profile
    with candidate_profile(313):
        session = gateway.GatewaySession()
        session.forced_rules = lambda: ("Blue\nMeadow",)
        source = "조건을 확인하세요.\nBlue\nMeadow\nDo not delete the original."
        masked = session.mask(source)
        assert "Blue" not in masked and "Meadow" not in masked
        assert session.restore(masked) == source


def test_conservative_vocabulary_is_a_subset_and_globally_restored():
    from secure_gateway.experiment_profiles import candidate_profile
    original = gateway.ordinary_words
    before = original("en")
    with candidate_profile(314):
        assert gateway.ordinary_words("en") <= before
        assert gateway.ordinary_words("en") != before
    assert gateway.ordinary_words is original


def test_instruction_candidate_does_not_change_masked_task():
    from secure_gateway.experiment_profiles import candidate_profile
    payload = request("Review EmberQzx. If approval is unknown, ask first; do not publish.")
    baseline = gateway.GatewaySession(natural_language="en").request(payload)
    with candidate_profile(315, {"variant": "concise"}):
        candidate = gateway.GatewaySession(natural_language="en").request(payload)
    assert candidate["input"] == baseline["input"]
    assert candidate["instructions"] != baseline["instructions"]
    assert "hidden numbers" in candidate["instructions"]


def test_scoped_correction_requires_explicit_trusted_binding():
    from secure_gateway.experiment_profiles import candidate_profile
    policy = {"workspace": "workspace-A", "trusted_project": "workspace-A", "language": "en",
              "policyrecords": [{"term": "meadow", "project": "workspace-A", "language": "en",
                                 "source": "explicit-local-correction",
                                 "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).timestamp(),
                                 "revoked": False}]}
    source = "Review meadow before publication."
    with candidate_profile(316, policy):
        session = gateway.GatewaySession(natural_language="en")
        masked = session.mask(source)
        assert "meadow" not in masked and session.restore(masked) == source
    policy["trusted_project"] = "workspace-B"
    with candidate_profile(316, policy):
        assert "meadow" in gateway.GatewaySession(natural_language="en").mask(source)


def test_bundle_scope_is_bound_to_original_whole_document():
    from secure_gateway.experiment_profiles import candidate_profile
    source = "Customer: Brook; Site: NorthQuay; Due: 2034-04-18; State: waiting approval"
    policy = {"document_sha256": sha256(source.encode()).hexdigest(), "scope": [0, len(source)],
              "required_fields": ["Customer", "Site", "Due"], "protect_fields": ["Customer", "Site", "Due"]}
    with candidate_profile(318, policy):
        session = gateway.GatewaySession(natural_language="en")
        masked = session.mask(source)
        assert "Brook" not in masked and "NorthQuay" not in masked and "2034-04-18" not in masked
        assert session.restore(masked) == source
        with pytest.raises(ValueError):
            session.mask(source + " changed")
