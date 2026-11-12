# Issue #315: real-LLM instruction screening

Decision: **hold / incomplete**. Two published synthetic tasks, two repeats, identical captured masked payload and three instruction variants; 12 interpretations and 12 independent grades. The small sample cannot establish general accuracy or treat one-case differences as an effect. Interpreter and grader share a model family.

| Criterion | Baseline | Concise | Examples |
| --- | ---: | ---: | ---: |
| action | 3/4 | 4/4 | 4/4 |
| condition | 4/4 | 4/4 | 4/4 |
| conditions | 4/4 | 4/4 | 4/4 |
| intent | 3/4 | 4/4 | 4/4 |
| prohibition | 4/4 | 4/4 | 4/4 |
| scope | 4/4 | 4/4 | 4/4 |

Verdicts with verified quoted excerpts: 71/72. Separate order and clarification-request verdicts were not included in the frozen rubric, and remain unmeasured. Different denominators reflect applicable task-specific rubrics. Counts and repeats are correlated.

Raw reported tokens: 380087; content tokens: 17855; errors 0, isolation violations 0, unrun 0. Call-level latency and usage: calls.json.

Cases were previously published, model identity is requested but not independently verified, and native host integration is not established. Toggles remain default OFF. See issue315-2.9.0 for committed offline protection results.

Content accounting uses the approved signed per-call formula; when measured input is below the fixed baseline, the estimate may be negative. The execution guard originally clamped individual values at zero, a conservative budget check; this report records the exact approved formula.
