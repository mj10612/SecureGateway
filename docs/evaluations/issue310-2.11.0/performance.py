"""Cold/warm, isolated synthetic engine timings; no provider calls.

Run from repository root: python performance.py OUTPUT.json
"""
from __future__ import annotations

from contextlib import nullcontext
from hashlib import sha256
import json
import math
import platform
import statistics
import subprocess
import sys
import time

import psutil

from secure_gateway import gateway
from secure_gateway.evaluation import write_json
from secure_gateway.experiment_profiles import candidate_profile


def input_text(kind: str, size: int) -> str:
    templates = {
        "prose": "Project name: glimmer. Ask before sending the checklist. ",
        "code": "def review_item(value):\n    return value + 1\n",
        "structured": "| Customer | Site | Due |\n|---|---|---|\n| Luma | East | 2038-06-21 |\n",
    }
    pattern = templates[kind]
    return (pattern * (size // len(pattern) + 1))[:size]


def policy(issue: int, text: str) -> dict:
    if issue == 311:
        return {"allow_roles": True}
    if issue == 316:
        return {"trusted_project": "local-A", "workspace": "local-A", "language": "en", "policyrecords": []}
    if issue == 318:
        return {"document_sha256": sha256(text.encode()).hexdigest(), "scope": [0, len(text)],
                "required_fields": ["Customer", "Site", "Due"], "protect_fields": ["Customer"]}
    return {}


def worker(issue: int, arm: str, kind: str, size: int) -> None:
    text = input_text(kind, size)
    process = psutil.Process()
    before = process.memory_info().peak_wset
    context = candidate_profile(issue, policy(issue, text)) if arm == "candidate" else nullcontext()
    durations = []
    with context:
        for _ in range(7):
            session = gateway.GatewaySession(natural_language="en")
            start = time.perf_counter()
            if kind == "code":
                session.mask(text, code=True, language="python")
            else:
                session.request({"model": "fixture", "input": [{"role": "user", "content": text}]})
            durations.append(time.perf_counter() - start)
    print(json.dumps({"cold_seconds": durations[0], "warm_seconds": durations[1:],
                      "peak_working_set_delta_bytes": max(0, process.memory_info().peak_wset - before)}))


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def main(output: str) -> None:
    results = []
    for issue in (310, 311, 316, 318):
        for kind in ("prose", "code", "structured"):
            for size in (1024, 10240, 102400):
                for arm in ("baseline", "candidate"):
                    cold, warm, memory = [], [], []
                    errors = []
                    for _ in range(5):
                        try:
                            run = subprocess.run([sys.executable, __file__, "--worker", str(issue), arm, kind, str(size)],
                                                 capture_output=True, text=True, timeout=300, check=True)
                            record = json.loads(run.stdout)
                            cold.append(record["cold_seconds"])
                            warm.extend(record["warm_seconds"])
                            memory.append(record["peak_working_set_delta_bytes"])
                        except (subprocess.SubprocessError, ValueError, KeyError) as exc:
                            errors.append(type(exc).__name__)
                    entry = {"issue": issue, "kind": kind, "bytes": size, "arm": arm,
                             "cold_seconds": cold, "warm_seconds": warm, "peak_working_set_delta_bytes": memory,
                             "errors": errors}
                    if cold and warm:
                        entry["metrics"] = {"cold_p50": statistics.median(cold), "cold_p95": percentile(cold, .95),
                                            "warm_p50": statistics.median(warm), "warm_p95": percentile(warm, .95)}
                    results.append(entry)
                    write_json(output, {"status": "running", "results": results})
                    print(f"{issue} {kind} {size} {arm}: {len(cold)} cold, {len(warm)} warm", flush=True)
    write_json(output, {"status": "completed" if all(not entry["errors"] for entry in results) else "incomplete",
                        "python": sys.version, "platform": platform.platform(), "psutil": psutil.__version__,
                        "code_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                        "method": "5 fresh processes per workload/arm; each creates 1 cold and 6 warm sessions; "
                                  "transform time excludes process startup; per-process Windows peak working set delta",
                        "results": results})


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "--worker":
        worker(int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5]))
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        raise SystemExit("Expected an output path")
