"""Domain policy precedence, persistence and indexed span matching."""

import itertools
import json
import unicodedata

import pytest

from secure_gateway.gateway import PrivacyGateway


def test_default_defense_is_on_and_persists_explicit_off(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "local-secret", state_dir=tmp_path) as gateway:
        assert gateway.domain_status()["enabled"] == {"defense": True, "automotive": False, "semiconductor": False}
        session = gateway.get_session("codex")
        text = "Please review the tactical data link before approval."
        masked = session.mask(text)
        assert "tactical data link" not in masked
        assert session.restore(masked) == text
        gateway.set_domain_policy({"defense": False, "automotive": True, "semiconductor": False})
        assert session.restore(masked) == text
    with PrivacyGateway(("127.0.0.1", 0), "local-secret", state_dir=tmp_path) as gateway:
        assert gateway.domain_status()["enabled"]["defense"] is False
        assert gateway.domain_status()["enabled"]["automotive"] is True


@pytest.mark.parametrize("flags", list(itertools.product([False, True], repeat=3)))
def test_all_policy_combinations_and_exact_originals(flags):
    from secure_gateway.domain_dictionaries import DomainCatalog
    catalog = DomainCatalog()
    policy = dict(zip(("defense", "automotive", "semiconductor"), flags))
    text = "tactical data link; battery management system; atomic layer deposition"
    spans = catalog.spans(text, policy)
    protected = [text[start:end] for start, end in spans]
    for term, enabled in zip(text.split("; "), flags):
        assert (term in protected) is enabled


def test_matcher_unicode_hyphen_longest_acronym_and_budget():
    from secure_gateway.domain_dictionaries import DomainCatalog
    catalog = DomainCatalog()
    policy = {"defense": True, "automotive": True, "semiconductor": True}
    for text in ["전술데이터링크를 검토", unicodedata.normalize("NFD", "전술데이터링크를 검토"), "TACTICAL-DATA-LINK", "AESA radar"]:
        assert catalog.spans(text, policy), text
    assert not catalog.spans("candy can be useful", policy)
    assert catalog.spans("CAN", policy)
    with pytest.raises(ValueError, match="budget"):
        catalog.spans("AESA " * 100, policy, max_matches=10)


def test_policy_update_is_atomic_and_refuses_active_requests(tmp_path, monkeypatch):
    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        before = gateway.domain_status()
        assert gateway.try_admit("codex")
        with pytest.raises(ValueError):
            gateway.set_domain_policy({"defense": False, "automotive": False, "semiconductor": False})
        gateway.release_admission("codex")
        import secure_gateway.gateway_install as install
        monkeypatch.setattr(install, "atomic_bytes", lambda *_: (_ for _ in ()).throw(OSError("disk")))
        with pytest.raises(OSError):
            gateway.set_domain_policy({"defense": False, "automotive": False, "semiconductor": False})
        assert gateway.domain_status() == before


def test_enabled_dictionary_corruption_blocks_startup(tmp_path):
    from secure_gateway.domain_dictionaries import DomainCatalog
    with pytest.raises(ValueError):
        DomainCatalog(directory=tmp_path)


def test_dictionary_does_not_weaken_url_or_forced_rules():
    with PrivacyGateway(("127.0.0.1", 0), "secret") as gateway:
        session = gateway.get_session("codex")
        gateway.mask_rules = ("review",)
        text = "review https://example.invalid/tactical-data-link/private-query"
        masked = session.mask(text)
        assert "example.invalid" not in masked and "review" not in masked
        assert session.restore(masked) == text
        assert "private-query" not in masked


def test_catalog_pages_are_bounded_without_bulk_payload():
    from secure_gateway.domain_dictionaries import DomainCatalog
    catalog = DomainCatalog()
    page = catalog.page("defense", query="radar", limit=3)
    assert len(page["entries"]) <= 3 and page["total"] >= 1
    assert "candidate_records" not in json.dumps(page)


@pytest.mark.parametrize("term", ["KF-21", "LongShot", "Manta Ray", "Project 1143.7 aircraft carrier", "radome", "탐색기", "구동장치", "전원공급장치"])
def test_defense_named_programs_and_subcomponents_are_active(term):
    from secure_gateway.domain_dictionaries import DomainCatalog
    catalog = DomainCatalog()
    assert catalog.spans("검토 대상 " + term + " 확인", {"defense": True}), term


def test_source_entities_and_core_concepts_are_counted_separately():
    from secure_gateway.domain_dictionaries import DomainCatalog
    catalog = DomainCatalog()
    defense = catalog.documents["defense"]["counts"]
    assert defense["active_concepts"] > 1000
    assert defense["editorial_core_concepts"] >= 100


def test_crossing_private_terms_protect_their_union():
    from secure_gateway.domain_dictionaries import TermIndex
    index = TermIndex([("radar sensor", "defense", False, "word"),
                       ("sensor array", "defense", False, "word")])
    text = "radar sensor array"
    assert index.spans(text, {"defense": True}) == [(0, len(text))]


def test_toggle_cache_invalidation_survives_concurrent_registry_removal(tmp_path):
    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        first, second = gateway.get_session("codex"), gateway.get_session("claude")
        class RemovingCache(dict):
            def clear(self):
                gateway.sessions.pop("codex", None)
                super().clear()
        first._mask_cache = RemovingCache()
        second._mask_cache[("old",)] = "old unprotected value"
        gateway.set_domain_policy({"defense": False, "automotive": True, "semiconductor": False})
        assert not second._mask_cache
        assert '"automotive": true' in second.domain_policy_version
        first.session.clear()
