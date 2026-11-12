# #318 real-LLM comprehension

The interpreter and grader use the same model family. These synthetic cases were enriched for observable candidate differences and do not estimate population rates.

## 318: ADOPT

A-eligible cases: 36. Whole-task pass counts: A=36, C=29, D1=29; D-only=0, C-only=0, one-sided p=1.0. Negative controls: 6; net loss=0.

Protection: 108 newly protected of 108 spans, 0 newly exposed; public overmask C/D=0/0 of 108; exact restore C/D=27/27 of 27; CI=passed.

| Criterion | A | C | D | Cases |
| --- | ---: | ---: | ---: | ---: |
| intent | 36 | 33 | 33 | 36 |
| action | 36 | 29 | 29 | 36 |
| conditions | 18 | 18 | 18 | 18 |
| prohibition | 36 | 36 | 36 | 36 |
| order | 6 | 5 | 5 | 6 |
| clarification | 17 | 17 | 17 | 17 |
| scope | 36 | 31 | 31 | 36 |
| bundle_task | 36 | 29 | 29 | 36 |

Fresh interpretations: 144; blinded quote-verified grades: 48; successful-call raw tokens: 3421338; content tokens: 537690.

See the manifest, first responses, first grades, frozen rubric and decision, and report JSON for isolation, per-case evidence, usage, and reproducibility.

The independent catalogue attack completed 144 fresh calls: catalogue-only prior top-1/top-3 0/0, baseline 39/39, candidate 8/8 (48 cases per arm); abstentions were 48, 9, and 40 respectively. Direct exposure did not increase. See `../inference-attack/report.json` for attack usage and records.

The replacement protection pre-check found 108/108 baseline-exposed targeted spans and 108/108 baseline-public controls. The field groups had been screened in a failed form representation before table assembly; four were excluded after format exploration, but 22 retained groups had prior baseline-only screening. This limits the offline holdout independence; see `../plan/holdout-format-provenance.md`.
