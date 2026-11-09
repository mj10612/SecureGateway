# Issue #324 - reliable multilingual baseline (2.7.0)

Fresh independently authored development/holdout families, with no vocabulary tuning on this holdout. Each task split has 17 languages and four criteria per task: a theoretical 68 points per repeat. Owner reference answers passed a separate 68/68 attainability audit. This does not guarantee every original model answer scores 68.

## Actual task-response results

Each language/arm has three fresh first responses. Scores below are means and sample standard deviations (ddof=1), not confidence intervals or independent-task failure probabilities. Requested model: gpt-6.1-sol; reasoning: medium; native CLI: codex-cli 0.167.0. Service-side build identity is unverified.

| Arm | Repeat totals / 68 | Mean | Sample SD | Whole-task successes per repeat / 17 |
| --- | --- | ---: | ---: | --- |
| original | 64, 64, 63 | 63.67 | 0.58 | 14, 14, 14 |
| human | 67, 65, 65 | 65.67 | 1.15 | 16, 15, 15 |
| baseline | 52, 50, 50 | 50.67 | 1.15 | 10, 9, 9 |

| Language | Original mean +/- SD / 4 | Human mean +/- SD / 4 | Baseline mean +/- SD / 4 |
| --- | ---: | ---: | ---: |
| ar | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 3.00 +/- 0.00 |
| bn | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| de | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 1.33 +/- 0.58 |
| en | 2.67 +/- 1.15 | 4.00 +/- 0.00 | 3.33 +/- 1.15 |
| es | 3.33 +/- 0.58 | 4.00 +/- 0.00 | 3.33 +/- 1.15 |
| fr | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| hi | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| id | 3.00 +/- 0.00 | 3.00 +/- 0.00 | 1.00 +/- 0.00 |
| ja | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| ko | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| mr | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 1.00 +/- 0.00 |
| pt | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| ru | 2.67 +/- 1.15 | 2.67 +/- 1.15 | 1.67 +/- 0.58 |
| te | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 1.00 +/- 0.00 |
| tr | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| ur | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 4.00 +/- 0.00 |
| zh | 4.00 +/- 0.00 | 4.00 +/- 0.00 | 3.00 +/- 0.00 |

## Privacy and restoration are separate

The actual holdout loopback capture measured all 102 privacy requests, 747 private occurrences and 282 public spans: **719 protected, 28 full exposures, 0 partial/ambiguous exposures; 177 public spans overmasked**. Seventeen requests contained a leak. All 102 outbound and restored-response replays were stable; 85/102 source texts restored exactly/semantically and 17 did not, despite HTTP 200. Session isolation and encrypted restart passed. These are existing baseline failures, not certified protection. Per-language, category, policy, language-mode, dialect and split denominators are in the reports.

The 17 task payloads contain another 64 private occurrences: 59 protected and 5 full exposures in four tasks. All 17 task roundtrips/replays passed. Do not hide these task-payload leaks behind the larger privacy set.

The development-only pilot measured 786 private occurrences: 751 protected and 35 full exposures, with 110/186 public spans overmasked. Two Claude captures failed restoration with HTTP 502 after forwarding; provider privacy remained measurable, with only 100/102 roundtrips passing. Development results cannot authorize adoption.

## Preserved first execution failure and prospective grading supplement

The primary run saved **153 first responses and 29 first grades**, then stopped on one native grader ValueError whose cause and token usage are permanently unknown. It remains stopped/incomplete; no original file was rewritten. Before new calls, the grade-only supplement froze copies/hashes of all parent evidence, exact requests, unchanged adapter/CLI/policy, its observer and a separate budget. It graded 123 never-attempted jobs plus one explicitly named reattempt with a recorded reason. It made 124 successful grading calls with no further errors. Every original first response and valid first grade is reused unchanged. The reattempt is a later stochastic grading sample, not an erased failure.

Combined semantic scoring is `completed_with_supplement`, with all 153 saved answers graded. The primary execution remains `incomplete`. Across both phases there were **307 attempts, 306 successful calls and one unknown-usage failed attempt**. Reported tokens are a **lower bound of 4,915,415** (2,861,052 primary + 2,054,363 supplement); do not claim an exact total or that the original execution met a known total budget. The separate reference audit used 17 calls and 274,989 reported tokens.

No candidate was evaluated or enabled. Baseline scores and a grading supplement cannot authorize adoption. Later candidates require contemporaneous controls, holdout-only task gains, privacy non-regression and integrity review. Holdout use is recorded in the append-only ledger beside issue324-data.

## Evidence

- [Protocol](../ISSUE324_PROTOCOL.md) and [commands](../ISSUE324_USAGE.md).
- [Frozen source data](../issue324-data/source-manifest.json), [reference audit](holdout-reference-audit/report.json), [independent audit verification](holdout-audit-independent-verification.json).
- [Primary incomplete joint report](holdout-baseline/report.json), [first responses](holdout-baseline/comprehension/first-responses.json), [first grades](holdout-baseline/comprehension/first-grades.json), [original failed-call journal](holdout-baseline/execution-journal.json).
- [Combined report](holdout-grading-supplement/report.json), [all per-language repeats](holdout-grading-supplement/combined-comprehension/report.json), [supplemental journal](holdout-grading-supplement/supplemental-journal.json), [prospective supplement freeze/reason](holdout-grading-supplement/freeze.json).
- [Source snapshots](source-snapshots/manifest.json) match exact already frozen hashes; copied after calls began, not reconstructed. Raw JSON/source bytes are pinned by .gitattributes. Exact-source verification can reject another checkout/platform with different adapter bytes; archived JSON remains directly readable.
- [Initial unit/static checks](unit-validation.json) and [post-recovery full suite](supplemental-unit-validation.json): 4,552 passed / 287 skipped on Windows. Unit mocks validate bookkeeping and are not model scores. Actual macOS stream-cancellation behavior requires remote CI.
- [Installed wheel/sdist proof](package-validation.json) and [raw log](package-smoke.log): both 2.6.2-to-2.7.0 upgrades passed, including four native offline host/tool cases per artifact and agreeing CLI/MCP/package versions. Tested package source/resource bytes equal the staged package code; later validation-only records do not alter runtime code.
