# Issue 323: public-policy validation, 2026-11-09

This development-only capture evaluates the uncommitted public-word candidate.
The holdout was not used. No model calls were made. The original corpus labels
were retained, including labels for names the revised user policy may permit.

The deterministic capture is in
`docs/evaluations/issue323-2.7.2/development-public-policy-candidate`.
Compared with the released 2.7.1 development baseline, the privacy suite
protected 464/786 annotated occurrences versus 751/786; 287 newly exposed
occurrences were classified as contextual (250 person, 37 organization).
The task-payload capture protected 10/71 versus 70/71; 60 newly exposed
occurrences were contextual (53 person, 7 organization). Under the old labels,
both comparisons regress. They do not establish which individual exposures
are acceptable under the revised policy. In particular, the policy permits
widely used names but does not establish that every organization or uncommon
person name is public. No pattern-classified occurrence was newly exposed in
this development capture.

The same capture measured 50/186 overmasked public occurrences versus 110/186
in the baseline, with 102/102 semantic round trips. It did not measure task
response quality. Do not treat a development capture as the holdout result.

An unrelated regression found in review allowed structured stop strings to be
treated as ordinary prose. The request now handles `stop` and `stop_sequences`
as structured private data. The xAI, validation, vocabulary, morphology and
public-policy tests passed: 366 passed, 1 skipped. Related tool workflow,
validation and numeric tests passed: 155 passed. Ruff and mypy passed on the
three modified gateway modules.

The earlier full suite reported 347 failures; a focused gateway run stopped at
12 failures (138 passed). Some failures encode the prior policy of masking
common names and ordinary domain words, but the remaining failures have not
all been classified. The required frozen holdout task and privacy assessment
has not been completed. The owner directed integration with organization-name
exposure accepted; this does not establish that every uncommon person name or
other unregistered sensitive value is safe to disclose. Keep the outstanding
evaluation and failure classification visible.

## Completed follow-up

The candidate was integrated in 2.7.10 and evaluated at the frozen 2.7.13 commit.
The [holdout report](../evaluations/issue323-2.7.13-holdout-continuation/README.md)
records a task-response gain from 48.00 to 61.00 / 68, with three repeats per
language. It preserves an interrupted primary run, its three unknown-usage
attempts and a separate explicit continuation. The owner reviewed and accepted
the complete newly exposed person/organization list. Original privacy labels
and failed strict adoption gates remain visible.

The integrated pre-alignment full suite had 4,554 passed, 345 failed and 288
skipped. All failures were confined to eight test files whose expectations used
the previous private-by-default policy. Their updated public-default and
explicit-private controls passed 811 tests with 2 skips. Historical evaluation
corpora and parser fixtures were not changed. Evaluation safeguards/diagnostics
passed 59 tests; Ruff, mypy, package build and version checks passed for 2.7.14.
