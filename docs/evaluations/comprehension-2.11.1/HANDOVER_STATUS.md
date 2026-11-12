# Handover status — Codex usage limit stopped the runs

Written 2026-11-12 ~09:59 local. No commit, push or PR was made; everything is
uncommitted on branch `eval/real-llm-comprehension`.

## Exact stop reason

`codex exec` reports, verbatim:

```
ERROR: You’ve hit your usage limit. Upgrade to Pro (https://chatgpt.com/explore/pro), visit https://chatgpt.com/settings/usage to purchase more credits or try again at 1:51 PM.
```

Both runs stopped at their first failed interpretation and recorded
`error_category: nonzero_exit` with `usage_known: false`. No grading was
performed, so no candidate has a decision from this session.

## #309 (and #306) — case authoring finished, run frozen, partially executed

* Authoring completed: replacement batches 1–10, 800 independently authored
  cases total, 85 distinct activating non-controls, activation rate **0.10625**
  (85/800). 77 unchanged controls were available; 8 were selected unchanged.
* The pilot's 27 cases are **not** reused in this run.
* Frozen plan: `309/plan-replication/`
  * `cases.json` — 93 cases (85 discriminating non-controls + 8 controls)
  * `rubric.json` sha256 `56ddbca879636acf658a8fd4ab88def781b38f445646e6a33513bb902106bcd3`
  * `decision.json` sha256 `ccb1f492d5720f3895daf61682ad6e66c70c1a6f1467547958798bdf4e76314d`
  * `preflight-ko_conjugation_split.json` — 85/85 non-controls C≠D, 0/8 controls changed
  * `budget.json` — 93 cases, 372 interpretation calls, 93 grades, model `gpt-6.1-sol`
* Run directory `309/comprehension-replication/`: manifest sha256
  `fcf8d9e4010ee512…` (372 jobs), 14 rows written, 13 completed, 1 failed
  (`b10-h037`, arm C). No grades.
* Pre-check for this run: C≠D among non-controls 85/85 = 100% (≥70% required);
  controls unchanged 8/8. Protection-side pre-checks are not applicable to this
  comprehension target; the offline protection gate used by the run is
  `309/offline/ko_conjugation_split/summary.json` (completed, gate passed by the
  frozen rule, no newly protected spans on that corpus).

## #313 — precondition met, run partially executed

* Case set already had 88 cases, 80 discriminating non-controls + 8 controls;
  no further authoring was needed.
* `313/comprehension/`: manifest sha256 `c213dcd7a27d3cd5…` (264 jobs), 243 rows
  written, 242 completed, 1 failed (`targeted-expansion5-h27`, arm C). No grades.
* Pre-check recorded: 80/80 non-controls changed; baseline public spans unmasked
  173/174 = 0.9943 (≥0.70 required).

## #319 — authoring only, not frozen

* Two independent author batches produced 80 new cases (40 tool_solvable,
  14 no_calculation, 26 impossible) in
  `319/plan/replication-batch{1,2}-authored.json`.
* Binding pre-check (`plan/check_319_binding.py`, no model call) passed 26/40 and
  28/40 cases. Declaring every operand as a forced rule
  (`replication-batch1-forced.json`) made binding worse (21/40), so forced-rule
  normalization is not the fix; the failing shapes are `gold_value_visible`
  (value still visible in masked text) and `unbound_gold_span` under forced
  rules.
* Nothing was frozen or run; the 40 tool-solvable requirement is **미측정**.

## Resume instructions

1. Wait until the Codex quota resets, then verify with a one-line `codex exec`.
2. The harness refuses to resume a run directory that contains a failed row
   (`interpret` returns False for any non-completed row). Move each failed row
   out of `first-responses.jsonl` into a `failed-responses-quarantined.jsonl`
   after re-verifying its `status`, keeping the manifest and all completed rows
   untouched, then re-invoke:
   * `uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_replication.py --issue 309 --run`
   * `uv run --locked python docs/evaluations/comprehension-2.11.1/plan/run_comprehension.py --issue 313 --run`
   Both validate stored responses, rubric and decision by hash before continuing.
3. After the #309 replication completes, derive #306 with
   `plan/write_306_from_replication.py` (shared A/B/C/D, zero extra calls).
4. For #319, re-author with operand shapes that bind without forced rules, or
   fix the binding check for the two failing shapes, before freezing.

## Worktree safety

`docs/evaluations/comprehension-2.11.1/` and `docs/ISSUE_RESOLUTION.md` were
copied and hashed to `../_comprehension_backup_20261112_092355` (793 files)
before any work. No destructive git command was run; `git status` shows only
`M docs/ISSUE_RESOLUTION.md` and the untracked evaluation tree.

## Update 2026-11-12 (coordinator)
* #313 COMPLETED: REJECT under the frozen rule. A/C/D whole-task 83/59/68 of 83; discordant D-only 10, C-only 1,
  one-sided p=0.005859; prohibition criterion net loss 2 (>= 2) drives the REJECT. 0 ungraded, protection gate passed,
  pre-check 80/80 non-controls changed. Evidence: `313/comprehension/report.json`. Issue #313 commented and closed (not planned).
  The failed row `targeted-expansion5-h27` (arm C) is in `313/comprehension/failed-responses-quarantined.jsonl`.
* #309 (+#306): POSTPONED until after issue #364 (Codex cost reduction). No #309 resume was started; frozen 93-case set unchanged.
* Next week order: #364 first, then #309 with the #364 method, then the evaluation PR.
