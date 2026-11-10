"""Committed benchmark runner for language-side accuracy experiments (v2.10.0).

Measures actual masking latency (cold and warm p50/p95) across 100 iterations on holdout corpora.
Records full machine information and writes benchmark.json per issue.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from secure_gateway import gateway
from secure_gateway.experiment_profiles import candidate_profile

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "docs" / "evaluations"
ITERATIONS = 100
WARMUP = 20


def get_machine_info():
    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "run_count": ITERATIONS,
        "warmup_runs": WARMUP,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def measure_session_latency(session_factory, sentences: list[str]):
    # Cold measurement (first fresh session call)
    cold_times = []
    for s in sentences:
        sess = session_factory()
        t0 = time.perf_counter()
        sess.mask(s)
        cold_times.append((time.perf_counter() - t0) * 1000)

    cold_times.sort()
    cold_p50 = cold_times[len(cold_times) // 2]
    cold_p95 = cold_times[int(len(cold_times) * 0.95)]

    # Warm measurement (reusing session over WARMUP + ITERATIONS)
    sess = session_factory()
    for _ in range(WARMUP):
        for s in sentences:
            sess.mask(s)

    warm_times = []
    for _ in range(ITERATIONS):
        for s in sentences:
            t0 = time.perf_counter()
            sess.mask(s)
            warm_times.append((time.perf_counter() - t0) * 1000)

    warm_times.sort()
    warm_p50 = warm_times[len(warm_times) // 2]
    warm_p95 = warm_times[int(len(warm_times) * 0.95)]
    warm_mean = statistics.mean(warm_times)

    return {
        "cold_p50_ms": round(cold_p50, 4),
        "cold_p95_ms": round(cold_p95, 4),
        "warm_p50_ms": round(warm_p50, 4),
        "warm_p95_ms": round(warm_p95, 4),
        "warm_mean_ms": round(warm_mean, 4),
    }


def benchmark_issue(issue: int):
    issue_dir = EVAL_DIR / f"issue{issue}-2.10.0"
    corpus_file = issue_dir / ("multilingual_corpus.json" if issue == 291 else "holdout_corpus.json")
    if not corpus_file.exists():
        print(f"Skipping issue {issue}: {corpus_file.name} missing")
        return

    corpus_data = json.loads(corpus_file.read_text(encoding="utf-8"))
    sentences = [c["text"] for c in corpus_data["cases"]]

    print(f"\nBenchmarking Issue #{issue} ({len(sentences)} holdout sentences, {ITERATIONS} runs)...")

    # Baseline
    b_perf = measure_session_latency(lambda: gateway.GatewaySession(natural_language="auto"), sentences)

    cand_results = {}
    if issue == 309:
        with candidate_profile(309):
            c_perf = measure_session_latency(lambda: gateway.GatewaySession(natural_language="ko"), sentences)
            cand_results["ko_conjugation_split"] = c_perf
    elif issue == 313:
        with candidate_profile(313):
            c_perf = measure_session_latency(lambda: gateway.GatewaySession(natural_language="auto"), sentences)
            cand_results["segment_language"] = c_perf
    elif issue == 314:
        with candidate_profile(314, {"variant": "conservative"}):
            c_b_perf = measure_session_latency(lambda: gateway.GatewaySession(natural_language="auto"), sentences)
            cand_results["vocab_conservative"] = c_b_perf
        with candidate_profile(314, {"variant": "calibrated"}):
            c_c_perf = measure_session_latency(lambda: gateway.GatewaySession(natural_language="auto"), sentences)
            cand_results["vocab_calibrated"] = c_c_perf
    elif issue == 306:
        with candidate_profile(309):
            c_perf = measure_session_latency(lambda: gateway.GatewaySession(natural_language="ko"), sentences)
            cand_results["umbrella_metrics"] = c_perf
    elif issue == 291:
        # Default engine multilingual verification
        c_perf = measure_session_latency(lambda: gateway.GatewaySession(natural_language="auto"), sentences)
        cand_results["default_engine_multilingual"] = c_perf

    benchmark_data = {
        "issue": issue,
        "version": "2.10.0",
        "machine_info": get_machine_info(),
        "baseline": b_perf,
        "candidates": cand_results,
        "memory_delta_mb": "미측정",
        "memory_note": "Per-request memory delta cannot be isolated deterministically without external OS process boundaries.",
    }

    out_file = issue_dir / "benchmark.json"
    out_file.write_text(json.dumps(benchmark_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Benchmark saved to {out_file}")
    print(f"  Baseline warm p50: {b_perf['warm_p50_ms']} ms, p95: {b_perf['warm_p95_ms']} ms")
    for name, perf in cand_results.items():
        print(f"  Candidate ({name}) warm p50: {perf['warm_p50_ms']} ms, p95: {perf['warm_p95_ms']} ms")


def main():
    print("=" * 70)
    print("Running Language Accuracy Latency Benchmarks (100 runs)")
    print("=" * 70)
    for issue in [309, 313, 314, 306, 291]:
        benchmark_issue(issue)
    print("\n" + "=" * 70)
    print("All benchmarks finished.")
    print("=" * 70)


if __name__ == "__main__":
    main()
