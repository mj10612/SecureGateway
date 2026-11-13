"""#319 natural-wording holdout: the corrected replication on gpt-6-luna.

Why this design exists: the 2.16.3 replication (``319/plan-replication``) was
declared INVALID in issue #319. The product rejected the alias form the model
sees (#375, fixed) and every case text told the interpreter to call the local
arithmetic tool and to return a result alias, so arm A (original text, no tool)
could not pass and the analysis set collapsed to three cases.

This plan reuses the 2.16.3 machinery unchanged except for the items below, all
preregistered before any model call:

1. **Fresh holdout.** Cases were authored by isolated authors that received the
   issue title/body and the natural-wording specification only
   (``plan/author_319_natural.py``). No case text names a tool, alias, mask,
   placeholder or evaluation, and no earlier case, response or answer key was
   provided.
2. **Arm-specific CLI features (#372).** A/C keep ``code_mode_host`` disabled so
   a no-tool arm cannot run code behind the event audit. D alone keeps it
   enabled, because codex-cli 0.167.2 exposes an MCP tool only as a nested tool
   of the code-mode ``exec`` tool. Tool availability is the experiment variable;
   the asymmetry and the resulting ``exec`` blind spot are disclosed.
3. **D prompt carries the tool contract.** The old per-case instruction is gone;
   only D's worker prompt states that the tool exists, its argument shape and
   that the host restores a returned alias for the user.
4. **No-tool arms are graded on the answer value.** The alias-return protocol is
   a D-only condition, so A and C get the additional rubric criterion
   ``answer_value``; D keeps run_319's ``operation_aliases`` /
   ``restored_result`` / ``unit`` rule. Every other criterion is verbatim from
   ``319/plan/rubric.json``.
5. **Offline alias-form probe (#375).** The stdio fixture probe now submits both
   the bare ``private_symbol_N`` form and the displayed ``⟦private_symbol_N⟧``
   form and requires both to compute and restore to the gold.

    uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_natural.py --prepare
    uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_natural.py --protection
    uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_natural.py --freeze
    uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_natural.py --run
    uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_natural.py --report
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PLAN = ROOT / "319" / "plan-natural"
OUT = ROOT / "319" / "comprehension-natural"
SPEC_MODEL = "gpt-6-luna"

_spec = importlib.util.spec_from_file_location("run_319_replication", HERE / "run_319_replication.py")
r = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r)

if r.MODEL != SPEC_MODEL:
    raise SystemExit(f"this plan is preregistered on {SPEC_MODEL}; MODEL={r.MODEL}")

PROMPT_D_NATURAL = (
    "Complete the supplied task. A local tool, local_alias_arithmetic, is available inside the exec tool as "
    "tools.mcp__alias_arithmetic__local_alias_arithmetic({\"operation\": \"add\"|\"subtract\"|\"multiply\"|"
    "\"date_difference\", \"aliases\": [the two aliases shown in the task]}) and returns only a new result alias. "
    "Use it when the task needs a value you cannot read; the local host restores result aliases for the user, so put "
    "the returned alias exactly where the number belongs in your answer. Do not use other tools, commands, files, "
    "browsing, agents or skills. Limit output to 512 tokens.\n")

r.PLAN, r.OUT = PLAN, OUT
r.SOURCES = (("ns", PLAN / "natural-solvable-authored.json"),
             ("ns2", PLAN / "natural-solvable2-authored.json"),
             ("nn", PLAN / "natural-nocalc-authored.json"),
             ("ni", PLAN / "natural-impossible-authored.json"))
r.PROTECTION_KEY = "319/plan-natural"
r.PROMPTS = {"A": r.PROMPT_NO_TOOL, "C": r.PROMPT_NO_TOOL, "D": PROMPT_D_NATURAL}
r.NO_TOOL_ANSWER_CRITERION = "answer_value"
r.RUBRIC_SRC = PLAN / "rubric-natural.json"

DESIGN_SUMMARY = (
    "Natural-wording holdout. Fresh isolated-author cases that never mention a tool, alias or mask; A and C keep "
    "code_mode_host disabled (#372) while D alone keeps code mode to reach the local MCP tool; D's prompt carries the "
    "tool contract; A/C are graded on answer_value plus unit and D on operation_aliases/restored_result/unit (run_319 "
    "rule). The 2.16.3 replication was declared INVALID in issue #319.")
r.DESIGN = {
    "transport": (
        "All arms: same Codex exec path (fresh ephemeral session, empty working directory, read-only sandbox, ChatGPT "
        "login only, lean CLI overrides). A/C also disable code_mode_host (#372) so a tool cannot run behind the event "
        "audit; D alone keeps code_mode_host enabled because the MCP tool is reachable only as a nested tool of exec, "
        "and only D adds the MCP server. Any other tool event, any tool-router stderr line in A/C, and any unexpected "
        "event fails closed."),
    "limitations": [
        "Interpreter and grader are the same model family.",
        "Same OS user; no hard filesystem jail for the MCP fixture.",
        "D keeps code-mode host enabled (the MCP tool is only reachable from exec), and a successful non-MCP nested "
        "call inside exec leaves no --json event and no stderr line; A/C are fail-closed, D's exec body is not fully "
        "auditable (disclosed, also in #372).",
        "Results are not comparable to the 2.11.1 gpt-6.1-sol run (model, transport and case wording differ).",
        "The 40/14/26 case counts are the original proportions; the offered 2.18.0 defaults publish numbers, so only "
        "forced-rule operands are masked here (see #374)."],
    "freeze_extra": {"design": DESIGN_SUMMARY, "natural_runner_sha256": r.fsha(Path(__file__)),
                     "natural_runner": str(Path(__file__).relative_to(ROOT)).replace("\\", "/")},
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_rubric():
    """The derived rubric must be the frozen rubric plus exactly the answer_value criterion."""
    base, derived = load(ROOT / "319" / "plan" / "rubric.json"), load(r.RUBRIC_SRC)
    extra = [c for c in derived["criteria"] if c["id"] not in {x["id"] for x in base["criteria"]}]
    kept = [c for c in derived["criteria"] if c["id"] in {x["id"] for x in base["criteria"]}]
    if kept != base["criteria"] or [c["id"] for c in extra] != ["answer_value"]:
        raise SystemExit("rubric-natural.json must be rubric.json plus exactly the answer_value criterion")
    for key, value in base.items():
        if key != "criteria" and derived.get(key) != value:
            raise SystemExit("rubric-natural.json changed a frozen rubric field: " + key)


def check_frozen_runner():
    freeze = PLAN / "freeze.json"
    if not freeze.exists():
        raise SystemExit("plan is not frozen; run --freeze first")
    recorded = load(freeze).get("natural_runner_sha256")
    if recorded != r.fsha(Path(__file__)):
        raise SystemExit("natural runner changed since freeze")


if __name__ == "__main__":
    check_rubric()
    if any(flag in sys.argv for flag in ("--run", "--report")):
        check_frozen_runner()
    r.main()
