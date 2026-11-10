# Issue #315 Evaluation Evidence (v2.9.0)

## Overview & Execution Context
- **Issue:** #315 masking-instruction wording
- **Candidates:** `instruction_concise` (B) and `instruction_examples` (C) behind isolated toggles (default OFF)
- **Status:** **부분 완료** (지침 구현, 페이로드/별칭 바이트 동일성, 증거 수집 완료 / 실 LLM 이해도 미측정)
- **Decision:** **hold — comprehension 미측정** (토글 기본값 OFF 유지)
- **Regeneration Command:** `uv run python scripts/generate_evidence_directories.py`
- **Note on Latency & Memory:** Latency and memory were measured on a machine under load from other jobs (in-process loopback samples; does not establish production latency or cold-process performance).

## Development vs Holdout Corpora
- **Development Corpus:** `docs/evaluations/accuracy-20261109/development-cases.json`
- **Committed Holdout Corpus:** `docs/evaluations/accuracy-20261109/holdout-cases.json` (cases for issue 315: `holdout-315-en-1`, `holdout-315-ko-1`)
- **Freeze:** Pre-declared thresholds, sample size (n=2), and pass criteria were committed in `freeze.json` before running the holdout.

## Side-by-Side Protection Measurements
| Measurement | Arm A (Baseline) | Arm B (Concise) | Arm C (Examples) |
| --- | ---: | ---: | ---: |
| Instruction length (chars) | 1106 | 511 | 778 |
| Masked payload byte delta | 0 (Byte-identical) | 0 (Byte-identical) | 0 (Byte-identical) |
| Fully protected sensitive occurrences | 4 / 6 | 4 / 6 | 4 / 6 |
| Full exposures | 2 / 6 | 2 / 6 | 2 / 6 |
| Partial exposures | 0 / 6 | 0 / 6 | 0 / 6 |
| Overmasked public spans | 0 / 8 | 0 / 8 | 0 / 8 |
| Exact echoed-string restoration | 2 / 2 | 2 / 2 | 2 / 2 |
| Semantic restoration | 2 / 2 | 2 / 2 | 2 / 2 |
| Replay stability | 2 / 2 | 2 / 2 | 2 / 2 |
| Session isolation / encrypted restart | Passed | Passed | Passed |
| Real-LLM Comprehension | 미측정 | 미측정 | 미측정 (환경/예산 제약) |

## Latency & Token Delta
- Concise saves 595 characters (~15 tokens) in system prompt.
- Examples adds -328 characters (~50 tokens) with synthetic disjoint examples.
- Masked payload byte delta across A/B/C is strictly 0 bytes.

## Acceptance Bullets Status
- [x] **Instruction replacement:** Replaces only `PRIVACY_INSTRUCTION` text at request dispatch.
- [x] **Payload byte identity:** Masked payload and aliases 100% byte-identical across A/B/C (`tests/test_instruction_wording.py`).
- [x] **Synthetic disjoint examples:** Candidate C uses synthetic examples disjoint from evaluation data.
- [x] **Toggle-off byte identity:** Proven 100% byte-identical against `origin/main` (`c92733f`) in `tests/test_toggle_off_byte_identity.py`.
- [x] **Evidence directory:** Documented in `docs/evaluations/issue315-2.9.0/`.
- [ ] **Real-LLM comprehension:** Not run (recorded as **미측정**).
