# Issue #324 evaluator review: uncommitted root changes

Reviewer: dispatched worker task_fd5ae6c99279 (read-only). Date: 2026-11-09.
Root: `D:/Source/Temp/Think/SecureMCP`, base commit `a3f37d4` plus uncommitted changes.
Acceptance reference: `docs/evaluations/ISSUE324_PROTOCOL.md`.

**Boundaries kept:** no edits in root, no corpus, reference or model-answer content
read, no LLM evaluation launched. `docs/evaluations/issue324-2.7.0/` and
`issue324-data/` were listed by filename only. A filename-only grep found no
`grading_alias_bindings` key under `docs/`.

## Reviewed files (sha256 at review time)

| File | sha256 |
| --- | --- |
| src/secure_gateway/evaluation_reliable.py | 2167ea2a6933e4974094f42076a9aac20d1f82eae3a650e98ac04c28f321a859 |
| src/secure_gateway/evaluation_reliable_cli.py | be1f9b6ee026516a1ce4b27c823475d2206df48e856ff7cd19de33ac633eb1d6 |
| src/secure_gateway/evaluation.py | 7d0f8fd5699bf7d9a10b7af9344295e909b984f4e88bf95fef1535919c684d0d |
| src/secure_gateway/evaluation_comprehension.py | d13eff55ca322d652aad88c200a9012fc0e20f3c5a3738d5ed618cf9be8d5a81 |
| src/secure_gateway/evaluation_codex_worker.py | 7b7e8fcca6155688ebb62b87d059d0d40e06b8e8677774f63af8d1f665be7fd9 |
| src/secure_gateway/evaluation_worker.py | 3c87e9e5a8b8010b7cd60ea4de7bfa55af4c9f0358b1040947c056cff54b94ed |
| tests/test_reliable_evaluation.py | 668c96d6fa1a1ee24266b8aa4ca96ce58db6b33310a34c12f4f02586f6ef2b4b |
| docs/evaluations/ISSUE324_PROTOCOL.md | fd742b7b0c1ef8835be4e4f1056e141586f9fac54a4b2065ff6cef3807ce9542 |

## Evidence class

All test evidence below is **unit/mock evidence**. I ran the following test files
from the root with `-B -p no:cacheprovider`, and `git status` was unchanged
afterwards:

- `tests/test_reliable_evaluation.py`
- `test_evaluation_statistics.py`
- `test_evaluation_comprehension.py`
- `test_evaluation_worker.py`
- `test_evaluation.py`

Result: 104 passed, 2 skipped.

The reliable-runner tests monkeypatch `run_codex_worker` with `fake_worker` (fixed
`total_tokens: 3`, all criteria passed). They prove phase ordering and budget
bookkeeping only; they are not model or grading evidence. The privacy tests use real
loopback capture but synthetic data. No finding below is confirmed by an actual
provider call.

## Findings, most severe first

### F1 — HIGH (validity): original/human arms receive the gateway's masked-context system prompt
`evaluation_comprehension.py:74-83`. The behavior predates this change set, but the
new `reliable` path depends on it. For every variant, `system` comes from
`records[variant == 'candidate'][id]['outbound']`. For `original` and `human` that is
the baseline **masked outbound** payload. The gateway injects `PRIVACY_INSTRUCTION`
into `instructions` or `system` (`gateway.py:1632-1647`): "This context was masked
locally. Names beginning private_symbol_ … are opaque references…".

As a result, the original arm is told its unmasked text was masked, and any private
text in a corpus system prompt reaches it masked while the user text is unmasked.
Protocol: "The interpreter receives only actual visible messages and the fixed
task-response instruction". Original-arm and human-arm scores are therefore not
measured on the actual visible request, and the original-minus-masked difference is
confounded.

The current fixtures do not catch this: unit tests use `report()` outbound equal to
the source payload, so no instruction is injected.

*Minimal fix:*
- Take `system` from `case['payload']` for `original`.
- For `human`, use the same original system prompt, or a fixed neutral one, as documented.
- Keep the outbound system prompt for `baseline`/`candidate`.
- Add a test with a real `run_privacy` capture asserting that the original-arm
  messages contain no `PRIVACY_INSTRUCTION`.

If the coordinator deliberately wants a shared instruction across arms, the protocol
must state it and the instruction must not falsely claim masking for the original arm.

### F2 — MEDIUM (reproducibility/freeze): native CLI version is not pinned or checked
`evaluation_reliable.py:101-110, 185-206`. The protocol requires pinning "native CLI
version … before calls". `freeze.json` stores only model, effort, budget and the
adapter hash. `run_codex_worker` records `cli_version` per call
(`evaluation_codex_worker.py:117-122, 151`), but nothing compares it with a frozen
value or checks that one cohort used one version. A CLI upgrade in the middle of a
run (or between baseline and candidate runs) goes unnoticed.

*Minimal fix:*
- In `prepare_reliable`, run `codex --version` once (no model call) and store `cli_version` in `frozen`.
- In `execute_reliable`, re-check it before starting.
- Reject any result whose `metadata.cli_version` or `metadata.adapter_source_sha256` differs from the freeze.
- In `joint_report`, report the set of observed versions.
- Include `cli_version` in the baseline-dir key comparison at line 124.

### F3 — MEDIUM (frozen cohort integrity): freeze checks can be bypassed by omitting keys; baseline/audit inputs are not hash-pinned
- `evaluation_reliable.py:199, 201, 205` uses
  `frozen.get('grading_policy_sha256', grading_policy_hash())`,
  `if 'corpus_byte_hashes' in frozen`, and `if 'jobs_sha256' in frozen`. A freeze
  missing these keys skips the check. This happens for real if `prepare_reliable`
  stops between the first `write_json(freeze)` (line 110) and the second (line 137),
  because the manifest exists while `jobs_sha256` does not. The unit fixture
  `prepared_small_run` depends on this leniency.
- `baseline_dir` (lines 121-131): the new freeze stores only `baseline_root` as a
  path. It does not store the sha256 of the previous `freeze.json`,
  `task-capture/report.json` or `privacy/report.json`, although the latter two supply
  the baseline outbound payloads and the privacy comparison.
- `reference_audit_dir` (lines 83-92): `report.json` is trusted as written. Its
  `first-grades.json`, `requests.json` and journal are not re-verified or hashed, and
  the audit's `adapter_source_sha256` is not compared with the run's.

*Minimal fix:*
- Make `grading_policy_sha256`, `corpus_byte_hashes` and `jobs_sha256` mandatory, and fail closed when any is missing.
- Write the final freeze atomically after `prepare_comprehension`, or write a `prepared: true` marker last.
- Store sha256 values of the baseline freeze, reports, and audit report/first-grades/requests in `frozen`, and re-check them in `execute_reliable` and `joint_report`.
- Recompute the audit totals from `first-grades.json` instead of trusting `report.json`.
- Update the test fixture to write a complete freeze.

### F4 — MEDIUM (holdout discipline): holdout reuse is not recorded
The protocol says a holdout becomes regression material once inspected or used for
tuning, and that only holdout metrics may support adoption. However:

- `prepare_reliable` can run the holdout split any number of times, with any candidate.
- `review_eligible` (lines 166-170) has no record of earlier holdout runs or inspections.

Repeated candidate attempts against the same holdout would each report
`review_eligible: True`.

*Minimal fix:*
- Keep an append-only holdout ledger, for example `holdout-uses.json` next to the
  data bundle, or require an explicit `--holdout-use-id`. Record each prepared
  candidate's code SHA and timestamp in it.
- Expose `prior_holdout_uses` in `adoption` and set `review_eligible = False` when it
  is greater than 0, unless the ledger entry is the one pre-registered for this
  candidate.

### F5 — MEDIUM (grading audit validity): grader receives the owner reference response
`evaluation_comprehension.py:88, 160-166`. Under policy v2 the grader receives
`owner_grading_context` containing `reference_response`, `rubric_notes`,
`missing_original_facts` and, for masked arms, `alias_bindings`. The policy text says
the reference "illustrates attainable full credit, not the only valid answer". Even
so, exposing a model answer to the grader invites grading by similarity to that
answer. The protocol line ("independent fresh grader sees the original/rubric/saved
answer") does not list the reference. The interpreter never receives it; the unit
test `test_preparation_freezes_153_blind_jobs_without_gold_or_reference` confirms
this, with mock data.

*Minimal fix:* either remove `reference_response` from the grader context (it is
already used separately in the reference audit), or record it explicitly in the
protocol and the frozen policy hash as an intended grader input. In both cases,
report this choice in `freeze.json`.

### F6 — LOW/MEDIUM (budget accounting): budgets can be overshot
`evaluation_reliable.py:229-240`, `evaluation_codex_worker.py:136`.

- The token and time checks run only before each batch. With `workers=3`, up to
  three calls start with no reservation of tokens or time.
- Each child has a fixed `timeout=300`, independent of the remaining `max_seconds`
  or `deadline_unix`. Actual wall time can exceed the budget by about 300 s, and
  tokens by about 3 × (input + 4 × `max_output_tokens`).

Failures still stop the run correctly: errors and unknown usage set `stopped` and are
never counted as passes.

*Minimal fix:*
- Pass `min(300, remaining_seconds)` as the worker timeout. This needs a request
  field or a wrapper parameter.
- Reserve a per-call worst-case token estimate before submitting a batch.
- Document the remaining overshoot bound in `report.json`.

### F7 — LOW (first-answer preservation): rejected first answers are discarded
`evaluation_reliable.py:244-268`. If `_validate_response` or `_validate_grades`
rejects a completed worker result (tool event, over-budget output, malformed grades),
the record is neither saved nor hashed. Only `status: error` and the exception name
are journaled. The run stops, so no silent retry happens. Still, the protocol's "do
not replace a first answer" is only enforced by `journal.stopped`. Deleting
`execution-journal.json` re-enables a retry with no evidence of the earlier attempt.

*Minimal fix:*
- Append rejected results, or at least their `digest` and `job_id`, to `rejected-first-records.json`.
- Store the journal's sha256 or a call counter in `freeze.json`'s sibling `execution-state`, so that a missing journal with existing first-responses fails closed.

### F8 — LOW (reference audit status): audit can never reach `passed` if the last call lacks usage
`evaluation_reliable.py:343-352`. A completed audit whose final call reports no
`total_tokens` sets `stopped`. Then `complete = ... and not journal['stopped']` gives
`incomplete` even with all 17 references graded, and a new audit directory is
required.

`requests.json` is also not hash-pinned in the audit `freeze.json`. Editing it, for
example to change the criteria, passes the immutability check at lines 308-310
because only the corpus hashes are compared.

*Minimal fix:*
- Separate `usage_unknown` from `complete`: the audit is complete if every request is graded, and unknown usage is reported as a budget-accounting caveat.
- Store `requests_sha256` in the audit freeze and verify it on resume.

### F9 — LOW (privacy at rest): alias→original bindings persisted in every capture report
`evaluation.py:335` stores `grading_alias_bindings` (the full session reverse map) in
each case of `privacy/report.json` and `task-capture/report.json`. Reports already
contain `restored_echo`, so originals were present before. However, the bindings add
every private value as an explicit map. On Windows, `write_json` applies no 0600
mode. These reports feed `compare_reports` and summaries, and could be copied into
`docs/evaluations`. The grep found no such key under `docs/` at review time.

*Minimal fix:* keep bindings only in the comprehension job `grading_context` (owner
side), or in a separate owner-only file. Remove them from shared capture reports, or
mark the reports owner-only in `summary.md`.

### F10 — LOW (review gate breadth): point-estimate gain gates `review_eligible`
`evaluation_reliable.py:158-170`.

- `gain` is `mean(passed_criteria_diff) > 0`. It ignores per-criterion regressions
  (`paired['regressed']`), especially `prohibition` and `conditions`, and ignores
  the original-arm ceiling.
- The `decision: None` behavior and the note text are correct.

*Minimal fix:* add `regressed_by_criterion` counts and a hard-failure regression flag
(any prohibition regression on holdout) to `adoption`, and require it to be empty for
`review_eligible`.

### F11 — INFO (reproducibility): preparation randomness
`prepare_comprehension` uses `uuid4` job IDs and a `SystemRandom` shuffle. This is
acceptable because `jobs_sha256` freezes the result after preparation, but it depends
on F3 (the `jobs_sha256` check is optional). Optionally record a seed or derive
`job_id` from (case, variant, repeat, freeze nonce) for auditability.

## Confirmed as working (unit/mock evidence only)

- Explicit `--execute` is required, and the CLI makes no call without it (`test_cli_requires_explicit_execute_before_any_model_call`).
- Interpretation completes for all jobs before any grade request (`execute_reliable:225-226`; `test_actual_runner_phase_order...`).
- Interpreter requests contain only `role, job_id, model, max_output_tokens, messages, reasoning_effort`; no criteria, reference or variant. `validate_request` rejects criteria in interpret requests.
- Grader results are validated twice:
  - `validate_result`: exact criterion IDs, boolean `passed`, nonempty evidence.
  - `_validate_grades`: response hash and provenance.
- An interrupted `running` call and unknown usage both stop the run without retry, and budgets cannot change on resume.
- Holdout splits require all 17 languages, one task per language (68 points), and no family crossing between splits. Privacy scenarios need six per language with both language modes and at least five secrets.
- Restore failure after provider capture is measured without roundtrip credit. Ambiguous alignment is not counted as protected. Duplicate spans are rejected.
- `repeated_statistics` input rows carry `split`/`template_group` from jobs. Missing grades remain missing.

## Untested paths (no unit coverage observed)

`audit_references` / `prepare_reference_audit` (entire module path), `baseline_dir`
four-arm (204-job) preparation and comparison, tamper detection for
corpus/jobs/policy/adapter, `workers > 1` concurrency, token/time budget exhaustion,
worker exception/validation-error paths in `execute_reliable`, a positive
`review_eligible` path, and real `run_privacy` + `prepare_comprehension` system-prompt
content (F1).
