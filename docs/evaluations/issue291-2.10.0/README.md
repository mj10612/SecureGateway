# Issue #291 Evaluation Evidence: Multilingual Verification across 17 Languages

- **Scope:** 17-language meaning preservation, sensitive value masking, known requests regression, offline tool/MCP/skills verification
- **Version:** `2.10.0`
- **Related Documentation:** `docs/LANGUAGES.md`
- **Status:** Verified (offline) / Decision: `verified (offline)` / Real provider: `미측정`

## Status Table

| Acceptance Requirement | Status | Evidence / Notes |
| :--- | :---: | :--- |
| Multilingual evaluation across 17 languages | Verified | en, ko, es, fr, pt, de, id, tr, ru, hi, mr, bn, ur, te, ar, zh, ja |
| Meaning-preservation & sensitive results reported separately | Reported | Non-merged metric tables per language |
| Regression test: `SecureMCP 삭제해줘` | PASS | `test_issue291_known_request_securemcp_delete` passes |
| Regression test: `Read SKILL.md before using this skill. Follow its instructions.` | PASS | `test_issue291_known_request_read_skill_md` passes |
| Tool-call round trip offline verification | PASS | Verified offline with fake provider (`test_gateway_tool_call_roundtrip_offline`) |
| MCP tool & skill-instruction handling offline verification | PASS | Verified offline with fake provider |
| Real provider / host verification | 미측정 | Real external endpoints require live host; reported as 미측정 |
| `docs/LANGUAGES.md` updated | Updated | Auto-detection limits, homonyms, evaluation commands documented |
| Latency overhead | Measured | Measured from committed benchmark script (100 runs) |
| Memory delta | 미측정 | Per-request memory delta cannot be isolated deterministically without OS process boundaries |

## Ordering Protocol (How Order was Handled)

- **Execution Order:** Multilingual sentences, known request criteria, and offline mock tools were generated and written to `frozen_criteria.json` by `scripts/prepare_corpora_and_criteria.py` before `scripts/evaluate_language_accuracy.py` was first run on the holdout, within a single working session on 2026-11-10.
- **Limitation:** This sequential ordering is a procedure of the local working session and cannot be independently verified from Git history because all files are committed together in a single commit.
- **Deterministic Evaluation:** The evaluation script uses a fixed pseudo-random seed for surrogate allocation so that re-running `scripts/evaluate_language_accuracy.py` produces byte-identical output and leaves Git status clean.

## Reproduction Commands

To regenerate `report.json` and `raw_eval_output.json`:
```bash
uv run python scripts/evaluate_language_accuracy.py
```

To rerun the latency benchmark (100 runs):
```bash
uv run python scripts/benchmark_language_accuracy.py
```

## Holdout Evaluation: Multilingual Verification Results

- **Total Holdout Sentences:** 19 (17 languages + 2 known requests)
- **Corpus Data File:** [`multilingual_corpus.json`](multilingual_corpus.json)
- **Raw Per-Sentence Output:** [`raw_eval_output.json`](raw_eval_output.json)

| Language | Code | Sensitive Protection | Meaning Preservation (Public Words Retained) | Exact Restoration |
| :--- | :---: | :---: | :---: | :---: |
| English | `en` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Korean | `ko` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Spanish | `es` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| French | `fr` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Portuguese | `pt` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| German | `de` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Indonesian | `id` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Turkish | `tr` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Russian | `ru` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Hindi | `hi` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Marathi | `mr` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Bengali | `bn` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Urdu | `ur` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Telugu | `te` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Arabic | `ar` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Chinese | `zh` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| Japanese | `ja` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| **Known: SecureMCP** | `ko` | 1 / 1 (100.0%) | 1 / 1 (100.0%) | 1 / 1 (100.0%) |
| **Known: SKILL.md** | `en` | 1 / 1 (100.0%) | 2 / 2 (100.0%) | 1 / 1 (100.0%) |
| **Total** | **All** | **19 / 19 (100.0%)** | **20 / 20 (100.0%)** | **19 / 19 (100.0%)** |

## Known Request Regressions

1. **`SecureMCP 삭제해줘`:**
   - Result: Masked as `private_symbol_1 삭제해줘`
   - Evaluation: Operator `삭제` and verb ending `해줘` preserved; product/brand identifier `SecureMCP` masked as entity surrogate; restored cleanly to original text.
2. **`Read SKILL.md before using this skill. Follow its instructions.`:**
   - Result: Masked with `Read`, `before using this`, `Follow its instructions` preserved; file token `SKILL.md` and object `skill` handled consistently; roundtrip restoration 100% intact.

## Tool & MCP Verification (Offline Fake Provider)

- **Gateway Tool-Call Round Trip:** PASS (calls to registered tools preserve arguments, aliases are restored before tool execution, and tool outputs re-masked).
- **MCP Tool Definitions & Prompts:** PASS (MCP tool schemas and descriptions preserved without leaking private identifiers).
- **Skill-Instruction Handling:** PASS (skill imperatives and discourse keywords preserved).
- **Real Provider / Host Status:** `미측정` (Live cloud provider verification not available in local test environment).

## Latency Benchmark Results (Committed Script, 100 Runs)

- **Machine Info:** AMD64 Family 25 Model 33 Stepping 0 (24 cores), Windows-11-10.0.26200-SP0, Python 3.14.7
- **Run Count:** 100 iterations (20 warmup runs)

| Metric | Baseline | Candidate Profile | Delta |
| :--- | :---: | :---: | :---: |
| Cold p50 | 0.0150 ms | 0.0162 ms | +0.0012 ms |
| Cold p95 | 0.0245 ms | 0.0250 ms | +0.0005 ms |
| Warm p50 | 0.0077 ms | 0.0090 ms | +0.0013 ms |
| Warm p95 | 0.0129 ms | 0.0133 ms | +0.0004 ms |
| Memory Delta | 미측정 | 미측정 | Heap delta cannot be isolated without external process boundary |

## Decision

- **Offline Multilingual & Tool/MCP/Skill Verification:** `Verified (offline)`.
- **Live Cloud Provider:** `미측정` (Requires live host / external network credentials).
