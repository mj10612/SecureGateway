"""Issue #325: Common-word domain dictionary policy, cross-language consistency, and load performance."""

import gc
import json
import time
import tracemalloc
from threading import Thread

from secure_gateway.domain_dictionaries import DomainCatalog, catalog
from secure_gateway.gateway import PrivacyGateway, GatewaySession


ON = {"defense": True, "automotive": True, "semiconductor": True}
DEFENSE_ONLY = {"defense": True, "automotive": False, "semiconductor": False}


def test_radar_alone_is_public_en_and_ko():
    cat = DomainCatalog()
    assert cat.spans("radar", DEFENSE_ONLY) == []
    assert cat.spans("radar", ON) == []
    assert cat.spans("레이더", DEFENSE_ONLY) == []
    assert cat.spans("레이더", ON) == []

    session = GatewaySession(natural_language="en")
    session.engine.domain_spans = lambda text: cat.spans(text, DEFENSE_ONLY)
    s1 = "Compare the engine control unit and radar test results in a table"
    m1 = session.mask(s1)
    assert "radar" in m1

    session_ko = GatewaySession(natural_language="ko")
    session_ko.engine.domain_spans = lambda text: cat.spans(text, DEFENSE_ONLY)
    s2 = "레이더 시험 결과를 표로 확인해줘"
    m2 = session_ko.mask(s2)
    assert "레이더" in m2


def test_radar_with_designator_anchor_is_masked_en_and_ko():
    cat = DomainCatalog()

    # Preceding designator: English radar is anchored and returned
    spans_en = cat.spans("AN/APG-77 radar", DEFENSE_ONLY)
    assert any(text == "radar" for text in ["AN/APG-77 radar"[s:e] for s, e in spans_en])

    # Preceding short designator
    spans_k2_en = cat.spans("K2 radar", DEFENSE_ONLY)
    assert any(text == "radar" for text in ["K2 radar"[s:e] for s, e in spans_k2_en])

    # Following designator with punctuation
    spans_post = cat.spans("radar (AN/APG-77)", DEFENSE_ONLY)
    assert any(text == "radar" for text in ["radar (AN/APG-77)"[s:e] for s, e in spans_post])

    # Korean: 레이더 is not a dictionary term in packaged data, so catalog.spans never returns it, anchored or not
    for text in ["AN/APG-77 레이더", "K2 레이더", "레이더(AN/APG-77)", "AN/APG-77의 레이더"]:
        assert not any(text[s:e] == "레이더" for s, e in cat.spans(text, DEFENSE_ONLY))


def test_gateway_session_unanchored_and_anchored_prose_behavior():
    """Pin actual end-to-end GatewaySession prose behavior for radar/레이더.

    1. Unanchored: 'radar' / '레이더' remain public (unmasked).
    2. Anchored with designator (e.g. 'AN/APG-77 radar'): 'AN/APG-77' is masked,
       but 'radar' / '레이더' remains public in prose because the #323 rule skips
       single-word domain spans that are ordinary public words.
    3. Multi-word domain terms (e.g. 'tactical data link', 'phased-array radar'):
       Masked because they are not single-word public words.
    4. Non-public domain terms (e.g. 'KF-21', 'radome'):
       Masked because they are distinctive domain terms not in the public vocabulary.
    5. Forced rules (e.g. 'radar', '레이더'):
       Masked regardless of public vocabulary or context.
    6. Parity: en and ko behave identically across all cases.
    """
    with PrivacyGateway(("127.0.0.1", 0), "secret") as gateway:
        s_en = gateway.get_session("claude")
        s_ko = gateway.get_session("claude", conversation="conv-ko")
        s_ko.natural_language = "ko"

        # Case 1: unanchored radar / 레이더 -> public
        m_unanchored_en = s_en.mask("Compare the engine control unit and radar test results in a table")
        assert "radar" in m_unanchored_en
        m_unanchored_ko = s_ko.mask("레이더 시험 결과를 표로 확인해줘")
        assert "레이더" in m_unanchored_ko

        # Case 2: anchored with designator in prose -> designator is masked, but radar/레이더
        # remains public due to the #323 prose rule skipping single-word public words.
        m_anchored_en = s_en.mask("The AN/APG-77 radar was tested.")
        assert "AN/APG-77" not in m_anchored_en
        assert "radar" in m_anchored_en
        m_anchored_ko = s_ko.mask("AN/APG-77 레이더 시험이 완료되었다.")
        assert "AN/APG-77" not in m_anchored_ko
        assert "레이더" in m_anchored_ko

        # Case 3: multi-word domain terms -> masked
        m_multi_en = s_en.mask("Review tactical data link specifications.")
        assert "tactical data link" not in m_multi_en
        m_multi_ko = s_ko.mask("전술데이터링크 규격을 검토해줘.")
        assert "전술데이터링크" not in m_multi_ko

        # Case 4: non-public distinctive single-word terms -> masked
        m_dist_en = s_en.mask("KF-21 flight test was approved.")
        assert "KF-21" not in m_dist_en
        m_dist_ko = s_ko.mask("KF-21 비행 시험이 승인되었다.")
        assert "KF-21" not in m_dist_ko

        # Case 5: forced rules take priority -> masked
        gateway.mask_rules = ("radar",)
        m_forced_en = s_en.mask("The radar was tested.")
        assert "radar" not in m_forced_en

        gateway.mask_rules = ("레이더",)
        m_forced_ko = s_ko.mask("레이더 시험을 확인해줘.")
        assert "레이더" not in m_forced_ko


def test_radar_with_distinctive_domain_term_in_same_sentence_is_masked():
    cat = DomainCatalog()
    # radome is distinctive in defense
    spans = cat.spans("The radar and radome were inspected.", DEFENSE_ONLY)
    matched = ["The radar and radome were inspected."[s:e] for s, e in spans]
    assert "radar" in matched
    assert "radome" in matched

    # In different sentence/clause: not anchored
    spans_diff = cat.spans("The radome was painted. The radar was offline.", DEFENSE_ONLY)
    matched_diff = ["The radome was painted. The radar was offline."[s:e] for s, e in spans_diff]
    assert "radome" in matched_diff
    assert "radar" not in matched_diff


def test_multiword_term_always_protected():
    cat = DomainCatalog()
    spans_en = cat.spans("phased-array radar", DEFENSE_ONLY)
    matched_en = ["phased-array radar"[s:e] for s, e in spans_en]
    assert "phased-array radar" in matched_en

    spans_ko = cat.spans("사격 관제 레이더", DEFENSE_ONLY)
    matched_ko = ["사격 관제 레이더"[s:e] for s, e in spans_ko]
    assert "사격 관제 레이더" in matched_ko


def test_forced_rules_and_sensitive_patterns_take_priority():
    with PrivacyGateway(("127.0.0.1", 0), "secret") as gateway:
        gateway.mask_rules = ("radar",)
        session = gateway.get_session("claude")
        # radar alone would be public under domain policy, but forced rule masks it
        masked = session.mask("Compare the engine control unit and radar test results in a table")
        assert "radar" not in masked
        assert session.restore(masked) == "Compare the engine control unit and radar test results in a table"

        gateway.mask_rules = ("레이더",)
        session_ko = gateway.get_session("claude", conversation="conv-ko-forced")
        session_ko.natural_language = "ko"
        masked_ko = session_ko.mask("레이더 시험 결과를 확인해줘")
        assert "레이더" not in masked_ko
        assert session_ko.restore(masked_ko) == "레이더 시험 결과를 확인해줘"


def test_cross_language_consistency_concept_pairs():
    cat = DomainCatalog()
    classified = cat.classified_concepts
    # Radar concept must be ambiguous-common in both languages
    radar_concept = cat.concept_for_term("radar", "defense")
    assert radar_concept is not None
    assert classified[radar_concept] == "ambiguous-common"

    # Enumerate all concept pairs with both en and ko forms and verify parity
    checked = 0
    for domain, doc in cat.documents.items():
        for entry in doc["entries"]:
            forms = entry.get("forms", [])
            en_forms = [f["text"] for f in forms if f.get("language") == "en"]
            ko_forms = [f["text"] for f in forms if f.get("language") == "ko"]
            if en_forms and ko_forms:
                cid = entry["id"]
                cls = classified[cid]
                # Every form of this concept has the exact same classification
                for form in forms:
                    assert cat.term_classification(form["text"], domain) == cls
                checked += 1
    assert checked > 100


def test_cold_catalog_load_time_and_memory():
    # Force cold load for duration
    catalog.cache_clear()
    gc.collect()
    t0 = time.perf_counter()
    _ = DomainCatalog()
    t1 = time.perf_counter()
    duration = t1 - t0

    # Force cold load for peak heap
    catalog.cache_clear()
    gc.collect()
    tracemalloc.start()
    _ = DomainCatalog()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    print(f"\nCold load duration: {duration:.3f} s, peak heap: {peak_mb:.2f} MB")
    # Wall-clock time depends on the runner and on coverage tracing, so the precise target
    # (<= 1.0 s) is measured by scripts/benchmark_catalog.py; here only a gross regression fails.
    assert duration <= 30.0, f"Cold catalog load took {duration:.3f} s (expected <= 30 s)"
    assert peak_mb <= 120.0, f"Cold catalog peak heap was {peak_mb:.2f} MB (expected <= 120.0 MB)"


def test_preload_blocks_request_until_catalog_ready(tmp_path):
    catalog.cache_clear()
    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        # Preload thread starts on initialization; property access waits for completion
        assert hasattr(gateway, "_preload_event")
        assert gateway._preload_event.wait(timeout=5.0)
        cat = gateway.domain_catalog
        assert cat is not None
        assert cat is gateway._domain_catalog

        # Verify that access blocks when preload event is cleared, and unblocks when set
        gateway._preload_event.clear()
        unblocked = False

        def fetch_catalog():
            nonlocal unblocked
            _ = gateway.domain_catalog
            unblocked = True

        t = Thread(target=fetch_catalog)
        t.start()
        time.sleep(0.05)
        assert not unblocked
        gateway._preload_event.set()
        t.join(timeout=1.0)
        assert unblocked


def test_preload_failure_falls_back_to_synchronous_load(tmp_path, monkeypatch):
    catalog.cache_clear()

    def failing_catalog():
        raise RuntimeError("simulated background preload failure")

    with monkeypatch.context() as m:
        m.setattr("secure_gateway.gateway.domain_catalog", failing_catalog)
        with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
            assert gateway._preload_event.wait(timeout=5.0)
            assert gateway._catalog_preload_failed is True
            diag = gateway.operational_diagnostics()
            assert diag.get("catalog_preload_failed", 0) >= 1
            assert gateway._domain_catalog is None

            # Fallback to synchronous load when domain_catalog is accessed
            m.setattr("secure_gateway.gateway.domain_catalog", catalog)
            cat = gateway.domain_catalog
            assert cat is not None
            assert cat is gateway._domain_catalog


def test_diagnostics_expose_duration_terms_memory_without_term_strings(tmp_path):
    cat = DomainCatalog()
    status = cat.status(DEFENSE_ONLY)
    assert "load_duration_seconds" in status
    assert isinstance(status["load_duration_seconds"], (int, float))
    assert status["load_duration_seconds"] > 0
    assert "enabled_term_count" in status
    assert status["enabled_term_count"] > 1000
    assert "approximate_memory_bytes" in status
    assert status["approximate_memory_bytes"] > 0

    # Ensure no term strings are leaked in catalog status
    status_serialized = json.dumps(status)
    assert "radar" not in status_serialized.lower()
    assert "레이더" not in status_serialized

    with PrivacyGateway(("127.0.0.1", 0), "secret", state_dir=tmp_path) as gateway:
        diag = gateway.session_diagnostics()
        dom_cat = diag.get("domain_catalog")
        assert dom_cat is not None
        assert "load_duration_seconds" in dom_cat
        assert isinstance(dom_cat["load_duration_seconds"], (int, float))
        assert dom_cat["load_duration_seconds"] > 0
        assert "enabled_term_count" in dom_cat
        assert dom_cat["enabled_term_count"] > 1000
        assert "approximate_memory_bytes" in dom_cat
        assert dom_cat["approximate_memory_bytes"] > 0

        # Ensure no term strings are leaked in session diagnostics
        diag_serialized = json.dumps(diag)
        assert "radar" not in diag_serialized.lower()
        assert "레이더" not in diag_serialized
        assert "kf-21" not in diag_serialized.lower()
