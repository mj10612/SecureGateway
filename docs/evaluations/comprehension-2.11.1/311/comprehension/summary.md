# Issue 311: merged role alias candidate

Decision: **REJECT**. The one-sided paired sign test does not show a benefit; the protection gate passed.

A-eligible cases: 79; A/C/D all-criterion passes: 79/73/70; D-only/C-only: 0/3; one-sided p=1.0.

| Criterion | Eligible applicable cases | A pass | C pass | D pass |
| --- | ---: | ---: | ---: | ---: |
| intent | 79 | 79 | 78 | 77 |
| action | 79 | 79 | 73 | 71 |
| conditions | 27 | 27 | 27 | 27 |
| prohibition | 61 | 61 | 61 | 61 |
| order | 17 | 17 | 17 | 17 |
| clarification | 20 | 20 | 20 | 20 |
| scope | 79 | 79 | 73 | 72 |
| role_relation | 79 | 79 | 78 | 76 |

Negative controls: 7; net loss 0. Protection: 0 newly exposed; 0 newly protected; overmask increase 0; exact restore C/D 29/29; CI passed; private-category leak checks 0/12.
Interpretations: 240; blinded quote-verified grades: 80; raw tokens: 5398715; content tokens: 592635. Each interpreter was fresh, read-only, and had zero tool events. The interpreter and grader share a model family. The sample was enriched for observable changes, and findings do not estimate a population rate.

Raw records: `manifest.json`, `first-responses.jsonl`, `first-grades.jsonl`, and `report.json`. The pre-#345 result is withdrawn and archived separately.
