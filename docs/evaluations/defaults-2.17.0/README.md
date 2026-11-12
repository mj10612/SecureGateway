# CI privacy comparison of the 2.17.0 gateway defaults

`run_defaults_ci.py` generates two legacy-corpus privacy reports in-process
(release profile, secure-gateway 2.17.0). The gateway in each is constructed from
`resolve_settings` features:

- **new default** `resolve_settings({})`: `contextual_name_spans` active;
  `scoped_corrections` and `attribute_bundle` policy-gated and inactive (no policy).
- **old default** `resolve_settings({}, all_off=True)`: nothing, the 2.15/2.16 path.

Each report was compared with
`secure-gateway evaluate compare --baseline docs/evaluations/issue324-2.7.0/legacy-privacy/report.json`.

| Metric (legacy corpus) | Old default | New default |
|---|---|---|
| compare exit / regression | 0 / no | 0 / no |
| new / resolved exposures vs baseline | 0 / 0 | 0 / 0 |
| integrity regressions | 0 | 0 |
| fully protected / sensitive | 57 / 66 | 57 / 66 |
| full / partial exposures | 9 / 0 | 9 / 0 |
| public overmasked / measured | 3 / 117 | **4 / 117** |
| exact roundtrip | 31 / 32 | 31 / 32 |

The legacy corpus contains no direct name introductions, so #310's measured gain
(88/132 newly protected name spans with no new exposure, `../joint-adopted-2.16/offline/310/`)
does not show here. The one additional overmask is a false positive in the case
`ko-general-contextual-flow`. The Korean introducer pattern reads
`파일 이름은 바꾸지 말며` ("do not change the file names") as "name is 바꾸지" and
masks the verb, hiding the prohibition. The same text also has the unannotated
modifier `가상` in `가상 프로젝트` masked. The sensitive word `흐름` in that case
was already exposed under both defaults (it is one of the 9 known exposures).

Files: `summary.json`, `new-default/` and `old-default/` (reports and comparisons).
