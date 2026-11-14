"""#319 preregistered replication: local arithmetic tool, arms A/C/D on gpt-6-luna.

Cases: the 80 independently authored replication cases
(319/plan/replication-batch{1,2}-authored.json) plus an optional, separately
authored ``plan-replication/supplement-authored.json``. Every declared
confidential operand is a forced rule (as ``normalize_319_forced.py``); the
binding pre-check from ``check_319_binding.py`` is re-run with current code and
the ``local_arithmetic`` feature flag. A case that does not bind, whose
"tool_solvable" operation the local tool does not support, or whose gold the
local tool cannot reproduce is excluded (reported, never counted).

Arms (run_319): A = original text, no tool; C = masked text, no tool;
D = identical masked text with the real allowlisted local arithmetic MCP tool
(``arithmetic_mcp_fixture.py``). All three arms use the same tool-capable Codex
path (fresh ephemeral session, empty working directory, read-only sandbox,
ChatGPT login only); only D gets the MCP server and any other tool or command
event fails closed. Grading reuses run_319's grader material, batched by 2 with
``evaluation_batch.build_grade_batch`` and the lean worker, with per-case quote
verification and one single-case re-grade.

    uv run --locked python <this file> --prepare     # no model call; rerunnable until frozen
    uv run --locked python <this file> --protection  # offline protection gate, current code
    uv run --locked python <this file> --freeze      # once, before any call
    uv run --locked python <this file> --run         # resumable; stops cleanly on usage limits
    uv run --locked python <this file> --report
"""
from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import re
import secrets
import shutil
import sys
import tempfile
import time

from secure_gateway import __version__, gateway, evaluation_batch as eb
from secure_gateway.encrypted_session import load_session, save_session
from secure_gateway.evaluation_worker import capture_worker_process, strict_json
from secure_gateway.gateway_features import GatewayFeatures

ISSUE, FEATURE = 319, "local_arithmetic"
ROOT = Path(__file__).resolve().parents[1]
SRC_PLAN = ROOT / "319" / "plan"
PLAN = ROOT / "319" / "plan-replication"
OUT = ROOT / "319" / "comprehension-replication"
FIXTURE = ROOT / "plan" / "arithmetic_mcp_fixture.py"
SOURCES = (("b1", SRC_PLAN / "replication-batch1-authored.json"),
           ("b2", SRC_PLAN / "replication-batch2-authored.json"),
           ("s", PLAN / "supplement-authored.json"),  # supplements are optional
           ("s2", PLAN / "supplement2-authored.json"))
MODEL, EFFORT = eb.DEFAULT_EVAL_MODEL, "low"
ARMS = ("A", "C", "D")
REQUIRED = {"tool_solvable": 40, "no_calculation": 14, "impossible": 26}
OFFSET_REPAIRS: list = []  # filled by normalize(); reported in the pre-check
TOOL_OPERATIONS = {"add", "subtract", "multiply"}
# codex-cli 0.167.2 reaches an MCP tool only as a nested tool of the code-mode
# ``exec`` tool. #372 disabled ``code_mode_host`` so a no-tool arm cannot run code
# behind the event audit; the tool arm therefore keeps code mode enabled and the
# A/C arms keep the full fail-closed set. The resulting asymmetry is the
# experiment variable itself (tool availability) and is disclosed in the plan.
CODE_MODE_HOST = "code_mode_host"
# A design may grade the answer value of the no-tool arms separately; the
# alias-return criterion only applies to the tool arm. None keeps run_319's rule.
NO_TOOL_ANSWER_CRITERION: str | None = None
RUBRIC_SRC = SRC_PLAN / "rubric.json"
PROTECTION_KEY = "319/plan-replication"
# A derived design (a new preregistration that reuses this machinery) supplies its
# own condition text, limitations and freeze fields without editing the frozen
# 2.16.3 plan or its published artifacts.
DESIGN: dict = {}
GRADE_BATCH, WORKERS, SEED = 2, 3, 20261113319
# Lean CLI overrides (evaluation_batch.LEAN_DISABLED_FEATURES + neutral
# model_instructions_file) for every arm. Set from the offline fake-provider probe
# (probe_319_codex_mcp.py -> plan-replication/transport-probe.json), which showed
# the MCP tool is still offered and executed with these overrides.
LEAN = True
FIXED_INPUT_TOKENS = 7070 if LEAN else 15100
SERVER, TOOL = "alias_arithmetic", "local_alias_arithmetic"
ENV_KEYS = {"PATH", "HOME", "USERPROFILE", "CODEX_HOME", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR",
            "LANG", "LC_ALL", "LC_CTYPE", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy",
            "https_proxy", "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
            "NODE_EXTRA_CA_CERTS"}
COMMON = {"intent", "action", "conditions", "prohibition", "order", "clarification", "scope"}
GRADE_SYSTEM = ("Grade each blinded response independently. Every verdict needs an exact nonempty verbatim "
                "excerpt of that answer or its sanitized tool transcript. Do not use tools.")  # run_319 verbatim
RETRY = ("Previous evidence failed validation. Provide exact excerpts from corresponding responses or "
         "transcripts.")  # run_319 verbatim
# run_319 wording plus one sentence that states the tool's call contract. codex-cli 0.167.2
# exposes MCP tools only as deferred nested tools of the code-mode ``exec`` tool, and their
# name and schema are absent from the model request (transport-probe.json); the product path
# (gateway inject_arithmetic_tool) shows the model a direct function schema instead.
PROMPT_D = ("Complete the supplied task. Use the local_alias_arithmetic tool only if needed. It is available "
            "inside the exec tool as tools.mcp__alias_arithmetic__local_alias_arithmetic({\"operation\": "
            "\"add\"|\"subtract\"|\"multiply\"|\"date_difference\", \"aliases\": [two issued aliases]}) and returns "
            "only a new result alias. Do not use other tools, commands, files, browsing, agents or skills. "
            "Limit output to 512 tokens.\n")
PROMPT_NO_TOOL = ("Complete the supplied task. Do not use tools, commands, files, browsing, agents or skills. "
                  "Limit output to 512 tokens.\n")
PROMPTS = {"A": PROMPT_NO_TOOL, "C": PROMPT_NO_TOOL, "D": PROMPT_D}


class UsageLimit(Exception):
    """Subscription usage/credit limit: stop cleanly and resume later."""


# --------------------------------------------------------------------------- utilities

def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def fsha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def rows(path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def append(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def contains_secret(text, values):
    """run_319: whole original tokens outside symbolic aliases."""
    text = re.sub(r"private_symbol_\d+", "[ALIAS]", text)
    return any(re.search(r"(?<![\w.])" + re.escape(v) + r"(?![\w.])", text) is not None for v in values if v)


def numeric(value):
    """run_319 report helper."""
    try:
        return [Decimal(x.replace(",", "")) for x in re.findall(r"(?<!\w)\d+(?:,\d{3})*(?:\.\d+)?(?!\w)", str(value))]
    except InvalidOperation:
        return []


def secret_values(case):
    """run_319: sensitive operands plus every number in the gold (computed value)."""
    return list(case["sensitive_values"]) + re.findall(r"(?<!\w)\d+(?:[.,]\d+)*(?!\w)", str(case.get("gold") or ""))


def sign(wins, losses):
    n = wins + losses
    return sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n if n else 1.0


# --------------------------------------------------------------------------- cases

def normalize(prefix, c):
    """Return (case, None) or (None, reason). Mirrors validate_cases.py for #319."""
    if (not isinstance(c, dict) or not isinstance(c.get("id"), str) or not isinstance(c.get("original"), str)
            or not isinstance(c.get("human_masked"), str) or not c.get("expected")
            or not isinstance(c.get("negative_control"), bool)):
        return None, "missing_or_invalid_fields"
    if not isinstance(c.get("applicable"), list) or not set(c["applicable"]) <= COMMON:
        return None, "invalid_criterion_id"
    if re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", c["original"]):
        return None, "email_requires_synthetic_review"
    label = c.get("label")
    if label not in REQUIRED or "operation" not in c or "unit" not in c or "gold" not in c:
        return None, "invalid_tool_case_metadata"
    text, spans = c["original"], c.get("sensitive_spans")
    if isinstance(spans, list):
        # Offsets are derived data: the authoring spec requires every span text to occur
        # exactly once in `original`, which determines its offsets uniquely. Recompute
        # mismatched offsets only in that case (content untouched); record each repair.
        repaired = []
        for x in spans:
            if (isinstance(x, dict) and isinstance(x.get("text"), str) and x["text"]
                    and (type(x.get("start")) is not int or type(x.get("end")) is not int
                         or text[x["start"]:x["end"]] != x["text"])
                    and text.count(x["text"]) == 1):
                start = text.index(x["text"])
                repaired.append({"text_len": len(x["text"]), "authored": [x.get("start"), x.get("end")],
                                 "derived": [start, start + len(x["text"])]})
                x["start"], x["end"] = start, start + len(x["text"])
        if repaired:
            OFFSET_REPAIRS.append({"id": prefix + ":" + c["id"], "spans": repaired})
    if not isinstance(spans, list) or not spans or any(
            not isinstance(x, dict) or type(x.get("start")) is not int or type(x.get("end")) is not int
            or text[x["start"]:x["end"]] != x.get("text") for x in spans):
        return None, "invalid_gold_offset"
    chunks, pos = [], 0
    for x in sorted(spans, key=lambda x: x["start"]):
        if x["start"] < pos:
            return None, "overlapping_sensitive_spans"
        chunks += [re.escape(text[pos:x["start"]]), r"\[PRIVATE_\d+\]"]
        pos = x["end"]
    if not re.fullmatch("".join(chunks) + re.escape(text[pos:]), c["human_masked"]):
        return None, "human_mask_not_minimal"
    applicable = sorted(set(c["applicable"]) | {"intent", "action", "scope"})
    by = {"A": applicable[:], "C": applicable[:], "D": applicable[:]}
    if label == "tool_solvable":
        by["D"] += ["operation_aliases", "restored_result", "unit"]
        by["C"] += ["restored_result", "unit"]
        by["A"] += ["restored_result", "unit"]
        if NO_TOOL_ANSWER_CRITERION:
            by["A"].insert(0, NO_TOOL_ANSWER_CRITERION)
            by["C"].insert(0, NO_TOOL_ANSWER_CRITERION)
    else:
        by["D"].append("necessary_tool")
    if "comparison" in str(c["operation"]).lower() or "greater_than" in str(c["operation"]).lower():
        for v in by.values():
            v.append("no_comparison")
    case = {"id": prefix + ":" + c["id"], "source_id": c["id"], "source": prefix, "original": text,
            "human_masked": c["human_masked"], "negative_control": c["negative_control"], "label": label,
            "operation": c["operation"], "unit": c["unit"], "gold": c["gold"], "expected": c["expected"],
            "applicable": applicable, "applicable_by_condition": by, "sensitive_spans": spans,
            "public_spans": c.get("public_spans", []), "forced_terms": [x["text"] for x in spans]}
    return case, None


def tool_policy(case, aliases):
    """run_319 unit policy: supported currency or USD; multiply's second operand is a count."""
    unit = case["unit"] if case["unit"] in {"USD", "EUR", "KRW"} else "USD"
    operation = str(case["operation"]).lower()
    allowed = {alias: "count" if operation.startswith("multiply") and i == 1 else unit
               for i, alias in enumerate(aliases)}
    return {"allowed": allowed, "result_units": {"multiply": unit, "date_difference": "days"}}


def capture(case, features=True):
    session = gateway.GatewaySession(
        natural_language="auto", features=GatewayFeatures(local_arithmetic=True) if features else None)
    terms = tuple(case["forced_terms"])
    session.forced_rules = lambda: terms
    payload = session.request({"model": "fixture", "input": [{"role": "user", "content": case["original"]}]})
    return session, payload


def aliases_of(session):
    return {str(v.surrogate): str(v.original) for v in session.session.reverse_store.values()}


def bind(case, session, payload):
    """check_319_binding.py rule: each gold span is exactly one alias and not visible."""
    aliases, masked = aliases_of(session), payload["input"][0]["content"]
    selected = []
    for text in case["forced_terms"]:
        matches = [a for a, original in aliases.items() if original == text]
        if len(matches) != 1:
            return None, "unbound_gold_span"
        if contains_secret(masked, [text]):
            return None, "gold_value_visible"
        selected.append(matches[0])
    return selected, None


def expected_order(case):
    """Return the operand order whose local result equals the authored gold, or None."""
    try:
        values = [Decimal(x) for x in case["forced_terms"]]
    except InvalidOperation:
        return None
    gold = numeric(case["gold"])
    if len(values) != 2 or not gold:
        return None
    op = str(case["operation"]).lower()
    for order in ((0, 1), (1, 0)):
        a, b = values[order[0]], values[order[1]]
        result = a + b if op == "add" else a - b if op == "subtract" else a * b
        if result == gold[0]:
            return list(order)
    return None


async def _mcp_call(fixture, operation, aliases):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=sys.executable, args=[str(FIXTURE), "--fixture", str(fixture)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            tools = await client.list_tools()
            result = await client.call_tool(TOOL, {"operation": operation, "aliases": aliases})
            data = result.structured_content
            if data is None:
                data = json.loads(result.content[0].text)
            return [t.name for t in tools.tools], data


def write_owner(directory, case, selected, session):
    token = secrets.token_hex(32)
    session.session.session_id = "arithmetic-fixture"
    save_session(directory / "session.enc", session.session, token)
    config = {"token": token, **tool_policy(case, selected), "calls": 0, "expires_at": time.time() + 3600}
    (directory / "fixture.json").write_text(json.dumps(config), encoding="utf-8")
    return directory / "fixture.json", token


def fixture_probe(case, selected, order):
    """Offline: drive the real stdio MCP fixture with both alias forms and restore locally.

    #375: this probe used to send only the bare ``private_symbol_N`` form, so it
    passed while the product rejected the ``⟦private_symbol_N⟧`` form the model
    actually sees. Both forms are now exercised with a fresh owner each; a
    tool_solvable case passes only when both compute and restore to the gold.
    """
    forms = {"bare": lambda alias: alias, "displayed": lambda alias: "⟦" + alias + "⟧"}
    out = {"tools_listed": [], "forms": {}}
    gold = numeric(case["gold"])
    for name, render in forms.items():
        session, _payload = capture(case)
        with tempfile.TemporaryDirectory(prefix="sg-319r-probe-") as d:
            fixture, token = write_owner(Path(d), case, selected, session)
            names, data = asyncio.run(_mcp_call(fixture, str(case["operation"]).lower(),
                                                [render(selected[i]) for i in order]))
            owner = gateway.GatewaySession(load_session(Path(d) / "session.enc", token, "arithmetic-fixture"))
            alias = data.get("alias") if isinstance(data, dict) else None
            restored = owner.restore(alias) if alias else None
        out["tools_listed"] = names
        out["forms"][name] = {
            "result_is_alias": bool(alias) and not numeric(re.sub(r"private_symbol_\d+", "", alias)),
            "restored_equals_gold": bool(restored) and bool(gold) and numeric(restored)[:1] == gold[:1],
            "error": data.get("error") if isinstance(data, dict) else None}
    out["ok"] = bool(out["forms"]) and all(
        v["result_is_alias"] and v["restored_equals_gold"] and TOOL in out["tools_listed"]
        for v in out["forms"].values())
    return out


def source_cases():
    found = []
    for prefix, path in SOURCES:
        if path.exists():
            found += [(prefix, path, c) for c in load(path)["cases"]]
    return found


def wrapper(arm):
    return PROMPTS[arm]


def build_jobs(cases):
    jobs = []
    for case in cases:
        for arm in ARMS:
            a = case["arms"][arm]
            request = {"role": "interpret", "job_id": sha([ISSUE, "replication", case["case_id"], arm])[:32],
                       "model": MODEL, "max_output_tokens": 512, "reasoning_effort": EFFORT,
                       "messages": [{"role": "system", "content": a["instructions"]},
                                    {"role": "user", "content": a["input"]}]}
            jobs.append({"case_id": case["case_id"], "arm": arm, "request": request})
    random.Random(SEED).shuffle(jobs)
    return jobs


def budget(cases, jobs):
    """Estimate calls and raw tokens; content tokens ~ characters / 4 (estimate only)."""
    def toks(text):
        return math.ceil(len(text) / 4)
    prompt = {j["request"]["job_id"]: toks(wrapper(j["arm"]) + json.dumps(j["request"]["messages"], ensure_ascii=False))
              for j in jobs}
    label = {c["case_id"]: c["label"] for c in cases}
    tool_schema, out_tokens, tool_turn = 250, 120, 80
    ac = [j for j in jobs if j["arm"] != "D"]
    d_solv = [j for j in jobs if j["arm"] == "D" and label[j["case_id"]] == "tool_solvable"]
    d_ctrl = [j for j in jobs if j["arm"] == "D" and label[j["case_id"]] != "tool_solvable"]
    raw_ac = sum(FIXED_INPUT_TOKENS + prompt[j["request"]["job_id"]] + out_tokens for j in ac)
    # A solvable D turn is two model requests (tool call, then answer): fixed input and context repeat.
    raw_ds = sum(2 * (FIXED_INPUT_TOKENS + tool_schema + prompt[j["request"]["job_id"]]) + tool_turn + out_tokens
                 for j in d_solv)
    raw_dc = sum(FIXED_INPUT_TOKENS + tool_schema + prompt[j["request"]["job_id"]] + out_tokens for j in d_ctrl)
    grade_content = math.ceil(sum(toks(json.dumps(c, ensure_ascii=False)) for c in cases) / len(cases)) + 1800
    grading = eb.estimate_budget(interpret_jobs=0, grade_cases=len(cases), interpret_batch=1,
                                 grade_batch=GRADE_BATCH, fixed_input_tokens=FIXED_INPUT_TOKENS,
                                 interpret_content_tokens=0, grade_content_tokens=grade_content)
    raw = raw_ac + raw_ds + raw_dc + grading["raw_tokens"]
    # Upper bound: a D solvable turn that first lists ALL_TOOLS inside exec makes three model requests.
    raw_upper = raw + sum(FIXED_INPUT_TOKENS + tool_schema + prompt[j["request"]["job_id"]] + tool_turn for j in d_solv)
    calls = len(jobs) + grading["grade_calls"] + grading["regrade_calls"]
    return {"model": MODEL, "lean_cli_overrides": LEAN, "fixed_input_tokens_per_model_request": FIXED_INPUT_TOKENS,
            "interpretation_calls": len(jobs), "grade_batch_calls": grading["grade_calls"],
            "expected_single_regrades_5pct": grading["regrade_calls"], "total_calls": calls,
            "max_calls_one_regrade_per_case": len(jobs) + grading["grade_calls"] + len(cases),
            "raw_tokens": {"A_and_C": raw_ac, "D_tool_solvable": raw_ds, "D_controls": raw_dc,
                           "grading_incl_regrades": grading["raw_tokens"], "total": raw,
                           "total_upper_three_requests_per_solvable_D": raw_upper},
            "raw_tokens_per_case": math.ceil(raw / len(cases)),
            "basis": ("Estimate only. Fixed input per model request from docs/EVALUATION_COST.md (lean 7,070; "
                      "native about 15,100); #309 luna lean run measured 7,444 input / 32 output per "
                      "interpretation. Content ~ chars/4 of wrapper+messages, 120 output tokens per answer; a "
                      "solvable D turn counted as two model requests (tool call + answer) plus 250 tokens of MCP "
                      "tool schema; grading batch 2 with per-case material ~ chars/4 of the case + 1,800 for three "
                      "responses, transcripts and verdicts; 5% single-case re-grades.")}


def prepare():
    if (PLAN / "freeze.json").exists():
        raise SystemExit("plan is frozen; --prepare is closed")
    PLAN.mkdir(parents=True, exist_ok=True)
    rubric = load(RUBRIC_SRC)
    criteria = {x["id"]: x for x in rubric["criteria"]}
    selected_cases, excluded, checks, leaks, probes = [], [], [], [], []
    for prefix, path, raw in source_cases():
        case, reason = normalize(prefix, raw)
        rid = prefix + ":" + str(raw.get("id")) if isinstance(raw, dict) else prefix + ":?"
        if reason:
            excluded.append({"id": rid, "label": raw.get("label"), "reason": reason})
            continue
        try:
            session, payload = capture(case)
        except Exception as exc:  # product refusal is a binding failure
            excluded.append({"id": case["id"], "label": case["label"], "reason": "capture_" + type(exc).__name__})
            continue
        selected_alias, reason = bind(case, session, payload)
        aliases = aliases_of(session)
        masked, instructions = payload["input"][0]["content"], payload.get("instructions", "")
        again_session, again = capture(case)
        deterministic = again == payload and aliases_of(again_session) == aliases
        off_session, off = capture(case, features=False)
        feature_off_equal = off["input"][0]["content"] == masked and off.get("instructions", "") == instructions
        off_aliases = aliases_of(off_session)
        # With the feature on, the gateway also masks words of its own injected tool schema
        # (the operation enum), which adds aliases that never occur in the task text.
        extra = sorted(set(aliases.values()) - set(off_aliases.values()))
        check = {"id": case["id"], "label": case["label"], "bound": reason is None,
                 "deterministic_capture": deterministic, "feature_off_task_equal": feature_off_equal,
                 "feature_off_aliases_subset": all(aliases.get(k) == v for k, v in off_aliases.items()),
                 "feature_on_extra_alias_originals": extra}
        if reason is None and not deterministic:
            reason = "nondeterministic_capture"
        order = None
        if reason is None and case["label"] == "tool_solvable":
            if str(case["operation"]).lower() not in TOOL_OPERATIONS:
                reason = "operation_not_supported_by_local_tool"
            elif (order := expected_order(case)) is None:
                reason = "gold_not_reproducible"
            else:
                probe = fixture_probe(case, selected_alias, order)
                probes.append({"id": case["id"], **probe})
                if not probe["ok"]:
                    reason = "fixture_probe_failed"
        check["reason"] = reason
        checks.append(check)
        # Provider-visible payload: the whole masked request (instructions, input and the
        # gateway's injected tool schema) and the exact worker prompts for C and D.
        values = secret_values({"sensitive_values": case["forced_terms"], "gold": case["gold"]})
        visible = {"gateway_payload": json.dumps(payload, ensure_ascii=False)}
        messages = [{"role": "system", "content": instructions}, {"role": "user", "content": masked}]
        for arm in ("C", "D"):
            visible["prompt_" + arm] = wrapper(arm) + json.dumps(messages, ensure_ascii=False)
        leak = {k: contains_secret(v, values) for k, v in visible.items()}
        leaks.append({"id": case["id"], "label": case["label"], **leak, "any": any(leak.values())})
        if reason is None and leaks[-1]["any"]:
            reason = check["reason"] = "provider_visible_value"
        if reason:
            excluded.append({"id": case["id"], "label": case["label"], "reason": reason})
            continue
        entry = {"case_id": case["id"], "source": case["source"], "source_id": case["source_id"],
                 "original": case["original"], "expected": case["expected"],
                 "negative_control": case["negative_control"], "applicable": case["applicable"],
                 "applicable_by_condition": case["applicable_by_condition"], "label": case["label"],
                 "operation": case["operation"], "unit": case["unit"], "gold": case["gold"],
                 "sensitive_values": case["forced_terms"], "forced_terms": case["forced_terms"],
                 "operand_aliases": selected_alias, "expected_operand_order": order,
                 "tool_policy": tool_policy(case, selected_alias),
                 "arms": {"A": {"instructions": instructions, "input": case["original"], "aliases": {}},
                          "C": {"instructions": instructions, "input": masked, "aliases": aliases},
                          "D": {"instructions": instructions, "input": masked, "aliases": aliases}}}
        selected_cases.append(entry)
    # Cap every label at its required count in source order (b1, b2, s, s2), decided
    # before any model call, so surplus supplement cases never shift the proportions.
    kept, seen = [], {k: 0 for k in REQUIRED}
    for c in selected_cases:
        if seen[c["label"]] < REQUIRED[c["label"]]:
            kept.append(c)
            seen[c["label"]] += 1
        else:
            excluded.append({"id": c["case_id"], "label": c["label"], "reason": "surplus_over_required_count"})
    selected_cases = kept
    counts = {k: sum(c["label"] == k for c in selected_cases) for k in REQUIRED}
    met = all(counts[k] >= v for k, v in REQUIRED.items())
    jobs = build_jobs(selected_cases)
    ids = [j["request"]["job_id"] for j in jobs]
    by_source = {}
    for c in checks:
        src = c["id"].split(":", 1)[0]
        b = by_source.setdefault(src, {"cases": 0, "bound": 0})
        b["cases"] += 1
        b["bound"] += c["bound"]
    precheck = {
        "issue": ISSUE, "secure_gateway_version": __version__, "feature": FEATURE,
        "rule": ("check_319_binding.py: every declared confidential operand (forced rule) binds to exactly one "
                 "gateway alias and no operand is visible in the masked task; tool_solvable cases must also use a "
                 "local-tool operation (add/subtract/multiply), have a gold the local tool reproduces, and pass the "
                 "offline stdio MCP fixture probe"),
        "sources": {p: {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": fsha(path)}
                    for p, path in SOURCES if path.exists()},
        "binding_by_source": by_source,
        "bound": sum(c["bound"] for c in checks), "checked": len(checks),
        "deterministic_capture": sum(c["deterministic_capture"] for c in checks),
        "feature_off_task_equal": sum(c["feature_off_task_equal"] for c in checks),
        "feature_off_aliases_subset": sum(c["feature_off_aliases_subset"] for c in checks),
        "feature_on_extra_alias_originals": sorted({x for c in checks for x in c["feature_on_extra_alias_originals"]}),
        "selected_by_label": counts, "required_by_label": REQUIRED, "requirements_met": met,
        "offset_repairs": OFFSET_REPAIRS,
        "excluded": excluded,
        "excluded_by_reason": {r: sum(x["reason"] == r for x in excluded) for r in sorted({x["reason"] for x in excluded})},
        "fixture_probe": {"tool_solvable_probed": len(probes), "both_alias_forms_ok": sum(p["ok"] for p in probes),
                          "per_form": {f: {"restored_equals_gold": sum(p["forms"].get(f, {}).get("restored_equals_gold")
                                                                        is True for p in probes),
                                            "result_is_alias": sum(p["forms"].get(f, {}).get("result_is_alias")
                                                                   is True for p in probes)}
                                        for f in ("bare", "displayed")}},
        "checks": checks,
    }
    selected_ids = {c["case_id"] for c in selected_cases}
    leak_doc = {"issue": ISSUE, "rule": ("No sensitive operand or number of the gold (computed value) appears as a "
                                         "whole token outside private_symbol_N aliases in the full gateway request "
                                         "payload (instructions, input, injected tool schema) or the exact C/D worker "
                                         "prompts. A is the original-text control and is excluded by design."),
                "cases": len(leaks), "cases_with_leak": sum(x["any"] for x in leaks),
                # Only selected cases reach a model. A case excluded above is never sent, so the
                # freeze gate applies to this count; a fixed wrapper constant can collide with a
                # short operand (for example "512 tokens" and the operand 512) and such a case is
                # excluded, not reworded.
                "selected_cases_with_leak": sum(x["any"] and x["id"] in selected_ids for x in leaks),
                "excluded_cases_with_leak": [x["id"] for x in leaks if x["any"] and x["id"] not in selected_ids],
                "results": leaks}
    manifest = {"schema_version": 1, "issue": ISSUE, "feature": FEATURE, "model": MODEL, "effort": EFFORT,
                "arms": list(ARMS), "secure_gateway_version": __version__, "cases": selected_cases, "jobs": jobs,
                "criterion_definitions": criteria, "shuffle_seed": SEED,
                "duplicate_job_ids": len(ids) - len(set(ids)),
                "disclosure": ("Synthetic data only. Same model family interprets and grades. D permits only the "
                               "local arithmetic MCP tool.")}
    dump(PLAN / "precheck.json", precheck)
    dump(PLAN / "payload-leak-check.json", leak_doc)
    dump(PLAN / "manifest.json", manifest)
    dump(PLAN / "fixture-probe.json", {"issue": ISSUE, "scope": "Offline: real stdio MCP fixture driven by a local "
                                       "MCP client with the expected aliases; no model.", "results": probes})
    dump(PLAN / "budget.json", budget(selected_cases, jobs) if selected_cases else {})
    print(json.dumps({"bound": precheck["bound"], "checked": precheck["checked"], "selected": counts,
                      "requirements_met": met, "excluded_by_reason": precheck["excluded_by_reason"],
                      "payload_leak_cases": leak_doc["cases_with_leak"], "fixture_probe": precheck["fixture_probe"],
                      "budget": load(PLAN / "budget.json").get("raw_tokens")}, indent=1))
    return manifest


def protection():
    """Re-run the frozen offline protection gate (offline_protection.py) with current code."""
    spec = importlib.util.spec_from_file_location("offline_protection", ROOT / "plan" / "offline_protection.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.root = ROOT
    key = PROTECTION_KEY  # output: <root>/<key>/offline/<feature>
    mod.source[key] = mod.source[ISSUE]
    result = mod.run(key, FEATURE)
    print(json.dumps({k: result.get(k) for k in ("status", "newly_exposed", "baseline_exact_restore",
                                                 "candidate_exact_restore", "ci", "protection_gate_passed")}))


def freeze():
    if (PLAN / "freeze.json").exists():
        raise SystemExit("already frozen")
    pre = load(PLAN / "precheck.json")
    if not pre["requirements_met"]:
        raise SystemExit("case requirements not met: " + json.dumps(pre["selected_by_label"]))
    leak = load(PLAN / "payload-leak-check.json")
    if leak.get("selected_cases_with_leak", leak["cases_with_leak"]):
        raise SystemExit("provider-visible leak in a selected payload")
    summary = PLAN / "offline" / FEATURE / "summary.json"
    if not summary.exists() or load(summary)["status"] != "completed":
        raise SystemExit("offline protection gate missing; run --protection")
    m = load(PLAN / "manifest.json")
    if m["duplicate_job_ids"] or sha(build_jobs(m["cases"])) != sha(m["jobs"]):
        raise SystemExit("job list invalid")
    (PLAN / "rubric.json").write_bytes(Path(RUBRIC_SRC).read_bytes())
    (PLAN / "decision.json").write_bytes((SRC_PLAN / "decision.json").read_bytes())
    dump(PLAN / "conditions.json", {
        "issue": ISSUE, "fixed": load(SRC_PLAN / "conditions.json")["fixed"],
        "A": "Original synthetic input, no tool (task-validity control).",
        "C": "Masked input (local_arithmetic feature flag capture), no tool.",
        "D": "Identical masked input with the real allowlisted local arithmetic MCP tool; no other tool allowed.",
        "transport": DESIGN.get("transport", (
            "All arms: same Codex exec path (fresh ephemeral session, empty working directory, read-only "
            "sandbox, ChatGPT login only" + (", lean CLI overrides" if LEAN else "") + "). Only D adds the "
            "MCP server and the one-sentence permission to use it; any other tool event fails closed."))})
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("rubric.json", "decision.json"):
        (OUT / ("frozen-" + name)).write_bytes((PLAN / name).read_bytes())
    doc = {
        "issue": ISSUE, "feature": FEATURE, "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": MODEL, "reasoning_effort": EFFORT, "arms": list(ARMS), "secure_gateway_version": __version__,
        "runner_sha256": fsha(Path(__file__)), "fixture_sha256": fsha(FIXTURE),
        "grading_adapter_sha256": eb.adapter_hash(), "lean_cli_overrides": LEAN,
        "disabled_features": list(eb.LEAN_DISABLED_FEATURES) if LEAN else [],
        "plan_files_sha256": {p.name: fsha(p) for p in sorted(PLAN.iterdir())
                              if p.is_file() and p.name not in ("freeze.json", "README.md")},
        "protection_summary_sha256": fsha(summary),
        "jobs_sha256": sha(m["jobs"]), "jobs": len(m["jobs"]), "cases": len(m["cases"]),
        "cases_by_label": pre["selected_by_label"], "budget_estimate": load(PLAN / "budget.json"),
        "decision_rule": ("frozen decision.json (run_319 operationalization): ADOPT iff protection gate passes AND "
                          "correct locally restored result >= 80% of A-eligible tool_solvable cases AND one-sided "
                          "exact sign test (D correct vs C all-pass, solvable cases) p < 0.05 AND <= 1 A-eligible "
                          "no_calculation/impossible case has a D tool call AND no C/D trajectory leaks an original or "
                          "computed value AND no duplicated inference; otherwise REJECT"),
        "ungraded": ("one single-case re-grade after a failed quote check; remaining ungraded cases are bounded: the "
                     "decision stands only if identical when every ungraded case is excluded, D-wins, C-wins, "
                     "both-fail or both-pass; otherwise UNDECIDED_RERUN_UNGRADED"),
        "limitations": DESIGN.get("limitations", [
            "Interpreter and grader are the same model family.",
            "Same OS user; no hard filesystem jail for the MCP fixture.",
            "Results are not comparable to the 2.11.1 gpt-6.1-sol run (model and transport differ)."]),
    }
    doc.update(DESIGN.get("freeze_extra", {}))
    dump(PLAN / "freeze.json", doc)
    print(json.dumps({"jobs": doc["jobs"], "cases": doc["cases"], "budget": doc["budget_estimate"]["raw_tokens"]}))


def verified():
    f = load(PLAN / "freeze.json")
    for name, digest in f["plan_files_sha256"].items():
        if fsha(PLAN / name) != digest:
            raise SystemExit("plan file changed: " + name)
    for name in ("rubric.json", "decision.json"):
        if fsha(OUT / ("frozen-" + name)) != f["plan_files_sha256"][name]:
            raise SystemExit("run copy changed: " + name)
    if fsha(PLAN / "offline" / FEATURE / "summary.json") != f["protection_summary_sha256"]:
        raise SystemExit("protection summary changed")
    if (fsha(Path(__file__)) != f["runner_sha256"] or fsha(FIXTURE) != f["fixture_sha256"]
            or eb.adapter_hash() != f["grading_adapter_sha256"] or MODEL != f["model"]):
        raise SystemExit("runner, fixture, grading adapter or model changed since freeze")
    m = load(PLAN / "manifest.json")
    if sha(m["jobs"]) != f["jobs_sha256"]:
        raise SystemExit("jobs differ from freeze")
    return m


# --------------------------------------------------------------------------- transport

def run_process(command, prompt, cwd, env):
    """The only process boundary of the interpretation path (replaced by the fake harness)."""
    return capture_worker_process(command, prompt, timeout=600, cwd=cwd, env=env, new_process_group=True, check=False)


def lean_worker(request):
    """The only model boundary of the grading path (replaced by the fake harness)."""
    return eb.run_lean_worker(request)


def arm_disabled_features(arm):
    """#372 fail-closed CLI feature set; only the tool arm keeps code-mode host."""
    return tuple(f for f in eb.LEAN_DISABLED_FEATURES if not (arm == "D" and f == CODE_MODE_HOST))


def codex_command(codex, output, instructions_file, fixture=None, provider=None, disabled=None):
    """run_319 argv with optional lean overrides; ``provider`` is only for the offline probe."""
    command = [codex, "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
               "--sandbox", "read-only", "--model", MODEL, "--json", "--output-last-message", str(output)]
    if provider is None:
        command += ["-c", 'forced_login_method="chatgpt"']
    command += ["-c", 'approval_policy="never"', "-c", "project_doc_max_bytes=0", "-c", 'developer_instructions=""',
                "-c", 'web_search="disabled"', "-c", "model_reasoning_effort=" + json.dumps(EFFORT)]
    if LEAN:
        command += ["-c", "model_instructions_file=" + json.dumps(str(instructions_file))]
        for feature in (eb.LEAN_DISABLED_FEATURES if disabled is None else disabled):
            command += ["--disable", feature]
    else:
        command += ["-c", "features.multi_agent=false"]
    if fixture is not None:
        params = {"command": str(Path(sys.executable).resolve()), "args": [str(FIXTURE.resolve()), "--fixture", str(fixture)],
                  # required: Codex waits for the server before the turn and fails closed if it cannot
                  # start. Without it, codex-cli 0.167.2 starts the turn before the Python fixture has
                  # answered tools/list (~1.2 s) and the tool is silently absent (transport-probe.json).
                  "required": True,
                  "enabled_tools": [TOOL], "startup_timeout_sec": 30, "tool_timeout_sec": 30,
                  "tools." + TOOL + ".approval_mode": "approve"}
        for k, v in params.items():
            command += ["-c", "mcp_servers." + SERVER + "." + k + "=" + json.dumps(v)]
    for k, v in (provider or {}).items():
        command += ["-c", k + "=" + json.dumps(v)]
    return command + ["-"]


def audit_events(raw, allow_tool):
    """run_319 audit plus evaluation_batch.parse_events usage-limit classification.

    #372 disables ``code_mode_host`` in the lean adapter, and codex-cli 0.167.2
    then emits one fixed warning item before the turn starts. As in
    ``evaluation_batch.parse_events`` exactly that item, once, before
    ``turn.started`` is accepted; every other non-message item still fails closed.
    """
    calls, usage, completed, started, warned = [], None, False, False, False
    for line in raw.splitlines():
        if not line.strip():
            continue
        event = strict_json(line)
        kind = event.get("type") if isinstance(event, dict) else None
        if kind in ("error", "turn.failed"):
            detail = event.get("error") if kind == "turn.failed" else event
            message = detail.get("message") if isinstance(detail, dict) else None
            if isinstance(message, str) and any(m in message.lower() for m in eb._LIMIT_MARKERS):
                raise UsageLimit()
            raise ValueError("ProviderFailure")
        if isinstance(kind, str) and kind.startswith("item."):
            item = event.get("item", {})
            typ = item.get("type")
            if (kind == "item.completed" and not started and not warned and isinstance(item, dict)
                    and set(item) == {"id", "type", "message"} and typ == "error"
                    and item.get("message") == eb.CODE_MODE_HOST_DISABLED_WARNING):
                warned = True
                continue
            if typ == "mcp_tool_call":
                if not allow_tool or item.get("server") != SERVER or item.get("tool") != TOOL:
                    raise ValueError("UnexpectedTool")
                if kind == "item.completed":
                    calls.append(item)
            elif typ not in ("agent_message", "reasoning"):
                raise ValueError("UnexpectedTool")
        elif kind == "turn.completed":
            if completed:
                raise ValueError("DuplicateTurn")
            completed, usage = True, event.get("usage")
        elif kind == "turn.started":
            started = True
        elif kind != "thread.started":
            raise ValueError("UnexpectedEvent")
    if not completed or not isinstance(usage, dict) or any(
            type(usage.get(k)) is not int for k in ("input_tokens", "output_tokens")):
        raise ValueError("MissingUsage")
    return calls, usage


def interpret_call(job, case):
    arm, request = job["arm"], job["request"]
    codex = shutil.which("codex")
    if codex is None:
        raise ValueError("CodexUnavailable")
    env = {k: v for k, v in os.environ.items() if k in ENV_KEYS}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="sg-319r-") as directory:
        root = Path(directory)
        workspace, owner = root / "workspace", root / "owner"
        workspace.mkdir()
        owner.mkdir()
        instructions = root / "instructions.md"
        instructions.write_text(eb.LEAN_BASE_INSTRUCTIONS, encoding="utf-8")
        fixture = token = None
        if arm == "D":
            session, payload = capture(case)
            selected, reason = bind(case, session, payload)
            if (reason or selected != case["operand_aliases"] or payload["input"][0]["content"] != case["arms"]["D"]["input"]
                    or payload.get("instructions", "") != case["arms"]["D"]["instructions"]
                    or aliases_of(session) != case["arms"]["D"]["aliases"]):
                raise ValueError("CaptureDrift")
            fixture, token = write_owner(owner, case, selected, session)
        output = root / "last.txt"
        command = codex_command(codex, output, instructions, fixture, disabled=arm_disabled_features(arm))
        prompt = (wrapper(arm) + json.dumps(request["messages"], ensure_ascii=False)).encode("utf-8")
        proc = run_process(command, prompt, workspace, env)
        calls, usage = audit_events(proc.stdout, arm == "D")
        if proc.returncode:
            raise ValueError("WorkerExitNonzero")
        # #372: the CLI's tool router logs every failed tool call on stderr. The no-tool
        # arms must stay tool-free, so such a log fails them closed. The tool arm keeps
        # code mode enabled to reach the MCP tool, and a successful non-MCP nested call
        # inside exec leaves no event and no stderr line; that blind spot is disclosed.
        stderr_tool_log = b"codex_core::tools" in (proc.stderr or b"")
        if arm != "D" and stderr_tool_log:
            raise ValueError("UnexpectedTool")
        final = output.read_text(encoding="utf-8")
        if not final.strip():
            raise ValueError("EmptyAnswer")
        trace = [{"tool": TOOL, "arguments": c.get("arguments"), "result": c.get("result"),
                  "status": c.get("status"), "error": bool(c.get("error"))} for c in calls]
        result = {"job_id": request["job_id"], "response": final, "tool_trace": trace, "tool_calls": len(calls),
                  "usage": usage, "metadata": {"fresh_session": True, "requested_model": MODEL, "tool_events": len(calls),
                                               "tool_allowlist_verified": True, "lean_cli_overrides": LEAN,
                                               "code_mode_host": CODE_MODE_HOST not in arm_disabled_features(arm),
                                               "stderr_tool_log": stderr_tool_log}}
        if arm == "D":
            owner_session = gateway.GatewaySession(load_session(owner / "session.enc", token, "arithmetic-fixture"))
            result["restored"] = owner_session.restore(final)
            result["derived_aliases"] = aliases_of(owner_session)
        if arm in ("C", "D"):
            visible = json.dumps({"task": case["arms"][arm]["input"], "trace": trace, "answer": final}, ensure_ascii=False)
            result["provider_value_leak"] = contains_secret(visible, secret_values(case))
    return {"status": "completed", "result": result, "elapsed_seconds": time.monotonic() - started,
            "raw_tokens": usage["input_tokens"] + usage["output_tokens"]}


def stop_for_limit():
    print("USAGE LIMIT reached - stopped cleanly; rerun --run to resume.", flush=True)
    sys.exit(3)


def interpret(m):
    path, failed_path = OUT / "first-responses.jsonl", OUT / "failed-calls.jsonl"
    jobs = {j["request"]["job_id"]: j for j in m["jobs"]}
    done = {}
    for r in rows(path):
        job = jobs.get(r["job_id"])
        res = r.get("result", {})
        if (job is None or r["job_id"] in done or r["status"] != "completed" or res.get("job_id") != r["job_id"]
                or r["arm"] != job["arm"] or res["metadata"].get("fresh_session") is not True
                or res["metadata"].get("requested_model") != MODEL
                or (job["arm"] != "D" and res["tool_calls"] != 0)):
            raise SystemExit("invalid or duplicated saved response")
        done[r["job_id"]] = r
    cases = {c["case_id"]: c for c in m["cases"]}
    pending = [j for j in m["jobs"] if j["request"]["job_id"] not in done]
    print("interpretations saved", len(done), "pending", len(pending), flush=True)

    def one(job):
        try:
            return interpret_call(job, cases[job["case_id"]])
        except UsageLimit:
            return {"status": "limit"}
        except Exception as exc:  # fixed category only
            return {"status": "failed", "error_category": type(exc).__name__}

    for pos in range(0, len(pending), WORKERS):
        chunk = pending[pos:pos + WORKERS]
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            results = list(pool.map(one, chunk))
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
        print("interpreted", min(pos + WORKERS, len(pending)), "of", len(pending), flush=True)
    saved = {r["job_id"] for r in rows(path)}
    missing = [j for j in m["jobs"] if j["request"]["job_id"] not in saved]
    if missing:
        raise SystemExit(f"{len(missing)} interpretations failed; rerun --run to retry them")
    return {r["job_id"]: r for r in rows(path)}


# --------------------------------------------------------------------------- grading

def job_for(m, cid, arm):
    return next(j for j in m["jobs"] if j["case_id"] == cid and j["arm"] == arm)


def grade_request(m, case, byjob):
    """run_319 grader material: blind labels, model-visible input, alias mapping, tool transcript."""
    cid = case["case_id"]
    labels = list(ARMS)
    random.Random(int(sha([ISSUE, "replication", cid])[:16], 16)).shuffle(labels)
    blind = {f"R{i + 1}": x for i, x in enumerate(labels)}
    responses, criteria = {}, []
    for label, arm in blind.items():
        result = byjob[job_for(m, cid, arm)["request"]["job_id"]]["result"]
        text = result["response"]
        if result.get("tool_trace"):
            text += "\nSANITIZED TOOL TRANSCRIPT: " + json.dumps(result["tool_trace"], ensure_ascii=False, sort_keys=True)
        a = case["arms"][arm]
        responses[label] = {"response": text, "model_visible_input": a["input"],
                            "synthetic_alias_mapping": result.get("derived_aliases", a["aliases"])}
        for criterion in case["applicable_by_condition"][arm]:
            x = m["criterion_definitions"][criterion]
            criteria.append({"id": label + "::" + criterion, "description": "For " + label + ": " + x["pass"]
                             + " Failure: " + x["fail"] + " Positive example: " + x["positive_example"]
                             + " Negative example: " + x["negative_example"]})
    # The grader is a trusted party: it already receives the original text with the
    # raw operands. Naming the case's correct value keeps answer_value verdicts
    # mechanical instead of asking the grader to recompute the arithmetic itself.
    msg = {"original": case["original"], "expected_case_behavior": case["expected"],
           "correct_answer": case["gold"], "responses": responses}
    request = {"role": "grade", "job_id": sha([ISSUE, "replication", cid, "grade"])[:32], "model": MODEL,
               "max_output_tokens": 2048, "reasoning_effort": EFFORT,
               "messages": [{"role": "system", "content": GRADE_SYSTEM},
                            {"role": "user", "content": json.dumps(msg, ensure_ascii=False)}],
               "criteria": criteria}
    return request, blind, responses


def quotes_valid(grades, request, responses):
    expected = [c["id"] for c in request["criteria"]]
    if not isinstance(grades, list) or sorted(g.get("id") for g in grades if isinstance(g, dict)) != sorted(expected):
        return False
    return all(type(g.get("passed")) is bool and isinstance(g.get("evidence"), str) and g["evidence"].strip()
               and g["evidence"] in responses[g["id"].split("::", 1)[0]]["response"] for g in grades)


def grade_call(request):
    try:
        return {"status": "completed", "result": lean_worker(request)}
    except eb.UsageLimitReached:
        return {"status": "limit"}
    except ValueError as exc:
        return {"status": "failed", "error": type(exc).__name__}


def grade(m, byjob):
    path = OUT / "first-grades.jsonl"
    final = {r["case_id"] for r in rows(path) if r["kind"] == "case" and r["status"] != "failed"}
    pending = [c for c in m["cases"] if c["case_id"] not in final]
    print("grades saved", len(final), "pending", len(pending), flush=True)
    for pos in range(0, len(pending), GRADE_BATCH):
        chunk = pending[pos:pos + GRADE_BATCH]
        built = {c["case_id"]: grade_request(m, c, byjob) for c in chunk}
        request, labels = eb.build_grade_batch({k: v[0] for k, v in built.items()},
                                               job_id=sha([ISSUE, "replication", "gb"] + sorted(built))[:32],
                                               seed=SEED + pos)
        res = grade_call(request)
        if res["status"] == "limit":
            stop_for_limit()
        append(path, {"kind": "call", "role": "grade_batch", "cases": sorted(built),
                      "usage": res.get("result", {}).get("usage"), "status": res["status"], "error": res.get("error")})
        try:
            split = eb.split_grade_batch(res["result"]["grades"], labels) if res["status"] == "completed" else {}
        except (ValueError, KeyError, TypeError, AttributeError):
            split = {}
        for cid, (req, blind, responses) in built.items():
            grades, how = split.get(cid), "batch"
            if not quotes_valid(grades, req, responses):
                retry = dict(req)
                retry["job_id"] = sha([ISSUE, "replication", cid, "regrade"])[:32]
                retry["messages"] = list(req["messages"]) + [{"role": "user", "content": RETRY}]
                single = grade_call(retry)
                if single["status"] == "limit":
                    stop_for_limit()
                append(path, {"kind": "call", "role": "regrade_single", "cases": [cid],
                              "usage": single.get("result", {}).get("usage"), "status": single["status"],
                              "error": single.get("error")})
                if single["status"] == "completed":
                    grades, how = single["result"].get("grades"), "regrade"
                else:
                    grades, how = None, "failed"  # transport failure: retried on resume
            ok = quotes_valid(grades, req, responses)
            append(path, {"kind": "case", "case_id": cid, "how": how,
                          "status": "completed" if ok else ("ungraded" if how != "failed" else "failed"),
                          "blind_labels": blind, "grades": grades if ok else None})
        print("graded", min(pos + GRADE_BATCH, len(pending)), "of", len(pending), flush=True)


# --------------------------------------------------------------------------- report

def evaluate(m, graded, byjob, offline, assign=None):
    """Frozen rule as operationalized by run_319. ``assign`` sets ungraded cases for the bound rule:
    None -> ungraded excluded; (C, D) booleans -> eligible with A passing."""
    results = {}
    for case in m["cases"]:
        cid = case["case_id"]
        d = byjob[job_for(m, cid, "D")["request"]["job_id"]]["result"]
        rec = graded.get(cid)
        if rec and rec["status"] == "completed":
            arms = {}
            for g in rec["grades"]:
                label, k = g["id"].split("::", 1)
                arms.setdefault(rec["blind_labels"][label], {})[k] = g["passed"]
            allpass = {a: all(v.values()) for a, v in arms.items()}
        elif assign is not None:
            arms = {"D": {k: assign[1] for k in ("operation_aliases", "restored_result", "unit")}}
            allpass = {"A": True, "C": assign[0], "D": assign[1]}
        else:
            continue
        results[cid] = {"case": case, "arms": arms, "allpass": allpass, "d": d}
    eligible = [v for v in results.values() if v["allpass"]["A"]]
    solvable = [v for v in eligible if v["case"]["label"] == "tool_solvable"]
    controls = [v for v in eligible if v["case"]["label"] != "tool_solvable"]
    wins = losses = correct = 0
    for v in solvable:
        c, dr, graded_d = v["case"], v["d"], v["arms"]["D"]
        gold = numeric(c["gold"])
        ok = bool(gold and gold[0] in numeric(dr["restored"]) and dr["tool_calls"] >= 1 and v["allpass"]["D"]
                  and all(graded_d.get(k, False) for k in ("operation_aliases", "restored_result", "unit")))
        correct += ok
        wins += ok and not v["allpass"]["C"]
        losses += v["allpass"]["C"] and not ok
    control_calls = sum(v["d"]["tool_calls"] > 0 for v in controls)
    responses = list(byjob.values())
    leaks = sum(r["result"].get("provider_value_leak", False) for r in responses if r["arm"] in ("C", "D"))
    ids = [r["job_id"] for r in responses]
    duplicates = len(ids) - len(set(ids))
    p = sign(wins, losses)
    rate = correct / len(solvable) if solvable else 0
    adopt = (offline["protection_gate_passed"] and rate >= .8 and p < .05 and control_calls <= 1
             and leaks == 0 and duplicates == 0)
    criterion = {k: {a: {"pass": sum(v["arms"].get(a, {}).get(k) is True for v in eligible),
                         "applicable": sum(k in v["arms"].get(a, {}) for v in eligible)} for a in ARMS}
                 for k in m["criterion_definitions"]}
    return {"decision": "ADOPT" if adopt else "REJECT", "eligible": len(eligible),
            "A_C_D_passes": {a: sum(v["allpass"].get(a, False) for v in eligible) for a in ARMS},
            "solvable_eligible": len(solvable), "correct_restored": correct, "correct_restored_rate": rate,
            "D_only": wins, "C_only": losses, "p_one_sided": p, "control_cases": len(controls),
            "unnecessary_or_forbidden_tool_cases": control_calls,
            "all_control_cases_with_D_tool_call": sum(
                byjob[job_for(m, c["case_id"], "D")["request"]["job_id"]]["result"]["tool_calls"] > 0
                for c in m["cases"] if c["label"] != "tool_solvable"),
            "provider_value_leak_trajectories": leaks, "duplicate_inferences": duplicates, "criteria": criterion}


def report():
    m = verified()
    byjob = {r["job_id"]: r for r in rows(OUT / "first-responses.jsonl")}
    graded = {}
    for r in rows(OUT / "first-grades.jsonl"):
        if r["kind"] == "case":
            graded[r["case_id"]] = r
    offline = load(PLAN / "offline" / FEATURE / "summary.json")
    missing_jobs = [j["request"]["job_id"] for j in m["jobs"] if j["request"]["job_id"] not in byjob]
    missing = [c["case_id"] for c in m["cases"] if graded.get(c["case_id"], {}).get("status") not in ("completed", "ungraded")]
    ungraded = sorted(c for c, r in graded.items() if r["status"] == "ungraded")
    usage = {"calls": 0, "raw_tokens": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    for u in [r["result"]["usage"] for r in byjob.values()] + [
            r["usage"] for r in rows(OUT / "first-grades.jsonl") if r["kind"] == "call" and r.get("usage")]:
        usage["calls"] += 1
        usage["raw_tokens"] += u["input_tokens"] + u["output_tokens"]
        for k in ("input_tokens", "cached_input_tokens", "output_tokens"):
            usage[k] += u.get(k, 0)
    doc = {"issue": ISSUE, "feature": FEATURE, "model": MODEL, "arms": list(ARMS),
           "freeze_sha256": fsha(PLAN / "freeze.json"), "usage": usage,
           "raw_tokens_per_case": round(usage["raw_tokens"] / len(m["cases"])),
           "failed_calls_retried": len(rows(OUT / "failed-calls.jsonl")), "ungraded": ungraded, "protection": offline}
    if missing_jobs or missing:
        doc["status"] = "incomplete"
        doc["missing_interpretations"] = len(missing_jobs)
        doc["missing_grades"] = missing
    else:
        doc["status"] = "completed"
        if ungraded:
            scenarios = {"ungraded_excluded": None, "ungraded_D_wins": (False, True), "ungraded_C_wins": (True, False),
                         "ungraded_both_fail": (False, False), "ungraded_both_pass": (True, True)}
            bounds = {}
            for name, value in scenarios.items():
                g = {k: v for k, v in graded.items() if v["status"] == "completed"}
                if value is None:
                    bounds[name] = evaluate(m, g, byjob, offline)
                else:
                    bounds[name] = evaluate(m, g, byjob, offline, value)
            doc["bounds"] = bounds
            decisions = {b["decision"] for b in bounds.values()}
            doc["result"] = dict(bounds["ungraded_excluded"])
            doc["result"]["decision"] = decisions.pop() if len(decisions) == 1 else "UNDECIDED_RERUN_UNGRADED"
        else:
            doc["result"] = evaluate(m, graded, byjob, offline)
    dump(OUT / "report.json", doc)
    shown = {k: v for k, v in doc.items() if k not in ("protection", "bounds")}
    if "result" in shown:
        shown["result"] = {k: v for k, v in shown["result"].items() if k != "criteria"}
    print(json.dumps(shown, ensure_ascii=False, indent=1)[:4000])
    return doc


def main():
    if MODEL != "gpt-6-luna" and not os.environ.get("SG_ALLOW_OTHER_MODEL"):
        raise SystemExit("this plan is preregistered on gpt-6-luna; MODEL=" + MODEL)
    parser = argparse.ArgumentParser()
    for flag in ("prepare", "protection", "freeze", "run", "report"):
        parser.add_argument("--" + flag, action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    if args.protection:
        protection()
    if args.freeze:
        freeze()
    if args.run:
        m = verified()
        byjob = interpret(m)
        grade(m, byjob)
        report()
    elif args.report:
        report()


if __name__ == "__main__":
    main()
