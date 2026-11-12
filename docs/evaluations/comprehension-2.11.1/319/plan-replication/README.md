# #319 local arithmetic: preregistered replication plan (prepared, NOT frozen)

Status: **prepared with secure-gateway 2.16.1, not frozen, no model call made.**
`--freeze` currently refuses because only **30** binding tool-solvable cases are available
(40 required). See "Blocker" below.

Runner: [`../../plan/run_319_replication.py`](../../plan/run_319_replication.py).
Model `gpt-6-luna` (`evaluation_batch.DEFAULT_EVAL_MODEL`), reasoning effort `low`,
ChatGPT subscription login only.

## Exact commands

```
# 0. (coordinator, ONE Codex call) author the 10 missing tool-solvable cases
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/author_319_replication_supplement.py
# 1. no model call; rerunnable until frozen (captures inputs, binding pre-check, leak check, budget)
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_replication.py --prepare
# 2. offline protection gate with current code (already run; output in offline/local_arithmetic/)
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_replication.py --protection
# 3. once, before any model call (refuses unless >= 40/14/26 cases, no leak, protection gate present)
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_replication.py --freeze
# 4. resumable; exit code 3 = usage limit reached, rerun the same command later
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_replication.py --run
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_replication.py --report
```

Offline checks (no model, no account):

```
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/probe_319_codex_mcp.py --write
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/validate_319_replication_fake.py
```

## Binding pre-check (`precheck.json`)

Rule from `plan/check_319_binding.py`, applied to every case: each declared confidential operand is
a forced rule (as `normalize_319_forced.py`) and binds to exactly one gateway alias, and no operand
stays visible in the masked task. The capture uses the per-session feature flag
`GatewayFeatures(local_arithmetic=True)`. Additional requirements for `tool_solvable`: the operation
is one the local tool offers (add, subtract, multiply), the authored gold equals the local result,
and the real stdio MCP fixture, driven by an MCP client with the issued aliases, returns a new
alias that restores to the gold.

| Source | Cases | Bind exactly |
|---|---:|---:|
| `replication-batch1-authored.json` | 40 | 40 |
| `replication-batch2-authored.json` | 40 | 40 |

- Binding: **80/80** (2.11.1 code bound 26 to 28; #363 fix confirmed). Capture deterministic 80/80.
- Feature flag on vs off: masked task and instructions identical 80/80. The only difference is
  four extra aliases for `add`, `subtract`, `multiply`, `date_difference`: with the feature on,
  the gateway masks the `operation` enum of its own injected tool schema (a product finding; the
  tool schema in the provider request then lists aliases instead of operation names).
- Excluded, not counted: **10** cases labelled `tool_solvable` that ask for **division**, which the
  local tool does not offer (`b1:ts16`-`ts20`, `b2:holdout_16`-`holdout_20`). The batch author
  specification allowed "divide" for solvable cases.
- Offline fixture probe: 30/30 tool-solvable cases return a new alias that restores to the gold.

Selected (`manifest.json`): **30 tool_solvable, 14 no_calculation, 26 impossible** (70 cases,
210 interpretation jobs). Requirement: 40 / 14 / 26.

## Blocker

30 < 40 tool-solvable cases. `author_319_replication_supplement.py` requests 10 more tool-solvable
cases from a fresh isolated author with the batch specification, restricted to add/subtract/multiply,
and writes `supplement-authored.json`; `--prepare` then includes them automatically (source prefix
`s:`) and re-runs every check. The existing 14 no-calculation and 26 impossible cases already match
the original proportions for 40 solvable cases.

## Provider-visible payload leak check (`payload-leak-check.json`)

Whole-token search for every sensitive operand and every number of the gold (computed value),
outside `private_symbol_N` aliases, in the full gateway request payload (instructions, input,
injected tool schema) and the exact C and D worker prompts: **0 of 80 cases leak**. A is the
original-text control and is excluded by design. Run-time C/D answers and D tool transcripts are
checked again per trajectory by the runner.

## Protection gate (`offline/local_arithmetic/summary.json`)

`plan/offline_protection.py` re-run with 2.16.1 (`--protection`): 29 cases, 0 newly exposed,
exact restore 29/29 baseline and candidate, CI compare exit 0, gate **passed**.

## Transport (`transport-probe.json`, codex-cli 0.167.2)

The probe runs the real Codex CLI with the exact D argv against a local fake Responses endpoint,
with `CODEX_HOME` set to an empty temporary directory (no user configuration, no login) and the real
stdio MCP fixture. Findings:

1. **Lean overrides keep the MCP tool working.** With `LEAN_DISABLED_FEATURES` and the neutral
   `model_instructions_file`, the D turn called the fixture once and the answer restored to the gold.
   First request 36,341 bytes lean vs 63,048 native. `LEAN = True` in the runner. This is verified
   for the CLI plumbing only; whether `gpt-6-luna` finds and uses the tool is what the run measures.
2. **run_319's argv loses the tool (startup race).** Without `mcp_servers.<name>.required = true`,
   the turn starts before the Python fixture answers `tools/list` (about 1.2 s) and the tool is
   silently absent, even with a 5 s model delay (both lean and native). The runner sets
   `required = true` (Codex waits and fails closed if the server cannot start). This may explain why
   only 4 of 12 tool-solvable D answers (plus the unsupported-unit case) in the 2.11.1 run made any
   tool call.
3. **MCP tools are deferred nested tools of the code-mode `exec` tool.** Their name and schema never
   appear in the model request; the model must call `exec` with JavaScript
   (`tools.mcp__alias_arithmetic__local_alias_arithmetic(...)`). Disabling `code_mode_host` makes
   the tool unreachable. The D prompt therefore adds one sentence stating this call contract (the
   product path, gateway `inject_arithmetic_tool`, shows the model a direct schema instead).
4. **`exec` itself emits no event.** A code-mode `exec` call (in C as well) produced no item in
   `codex exec --json`, so the fail-closed audit cannot see it; nested MCP calls do appear as
   `mcp_tool_call`. With the lean overrides the nested tools inside `exec` are `apply_patch`,
   `clock__curr_time` and the MCP resource readers (native also exposes `exec_command` and others).
   This also applies to the lean `evaluation_batch` transport. Disclosed as a limitation.

## Frozen design (applied by `--freeze`)

- Rubric and decision rule: `319/plan/rubric.json` and `decision.json` copied verbatim. Decision as
  operationalized in `run_319.py`: ADOPT iff protection gate passes AND correct locally restored
  result >= 80% of A-eligible tool-solvable cases (graded `operation_aliases`, `restored_result`,
  `unit`, D all-pass, >= 1 tool call, gold in restored answer) AND one-sided exact sign test
  (D correct vs C all-pass) p < 0.05 AND <= 1 A-eligible no-calculation/impossible case with a D tool
  call AND 0 C/D trajectories with an original or computed value AND 0 duplicated inferences.
- Arms (run_319): A original text, no tool; C masked, no tool; D identical masked text plus the
  allowlisted MCP tool. All arms use the same Codex path (fresh ephemeral session, empty working
  directory, read-only sandbox, lean overrides); only D gets the MCP server and the tool sentence.
  Any non-message event other than D's allowlisted MCP call fails closed.
- Grading: run_319 grader material (blind labels, model-visible input, alias mapping, sanitized tool
  transcript, `GRADE_SYSTEM` verbatim), batched by 2 with `build_grade_batch`/`split_grade_batch`
  on the lean worker, per-case quote and criterion-set verification, one single-case re-grade.
  Remaining ungraded cases: the decision stands only if identical with each ungraded case excluded,
  D-wins, C-wins, both-fail and both-pass; otherwise `UNDECIDED_RERUN_UNGRADED`.
- Usage limits: interpretation events are classified with `evaluation_batch._LIMIT_MARKERS`
  (as `parse_events`), grading via `UsageLimitReached`; the run stops with exit code 3 and resumes.

## Budget estimate (`budget.json`, current 70 cases; estimate only)

| Item | Calls | Raw tokens |
|---|---:|---:|
| A and C interpretations | 140 | 1,061,814 |
| D, tool-solvable (2 model requests per turn) | 30 | 473,576 |
| D, controls | 40 | 316,225 |
| Grading, batch 2, plus 5% single re-grades | 35 + 4 | 518,820 |
| **Total** | **249** | **2,370,435** (33,864 per case) |

Upper bound with 3 model requests per solvable D turn: 2,606,623. Maximum calls with one re-grade
per case: 315. With the 10 supplement cases (80 cases, 240 interpretations) expect about 280 calls
and 2.7 M raw tokens.

## Fake end-to-end check (`validate_319_replication_fake.py`)

Runs `--freeze`, `--run` (repeatedly) and `--report` on a 12-case subset in a temporary directory
outside `docs/`, replacing only the Codex subprocess (a fake that checks the argv and drives the real
MCP fixture) and the grading call. All 15 checks pass: usage-limit stop (exit 3) and resume in both
interpretation and grading, a forbidden tool event failed closed and retried, every job saved once,
D restored answers equal the gold, single-case re-grade, ungraded bound rule
(`UNDECIDED_RERUN_UNGRADED` when the C-wins bound flips ADOPT to REJECT), forbidden control call
counted, usage accounting, and REJECT on an injected leak or failed protection gate.

## Limitations

Interpreter and grader are the same model family; same OS user and no hard filesystem jail for the
MCP fixture; `exec` usage is invisible to the event audit; results are not comparable with the
2.11.1 `gpt-6.1-sol` run (model, transport and the MCP startup setting differ).
