# Issue #324: reliable task-response and multilingual privacy evaluation

Protocol drafted before inspecting the independently authored holdout or changing
the masking engine for #323. Existing 17 paragraphs and the 2026-11-09 candidate
screens are regression/development evidence, never adoption holdouts.

## Data and decision boundary

Claude authors new development and holdout task families and privacy scenarios
in a separate worktree without reading prior fixtures, model answers, vocabulary
implementation or the other worktree. Each task split has one task in each of
the 17 supported languages and four criteria: intent, conditions, prohibition,
scope. Its theoretical maximum per repeat is **68**, not an artificially reduced
ceiling. Privacy splits each have six scenarios per language, with at least five
private occurrences per scenario (at least 510 per split). Report actual counts;
missing cases or invalid translations cannot be silently excluded.

Keep template families, translations and name-only variations in one split.
Freeze files, source/adapter/rubric versions and hashes. Validation of holdout
schema/offsets may reveal counts and errors, not task text to the optimizer.
Develop #323 only on development material and licensed general-language sources.
Freeze a candidate before requesting its holdout evaluation. Once inspected or
used to tune a candidate, a holdout becomes regression material; do not repeatedly
optimize against it and call it untouched. Only holdout metrics may support an
adoption decision. Development/regression results remain separately visible.

## Information-deferral grading policy, version 2

Score an actual answer, not a paraphrase. However, an unavailable fact is not a
license to invent an item list, room dimension, material, recipient or number.
Credit a targeted clarification and a useful conditional outline when those are
the appropriate way to carry out the visible request. If a particular decision
requires a missing fact, deferring that decision is correct; do not demand a
concrete choice the original prompt makes impossible. Still require all other
supported work, order, prohibitions and output scope. Do not accept blanket refusal
merely because names are opaque. Grade semantic equivalence rather than required
keywords or an exact reference-answer wording.

Explicit numeric and structural limits have no tolerance. Count whitespace-delimited
letter/digit tokens as words, excluding standalone list markers; whole-message
limits include requested titles, salutations and signatures. Count NFC codepoints
including spaces/punctuation for character limits unless the task says otherwise.
Sentence endings include native punctuation, excluding decimals, emails and
abbreviations; headings, salutations and fixed sign-offs are not separate sentences.
Clarifications must fit the requested length and structure. These generic rules
were settled from metadata-only author inventory before holdout reference auditing.
The earlier development reference audit used the pre-counting-rules policy and
remains pilot evidence; its saved grades are never rewritten or reused as a
verification of the final policy hash.

Owner-side full-credit reference responses must satisfy the four criteria without
inventing missing information. Audit them independently before the measurement
freeze; reference auditing is rubric validation, not a model-comprehension score.
The actual original arm can still make mistakes. A theoretical ceiling of 68
does not guarantee every stochastic original answer will score 68.

The interpreter receives only actual visible messages and the fixed task-response
instruction, never originals/gold, variant names, privacy annotations, reference
responses, parent history or previous answers. Save its first answer before an
independent fresh grader sees the original/rubric/saved answer. Do not replace a
first answer or first grade; supplementary adjudication must be reported separately.
Original and human controls use source system instructions; only masked arms use
the gateway-injected masked-context instruction. Reference answers are used only
for the separate attainability audit, never as an answer key for performance graders.
Owner-side missing-fact notes and alias identity bindings remain available to graders.

## Repeats, budgets and reporting

Use at least **three fresh repetitions per language and arm**. Pin the requested
model and reasoning configuration, native CLI version, adapter hash and output
budget before calls. Record requested identity separately from an unverified
service-side build. Each call uses a fresh ephemeral context/empty cwd; same-user
filesystem/auth remains and is not a hard information-flow sandbox. Reject tool
events in semantic tasks. Ordinary tool/MCP capability has separate tests.

For the initial #324 holdout baseline, original/human/baseline arms require 153
interpretations and 153 independent grades (306 calls). A later frozen candidate
comparison uses all four arms on the same cohort: 204 interpretations and 204
grades (408 calls), keeping contemporaneous controls rather than attributing
service/model drift to vocabulary. Reference-response auditing is a separately
budgeted phase. No inference starts without an explicit execute option and a
saved budget: calls, wall time, reported input/output tokens, worker concurrency
and maximum output. Unknown failed-call usage stops subsequent automated calls;
failures, omissions and budget exhaustion stay incomplete, never count as passes.
The native CLI exposes reported usage rather than a provider hard token cap. Token
and wall-time limits stop scheduling; already submitted calls can finish after a
limit. With three workers, at most three calls remain in flight, each with a
300-second process timeout. Report this boundary with actual usage and elapsed
time rather than claiming a strict provider-side budget.

For each language/arm report each repeat's score out of four, the arithmetic mean
and sample standard deviation (ddof=1), whole-task successes and failed criteria.
For each arm/repeat report the sum out of 68, then mean and sample SD across the
three sums. Incomplete repeats cannot create a complete mean; retain observed
values separately. Report paired baseline/candidate differences by task/repeat.
Criteria and repeated answers are correlated: do not call 204 rubric items 204
independent tasks or infer real-world failure probabilities from this small study.

## Privacy and integrity alongside task scores

Capture actual final loopback HTTP payloads, not just a helper's intermediate
string. Score source-offset private/public annotations independently of model
grades. Report full/partial/ambiguous/unmeasured exposure, requests with leaks,
overmasking, and denominators by language, sensitivity policy/category, dialect,
language mode and split. Include both auto and explicit-language settings.
Only explicitly owner-registered `explicit` terms may become forced rules;
contextual gold labels must not be injected into masking policy. Common-word
names must be paired with ordinary-use controls. Preserve normalization and
repeated-occurrence provenance; an ambiguous alignment is not certified protection.

Verify exact/decoded JSON restoration, replay, session isolation and encrypted
restart separately. A roundtrip is not privacy or comprehension. Every joint
report links the frozen privacy and task reports and exposes their statuses.
No adoption can pass on incomplete measurement, new full/meaningful partial
exposure of a baseline-protected occurrence, or weakened explicit/private/code
protection. Existing baseline leaks remain failures and are reported separately.

Task gains must occur on holdout, with the repeat distribution and hard-condition/
prohibition failures reviewed. The implementation reports eligibility for review;
it does not silently enable a policy from a point estimate. Any candidate that
needs repair after holdout inspection requires a new independent confirmation
before an adoption claim. This protocol and data alone do not close #324: the
new path must be exercised with actual fresh interpretation and grading calls.

## Prospective grade-only recovery after the first native failure

The initial holdout execution stopped after 153 saved first answers, 29 saved
first grades and one native grading failure with unknown usage. Its original
journal/report remain stopped and incomplete. The lost failure cause/usage cannot
be reconstructed. No prompt, criterion result or answer was inspected to choose a
replacement. Successful first grades and every first answer remain immutable.

A coordinator-initiated, separately frozen supplement may grade the 123 missing
and never-attempted jobs. The failed job is excluded by default; completing it
requires its explicit job ID and a reason recorded before any call. This is a
later stochastic grading attempt of the same saved answer, not a replacement
interpretation or an erased first attempt. The supplement has its own execute
option, immutable call/time/reported-token budget, journal and failure policy.
It does not reset or resume the stopped original execution.

For this recovery, keep the original native adapter, prompts, requested identity,
reasoning effort and output budget unchanged. A separately fingerprinted observer
calls that adapter verbatim and records only safe failure codes, elapsed time,
validated available usage and content-free rejected-message hashes. It does not
change successful results or reveal arbitrary exception text/stderr/environment.

The combined report identifies every grade as first, supplemental or an explicit
reattempt. Report complete semantic groups separately from execution status:
the parent remains incomplete, and total reported tokens remain a lower bound
because the original failed call has unknown usage. A completed supplement cannot
claim that the original run completed or satisfied a known total token budget.
Record this grade-only use in the holdout ledger; it is not a new candidate or
permission to optimize against holdout. Baseline-only scores never enable a policy.
