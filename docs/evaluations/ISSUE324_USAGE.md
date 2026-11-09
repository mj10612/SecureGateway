# Frozen multilingual evaluation commands

These commands use synthetic owner-authored data. Reports include source text and
alias bindings for local scoring; they are not sanitized production telemetry.
Development and holdout outputs remain separate. No engine vocabulary change is
authorized by a development score.

Validate schema, offsets, split families and raw hashes without printing tasks:

```powershell
secure-gateway evaluate reliable validate --data-dir docs/evaluations/issue324-data
```

Check that the owner reference responses can attain all 68 criteria. This is a
separate grading audit, not a model task-response score. The execute option makes
real fresh model calls through the installed native Codex CLI and subscription:

```powershell
secure-gateway evaluate reliable audit-references --data-dir docs/evaluations/issue324-data --output-dir audit-new --split holdout --execute --max-calls 17 --max-seconds 900 --max-tokens 600000
```

Prepare actual loopback privacy captures and blind task jobs in a new directory;
preparation makes no model calls. Use `--split development` for development work.

```powershell
secure-gateway evaluate reliable prepare --data-dir docs/evaluations/issue324-data --output-dir baseline-new --split holdout --reference-audit-dir audit-new --repeats 3 --model gpt-6.1-sol --reasoning-effort medium --max-output-tokens 2048
secure-gateway evaluate reliable run --output-dir baseline-new --execute --max-calls 306 --max-seconds 7200 --max-tokens 12000000 --workers 3
secure-gateway evaluate reliable report --output-dir baseline-new
```

The baseline measures 17 languages × 3 arms × 3 repeats, followed by 153 independent
fresh grades. Save all first answers before starting any grader. Original and human
controls use source system instructions; masked arms use their actual outbound
instructions. Performance graders receive original/rubric/saved answer and owner
missing-fact/alias notes, but no reference answer key. Report each language out of
four and each repeat out of 68, with mean and sample SD; incomplete groups have no
complete mean. Privacy, public overmasking and restoration remain separate axes.

For a pre-registered frozen candidate, add `--baseline-dir baseline-new` when
preparing a new output directory and allow 408 calls for the four contemporaneous
arms. Candidate preparation compares both privacy and task-payload privacy against
the saved baseline. Baseline-only measurements cannot authorize adoption. Reusing
a holdout after inspecting a failed candidate requires independent confirmation,
as specified in the [protocol](ISSUE324_PROTOCOL.md).
The default append-only use ledger lives beside the data directory; its path can
be set with `--holdout-ledger`. An explicit `--holdout-reuse-reason` permits another
diagnostic candidate run, which remains ineligible for adoption review. Keep the
ledger with the evidence when moving a prepared run. Both per-criterion gross and
net changes remain in the report; a net conditions/prohibition regression blocks
eligibility, and every individual hard failure still requires owner review.

Call counts are bounded. Token/time budgets stop scheduling from reported usage;
already-running native calls may finish later (up to three calls, each with a
300-second process timeout). The CLI has no provider hard output-token cap. Unknown
usage or interrupted calls stop automation, retain incomplete status and do not
trigger automatic retries. All mock unit results validate bookkeeping only.

If a run stops during grading after saving every first answer, preserve it and
prepare a separate grade-only supplement. A failed grading job is excluded unless
explicitly named with a reason; previously successful grades are never replaced:

```powershell
secure-gateway evaluate reliable supplement-grades prepare --parent-dir baseline-new --output-dir grades-new --reattempt-job-id FAILED_JOB_ID --reattempt-reason "Complete a missing grade of the saved answer; retain the original failure and unknown usage."
secure-gateway evaluate reliable supplement-grades run --output-dir grades-new --execute --max-calls 124 --max-seconds 3600 --max-tokens 4000000 --workers 3
secure-gateway evaluate reliable supplement-grades report --output-dir grades-new
```

Set the call budget to the actual frozen schedule size. The new report distinguishes
the stopped primary execution, supplemental execution and combined semantic scores.
An unknown parent usage remains unknown; reported total tokens are a lower bound.
