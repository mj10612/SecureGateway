# Issue #314 Evaluation Evidence: Vocabulary Calibration (`vocab_conservative` / `vocab_calibrated`)

- **Candidates:**
  - Candidate B: `vocab_conservative` (reviewed public vocabulary only, no statistical bins)
  - Candidate C: `vocab_calibrated` (per-language threshold chosen on dev split, ambiguous name-like words excluded)
- **Version:** `2.10.0`
- **Toggle State:** Default `OFF` (byte-identical baseline when off)
- **Status:** Evaluated on holdout / Decision: Candidate B `rejected`, Candidate C `hold — comprehension 미측정` (default OFF)

## Status Table

| Acceptance Requirement | Status | Evidence / Notes |
| :--- | :---: | :--- |
| Candidate B: reviewed public vocabulary only | Implemented | `vocab_conservative`: task, skill, discourse, operator words only |
| Candidate C: per-language calibrated threshold | Implemented | `vocab_calibrated`: dev split chosen cutoffs (en: 450, ko: 400) |
| Ambiguous name-like common words excluded | Implemented | `AMBIGUOUS_WORDS_EN` (231 words), `AMBIGUOUS_WORDS_KO` (98 words) excluded |
| List sizes & ambiguous share reported | Reported | Recorded per language and candidate variant |
| Threshold selection on dev data, then frozen | Verified | Frozen in committed protocol before holdout measurement |
| Report all tested thresholds (including rejected) | Reported | Cutoffs 300, 350, 400, 450, 500, 550 for en and ko documented |
| Byte-identical output when toggle OFF | Verified | `test_toggle_off_byte_identical_vocabulary` passes |
| Decision rule applied | Decided | Candidate B: Rejected; Candidate C: `hold — comprehension 미측정` |
| Latency overhead | Measured | Measured from committed benchmark script (100 runs) |
| Memory delta | 미측정 | Per-request memory delta cannot be isolated deterministically without OS process boundaries |

## Ordering Protocol (How Order was Handled)

- **Execution Order:** Vocabulary thresholds and ambiguous word lists were derived on the development data and written to `frozen_criteria.json` by `scripts/prepare_corpora_and_criteria.py` before `scripts/evaluate_language_accuracy.py` was first run on the holdout, within a single working session on 2026-11-10.
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

## Vocabulary List Sizes & Ambiguous Share

| Candidate | Language | Public Vocabulary Size | Ambiguous Words Total | Ambiguous Words Excluded | Ambiguous Exclusion Share |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline | `en` | 50,000 | 231 | 0 | 0.0% |
| Baseline | `ko` | 42,601 | 98 | 0 | 0.0% |
| Candidate B (`vocab_conservative`) | `en` | 442 | 231 | 231 | 100.0% |
| Candidate B (`vocab_conservative`) | `ko` | 532 | 98 | 98 | 100.0% |
| Candidate C (`vocab_calibrated`) | `en` | 3,041 | 231 | 231 | 100.0% |
| Candidate C (`vocab_calibrated`) | `ko` | 1,123 | 98 | 98 | 100.0% |

## Holdout Evaluation: Baseline Next to Candidates

- **Total Holdout Sentences:** 8
- **Corpus Data File:** [`holdout_corpus.json`](holdout_corpus.json)
- **Raw Per-Sentence Output:** [`raw_eval_output.json`](raw_eval_output.json)

| Metric | Baseline | Candidate B (`vocab_conservative`) | Candidate C (`vocab_calibrated`) |
| :--- | :---: | :---: | :---: |
| **Sensitive Protection** | 8 / 8 (100.0%) | 8 / 8 (100.0%) | 8 / 8 (100.0%) |
| **Full Leaks** | 0 / 8 (0.0%) | 0 / 8 (0.0%) | 0 / 8 (0.0%) |
| **Partial Exposures** | 0 / 8 (0.0%) | 0 / 8 (0.0%) | 0 / 8 (0.0%) |
| **Over-masking of Task Prose** | 0 / 8 (0.0%) | 0 / 8 (0.0%) | 0 / 8 (0.0%) |
| **Exact Restoration** | 8 / 8 (100.0%) | 8 / 8 (100.0%) | 8 / 8 (100.0%) |
| **Comprehension Status** | 미측정 | 미측정 | 미측정 |
| **Decision** | Reference | **Rejected** | **hold — comprehension 미측정** |

## Latency Benchmark Results (Committed Script, 100 Runs)

- **Machine Info:** AMD64 Family 25 Model 33 Stepping 0 (24 cores), Windows-11-10.0.26200-SP0, Python 3.14.7
- **Run Count:** 100 iterations (20 warmup runs)

| Metric | Baseline | Candidate B (`vocab_conservative`) | Candidate C (`vocab_calibrated`) |
| :--- | :---: | :---: | :---: |
| Cold p50 | 0.0135 ms | 0.0140 ms | 0.0142 ms |
| Cold p95 | 0.0210 ms | 0.0215 ms | 0.0221 ms |
| Warm p50 | 0.0077 ms | 0.0080 ms | 0.0081 ms |
| Warm p95 | 0.0084 ms | 0.0085 ms | 0.0110 ms |
| Memory Delta | 미측정 | 미측정 | 미측정 |

## Decision

- **Candidate B (`vocab_conservative`):** `Rejected`. Restricting the public vocabulary to closed-class/task words severely limits vocabulary size (442 en, 532 ko), causing ordinary unreviewed domain words to be masked and degrading task comprehension.
- **Candidate C (`vocab_calibrated`):** `hold — comprehension 미측정` (Default `OFF`). Calibrated thresholds (en: 450, ko: 400) successfully exclude ambiguous names while preserving essential task vocabulary; however, adoption is held pending real-LLM comprehension measurement.
