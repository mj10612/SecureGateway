"""#309 preregistered run on gpt-6-luna with the #364 validated transport.

Inputs are reused byte-for-byte from the frozen replication manifest
(309/comprehension-replication/manifest.json, captured by the candidate code at
freeze time). Only arms A, C and D1 run (condition B dropped by owner decision to
save Codex usage). Transport: secure_gateway.evaluation_batch lean session, one
call per interpretation, grading batched by 2 (validated in #364).

Run from a checkout whose secure_gateway has evaluation_batch (>= 2.15.0):
    uv run --locked python <this file> --freeze      # once, before any call
    uv run --locked python <this file> --run         # resumable
    uv run --locked python <this file> --report
"""
import argparse
import concurrent.futures
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

from secure_gateway import __version__, evaluation_batch as eb

ROOT = Path(__file__).resolve().parents[1]
ISSUE, VARIANT = 309, "ko_conjugation_split"
SRC = ROOT / "309" / "comprehension-replication" / "manifest.json"
PLAN_SRC = ROOT / "309" / "plan-replication"
PLAN = ROOT / "309" / "plan-luna"
OUT = ROOT / "309" / "comprehension-luna"
MODEL, EFFORT = eb.DEFAULT_EVAL_MODEL, "low"
ARMS = ("A", "C", "D1")
GRADE_BATCH, WORKERS, SEED = 2, 3, 20261112
GRADE_SYSTEM = ("Grade each blinded response independently. Evidence must be a nonempty exact verbatim "
                "excerpt of the corresponding response, without added quotation marks; if a violation is "
                "absence, quote enough of that actual response to support the judgment. Do not use tools.")
RETRY = ("The previous quote validation failed. Supply only exact nonempty excerpts from the corresponding "
         "response for every verdict.")


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def fsha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def append(path, row):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def source():
    return json.loads(SRC.read_text(encoding="utf-8"))


def build_jobs(m):
    jobs = []
    for case in m["cases"]:
        for arm in ARMS:
            a = case["arms"][arm]
            request = {"role": "interpret", "job_id": sha([ISSUE, "luna", case["case_id"], arm])[:32],
                       "model": MODEL, "max_output_tokens": 512, "reasoning_effort": EFFORT,
                       "messages": [{"role": "system", "content": a["instructions"]},
                                    {"role": "user", "content": a["input"]}]}
            jobs.append({"case_id": case["case_id"], "arm": arm, "request": request})
    random.Random(SEED).shuffle(jobs)
    return jobs


def freeze():
    if (PLAN / "freeze.json").exists():
        raise SystemExit("already frozen")
    PLAN.mkdir(parents=True)
    OUT.mkdir(parents=True)
    m = source()
    for name in ("rubric.json", "decision.json", "cases.json", "conditions.json",
                 "preflight-" + VARIANT + ".json"):
        (PLAN / name).write_bytes((PLAN_SRC / name).read_bytes())
    (OUT / "frozen-rubric.json").write_bytes((PLAN / "rubric.json").read_bytes())
    (OUT / "frozen-decision.json").write_bytes((PLAN / "decision.json").read_bytes())
    jobs = build_jobs(m)
    est = eb.estimate_budget(interpret_jobs=len(jobs), grade_cases=len(m["cases"]), interpret_batch=1,
                             grade_batch=GRADE_BATCH, fixed_input_tokens=7070,
                             interpret_content_tokens=400, grade_content_tokens=2000)
    doc = {
        "issue": ISSUE, "variant": VARIANT, "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": MODEL, "reasoning_effort": EFFORT, "arms": list(ARMS),
        "condition_B": "dropped by owner decision (Codex usage); #306 is not derived from this run",
        "transport": {"adapter": "secure_gateway.evaluation_batch.run_lean_worker",
                      "adapter_source_sha256": eb.adapter_hash(), "secure_gateway_version": __version__,
                      "interpretation": "one fresh lean call per (case, arm)",
                      "grading": f"lean, batch {GRADE_BATCH} (accepted in #364 validation)",
                      "disabled_features": list(eb.LEAN_DISABLED_FEATURES)},
        "inputs": {"source_manifest": "309/comprehension-replication/manifest.json",
                   "source_manifest_sha256": fsha(SRC), "source_run_identity": m["run_identity"],
                   "note": "model-visible inputs reused byte-for-byte; the 13 partial gpt-6.1-sol answers of that run are not used"},
        "plan_files_sha256": {p.name: fsha(p) for p in sorted(PLAN.iterdir()) if p.name != "freeze.json"},
        "jobs_sha256": sha(jobs), "jobs": len(jobs), "cases": len(m["cases"]),
        "shuffle_seed": SEED, "budget_estimate": est,
        "decision_rule": "frozen decision.json (comprehension target): ADOPT iff protection gate passes AND "
                         "D wins the one-sided exact sign test p<0.05 AND no criterion net loss >=2 AND "
                         "negative controls no net regression; otherwise REJECT",
        "ungraded": "one single-case re-grade after a failed quote check; then bound rule both directions",
        "limitations": ["Interpreter and grader are the same model family.",
                        "Lean grader is stricter than the native grader used for earlier candidates; "
                        "results are not comparable across transports or models."],
    }
    (PLAN / "freeze.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"jobs": len(jobs), "budget": est}, indent=1))


def verified():
    f = json.loads((PLAN / "freeze.json").read_text(encoding="utf-8"))
    if fsha(SRC) != f["inputs"]["source_manifest_sha256"]:
        raise SystemExit("source manifest changed")
    for name, digest in f["plan_files_sha256"].items():
        if fsha(PLAN / name) != digest:
            raise SystemExit("plan file changed: " + name)
    for name in ("rubric.json", "decision.json"):
        if fsha(OUT / ("frozen-" + name)) != f["plan_files_sha256"][name]:
            raise SystemExit("run copy changed: " + name)
    if f["transport"]["adapter_source_sha256"] != eb.adapter_hash():
        raise SystemExit("adapter changed since freeze")
    m = source()
    jobs = build_jobs(m)
    if sha(jobs) != f["jobs_sha256"] or MODEL != f["model"]:
        raise SystemExit("jobs differ from freeze")
    return m, jobs


def call(request):
    started = time.monotonic()
    try:
        result = eb.run_lean_worker(request)
        return {"status": "completed", "result": result, "elapsed_seconds": time.monotonic() - started}
    except eb.UsageLimitReached:
        return {"status": "limit"}
    except ValueError as exc:
        return {"status": "failed", "error": str(exc), "elapsed_seconds": time.monotonic() - started}


def stop_for_limit():
    print("USAGE LIMIT reached - stopped cleanly; rerun --run to resume.", flush=True)
    sys.exit(3)


def interpret(jobs):
    path, failed_path = OUT / "first-responses.jsonl", OUT / "failed-calls.jsonl"
    done = {}
    for r in rows(path):
        meta = r["result"]["metadata"]
        if (r["status"] != "completed" or meta.get("tool_events") != 0 or meta.get("fresh_session") is not True
                or meta.get("requested_model") != MODEL or r["result"]["job_id"] != r["job_id"]):
            raise SystemExit("invalid saved response")
        done[r["job_id"]] = r
    pending = [j for j in jobs if j["request"]["job_id"] not in done]
    print("interpretations saved", len(done), "pending", len(pending), flush=True)
    for pos in range(0, len(pending), WORKERS):
        chunk = pending[pos:pos + WORKERS]
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            results = list(pool.map(lambda j: call(j["request"]), chunk))
        limit = False
        for job, res in zip(chunk, results):
            row = {"job_id": job["request"]["job_id"], "case_id": job["case_id"], "arm": job["arm"], **res}
            if res["status"] == "completed":
                append(path, row)
            elif res["status"] == "limit":
                limit = True
            else:
                append(failed_path, row)
        if limit:
            stop_for_limit()
        if (pos // WORKERS) % 10 == 0 or pos + WORKERS >= len(pending):
            print("interpreted", min(pos + WORKERS, len(pending)), "of", len(pending), flush=True)
    answers = {(r["case_id"], r["arm"]): r["result"]["response"] for r in rows(path)}
    missing = [j for j in jobs if (j["case_id"], j["arm"]) not in answers]
    if missing:
        raise SystemExit(f"{len(missing)} interpretations failed; rerun --run to retry them")
    return answers


def grade_request(m, case, answers):
    cid = case["case_id"]
    labels = list(ARMS)
    random.Random(int(sha([ISSUE, "luna", cid])[:16], 16)).shuffle(labels)
    blind = {f"R{i + 1}": x for i, x in enumerate(labels)}
    responses, criteria = {}, []
    for label, arm in blind.items():
        a = case["arms"][arm]
        responses[label] = {"response": answers[(cid, arm)], "model_visible_input": a["input"],
                            "synthetic_alias_mapping": a["aliases"]}
        for criterion in case["applicable"]:
            x = m["criterion_definitions"][criterion]
            criteria.append({"id": label + "::" + criterion, "description": "For " + label + ": " + x["pass"]
                             + " Failure: " + x["fail"] + " Positive example: " + x["positive_example"]
                             + " Negative example: " + x["negative_example"]})
    msg = {"original": case["original"], "expected_case_behavior": case["expected"], "responses": responses}
    request = {"role": "grade", "job_id": sha([ISSUE, "luna", cid, "grade"])[:32], "model": MODEL,
               "max_output_tokens": 2048, "reasoning_effort": EFFORT,
               "messages": [{"role": "system", "content": GRADE_SYSTEM},
                            {"role": "user", "content": json.dumps(msg, ensure_ascii=False)}],
               "criteria": criteria}
    return request, blind, responses


def quotes_valid(grades, responses):
    return all(g["id"].split("::", 1)[0] in responses
               and g["evidence"] in responses[g["id"].split("::", 1)[0]]["response"] for g in grades)


def grade(m, answers):
    path = OUT / "first-grades.jsonl"
    final = {r["case_id"] for r in rows(path) if r["kind"] == "case" and r["how"] != "failed"}
    pending = [c for c in m["cases"] if c["case_id"] not in final]
    print("grades saved", len(final), "pending", len(pending), flush=True)
    for pos in range(0, len(pending), GRADE_BATCH):
        chunk = pending[pos:pos + GRADE_BATCH]
        built = {c["case_id"]: grade_request(m, c, answers) for c in chunk}
        request, labels = eb.build_grade_batch({k: v[0] for k, v in built.items()},
                                               job_id=sha([ISSUE, "luna", "gb"] + sorted(built))[:32],
                                               seed=SEED + pos)
        res = call(request)
        if res["status"] == "limit":
            stop_for_limit()
        append(path, {"kind": "call", "role": "grade_batch", "cases": sorted(built),
                      "usage": res.get("result", {}).get("usage"), "status": res["status"],
                      "error": res.get("error")})
        split = eb.split_grade_batch(res["result"]["grades"], labels) if res["status"] == "completed" else {}
        for cid, (req, blind, responses) in built.items():
            grades, how = split.get(cid), "batch"
            if not grades or not quotes_valid(grades, responses):
                retry = dict(req)
                retry["job_id"] = sha([ISSUE, "luna", cid, "regrade"])[:32]
                retry["messages"] = list(req["messages"]) + [{"role": "user", "content": RETRY}]
                single = call(retry)
                if single["status"] == "limit":
                    stop_for_limit()
                append(path, {"kind": "call", "role": "regrade_single", "cases": [cid],
                              "usage": single.get("result", {}).get("usage"), "status": single["status"],
                              "error": single.get("error")})
                if single["status"] == "completed":
                    grades, how = single["result"]["grades"], "regrade"
                else:
                    grades, how = None, "failed"  # transport failure: retried on resume
            ok = bool(grades) and quotes_valid(grades, responses)
            append(path, {"kind": "case", "case_id": cid, "how": how,
                          "status": "completed" if ok else ("ungraded" if how != "failed" else "failed"),
                          "blind_labels": blind, "grades": grades if ok else None})
        print("graded", min(pos + GRADE_BATCH, len(pending)), "of", len(pending), flush=True)


def evaluate(m, graded, preflight, offline, assign=None):
    """Frozen rule. ``assign`` maps ungraded case -> (C passes, D1 passes) for bounds."""
    allp, crit_arms, eligible = {}, {}, []
    for case in m["cases"]:
        cid = case["case_id"]
        rec = graded.get(cid)
        if rec and rec["status"] == "completed":
            arms = {}
            for g in rec["grades"]:
                label, criterion = g["id"].split("::", 1)
                arms.setdefault(rec["blind_labels"][label], {})[criterion] = g["passed"]
            if all(arms["A"].values()):
                eligible.append(cid)
                allp[cid] = {k: all(v.values()) for k, v in arms.items()}
                crit_arms[cid] = arms
        elif assign and cid in assign:
            eligible.append(cid)
            allp[cid] = {"A": True, "C": assign[cid][0], "D1": assign[cid][1]}
    wins = sum(not allp[c]["C"] and allp[c]["D1"] for c in eligible)
    losses = sum(allp[c]["C"] and not allp[c]["D1"] for c in eligible)
    n = wins + losses
    p = sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n if n else 1.0
    criterion = {}
    for cr in m["criterion_definitions"]:
        app = [c for c in crit_arms if cr in crit_arms[c]["C"] and cr in crit_arms[c]["D1"]]
        if app:
            criterion[cr] = {"A": sum(crit_arms[c]["A"].get(cr, False) for c in app),
                             "C": sum(crit_arms[c]["C"][cr] for c in app),
                             "D": sum(crit_arms[c]["D1"][cr] for c in app), "cases": len(app)}
    controls = {c["case_id"] for c in m["cases"] if c["negative_control"]}
    control_loss = (sum(allp[c]["C"] and not allp[c]["D1"] for c in eligible if c in controls)
                    - sum(not allp[c]["C"] and allp[c]["D1"] for c in eligible if c in controls))
    pf = {x["id"]: x for x in preflight["cases"]}
    adopt = (offline["protection_gate_passed"] and wins > losses and p < .05
             and all(v["C"] - v["D"] < 2 for v in criterion.values()) and control_loss <= 0)
    return {"decision": "ADOPT" if adopt else "REJECT", "analysis_cases": len(eligible),
            "analysis_discriminating_cases": sum(pf[c]["full_payload_equal"] is False for c in eligible if c in pf),
            "whole_task_passes": {k: sum(allp[c][k] for c in eligible) for k in ARMS},
            "D_only": wins, "C_only": losses, "p_one_sided": p, "per_criterion": criterion,
            "negative_control_count": sum(c in controls for c in eligible),
            "negative_control_net_loss": control_loss}


def report():
    m, _jobs = verified()
    graded = {}
    for r in rows(OUT / "first-grades.jsonl"):
        if r["kind"] == "case":
            graded[r["case_id"]] = r
    preflight = json.loads((PLAN / ("preflight-" + VARIANT + ".json")).read_text(encoding="utf-8"))
    offline = json.loads((ROOT / "309" / "offline" / VARIANT / "summary.json").read_text(encoding="utf-8"))
    missing = [c["case_id"] for c in m["cases"] if graded.get(c["case_id"], {}).get("status") not in ("completed", "ungraded")]
    ungraded = [c for c, r in graded.items() if r["status"] == "ungraded"]
    usage = {"calls": 0, "raw_tokens": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    for r in rows(OUT / "first-responses.jsonl"):
        u = r["result"]["usage"]
        usage["calls"] += 1
        usage["raw_tokens"] += u["input_tokens"] + u["output_tokens"]
        for k in ("input_tokens", "cached_input_tokens", "output_tokens"):
            usage[k] += u.get(k, 0)
    for r in rows(OUT / "first-grades.jsonl"):
        if r["kind"] == "call" and r.get("usage"):
            u = r["usage"]
            usage["calls"] += 1
            usage["raw_tokens"] += u["input_tokens"] + u["output_tokens"]
            for k in ("input_tokens", "cached_input_tokens", "output_tokens"):
                usage[k] += u.get(k, 0)
    doc = {"issue": ISSUE, "variant": VARIANT, "model": MODEL, "arms": list(ARMS),
           "freeze_sha256": fsha(PLAN / "freeze.json"), "usage": usage,
           "raw_tokens_per_case": round(usage["raw_tokens"] / len(m["cases"])),
           "ungraded": ungraded, "protection": offline}
    if missing:
        doc["status"] = "incomplete"
        doc["missing"] = missing
    else:
        doc["status"] = "completed"
        if ungraded:
            bounds = {name: evaluate(m, graded, preflight, offline, {c: value for c in ungraded})
                      for name, value in (("ungraded_D_wins", (False, True)), ("ungraded_C_wins", (True, False)),
                                          ("ungraded_both_fail", (False, False)), ("ungraded_both_pass", (True, True)))}
            doc["bounds"] = bounds
            decisions = {b["decision"] for b in bounds.values()}
            doc["result"] = bounds["ungraded_both_fail"]
            doc["result"]["decision"] = decisions.pop() if len(decisions) == 1 else "UNDECIDED_RERUN_UNGRADED"
        else:
            doc["result"] = evaluate(m, graded, preflight, offline)
    (OUT / "report.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shown = {k: v for k, v in doc.items() if k not in ("protection", "bounds")}
    print(json.dumps(shown, ensure_ascii=False, indent=1)[:4000])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        freeze()
    if args.run:
        m, jobs = verified()
        answers = interpret(jobs)
        grade(m, answers)
        report()
    elif args.report:
        report()


if __name__ == "__main__":
    main()
