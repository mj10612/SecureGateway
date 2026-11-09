# Corrected task-response adapter retest

This is a new execution of the same existing 17-language paragraph fixture and
two known requests. Original, human-minimally-masked and current-baseline arms
each receive one fresh repeat. The adapter now asks for the requested response,
including an appropriate clarification, and explicitly forbids merely
paraphrasing what the task means. It still forbids tools and external context.

The prior [`../multilingual-regression/`](../multilingual-regression/) run had an
adapter/rubric mismatch and is retained only as a diagnostic. Its task-performance
scores are not a valid baseline comparison. This retest uses new opaque job IDs,
fresh model contexts and new first responses, followed by independent grading;
old answers or grades are not repaired or imported.

`retest-input-comparison.json` checks the frozen corpus and arm messages. Fresh
HTTP sessions issue new random numeric-alias digits in some baseline inputs;
the corpus and messages after reserved-numeric-alias normalization are unchanged.
This is a new regression measurement, not a causal score comparison against the
invalid old adapter run.

`freeze.json` fixes the captured queries, corpus/script/source hashes, requested
model, repeat count and budgets before inference. The maximum is 114 model calls,
2,500,000 reported tokens, 1,200 seconds for scheduling and three concurrent
workers. A failed call with unknown usage stops scheduling; incomplete work is
not successful measurement. Already-running calls can exceed the scheduling
deadline or a reported token threshold; these are not provider hard caps.

`http-captures.json` and `privacy.json` record actual loopback HTTP payloads,
protection, exact restoration and replay separately from model scores. Privacy
annotations cover the fixture's shared synthetic names/identifiers,
not comprehensive locale-specific names, contact patterns or industrial terms.
Interpreter inputs contain only the captured instruction/task appropriate to their arm;
the local corpus, arm labels, original/gold and rubric are not supplied to masked
interpreters. Graders receive the saved first response and fixed original/rubric.

The model identity is the requested Codex CLI `gpt-6.1-sol` setting, not an
independently verified server build. Workers use fresh empty directories and
contexts but share the OS user and subscription authentication; this is not a
hard filesystem jail. Tool events are rejected. These semantic text jobs do not
certify hosted-provider gateway routing or native host tool execution.

The paragraphs are existing regression material and were inspected previously.
One repeat per arm is descriptive and does not establish population accuracy,
an uncertainty interval or causal improvement over historical versions. The
17-paragraph scores (68 criteria per arm) and two known requests (8 criteria per
arm) are reported separately in `report.json`.

## Recorded result

All 114 calls completed without errors in 498.16 seconds, reporting 1,833,695
tokens. No first response or grade was replaced.

| Regression subset | Original | Human masking | Current baseline |
| --- | --- | --- | --- |
| 17 paragraphs: criteria passed / 68 | 67 | 67 | 50 |
| 17 paragraphs: all criteria passed / 17 tasks | 16 | 16 | 8 |
| Two known requests: criteria passed / 8 | 8 | 8 | 7 |

The Korean deletion request passed all four baseline criteria. The baseline
SKILL.md answer asked for the missing file contents; its independent grader
withheld the intent point because it did not explicitly acknowledge following
the file's instructions. All three SKILL.md arm inputs are byte-identical, so
this one-point difference is not evidence of a masking effect. First grades
are retained, including that judgment.

The actual HTTP captures protected all 35 annotated reference occurrences and
passed all 19 exact-restoration/replay checks, plus session isolation and
encrypted restart. These limited reference checks do not establish comprehensive
privacy coverage. The remaining paragraph failures show that broad multilingual
task-response preservation is not solved by the current baseline.
