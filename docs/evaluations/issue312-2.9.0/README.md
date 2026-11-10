# Issue #312 Evaluation Evidence (v2.9.0)

## Overview & Execution Context
- **Issue:** #312 format+field-context sensitive numbers/identifiers
- **Candidate:** `numeric_context` (C) behind isolated profile toggle (default OFF)
- **Status:** **부분 완료** (코드 구현, 토글 OFF 바이트 동일성, 증거 수집 완료 / 실 LLM 이해도 미측정)
- **Decision:** **hold — comprehension 미측정** (토글 기본값 OFF 유지)
- **Regeneration Command:** `uv run python scripts/generate_evidence_directories.py`
- **Note on Latency & Memory:** Latency and memory were measured on a machine under load from other jobs (in-process loopback samples; does not establish production latency or cold-process performance).

## Development vs Holdout Corpora
- **Development Corpus:** `docs/evaluations/accuracy-20261109/development-cases.json`
- **Committed Holdout Corpus:** `docs/evaluations/accuracy-20261109/holdout-cases.json` (cases for issue 312: `holdout-312-en-1`, `holdout-312-ko-1`)
- **Freeze:** Pre-declared thresholds, sample size (n=2), and pass criteria were committed in `freeze.json` before running the holdout.

## Side-by-Side Protection Measurements
| Measurement | Baseline | Candidate (numeric_context) | Status |
| --- | ---: | ---: | --- |
| Fully protected sensitive occurrences | 6 / 8 | 6 / 8 | Maintained (No regression) |
| Full exposures | 2 / 8 | 2 / 8 | No new exposures |
| Partial exposures | 0 / 8 | 0 / 8 | Zero |
| Overmasked public spans | 2 / 8 | 2 / 8 | Preserved |
| Exact echoed-string restoration | 2 / 2 | 2 / 2 | Passed |
| Semantic restoration | 2 / 2 | 2 / 2 | Passed |
| Replay stability | 2 / 2 | 2 / 2 | Passed |
| Session isolation / encrypted restart | Passed | Passed | Passed |
| Real-LLM Comprehension | 미측정 | 미측정 | 미측정 (환경/예산 제약) |

## Latency & Traced Memory
- **Baseline warm p95:** 1.871 ms
- **Candidate warm p95:** 1.09 ms (<= 1.25x baseline + 5ms gate passed)
- **Candidate peak traced memory:** 262.6 KiB

## Acceptance Bullets Status
- [x] **Format verification:** Luhn checksum (credit cards, IMEI), Korean RRN, Korean Business Registration Number checks implemented in `numeric_context.py`.
- [x] **Source structure context:** Sensitive numeric fields recognized via original JSON key path, structure parser field names, or adjacent prose label without reading aliased text.
- [x] **Failed checksum rule:** A failed checksum never marks a number public.
- [x] **Exact restoration:** Sign, leading zeros, precision, big integers, and JSON scalar type (int/float vs string) restored exactly.
- [x] **Protocol exclusion:** Provider protocol numbers (`max_tokens`, `temperature`, `top_p`) excluded from user data masking.
- [x] **Toggle-off byte identity:** Proven 100% byte-identical against `origin/main` (`c92733f`) in `tests/test_toggle_off_byte_identity.py`.
- [x] **Evidence directory:** Documented in `docs/evaluations/issue312-2.9.0/`.
- [ ] **Real-LLM comprehension:** Not run (recorded as **미측정**).
