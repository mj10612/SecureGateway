# 2.17.0 gateway defaults: #310 predicate guard and CI privacy comparison

No model call was made. All files here were produced with secure-gateway 2.17.0,
rebased on 2.16.1 (#368).

## Why a guard was needed

The first 2.17.0 candidate enabled #310 unchanged. On the legacy CI corpus it masked
`바꾸지` in `파일 이름은 바꾸지 말며` ("do not change the file names"): the introducer
pattern `이름은 <word>` took the prohibition verb as a name, hiding the
instruction from the model. It also masked the modifiers `가상`/`차량`/`반도체` in
`가상 (차량) 프로젝트 <name>의`. Public overmask went from 3 to 4 of 117.

`experiment_context.name_spans` now rejects:

- an unquoted introducer value that is a predicate:
  - a Korean word with an unambiguous verbal ending from the `grammar_ko`
    conjugation table, or a final/request ending, but never a copula;
  - a connective (`-지/-고/-게/-도록/-기` or open-syllable `-어/-아`) followed by a
    negation (`말/마/않/못`) or by a conjugated auxiliary (`주세요`, `있다`);
  - `-ㄹ/-을` followed by a bound noun (`수`, `것`);
  - an English modal, copula or `to`/`later` (lowercase);
- a spaced word in `<word> 프로젝트 <name>의`, where the name is the following word.

Forced rules and aliases registered earlier still win, and quoted explicit names are
unaffected.

## (a) Frozen comprehension inputs (`fix-310/summary.json`)

The 144 frozen cases were re-captured (C = all off, J = adopted features with the
case policy) and compared with the original frozen C/D1 after alias
canonicalization:

| Source | C unchanged | J equal to original D |
|---|---|---|
| #310 | 48/48 | **47/48** |
| #316 | 48/48 | 48/48 |
| #318 | 48/48 | 48/48 |

The one change is `310:targeted-H30` (`… 이유나 제품 이름은 덧붙이지 마세요.`):

- The old D masked the prohibition verb `덧붙이지` ("do not add").
- The new J keeps it visible; the introduced product name stays masked.
- In the original run, A, C and D all passed every criterion on this case
  (a tie that contributes nothing to the 0/0 discordances), so the transferred
  #310 result (A/C/D 30/27/27) is unaffected. The new input itself was not
  re-measured.

## (b) Offline protection (`fix-310/summary.json`)

| Set | Newly protected single / joint | Newly exposed | Public overmask B/S/J | Exact restore B/S/J |
|---|---|---|---|---|
| #310 introducer (22) | 88 / 88 of 132 | 0 | 0/0/0 | 22/22/22 |
| #316 correction-sensitive (208) | 104 / 104 | 0 | 0/0/0 | 208/208/208 |
| #318 bundle-table (27) | 108 / 108 | 0 | 0/0/0 | 27/27/27 |

These are identical to the numbers behind each ADOPT decision.

## (c) CI privacy comparison (`run_defaults_ci.py`, `summary.json`)

Two legacy-corpus privacy reports were generated in-process, one with the new
default (`resolve_settings({})`: #310 active, #316/#318 policy-gated and inactive)
and one with the old default (`all_off`). Each was compared with
`secure-gateway evaluate compare --baseline docs/evaluations/issue324-2.7.0/legacy-privacy/report.json`.

| Metric | Old default | New default |
|---|---|---|
| compare exit / regression | 0 / no | 0 / no |
| new / resolved exposures | 0 / 0 | 0 / 0 |
| integrity regressions | 0 | 0 |
| protected / sensitive | 57 / 66 | 57 / 66 |
| public overmasked | 3 / 117 | **3 / 117** |
| exact roundtrip | 31 / 32 | 31 / 32 |

All metrics are identical. The legacy corpus has no direct name introductions, so
#310's gain shows only in (b).

Regression tests: `tests/test_name_context_predicates.py`, `tests/test_feature_defaults.py`.
