# Issue #309 Evaluation Evidence: Korean Conjugation Split (`ko_conjugation_split`)

- **Candidate Profile:** `ko_conjugation_split` (`issue=309`)
- **Version:** `2.10.0`
- **Toggle State:** Default `OFF` (byte-identical baseline when off)
- **Status:** Evaluated on holdout / Decision: `hold — comprehension 미측정` (default OFF)

## Status Table

| Acceptance Requirement | Status | Evidence / Notes |
| :--- | :---: | :--- |
| Rule-based bounded ending table | Implemented | `-면/-으면`, `-기 전에/-ㄴ 뒤에`, `-지 말고/-지 마`, `-세요/-해줘`, `-ㄴ/-은/-된` in `grammar_ko.py` |
| Stem judged by existing policy | Implemented | Sensitive/named stems masked; ordinary stems preserved |
| Grammatical ending kept public | Implemented | Endings retained outside masked surrogate |
| No morphological analyser dependency | Verified | Zero extra packages, pure python rule/coda decomposition |
| Fallback to legacy behaviour on uncertainty | Implemented | Unrecognized stems/coda mismatches fall back to legacy tokenization |
| Forced rule / dictionary / mapping stems | Implemented | Stem masked as surrogate, ending preserved publicly |
| Unseen holdout evaluation | Verified | Evaluated on unseen stems, endings, and spacing |
| Byte-identical output when toggle OFF | Verified | `test_toggle_off_byte_identical_korean_conjugation` passes |
| Protection measurement (exposure & restore) | Measured | Baseline next to candidate reported below |
| Real-LLM comprehension | 미측정 | Unset `SECURE_GATEWAY_LIVE_SUBSCRIPTION`; offline report |
| Latency overhead | Measured | Measured from committed benchmark script (100 runs) |
| Memory delta | 미측정 | Per-request memory delta cannot be isolated deterministically without OS process boundaries |

## Ordering Protocol (How Order was Handled)

- **Execution Order:** Acceptance criteria and ending definitions were generated and written to `frozen_criteria.json` by `scripts/prepare_corpora_and_criteria.py` before `scripts/evaluate_language_accuracy.py` was first run on the holdout, within a single working session on 2026-11-10.
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

- **Total Holdout Sentences:** 16
- **Corpus Data File:** [`holdout_corpus.json`](holdout_corpus.json)
- **Raw Per-Sentence Output:** [`raw_eval_output.json`](raw_eval_output.json)

| Metric | Baseline (Toggle OFF) | Candidate (`ko_conjugation_split`) | Comparison / Outcome |
| :--- | :---: | :---: | :--- |
| **Sensitive Protection** | 16 / 16 (100.0%) | 16 / 16 (100.0%) | Zero secret leaks in both arms |
| **Full Leaks** | 0 / 16 (0.0%) | 0 / 16 (0.0%) | No full exposure |
| **Partial Exposures** | 0 / 16 (0.0%) | 0 / 16 (0.0%) | No partial exposure |
| **Over-masking of Endings** | **13 / 16 (81.2%)** | **1 / 16 (6.2%)** | **Substantial reduction:** candidate keeps grammatical endings public |
| **Exact Restoration** | 16 / 16 (100.0%) | 16 / 16 (100.0%) | Perfect bijective restore across all 16 sentences |

## Latency Benchmark Results (Committed Script, 100 Runs)

- **Machine Info:** AMD64 Family 25 Model 33 Stepping 0 (24 cores), Windows-11-10.0.26200-SP0, Python 3.14.7
- **Run Count:** 100 iterations (20 warmup runs)

| Metric | Baseline | Candidate (`ko_conjugation_split`) | Delta |
| :--- | :---: | :---: | :---: |
| Cold p50 | 0.0094 ms | 0.0102 ms | +0.0008 ms |
| Cold p95 | 0.0142 ms | 0.0146 ms | +0.0004 ms |
| Warm p50 | 0.0053 ms | 0.0054 ms | +0.0001 ms |
| Warm p95 | 0.0059 ms | 0.0060 ms | +0.0001 ms |
| Memory Delta | 미측정 | 미측정 | Heap delta cannot be isolated without external process boundary |

## Decision

- **Decision:** `hold — comprehension 미측정` (Default `OFF`).
- **Reason:** In accordance with the experiment protocol, candidates without measured real-LLM comprehension cannot be marked `adopt-candidate`. Because `SECURE_GATEWAY_LIVE_SUBSCRIPTION` is unset in this environment, comprehension is reported honestly as `미측정`. The toggle remains default `OFF`.
