# Issue #313 Evaluation Evidence: Per-Segment Language Handling (`segment_language`)

- **Candidate Profile:** `segment_language` (`issue=313`)
- **Version:** `2.10.0`
- **Toggle State:** Default `OFF` (byte-identical baseline when off)
- **Status:** Evaluated on holdout / Decision: `hold — comprehension 미측정` (default OFF)

## Status Table

| Acceptance Requirement | Status | Evidence / Notes |
| :--- | :---: | :--- |
| Per-segment language choice | Implemented | Segments split on sentences (`[.!?。！？]\s+`), quotes (`["'“”‘’]`), list items |
| Evidence via `detect_natural_language()` | Implemented | Korean/English character ratio detection per segment |
| Confidence/length floor inheritance | Implemented | Segments under 8 characters inherit parent request language |
| No union of public vocabularies | Verified | Evaluated per segment with its own language lexicon only |
| Whole-text protection run first | Implemented | Sensitive patterns, forced rules, code spans, URLs/emails detected whole-text |
| Segment boundaries do not cut spans | Verified | Boundaries overlapping protected spans are strictly suppressed |
| Supported languages | Documented | Korean (`ko`) and English (`en`) only |
| Byte-identical output when toggle OFF | Verified | `test_toggle_off_byte_identical_mixed_language` passes |
| Protection measurement (exposure & restore) | Measured | Baseline next to candidate reported below |
| Real-LLM comprehension | 미측정 | Unset `SECURE_GATEWAY_LIVE_SUBSCRIPTION`; offline report |
| Latency overhead | Measured | Measured from committed benchmark script (100 runs) |
| Memory delta | 미측정 | Per-request memory delta cannot be isolated deterministically without OS process boundaries |

## Ordering Protocol (How Order was Handled)

- **Execution Order:** Acceptance criteria, boundary patterns, and floor rules were generated and written to `frozen_criteria.json` by `scripts/prepare_corpora_and_criteria.py` before `scripts/evaluate_language_accuracy.py` was first run on the holdout, within a single working session on 2026-11-10.
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

## Holdout Evaluation: Baseline Next to Candidate

- **Total Holdout Sentences:** 8
- **Corpus Data File:** [`holdout_corpus.json`](holdout_corpus.json)
- **Raw Per-Sentence Output:** [`raw_eval_output.json`](raw_eval_output.json)

| Metric | Baseline (Toggle OFF) | Candidate (`segment_language`) | Comparison / Outcome |
| :--- | :---: | :---: | :--- |
| **Sensitive Protection** | 8 / 8 (100.0%) | 8 / 8 (100.0%) | Zero secret leaks in both arms |
| **Boundary Cuts through Protected Spans** | 0 / 8 (0.0%) | 0 / 8 (0.0%) | Boundaries strictly suppressed around code, email, and forced terms |
| **Full Leaks** | 0 / 8 (0.0%) | 0 / 8 (0.0%) | No full exposure |
| **Partial Exposures** | 0 / 8 (0.0%) | 0 / 8 (0.0%) | No partial exposure |
| **Over-masking of Public Spans** | 2 / 8 (25.0%) | 2 / 8 (25.0%) | Public segments preserved across boundaries |
| **Exact Restoration** | 8 / 8 (100.0%) | 8 / 8 (100.0%) | Perfect round-trip restore across all 8 mixed sentences |

## Latency Benchmark Results (Committed Script, 100 Runs)

- **Machine Info:** AMD64 Family 25 Model 33 Stepping 0 (24 cores), Windows-11-10.0.26200-SP0, Python 3.14.7
- **Run Count:** 100 iterations (20 warmup runs)

| Metric | Baseline | Candidate (`segment_language`) | Delta |
| :--- | :---: | :---: | :---: |
| Cold p50 | 0.0225 ms | 0.0242 ms | +0.0017 ms |
| Cold p95 | 0.0381 ms | 0.0390 ms | +0.0009 ms |
| Warm p50 | 0.0116 ms | 0.0119 ms | +0.0003 ms |
| Warm p95 | 0.0159 ms | 0.0128 ms | -0.0031 ms |
| Memory Delta | 미측정 | 미측정 | Heap delta cannot be isolated without external process boundary |

## Decision

- **Decision:** `hold — comprehension 미측정` (Default `OFF`).
- **Reason:** While boundary suppression and multi-segment language routing pass all safety and restoration checks, real-LLM comprehension remains `미측정` due to the lack of a live model subscription. By the fixed rule, adoption is held pending live comprehension verification.
