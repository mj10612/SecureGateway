# Real-LLM evaluation cost: lean sessions and batching (issue #364)

Real-LLM comprehension evaluations run through `codex exec` on the owner's ChatGPT
subscription (never an API key). Before 2.15.0 every interpretation and every
grade was its own fresh session, and each session carried about 15,100 fixed
input tokens of agent instructions and tool definitions. In the #313 run, that
fixed overhead made up most of the 5.56 M raw tokens (63,200 per case) and
repeatedly exhausted 5-hour and weekly limits.

`secure_gateway.evaluation_batch` (2.15.0) is a second, explicitly selected
adapter. The frozen native adapter `evaluation_codex_worker` is unchanged, so
saved evidence and reference audits that pin its hash stay valid.

## What changes

| Lever | How | Measured effect (codex-cli 0.167.1) |
|---|---|---|
| Lean session | `--disable` for 27 tool features a text task never needs (28 from 2.17.1: `code_mode_host`, #372), and `model_instructions_file` pointing to a one-line neutral instruction | fixed input per call 15,100 → about 7,070 tokens |
| Interpretation batching | `build_interpret_batch`: up to 32 independent tasks of the same condition in one call, shuffled with a recorded seed, opaque labels `T1..Tn`, JSON answer list split by `parse_interpret_batch` | batch 8: 264 answers in 33 calls; **not yet accepted** (see below) |
| Grading batching | `build_grade_batch`: several cases' unchanged per-case grade requests in one call, criterion IDs prefixed `K1::…`, split by `split_grade_batch` | batch 2 accepted; batch 4 rejected |
| Budget preview | `estimate_budget(...)` returns calls and raw tokens before a run | |
| Clean stop | a usage or credit limit raises `UsageLimitReached` (fixed message) so runners stop and resume | |

The overrides exist only on the argv of the evaluation subprocess. The adapter
never writes the user's `config.toml`, auth files or Orca account settings;
ordinary Codex CLI use keeps its own configuration (tested in
`tests/test_evaluation_batch.py`). To use a particular subscription account for a
run, set `CODEX_HOME` for that command only.

## What stays the same

- Fresh ephemeral session, empty working directory, read-only sandbox,
  `forced_login_method="chatgpt"`, no API-key fallback, environment allowlist.
- Any event other than an agent message or reasoning fails the call closed,
  including CLI warnings, with one exact exception described below.

## Code-mode tool calls (issue #372)

What the event check did **not** cover before 2.17.1: on codex-cli 0.167.x the
bundled metadata of the evaluation models (`gpt-6-luna`, `gpt-6.1-sol`, …) is
`tool_mode: "code_mode_only"`. The session therefore offers the model an `exec`
tool (JavaScript in a V8 isolate without Node, file system or network) that can
call nested tools, plus `wait`, `request_user_input(_async)` and collaboration
tools. An offline probe (real codex-cli 0.167.2, local fake model endpoint,
empty temporary `CODEX_HOME`, no account or model call;
`docs/evaluations/issue372/probe_372_code_mode.py`, results in
`probe-results.json` next to it) showed:

- A successful `exec` call leaves **no** item in `codex exec --json` events and
  nothing on stderr. With the 2.15.0–2.17.0 lean flags, nested tools reachable
  from `exec` were `apply_patch` (rejected by the read-only sandbox),
  `clock__curr_time` (succeeded) and MCP resource listing (no servers
  configured). No nested tool could read or list files, run a command or reach
  the network. So "no tool events, fails closed on tool use" was stronger than
  what the check could see: it saw MCP/command/file-change items, not code mode.
- The `code_mode`/`code_mode_only` features do not remove `exec` (the model
  metadata decides). Disabling `code_mode_host` keeps `exec` offered but makes
  every `exec` and `wait` call fail inside the CLI ("code-mode host is
  disabled"); the CLI then emits one fixed warning item before the turn starts.
- Every failed tool call (rejected `exec`, `apply_patch`, unsupported
  collaboration tool, malformed call) is logged on stderr by the CLI's tool
  router (`codex_core::tools::router`) even though no event is emitted.
- The frozen native adapter (`evaluation_codex_worker`, unchanged) disables only
  multi-agent and web search, so its `exec` also reaches `exec_command`,
  `write_stdin`, `view_image`, `apply_patch`, goal and clock tools. In the probe
  `exec_command` was rejected ("blocked by policy") and `view_image` opened a
  file outside the working directory but rejected it as not an image; whether a
  command would run under the owner's real setup was not tested. Such nested
  calls emit no event either, so the native "tool events 0" also did not cover
  code mode.

From 2.17.1 the lean session disables `code_mode_host` as well (28 features),
`parse_events` accepts exactly that one warning text once before
`turn.started` (any other text, position or repetition still fails closed), and
`run_lean_worker` fails closed when stderr contains the tool-router log target.
With these settings no executable tool can run, and every executable-tool
attempt is rejected; result metadata lists the checks in `tool_call_checks`.
Remaining, disclosed: `request_user_input_async` stays offered and returns
`{"accepted":true}` without a router log; it executes nothing and its question
surfaces as an extra `agent_message` item (the final answer file keeps the last
message). A model-metadata override (`model_catalog_json` with `tool_mode`
unset) removes `exec` from the offer offline, but whether it overrides the
subscription's remote model catalog cannot be verified without an account, so
it is not used.

Runs frozen with an earlier adapter hash keep that hash and are not re-run; a
frozen runner that checks the hash (for example `run_joint.py`) refuses to
resume under 2.17.1 and must be resumed from its frozen commit.

Earlier answers: no evidence suggests that any saved answer used a tool. The
CLI's `turn.completed` usage sums every model request of the turn (the probe:
one request 11 input tokens, one tool round trip 22), and a round trip resends
the whole prompt, so a call with a tool call reports at least twice its fixed
input. All 279 lean `gpt-6-luna` interpretation calls of
`comprehension-2.11.1/309/comprehension-luna` reported 7,399–7,487 input
tokens and its 60 grade calls 8,107–12,910, all below 2 × 7,070. In the native
runs (fixed input ≈ 14,300+) every directory without an MCP tool arm stays below
22,200 input tokens per call, also below 2 × the fixed input. Directories with
an intended MCP tool arm (`arithmetic-mcp*`, `319/comprehension`) show expected
round trips that are visible as `mcp_tool_call` items. In `eval-cost-364`
stages G, G2 and I, calls of the same shape stay within 1.19× of each other
(4-case grades 13,518–16,071, 2-case grades 10,241–12,086, single re-grades
8,639–9,148, 8-task interpretations 9,513–9,727), so no call doubled. The
check relies on the reported usage only; it rules out a second model request
in those calls, not a hypothetical tool that runs without one.
- An interpreter still never sees the original text, gold behaviour, rubric or
  another condition's answer. Inside one batch the tasks of the **same
  condition** can see each other; the batch rules tell the model to treat each
  task alone. This is a disclosed limitation, measured below.
- Graders still need a verified verbatim quote for every verdict, checked per
  case against that case's own responses. A failing case is re-graded once on
  its own; if it still fails it is ungraded and the bound rule applies.
- Frozen rubric, decision rule and resume-from-validated-inputs are unchanged.

## Model

New preregistered runs use `DEFAULT_EVAL_MODEL = "gpt-6-luna"` (owner's choice,
2026-11-12). Runs already frozen with `gpt-6.1-sol` keep it; never compare arms
or runs produced by different models.

## Validation against the individual method

The preregistration, script and evidence are in
`docs/evaluations/eval-cost-364/` (see its `README.md` for all numbers). The
acceptance thresholds were fixed before any batched call. Summary on the 88
#313 cases (`gpt-6.1-sol`, reference 63,200 raw tokens per case):

| Configuration | Raw tokens / case | Validation status |
|---|---|---|
| lean grading, batch 4 | (grading only) 5,025 | rejected: criterion agreement 0.947 < 0.95 |
| lean grading, batch 2 | (grading only) 6,748 | **accepted** (0.956 / 0.947) |
| lean interpretation batch 8 + grading batch 2 | **10,516 (−83%)** | **not accepted**: arm C passes −7 (limit ±5) |
| lean interpretation 1 per item + grading batch 2 (preregistered fallback) | ≈ 29,500 (−53%, estimate) | usable now |

Current guidance: use the lean session and grading batch 2. Do not use
interpretation batching for a decision run until a preregistered check shows it
agrees when both transports are graded by the same grader (the exploratory
analysis in the evidence README attributes the arm-C shift to the grader, not
to interpretation batching, but that is not yet confirmed).

The lean grader is stricter than the native one, mostly on baseline answers that
kept an over-masked public word as an alias. Within one run every arm has the
same grader, so paired comparisons stay fair; never compare pass rates or
decisions across runs that used different transports.

## Case authoring

Only cases whose model-facing input the candidate actually changes are useful
(#309: 85 of 800 authored, 10.6%). Author in small batches and screen each batch
offline (baseline vs candidate payload, no LLM) before authoring more; stop as
soon as the discriminating target is met. Size the next batch from the observed
activation rate instead of a fixed count.

## Running a batched evaluation

```python
from secure_gateway import evaluation_batch as eb

plan = eb.estimate_budget(interpret_jobs=279, grade_cases=93, interpret_batch=1,
                          grade_batch=2, fixed_input_tokens=7070,
                          interpret_content_tokens=400, grade_content_tokens=2500)
# One lean call per interpretation (validated configuration):
result = eb.run_lean_worker(interpret_request)          # may raise UsageLimitReached
# Grading: combine two unchanged per-case grade requests, then split and verify
# every quote against that case's own responses.
grade_request, labels = eb.build_grade_batch({case_a: req_a, case_b: req_b},
                                             job_id=..., seed=...)
per_case = eb.split_grade_batch(eb.run_lean_worker(grade_request)["grades"], labels)
```

`build_interpret_batch` / `parse_interpret_batch` with `run_lean_worker(...,
batch=True)` are available for the confirmation run described above.

Save every call's result as soon as it returns, show the budget before starting,
and stop on `UsageLimitReached`; rerunning the same command resumes.
