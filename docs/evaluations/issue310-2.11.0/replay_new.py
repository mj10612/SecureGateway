"""Run the preregistered synthetic holdout with the repository HTTP evaluator."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

from secure_gateway.evaluation import load_corpus, run_privacy, write_json
from secure_gateway.experiment_profiles import candidate_profile


def main(output: Path) -> None:
    corpus = load_corpus("docs/evaluations/issue310-2.11.0/new-holdout.json")
    summaries = []
    for case in corpus["cases"]:
        issue = case["issue_number"]
        sample = deepcopy(corpus)
        sample["cases"] = [case]
        base = output / str(issue) / case["id"]
        write_json(base / "corpus.json", sample)
        baseline = run_privacy(sample, output_dir=base / "baseline", profile="release", max_seconds=60)
        with candidate_profile(issue, case["local_policy"]):
            candidate = run_privacy(sample, output_dir=base / "candidate", profile="release", max_seconds=60)
        summaries.append({"id": case["id"], "issue": issue,
                          "baseline_status": baseline["status"], "candidate_status": candidate["status"],
                          "baseline": baseline["metrics"], "candidate": candidate["metrics"]})
    write_json(output / "comparison.json", summaries)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Expected a new output directory")
    main(Path(sys.argv[1]))
