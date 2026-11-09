# Candidate experiments: actual first responses and independent grades

Date: 2026-11-09. These are synthetic exploratory screens, not production
accuracy estimates. None of candidates #309–#318 is enabled by normal gateway
installation. A failed candidate is not repaired by reporting restoration as
comprehension, or by ignoring existing privacy failures.

**Validity correction:** the first-run tables below are retained as harness
diagnostics only. The old worker asked for an interpretation/paraphrase, while
some graders demanded an actual plan or clarification question. Original answers
that correctly described the task were penalized for not executing it. Those
scores cannot support adoption or rejection. `holdout-task-response-retest/`
uses the same frozen candidates/corpus with a corrected task-response adapter;
its separate first responses/grades supersede the invalid decision, not the
historical files. It is a retest, not a new untouched holdout.

## Execution and deviations

The independently authored `holdout-cases.json` contains two task families per
candidate. The author did not receive candidate implementations or the development
corpus; an initial broad repository search incidentally displayed unrelated
existing fixture snippets. This is a limited independence claim, not a blinded
clinical-style study. `development-cases.json` is development material.

For each candidate, actual loopback HTTP captures produced baseline and candidate
provider payloads with defense On and automotive/semiconductor Off. Original,
human minimally masked, baseline and candidate arms each received two fresh
interpretations. Every first response was saved before a separate fresh grader
received the original, rubric and saved answer. Interpreter JSONL files contain
only actual model messages and opaque IDs. Gold and variant labels occur in the
owner manifest, not interpreter requests. No answer was retried or replaced.

The completed run made **320 actual Codex CLI child calls**: 160 interpretation
and 160 grading calls. Reported total usage was **5,104,647 tokens**, including
cached input tokens in that total. Runtime was 1,292.125 seconds. The requested
model setting was `gpt-6.1-sol`, CLI 0.167.0; exact service-side model build was
not independently verified. Children used fresh empty working directories,
ignored user configuration/rules, subscription authentication and a read-only
sandbox. Tool events were rejected. Same-user filesystem/auth access remains;
this is not a hard information-flow sandbox.

**The executed budget differs from the original protocol.**
`EXPERIMENT_PROTOCOL_20261109.md` planned 512/768 output tokens and 32,768 total
tokens per candidate. The prepared jobs actually allowed 1,024 output tokens and
the dispatched runner used an aggregate 320-call/7,200-second/12-million-token
budget. CLI system-prompt overhead alone made the earlier token budget
impractical. This deviation was not preregistered in that protocol; the results
must be treated as exploratory, not a protocol-conforming confirmation. The
original protocol is retained. Failed worker smoke calls outside this run are
not substituted for its first responses or included in its known-usage total.

Captures were frozen in a dirty prototype tree reporting package 2.5.2 and its
source fingerprint, before the final 2.6.0 version bump and final small dictionary
metadata/seed additions. Their recorded manifest hash identifies that dictionary
revision. Do not relabel them as captures of the final release. Final release
privacy and dictionary performance are measured separately under
`../domains-2.6.0/`.

## First-run diagnostic scores — invalid for task-performance decisions

Each arm has **16 correlated rubric criteria across four responses** (two task
families × two repeats). Whole-task counts require all four criteria in a response.
Criteria are not independent samples. No confidence interval or real-world failure
probability is inferred. Original/human failures are retained rather than blamed
on masking.

| Issue / candidate | Original | Human | Baseline | Candidate | Whole candidate tasks / 4 | Paired gains / losses | Full exposed sensitive spans, baseline → candidate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| #309 reviewed Korean morphology | 10/16 | 10/16 | 6/16 | 7/16 | 0 | 1 / 0 | 0 → 0 |
| #310 explicit name-role protection | 8/16 | 13/16 | 8/16 | 8/16 | 0 | 0 / 0 | 0 → 0 |
| #311 permitted coarse role hints | 16/16 | 16/16 | 6/16 | 7/16 | 1 | 1 / 0 | 0 → 0 |
| #312 numeric field protection | 15/16 | 14/16 | 4/16 | 8/16 | 0 | 4 / 0 | 0 → 0 |
| #313 per-line mixed-language selection | 9/16 | 10/16 | 6/16 | 6/16 | 0 | 0 / 0 | 0 → 0 |
| #314 conservative public vocabulary | 10/16 | 10/16 | 4/16 | 1/16 | 0 | 0 / 3 | 1 → 0 |
| #315 concise privacy instruction | 15/16 | 16/16 | 9/16 | 10/16 | 0 | 1 / 0 | 0 → 0 |
| #316 scoped additional protection | 10/16 | 10/16 | 5/16 | 7/16 | 0 | 2 / 0 | 1 → 0 |
| #317 explicit table/form protection | 16/16 | 16/16 | 7/16 | 6/16 | 0 | 2 / 3 | 0 → 0 |
| #318 scoped attribute bundles | 16/16 | 10/16 | 9/16 | 7/16 | 0 | 1 / 3 | 0 → 0 |

The first grading pass appeared to fail the adoption screen. #309,
#311 and #315 have insufficient paired gains and hard-condition failures. #310,
#312, #313 and #317 show no new protection on their two holdout families; #317
also loses criteria. #314 and #316 remove one observed exposure each, but do not
meet the comprehension condition. #318 loses criteria without a new measured
protection benefit. **The task/grade mismatch invalidates that rejection decision.**
Keep every candidate out of the default pending the corrected retest and any
required larger confirmation. This is not proof that the candidates improve or
that every future morphology/name/context approach will fail.

`candidate-screen-summary.json` records denominators and paired counts. Each
`holdout/<issue>/` directory retains actual outbound payloads, source gold spans,
privacy/integrity metrics, first responses, independent grades and response hashes.
The 20-family confirmation gate has not run.
The proposed five-cold-process/30-warm full-transform performance gate was also
not completed for these rejected candidates; no latency eligibility is claimed.

## Separate inference and actual-tool screens

`bundle-inference/` freezes two four-record synthetic catalogs before its 12
actual inference calls. Catalog-only, baseline-plus-catalog and
candidate-plus-catalog each yielded four abstentions, zero correct top-1
identifications and zero unsupported selections. This measures no improvement
over baseline; it is not a real-world reidentification probability or a top-k
measurement. Catalogs were authored after the captures, so this is a separate
exploratory attack screen.

`arithmetic/` contains four actual local tool executions by fresh interpreters
(two multiplication and two date-difference runs), alias-only tool traces and
saved final responses. Local restoration returned 51.00 USD and four days
respectively. A fresh independent grader passed the five supplied checks,
including two actual no-tool controls. The tool interpreters received only the
issued aliases and explicitly public units, not the operands, dates or gold.
General shell access was restricted by instruction to one dispatcher command;
this is weaker isolation than a dedicated MCP tool. The traces are parent-attested,
not cryptographically authenticated. Interpreter token usage was unavailable.
No full four-arm host/MCP comparison or larger confirmation is claimed, and this
dispatcher is not automatically installed or enabled.

## Remaining baseline limitations

The final-release 32-request privacy regression has nine existing full exposures
among 66 annotated sensitive occurrences, zero partial exposures, and 30/117
overmasked public spans. All 32 decoded payloads and replays restore correctly;
one exact JSON text roundtrip differs only in serialization whitespace. These
are separate limitations. The dictionary feature and runtime fixes do not imply
that #291/#306's general privacy/meaning problem has been solved.
