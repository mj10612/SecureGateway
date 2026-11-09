# Issue #324 holdout-baseline stop: diagnosis and supplemental-grading design

Read-only analysis by worker task_c91607fd0be6, 2026-11-09. No code edits, no LLM calls, no commits.
I read no task, reference or answer text. Run artifacts were opened only through
programmatic metadata checks: counts, sizes, hashes, usage numbers and mtimes. The only
native CLI call was `codex exec --help`.

Run: `docs/evaluations/issue324-2.7.0/holdout-baseline` (freeze schema 2, prepared, `codex-cli 0.167.0`,
adapter `7b7e8fcc…6d0d95e`/full `7b7e8fcca6155688ebb62b87d059d0d40e06b8e8677774f63af8d1f665be7fd9`,
`gpt-6.1-sol`, effort medium, max_output_tokens 2048).
Code at analysis time: `evaluation_reliable.py` 619aa700…, `evaluation_codex_worker.py` 7b7e8fcc…,
`evaluation_worker.py` 3c87e9e5…, `evaluation_reliable_cli.py` 6417f5a1….

## 1. What the evidence establishes

| Fact | Evidence |
| --- | --- |
| Journal: 183 calls = 153 interpret + 30 grade; 182 completed, 1 error; `stopped: true`, stop reason "Worker error or rejected record." | `execution-journal.json` |
| Failed call: `361a76ba34a64a5d9265b8c8a74d7f62`, phase grade, `error: ValueError`, no `usage` key | journal entry index 182 (the final call) |
| Job identity: variant `baseline`, repeat 2, language `ur`, 4 criteria. No other `ur` job had been graded yet. | manifest job metadata |
| Manifest: 153 responses, 29 grades, `errors: []`, `attempts: 0`. There is no `comprehension/rejected-records.json`. | manifest / directory listing |
| Reported usage: 2,861,052 tokens across 182 completed calls. This is a **lower bound**, because one call's usage is unknown. | journal |
| 61 batches with at most 3 in flight; elapsed 886.8 s, about 14.5 s per batch on average | journal |
| The failing call's grade request rebuilt from manifest job + saved response is valid: 6,654 bytes against a 1 MiB limit, with a prompt of 6,939 bytes. Grade requests across all jobs range from 4,271 to 9,613 bytes. | `validate_request(_grade_request(...))`, no model call |
| Completed grade outputs are small: output tokens median 170, max 276 against a 2048 limit; reasoning tokens max 58. No grade exceeded 75% of the budget. Interpret output max was 719. | journal usage |
| The error was recorded 1.44 s after the last successful grade was saved: `first-grades.json`/`manifest.json` mtime 11:41:52.67, journal 11:41:54.11 (+0900) | file mtimes |

**Excluded by evidence:**
- **The runner-side checks** (`_check_provenance`, `_validate_grades`, saving, `continue_comprehension`). All of these run after a result is returned, and any failure there writes `rejected-records.json`. That file does not exist, so `future.result()` itself raised: the ValueError came from inside `run_codex_worker`.
- **`validate_request`** (the rebuilt request is valid) and **a missing `codex`** (other calls in the same batch succeeded).

**Not determinable:**
- **Stage:** the adapter raises plain `ValueError` from about 25 sites, deliberately drops stderr, and keeps no stage. The temp directory is already deleted, and the journal has no per-call start or end timestamps.
- **Timeout:** a 300 s timeout cannot be excluded. The batch start time is not recorded; the 1.44 s gap only bounds when the failure was *processed* relative to the last success.
- **Output size:** low grade-output usage elsewhere makes an output-budget rejection unlikely, but it is not excluded.

Candidate ValueError stages inside `run_codex_worker`, in execution order:

1. `codex --version` capture: start failure, timeout of 10 s, nonzero exit, or an invalid version string.
2. `codex exec` capture (`capture_worker_process`): start failure, more than 1 MiB of combined stdout+stderr, a capture error, **nonzero exit** ("Worker executable failed." — e.g. auth, rate or usage limit, network, server; stdout is discarded on this path), or a **300 s timeout**.
3. `_parse_events`:
   - an invalid JSONL event
   - an **`error`/`turn.failed` event** (provider-side failure)
   - a tool or unknown item type
   - an unsupported event or multiple turns
   - invalid usage
   - no `turn.completed`
4. Final message: missing or unreadable file, more than 1 MiB, or not UTF-8.
5. Grade parsing (`strict_json`): invalid JSON, duplicate keys, or a shape other than `{"grades": …}`.
6. `validate_result`:
   - identity
   - reported `output_tokens` above 2048
   - wrong, duplicate or missing criterion ids, non-boolean `passed`, empty evidence
   - grade JSON above 4 × 2048 bytes

For stages 4–6 the usage *had* already been parsed from `turn.completed` in memory but was
discarded by the exception. For stages 1–3 it is genuinely unknown. Because the stage is unknown,
the call must stay **unknown usage**. Malformed JSON is one possibility among many and must not be
assumed.

`codex exec --help` (0.167.0) offers `--output-schema <FILE>` (JSON Schema for the final response),
`--json` and `-o/--output-last-message`. A schema could reduce malformed-grade risk. However, it
changes the generation conditions relative to the 29 saved first grades and the reference audit,
so it **should not** be introduced into this cohort's supplemental grading. It is a candidate only
for a future, newly frozen cohort with a fresh reference audit.

## 2. Recommended observability (prospective; changes adapter hash)

### 2.1 `src/secure_gateway/evaluation_worker.py`
```python
class WorkerFailure(ValueError):          # subclass: every existing `except ValueError` still works
    stage: str        # 'request_validation'|'cli_version'|'process_start'|'process_exit'|'timeout'|
                      # 'output_limit'|'capture'|'event_parse'|'provider_error_event'|'tool_event'|
                      # 'no_turn'|'final_message'|'grade_json'|'result_validation'
    code: str         # the existing fixed message, never model/stderr text
    usage: dict | None          # set only when a turn.completed usage was parsed
    returncode: int | None
    elapsed_seconds: float | None
    evidence: dict    # bounded, content-free unless explicitly owner-only (below)
```
- `capture_worker_process`:
  - Raise `WorkerFailure` with the stage `timeout`, `process_exit`, `output_limit`, `capture` or `process_start`.
  - On `process_exit`, attach the **stdout bytes** (≤1 MiB, already bounded) to the exception object, but never write them to disk. The adapter can then parse event *types* and usage.
  - Record `elapsed_seconds`.
- `validate_result`: raise `WorkerFailure(stage='result_validation', code=<existing message>)`.

### 2.2 `src/secure_gateway/evaluation_codex_worker.py`
- Wrap each stage. Re-raise as `WorkerFailure`, carrying `usage` whenever `_parse_events` saw `turn.completed`. Parse events best-effort even after a nonzero exit, to recover usage and event-type counts.
- `evidence`, which is bounded and stores no prompt or stderr text:
  - `event_counts` by type
  - stdout and stderr byte lengths and `sha256`
  - `stderr_classes`: allowlisted regex flags only, such as `rate_limit|usage_limit|auth|network|timeout|server_error`
  - `provider_error`: only allowlisted `code`/`type` fields of an error event, if present; never `message`
- **Bounded rejected-record proof** for stages 4–6, where the model produced something:
  - `final_sha256` and `final_bytes`
  - `final_excerpt`: the first ≤16 KiB, owner-only. Synthetic holdout answers are owner artifacts, and grade JSON contains evidence text, so mark it as owner-only and never print it in summaries.
  - For `grade_json`/`result_validation`, the parsed `grades` object when it is valid JSON.
- No change to `_prompt()`, argv, environment allowlist, validation thresholds, timeout values or result shape on success.

### 2.3 `src/secure_gateway/evaluation_reliable.py` (runner)
- **Each journal call** gains `started_at_unix`, `finished_at_unix`, and, on failure, `stage`, `code`, `returncode` and `elapsed_seconds`.
  - It records `usage` when `WorkerFailure.usage` is known; that usage counts toward `reported_tokens`.
  - It records `usage_unknown: true` otherwise.
  - Policy is unchanged: any error still stops the run, and unknown usage still stops it with no automatic retry.
- **`rejected-records.json`** also receives a proof entry when `run_codex_worker` raised `WorkerFailure` with a final-message proof (`record=None`, `failure=evidence`).
- **`_execution_summary`** adds failure counts by stage, `known_failure_usage_tokens` and `unknown_usage_calls`. It also notes that totals are a lower bound whenever `unknown_usage_calls > 0`.

### 2.4 Adapter provenance (hash will change from `7b7e8fcc…`)
The stopped run and the reference audit are frozen under H1 = `7b7e8fcc…`. Do **not** retrofit
either. Instead:

1. **Before editing the adapter, record golden digests** under H1 in a new test. Use fixed synthetic interpret and grade requests and capture:
   - the `_prompt(request)` bytes
   - the exact `codex exec` argv, captured via a monkeypatched `capture_worker_process`
   - the success-path result shape and metadata keys (excluding `adapter_source_sha256`)
2. **After the change (H2), the same test must pass.** This is mock evidence that the generation
   conditions are unchanged; it is not proof of identical service behaviour.
3. **New freezes store an explicit `adapter_equivalence` record:**
   `{previous: H1, current: H2, scope: 'failure observability only', golden_test: <path>, golden_sha256: …}`.
4. **`verify_reference_audit` stays strict by default.** It accepts an audit adapter different from
   the current one only when the caller passes that frozen equivalence record. The resulting
   verification lists both hashes; nothing is silently accepted.
5. **Existing frozen evidence** keeps H1. Supplemental records are labelled H2, and reports show
   mixed adapters per grade source.

## 3. Prospectively frozen supplemental grading stage

Goal: finish the missing 124 grades (153 − 29), and the one failed attempt only if explicitly
authorised. The parent run stays exactly as it is: it remains `stopped`/`incomplete`, and its
journal, manifest, first-responses and first-grades are never written to.

### 3.1 Files and interfaces (`evaluation_reliable.py`)
```python
def prepare_supplemental_grading(run_dir, *, reason: str, reattempt_job_ids: tuple[str, ...] = (),
                                 supplement_id: str | None = None) -> dict
def execute_supplemental_grading(run_dir, supplement_id, *, execute: bool = False, max_calls: int,
                                 max_seconds: float, max_tokens: int, workers: int = 1) -> dict
def supplemented_report(run_dir, supplement_id) -> dict
```
Layout: `<run>/supplements/<supplement_id>/{freeze.json, journal.json, grades.json, rejected-records.json, report.json, summary.md}`

**`freeze.json`** is written last as `prepared: true` before any call. It contains:
- **Parent identity:**
  - `parent_freeze_sha256`, `parent_journal_sha256`, `parent_manifest_sha256`, `parent_jobs_sha256`
  - `first_responses_sha256`, `first_grades_sha256`
  - `parent_stop_reason`, `parent_reported_tokens_lower_bound` (2,861,052)
- **`parent_failed_calls`**: `[{job_id, phase, error, usage_unknown: true, journal_index}]`, transparently recorded.
- **Pending work:**
  - `pending_job_ids`: graded neither in the parent nor among the failed calls, by default 123.
  - `reattempt_job_ids`: an explicit subset of failed calls, e.g. `361a76ba…`. Each must carry an explicit `reason`. Otherwise that job remains ungraded and the cohort stays incomplete.
  - `grade_request_digests`: `{job_id: digest(_grade_request(job, saved_response))}`, so requests are rebuilt deterministically from frozen first answers and never from new interpretations.
- **Configuration:**
  - `model`, `reasoning_effort`, `max_output_tokens`
  - `cli_version`, which must equal the parent's or preparation refuses
  - `grading_policy_sha256`, which must equal the parent's
  - `adapter_source_sha256` (H2), `parent_adapter_sha256` (H1) and the `adapter_equivalence` record
- **Budget:** the execution budget is part of the freeze and immutable, e.g. calls 124, tokens 2.6 M (124 × ~16.5 k observed grade total ≈ 2.05 M plus margin), 3600 s, ≤3 workers.
- **Holdout ledger:** append an entry with kind `baseline_supplement` that references the parent `use_id`. This records that the holdout was touched again; it is **not** a new candidate use.

**Execution:**
- Grade phase only.
- Before execution, verify:
  - all parent hashes
  - each request digest
  - the parent journal is still `stopped`
  - native CLI equals the frozen value
  - the adapter is H2
- It has its own journal, `grades.json` and rejected records. It never imports or writes the parent manifest.
- The same rules apply as for the primary run: reserve before launch, a `running` entry on resume stops, unknown usage stops, budgets are immutable, `execute=True` is required, and nothing is retried automatically.

**Report:**
- `original_run: {status: 'incomplete', stopped: true, reason, unknown_usage_calls: 1}` is unchanged.
- `supplement: {status, calls, reported_tokens, unknown_usage_calls, by_stage}`.
- `combined`:
  - `grade_sources: {first: 29, supplemental: N, missing: M}`
  - `status: 'completed_with_supplement' | 'incomplete'`
  - `reported_tokens_lower_bound`
  - `adapters: {H1: 29 + 153 interpret, H2: N}`
  - time span of both stages
- `repeated_statistics` over merged rows, with each row tagged `grade_stage: first|supplemental`.
- The combined result never reports `completed` for the original run. A baseline is never adoption-eligible.

### 3.2 `src/secure_gateway/evaluation_reliable_cli.py` (coordinator-owned)
`evaluate reliable supplement-grades prepare --run-dir --reason [--reattempt-job ID --reattempt-reason TEXT]... --max-calls --max-seconds --max-tokens --workers`
`evaluate reliable supplement-grades run --run-dir --supplement-id --execute`
`evaluate reliable supplement-grades report --run-dir --supplement-id`

### 3.3 Protocol amendment, before execution
Add a rule to `docs/evaluations/ISSUE324_PROTOCOL.md`. Supplemental grading:
- may complete missing grades of saved first answers, with an explicit new budget
- never repeats interpretations or replaces first grades
- reattempts an unknown-usage failed call only by named, reasoned authorisation, never automatically
- records the attempt as supplemental, not first
- leaves the original run's status unchanged

## 4. Minimal regression proof (all mock, no native inference)

**1. `tests/test_codex_worker_failures.py`** (new):
- **H1 golden:** prompt and argv digests; success result shape.
- **Stage capture**, simulated with a monkeypatched `capture_worker_process`:
  - nonzero exit whose stdout holds `turn.completed` usage → `WorkerFailure(stage='process_exit', usage=…)`
  - timeout → `stage='timeout'`, `usage=None`
  - `turn.failed` event → `provider_error_event`, with no message text stored
  - invalid grade JSON after `turn.completed` → `grade_json`, usage known, proof `final_sha256`/`final_bytes`/bounded excerpt ≤16 KiB
  - output tokens > 2048 → `result_validation` with usage
- **Content hygiene:** stderr is never in exception `str()` or evidence; only sha256/length/classes are kept.
- **Compatibility:** `isinstance(err, ValueError)` remains true.

**2. `tests/test_reliable_evaluation_guards.py`** (extend):
- A `WorkerFailure` with known usage → journal stage/usage counted, `usage_unknown` false, run still stopped, proof in rejected records.
- Without usage → `usage_unknown` true.
- Journal entries carry start/finish timestamps.

**3. `tests/test_reliable_supplement.py`** (new):
- **Setup:** a mock stopped run with 153 interpret, 29 grades and 1 failed unknown-usage grade, built with mocks like `prepared_run`.
- **Preparation:**
  - refuses without `reason`
  - refuses if any parent artifact hash changed or the parent journal is not stopped
  - default pending is 123; the failed job is included only through explicit `reattempt_job_ids` with a reason
- **Execution:**
  - the worker sees only grade requests, whose digests equal the frozen ones
  - parent journal, manifest, first-responses and first-grades bytes are identical after execution
  - resume, running-entry stop, unknown-usage stop and immutable budget behave as in the primary run
- **Report:**
  - shows the original as incomplete/stopped with `unknown_usage_calls: 1`
  - shows `grade_sources` of 29/123(+1)
  - has a lower-bound token note
  - lists mixed adapters
- **Audit check:** `verify_reference_audit` rejects H1-vs-H2 without the equivalence record and accepts it with the record, listing both hashes.

**4. Full root suite**, plus ruff and mypy.

## 5. Unavoidable limitations

- **Cause:** the root cause and token usage of call `361a76ba…` are permanently unknowable: there is no stage, no stderr, the temp directory is gone, and there are no per-call timestamps. All token totals for this run are lower bounds.
- **Reattempt:** a reattempted grade is a new stochastic sample taken later in time. It cannot be called a first grade, and service-side drift between the stages cannot be excluded.
- **Adapter equivalence:** this rests on golden tests of prompt, argv and validation (mock evidence). Behaviour of the provider or CLI is not proven identical.
- **Usage after the change:** usage will still be unknown for process-exit, timeout and provider-error failures without a `turn.completed` event, so those still stop the run under the existing policy.
- **Excerpts:** the owner-only excerpt contains model output for rejected grades or answers. It must stay out of summaries and shared reports.
- **`--output-schema`:** it is available, but using it would change grading conditions for this cohort, so it is excluded here.
