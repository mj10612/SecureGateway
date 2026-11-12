# #311 role aliases: REJECT

A-eligible cases: 79; whole-task A/C/D passes: 79/71/68. D-only/C-only: 0/3; one-sided sign-test p=1.0. The role-relation criterion loses two cases, independently failing the criterion gate.

| Criterion | Applicable | A | C | D |
| --- | ---: | ---: | ---: | ---: |
| intent | 79 | 79 | 75 | 75 |
| action | 79 | 79 | 71 | 70 |
| conditions | 27 | 27 | 27 | 27 |
| prohibition | 61 | 61 | 60 | 60 |
| order | 17 | 17 | 17 | 17 |
| clarification | 20 | 20 | 20 | 20 |
| scope | 79 | 79 | 73 | 73 |
| role_relation | 79 | 79 | 76 | 74 |

Negative controls: 7 A-eligible, net loss 0. Protection: 0 newly exposed, exact restore 29/29, CI compare passed, and 0 category leaks in 12 private-role fixtures. Baseline and candidate each exposed 156 of 174 gold spans; the gate tests regression, not absolute protection.

Isolation and budget: 240 fresh read-only zero-tool interpretations; 80 blind grades with mechanically verified quotes; 5037302 raw and 231222 content tokens. The previous interrupted attempt is preserved separately and excluded. The interpreter and grader are the same model family; the sample is synthetic and enriched for changed inputs, so these figures do not estimate population effects.
