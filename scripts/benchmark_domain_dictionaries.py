"""Synthetic index scale is separate from curated concept coverage."""
import argparse
from hashlib import sha256
import json
import platform
import re
import statistics
import time
import tracemalloc
from pathlib import Path

from secure_gateway.domain_dictionaries import DomainCatalog, TermIndex


def measure(call, repeats):
    samples = []
    value = None
    for _ in range(repeats):
        start = time.perf_counter()
        value = call()
        samples.append((time.perf_counter() - start) * 1000)
    return {"p50_ms": statistics.median(samples), "max_ms": max(samples),
            "p95_ms": None if repeats < 20 else sorted(samples)[int(.95 * (repeats - 1))],
            "p99_ms": None if repeats < 100 else sorted(samples)[int(.99 * (repeats - 1))],
            "samples": repeats, "result_count": len(value) if isinstance(value, list) else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    policy = {"defense": True, "automotive": True, "semiconductor": True}
    report = {"hardware": platform.platform(), "python": platform.python_version(),
              "thresholds_predeclared": {"one_kib_default_extra_p95_ms": 25, "synthetic_100k_index_peak_mib": 512,
                                          "one_mib_scan_max_ms": 10000},
              "tail_note": "p95 requires20 samples; p99 requires100. Shared host timings are not SLAs.", "curated": {}, "synthetic": []}
    start = time.perf_counter()
    catalog = DomainCatalog()
    report["curated"]["load_build_ms"] = (time.perf_counter() - start) * 1000
    report["curated"]["manifest_hash"] = catalog.version
    report["curated"]["counts"] = catalog.status(policy)["domains"]
    for size in (1024, 10240, 102400, 1048576):
        text = ("Please review the report before approval. " * (size // 40 + 1))[:size]
        report["curated"][str(size)] = measure(lambda: catalog.spans(text, policy), args.repeats)
    for count in (1000, 10000, 100000):
        terms = [(f"syntheticcomponent{index:06d}", "defense", False, "word") for index in range(count)]
        tracemalloc.start()
        start = time.perf_counter()
        index = TermIndex(terms)
        elapsed = (time.perf_counter() - start) * 1000
        peak = tracemalloc.get_traced_memory()[1] / 1024 ** 2
        tracemalloc.stop()
        row = {"strings": count, "build_ms": elapsed, "build_peak_mib": peak, "states": len(index.edges)}
        for size in (1024, 10240, 102400, 1048576):
            text = ("a normal report without any protected terms. " * (size // 43 + 1))[:size]
            row[str(size)] = measure(lambda: index.spans(text, policy), args.repeats)
        hit = terms[-1][0]
        row["sparse_match"] = measure(lambda: index.spans("review " + hit + " before approval", policy), args.repeats)
        assert index.spans(hit, policy) == [(0, len(hit))]
        # Small/medium regex baseline: same exact ASCII terms and boundaries.
        if count <= 10000:
            start = time.perf_counter()
            regex = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(term[0]) for term in terms) + r")(?!\w)")
            row["regex_build_ms"] = (time.perf_counter() - start) * 1000
            row["regex_sparse"] = measure(lambda: list(regex.finditer("review " + hit + " before approval")), args.repeats)
            assert len(list(regex.finditer(hit))) == 1
        row["input_hash"] = sha256("\n".join(term[0] for term in terms).encode()).hexdigest()
        report["synthetic"].append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    print(args.output)


if __name__ == "__main__":
    main()
