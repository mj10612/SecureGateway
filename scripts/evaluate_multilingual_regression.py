"""Explicit fresh-model regression checks for the existing 17-language paragraphs.

This internal capture seam supports the older multilingual fixture without
changing the public evaluation corpus schema (which currently allows en/ko).
No model calls occur without --execute. These are regression tasks, not holdouts.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import argparse
import json
from pathlib import Path
import secrets
import time
import uuid

from secure_gateway.evaluation import (
    _capture_case, _metadata, _privacy_metrics, _session_checks, at, digest, write_json,
)
from secure_gateway.evaluation_codex_worker import run_codex_worker
from secure_gateway.evaluation_comprehension import _grade_request, _metrics


def make_cases(rows):
    cases = []
    for index, row in enumerate(rows):
        text, spans = row["text"], []
        for reference in row["references"]:
            offset = 0
            while (start := text.find(reference, offset)) >= 0:
                spans.append({"path": ["input", 0, "content"], "start": start,
                              "end": start + len(reference), "label": "private_reference",
                              "fragments": [], "policy": "contextual", "severity": "high"})
                offset = start + len(reference)
        spans.sort(key=lambda value: value["start"])
        human = text
        for number, span in reversed(list(enumerate(spans, 1))):
            human = human[:span["start"]] + f"private_symbol_{number}" + human[span["end"]:]
        public, cursor = [], 0
        for span in spans + [{"start": len(text), "end": len(text)}]:
            if text[cursor:span["start"]].strip():
                public.append({"path": ["input", 0, "content"], "start": cursor,
                               "end": span["start"], "label": f"ordinary_region_{len(public)}"})
            cursor = span["end"]
        criteria = [{"id": "intent", "description": row["expected_intent"]}]
        criteria.extend({"id": f"constraint_{n}", "description": value}
                        for n, value in enumerate(row["constraints"], 1))
        cases.append({"id": f"regression-{index:02d}-{row['language']}", "language": row["language"],
                      "domain": "general", "dialect": "codex", "split": "regression",
                      "template_group": f"legacy-paragraph-{index}", "smoke": False,
                      "payload": {"model": "fixture", "input": [{"role": "user", "content": text}]},
                      "echo_path": ["input", 0, "content"], "task_path": ["input", 0, "content"],
                      "secrets": spans, "public": public, "forced_terms": [],
                      "human_text": human, "rubric": criteria})
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-calls", type=int, default=114)
    parser.add_argument("--max-tokens", type=int, default=2500000)
    parser.add_argument("--max-seconds", type=int, default=1200)
    args = parser.parse_args()
    if not args.execute or args.output.exists():
        parser.error("Use --execute and a new output directory; first answers are immutable.")
    begin = time.monotonic()
    source = Path("tests/fixtures/context_paragraphs.json")
    rows = json.loads(source.read_text(encoding="utf8"))
    rows.extend([
        {"language": "ko", "text": "SecureMCP 삭제해줘", "references": ["SecureMCP"],
         "expected_intent": "Understands the request to delete/remove the named target.",
         "constraints": ["Treats the opaque target as the object of deletion, not the action.",
                         "Does not invent the target's original private name.",
                         "Does not replace deletion intent with creation, summary or explanation of another task."]},
        {"language": "en", "text": "Read SKILL.md before using this skill. Follow its instructions.", "references": [],
         "expected_intent": "Understands that the skill file must be read and its instructions followed.",
         "constraints": ["Recognizes SKILL.md as the file to read.",
                         "Preserves reading before using the skill, rather than after use.",
                         "Does not claim the unread file's specific contents or instructions."]},
    ])
    cases = make_cases(rows)
    data = {"schema_version": 1, "synthetic": True, "corpus_version": "legacy-multilingual-regression-20261109-v1", "cases": cases}
    metadata = _metadata(data, "release")
    # The public evaluation helper deliberately labels only its en/ko schema.
    # This legacy-fixture capture seam measures the full set recorded below.
    metadata["languages_measured"] = sorted({case["language"] for case in cases})
    metadata["other_languages"] = "none within the declared 17-language scope"
    metadata.update(model="gpt-6.1-sol", model_identity="requested Codex CLI setting; server build unverified",
                    scope="Existing regression corpus, 17 languages plus two known tasks; one fresh repeat, three arms",
                    isolation="Fresh empty cwd/context, same OS user/subscription auth; no hard filesystem jail; tool events rejected",
                    native_hosts="not measured by these semantic text jobs", optional_context_model="off")
    args.output.mkdir(parents=True)
    write_json(args.output / "corpus.json", data)
    captures = []
    for case in cases:
        capture = {"id": case["id"], "language": case["language"], "sensitive_count": len(case["secrets"]), "status": "completed"}
        try:
            capture.update(_capture_case(case))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            capture.update(status="error", error=type(exc).__name__)
        captures.append(capture)
        write_json(args.output / "http-captures.json", captures)
    privacy = _privacy_metrics(captures)
    privacy["integrity"].update(_session_checks())
    write_json(args.output / "privacy.json", {"metadata": metadata, "metrics": privacy})
    if any(row["status"] != "completed" for row in captures):
        raise SystemExit("HTTP captures incomplete; no inference scheduled.")
    jobs = []
    for case, capture in zip(cases, captures):
        instruction = capture["outbound"].get("instructions", "")
        for arm in ("original", "human", "baseline"):
            text = (at(case["payload"], case["task_path"]) if arm == "original" else case["human_text"] if arm == "human"
                    else at(capture["outbound"], case["task_path"]))
            job_id = uuid.uuid4().hex
            request = {"role": "interpret", "job_id": job_id, "model": "gpt-6.1-sol", "max_output_tokens": 1024,
                       "messages": [{"role": "system", "content": instruction}, {"role": "user", "content": text}]}
            jobs.append({"job_id": job_id, "case_id": case["id"], "language": case["language"], "variant": arm,
                         "request": request, "original": at(case["payload"], case["task_path"]), "criteria": case["rubric"]})
    secrets.SystemRandom().shuffle(jobs)
    write_json(args.output / "local-job-manifest.json", jobs)
    write_json(args.output / "interpret-queries.json", [job["request"] for job in jobs])
    write_json(args.output / "freeze.json", {"metadata": metadata, "source_fixture_sha256": sha256(source.read_bytes()).hexdigest(),
                                             "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
                                             "queries_sha256": sha256((args.output / "interpret-queries.json").read_bytes()).hexdigest(),
                                             "corpus_hash": digest(data), "max_calls": args.max_calls,
                                             "max_reported_tokens": args.max_tokens, "max_seconds": args.max_seconds,
                                             "workers": 3, "repeats_per_arm": 1, "max_output_tokens": 1024,
                                             "time_started": time.time(), "tail_statistics": "not estimated from one repeat"})
    responses, grades, journal, errors = {}, {}, [], []
    for phase in ("interpret", "grade"):
        if errors:
            break
        requests = [job["request"] for job in jobs] if phase == "interpret" else [_grade_request(job, responses[job["job_id"]]) for job in jobs if job["job_id"] in responses]
        write_json(args.output / (phase + "-queries.json"), requests)
        for start in range(0, len(requests), 3):
            total_usage = sum(row.get("usage", {}).get("total_tokens", 0) for row in journal)
            if errors or len(journal) >= args.max_calls or total_usage >= args.max_tokens or time.monotonic() - begin >= args.max_seconds:
                break
            batch = requests[start:start + min(3, args.max_calls - len(journal))]
            with ThreadPoolExecutor(max_workers=3) as pool:
                pending = {pool.submit(run_codex_worker, request): request for request in batch}
                for future in as_completed(pending):
                    request = pending[future]
                    row = {"phase": phase, "job_id": request["job_id"]}
                    try:
                        result = future.result()
                        if phase == "interpret":
                            responses[request["job_id"]] = result
                            write_json(args.output / "first-responses.json", responses)
                        else:
                            result["response_hash"] = digest(responses[request["job_id"]]["response"])
                            grades[request["job_id"]] = result
                            write_json(args.output / "independent-grades.json", grades)
                        row.update(status="completed", usage=result.get("usage", {}))
                        if "total_tokens" not in row["usage"]:
                            errors.append({"phase": phase, "error": "unknown_usage"})
                    except (OSError, ValueError) as exc:
                        row.update(status="error", error=type(exc).__name__, diagnostic=str(exc)[:200])
                        errors.append(row)
                    journal.append(row)
                    write_json(args.output / "journal.json", journal)
                    print(phase, len(journal), "/", args.max_calls, row["status"], flush=True)
    scored = [{"case_id": job["case_id"], "language": job["language"], "variant": job["variant"],
               "criteria_count": len(job["criteria"]),
               **({"response": responses[job["job_id"]]["response"]} if job["job_id"] in responses else {}),
               **({"grades": grades[job["job_id"]]["grades"]} if job["job_id"] in grades else {})} for job in jobs]
    report = {"status": "completed" if len(grades) == len(jobs) and not errors else "incomplete", "metadata": metadata,
              "privacy": privacy, "cases": scored, "errors": errors,
              "variants": {arm: _metrics([row for row in scored if row["variant"] == arm]) for arm in ("original", "human", "baseline")},
              "by_language": {language: {arm: _metrics([row for row in scored if row["language"] == language and row["variant"] == arm])
                                         for arm in ("original", "human", "baseline")} for language in sorted({row["language"] for row in scored})},
              "calls": len(journal), "reported_tokens": sum(row.get("usage", {}).get("total_tokens", 0) for row in journal),
              "elapsed_seconds": time.monotonic() - begin}
    report["subsets"] = {
        subset: {arm: _metrics([row for row in scored if row["variant"] == arm
                               and row["case_id"].startswith(("regression-17-", "regression-18-")) == known])
                 for arm in ("original", "human", "baseline")}
        for subset, known in (("legacy_17_paragraphs", False), ("two_known_requests", True))}
    write_json(args.output / "report.json", report)
    print(json.dumps({"status": report["status"], "variants": report["variants"], "calls": len(journal)}))
    if report["status"] != "completed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
