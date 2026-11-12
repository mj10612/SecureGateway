# Issue #314: real-LLM screening

Two published synthetic tasks, two repeats per condition. The small sample cannot establish general accuracy or treat one-case differences as an effect. Interpreter and grader share a model family.

| Criterion | Original | Human | Baseline | Candidate |
| --- | ---: | ---: | ---: | ---: |
| action | 4/4 | 3/4 | 2/4 | 3/4 |
| clarification | 4/4 | 4/4 | 4/4 | 4/4 |
| condition | 4/4 | 4/4 | 4/4 | 4/4 |
| conditions | 4/4 | 4/4 | 4/4 | 4/4 |
| intent | 4/4 | 3/4 | 2/4 | 3/4 |
| order | 4/4 | 4/4 | 4/4 | 4/4 |
| prohibition | 4/4 | 4/4 | 4/4 | 4/4 |
| scope | 4/4 | 4/4 | 4/4 | 4/4 |

Decision: **hold**; default OFF. Baseline 28/32 criterion passes and 2/4 whole-task passes; candidate 30/32 and 3/4. See report.json for paired outcomes.

Separate HTTP capture: baseline protected 0/2, full exposures 2/2, partial 0/2; candidate protected 0/2, full exposures 2/2, partial 0/2. Refer also to the committed issue-specific offline evidence; these are not general leakage rates.

Verdicts with verified quoted excerpts: 128/128. Different denominators reflect task-specific applicability. Counts and repeats are correlated.

Raw reported tokens: 506544; content tokens: 23568. Errors: 0; isolation violations: 0; unrun: 0; stop: None. Call-level latency and usage: calls.json.

Cases were previously published; requested model identity is not independently verified, and native host integration is not established.

Content accounting uses the approved signed per-call formula; when measured input is below the fixed baseline, the estimate may be negative. The execution guard originally clamped individual values at zero, a conservative budget check; this report records the exact approved formula.
