# #319 local arithmetic: natural-wording holdout (frozen, run on gpt-6-luna)

Status: **frozen 2026-11-13T07:38:40Z on secure-gateway 2.18.0, run once on `gpt-6-luna`;
decision REJECT, identical under every ungraded bound.** Not a new feature: the same
`local_arithmetic` candidate, still default **off**, measured with corrected cases.

Runner: [`../../plan/run_319_natural.py`](../../plan/run_319_natural.py) (design wrapper) over
[`../../plan/run_319_replication.py`](../../plan/run_319_replication.py) (frozen machinery).
Authors: [`../../plan/author_319_natural.py`](../../plan/author_319_natural.py).

## Why this plan replaces the 2.16.3 replication

The 2.16.3 run in `319/plan-replication` + `319/comprehension-replication` was declared
**INVALID** in issue #319 and is kept unchanged as historical evidence:

1. the local tool rejected the alias form the model sees (`⟦private_symbol_N⟧`, #375, fixed in 2.17.1), so
   33 of 40 tool calls in D were rejected; and
2. every case text instructed the interpreter to call the tool and return a result alias, so arm A
   (original text, no tool) could not pass and the analysis set fell to three cases.

This plan fixes the second cause and the offline check behind the first.

## Design deltas (preregistered before any model call)

1. **Fresh holdout, natural wording.** Three isolated authors received the issue title/body and the
   case specification only — never the implementation, an earlier case, any response or the answer
   key. No case text names a tool, alias, mask, placeholder or evaluation. Requested with slack
   (46 + 24 tool-solvable, 16 no-calculation, 28 impossible) and capped at 40/14/26 in source order.
2. **Arm-specific CLI features (#372).** A/C keep `code_mode_host` disabled, so a no-tool arm cannot
   run code behind the event audit. D alone keeps it enabled, because codex-cli 0.167.2 exposes an
   MCP tool only as a nested tool of the code-mode `exec` tool. Tool availability is the variable
   under test; the asymmetry and its `exec` blind spot are disclosed below.
3. **The tool contract moved from the case text to D's worker prompt** (tool name, argument shape,
   and that the host restores a returned alias for the user).
4. **No-tool arms are graded on the answer value.** The alias-return protocol only exists in D, so A
   and C also get the derived `answer_value` criterion; D keeps run_319's
   `operation_aliases` / `restored_result` / `unit` rule. `rubric-natural.json` is
   `319/plan/rubric.json` verbatim plus exactly that one criterion (checked by the runner).
5. **The offline fixture probe submits both alias forms** (`private_symbol_N` and the displayed
   `⟦private_symbol_N⟧`) and requires both to compute and restore to the gold (#375 regression).

## Commands

```
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/author_319_natural.py --label solvable
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/author_319_natural.py --label solvable2
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/author_319_natural.py --label no_calculation
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/author_319_natural.py --label impossible
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_natural.py --prepare
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_natural.py --protection
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_natural.py --freeze
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_natural.py --run
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_319_natural.py --report
```

Plumbing check with no model call (15 checks: usage-limit stop/resume, fail-closed tool events,
per-arm feature sets, real stdio fixture, ungraded bounds, gate sensitivity):

```
uv run --locked python docs/evaluations/comprehension-2.11.1/plan/validate_319_replication_fake.py
```

## Cases and pre-check (`precheck.json`, `manifest.json`)

| Source | Authored | Label |
|---|---:|---|
| `natural-solvable-authored.json` | 46 | tool_solvable |
| `natural-solvable2-authored.json` | 24 | tool_solvable (comma-free supplement) |
| `natural-nocalc-authored.json` | 16 | no_calculation |
| `natural-impossible-authored.json` | 28 | impossible |

- Binding (`check_319_binding.py` rule + gold reproducibility + offline fixture): **114/114** authored
  cases bind to exactly one alias each; capture deterministic **114/114**; feature off vs on task,
  instructions and aliases identical **114/114**; the feature adds **no** extra alias.
- Selected: **40 tool_solvable, 14 no_calculation, 26 impossible** (80 cases, 240 jobs).
- Excluded, never counted: 22 `gold_not_reproducible` (the first solvable author wrote comma-grouped
  thousands such as `1,275.4`, which the tool's bounded-decimal policy rejects; the cases are
  excluded, never edited, and `solvable2` supplied replacements), 1 `provider_visible_value`
  (`ns:c23`'s operand `512` collides with the fixed wrapper constant "512 tokens"; excluded, not
  reworded), 11 `surplus_over_required_count`.
- Offset repairs: **97** authored `sensitive_spans` offsets were recomputed where the span text
  occurs exactly once (spans are derived data; no case content changed). Recorded in `precheck.json`.

## Offline gates

- **Alias forms (`fixture-probe.json`).** 48 tool-solvable candidates driven through the real stdio
  MCP fixture with a local MCP client: bare **48/48** and displayed `⟦…⟧` **48/48** return a new
  alias that restores to the gold. This is the #375 regression the 2.16.3 check missed.
- **Provider-visible payload (`payload-leak-check.json`).** No sensitive operand and no gold number
  as a whole token in the full gateway request or the exact C/D prompts: **0 selected cases leak**
  (1 excluded case, see above).
- **Protection (`offline/local_arithmetic/summary.json`).** 29 cases, 0 newly exposed, exact restore
  29/29 baseline and candidate, CI compare exit 0, gate **passed**.

## Run and result (`comprehension-natural/report.json`)

`gpt-6-luna`, reasoning effort low, ChatGPT login only, lean CLI overrides, fresh ephemeral session
per job, read-only empty workspace. 240 interpretations, 0 failed; 71 grading calls (37 batches,
31 single re-grades, 3 batch transport failures retried); **308 counted calls, 3,188,461 raw tokens
(39,856 per case)**.

| Gate (frozen `decision.json`) | Result | Verdict |
|---|---|---|
| Protection gate passes | yes (0 newly exposed, 29/29 restore) | pass |
| Correct restored result >= 80% of A-eligible tool-solvable cases | **23/35 = 65.7%** | **fail** |
| Exact one-sided sign test D vs C, p < 0.05 | 23 D-only / 0 C-only, p = 1.19e-07 | pass |
| <= 1 A-eligible no-calculation/impossible case with a D tool call | **8** | **fail** |
| 0 C/D trajectories with an original or computed value | 0 | pass |
| No duplicated inference | 0 | pass |

**Decision: REJECT.** On the 52 A-eligible cases, whole-task passes are **A 52 / C 12 / D 32**. The
decision is unchanged when the 7 ungraded cases are excluded, D-wins, C-wins, both-fail or
both-pass.

What the numbers separate:

- **A is now judgeable again**: 35/35 A-eligible tool-solvable cases pass `answer_value`,
  `restored_result` and `unit`, so the correction that motivated this plan worked.
- **C cannot do the task by construction**: 0/35 pass `answer_value` and `restored_result`; the
  masking alone leaves no path to the value.
- **The tool path works mechanically**: D used the issued aliases in 34/35 cases, the local result
  restored to the gold in 32/35, and no trajectory exposed an original or computed value.
- **The end-to-end gate still fails**, and most of the gap is grading, not arithmetic: 13 D
  tool-solvable cases miss all-criteria pass, and the failing criteria are `scope` 9,
  `restored_result` 3, `action` 3, `unit` 3, `operation_aliases` 1. The `scope` verdicts quote the
  sanitized tool transcript that only D has, so the criterion penalises the condition under test;
  the three `restored_result` misses are answers that wrote the bare `private_symbol_N` form, which
  the grader did not resolve although local restore did.
- **Unnecessary calls are real**: 29 of 40 control trajectories call the tool; 8 of the 17
  A-eligible controls do (gate allows 1). In no-calculation cases the model called `add` with the
  same alias twice and then ignored the result; in impossible cases it tried to combine the single
  issued operand with a name alias. D's prompt sentence "use it when the task needs a value you
  cannot read" plausibly invites the impossible-case attempts.

## Limitations

- Interpreter and grader are the same model family; the grader is also the only judge of `scope`,
  `action` and `unit`, and those verdicts are mechanical-quote-checked only.
- 7 of 80 cases (8.75%) stayed ungraded after the one allowed re-grade (quote validation); the
  decision is identical under all five bounds, but the graded counts are optimistic-tail-sensitive.
- D keeps `code_mode_host` enabled to reach the MCP tool. A/C are fail-closed (#372); a successful
  non-MCP nested call inside D's `exec` body emits no event and no stderr line, so D's exec body is
  not fully auditable. This is the same trade-off recorded in #372 and in the 2.16.3 plan.
- The tool's own outputs are aliases only, and the D prompt advertises the tool, so D's call-rate
  evidence is a property of this condition, not of the product's default host injection.
- Baseline masking also aliases fictional organisation names and the `KRW` code, so C/D see fewer
  plain words than A; the feature-off capture was byte-identical, so this is not caused by the
  candidate.
- The 2.18.0 defaults publish ordinary numbers (#374); only forced-rule operands are masked here, so
  this result speaks to forced/sensitive numbers, not to default prose numbers.
- Not comparable with the 2.11.1 `gpt-6.1-sol` run or with the invalid 2.16.3 run (model, transport,
  case wording and tool availability differ).

## What a next run needs (not done here)

1. Neutralise D's prompt wording so it cannot be read as "call the tool for a value you cannot see"
   (for example: "call it only when the task shows two aliases for the two operands").
2. Grade `scope` on the answer only, or drop it for D, since the sanitized tool transcript is part of
   D's material by construction.
3. Resolve the bare-alias answer form in the grading material (or require the displayed form in the
   answer), which caused three `restored_result` misses.
4. Keep the #375 two-form offline probe and the natural-wording author specification; both worked.
