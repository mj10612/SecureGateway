"""Freeze and run development-only public-exception controls using the HTTP harness."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

from secure_gateway.evaluation import load_corpus, run_privacy, validate_corpus, write_json
from secure_gateway.experiment_profiles import candidate_profile

ROOT = Path("docs/evaluations/issue316-2.11.0")


def prepare() -> None:
    text = "Review Mirel tomorrow. Ask before publishing."
    path = ["input", 0, "content"]
    start = text.index("Mirel")
    record = {"term": "Mirel", "project": "local-A", "language": "en",
              "source": "explicit-local-correction", "expires_at": 4102444800, "revoked": False}
    cases = []
    for condition in ("public", "forced", "wrong"):
        secret = [] if condition == "public" else [{"path": path, "start": start, "end": start + 5,
                  "label": "name", "fragments": [], "policy": "explicit" if condition == "forced" else "contextual",
                  "severity": "high"}]
        public = [{"path": path, "start": start, "end": start + 5, "label": "name"}] if condition == "public" else []
        cases.append({"id": "dev-public-" + condition, "issue_number": 316, "template_group": condition,
                      "split": "development", "language": "en", "domain": "general", "dialect": "codex",
                      "payload": {"model": "fixture", "input": [{"role": "user", "content": text}]},
                      "echo_path": path, "task_path": path, "secrets": secret, "public": public,
                      "forced_terms": ["Mirel"] if condition == "forced" else [], "rubric": [],
                      "human_text": text.replace("Mirel", "private_symbol_1") if secret else text,
                      "smoke": True, "local_policy": {"trusted_project": "local-A", "workspace": "local-A",
                      "language": "en", "policyrecords": [], "public_records": [record]}})
    data = {"schema_version": 1, "corpus_version": "correction-public-development-2.10.0-v1",
            "synthetic": True, "cases": cases}
    validate_corpus(data)
    write_json(ROOT / "public-development.json", data)


def run(output: Path) -> None:
    data = load_corpus(ROOT / "public-development.json")
    rows = []
    for case in data["cases"]:
        sample = deepcopy(data)
        sample["cases"] = [case]
        base = output / case["id"]
        baseline = run_privacy(sample, output_dir=base / "baseline", profile="release", max_seconds=60)
        with candidate_profile(316, case["local_policy"]):
            candidate = run_privacy(sample, output_dir=base / "candidate", profile="release", max_seconds=60)
        rows.append({"id": case["id"], "baseline_status": baseline["status"],
                     "candidate_status": candidate["status"], "baseline": baseline["metrics"],
                     "candidate": candidate["metrics"]})
    write_json(output / "comparison.json", rows)


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    elif len(sys.argv) == 3 and sys.argv[1] == "run":
        run(Path(sys.argv[2]))
    else:
        raise SystemExit("Expected prepare or run OUTPUT_DIR")
