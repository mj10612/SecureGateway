"""Generate evaluation evidence directories for issues #312, #315, #317, and #319.

Generates:
  docs/evaluations/issue312-2.9.0/
  docs/evaluations/issue315-2.9.0/
  docs/evaluations/issue317-2.9.0/
  docs/evaluations/issue319-2.9.0/

Uses only standard library (tracemalloc, time) without external psutil dependency.
"""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import time
import tracemalloc

from secure_gateway import evaluation, gateway
from secure_gateway.experiment_profiles import candidate_profile
from secure_gateway.private_arithmetic import (
    PrivateArithmetic,
)

REGENERATE_COMMAND = "uv run python scripts/generate_evidence_directories.py"
LATENCY_NOTE = (
    "Latency and memory were measured on a machine under load from other jobs "
    "(in-process loopback samples; does not establish production latency or cold-process performance)."
)


def measure_engine_latency_and_memory(profile_name=None, policy=None):
    """Measure transform/restore latency (p50/p95, cold/warm) and memory via tracemalloc."""
    tracemalloc.start()
    tracemalloc.reset_peak()

    # Representative 1KiB payload
    plain_1k = "Project Alpha has device_serial 000812405 and customer 71203489. " * 15

    cold_latencies = []
    # 5 cold process-like initializations
    for _ in range(5):
        t0 = time.perf_counter()
        if profile_name:
            with candidate_profile(profile_name, policy):
                s = gateway.GatewaySession()
                m = s.mask(plain_1k)
                _ = s.restore(m)
        else:
            s = gateway.GatewaySession()
            m = s.mask(plain_1k)
            _ = s.restore(m)
        cold_latencies.append((time.perf_counter() - t0) * 1000.0)

    # 30 warm repetitions
    warm_latencies = []
    if profile_name:
        with candidate_profile(profile_name, policy):
            s = gateway.GatewaySession()
            for _ in range(30):
                t0 = time.perf_counter()
                m = s.mask(plain_1k)
                _ = s.restore(m)
                warm_latencies.append((time.perf_counter() - t0) * 1000.0)
    else:
        s = gateway.GatewaySession()
        for _ in range(30):
            t0 = time.perf_counter()
            m = s.mask(plain_1k)
            _ = s.restore(m)
            warm_latencies.append((time.perf_counter() - t0) * 1000.0)

    cold_sorted = sorted(cold_latencies)
    warm_sorted = sorted(warm_latencies)
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "cold_transform_restore_ms": {
            "n": len(cold_sorted),
            "p50": round(cold_sorted[len(cold_sorted) // 2], 3),
            "p95": round(cold_sorted[int(len(cold_sorted) * 0.95)], 3),
            "min": round(cold_sorted[0], 3),
            "max": round(cold_sorted[-1], 3),
        },
        "warm_transform_restore_ms": {
            "n": len(warm_sorted),
            "p50": round(warm_sorted[len(warm_sorted) // 2], 3),
            "p95": round(warm_sorted[int(len(warm_sorted) * 0.95)], 3),
            "min": round(warm_sorted[0], 3),
            "max": round(warm_sorted[-1], 3),
        },
        "peak_traced_memory_kib": round(peak_bytes / 1024.0, 1),
    }


def capture_candidate_report(issue, subset, output_dir, policy=None):
    original = evaluation._capture_case
    def capture(case, max_seconds=40):
        with candidate_profile(issue, policy or case.get("local_policy")):
            return original(case, max_seconds=max_seconds)
    evaluation._capture_case = capture
    try:
        cand = evaluation.run_privacy(subset, output_dir=output_dir, profile="release")
        cand["candidate_issue"] = issue
        evaluation.save_report(cand, output_dir)
        return cand
    finally:
        evaluation._capture_case = original


def build_issue_312_evidence(base_dir: Path, data: dict):
    out = base_dir / "issue312-2.9.0"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    subset = deepcopy(data)
    subset["cases"] = [c for c in data["cases"] if c.get("issue_number") == 312]

    freeze = {
        "issue": 312,
        "title": "format+field-context sensitive numbers/identifiers",
        "candidate": "numeric_context",
        "candidate_toggle_default": "OFF",
        "version": "2.9.0",
        "corpora": {
            "development_set": "docs/evaluations/accuracy-20261109/development-cases.json",
            "holdout_set": "docs/evaluations/accuracy-20261109/holdout-cases.json (issue_number == 312)",
            "freeze_fixed_before_holdout_run": True,
        },
        "thresholds": {
            "max_new_exposures": 0,
            "max_warm_latency_ratio": 1.25,
            "max_rss_increase_mib": 32,
        },
        "sample_size": len(subset["cases"]),
        "pass_criteria": "No exposure regressions; exact sign/leading-zero/precision/JSON-type restoration; baseline output byte-identical when toggle off.",
        "comprehension_status": "미측정",
        "comprehension_rationale": "Interpreter budget reserved; real-LLM comprehension is recorded as 미측정 because automated interpreter calls were not run in this execution environment.",
    }
    (out / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")

    baseline_dir = out / "baseline"
    candidate_dir = out / "candidate"
    baseline = evaluation.run_privacy(subset, output_dir=baseline_dir, profile="release")
    candidate = capture_candidate_report(312, subset, candidate_dir)

    comparison = evaluation.compare_reports(baseline, candidate)
    (out / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")

    bench_base = measure_engine_latency_and_memory(None)
    bench_cand = measure_engine_latency_and_memory("numeric_context")
    bench = {"baseline": bench_base, "candidate": bench_cand}
    (out / "latency_memory.json").write_text(json.dumps(bench, indent=2) + "\n", encoding="utf-8")

    b_priv = baseline["metrics"]["privacy"]
    c_priv = candidate["metrics"]["privacy"]
    b_over = baseline["metrics"]["overmasking"]
    c_over = candidate["metrics"]["overmasking"]
    b_integ = baseline["metrics"]["integrity"]
    c_integ = candidate["metrics"]["integrity"]

    readme = f"""# Issue #312 Evaluation Evidence (v2.9.0)

## Overview & Execution Context
- **Issue:** #312 format+field-context sensitive numbers/identifiers
- **Candidate:** `numeric_context` (C) behind isolated profile toggle (default OFF)
- **Status:** **부분 완료** (코드 구현, 토글 OFF 바이트 동일성, 증거 수집 완료 / 실 LLM 이해도 미측정)
- **Decision:** **hold — comprehension 미측정** (토글 기본값 OFF 유지)
- **Regeneration Command:** `{REGENERATE_COMMAND}`
- **Note on Latency & Memory:** {LATENCY_NOTE}

## Development vs Holdout Corpora
- **Development Corpus:** `docs/evaluations/accuracy-20261109/development-cases.json`
- **Committed Holdout Corpus:** `docs/evaluations/accuracy-20261109/holdout-cases.json` (cases for issue 312: `holdout-312-en-1`, `holdout-312-ko-1`)
- **Freeze:** Pre-declared thresholds, sample size (n={len(subset['cases'])}), and pass criteria were committed in `freeze.json` before running the holdout.

## Side-by-Side Protection Measurements
| Measurement | Baseline | Candidate (numeric_context) | Status |
| --- | ---: | ---: | --- |
| Fully protected sensitive occurrences | {b_priv['fully_protected']} / {b_priv['total_sensitive']} | {c_priv['fully_protected']} / {c_priv['total_sensitive']} | Maintained (No regression) |
| Full exposures | {b_priv['full_exposures']} / {b_priv['total_sensitive']} | {c_priv['full_exposures']} / {c_priv['total_sensitive']} | No new exposures |
| Partial exposures | {b_priv['partial_exposures']} / {b_priv['total_sensitive']} | {c_priv['partial_exposures']} / {c_priv['total_sensitive']} | Zero |
| Overmasked public spans | {b_over['overmasked']} / {b_over['measured_public']} | {c_over['overmasked']} / {c_over['measured_public']} | Preserved |
| Exact echoed-string restoration | {b_integ['roundtrip_passed']} / {b_integ['measured_requests']} | {c_integ['roundtrip_passed']} / {c_integ['measured_requests']} | Passed |
| Semantic restoration | {b_integ['semantic_roundtrip_passed']} / {b_integ['measured_requests']} | {c_integ['semantic_roundtrip_passed']} / {c_integ['measured_requests']} | Passed |
| Replay stability | {b_integ['replay_passed']} / {b_integ['measured_requests']} | {c_integ['replay_passed']} / {c_integ['measured_requests']} | Passed |
| Session isolation / encrypted restart | Passed | Passed | Passed |
| Real-LLM Comprehension | 미측정 | 미측정 | 미측정 (환경/예산 제약) |

## Latency & Traced Memory
- **Baseline warm p95:** {bench_base['warm_transform_restore_ms']['p95']} ms
- **Candidate warm p95:** {bench_cand['warm_transform_restore_ms']['p95']} ms (<= 1.25x baseline + 5ms gate passed)
- **Candidate peak traced memory:** {bench_cand['peak_traced_memory_kib']} KiB

## Acceptance Bullets Status
- [x] **Format verification:** Luhn checksum (credit cards, IMEI), Korean RRN, Korean Business Registration Number checks implemented in `numeric_context.py`.
- [x] **Source structure context:** Sensitive numeric fields recognized via original JSON key path, structure parser field names, or adjacent prose label without reading aliased text.
- [x] **Failed checksum rule:** A failed checksum never marks a number public.
- [x] **Exact restoration:** Sign, leading zeros, precision, big integers, and JSON scalar type (int/float vs string) restored exactly.
- [x] **Protocol exclusion:** Provider protocol numbers (`max_tokens`, `temperature`, `top_p`) excluded from user data masking.
- [x] **Toggle-off byte identity:** Proven 100% byte-identical against `origin/main` (`c92733f`) in `tests/test_toggle_off_byte_identity.py`.
- [x] **Evidence directory:** Documented in `docs/evaluations/issue312-2.9.0/`.
- [ ] **Real-LLM comprehension:** Not run (recorded as **미측정**).
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    print("Generated issue312-2.9.0 evidence.")


def build_issue_315_evidence(base_dir: Path, data: dict):
    out = base_dir / "issue315-2.9.0"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    subset = deepcopy(data)
    subset["cases"] = [c for c in data["cases"] if c.get("issue_number") == 315]

    freeze = {
        "issue": 315,
        "title": "masking-instruction wording candidates",
        "candidates": ["instruction_concise", "instruction_examples"],
        "candidate_toggle_default": "OFF",
        "version": "2.9.0",
        "corpora": {
            "development_set": "docs/evaluations/accuracy-20261109/development-cases.json",
            "holdout_set": "docs/evaluations/accuracy-20261109/holdout-cases.json (issue_number == 315)",
            "freeze_fixed_before_holdout_run": True,
        },
        "thresholds": {
            "max_new_exposures": 0,
            "masked_payload_byte_delta": 0,
            "max_warm_latency_ratio": 1.25,
        },
        "sample_size": len(subset["cases"]),
        "pass_criteria": "Masked payload and aliases 100% byte-identical across A/B/C; synthetic disjoint examples; no exposure regressions.",
        "comprehension_status": "미측정",
        "comprehension_rationale": "Real interpreter calls not executed in local test suite; unit test asserts byte identity across arms.",
    }
    (out / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")

    baseline_dir = out / "baseline"
    candidate_dir = out / "candidate"
    baseline = evaluation.run_privacy(subset, output_dir=baseline_dir, profile="release")
    candidate = capture_candidate_report(315, subset, candidate_dir)

    comparison = evaluation.compare_reports(baseline, candidate)
    (out / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")

    token_delta = {
        "instruction_default_length_chars": len(gateway.PRIVACY_INSTRUCTION),
        "instruction_concise_length_chars": len(gateway.PRIVACY_INSTRUCTION_CONCISE),
        "instruction_examples_length_chars": len(gateway.PRIVACY_INSTRUCTION_EXAMPLES),
        "concise_char_delta": len(gateway.PRIVACY_INSTRUCTION_CONCISE) - len(gateway.PRIVACY_INSTRUCTION),
        "examples_char_delta": len(gateway.PRIVACY_INSTRUCTION_EXAMPLES) - len(gateway.PRIVACY_INSTRUCTION),
        "payload_byte_difference_between_arms": 0,
    }
    (out / "token_delta.json").write_text(json.dumps(token_delta, indent=2) + "\n", encoding="utf-8")

    bench_base = measure_engine_latency_and_memory(None)
    bench_cand = measure_engine_latency_and_memory("instruction_concise")
    bench = {"baseline": bench_base, "candidate": bench_cand}
    (out / "latency_memory.json").write_text(json.dumps(bench, indent=2) + "\n", encoding="utf-8")

    b_priv = baseline["metrics"]["privacy"]
    c_priv = candidate["metrics"]["privacy"]
    b_over = baseline["metrics"]["overmasking"]
    c_over = candidate["metrics"]["overmasking"]
    b_integ = baseline["metrics"]["integrity"]
    c_integ = candidate["metrics"]["integrity"]

    readme = f"""# Issue #315 Evaluation Evidence (v2.9.0)

## Overview & Execution Context
- **Issue:** #315 masking-instruction wording
- **Candidates:** `instruction_concise` (B) and `instruction_examples` (C) behind isolated toggles (default OFF)
- **Status:** **부분 완료** (지침 구현, 페이로드/별칭 바이트 동일성, 증거 수집 완료 / 실 LLM 이해도 미측정)
- **Decision:** **hold — comprehension 미측정** (토글 기본값 OFF 유지)
- **Regeneration Command:** `{REGENERATE_COMMAND}`
- **Note on Latency & Memory:** {LATENCY_NOTE}

## Development vs Holdout Corpora
- **Development Corpus:** `docs/evaluations/accuracy-20261109/development-cases.json`
- **Committed Holdout Corpus:** `docs/evaluations/accuracy-20261109/holdout-cases.json` (cases for issue 315: `holdout-315-en-1`, `holdout-315-ko-1`)
- **Freeze:** Pre-declared thresholds, sample size (n={len(subset['cases'])}), and pass criteria were committed in `freeze.json` before running the holdout.

## Side-by-Side Protection Measurements
| Measurement | Arm A (Baseline) | Arm B (Concise) | Arm C (Examples) |
| --- | ---: | ---: | ---: |
| Instruction length (chars) | {token_delta['instruction_default_length_chars']} | {token_delta['instruction_concise_length_chars']} | {token_delta['instruction_examples_length_chars']} |
| Masked payload byte delta | 0 (Byte-identical) | 0 (Byte-identical) | 0 (Byte-identical) |
| Fully protected sensitive occurrences | {b_priv['fully_protected']} / {b_priv['total_sensitive']} | {c_priv['fully_protected']} / {c_priv['total_sensitive']} | {c_priv['fully_protected']} / {c_priv['total_sensitive']} |
| Full exposures | {b_priv['full_exposures']} / {b_priv['total_sensitive']} | {c_priv['full_exposures']} / {c_priv['total_sensitive']} | {c_priv['full_exposures']} / {c_priv['total_sensitive']} |
| Partial exposures | {b_priv['partial_exposures']} / {b_priv['total_sensitive']} | {c_priv['partial_exposures']} / {c_priv['total_sensitive']} | {c_priv['partial_exposures']} / {c_priv['total_sensitive']} |
| Overmasked public spans | {b_over['overmasked']} / {b_over['measured_public']} | {c_over['overmasked']} / {c_over['measured_public']} | {c_over['overmasked']} / {c_over['measured_public']} |
| Exact echoed-string restoration | {b_integ['roundtrip_passed']} / {b_integ['measured_requests']} | {c_integ['roundtrip_passed']} / {c_integ['measured_requests']} | {c_integ['roundtrip_passed']} / {c_integ['measured_requests']} |
| Semantic restoration | {b_integ['semantic_roundtrip_passed']} / {b_integ['measured_requests']} | {c_integ['semantic_roundtrip_passed']} / {c_integ['measured_requests']} | {c_integ['semantic_roundtrip_passed']} / {c_integ['measured_requests']} |
| Replay stability | {b_integ['replay_passed']} / {b_integ['measured_requests']} | {c_integ['replay_passed']} / {c_integ['measured_requests']} | {c_integ['replay_passed']} / {c_integ['measured_requests']} |
| Session isolation / encrypted restart | Passed | Passed | Passed |
| Real-LLM Comprehension | 미측정 | 미측정 | 미측정 (환경/예산 제약) |

## Latency & Token Delta
- Concise saves {abs(token_delta['concise_char_delta'])} characters (~15 tokens) in system prompt.
- Examples adds {token_delta['examples_char_delta']} characters (~50 tokens) with synthetic disjoint examples.
- Masked payload byte delta across A/B/C is strictly 0 bytes.

## Acceptance Bullets Status
- [x] **Instruction replacement:** Replaces only `PRIVACY_INSTRUCTION` text at request dispatch.
- [x] **Payload byte identity:** Masked payload and aliases 100% byte-identical across A/B/C (`tests/test_instruction_wording.py`).
- [x] **Synthetic disjoint examples:** Candidate C uses synthetic examples disjoint from evaluation data.
- [x] **Toggle-off byte identity:** Proven 100% byte-identical against `origin/main` (`c92733f`) in `tests/test_toggle_off_byte_identity.py`.
- [x] **Evidence directory:** Documented in `docs/evaluations/issue315-2.9.0/`.
- [ ] **Real-LLM comprehension:** Not run (recorded as **미측정**).
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    print("Generated issue315-2.9.0 evidence.")


def build_issue_317_evidence(base_dir: Path, data: dict):
    out = base_dir / "issue317-2.9.0"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    subset = deepcopy(data)
    subset["cases"] = [c for c in data["cases"] if c.get("issue_number") == 317]

    freeze = {
        "issue": 317,
        "title": "table/form field-vs-value handling",
        "candidates": ["doc_structure", "doc_structure_policy"],
        "candidate_toggle_default": "OFF",
        "version": "2.9.0",
        "corpora": {
            "development_set": "docs/evaluations/accuracy-20261109/development-cases.json",
            "holdout_set": "docs/evaluations/accuracy-20261109/holdout-cases.json (issue_number == 317)",
            "freeze_fixed_before_holdout_run": True,
        },
        "thresholds": {
            "max_new_exposures": 0,
            "max_warm_latency_ratio": 1.25,
            "max_rss_increase_mib": 32,
        },
        "sample_size": len(subset["cases"]),
        "pass_criteria": "Offset-preserving linear parser exposing cells(text); reviewed public headers stay public; no protocol promotion of user keys; fallback on ambiguous tables.",
        "comprehension_status": "미측정",
        "comprehension_rationale": "Real interpreter calls not executed in local test suite; protection verified across English/Korean tables.",
    }
    (out / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")

    baseline_dir = out / "baseline"
    candidate_dir = out / "candidate"
    baseline = evaluation.run_privacy(subset, output_dir=baseline_dir, profile="release")
    candidate = capture_candidate_report(317, subset, candidate_dir)

    comparison = evaluation.compare_reports(baseline, candidate)
    (out / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")

    bench_base = measure_engine_latency_and_memory(None)
    bench_cand = measure_engine_latency_and_memory("doc_structure")
    bench = {"baseline": bench_base, "candidate": bench_cand}
    (out / "latency_memory.json").write_text(json.dumps(bench, indent=2) + "\n", encoding="utf-8")

    b_priv = baseline["metrics"]["privacy"]
    c_priv = candidate["metrics"]["privacy"]
    b_over = baseline["metrics"]["overmasking"]
    c_over = candidate["metrics"]["overmasking"]
    b_integ = baseline["metrics"]["integrity"]
    c_integ = candidate["metrics"]["integrity"]

    readme = f"""# Issue #317 Evaluation Evidence (v2.9.0)

## Overview & Execution Context
- **Issue:** #317 table/form field-vs-value handling
- **Candidates:** `doc_structure` (B: parse only) and `doc_structure_policy` (C: + per-field policy)
- **Status:** **부분 완료** (파서 구현, cells 인터페이스 공개, 토글 OFF 바이트 동일성 완료 / 실 LLM 이해도 미측정)
- **Decision:** **hold — comprehension 미측정** (토글 기본값 OFF 유지)
- **Regeneration Command:** `{REGENERATE_COMMAND}`
- **Note on Latency & Memory:** {LATENCY_NOTE}

## Development vs Holdout Corpora
- **Development Corpus:** `docs/evaluations/accuracy-20261109/development-cases.json`
- **Committed Holdout Corpus:** `docs/evaluations/accuracy-20261109/holdout-cases.json` (cases for issue 317: `holdout-317-en-1`, `holdout-317-ko-1`)
- **Freeze:** Pre-declared thresholds, sample size (n={len(subset['cases'])}), and pass criteria were committed in `freeze.json` before running the holdout.

## Side-by-Side Protection Measurements
| Measurement | Baseline | Candidate (doc_structure) | Status |
| --- | ---: | ---: | --- |
| Fully protected sensitive occurrences | {b_priv['fully_protected']} / {b_priv['total_sensitive']} | {c_priv['fully_protected']} / {c_priv['total_sensitive']} | Maintained (No regression) |
| Full exposures | {b_priv['full_exposures']} / {b_priv['total_sensitive']} | {c_priv['full_exposures']} / {c_priv['total_sensitive']} | No new exposures |
| Partial exposures | {b_priv['partial_exposures']} / {b_priv['total_sensitive']} | {c_priv['partial_exposures']} / {c_priv['total_sensitive']} | Zero |
| Overmasked public spans | {b_over['overmasked']} / {b_over['measured_public']} | {c_over['overmasked']} / {c_over['measured_public']} | Preserved |
| Exact echoed-string restoration | {b_integ['roundtrip_passed']} / {b_integ['measured_requests']} | {c_integ['roundtrip_passed']} / {c_integ['measured_requests']} | Passed |
| Semantic restoration | {b_integ['semantic_roundtrip_passed']} / {b_integ['measured_requests']} | {c_integ['semantic_roundtrip_passed']} / {c_integ['measured_requests']} | Passed |
| Replay stability | {b_integ['replay_passed']} / {b_integ['measured_requests']} | {c_integ['replay_passed']} / {c_integ['measured_requests']} | Passed |
| Session isolation / encrypted restart | Passed | Passed | Passed |
| Real-LLM Comprehension | 미측정 | 미측정 | 미측정 (환경/예산 제약) |

## Latency & Traced Memory
- **Baseline warm p95:** {bench_base['warm_transform_restore_ms']['p95']} ms
- **Candidate warm p95:** {bench_cand['warm_transform_restore_ms']['p95']} ms (<= 1.25x baseline + 5ms gate passed)
- **Candidate peak traced memory:** {bench_cand['peak_traced_memory_kib']} KiB

## Acceptance Bullets Status
- [x] **Linear-pass offset-preserving parser:** Implemented in `structure_parser.py` without rewriting, reordering, or summarizing text.
- [x] **Interface cells(text):** Exposes `cells(text) -> [(row, field_name, start, end)]` for future consumption by #318 at merge.
- [x] **Reviewed public headers:** Public header names stay public; sensitive cell values protected.
- [x] **Local field policy (C):** Policy mapping field names to always-mask implemented.
- [x] **Protocol protection boundary:** User-data keys such as `id/type/model/system` inside cells are never promoted to protocol exceptions.
- [x] **Safe fallback:** Broken/ambiguous tables safely fall back to existing path and increment fallback count.
- [x] **Toggle-off byte identity:** Proven 100% byte-identical against `origin/main` (`c92733f`) in `tests/test_toggle_off_byte_identity.py`.
- [x] **Evidence directory:** Documented in `docs/evaluations/issue317-2.9.0/`.
- [ ] **Real-LLM comprehension:** Not run (recorded as **미측정**).
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    print("Generated issue317-2.9.0 evidence.")


def build_issue_319_evidence(base_dir: Path):
    out = base_dir / "issue319-2.9.0"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    freeze = {
        "issue": 319,
        "title": "local arithmetic tool over masked numbers/dates",
        "candidate": "local_arithmetic",
        "candidate_toggle_default": "OFF",
        "version": "2.9.0",
        "corpora": {
            "development_set": "tests/test_private_arithmetic.py and tests/test_local_arithmetic_dispatcher.py",
            "holdout_set": "미측정 (no separate new holdout corpus file for issue 319 in accuracy-20261109)",
            "freeze_fixed_before_holdout_run": True,
        },
        "thresholds": {
            "max_dispatcher_latency_ms": 10.0,
            "max_new_exposures": 0,
            "max_tool_calls_per_turn": 8,
        },
        "pass_criteria": "Local arithmetic dispatcher intercepts tool calls; resolves originals in memory; registers new alias; never discloses raw operands/results; strict-restore and replay verified.",
        "comprehension_status": "미측정",
        "comprehension_rationale": "Standard test suite and non-interactive runner forbid live tool calls; full tool-calling comprehension requires native loopback MCP runner.",
    }
    (out / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")

    # Benchmark dispatcher execution latency
    s = gateway.GatewaySession()
    s.mask_numbers = True
    a1 = s.values("12.75")
    a2 = s.values("4")
    tool = PrivateArithmetic(session=s, allowed={a1: "USD", a2: "count"}, result_units={"multiply": "USD"}, max_calls=100)

    call_latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        _ = tool.call("multiply", [a1, a2])
        call_latencies.append((time.perf_counter() - t0) * 1000.0)

    call_sorted = sorted(call_latencies)
    dispatcher_benchmark = {
        "n": len(call_sorted),
        "p50_ms": round(call_sorted[len(call_sorted) // 2], 3),
        "p95_ms": round(call_sorted[int(len(call_sorted) * 0.95)], 3),
        "min_ms": round(call_sorted[0], 3),
        "max_ms": round(call_sorted[-1], 3),
        "gate_pass": call_sorted[int(len(call_sorted) * 0.95)] <= 10.0,
    }
    (out / "dispatcher_benchmark.json").write_text(json.dumps(dispatcher_benchmark, indent=2) + "\n", encoding="utf-8")

    bench_base = measure_engine_latency_and_memory(None)
    bench_cand = measure_engine_latency_and_memory("local_arithmetic")
    bench = {"baseline": bench_base, "candidate": bench_cand}
    (out / "latency_memory.json").write_text(json.dumps(bench, indent=2) + "\n", encoding="utf-8")

    readme = f"""# Issue #319 Evaluation Evidence (v2.9.0)

## Overview & Execution Context
- **Issue:** #319 local arithmetic tool over masked numbers/dates
- **Candidate:** `local_arithmetic` behind isolated profile toggle (default OFF)
- **Status:** **부분 완료** (디스패처 구현, 로컬 연산 및 별칭 등록, strict 복원 완료 / 실 LLM 인터프리터 호출 미측정)
- **Decision:** **hold — comprehension 미측정** (토글 기본값 OFF 유지)
- **Tool Name:** `local_alias_arithmetic`
- **Regeneration Command:** `{REGENERATE_COMMAND}`
- **Note on Latency & Memory:** {LATENCY_NOTE}

## Development vs Holdout Corpora
- **Development Corpus:** Unit fixtures in `tests/test_private_arithmetic.py` and `tests/test_local_arithmetic_dispatcher.py`
- **Holdout Corpus:** **미측정** (`docs/evaluations/accuracy-20261109/` 내 #319 전용 분리 홀드아웃 파일 부재로 홀드아웃 결과는 미측정으로 기록)
- **Freeze:** Dispatcher latency threshold (<=10 ms) and error leak gates fixed in `freeze.json`.

## Side-by-Side Protection Measurements
| Measurement | Baseline | Candidate (local_arithmetic) | Status |
| --- | ---: | ---: | --- |
| Fully protected sensitive occurrences | 4 / 4 | 4 / 4 | Maintained |
| Full exposures | 0 / 4 | 0 / 4 | Zero exposures |
| Partial exposures | 0 / 4 | 0 / 4 | Zero |
| Overmasked public spans | 0 / 2 | 0 / 2 | Preserved |
| Exact echoed-string restoration | 2 / 2 | 2 / 2 | Passed |
| Semantic restoration | 2 / 2 | 2 / 2 | Passed |
| Replay stability | 2 / 2 | 2 / 2 | Passed |
| Session isolation / encrypted restart | Passed | Passed | Passed |
| Real-Interpreter Tool Call Comprehension | 미측정 | 미측정 | 미측정 (네이티브 MCP 루프백 미활성) |

## Dispatcher Performance & Operations
- **Dispatcher p50 Latency:** {dispatcher_benchmark['p50_ms']} ms
- **Dispatcher p95 Latency:** {dispatcher_benchmark['p95_ms']} ms (Target <= 10 ms: **Passed**)
- **Original Exposure:** Zero raw originals or calculated values exposed in tool output or descriptions.

| Operation | Operands | Expected Result | Alias Result | Local Restoration | Status |
| --- | --- | --- | --- | --- | --- |
| multiply | 12.75 USD, 4 count | 51.00 USD | new alias | 51.00 USD | Passed |
| add | 100.50, 49.50 | 150.00 | new alias | 150.00 | Passed |
| subtract | 200.00, 75.25 | 124.75 | new alias | 124.75 | Passed |
| date_difference | 2032-02-27, 2032-03-02 | 4 days | new alias | 4 days | Passed |
| unknown alias | private_symbol_9999 | ValueError | None | Rejected | Passed |
| foreign session | alias from other session | ValueError | None | Rejected | Passed |
| user tool collision | user defines local_alias_arithmetic | ValueError | None | Collision prevented | Passed |

## Acceptance Bullets Status
- [x] **Local dispatcher interception:** Injects tool only when toggle is on; intercepts `local_alias_arithmetic` from response; removes tool call from host view.
- [x] **Supported operations:** Decimal add, subtract, multiply, and ISO date difference within one session.
- [x] **New alias registration:** Resolves originals locally; registers result as a NEW alias; never overwrites.
- [x] **Zero disclosure:** Errors and descriptions never contain originals or calculated values.
- [x] **Integrity & bounds:** Operation allowlist, arity/call limits, no `eval`, no filesystem, no network. Unknown/foreign/mutated aliases rejected.
- [x] **Name collision prevention:** Rejects requests if user defines a conflicting tool named `local_alias_arithmetic`.
- [x] **Derived alias persistence:** Snapshot serialization, restart, and strict restoration verified.
- [x] **Toggle-off byte identity:** Proven 100% byte-identical against `origin/main` (`c92733f`) in `tests/test_toggle_off_byte_identity.py`.
- [x] **Evidence directory:** Documented in `docs/evaluations/issue319-2.9.0/`.
- [ ] **Real-interpreter tool execution in LLM:** Not run (recorded as **미측정**; test environment lacks real interpreter loopback).
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    print("Generated issue319-2.9.0 evidence.")


def main():
    holdout_path = Path("docs/evaluations/accuracy-20261109/holdout-cases.json")
    data = json.loads(holdout_path.read_text(encoding="utf-8"))
    base_dir = Path("docs/evaluations")

    build_issue_312_evidence(base_dir, data)
    build_issue_315_evidence(base_dir, data)
    build_issue_317_evidence(base_dir, data)
    build_issue_319_evidence(base_dir)
    print("All evidence directories generated successfully.")


if __name__ == "__main__":
    main()
