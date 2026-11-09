"""Pair isolated candidate captures, then export immutable blind LLM jobs."""
from contextlib import contextmanager
import argparse
from copy import deepcopy
import json
from pathlib import Path

from secure_gateway import evaluation
from secure_gateway.evaluation_comprehension import prepare_comprehension
from secure_gateway.experiment_profiles import candidate_profile


@contextmanager
def capture_candidate(issue):
    original = evaluation._capture_case
    def capture(case, max_seconds=40):
        with candidate_profile(issue, case.get("local_policy")):
            return original(case, max_seconds=max_seconds)
    evaluation._capture_case = capture
    try:
        yield
    finally:
        evaluation._capture_case = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--issues", default="309,310,311,312,313,314,315,316,317,318")
    parser.add_argument("--prepare-llm", action="store_true")
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    data = evaluation.load_corpus(args.corpus)
    summary = []
    for issue in map(int, args.issues.split(",")):
        subset = deepcopy(data)
        subset["cases"] = [case for case in data["cases"] if case.get("issue_number") == issue]
        evaluation.validate_corpus(subset)
        directory = args.output / str(issue)
        if (directory / "baseline/report.json").exists():
            baseline = json.loads((directory / "baseline/report.json").read_text(encoding="utf8"))
        else:
            baseline = evaluation.run_privacy(subset, output_dir=directory / "baseline", profile="release")
        if (directory / "candidate/report.json").exists():
            candidate = json.loads((directory / "candidate/report.json").read_text(encoding="utf8"))
        else:
            with capture_candidate(issue):
                candidate = evaluation.run_privacy(subset, output_dir=directory / "candidate", profile="release")
            candidate["candidate_issue"] = issue
            evaluation.save_report(candidate, directory / "candidate")
        row = {"issue": issue, "baseline": baseline["metrics"], "candidate": candidate["metrics"],
               "baseline_status": baseline["status"], "candidate_status": candidate["status"],
               "comparison": evaluation.compare_reports(baseline, candidate)}
        if args.prepare_llm and baseline["status"] == candidate["status"] == "completed":
            target = directory / "comprehension"
            if not (target / "manifest.json").exists():
                prepare_comprehension(subset, baseline, candidate, output_dir=target,
                                      model=args.model, profile="release", repeats=args.repeats, max_output_tokens=1024)
            row["blind_jobs"] = str(target / "interpret-jobs.jsonl")
        summary.append(row)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "capture-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf8")
        print(f"#{issue}: baseline={baseline['status']}, candidate={candidate['status']}", flush=True)


if __name__ == "__main__":
    main()
