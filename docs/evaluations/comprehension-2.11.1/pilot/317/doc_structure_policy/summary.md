# Issue #317 doc_structure_policy: real-LLM screening

Decision: **hold**. Two published synthetic tasks, two repeats per condition, 16 interpretations and 16 independent grades. The small sample cannot establish general accuracy or treat one-case differences as an effect. Interpreter and grader share a model family.

| Criterion | Original | Human | Baseline | Candidate |
| --- | ---: | ---: | ---: | ---: |
| action | 4/4 | 4/4 | 4/4 | 4/4 |
| condition | 4/4 | 4/4 | 4/4 | 4/4 |
| conditions | 4/4 | 4/4 | 4/4 | 4/4 |
| intent | 4/4 | 4/4 | 4/4 | 4/4 |
| prohibition | 4/4 | 4/4 | 4/4 | 2/4 |
| scope | 4/4 | 4/4 | 4/4 | 4/4 |

Baseline: 24/24 criteria and 4/4 whole-task passes. Candidate: 22/24 criteria and 2/4 whole-task passes. Different denominators reflect task-specific rubrics; counts and repeats are correlated. See report.json for paired outcomes.

Raw reported tokens: 496336; content tokens: 13360; errors 0, isolation violations 0, unrun 0. Call-level latency and usage: calls.json.

The grader was explicitly instructed to cite verbatim excerpts. Cases were previously published, requested model identity is not independently verified, and no native host integration is established. Toggle remains default OFF.

See the committed issue317-2.9.0 evidence for existing offline protection numbers.

**Rubric coverage limitation:** Separate order and clarification-request verdicts were not included in the frozen rubric, so those criteria remain unmeasured as separate categories.

Content accounting uses the approved signed per-call formula; when measured input is below the fixed baseline, the estimate may be negative. The execution guard originally clamped individual values at zero, a conservative budget check; this report records the exact approved formula.
