"""Issue #364 validation: batched lean evaluation vs the #313 individual reference.

Run from the repository root (subscription login only; nothing is written to the
user's Codex configuration):

    uv run --locked python docs/evaluations/eval-cost-364/run_validation.py --stage G
    uv run --locked python docs/evaluations/eval-cost-364/run_validation.py --stage I
    uv run --locked python docs/evaluations/eval-cost-364/run_validation.py --report

Every call is appended to a JSONL file as soon as it returns, so an interrupted
stage resumes where it stopped. A subscription usage limit stops the stage cleanly.
"""
import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

from secure_gateway import evaluation_batch as eb

ROOT = Path(__file__).resolve().parent
REF = ROOT / "reference-313"
PRE = json.loads((ROOT / "preregistration.json").read_text(encoding="utf-8"))
MODEL, EFFORT = "gpt-6.1-sol", "low"
I_BATCH, G_BATCH, SEED = 8, 4, 364
# Stage -> grade batch size. G/I are the preregistered sizes; G2/G1 are the
# preregistered fallbacks (grade batch 2, then individual lean grading).
STAGE_GRADE_BATCH = {"G": 4, "G2": 2, "G1": 1, "I": 2}  # I uses the accepted grading size
GRADE_SYSTEM = ("Grade each blinded response independently. Evidence must be a nonempty exact verbatim "
                "excerpt of the corresponding response, without added quotation marks; if a violation is "
                "absence, quote enough of that actual response to support the judgment. Do not use tools.")
RETRY = ("The previous quote validation failed. Supply only exact nonempty excerpts from the corresponding "
         "response for every verdict.")


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def rows(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append(path, row):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def verify_reference():
    expected = {}
    for line in (ROOT / "reference-313.sha256").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(" *", 1)
        expected[name] = digest
    for name, digest in expected.items():
        if hashlib.sha256((REF / name).read_bytes()).hexdigest() != digest:
            raise SystemExit("reference file changed: " + name)


def manifest():
    return json.loads((REF / "manifest.json").read_text(encoding="utf-8"))


def grade_request(m, case, answers):
    """Byte-for-byte the reference runner's per-case grade request."""
    cid = case["case_id"]
    labels = list(case["arms"])
    random.Random(int(sha([m["issue"], cid])[:16], 16)).shuffle(labels)
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
    request = {"role": "grade", "job_id": sha([m["issue"], cid, "grade"])[:32], "model": MODEL,
               "max_output_tokens": 2048, "reasoning_effort": EFFORT,
               "messages": [{"role": "system", "content": GRADE_SYSTEM},
                            {"role": "user", "content": json.dumps(msg, ensure_ascii=False)}],
               "criteria": criteria}
    return request, blind, responses


def quotes_valid(grades, responses):
    return all(g["id"].split("::", 1)[0] in responses
               and g["evidence"] in responses[g["id"].split("::", 1)[0]]["response"] for g in grades)


def call(request, *, batch=False):
    try:
        result = eb.run_lean_worker(request, batch=batch)
        return {"status": "completed", "result": result}
    except eb.UsageLimitReached:
        print("USAGE LIMIT reached - stopping cleanly; rerun the same command to resume.", flush=True)
        sys.exit(3)
    except ValueError as exc:
        return {"status": "failed", "error": str(exc)}


def reference_answers(m):
    byjob = {r["job_id"]: r for r in rows(REF / "first-responses.jsonl")}
    answers = {}
    for job in m["jobs"]:
        row = byjob[job["request"]["job_id"]]
        assert row["status"] == "completed"
        answers[(job["case_id"], job["arm"])] = row["result"]["response"]
    return answers


def run_grading(m, answers, out, g_batch=G_BATCH):
    path = out / "grades.jsonl"
    # A case whose calls failed in transport (e.g. credit exhaustion) is retried on
    # resume; a case left ungraded by quote verification is final.
    done = {r["case_id"] for r in rows(path) if r["kind"] == "case" and r["how"] != "failed"}
    pending = [c for c in m["cases"] if c["case_id"] not in done]
    for pos in range(0, len(pending), g_batch):
        chunk = pending[pos:pos + g_batch]
        built = {c["case_id"]: grade_request(m, c, answers) for c in chunk}
        request, labels = eb.build_grade_batch({k: v[0] for k, v in built.items()},
                                               job_id=sha(["364", out.name, "g", pos])[:32], seed=SEED + pos)
        attempt = call(request)
        append(path, {"kind": "call", "role": "grade_batch", "cases": len(chunk),
                      "usage": attempt.get("result", {}).get("usage"), "status": attempt["status"],
                      "error": attempt.get("error")})
        split = eb.split_grade_batch(attempt["result"]["grades"], labels) if attempt["status"] == "completed" else {}
        for cid, (req, blind, responses) in built.items():
            grades, how = split.get(cid), "batch"
            if not grades or not quotes_valid(grades, responses):
                retry = dict(req)
                retry["job_id"] = sha(["364", out.name, cid, "regrade"])[:32]
                retry["messages"] = list(req["messages"]) + [{"role": "user", "content": RETRY}]
                single = call(retry)
                append(path, {"kind": "call", "role": "regrade_single", "cases": 1,
                              "usage": single.get("result", {}).get("usage"), "status": single["status"],
                              "error": single.get("error")})
                grades, how = (single["result"]["grades"], "regrade") if single["status"] == "completed" else (None, "failed")
            ok = bool(grades) and quotes_valid(grades, responses)
            append(path, {"kind": "case", "case_id": cid, "status": "completed" if ok else "ungraded",
                          "how": how, "blind_labels": blind, "grades": grades if ok else None})
        print("graded", min(pos + g_batch, len(pending)), "of", len(pending), flush=True)


def run_interpretation(m, out):
    path = out / "responses.jsonl"
    saved = {}
    for r in rows(path):
        if r["kind"] == "answer":
            saved[r["job_id"]] = r
    by_arm = {}
    for job in m["jobs"]:
        by_arm.setdefault(job["arm"], []).append(job)
    for arm, jobs in sorted(by_arm.items()):
        jobs = sorted(jobs, key=lambda j: j["request"]["job_id"])
        random.Random(f"{SEED}:{arm}").shuffle(jobs)
        for pos in range(0, len(jobs), I_BATCH):
            chunk = jobs[pos:pos + I_BATCH]
            if all(j["request"]["job_id"] in saved for j in chunk):
                continue
            items = [{"key": j["request"]["job_id"], "instructions": j["request"]["messages"][0]["content"],
                      "input": j["request"]["messages"][1]["content"]} for j in chunk]
            for attempt_no in (1, 2):
                request, labels = eb.build_interpret_batch(
                    items, job_id=sha(["364", arm, pos, attempt_no])[:32], model=MODEL,
                    max_output_tokens_per_item=512, seed=SEED + pos + attempt_no, reasoning_effort=EFFORT)
                attempt = call(request, batch=True)
                answers = None
                if attempt["status"] == "completed":
                    try:
                        answers = eb.parse_interpret_batch(attempt["result"]["response"], labels,
                                                           max_output_tokens_per_item=512)
                    except ValueError as exc:
                        attempt = {"status": "failed", "error": str(exc), "result": attempt["result"]}
                append(path, {"kind": "call", "role": "interpret_batch", "arm": arm, "items": len(chunk),
                              "attempt": attempt_no, "usage": attempt.get("result", {}).get("usage"),
                              "status": attempt["status"], "error": attempt.get("error")})
                if answers:
                    for j in chunk:
                        row = {"kind": "answer", "job_id": j["request"]["job_id"], "case_id": j["case_id"],
                               "arm": arm, "response": answers[j["request"]["job_id"]]}
                        append(path, row)
                        saved[row["job_id"]] = row
                    break
            else:
                raise SystemExit("batch could not be split twice - stage incomplete")
            print("interpreted", arm, min(pos + I_BATCH, len(jobs)), "of", len(jobs), flush=True)
    return {(r["case_id"], r["arm"]): r["response"] for r in saved.values()}


def scores_from(m, graded):
    """{case_id: {arm: {criterion: passed}}} from per-case grades and blind labels."""
    out = {}
    for case in m["cases"]:
        rec = graded[case["case_id"]]
        arms = {}
        for g in rec["grades"]:
            label, criterion = g["id"].split("::", 1)
            arms.setdefault(rec["blind_labels"][label], {})[criterion] = g["passed"]
        out[case["case_id"]] = arms
    return out


def decision(m, scores, protection_passed=True):
    eligible = [cid for cid, arms in scores.items() if all(arms["A"].values())]
    allp = {cid: {arm: all(v.values()) for arm, v in scores[cid].items()} for cid in eligible}
    wins = sum(not allp[c]["C"] and allp[c]["D1"] for c in eligible)
    losses = sum(allp[c]["C"] and not allp[c]["D1"] for c in eligible)
    n = wins + losses
    p = sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n if n else 1.0
    crit = {}
    for cr in m["criterion_definitions"]:
        app = [c for c in eligible if cr in scores[c]["C"] and cr in scores[c]["D1"]]
        if app:
            crit[cr] = {"C": sum(scores[c]["C"][cr] for c in app), "D": sum(scores[c]["D1"][cr] for c in app)}
    neg = {x["case_id"] for x in m["cases"] if x["negative_control"]}
    control_loss = (sum(allp[c]["C"] and not allp[c]["D1"] for c in eligible if c in neg)
                    - sum(not allp[c]["C"] and allp[c]["D1"] for c in eligible if c in neg))
    adopt = (protection_passed and wins > losses and p < .05
             and all(v["C"] - v["D"] < 2 for v in crit.values()) and control_loss <= 0)
    return {"decision": "ADOPT" if adopt else "REJECT", "analysis_cases": len(eligible),
            "whole_task_passes": {k: sum(allp[c][k] for c in eligible) for k in ("A", "C", "D1")},
            "D_only": wins, "C_only": losses, "p_one_sided": p,
            "criterion_C_minus_D": {k: v["C"] - v["D"] for k, v in crit.items()},
            "negative_control_net_loss": control_loss}


def reference_scores(m):
    graded = {}
    for r in rows(REF / "first-grades.jsonl"):
        graded[r["case_id"]] = {"blind_labels": r["blind_labels"], "grades": r["attempts"][-1]["result"]["grades"]}
    return scores_from(m, graded)


def stage_scores(m, out):
    graded = {r["case_id"]: r for r in rows(out / "grades.jsonl") if r["kind"] == "case"}
    missing = [c["case_id"] for c in m["cases"] if c["case_id"] not in graded or graded[c["case_id"]]["status"] != "completed"]
    return (scores_from(m, graded) if not missing else None), missing


def usage_total(out):
    total = {"calls": 0, "raw_tokens": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    for name in ("responses.jsonl", "grades.jsonl"):
        for r in rows(out / name):
            if r["kind"] == "call" and r.get("usage"):
                total["calls"] += 1
                total["raw_tokens"] += r["usage"]["input_tokens"] + r["usage"]["output_tokens"]
                for k in ("input_tokens", "cached_input_tokens", "output_tokens"):
                    total[k] += r["usage"].get(k, 0)
    return total


def compare(ref, got):
    crit_ref, crit_got, whole_ref, whole_got = {}, {}, {}, {}
    for cid, arms in ref.items():
        for arm, crits in arms.items():
            whole_ref[(cid, arm)] = all(crits.values())
            whole_got[(cid, arm)] = all(got[cid][arm].values())
            for cr, passed in crits.items():
                crit_ref[(cid, arm, cr)] = passed
                crit_got[(cid, arm, cr)] = got[cid][arm][cr]
    per_arm = {arm: {"reference": sum(v for (c, a), v in whole_ref.items() if a == arm),
                     "stage": sum(v for (c, a), v in whole_got.items() if a == arm)}
               for arm in ("A", "C", "D1")}
    return {"criterion": eb.agreement(crit_ref, crit_got), "whole_task": eb.agreement(whole_ref, whole_got),
            "per_arm_whole_task_all_cases": per_arm}


def report(m):
    ref = reference_scores(m)
    ref_dec = decision(m, ref)
    result = {"reference": ref_dec, "preregistration_sha256": hashlib.sha256((ROOT / "preregistration.json").read_bytes()).hexdigest(),
              "adapter_source_sha256": eb.adapter_hash(), "stages": {}}
    for stage in STAGE_GRADE_BATCH:
        out = ROOT / ("stage-" + stage)
        scores, missing = stage_scores(m, out) if out.exists() else (None, ["not run"])
        entry = {"usage": usage_total(out) if out.exists() else None}
        if scores is None:
            entry["status"] = "incomplete"
            entry["missing_or_ungraded"] = missing[:20]
        else:
            entry["status"] = "completed"
            entry["agreement"] = compare(ref, scores)
            entry["decision"] = decision(m, scores)
            last = {r["case_id"]: r["how"] for r in rows(out / "grades.jsonl") if r["kind"] == "case"}
            entry["how"] = {h: list(last.values()).count(h) for h in sorted(set(last.values()))}
            entry["grade_batch_size"] = STAGE_GRADE_BATCH[stage]
            u = entry["usage"]
            entry["raw_tokens_per_case"] = round(u["raw_tokens"] / len(m["cases"]))
        result["stages"][stage] = entry
    (ROOT / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1)[:6000])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=list(STAGE_GRADE_BATCH))
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    verify_reference()
    m = manifest()
    if args.stage:
        out = ROOT / ("stage-" + args.stage)
        out.mkdir(exist_ok=True)
        answers = run_interpretation(m, out) if args.stage == "I" else reference_answers(m)
        run_grading(m, answers, out, STAGE_GRADE_BATCH[args.stage])
    if args.report:
        report(m)


if __name__ == "__main__":
    main()
