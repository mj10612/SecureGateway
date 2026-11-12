# #315 instruction variants: real-LLM evaluation

80 independently authored synthetic cases, one response per condition; all 320 interpretations were saved before the 80 blinded case grades. The analysis set comprises cases where the original-text A control passed all applicable criteria.

## instruction_concise: REJECT

A-eligible 74/80; A/C/D all-criterion passes 74/60/56. D-only improvements 1; C-only 5; exact one-sided p=0.984375. Negative controls: 8 A-eligible, net loss 1. Input differs by construction in 74/74 analysis cases.

| Criterion | A pass | C pass | D pass | Applicable |
| --- | ---: | ---: | ---: | ---: |
| intent | 74 | 68 | 65 | 74 |
| action | 74 | 61 | 59 | 74 |
| conditions | 13 | 13 | 13 | 13 |
| prohibition | 72 | 72 | 72 | 72 |
| order | 12 | 12 | 12 | 12 |
| clarification | 13 | 12 | 9 | 13 |
| scope | 74 | 63 | 62 | 74 |
| solvable_without_original | 57 | 53 | 51 | 57 |
| hidden_value_limit | 17 | 16 | 16 | 17 |
| alias_identity | 8 | 8 | 8 | 8 |
| tool_alias | 10 | 5 | 4 | 10 |
| injection_resistance | 11 | 11 | 11 | 11 |

Protection: 0 newly exposed spans; exact restore 29/29 baseline and 29/29 candidate; legacy CI comparison passed.

## instruction_examples: REJECT

A-eligible 74/80; A/C/D all-criterion passes 74/60/58. D-only improvements 1; C-only 3; exact one-sided p=0.9375. Negative controls: 8 A-eligible, net loss 1. Input differs by construction in 74/74 analysis cases.

| Criterion | A pass | C pass | D pass | Applicable |
| --- | ---: | ---: | ---: | ---: |
| intent | 74 | 68 | 68 | 74 |
| action | 74 | 61 | 60 | 74 |
| conditions | 13 | 13 | 13 | 13 |
| prohibition | 72 | 72 | 72 | 72 |
| order | 12 | 12 | 12 | 12 |
| clarification | 13 | 12 | 11 | 13 |
| scope | 74 | 63 | 62 | 74 |
| solvable_without_original | 57 | 53 | 52 | 57 |
| hidden_value_limit | 17 | 16 | 17 | 17 |
| alias_identity | 8 | 8 | 8 | 8 |
| tool_alias | 10 | 5 | 5 | 10 |
| injection_resistance | 11 | 11 | 11 | 11 |

Protection: 0 newly exposed spans; exact restore 29/29 baseline and 29/29 candidate; legacy CI comparison passed.

## Usage and isolation

| Arm | Calls | Raw tokens | Content tokens | Mean content token delta vs C | Median latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 80 | 1221664 | 20144 | - | 5.98 |
| C | 80 | 1223657 | 22137 | - | 6.11 |
| D1 | 80 | 1214297 | 12777 | -117.0 | 6.45 |
| D2 | 80 | 1220021 | 18501 | -45.5 | 6.11 |

Total interpretation plus grading usage: 6339836 raw tokens and 332236 content tokens; each call's elapsed time and usage is recorded in the first-response/grade records. All 320/320 interpretations used a fresh read-only context with zero tool events. All 80 case grades have verified excerpts; 0 required regrading.

Interpreter and grader are from the same model family; synthetic cases and the selected instruction variants do not establish real-world generality.

Tool-argument criteria assess arguments produced in the response; interpreters were not allowed to invoke tools. Actual local arithmetic tool execution is assessed separately under #319.
