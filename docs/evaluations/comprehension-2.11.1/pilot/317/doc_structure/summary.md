# Issue #317 doc_structure: real-LLM screening

Decision: **hold / incomplete**. Two published synthetic tasks, two repeats and four conditions; 16 interpretations and 16 independent grades. The small sample cannot establish general accuracy or treat one-case differences as an effect. Interpreter and grader use the same model family.

| Criterion | Original | Human | Baseline | Candidate |
| --- | ---: | ---: | ---: | ---: |
| action | 4/4 | 4/4 | 4/4 | 4/4 |
| condition | 4/4 | 4/4 | 4/4 | 4/4 |
| conditions | 4/4 | 4/4 | 4/4 | 4/4 |
| intent | 4/4 | 4/4 | 4/4 | 4/4 |
| prohibition | 4/4 | 4/4 | 4/4 | 3/4 |
| scope | 4/4 | 4/4 | 4/4 | 4/4 |

Different denominators reflect applicable task-specific rubrics. Counts and repeats are correlated. See report.json for all-task and paired outcomes.

Raw reported tokens: 497986; content tokens: 15010; errors 0, isolation violations 0, unrun 0. Call-level latency and usage: calls.json.

The grader instruction requested a citation or omission but did not explicitly require a quoted excerpt for every verdict; some explanations lack the required quoted excerpt. Therefore the strict evidence requirement is incomplete, and no extra grader calls were made after the 32-call cap. These cases were previously published; model identity is requested rather than independently verified. Toggle remains default OFF.

See the committed `issue317-2.9.0` evidence for offline protection results; no live interpretation result changes those numbers.

**Rubric coverage limitation:** Separate order and clarification-request verdicts were not included in the frozen rubric, so those criteria remain unmeasured as separate categories.

Content accounting uses the approved signed per-call formula; when measured input is below the fixed baseline, the estimate may be negative. The execution guard originally clamped individual values at zero, a conservative budget check; this report records the exact approved formula.
