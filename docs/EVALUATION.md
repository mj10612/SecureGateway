# Privacy and LLM comprehension evaluation

The evaluation commands measure two separate questions: whether the gateway protects annotated secrets, and whether an actual LLM can still follow the outbound task. A privacy score, a readable sentence, and a successful unit test do not establish LLM comprehension. The suites report these measurements separately.

The packaged corpus contains only invented projects, records, paths, contacts and source code. Defense examples concern synthetic exercises and document workflows; they contain no real customer or government material. Evaluation uses temporary local gateway state and does not modify running gateways or user settings. Inference starts only when the comprehension suite is explicitly enabled with `--real-llm`.

## Run the privacy suite

```sh
secure-gateway evaluate --suite privacy --profile smoke --output-dir /tmp/sg-baseline-smoke
secure-gateway evaluate --suite privacy --profile standard --output-dir /tmp/sg-baseline-standard
secure-gateway evaluate --suite privacy --profile release --max-seconds 300 --output-dir /tmp/sg-baseline-release
```

Each case sends a native Claude or Codex request through a real loopback HTTP gateway to a local echo provider. The provider records the actual outbound payload. The runner scores that capture, checks restoration of the selected echoed field, and replays the request to check stability. Tool argument JSON additionally has a semantic restoration check: whitespace canonicalization can fail exact string equality while preserving JSON values/types. Both results and the restored synthetic echo are recorded. Separate checks cover Claude/Codex session separation and restoration after an encrypted snapshot restart. These checks do not contact a model provider.

Use a new output directory for each run. `report.json` contains metadata, per-case outcomes and captured outbound payloads; `summary.md` presents the aggregate scores. `progress.json` preserves partial results during execution. A failed, skipped or budget-exhausted request remains unmeasured rather than becoming a protected sample. An alternate versioned synthetic corpus can be supplied with `--corpus PATH`.

| Profile | Privacy cases | Coverage |
| --- | ---: | --- |
| `smoke` | 8 | One prose task for every Korean/English and domain combination, including unforced `drift` and `흐름` names. |
| `standard` | 24 | Smoke tasks, fenced source, JSON data, tool arguments, tool results and tool schemas. |
| `release` | 32 | All cases, including ordinary-word name controls, repeated occurrences and Unicode normalization variants. |

Run the same profile and corpus on the baseline and candidate revisions, saving their artifacts separately:

```sh
secure-gateway evaluate compare \
  --baseline /tmp/sg-baseline-release/report.json \
  --candidate /tmp/sg-candidate-release/report.json \
  --output-dir /tmp/sg-privacy-comparison
```

Comparisons require compatible corpus and settings hashes, case selection and report schemas. They distinguish existing exposures, newly exposed occurrences and resolved exposures. Existing baseline leaks remain visible in the reports. A completed measurement can exit successfully while reporting baseline leaks; success means the run completed. A comparison also detects newly failing exact/semantic restoration, replay, session isolation and snapshot checks. A comparison with a regression exits with status `1`; an incomplete evaluation exits with status `2`. A complete run without a regression exits with status `0`.

## What the privacy numbers mean

| Measurement | Definition |
| --- | --- |
| Fully protected occurrence | Neither the full annotated secret nor a curated meaningful fragment remains at the corresponding source occurrence in outbound text. |
| Protection accuracy | Fully protected sensitive occurrences divided by all scheduled sensitive occurrences, reported only when all occurrences were measured. |
| Observed accuracy | Fully protected occurrences divided by measured occurrences; a diagnostic that must be read alongside unmeasured counts. |
| Full exposure | The complete annotated secret remains visible at its aligned source occurrence. |
| Partial exposure | A curated secret fragment remains visible without the full secret remaining visible. |
| Request with a leak | A measured request containing at least one full or partial exposure. |
| Overmasking | An annotated public occurrence is no longer fully visible at its aligned source occurrence; the rate uses measured public occurrences. |
| Restoration / replay | Exact restoration of the selected echoed string / stable outbound request and restored answer on replay. |

When expanding actual engine aliases reconstructs the source field exactly, the scorer uses that alias provenance to locate public and protected ranges, without feeding gold annotations into the engine. Otherwise source alignment estimates the positions of repeated occurrences and secret/public uses. It is a conservative string-alignment measurement on small synthetic fields. When repeated public/secret spellings cannot be attributed uniquely, `alignment_ambiguous` flags the occurrence and counts a potential exposure (and possible public overmasking), rather than certifying protection. `ambiguous_possible_exposures` separates these cases; full-exposure totals include this conservative bound. It does not detect every paraphrase, encoding, semantic inference or possible fragment. Short Korean names can have an empty fragment list; their complete annotated spelling is still checked. An overmasked public clause counts as an overmasked occurrence, even if part of the clause remains visible.

## Run actual LLM comprehension

First produce baseline and candidate privacy reports with the same corpus and profile. Their recorded outbound text supplies the masked arms. The comprehension suite compares four inputs for the same underlying task:

| Arm | Input |
| --- | --- |
| A | Original synthetic task. |
| B | Manually written reference that masks only the annotated secrets. |
| C | Task text captured from the baseline gateway's outbound request. |
| D | Task text captured from the candidate gateway's outbound request. |

The interpreter receives its assigned task only. It must not receive another arm's text, the original secret for a masked arm, the gold rubric, a prior answer, or the parent agent's conversation. Opaque shuffled job identifiers separate jobs from arm labels. Each response is stored before a separate fresh grader receives that response and its criteria. Comprehension profiles select the first 1, 4 or 8 smoke prose cases respectively, across all four arms and the configured repeats.

For the automated Codex CLI adapter:

```sh
secure-gateway evaluate --suite comprehension --real-llm \
  --provider codex --model MODEL --profile smoke \
  --baseline /tmp/sg-baseline-release/report.json \
  --candidate /tmp/sg-candidate-release/report.json \
  --output-dir /tmp/sg-comprehension
```

Choose a model available to the selected runner. The adapter launches a fresh ephemeral CLI session in an empty temporary working directory, ignores project/user instruction files and configuration, disables web search and multi-agent execution, and rejects tool events. It uses the caller's existing authentication with no alternate provider fallback. Record the requested model and runner metadata; a requested CLI model setting does not independently verify the provider's resolved model identity.

For native agent orchestration or a different provider, prepare the work first:

```sh
secure-gateway evaluate --suite comprehension --real-llm \
  --provider external --model MODEL --profile smoke \
  --baseline /tmp/sg-baseline-release/report.json \
  --candidate /tmp/sg-candidate-release/report.json \
  --output-dir /tmp/sg-comprehension-native --prepare-only
```

`interpret-jobs.jsonl` contains the interpreter jobs. `manifest.json` is private runner state containing the correspondence between jobs, arms and grading material. Give each fresh interpreter only its job's messages; keep the manifest and rubric outside its context. Native subagents must start with no inherited conversation and must not inspect the repository or other job files. Persist the actual returned answers in a JSON array:

```json
[
  {
    "job_id": "JOB_ID_FROM_INTERPRET_JOBS",
    "model": "MODEL_USED",
    "response": "The actual model answer.",
    "execution": {
      "kind": "actual_llm_subagent",
      "fresh_context": true,
      "runner": "Runner name and version",
      "isolation": "Fresh context; only this job's messages were supplied"
    }
  }
]
```

Import the answers to create `grade-jobs.jsonl`:

```sh
secure-gateway evaluate --suite comprehension --real-llm \
  --output-dir /tmp/sg-comprehension-native --responses /tmp/sg-responses.json
```

Run each grading job in another fresh context after the corresponding answer has been recorded. Import a JSON array with the exact job and response hash supplied by the grading job:

```json
[
  {
    "job_id": "JOB_ID_FROM_GRADE_JOBS",
    "model": "MODEL_USED",
    "response_hash": "RESPONSE_HASH_FROM_GRADE_JOB",
    "grades": [
      {
        "id": "CRITERION_ID_FROM_GRADE_JOB",
        "passed": true,
        "evidence": "A concrete statement in the recorded answer supporting this judgment."
      }
    ],
    "execution": {
      "kind": "actual_llm_subagent",
      "fresh_context": true,
      "runner": "Runner name and version",
      "isolation": "Fresh grader context after the interpretation was recorded"
    }
  }
]
```

```sh
secure-gateway evaluate --suite comprehension --real-llm \
  --output-dir /tmp/sg-comprehension-native --grades /tmp/sg-grades.json
```

Use the model specified by the prepared job for both interpretation and grading. Include every criterion exactly once, with a Boolean result and nonempty evidence. Do not replace actual inference with hand-written expected answers or a keyword-checking script. Execution provenance is auditable runner metadata, not cryptographic proof that an external service used the stated model or isolation.

The comprehension result counts passed criteria against all scheduled criteria, plus intent and all-required request counts. It withholds a complete accuracy score while any responses or grades are missing, and reports observed accuracy and missing counts separately. Interpretation success and grader success are separate execution outcomes. No privacy and comprehension scores are combined into a single accuracy number.

## External worker executable

An explicitly selected `--provider external --worker-command /absolute/path/to/worker` can automate the same work. The command is one executable, invoked without shell expansion. It reads one JSON object from stdin and emits one JSON object to stdout. Interpreter requests contain `role: "interpret"`, an opaque `job_id`, `model`, `max_output_tokens`, and `messages` of `{role, content}`. Its response contains matching `job_id`, the actual `model`, and a nonempty `response`.

Grader requests instead use `role: "grade"` and additionally contain `criteria` as `{id, description}` objects. The worker returns matching identity and a `grades` array of `{id, passed, evidence}` objects; it must not return an interpretation in the grader result. Worker results may also contain `usage` with nonnegative integer token counts and `metadata`. If usage is reported, `total_tokens` is required and reported `output_tokens` must not exceed the requested limit. The prepared-file import format above additionally binds grades to a stored `response_hash` and records explicit execution provenance.

Workers are opt-in processes with call, wall-time and captured-output limits. The runner bounds stdin/stdout/stderr and rejects reported output-token overages. Its UTF-8 byte guard is an output-size bound; it is not an exact tokenizer count or a provider-enforced generation cap. If a failed/rejected inference has unknown usage, or a successful external worker omits usage, automatic execution stops conservatively and records `token_usage_unknown`. Reported total usage is checked before subsequent calls; it cannot retroactively prevent an already executing provider request from consuming tokens. Native imports record their own provenance and may leave token usage unreported. Inspect `evaluate --help` for the available budget options. Temporary working directories and fresh conversations reduce accidental context carryover; workers still run as the same OS user, and the Codex adapter shares subscription authentication. These are not hard filesystem jails.

## Corpus and interpretation limits

`src/secure_gateway/evaluation_corpus.json` has schema version `1` and corpus version `1.0.0`. Its 32 curated cases cover Korean and English across general, defense, automotive and semiconductor domains, with four cases per language/domain pair and sixteen cases per request dialect. Sixteen prose cases carry task rubrics; structured/source cases carry no comprehension rubric. Other fifteen supported languages are unmeasured by this corpus.

Annotations point to string fields in the original source payload. `start` and `end` are Python/Unicode code-point offsets into those strings, with an exclusive end; they are not UTF-8 byte offsets or grapheme indexes. Preserve the NFC and NFD spellings exactly when editing. Every repeated annotated secret occurrence has its own span. The human reference minimally replaces the annotated project names and retains the original task's instructions.

`forced_terms` includes only explicitly supplied policy secrets labeled `explicit`; contextual project names and pattern-detected contacts/paths are not added from gold annotations. In particular, ordinary names such as `drift` and `흐름` remain unforced. The engine receives the source payload and explicit policy only. Human references, public/secret spans and rubrics are evaluation material and must not become masking rules or model input for masked interpretation arms.

The split labels identify development, regression and synthetic holdout template groups; aliases of a template do not cross splits. Once a holdout case is inspected or used to tune behavior, it is no longer untouched evidence. This packaged, readable corpus is a regression resource, not a claim of independent real-world generalization. Keep historical result artifacts and corpus hashes when changing fixtures or annotations.

Request transformation and response restoration timings are measured separately from the full HTTP round trip, with first-pass/replay sample counts and p50/p95/p99. These are small in-process fixture timings, not cold-process or production throughput guarantees. Reports record package/code/corpus versions and package source hashes, settings and corpus hashes, selected cases, environment, timing and errors. From 2.6.0, metadata records the packaged dictionary manifest hash and default domain flags (defense On, automotive/semiconductor Off); the ordinary CLI does not offer a custom toggle matrix. Separate dictionary tests/matrix artifacts identify their actual flags. Local HTTP tests do not certify native Claude/Codex clients, hosted provider behavior or production disclosure risk. Offline unit tests validate the runner and its accounting; only recorded, independently executed LLM jobs measure comprehension.

Prepared-run model/profile/repeats/output settings are immutable; explicitly conflicting resume options fail instead of silently using old settings. Use a fresh output directory to change them. Rubric criteria and repeated trials are correlated; the report supplies request counts and descriptive paired outcomes, not a generalization confidence interval.

`--prepare-only` and a response import awaiting grades intentionally produce an incomplete report and exit `2`. This signals pending interpretation/grading, not a completed comprehension measurement; orchestration scripts should handle that status before proceeding to the next phase.
