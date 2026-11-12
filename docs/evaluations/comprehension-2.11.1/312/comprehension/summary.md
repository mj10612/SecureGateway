# #312 numeric contexts: REJECT

Corrected offline protection: 0 newly protected and 0 newly exposed spans among 180 sensitive spans; C/D exposed 0/0. C/D overmasked 95/95 of 160 public spans; exact restore 62/62; CI compare passed. The predeclared requirement of more than zero newly protected spans was not met.

| Public context | Spans | C overmasked | D overmasked |
| --- | ---: | ---: | ---: |
| prose_quantity | 25 | 25 | 25 |
| prose_duration_date | 25 | 25 | 25 |
| version | 20 | 20 | 20 |
| code_loop_constant | 25 | 0 | 0 |
| json_numbers | 25 | 25 | 25 |
| code_loop_index | 40 | 0 | 0 |

Comprehension: 37 A-eligible; A/C/D passes 37/33/33; D-only/C-only 1/1; one-sided p=0.75; 6 negative controls, net loss 0.

| Criterion | Applicable | A | C | D |
| --- | ---: | ---: | ---: | ---: |
| intent | 37 | 37 | 35 | 35 |
| action | 37 | 37 | 35 | 34 |
| conditions | 18 | 18 | 18 | 17 |
| prohibition | 27 | 27 | 27 | 27 |
| order | 5 | 5 | 5 | 5 |
| clarification | 4 | 4 | 4 | 4 |
| scope | 37 | 37 | 35 | 35 |
| code_review | 33 | 33 | 31 | 32 |

The first protection result and REJECT were withdrawn: all 180 original public spans were key-value assignments. The original capture used default natural_language=auto, prose_mode=content_words, mask_numbers=false; D enabled numeric_context. Eight synthetic samples are recorded in the plan. The corrected set combines 180 original sensitive spans with 160 new independently authored, offset-validated public spans, with zero discarded cases; only public measurements changed. One offline rerun stopped on PermissionError after 11 cases; that partial attempt is preserved, and the next offline rerun completed.

Isolation and budget: 144 fresh read-only zero-tool interpretations; 48 blind quote-verified grades; 3049715 raw and 166067 content tokens, excluding independent case authoring. No interpretation or grading was repeated for this correction. Interpreter and grader are the same model family; the synthetic sample is enriched for changed inputs and is not a population estimate.
