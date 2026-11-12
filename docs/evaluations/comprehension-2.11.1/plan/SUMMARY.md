# Real-LLM comprehension plan - preflight revision

No interpretation, grading, inference-attack or offline protection-gate evaluation has been run. Pilot evidence is in `pilot/` only. The coordinator approved the base plan, the 2048 multi-response grade cap, the absolute two-case protection non-inferiority limit, and the #315/#319 treatment exceptions. Preflight remains **INCOMPLETE** for two variants.

| Candidate | Cases | C != D non-controls | Changed controls | Relevant random sample | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| #309 Korean condition/order/negation | 46 | 27/38 | 0/8 | 10/10 | PASS |
| #310 name-context protection | 48 | 40/40 | 0/8 | 10/10 | PASS |
| #311 role hints; private-category check | 80 | 68/72 | 0/8 | 10/10 | PASS |
| #312 numeric contexts/code review | 48 | 40/40 | 0/8 | 10/10 | PASS |
| #313 mixed-language instruction | 42 | 24/34 | 0/8 | 10/10 | PASS |
| #314 daily vocabulary | 78 | 1/70 | 0/8 | 2/10 | BLOCKED |
| #315 concise instruction | 80 | 72/72 | 0/8 | 10/10 | PASS |
| #315 example instruction | 80 | 72/72 | 0/8 | 10/10 | PASS |
| #316 scoped correction | 48 | 40/40 | 0/8 | 10/10 | PASS |
| #317 structure only | 63 | 0/55 | 0/8 | 0/10 | BLOCKED |
| #317 structure with field policy | 47 | 39/39 | 0/8 | 10/10 | PASS |
| #318 attribute bundle/inference attack | 48 | 40/40 | 0/8 | 10/10 | PASS |
| #319 local tool | 24 | 20/20 | 0/4 | 10/10 | PASS |

#306 shares #309 (46 cases including eight human-minimal B controls); #291 has 34 newly authored requests and two known requests, with no candidate. For #315 and #319 only, the full payload intentionally differs on every case; control counts compare masked task and active alias bindings, as approved. The A-passing analysis-set C != D counts are **pending** until A is graded. The case sets were enriched offline for observable C/D differences; results are conditional on that selection and do not estimate effects across typical inputs.

**Blockers.** #314 has only 6 changed cases among 309 screened non-controls across the original and five independently authored targeted batches, with 47 unchanged controls. Its current 10-case relevance check passes only 2/10. #317 structure-only has four changed cases among 165 screened non-controls across original and targeted sets; its current review passes 0/10. The independently evaluated structure-policy variant passes with 39/39 changed and eight unchanged controls. No interpretation can begin under the coordinator's all-candidate preflight instruction until these two failures are resolved or the instruction is revised. Details, counts, discarded cases, author provenance and per-case sample reviews are under each issue's `plan/`.

Protection-target corpora #310/#312/#316/#318 have **174/174, 180/180, 180/180, 156/156 sensitive/public spans** after offset validation. #311 has 12 separate private-category fixtures. Common rubric: intent, action, conditions, prohibition, order, clarification exactly when needed, output scope/format, plus the issue-specific criteria in each `rubric.json`. Synthetic provenance and offset, duplicate, applicability-shape and email-pattern checks are recorded; no automated check proves a fictional name cannot coincide with a real one.

Decision rules are unchanged: comprehension requires the protection gate, one-sided paired sign test p < 0.05 favoring D, no criterion net loss >=2, and no negative-control net regression. Protection requires its gate, >0 newly protected, zero newly exposed, <=2 extra public over-masks, and absolute net paired loss <=2; #318 also requires lower top-1 inference success. #319 uses its separate tool and payload gates. Errors, missing evidence or ungraded cases are INCOMPLETE and rerun, never decided.

Per case: one fresh interpretation per condition, one blinded multi-response grade, verified quote for every verdict, and at most one re-grade. Interpretation cap 512, grading cap 2048 where needed. Current **provisional** estimate is 2,986 initial calls, 47,285,112 raw tokens and 2,217,414 content tokens, excluding case authoring and re-grades; #314 and structure-only #317 budgets will change if their holdouts change. At an illustrative 10% D-only effect with no losses and all A cases passing, 42 cases yield about 41% detection probability and 46 about 49%; these smaller enriched samples are less decisive than 80 and effects may be missed. The interpreter and grader use the same model family.
