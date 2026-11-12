# Joint evaluation of the adopted candidates (#310, #316 B, #318) — prepared, not run

> **Decided without a model run: ADOPT-JOINT — see [DECISION.md](DECISION.md).**
> J was identical to each candidate's original D on all 144 cases, so the
> comprehension run, the freeze and the attack were not performed.
> `preregistration.json` was never frozen. The commands below are kept for the record only.

Question: can `contextual_name_spans` (#310), `scoped_corrections` protect-only
(#316 condition B) and `attribute_bundle` (#318) be enabled **together** by
default? The decision rule is in [`preregistration.json`](preregistration.json).
No model call has been made. The coordinator freezes the plan and then runs it.

Code: secure-gateway 2.16.0 with per-session `GatewayFeatures` (#354, PR #366).
Captures use `GatewaySession(features=...)`, and offline/CI use
`PrivacyGateway(features=...)`. No process-global `candidate_profile` is used.

## Layout

| Path | Content |
|---|---|
| `plan/cases.json` | 144 cases: union of the frozen #310/#316/#318 comprehension cases (48 each, 8 negative controls each), `case_id = <source>:<id>`, each with its own `trusted_local_policy` |
| `captures/manifest.json` | Model-visible arms A/C/J per case plus the merged rubric criterion definitions (identical across the three candidates) |
| `plan/precheck.json` | C vs J differences, compared with the original frozen C/D |
| `offline/<310,316,318>/` | Baseline / single / joint protection per set (`summary.json`, `occurrences.json`) |
| `offline/ci-joint/` | In-process privacy report with all three features on and its `evaluate compare` result |
| `offline/summary.json` | Part (a) gate |
| `attack/manifest.json` | Prepared #318 catalogue-attack jobs (prior/C/J, 144 calls). **Not run**, secondary only |
| `plan/budget.json` | `evaluation_batch.estimate_budget` output |
| `run/` | Created by `--freeze`, then `--run` (freeze record, responses, grades, report) |

## Pre-check (`--prepare`, no model)

Arms are compared after each alias is replaced with its bound original, because
numeric aliases are random per capture.

| Source | Non-control J ≠ C | Original D ≠ C | D differed, J does not | J differs, D did not | C drift | J ≠ original D |
|---|---|---|---|---|---|---|
| #310 | 40/40 (100%) | 40 | 0 | 0 | 0 | 0 |
| #316 | 38/40 (95%) | 38 | 0 | 0 | 0 | 0 |
| #318 | 32/40 (80%) | 32 | 0 | 0 | 0 | 0 |
| pooled | 110/120 (91.7%) | 110 | 0 | 0 | 0 | 0 |

No negative control changes. **Finding:** on every case, J is identical to the
candidate's own original D (canonical form). Turning on the other features adds
no change to these cases: #310 finds nothing extra in the #316/#318 texts, and
the policy-bound features are inactive without a policy. On these cases the C vs J
comparison is therefore, input for input, the earlier C vs D comparison, re-measured
on the new transport/model. Cross-feature interaction shows up only offline
(below) and on the CI corpus.

## Offline protection (part a)

Each case uses its own policy. Single = that candidate alone. Joint = #310 plus
the case's policy-bound feature.

| Set | Sensitive / public spans | Exposed B / S / J | Newly protected S / J | Newly exposed J vs B | Overmask B / S / J | Exact restore B / S / J | Gate |
|---|---|---|---|---|---|---|---|
| #310 `introducer-cases.json` (22) | 132 / 132 | 132 / 44 / 44 | 88 / 88 | 0 | 0 / 0 / 0 | 22 / 22 / 22 | pass |
| #316 `protection-correction-sensitive.json` (208) | 104 / 104 | 104 / 0 / 0 | 104 / 104 | 0 | 0 / 0 / 0 | 208 / 208 / 208 | pass |
| #318 `protection-bundle-table.json` (27) | 108 / 108 | 108 / 0 / 0 | 108 / 108 | 0 | 0 / 0 / 0 | 27 / 27 / 27 | pass |

The single arm reproduces the numbers behind each ADOPT decision exactly
(`single_reproduces_adopt_numbers: true`). Joint outbound payloads are
byte-identical to single on all 257 protection cases.

CI: a privacy report generated in-process with all three features on (#316/#318
policy = `cases[0]` of their replacement sets, the same convention as the
single-candidate runs), then
`secure-gateway evaluate compare --baseline docs/evaluations/issue324-2.7.0/legacy-privacy/report.json`:
exit 0, comparable, no regression, 0 new exposures, 0 integrity regressions
(9 existing exposures, as in the baseline). **Part (a): passed.**

## Budget (`plan/budget.json`)

| Run | Calls | Raw tokens (estimate) |
|---|---|---|
| Comprehension: 432 interpretations + 72 grade batches + ~8 re-grades | 512 | 4,096,640 (≈28,450 per case) |
| Optional #318 attack | 144 | 1,075,680 |

Constants: lean fixed input 7,070 tokens, 400 content tokens per
interpretation, 2,000 per graded case, 5% re-grades. These match
`run_309_luna.py`, whose real run measured 30,173 raw tokens per case.

## Dry run (fake adapter, no model call)

`--dry-run <dir outside docs/>` replaces `run_lean_worker` with a deterministic
fake that returns validated results. The fake injects quote failures,
permanently ungraded cases and, with `--fake-limit-after N`, a
`UsageLimitReached`. Its output never touches `run/`. It was validated as follows:

1. With `--fake-limit-after 100`, the run stopped cleanly after 100 saved interpretations.
2. Rerunning the same command resumed from the saved rows: 432 interpretations,
   72 grade batches with single-case re-grades, and 16 ungraded cases that went
   through the five-scenario bound rule (`UNDECIDED_RERUN_UNGRADED` on fake data).
   The 144 attack calls were scored and the report was written.

The fake verdicts are random, so the dry-run numbers mean nothing.

## Commands for the coordinator

Run these from the repository root on this branch. Do not edit anything under this
directory after `--freeze`. `--run` and `--report` check every frozen hash, the
adapter hash and the job list.

```powershell
# optional: repeat the plumbing check (any directory outside docs/)
uv run --locked --all-extras python docs/evaluations/joint-adopted-2.16/run_joint.py --dry-run $env:TEMP\joint-dry --fake-limit-after 50
uv run --locked --all-extras python docs/evaluations/joint-adopted-2.16/run_joint.py --dry-run $env:TEMP\joint-dry

# 1. freeze (once, before any model call)
uv run --locked --all-extras python docs/evaluations/joint-adopted-2.16/run_joint.py --freeze
# 2. run (resumable; exit 3 = usage limit, rerun the same command later)
uv run --locked --all-extras python docs/evaluations/joint-adopted-2.16/run_joint.py --run
# 3. optional secondary attack (descriptive only)
uv run --locked --all-extras python docs/evaluations/joint-adopted-2.16/run_joint.py --run-attack
# 4. report (also written at the end of --run)
uv run --locked --all-extras python docs/evaluations/joint-adopted-2.16/run_joint.py --report
```

`--prepare` regenerates captures, offline results and attack jobs. Numeric aliases
change on every capture, so do **not** rerun it after review. It refuses once
`run/freeze.json` exists.

## Limitations

- Policy-bound features are tied to their own case's project or document hash. #316 and
  #318 are therefore never active together on one comprehension or protection case;
  all three are active together only on the CI privacy corpus.
- Interpreter and grader share a model family. The cases were enriched for each
  candidate's differences. Results are not compared numerically with the earlier
  native-transport `gpt-6.1-sol` runs.
