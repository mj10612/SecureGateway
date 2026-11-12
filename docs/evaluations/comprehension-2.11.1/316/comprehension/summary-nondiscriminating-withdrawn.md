# #316 real-LLM comprehension

The interpreter and grader use the same model family. These synthetic cases were enriched for observable candidate differences and do not estimate population rates.

## 316: REJECT

A-eligible cases: 35. Whole-task pass counts: A=35, C=31, D1=29; D-only=0, C-only=2, one-sided p=1.0. Negative controls: 8; net loss=0.

Protection: 0 newly protected of 180 spans, 0 newly exposed; public overmask C/D=0/0 of 180; exact restore C/D=30/30 of 30; CI=passed.

| Criterion | A | C | D | Cases |
| --- | ---: | ---: | ---: | ---: |
| intent | 35 | 32 | 30 | 35 |
| action | 35 | 31 | 29 | 35 |
| conditions | 8 | 7 | 7 | 8 |
| prohibition | 26 | 26 | 25 | 26 |
| order | 5 | 4 | 4 | 5 |
| clarification | 8 | 8 | 8 | 8 |
| scope | 35 | 31 | 31 | 35 |
| followup | 35 | 33 | 32 | 35 |

Fresh interpretations: 144; blinded quote-verified grades: 48; successful-call raw tokens: 3339755; content tokens: 456107.

See the manifest, first responses, first grades, frozen rubric and decision, and report JSON for isolation, per-case evidence, usage, and reproducibility.
