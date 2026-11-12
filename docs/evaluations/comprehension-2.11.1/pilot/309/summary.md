# Issue #309: real-LLM screening

Decision: **hold**. Four published synthetic Korean tasks, one repeat, four conditions; 16 interpretations and 16 independent grades completed. This small sample cannot establish general accuracy or treat one-case differences as an effect. Interpreter and grader share a model family. Requested model identity is not independently verified.

| Criterion | Original | Human | Baseline | Candidate |
| --- | ---: | ---: | ---: | ---: |
| intent | 3/4 | 4/4 | 3/4 | 3/4 |
| action | 3/4 | 4/4 | 3/4 | 3/4 |
| condition | 4/4 | 4/4 | 4/4 | 4/4 |
| prohibition | 4/4 | 4/4 | 4/4 | 4/4 |
| order | 3/3 | 3/3 | 3/3 | 3/3 |
| clarification | 4/4 | 4/4 | 4/4 | 4/4 |
| scope | 3/4 | 4/4 | 3/4 | 3/4 |
| evidence | 1/1 | 1/1 | 1/1 | 1/1 |

Order is applicable to three tasks; the fourth has an evidence/observation criterion instead. Counts are correlated rubric items, not independent samples. Baseline and candidate each pass 25/28 criteria, with 3/4 whole-task passes; inspect paired outcomes in report.json.

Committed #309 offline evidence: 16/16 protected in both arms, 0 full or partial leaks, exact restoration 16/16; overmasked endings 13/16 baseline and 1/16 candidate. In this separate four-task HTTP capture, protected 0/4 in each arm and full exposure 4/4 in each; this reflects the known contextual-name limitations of these tasks, and does not contradict or replace the issue-specific offline corpus.

Raw reported tokens: 505094; content tokens under approved deviation: 22118. Call-level latency and usage are in calls.json. Errors: 0; isolation violations: 0; unrun: 0. Two diagnostic calls are recorded separately under smoke and excluded from this screening.

These cases were previously published and are not independently sequestered. Native host integration and broader language coverage are not established. The candidate remains default OFF.

**Evidence limitation:** The existing grader instruction requested a citation or omission but did not explicitly require a quoted excerpt in every verdict. Some verdicts therefore have explanatory evidence rather than a quoted excerpt; the strict excerpt requirement remains incomplete. No extra grader calls were made because the 32-call cap was reached.

Content accounting uses the approved signed per-call formula; when measured input is below the fixed baseline, the estimate may be negative. The execution guard originally clamped individual values at zero, a conservative budget check; this report records the exact approved formula.
