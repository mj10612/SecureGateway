# Issue #319 Evaluation Evidence (v2.9.0)

## Overview & Execution Context
- **Issue:** #319 local arithmetic tool over masked numbers/dates
- **Candidate:** `local_arithmetic` behind isolated profile toggle (default OFF)
- **Status:** **부분 완료** (디스패처 구현, 로컬 연산 및 별칭 등록, strict 복원 완료 / 실 LLM 인터프리터 호출 미측정)
- **Decision:** **hold — comprehension 미측정** (토글 기본값 OFF 유지)
- **Tool Name:** `local_alias_arithmetic`
- **Regeneration Command:** `uv run python scripts/generate_evidence_directories.py`
- **Note on Latency & Memory:** Latency and memory were measured on a machine under load from other jobs (in-process loopback samples; does not establish production latency or cold-process performance).

## Development vs Holdout Corpora
- **Development Corpus:** Unit fixtures in `tests/test_private_arithmetic.py` and `tests/test_local_arithmetic_dispatcher.py`
- **Holdout Corpus:** **미측정** (`docs/evaluations/accuracy-20261109/` 내 #319 전용 분리 홀드아웃 파일 부재로 홀드아웃 결과는 미측정으로 기록)
- **Freeze:** Dispatcher latency threshold (<=10 ms) and error leak gates fixed in `freeze.json`.

## Side-by-Side Protection Measurements
| Measurement | Baseline | Candidate (local_arithmetic) | Status |
| --- | ---: | ---: | --- |
| Fully protected sensitive occurrences | 4 / 4 | 4 / 4 | Maintained |
| Full exposures | 0 / 4 | 0 / 4 | Zero exposures |
| Partial exposures | 0 / 4 | 0 / 4 | Zero |
| Overmasked public spans | 0 / 2 | 0 / 2 | Preserved |
| Exact echoed-string restoration | 2 / 2 | 2 / 2 | Passed |
| Semantic restoration | 2 / 2 | 2 / 2 | Passed |
| Replay stability | 2 / 2 | 2 / 2 | Passed |
| Session isolation / encrypted restart | Passed | Passed | Passed |
| Real-Interpreter Tool Call Comprehension | 미측정 | 미측정 | 미측정 (네이티브 MCP 루프백 미활성) |

## Dispatcher Performance & Operations
- **Dispatcher p50 Latency:** 0.024 ms
- **Dispatcher p95 Latency:** 0.032 ms (Target <= 10 ms: **Passed**)
- **Original Exposure:** Zero raw originals or calculated values exposed in tool output or descriptions.

| Operation | Operands | Expected Result | Alias Result | Local Restoration | Status |
| --- | --- | --- | --- | --- | --- |
| multiply | 12.75 USD, 4 count | 51.00 USD | new alias | 51.00 USD | Passed |
| add | 100.50, 49.50 | 150.00 | new alias | 150.00 | Passed |
| subtract | 200.00, 75.25 | 124.75 | new alias | 124.75 | Passed |
| date_difference | 2032-02-27, 2032-03-02 | 4 days | new alias | 4 days | Passed |
| unknown alias | private_symbol_9999 | ValueError | None | Rejected | Passed |
| foreign session | alias from other session | ValueError | None | Rejected | Passed |
| user tool collision | user defines local_alias_arithmetic | ValueError | None | Collision prevented | Passed |

## Acceptance Bullets Status
- [x] **Local dispatcher interception:** Injects tool only when toggle is on; intercepts `local_alias_arithmetic` from response; removes tool call from host view.
- [x] **Supported operations:** Decimal add, subtract, multiply, and ISO date difference within one session.
- [x] **New alias registration:** Resolves originals locally; registers result as a NEW alias; never overwrites.
- [x] **Zero disclosure:** Errors and descriptions never contain originals or calculated values.
- [x] **Integrity & bounds:** Operation allowlist, arity/call limits, no `eval`, no filesystem, no network. Unknown/foreign/mutated aliases rejected.
- [x] **Name collision prevention:** Rejects requests if user defines a conflicting tool named `local_alias_arithmetic`.
- [x] **Derived alias persistence:** Snapshot serialization, restart, and strict restoration verified.
- [x] **Toggle-off byte identity:** Proven 100% byte-identical against `origin/main` (`c92733f`) in `tests/test_toggle_off_byte_identity.py`.
- [x] **Evidence directory:** Documented in `docs/evaluations/issue319-2.9.0/`.
- [ ] **Real-interpreter tool execution in LLM:** Not run (recorded as **미측정**; test environment lacks real interpreter loopback).
