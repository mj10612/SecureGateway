"""Reproducible cold benchmark for DomainCatalog loading and heap footprint.

Measurement conditions:
- Module imports are pre-warmed before measurement (import excluded).
- Enabled domains: default ({"defense": True, "automotive": False, "semiconductor": False}).
- Timing: tracemalloc OFF during timing to prevent profiling hook overhead.
  Measured over 5 runs with cache cleared and gc.collect() between runs (median reported).
- Memory: tracemalloc started immediately before cold DomainCatalog() construction
  after cache clear and gc.collect(). Peak heap reported in MB, along with top allocators.
"""

from __future__ import annotations

import gc
import statistics
import time
import tracemalloc

# 1. Warm imports (import excluded from benchmark timing/memory)
from secure_gateway.domain_dictionaries import DomainCatalog, catalog, DEFAULTS


def run_benchmark(runs: int = 5) -> dict[str, float]:
    print("=" * 60)
    print("DomainCatalog Cold Load Benchmark")
    print(f"Enabled domains: {DEFAULTS}")
    print(f"Timing runs: {runs} (tracemalloc OFF during timing)")
    print("=" * 60)

    # Pre-warm catalog import structures
    catalog.cache_clear()
    gc.collect()

    # 1. Measure load duration (tracemalloc OFF)
    durations = []
    for i in range(runs):
        catalog.cache_clear()
        gc.collect()
        t0 = time.perf_counter()
        _ = DomainCatalog()
        t1 = time.perf_counter()
        durations.append(t1 - t0)
        print(f"  Run {i + 1}: {durations[-1]:.3f} s")

    median_duration = statistics.median(durations)
    min_duration = min(durations)
    print(f"\nTiming summary: median={median_duration:.3f} s, min={min_duration:.3f} s")

    # 2. Measure peak heap (tracemalloc ON)
    catalog.cache_clear()
    gc.collect()
    tracemalloc.start()
    _ = DomainCatalog()
    current, peak = tracemalloc.get_traced_memory()
    snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()

    current_mb = current / (1024 * 1024)
    peak_mb = peak / (1024 * 1024)
    print(f"\nMemory summary: peak={peak_mb:.2f} MB, retained={current_mb:.2f} MB")

    print("\nTop 10 memory-holding lines at completion:")
    for stat in snapshot.statistics("lineno")[:10]:
        print(f"  {stat}")

    return {
        "median_duration_s": median_duration,
        "min_duration_s": min_duration,
        "peak_heap_mb": peak_mb,
        "retained_heap_mb": current_mb,
    }


if __name__ == "__main__":
    run_benchmark()
