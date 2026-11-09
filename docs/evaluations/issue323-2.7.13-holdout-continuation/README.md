# Issue 323 holdout results

Evaluated candidate: 2.7.13, commit `089be42`. Requested model: gpt-6.1-sol, medium reasoning, native CLI codex-cli 0.167.0. The service-side build is unverified. Each of 17 languages has three fresh responses per arm and four scoring criteria (68 possible points per repeat).

## Task-response scores

| Arm | Repeat totals / 68 | Mean | Sample SD |
| --- | --- | ---: | ---: |
| original | 65, 65, 65 | 65.00 | 0.00 |
| human | 65, 65, 64 | 64.67 | 0.58 |
| baseline | 47, 51, 46 | 48.00 | 2.65 |
| candidate | 62, 59, 62 | 61.00 | 1.73 |

Candidate gain against the contemporaneous baseline: **13.00 / 68**. Across paired repeated criteria, 43 improved and 4 regressed; no net conditions/prohibition regression was flagged. These repetitions are correlated, not independent real-world tasks.

| Language | Original mean +/- SD / 4 | Human | Baseline | Candidate |
| --- | ---: | ---: | ---: | ---: |
| ar | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 3.00 +/- 0.00 | 4.00 +/- 0.00 |
| bn | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| de | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 1.00 +/- 0.00 | 4.00 +/- 0.00 |
| en | 4.00 +/- 0.00 | 3.33 +/- 0.58 | 2.67 +/- 1.15 | 3.33 +/- 0.58 |
| es | 4.00 +/- 0.00 | 3.67 +/- 0.58 | 1.67 +/- 1.15 | 1.67 +/- 0.58 |
| fr | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| hi | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| id | 3.00 +/- 0.00 | 3.00 +/- 0.00 | 1.00 +/- 0.00 | 3.33 +/- 1.15 |
| ja | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| ko | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 3.67 +/- 0.58 | 4.00 +/- 0.00 |
| mr | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 1.00 +/- 0.00 | 3.67 +/- 0.58 |
| pt | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| ru | 2.00 +/- 0.00 | 2.67 +/- 1.15 | 2.00 +/- 0.00 | 2.00 +/- 0.00 |
| te | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 1.33 +/- 0.58 | 4.00 +/- 0.00 |
| tr | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 3.67 +/- 0.58 | 4.00 +/- 0.00 |
| ur | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| zh | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 3.00 +/- 0.00 | 3.00 +/- 0.00 |

## Privacy and restoration

Original labels are unchanged. The owner reviewed and accepted the [full newly exposed item list](../issue323-2.7.13-new-exposures.md). This records an owner-accepted policy tradeoff, not a pass of the old privacy gate.

| Measure | Baseline | Candidate |
| --- | ---: | ---: |
| Protected privacy occurrences / 747 | 719 | 465 |
| Full privacy exposures | 28 | 282 |
| Public spans overmasked / 282 | 177 | 46 |
| Privacy semantic round trips / 102 | 85 | 85 |
| Task semantic round trips / 17 | 17 | 17 |

There were 254 new privacy-suite exposures (239 person, 15 organization) and 42 new task-payload exposures (33 person, 9 organization), all contextual labels. No new pattern-classified exposure was observed in this cohort. The 17 privacy restoration mismatches also existed in the baseline.

## Interrupted primary execution and continuation

The original process disappeared after saving 63 first answers, with three calls still marked running. The original run remains stopped/incomplete. Its 31 original files are hash-pinned, copied and also preserved byte-for-byte in `preserved-parent.zip`. All 63 saved answers were reused unchanged. Before more calls, the separate continuation plan named the three interrupted jobs and froze the exact pending schedule and budgets. No candidate source or requests were tuned. The new 141 answers and all 204 independent grades completed.

Across both phases: **411 attempts, 408 successful calls, 3 interrupted calls with unknown usage**. Reported usage is a **lower bound of 6,497,711 tokens**, not an exact total; the interrupted primary run did not meet a known total budget. The continuation ran for 1720.8 seconds; original elapsed time is incomplete.

The derivative report is not eligible for pristine first-use adoption: it explicitly omits that claim, retains the old privacy regressions and inherited restoration failures, and leaves automatic adoption false. Task scores are complete with continuation. The raw executor labels a non-stopped journal `open`; all scheduled answers/grades are present and its process has exited.

## Validation and evidence

- [Machine-readable completion verification](completion-verification.json), [continuation plan](continuation-plan.json), and [combined report](run/report.json).
- [All language repeats and criterion changes](run/comprehension/report.json), [first responses](run/comprehension/first-responses.json), [first grades](run/comprehension/first-grades.json).
- [Validation checks](validation/checks.json): the pre-alignment full run had 4,554 passed / 345 failed / 288 skipped. The eight affected policy files subsequently passed 811 tests with 2 skips; all 345 failures were in those files. Other unchanged tests were not rerun. Evaluation guards/diagnostics passed 59 tests. Ruff and mypy passed.
- Package 2.7.14 records these results, aligns existing tests with public-default versus explicit-private controls, retains evaluator error diagnostics and the owner-only major-version rule. The evaluated engine remains the frozen 2.7.13 candidate.
