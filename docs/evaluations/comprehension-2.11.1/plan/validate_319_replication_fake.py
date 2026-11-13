"""End-to-end plumbing check of run_319_replication.py with a fake model. No model call.

Everything runs in a temporary directory outside docs/: a subset of the prepared
manifest is frozen there and run through the real runner code (--freeze, --run,
--report). Only the two model boundaries are replaced:

* ``run_process`` (the Codex subprocess): a fake Codex that checks the argv
  (lean overrides; MCP server only and ``required`` for D; read-only sandbox;
  empty cwd), and for D drives the REAL stdio MCP fixture through an MCP client,
  emitting the same JSON events Codex emits (transport-probe.json).
* ``lean_worker`` (the grading call): a fake grader that quotes the answers.

Injected faults: one usage limit during interpretation and one during grading
(runner must exit 3 and resume), one forbidden tool event (failed, retried), one
quote failure fixed by the single-case re-grade, one case left ungraded (bound
rule), one forbidden D tool call on a control case.

    uv run --locked python docs/evaluations/comprehension-2.11.1/plan/validate_319_replication_fake.py
"""
import asyncio
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run_319_replication", HERE / "run_319_replication.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
LOCK = threading.Lock()
STATE = {"interp_limit": 1, "bad_tool": 1, "grade_limit": 1, "codex_calls": 0, "grade_calls": 0}


def pick(manifest):
    by = {k: [c for c in manifest["cases"] if c["label"] == k] for k in r.REQUIRED}
    cases = by["tool_solvable"][:6] + by["no_calculation"][:3] + by["impossible"][:3]
    return {**manifest, "cases": cases, "jobs": r.build_jobs(cases)}


def events(answer, calls=(), limit=False, bad=False, code_mode_warning=False):
    out = [{"type": "thread.started", "thread_id": "fake"}]
    if code_mode_warning:  # #372: the CLI's fixed warning with code_mode_host disabled
        out.append({"type": "item.completed", "item": {"id": "w", "type": "error",
                                                        "message": r.eb.CODE_MODE_HOST_DISABLED_WARNING}})
    out.append({"type": "turn.started"})
    if limit:
        out.append({"type": "turn.failed", "error": {"message": "You've hit your usage limit. Try again later."}})
        return out
    if bad:
        out.append({"type": "item.completed", "item": {"id": "x", "type": "command_execution", "command": "dir"}})
    for i, (args, result) in enumerate(calls):
        item = {"id": f"m{i}", "type": "mcp_tool_call", "server": r.SERVER, "tool": r.TOOL, "arguments": args,
                "result": {"content": [{"type": "text", "text": json.dumps(result)}], "structured_content": result},
                "error": None, "status": "completed"}
        out += [{"type": "item.started", "item": {**item, "result": None, "status": "in_progress"}},
                {"type": "item.completed", "item": item}]
    out.append({"type": "item.completed", "item": {"id": "a", "type": "agent_message", "text": answer}})
    out.append({"type": "turn.completed", "usage": {"input_tokens": 7400, "cached_input_tokens": 3000,
                                                    "output_tokens": 40}})
    return out


def fake_codex(cases):
    by_input = {}
    for c in cases:
        by_input[("A", c["arms"]["A"]["input"])] = c
        by_input[("M", c["arms"]["C"]["input"])] = c
    forbidden = next(c["case_id"] for c in cases if c["label"] == "impossible")

    def run(command, prompt, cwd, env):
        assert command[1] == "exec" and "--ephemeral" in command and command[command.index("--sandbox") + 1] == "read-only"
        assert 'forced_login_method="chatgpt"' in command and not any(Path(cwd).iterdir()), "isolation"
        d = any(a.startswith("mcp_servers.") for a in command)
        disabled = {command[i + 1] for i, a in enumerate(command[:-1]) if a == "--disable"}
        assert disabled == (set(r.arm_disabled_features("D" if d else "A")) if r.LEAN else set()), "arm features"
        assert (r.CODE_MODE_HOST in disabled) != d, "only D keeps code-mode host"
        assert d == ("mcp_servers." + r.SERVER + ".required=true" in command)
        text = prompt.decode("utf-8")
        assert text.startswith(r.PROMPT_D if d else r.PROMPT_NO_TOOL)
        messages = json.loads(text.split("\n", 1)[1] if not d else text[len(r.PROMPT_D):])
        user = messages[1]["content"]
        case = by_input.get(("A", user)) if not d else None
        arm = "A" if case else ("D" if d else "C")
        case = case or by_input[("M", user)]
        output = Path(command[command.index("--output-last-message") + 1])
        with LOCK:
            STATE["codex_calls"] += 1
            limit = STATE["interp_limit"] and STATE["codex_calls"] == 5
            bad = STATE["bad_tool"] and STATE["codex_calls"] == 9
            if limit:
                STATE["interp_limit"] -= 1
            if bad:
                STATE["bad_tool"] -= 1
        calls = []
        if arm == "A":
            answer = "ANSWER-A " + str(case["gold"])[:60]
        elif arm == "C":
            answer = "ANSWER-C The local tool is unavailable here, so I cannot compute the protected result."
        else:
            arg = next(a for a in command if a.startswith("mcp_servers." + r.SERVER + ".args="))
            fixture = Path(json.loads(arg.split("=", 1)[1])[-1])
            if case["label"] == "tool_solvable" or case["case_id"] == forbidden:
                order = case["expected_operand_order"] or list(range(len(case["operand_aliases"])))
                aliases = ([case["operand_aliases"][i] for i in order] * 2)[:2]
                op = str(case["operation"]).lower() if case["label"] == "tool_solvable" else "add"
                _names, result = asyncio.run(r._mcp_call(fixture, op, aliases))
                calls.append(({"operation": op, "aliases": aliases}, result))
                answer = "ANSWER-D Protected result alias: " + str(result.get("alias", "none"))
            else:
                answer = "ANSWER-D No calculation is needed; I did not call the tool."
        if not limit and not bad:
            output.write_text(answer, encoding="utf-8")
        stream = "\n".join(json.dumps(e) for e in events(answer, calls, limit, bad, not d)) + "\n"
        return subprocess.CompletedProcess(command, 1 if limit else 0, stream.encode(), b"")
    return run, forbidden


def fake_grader(cases, regrade_ok, ungraded):
    def verdict(cid, criterion, text):
        arm = text.split(" ", 1)[0][-1]
        passed = True
        if arm == "C" and criterion == "restored_result":
            passed = False
        if arm == "D" and criterion == "necessary_tool" and "Protected result alias" in text:
            passed = False
        return passed

    def grade(request):
        with LOCK:
            STATE["grade_calls"] += 1
            if STATE["grade_limit"] and STATE["grade_calls"] == 3:
                STATE["grade_limit"] -= 1
                raise r.eb.UsageLimitReached()
        content = json.loads(request["messages"][1]["content"])
        if "cases" in content:  # batch: K labels map to materials in order
            materials = {x["case"]: json.loads(x["material"]) for x in content["cases"]}
        else:
            materials = {"": content}
        grades = []
        single = "cases" not in content
        for criterion in request["criteria"]:
            cid_label, _, rest = criterion["id"].rpartition("::")
            klabel, _, rlabel = cid_label.rpartition("::")
            material = materials[klabel]
            cid = next(c["case_id"] for c in cases if c["original"] == material["original"])
            response = material["responses"][rlabel]["response"]
            evidence = response[:14]
            if cid == ungraded or (cid == regrade_ok and not single):
                evidence = "NOT IN THE RESPONSE"
            grades.append({"id": criterion["id"], "passed": verdict(cid, rest, response), "evidence": evidence})
        return {"job_id": request["job_id"], "grades": grades,
                "usage": {"input_tokens": 10800, "cached_input_tokens": 5000, "output_tokens": 1100}}
    return grade


def run_cli(*flags):
    sys.argv = ["run_319_replication.py", *flags]
    try:
        r.main()
        return 0
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1


def main():
    real_plan = r.PLAN
    with tempfile.TemporaryDirectory(prefix="sg-319r-fake-") as d:
        root = Path(d)
        r.PLAN, r.OUT = root / "plan-replication", root / "comprehension-replication"
        r.PLAN.mkdir()
        manifest = pick(r.load(real_plan / "manifest.json"))
        for name in ("precheck.json", "payload-leak-check.json", "budget.json", "fixture-probe.json"):
            shutil.copyfile(real_plan / name, r.PLAN / name)
        pre = r.load(r.PLAN / "precheck.json")
        pre["requirements_met"] = True  # subset run; the real freeze enforces the counts
        r.dump(r.PLAN / "precheck.json", pre)
        r.dump(r.PLAN / "manifest.json", manifest)
        r.dump(r.PLAN / "offline" / r.FEATURE / "summary.json",
               {"status": "completed", "protection_gate_passed": True, "note": "FAKE for plumbing check"})
        cases = manifest["cases"]
        solvable = [c["case_id"] for c in cases if c["label"] == "tool_solvable"]
        codex, forbidden = fake_codex(cases)
        r.run_process = codex
        r.lean_worker = fake_grader(cases, regrade_ok=solvable[1], ungraded=solvable[0])
        # shutil.which("codex") must exist for interpret_call; the fake never runs it.
        assert run_cli("--freeze") == 0
        codes = []
        for _ in range(6):
            codes.append(run_cli("--run"))
            if codes[-1] == 0:
                break
        failed = r.rows(r.OUT / "failed-calls.jsonl")
        if not (r.OUT / "report.json").exists():
            print(json.dumps({"exit_codes": codes, "failed": failed}, indent=1))
            sys.exit(1)
        rep = r.load(r.OUT / "report.json")
        grades = r.rows(r.OUT / "first-grades.jsonl")
        responses = r.rows(r.OUT / "first-responses.jsonl")
        res = rep["result"]
        checks = {
            "exit_codes_limit_then_resume": codes[:1] == [3] and codes[-1] == 0 and 3 in codes,
            "forbidden_tool_event_failed_closed_then_retried": len(failed) == 1 and failed[0]["error_category"] == "ValueError",
            "all_interpretations_once": len(responses) == len(manifest["jobs"]) == len({x["job_id"] for x in responses}),
            "d_tool_calls_real_fixture": all(x["result"]["tool_calls"] == 1 for x in responses
                                            if x["arm"] == "D" and x["case_id"] in solvable),
            "d_restored_equals_gold": all(r.numeric(x["result"]["restored"])[-1:] == r.numeric(
                next(c["gold"] for c in cases if c["case_id"] == x["case_id"]))[:1]
                for x in responses if x["arm"] == "D" and x["case_id"] in solvable),
            "regrade_single_used": any(g.get("how") == "regrade" and g["status"] == "completed" for g in grades),
            "ungraded_bound_rule": rep["ungraded"] == [solvable[0]] and res["decision"] == "UNDECIDED_RERUN_UNGRADED",
            "excluded_bound_adopts": rep["bounds"]["ungraded_excluded"]["decision"] == "ADOPT",
            "c_wins_bound_rejects": rep["bounds"]["ungraded_C_wins"]["decision"] == "REJECT",
            "control_forbidden_call_counted": rep["bounds"]["ungraded_excluded"]["unnecessary_or_forbidden_tool_cases"] == 1,
            "no_leaks": res["provider_value_leak_trajectories"] == 0,
            "usage_counted": rep["usage"]["calls"] == len(responses) + sum(1 for g in grades if g["kind"] == "call" and g.get("usage")),
        }
        # Gate sensitivity on the saved run: a provider-visible leak or a failed protection gate
        # must each turn ADOPT into REJECT.
        m = r.verified()
        byjob = {x["job_id"]: x for x in responses}
        graded = {g["case_id"]: g for g in grades if g["kind"] == "case" and g["status"] == "completed"}
        base = r.evaluate(m, graded, byjob, {"protection_gate_passed": True})
        leak = json.loads(json.dumps(byjob))
        next(x for x in leak.values() if x["arm"] == "C")["result"]["provider_value_leak"] = True
        nogate = r.evaluate(m, graded, byjob, {"protection_gate_passed": False})
        checks["sensitivity_base_adopt"] = base["decision"] == "ADOPT"
        checks["sensitivity_leak_rejects"] = r.evaluate(m, graded, leak, {"protection_gate_passed": True})["decision"] == "REJECT"
        checks["sensitivity_protection_rejects"] = nogate["decision"] == "REJECT"
        print(json.dumps({"checks": checks, "exit_codes": codes, "decision": res["decision"],
                          "bounds": {k: v["decision"] for k, v in rep["bounds"].items()},
                          "excluded_scenario": {k: rep["bounds"]["ungraded_excluded"][k] for k in (
                              "eligible", "solvable_eligible", "correct_restored", "D_only", "C_only", "p_one_sided",
                              "unnecessary_or_forbidden_tool_cases")}}, indent=1))
        if not all(checks.values()):
            sys.exit(1)


if __name__ == "__main__":
    main()
