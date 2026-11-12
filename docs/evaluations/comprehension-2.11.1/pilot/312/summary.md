# Issue #312: real-LLM screening

Two published synthetic tasks, two repeats per condition. The small sample cannot establish general accuracy or treat one-case differences as an effect. Interpreter and grader share a model family.

| Criterion | Original | Human | Baseline | Candidate |
| --- | ---: | ---: | ---: | ---: |
| action | 4/4 | 4/4 | 0/4 | 0/4 |
| clarification | 4/4 | 4/4 | 4/4 | 4/4 |
| condition | 2/4 | 2/4 | 0/4 | 0/4 |
| conditions | 2/4 | 2/4 | 2/4 | 2/4 |
| intent | 4/4 | 4/4 | 0/4 | 0/4 |
| order | 2/4 | 2/4 | 2/4 | 2/4 |
| prohibition | 4/4 | 4/4 | 4/4 | 4/4 |
| scope | 4/4 | 4/4 | 4/4 | 4/4 |

Decision: **hold / incomplete**; default OFF. Baseline 16/32 criterion passes and 0/4 whole-task passes; candidate 16/32 and 0/4. See report.json for paired outcomes.

Separate HTTP capture: baseline protected 6/8, full exposures 2/8, partial 0/8; candidate protected 6/8, full exposures 2/8, partial 0/8. Refer also to the committed issue-specific offline evidence; these are not general leakage rates.

Verdicts with verified quoted excerpts: 126/128. Different denominators reflect task-specific applicability. Counts and repeats are correlated.

Raw reported tokens: 510156; content tokens: 27180. Errors: 0; isolation violations: 0; unrun: 0; stop: None. Call-level latency and usage: calls.json.

Cases were previously published; requested model identity is not independently verified, and native host integration is not established.
