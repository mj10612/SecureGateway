# Issue #308 initial evaluation evidence

This is evidence that the evaluation infrastructure runs, and an initial baseline for future experiments. It is not evidence that the masking engine has been improved. No masking rules, dictionaries or grammar behavior were changed in this release.

## Offline HTTP privacy baseline

The release profile executed 32 invented Korean/English cases across general, defense, automotive and semiconductor domains, through actual loopback gateway HTTP requests. The echo provider recorded outbound payloads. The 66 sensitive and 117 public annotations include explicit-policy and unforced contextual cases.

| Measurement | Result |
| --- | ---: |
| Fully protected sensitive occurrences | 57 / 66 (86.36%) |
| Full exposed sensitive occurrences | 9 / 66 |
| Partial exposed occurrences | 0 |
| Ambiguous possible exposures | 0 |
| Requests with an annotated exposure | 9 / 32 |
| Overmasked public spans | 30 / 117 (25.64%) |
| Exact echoed-string restoration | 31 / 32 |
| Semantic restoration | 32 / 32 |
| Replay stability | 32 / 32 |
| Session separation / encrypted restart | Both passed |

The exact-string mismatch is `ko-general-tool-arguments`: JSON arguments are compacted (spaces around separators are removed), while the decoded keys, values and types remain equal. Exact and semantic results are deliberately separate.

The nine exposures are contextual ordinary-word names without explicit forced policy. Gold labels were not injected into the engine. They remain unresolved baseline findings for the accuracy experiments, including #310. These fractions are specific to this small synthetic corpus; they are not production disclosure probabilities or comparisons to the old 510-probe corpus.

See [the captured report](privacy/report.json) for per-language/domain/path scores, transformation/restoration timings, inputs and errors. First/replay measurements are in-process loopback fixture samples, collected on a shared host while verification work could run concurrently. They do not establish production latency or cold-process performance. Domain dictionary toggles (#307) and fifteen other languages are unmeasured.

## Actual LLM subagent smoke test

One English conditional-review task was evaluated in four arms: original, manually masked, gateway baseline and gateway candidate. Baseline and candidate used the **same unchanged engine capture**; this run cannot demonstrate an improvement between versions.

Four actual interpretation subagents were started with `collaboration.spawn_agent(fork_turns="none")`. Each received only its supplied system instruction and task, with an instruction to use no tools. They received no original for the masked arms, gold criteria, other answers, arm labels or parent conversation. Their first answers were saved before four separate fresh grading subagents received the original task, rubric and corresponding saved answer. All eight agents used no tools.

| Arm | Actual first answer | Criteria passed |
| --- | --- | ---: |
| Original | Is AmberPebble’s status ready for review? | 4 / 4 |
| Human masking | Is [PROJECT] ready for review? | 4 / 4 |
| Baseline | Is the status of private_symbol_2 ready for review? | 4 / 4 |
| Candidate | Is private_symbol_2 ready for review? | 4 / 4 |

The rubric checks eventual review intent, readiness prerequisite, clarification before proposing steps, and no command execution. These are **one task, four input conditions and sixteen correlated criterion judgments**, not sixteen independent examples or an estimate of overall LLM accuracy. There were no observed baseline/candidate criterion changes in this smoke test.

The runner did not expose an independently verified model/version; artifacts label it `inherited-session-model-unreported`. Exact token usage and inference latency were not exposed by this orchestration tool. No native Codex/Claude client or hosted provider integration is certified by this run. The optional Codex CLI adapter has executable-contract tests; this artifact uses the native subagent import path.

The [first responses](comprehension/actual-responses.json), [independent grades and evidence](comprehension/actual-grades.json), [blind jobs](comprehension/interpret-jobs.jsonl), [synthetic runner manifest](comprehension/manifest.json) and [final report](comprehension/report.json) preserve the evidence. The manifest is included only because this corpus is synthetic; it contains originals and rubrics and must never be given to an interpretation worker. Native grading agents received the original/rubric/saved-response portion of each grading job; automated workers additionally receive the recorded model input for interpretation of aliases.

## Repeat

```sh
secure-gateway evaluate --suite privacy --profile release --output-dir /tmp/sg-next
secure-gateway evaluate compare --baseline docs/evaluations/issue308-v2.5.0/privacy/report.json --candidate /tmp/sg-next/report.json
```

For actual comprehension reruns use [the opt-in subagent workflow](../../EVALUATION.md). Always save new artifacts rather than overwrite historical results. Reports were generated before the release commit: `code_sha` identifies its parent revision, package version identifies this release, and the privacy report’s `source_hash` records the evaluated package source fingerprint. The earlier comprehension job capture predates this source-fingerprint field and retains per-job input hashes.
