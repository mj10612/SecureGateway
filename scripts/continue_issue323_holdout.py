"""Preserve the interrupted #323 run and prepare an explicit continuation.

One-off recovery record: no original answers or journals are rewritten and no
candidate/source/request is tuned. The three interrupted jobs are named in the
plan before another native call. The derivative is ineligible for pristine
holdout adoption and retains unknown parent usage.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import time

from secure_gateway import evaluation_reliable as reliable


def prepare(parent: Path, output: Path):
    if output.exists():
        raise ValueError("Use a new continuation directory.")
    frozen = json.loads((parent / "freeze.json").read_bytes())
    problems = reliable._verify_freeze(parent, frozen, check_native_cli=True)
    if problems:
        raise ValueError(str(problems))
    journal = json.loads((parent / "execution-journal.json").read_bytes())
    state = json.loads((parent / "comprehension/manifest.json").read_bytes())
    answers = json.loads((parent / "comprehension/first-responses.json").read_bytes())
    assert journal["stopped"] is True
    assert {answer["job_id"]: answer for answer in answers} == state["responses"]
    assert not state["grades"]
    interrupted = [call for call in journal["calls"] if call["status"] == "running"]
    assert len(interrupted) == 3
    assert all(call["phase"] == "interpret" and call["job_id"] not in state["responses"]
               for call in interrupted)
    assert len(answers) == 63
    before = {str(path.relative_to(parent)): sha256(path.read_bytes()).hexdigest()
              for path in parent.rglob("*") if path.is_file()}
    shutil.copytree(parent, output / "parent-evidence")
    shutil.copytree(parent, output / "run")
    run = output / "run"
    pending = [job["job_id"] for job in state["jobs"] if job["job_id"] not in state["responses"]]
    continuation_calls = len(pending) + len(state["jobs"])
    plan = {
        "schema_version": 1,
        "reason": "User explicitly requested continuing after the execution process disappeared; preserve saved responses and all interrupted attempts.",
        "user_instruction": "계속해줘",
        "parent_sha256": before,
        "candidate_commit": "089be42d95961771ce7b721b65a70cf24486d885",
        "saved_answers_reused": len(answers),
        "reattempt_job_ids": [call["job_id"] for call in interrupted],
        "pending_answer_ids": pending,
        "new_interpretations": len(pending),
        "new_grades": len(state["jobs"]),
        "new_call_budget": continuation_calls,
        "unknown_parent_usage_calls": len(interrupted),
        "usage_note": "Combined reported usage is a lower bound; no known total token budget was met by the interrupted parent.",
        "eligibility": "Continuation after interruption, not a pristine first-use adoption run.",
    }
    for call in journal["calls"]:
        if call["status"] == "running":
            call.update(status="interrupted", usage_unknown=True,
                        error="Execution process disappeared; explicit named continuation reattempt.")
    journal.update(stopped=False, stop_reason=None, elapsed_seconds=0.0,
                   started_at_unix=time.time(), deadline_unix=time.time() + 7200,
                   continuation_plan="../continuation-plan.json")
    journal["budget"] = {"max_calls": len(journal["calls"]) + continuation_calls,
                         "max_seconds": 7200, "max_reported_tokens": 12000000, "workers": 3}
    frozen.update(holdout_use=None, continuation={"plan": "../continuation-plan.json",
                                                 "parent_freeze_sha256": before["freeze.json"]})
    for path, value in ((run / "execution-journal.json", journal),
                        (run / "freeze.json", frozen), (output / "continuation-plan.json", plan)):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    after = {str(path.relative_to(parent)): sha256(path.read_bytes()).hexdigest()
             for path in parent.rglob("*") if path.is_file()}
    assert before == after
    assert (run / "comprehension/first-responses.json").read_bytes() == (parent / "comprehension/first-responses.json").read_bytes()
    assert not reliable._verify_freeze(run, frozen, check_native_cli=True)
    print(json.dumps({"new_calls": continuation_calls, "total_attempt_budget": journal["budget"]["max_calls"],
                      "answers_reused": len(answers), "explicit_reattempts": len(interrupted)}, indent=2))


if __name__ == "__main__":
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
