"""Bounded matcher-only matrix; no HTTP, masking, provider, or model timings."""
from __future__ import annotations

import argparse
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import platform
import statistics
import time
import tracemalloc

from secure_gateway.domain_dictionaries import DEFAULTS, DomainCatalog, TermIndex


def repeat_bytes(unit: str, size: int) -> str:
    raw = unit.encode("utf8")
    text = (raw * (size // len(raw) + 1))[:size].decode("utf8", errors="ignore")
    return text + " " * (size - len(text.encode("utf8")))


def document(language: str, density: str, size: int) -> str:
    units = {
        "en": ("Please review this report. ", "AESA"),
        "ko": ("이 문서를 먼저 읽어 주세요. ", "송수신모듈"),
        "mixed": ("이 문서를 review before approval. ", "AESA 송수신모듈"),
    }
    plain, term = units[language]
    if density == "dense":
        return repeat_bytes(term + " ", size)
    text = repeat_bytes(plain, size)
    if density == "sparse":
        suffix = " " + term + " "
        return repeat_bytes(plain, size - len(suffix.encode("utf8"))) + suffix
    return text


def measure(call, repeats: int, deadline: float):
    samples, cpu_samples, counts, errors = [], [], [], []
    for _ in range(repeats):
        if time.perf_counter() >= deadline:
            break
        begin, cpu = time.perf_counter(), time.process_time()
        try:
            value = call()
            counts.append(len(value))
            errors.append(None)
        except ValueError as exc:
            counts.append(None)
            errors.append(str(exc))
        samples.append((time.perf_counter() - begin) * 1000)
        cpu_samples.append((time.process_time() - cpu) * 1000)
    return {"samples": len(samples), "p50_ms": statistics.median(samples) if samples else None,
            "max_ms": max(samples) if samples else None, "p95_ms": None, "p99_ms": None,
            "cpu_p50_ms": statistics.median(cpu_samples) if cpu_samples else None,
            "hit_counts": counts, "errors": errors,
            "status": "measured" if len(samples) == repeats else "budget_incomplete"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=120)
    args = parser.parse_args()
    if not 1 <= args.max_seconds <= 120:
        parser.error("Time budget must be 1..120 seconds")
    begin = time.perf_counter()
    deadline = begin + args.max_seconds
    catalog = DomainCatalog()
    domains = tuple(DEFAULTS)
    policies = [dict(zip(domains, bits)) for bits in product((False, True), repeat=3)]
    report = {"scope": "Actual packaged dictionary matcher only; not full transform, HTTP, tool or LLM latency",
              "platform": platform.platform(), "processor": platform.processor(), "python": platform.python_version(),
              "manifest_hash": catalog.version, "index_builds": catalog.index.build_count,
              "load_build_ms": (time.perf_counter() - begin) * 1000,
              "max_seconds": args.max_seconds, "requested_repeats": 3,
              "tail_note": "Three warm repetitions cannot estimate p95/p99; both are null. Shared-host timings are not SLAs.",
              "matrix": [], "probes": []}
    all_on = dict.fromkeys(domains, True)

    def probe(name, call):
        result = measure(call, 1, deadline)
        report["probes"].append({"name": name, **result})

    crossing = TermIndex([("alpha beta", "defense", False, "word"),
                          ("beta gamma", "defense", False, "word")])
    probe("overlapping_spans_union", lambda: crossing.spans("alpha beta gamma", all_on))
    report["probes"][-1]["exact_union_correct"] = crossing.spans("alpha beta gamma", all_on) == [(0, 16)]
    prefixes = TermIndex([("sharedprefixcomponent" + str(i).zfill(4), "defense", False, "word") for i in range(1000)])
    probe("1000_shared_prefix_terms_1mib_nohit", lambda: prefixes.spans(repeat_bytes("sharedprefixcomponentx ", 1048576), all_on))
    budget_index = TermIndex([("ab", "defense", False, "word"), ("ab ab", "defense", False, "word")])
    probe("matching_budget_rejects_without_partial_result", lambda: budget_index.spans("ab " * 1000, all_on, max_matches=100))
    probe("maximum_16mib_ascii_boundary", lambda: catalog.spans("z" * (16 * 1024 * 1024), all_on))
    probe("above_16mib_rejected", lambda: catalog.spans("z" * (16 * 1024 * 1024 + 1), all_on))
    unicode_text = document("mixed", "none", 1048576)
    if time.perf_counter() < deadline:
        tracemalloc.start()
        memory_start = time.perf_counter()
        try:
            unicode_hits = catalog.spans(unicode_text, all_on)
            report["unicode_1mib_peak"] = {"peak_mib": tracemalloc.get_traced_memory()[1] / 1024 ** 2,
                                           "input_bytes": len(unicode_text.encode("utf8")), "hits": len(unicode_hits),
                                           "instrumented_ms": (time.perf_counter() - memory_start) * 1000,
                                           "note": "tracemalloc instrumentation is excluded from ordinary matrix timings"}
        finally:
            tracemalloc.stop()
    # All sizes and policy combinations are explicit even when budget runs out.
    for size, language, density, policy in product((1024, 10240, 102400, 1048576),
                                                  ("en", "ko", "mixed"), ("none", "sparse", "dense"), policies):
        text = document(language, density, size)
        row = {"requested_input_bytes": size, "input_bytes": len(text.encode("utf8")),
               "characters": len(text), "input_sha256": sha256(text.encode("utf8")).hexdigest(),
               "language": language, "density": density, "policy": policy,
               **measure(lambda: catalog.spans(text, policy), 3, deadline)}
        if row["p50_ms"] and row["status"] == "measured":
            row["matcher_mib_per_second"] = size / 1048576 / (row["p50_ms"] / 1000)
        report["matrix"].append(row)
    report["elapsed_seconds"] = time.perf_counter() - begin
    report["measured_rows"] = sum(row["status"] == "measured" for row in report["matrix"])
    report["scheduled_rows"] = len(report["matrix"])
    report["nohit_note"] = "none means no deliberately inserted hit; actual incidental hits are retained and counted."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    print(json.dumps({key: report[key] for key in ("measured_rows", "scheduled_rows", "elapsed_seconds", "manifest_hash")}))


if __name__ == "__main__":
    main()
