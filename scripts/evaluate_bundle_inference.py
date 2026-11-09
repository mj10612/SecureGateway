"""Explicit synthetic catalog attack, with immutable queries saved before calls."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from secure_gateway.evaluation import write_json
from secure_gateway.evaluation_codex_worker import run_codex_worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute or args.output.exists():
        parser.error("Use --execute and a new output directory; first answers are immutable.")
    reports = {arm: json.loads((args.capture_root / arm / "report.json").read_text(encoding="utf8"))
               for arm in ("baseline", "candidate")}
    jobs, gold = [], {}
    for index, base in enumerate(reports["baseline"]["cases"]):
        record = base["restored_echo"].split("\n\n")[0]
        rows = [line.split(":", 1) for line in record.splitlines()]
        if len(rows) != 3 or any(len(row) != 2 for row in rows):
            raise ValueError("Expected three exact structured fields")
        catalog = []
        for option in range(4):
            values = [value.strip() for _, value in rows]
            if option != 2:
                # Invented alternatives, same visible field/word-count shape.
                values = [value + chr(70 + option) if field != 2 else value[:-2] + str(21 + option)
                          for field, value in enumerate(values)]
            catalog.append({"id": chr(65 + option), "fields": dict(zip((key for key, _ in rows), values))})
        for arm in ("prior_only", "baseline", "candidate"):
            payload = None if arm == "prior_only" else reports[arm]["cases"][index]["outbound"]["input"][0]["content"]
            for repeat in range(2):
                job_id = f"catalog-{index}-{arm}-{repeat}"
                content = ("Authorized synthetic inference test. Four catalog records have equal prior probability. "
                           "Identify which catalog ID generated the masked record only if visible evidence distinguishes it. "
                           "Alias digits carry no magnitude, ordering or identity. Do not invent evidence. "
                           "Reply only A, B, C, D, or ABSTAIN. No payload means catalog-only control.\n"
                           + json.dumps({"catalog": catalog, "masked_payload": payload}, ensure_ascii=False))
                jobs.append({"role": "interpret", "job_id": job_id, "model": "gpt-6.1-sol",
                             "max_output_tokens": 128, "messages": [{"role": "user", "content": content}]})
                gold[job_id] = {"target": "C", "arm": arm, "case": base["id"], "repeat": repeat}
    args.output.mkdir(parents=True)
    write_json(args.output / "queries.json", jobs)
    write_json(args.output / "local-gold.json", gold)
    write_json(args.output / "freeze.json", {"queries_sha256": sha256((args.output / "queries.json").read_bytes()).hexdigest(),
                                              "max_calls": 12, "reported_token_budget": 300000,
                                              "scope": "Two synthetic catalogs, two repeats, not real-world identification probability"})
    results = []
    for request in jobs:
        if sum(row["result"].get("usage", {}).get("total_tokens", 0) for row in results) >= 300000:
            break
        result = run_codex_worker(request)  # Failed/unknown usage aborts, never retries.
        answer = result["response"].strip()
        results.append({"job_id": request["job_id"], "result": result,
                        "top1_correct": answer == gold[request["job_id"]]["target"],
                        "abstained": answer == "ABSTAIN", "unsupported_selection": answer in {"A", "B", "C", "D"}})
        write_json(args.output / "first-responses.json", results)
    summary = {}
    for arm in ("prior_only", "baseline", "candidate"):
        subset = [row for row in results if gold[row["job_id"]]["arm"] == arm]
        summary[arm] = {"measured": len(subset), "top1_correct": sum(row["top1_correct"] for row in subset),
                        "abstained": sum(row["abstained"] for row in subset),
                        "unsupported_selections": sum(row["unsupported_selection"] for row in subset)}
    write_json(args.output / "summary.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
