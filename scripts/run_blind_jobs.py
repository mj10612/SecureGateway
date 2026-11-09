"""Explicit actual Codex workers; persist first answers before blind grading."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import time

from secure_gateway.evaluation import write_json
from secure_gateway.evaluation_codex_worker import run_codex_worker
from secure_gateway.evaluation_comprehension import continue_comprehension


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="Explicitly run real subscription inference.")
    parser.add_argument("--max-calls", type=int, default=320)
    parser.add_argument("--max-seconds", type=int, default=7200)
    parser.add_argument("--max-tokens", type=int, default=12_000_000)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if not args.execute or not 1 <= args.workers <= 3:
        parser.error("Use --execute and 1..3 workers; no implicit provider calls.")
    begin = time.monotonic()
    journal_path = args.root / "actual-worker-journal.json"
    journal = json.loads(journal_path.read_text(encoding="utf8")) if journal_path.exists() else {"calls": [], "started": time.time()}
    if not journal["calls"]:
        from hashlib import sha256
        import inspect
        journal["execution_budget"] = {"max_calls": args.max_calls, "max_seconds": args.max_seconds,
                                       "max_reported_tokens": args.max_tokens, "workers": args.workers}
        journal["adapter_source_sha256"] = sha256(Path(inspect.getfile(run_codex_worker)).read_bytes()).hexdigest()
        write_json(journal_path, journal)
    stopped = any(row.get("status") == "error" for row in journal["calls"])
    directories = sorted(args.root.glob("*/comprehension"))
    for phase, filename, output_name in [("interpret", "interpret-jobs.jsonl", "actual-responses.json"),
                                         ("grade", "grade-jobs.jsonl", "actual-grades.json")]:
        scheduled = []
        for directory in directories:
            if not (directory / filename).exists():
                continue
            saved = json.loads((directory / output_name).read_text(encoding="utf8")) if (directory / output_name).exists() else []
            done = {row["job_id"] for row in saved}
            for line in (directory / filename).read_text(encoding="utf8").splitlines():
                request = json.loads(line)
                if request["job_id"] not in done:
                    scheduled.append((directory, request))
        cursor = 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            while cursor < len(scheduled) and not stopped:
                usage = sum(row.get("usage", {}).get("total_tokens", 0) for row in journal["calls"])
                if len(journal["calls"]) >= args.max_calls or time.monotonic() - begin >= args.max_seconds or usage >= args.max_tokens:
                    break
                batch = scheduled[cursor:cursor + min(args.workers, args.max_calls - len(journal["calls"]))]
                cursor += len(batch)
                futures = {pool.submit(run_codex_worker, {key: value for key, value in request.items() if key != "response_hash"}): (directory, request)
                           for directory, request in batch}
                for future in as_completed(futures):
                    directory, request = futures[future]
                    row = {"job_id": request["job_id"], "phase": phase, "issue": directory.parent.name}
                    try:
                        result = future.result()
                        result["execution"] = {"kind": "actual_llm_subagent", "fresh_context": True,
                                               "runner": "Codex CLI fresh child", "isolation": "Fresh empty cwd, same OS user, no hard filesystem jail; tool events rejected."}
                        if phase == "grade":
                            result["response_hash"] = request["response_hash"]
                        path = directory / output_name
                        saved = json.loads(path.read_text(encoding="utf8")) if path.exists() else []
                        if any(record["job_id"] == result["job_id"] for record in saved):
                            raise ValueError("Cannot replace first response")
                        saved.append(result)
                        write_json(path, saved)
                        row.update(status="completed", usage=result.get("usage", {}))
                        continue_comprehension(directory, **{"responses_path" if phase == "interpret" else "grades_path": path})
                    except (ValueError, OSError) as exc:
                        row.update(status="error", error=type(exc).__name__, diagnostic=str(exc)[:200])
                        stopped = True  # A failed inference can consume unknown usage.
                    journal["calls"].append(row)
                    write_json(journal_path, journal)
                    print(f"{phase} #{row['issue']} {row['status']} ({len(journal['calls'])}/{args.max_calls})", flush=True)
        if stopped:
            break
    reports = []
    for directory in directories:
        report = continue_comprehension(directory)
        reports.append({"issue": directory.parent.name, "status": report["status"], "metrics": report["metrics"]})
    write_json(args.root / "actual-summary.json", {"reports": reports, "stopped_after_unknown_usage": stopped,
                                                   "calls": len(journal["calls"]), "elapsed_seconds": time.monotonic() - begin})
    if stopped:
        raise SystemExit("Stopped after failed worker; unknown usage and incomplete measurements retained.")


if __name__ == "__main__":
    main()
