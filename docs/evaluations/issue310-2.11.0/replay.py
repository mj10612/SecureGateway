"""Replay frozen synthetic cohorts with the existing HTTP privacy evaluator.

Run from the repository root after the recorded freeze commit:
  uv run --locked --all-extras python docs/evaluations/issue310-2.11.0/replay.py OUTPUT_DIR
The 2026-11-09 holdout was already inspected; this is a regression replay.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

from secure_gateway.evaluation import load_corpus, run_privacy, write_json
from secure_gateway.experiment_profiles import candidate_profile


def main(output: Path) -> None:
    source = Path("docs/evaluations/accuracy-20261109")
    summaries = []
    for split in ("development", "holdout"):
        corpus = load_corpus(source / f"{split}-cases.json")
        for issue in (310, 311, 316, 318):
            for case in (c for c in corpus["cases"] if c.get("issue_number") == issue):
                sample = deepcopy(corpus)
                sample["cases"] = [case]
                base = output / str(issue) / split / case["id"]
                baseline = run_privacy(sample, output_dir=base / "baseline", profile="release", max_seconds=60)
                with candidate_profile(issue, case.get("local_policy") or {}):
                    candidate = run_privacy(sample, output_dir=base / "candidate", profile="release", max_seconds=60)
                summaries.append({"id": case["id"], "issue": issue, "split": split,
                                  "baseline_status": baseline["status"], "candidate_status": candidate["status"],
                                  "baseline": baseline["metrics"], "candidate": candidate["metrics"]})
    write_json(output / "comparison.json", summaries)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Expected a new output directory")
    main(Path(sys.argv[1]))
