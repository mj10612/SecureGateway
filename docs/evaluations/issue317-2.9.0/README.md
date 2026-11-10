# Issue #317 Evaluation Evidence (v2.9.0)

## Overview & Execution Context
- **Issue:** #317 table/form field-vs-value handling
- **Candidates:** `doc_structure` (B: parse only) and `doc_structure_policy` (C: + per-field policy)
- **Status:** **부분 완료** (파서 구현, cells 인터페이스 공개, 토글 OFF 바이트 동일성 완료 / 실 LLM 이해도 미측정)
- **Decision:** **hold — comprehension 미측정** (토글 기본값 OFF 유지)
- **Regeneration Command:** `uv run python scripts/generate_evidence_directories.py`
- **Note on Latency & Memory:** Latency and memory were measured on a machine under load from other jobs (in-process loopback samples; does not establish production latency or cold-process performance).

## Development vs Holdout Corpora
- **Development Corpus:** `docs/evaluations/accuracy-20261109/development-cases.json`
- **Committed Holdout Corpus:** `docs/evaluations/accuracy-20261109/holdout-cases.json` (cases for issue 317: `holdout-317-en-1`, `holdout-317-ko-1`)
- **Freeze:** Pre-declared thresholds, sample size (n=2), and pass criteria were committed in `freeze.json` before running the holdout.

## Side-by-Side Protection Measurements
| Measurement | Baseline | Candidate (doc_structure) | Status |
| --- | ---: | ---: | --- |
| Fully protected sensitive occurrences | 3 / 6 | 4 / 6 | Maintained (No regression) |
| Full exposures | 3 / 6 | 2 / 6 | No new exposures |
| Partial exposures | 0 / 6 | 0 / 6 | Zero |
| Overmasked public spans | 0 / 8 | 0 / 8 | Preserved |
| Exact echoed-string restoration | 2 / 2 | 2 / 2 | Passed |
| Semantic restoration | 2 / 2 | 2 / 2 | Passed |
| Replay stability | 2 / 2 | 2 / 2 | Passed |
| Session isolation / encrypted restart | Passed | Passed | Passed |
| Real-LLM Comprehension | 미측정 | 미측정 | 미측정 (환경/예산 제약) |

## Latency & Traced Memory
- **Baseline warm p95:** 1.382 ms
- **Candidate warm p95:** 1.194 ms (<= 1.25x baseline + 5ms gate passed)
- **Candidate peak traced memory:** 320.2 KiB

## Acceptance Bullets Status
- [x] **Linear-pass offset-preserving parser:** Implemented in `structure_parser.py` without rewriting, reordering, or summarizing text.
- [x] **Interface cells(text):** Exposes `cells(text) -> [(row, field_name, start, end)]` for future consumption by #318 at merge.
- [x] **Reviewed public headers:** Public header names stay public; sensitive cell values protected.
- [x] **Local field policy (C):** Policy mapping field names to always-mask implemented.
- [x] **Protocol protection boundary:** User-data keys such as `id/type/model/system` inside cells are never promoted to protocol exceptions.
- [x] **Safe fallback:** Broken/ambiguous tables safely fall back to existing path and increment fallback count.
- [x] **Toggle-off byte identity:** Proven 100% byte-identical against `origin/main` (`c92733f`) in `tests/test_toggle_off_byte_identity.py`.
- [x] **Evidence directory:** Documented in `docs/evaluations/issue317-2.9.0/`.
- [ ] **Real-LLM comprehension:** Not run (recorded as **미측정**).
