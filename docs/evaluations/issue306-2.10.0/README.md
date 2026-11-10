# Issue #306 Evaluation Evidence: Accuracy Metrics & Umbrella Measurements

- **Scope:** Sections 3 & 5 (Gold span metrics, breakdowns, restore/alias integrity, dev/regression/holdout split)
- **Version:** `2.10.0`
- **Related Issues:** Umbrella for #309, #310, #314; references `exp/310-311-316-318-names-policy` for Section 1 name-context detection.
- **Status:** Delivered Sections 3 & 5 / Decision: `hold — comprehension 미측정`

## Status Table

| Acceptance Requirement | Status | Evidence / Notes |
| :--- | :---: | :--- |
| Character-offset gold spans | Implemented | Exact char spans for FN, FP, partial, leak annotations |
| Separate FN / FP / partial / leak counts | Reported | Independent non-merged metric reporting |
| Denominators per language / domain / target | Reported | Broken down across `ko`/`en`, `tech`/`general`, and target types |
| Restore / alias / protocol integrity | Reported | Evaluated as a separate independent metric |
| Dev vs regression vs new-holdout split | Implemented | 4 issue reproductions kept as dedicated regression cases |
| Issue #306 4 reproduction cases | Passing | `test_issue306_four_reproductions_with_forced_rules` passes |
| Real-LLM comparison (Section 4) | Stated | Honestly reported with `미측정` status |
| Name-context detection (Section 1) | Referenced | Implemented on `exp/310-311-316-318-names-policy` (not duplicated here) |
| Latency overhead | Measured | Measured from committed benchmark script (100 runs) |
| Memory delta | 미측정 | Per-request memory delta cannot be isolated deterministically without OS process boundaries |

## Ordering Protocol (How Order was Handled)

- **Execution Order:** Section 3 gold span definitions and metric breakdown dimensions were generated and written to `frozen_criteria.json` by `scripts/prepare_corpora_and_criteria.py` before `scripts/evaluate_language_accuracy.py` was first run on the holdout, within a single working session on 2026-11-10.
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

## Regression Suite (The 4 Issue Reproductions)

| Reproduction Case | Description | Result |
| :--- | :--- | :---: |
| **Repro 1** | Korean verb inflection over-masking: `분석하고 ... 검토해줘` | **PASS** (inflected stems masked, endings preserved) |
| **Repro 2** | Latin identifier with Korean particle: `EmberQzx면 ... EmberQzx해줘` | **PASS** (`EmberQzx` masked as entity surrogate, `면`/`해줘` kept) |
| **Repro 3** | Mixed-language segment boundary: Korean instructions with English code fragment | **PASS** (segment boundaries respect code & literal spans) |
| **Repro 4** | Ambiguous name homonym in Korean screening: `구름` / `바다` in name position | **PASS** (ambiguous common names masked under calibrated profile) |

## Holdout Evaluation: Baseline Next to Candidate

- **Total Holdout Sentences:** 8
- **Corpus Data File:** [`holdout_corpus.json`](holdout_corpus.json)
- **Raw Per-Sentence Output:** [`raw_eval_output.json`](raw_eval_output.json)

| Metric | Baseline | Candidate Profile | Comparison / Outcome |
| :--- | :---: | :---: | :--- |
| **Sensitive Protection** | 7 / 8 (87.5%) | 7 / 8 (87.5%) | 7 entities protected without forced rules; unforced ports require domain rule |
| **Full Leaks** | 1 / 8 (12.5%) | 1 / 8 (12.5%) | Port number without forced rule handled by domain policy |
| **Partial Exposures** | 0 / 8 (0.0%) | 0 / 8 (0.0%) | Zero partial exposure |
| **Over-masking of Public Spans** | 0 / 8 (0.0%) | 0 / 8 (0.0%) | Task words preserved |
| **Exact Restoration** | 8 / 8 (100.0%) | 8 / 8 (100.0%) | Perfect bijective restoration |

### Protocol & Restore Integrity (Reported as Separate Metric)

| Metric | Measured | Target |
| :--- | :---: | :---: |
| Exact Echoed-String Round-Trip Restoration | 8 / 8 (100.0%) | 100.0% |
| Alias Replay Stability | 8 / 8 (100.0%) | 100.0% |
| Protocol / Schema Preservation | 8 / 8 (100.0%) | 100.0% |

## Latency Benchmark Results (Committed Script, 100 Runs)

- **Machine Info:** AMD64 Family 25 Model 33 Stepping 0 (24 cores), Windows-11-10.0.26200-SP0, Python 3.14.7
- **Run Count:** 100 iterations (20 warmup runs)

| Metric | Baseline | Candidate Profile | Delta |
| :--- | :---: | :---: | :---: |
| Cold p50 | 0.0118 ms | 0.0120 ms | +0.0002 ms |
| Cold p95 | 0.0182 ms | 0.0185 ms | +0.0003 ms |
| Warm p50 | 0.0062 ms | 0.0062 ms | +0.0000 ms |
| Warm p95 | 0.0069 ms | 0.0070 ms | +0.0001 ms |
| Memory Delta | 미측정 | 미측정 | Heap delta cannot be isolated without external process boundary |

## Decision

- **Sections 3 & 5:** `Delivered` (Character-offset gold spans, breakdown metrics, and separated integrity reporting implemented).
- **Comprehension:** `hold — comprehension 미측정` (Live LLM evaluation unset; synthetic proxy prohibited).
