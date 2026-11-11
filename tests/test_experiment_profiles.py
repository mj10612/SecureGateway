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


def test_bundle_table_requires_fields_in_same_row():
    from secure_gateway.experiment_profiles import candidate_profile
    source = "| Customer | Site | Due |\n|---|---|---|\n| meadow | quay | 2034-04-18 |\n| grove | | 2035-01-01 |"
    policy = {"document_sha256": sha256(source.encode()).hexdigest(), "scope": [0, len(source)],
              "required_fields": ["Customer", "Site", "Due"], "protect_fields": ["Customer"]}
    from secure_gateway.experiment_bundle import bundle_spans
    assert [source[start:end] for start, end in bundle_spans(source, policy)] == ["meadow"]
    with candidate_profile(318, policy):
        session = gateway.GatewaySession(natural_language="en")
        masked = session.mask(source)
        assert "meadow" not in masked
        assert session.restore(masked) == source


@pytest.mark.parametrize("issue,policy", [
    (310, {}),
    (311, {"allow_roles": True}),
    (316, {"trusted_project": "p", "workspace": "p", "language": "en", "policyrecords": []}),
    (318, {}),
])
def test_profile_off_matches_frozen_baseline_bytes(issue, policy):
    import json
    from secure_gateway.experiment_profiles import candidate_profile

    with candidate_profile(issue, policy):
        pass
    payload = request("Review EmberQzx. If approval is unknown, ask first; do not publish.")
    result = gateway.GatewaySession(natural_language="en").request(payload)
    encoded = json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    assert sha256(encoded).hexdigest() == "a904367ef76f8571e15b5876ad46f5c5d195ac93fca329451aec4ca2a7859043"


def test_name_context_session_scope_and_controls():
    from secure_gateway.experiment_profiles import candidate_profile

    with candidate_profile(310):
        session = gateway.GatewaySession(natural_language="en")
        first = session.request(request("Project name: drift. Review it."))["input"][0]["content"]
        later = session.request(request("Check drift before release."))["input"][0]["content"]
        assert "drift" not in first and "drift" not in later
        assert session.restore(later) == "Check drift before release."
        other = gateway.GatewaySession(natural_language="en")
        assert "drift" in other.request(request("Watch physical drift."))["input"][0]["content"]
        korean = gateway.GatewaySession(natural_language="ko")
        assert "흐름" in korean.mask("업무 흐름을 설명해 주세요.")
        named = korean.request(request("프로젝트명은 흐름. 확인하세요."))["input"][0]["content"]
        assert "흐름" not in named


def test_name_context_does_not_register_quoted_or_tool_introductions():
    from secure_gateway.experiment_profiles import candidate_profile

    tool = {"model": "fixture", "input": [{"role": "tool", "content": "Project name: drift"}]}
    baseline = gateway.GatewaySession(natural_language="en")
    baseline.request(tool)
    baseline_followup = baseline.request(request("Watch physical drift."))
    with candidate_profile(310):
        session = gateway.GatewaySession(natural_language="en")
        session.request(request('A document says "Project name: drift". Summarize it.'))
        assert "drift" in session.request(request("Watch physical drift."))["input"][0]["content"]
        other = gateway.GatewaySession(natural_language="en")
        other.request(tool)
        assert other.request(request("Watch physical drift.")) == baseline_followup


def test_role_hints_ignore_tool_results_and_quoted_data():
    from secure_gateway.experiment_profiles import candidate_profile

    tool = {"model": "fixture", "input": [{"role": "tool", "content": "Reviewer: MirelQzx"}]}
    quoted = request('The document says "Reviewer: MirelQzx"; summarize it.')
    with candidate_profile(311, {"allow_roles": True}):
        for payload in (tool, quoted):
            result = gateway.GatewaySession(natural_language="en").request(payload)
            assert "Role hints" not in result["instructions"]


def test_correction_encrypted_persistence_scope_and_expiry(tmp_path):
    from secure_gateway.experiment_corrections import load_records, save_record
    from secure_gateway.experiment_profiles import candidate_profile

    now = datetime.now(timezone.utc).timestamp()
    record = {"term": "meadow", "project": "alpha", "language": "en",
              "source": "explicit-local-correction", "policy_version": 1,
              "created_at": now, "expires_at": now + 3600, "revoked": False}
    path = tmp_path / "corrections.enc"
    save_record(path, "secret-passphrase", record)
    assert b"meadow" not in path.read_bytes()
    records = load_records(path, "secret-passphrase")
    assert records == [record]
    policy = {"trusted_project": "alpha", "workspace": "alpha", "language": "en", "policyrecords": records}
    with candidate_profile(316, policy):
        masked = gateway.GatewaySession(natural_language="en").mask("Review meadow tomorrow.")
        assert "meadow" not in masked
    records[0]["revoked"] = True
    policy["policyrecords"] = records
    with candidate_profile(316, policy):
        assert "meadow" in gateway.GatewaySession(natural_language="en").mask("Review meadow tomorrow.")
    with pytest.raises(ValueError):
        load_records(path, "wrong-passphrase")


def test_correction_cli_saves_only_when_explicit(tmp_path):
    from click.testing import CliRunner
    from secure_gateway.cli import main
    from secure_gateway.experiment_corrections import load_records

    path = tmp_path / "policy.enc"
    runner = CliRunner()
    args = ["corrections", "save", "--file", str(path), "--project", "alpha", "--language", "en"]
    denied = runner.invoke(main, args, input="meadow\npassphrase\n")
    assert denied.exit_code != 0 and not path.exists()
    saved = runner.invoke(main, args + ["--yes"], input="meadow\npassphrase\n")
    assert saved.exit_code == 0
    assert "meadow" not in saved.output
    assert load_records(path, "passphrase")[0]["term"] == "meadow"


def test_role_hint_accepts_explicit_project_name_introduction():
    from secure_gateway.experiment_profiles import candidate_profile

    with candidate_profile(311, {"allow_roles": True}):
        result = gateway.GatewaySession(natural_language="en").request(request("Project name: MirelQzx. Review it."))
        assert "=project" in result["instructions"]


def test_correction_conflict_expiry_revocation_and_restart(tmp_path):
    from secure_gateway.experiment_corrections import load_records, revoke_record, save_record
    from secure_gateway.experiment_profiles import candidate_profile

    now = datetime.now(timezone.utc).timestamp()
    record = {"term": "meadow", "project": "alpha", "language": "en",
              "source": "explicit-local-correction", "policy_version": 1,
              "created_at": now - 100, "expires_at": now - 1, "revoked": False}
    path = tmp_path / "policy.enc"
    save_record(path, "passphrase", record)
    with pytest.raises(ValueError):
        save_record(path, "passphrase", record)
    policy = {"trusted_project": "alpha", "workspace": "alpha", "language": "en",
              "policyrecords": load_records(path, "passphrase")}
    with candidate_profile(316, policy):
        session = gateway.GatewaySession(natural_language="en")
        assert "meadow" in session.mask("Review meadow tomorrow.")
        session.forced_rules = lambda: ("meadow",)
        assert "meadow" not in session.mask("Review meadow tomorrow.")
    revoke_record(path, "passphrase", "alpha", "en", "meadow")
    assert load_records(path, "passphrase")[0]["revoked"] is True


def test_name_introduced_quoted_value_and_budget():
    from secure_gateway.experiment_name_context import trusted_name_spans

    text = 'Customer named "Silver Oak" requested review.'
    assert [text[start:end] for start, end in trusted_name_spans(text)] == ["Silver Oak"]
    quoted = "Document: 'Project name: drift'"
    assert trusted_name_spans(quoted) == []
    oversized = " ".join("Project name: drift." for _ in range(129))
    assert trusted_name_spans(oversized) == []


def test_role_hint_combines_with_name_context_without_alias_rewrite():
    from secure_gateway.experiment_profiles import candidate_profile

    with candidate_profile(311, {"allow_roles": True, "with_name_context": True}):
        session = gateway.GatewaySession(natural_language="en")
        result = session.request(request("Project name: drift. Review it."))
        assert "drift" not in result["input"][0]["content"]
        assert "private_symbol_1=project" in result["instructions"]
        assert session.restore(result["input"][0]["content"]) == "Project name: drift. Review it."


def test_scoped_public_exception_never_overrides_protection():
    from secure_gateway.experiment_profiles import candidate_profile

    future = (datetime.now(timezone.utc) + timedelta(days=1)).timestamp()
    def record(term):
        return {"term": term, "project": "alpha", "language": "en", "source": "explicit-local-correction",
                "expires_at": future, "revoked": False}
    policy = {"trusted_project": "alpha", "workspace": "alpha", "language": "en", "policyrecords": [],
              "public_records": [record("Mirel")]}
    with candidate_profile(316, policy):
        session = gateway.GatewaySession(natural_language="en")
        assert "Mirel" in session.mask("Review Mirel tomorrow.")
        forced = gateway.GatewaySession(natural_language="en")
        forced.forced_rules = lambda: ("Mirel",)
        assert "Mirel" not in forced.mask("Review Mirel tomorrow.")
        known = gateway.GatewaySession(natural_language="en")
        known.mask("Mirel", code=True)
        assert "Mirel" not in known.mask("Review Mirel tomorrow.")
        assert "Mirel" not in gateway.GatewaySession(natural_language="en").mask("Email Mirel@example.test")
        domain = gateway.GatewaySession(natural_language="en")
        domain.engine.domain_spans = lambda text: [(text.index("Mirel"), text.index("Mirel") + 5)]
        assert "Mirel" not in domain.mask("Review Mirel tomorrow.")
    policy["policyrecords"] = [record("Mirel")]
    with candidate_profile(316, policy):
        assert "Mirel" not in gateway.GatewaySession(natural_language="en").mask("Review Mirel tomorrow.")
    policy["policyrecords"] = []
    policy["workspace"] = "different"
    with candidate_profile(316, policy):
        assert "Mirel" not in gateway.GatewaySession(natural_language="en").mask("Review Mirel tomorrow.")


def test_public_exception_does_not_change_tool_payloads():
    from secure_gateway.experiment_profiles import candidate_profile

    future = (datetime.now(timezone.utc) + timedelta(days=1)).timestamp()
    record = {"term": "Mirel", "project": "alpha", "language": "en", "source": "explicit-local-correction",
              "expires_at": future, "revoked": False}
    policy = {"trusted_project": "alpha", "workspace": "alpha", "language": "en", "policyrecords": [],
              "public_records": [record]}
    tool = {"model": "fixture", "input": [{"role": "tool", "content": "Review Mirel tomorrow."}]}
    baseline = gateway.GatewaySession(natural_language="en").request(tool)
    with candidate_profile(316, policy):
        assert gateway.GatewaySession(natural_language="en").request(tool) == baseline
        user = gateway.GatewaySession(natural_language="en").request(request("Review Mirel tomorrow."))
        assert "Mirel" in user["input"][0]["content"]


def test_bundle_cells_interface_includes_form_and_table_values():
    from secure_gateway.experiment_bundle import cells

    source = "Customer: Brook\nSite: North\n| Customer | Site |\n|---|---|\n| Willow | South |"
    records = [(row, name, source[start:end]) for row, name, start, end in cells(source)]
    assert any(name.casefold() == "customer" and value == "Brook" for _, name, value in records)
    assert any(name.casefold() == "site" and value == "North" for _, name, value in records)
    assert any(name.casefold() == "customer" and value == "Willow" for _, name, value in records)


def test_name_context_korean_copula_is_not_part_of_the_name():
    from secure_gateway.experiment_name_context import trusted_name_spans
    from secure_gateway.experiment_profiles import candidate_profile

    source = "프로젝트명은 흐름입니다. 확인하세요."
    assert [source[start:end] for start, end in trusted_name_spans(source)] == ["흐름"]
    with candidate_profile(310):
        session = gateway.GatewaySession(natural_language="ko")
        masked = session.request(request(source))["input"][0]["content"]
        assert "흐름" not in masked
        assert "입니다" in masked
        assert session.restore(masked) == source


def test_role_declarations_have_bounded_input_and_candidates():
    from secure_gateway.experiment_name_context import role_declarations
    from secure_gateway.experiment_profiles import _ROLE_FIELD

    assert role_declarations("x" * (1024 * 1024 + 1), _ROLE_FIELD) == []
    text = " ".join("Reviewer: Mirel." for _ in range(100))
    assert len(role_declarations(text, _ROLE_FIELD)) == 64
