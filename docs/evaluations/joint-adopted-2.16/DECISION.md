# Joint decision: #310 + #316 (B) + #318 — ADOPT-JOINT (no model run)

Decided by the coordinator after reviewing the `--prepare` output (commit
`e4c2667`), **before any model call**. The comprehension run, the freeze and the
#318 attack were not performed; `preregistration.json` is retained but was never
frozen and is superseded by this document.

## Why no comprehension run

A joint run can only detect an interaction if the joint configuration shows the
model something different from what each candidate showed on its own. It does not:

- **Model-visible input.** All 144 frozen comprehension cases (48 each from #310,
  #316 and #318, 24 negative controls) were captured with 2.16.0
  `GatewaySession(features=...)`: C = `GatewayFeatures()`, J =
  `contextual_name_spans` plus the case's own trusted #316/#318 policy. Arms were
  compared after replacing every alias by its bound original
  (`⟦original⟧`), with the privacy instructions included, because numeric
  aliases are random per capture. Result (`plan/precheck.json`):
  - J equals the candidate's original frozen D1 on **144/144** cases, and the
    new C equals the original C on **144/144**.
  - J differs from C on 110/120 non-control cases (#310 40/40, #316 38/40,
    #318 32/40), exactly the cases where the original D differed; 0 cases where
    D differed but J does not; 0 cases where J differs but D did not; 0 controls
    changed.
- **Offline protection.** On all 257 protection cases, the joint outbound payload
  is byte-identical to the single-candidate payload (`offline/*/summary.json`,
  `joint_payload_differs_from_single = 0`).

A comprehension re-run would therefore only re-measure the old C vs D
comparisons on another model and transport.

## Offline gate (part a, measured)

| Set | Sensitive / public | Exposed baseline / single / joint | Newly protected single / joint | Newly exposed (joint vs baseline) | Public overmask B / S / J | Exact restore B / S / J |
|---|---|---|---|---|---|---|
| #310 `introducer-cases.json` (22) | 132 / 132 | 132 / 44 / 44 | 88 / 88 | 0 | 0 / 0 / 0 | 22 / 22 / 22 |
| #316 `protection-correction-sensitive.json` (208) | 104 / 104 | 104 / 0 / 0 | 104 / 104 | 0 | 0 / 0 / 0 | 208 / 208 / 208 |
| #318 `protection-bundle-table.json` (27) | 108 / 108 | 108 / 0 / 0 | 108 / 108 | 0 | 0 / 0 / 0 | 27 / 27 / 27 |

The single arm reproduced each ADOPT decision's numbers exactly. CI: an
in-process privacy report with all three features on (`offline/ci-joint/`),
compared with `secure-gateway evaluate compare --baseline
docs/evaluations/issue324-2.7.0/legacy-privacy/report.json`: exit 0, comparable,
no regression, 0 new exposures, 0 integrity regressions.

## Decision

**ADOPT-JOINT.** The offline gate passes on every set and on the CI corpus.
Comprehension non-inferiority transfers from each candidate's measured result
because the model-visible input under J is identical to that candidate's D:

| Candidate | Evidence | A-eligible | A / C / D | D-only / C-only |
|---|---|---|---|---|
| #310 | `comprehension-2.11.1/310/comprehension/report.json` | 30 | 30 / 27 / 27 | 0 / 0 |
| #316 B | `comprehension-2.11.1/316/comprehension/report.json` | 35 | 35 / 31 / 29 | 0 / 2 (within the 2-case bound) |
| #318 | `comprehension-2.11.1/318/comprehension/report.json` | 36 | 36 / 29 / 29 | 0 / 0 |

Pooled net paired loss is 2, and negative controls have no net loss in any
of the three.

## Limitations

- The transferred comprehension results come from `gpt-6.1-sol` on the native
  transport (2.11.1 runs), not from the lean transport/`gpt-6-luna` used for
  newer runs.
- #316 and #318 policies are bound to one project or one document hash, so the two
  never co-occur on a comprehension or protection case. Their interaction is
  untested except on the CI privacy corpus, where all three ran together.
- The #318 catalogue attack under J was not rerun. Its input is identical to the
  original D, so the original attack result (top-1 39 → 8) applies unchanged.
- The interpreter and grader of the original runs share a model family. The
  synthetic cases were enriched for candidate differences.
