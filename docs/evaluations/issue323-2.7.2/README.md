# Issue #323 development work (not adopted)

This folder records development-only preparations made while the working package
version was 2.7.2. Version 2.7.2's committed production change is the separate
digit-leading path restoration fix; the vocabulary candidate is uncommitted.

The original #324 corpus and all historical results remain unchanged. The
development reference audit found a Marathi reference-response formatting error:
an explicitly required one-line signature was split across two lines. Its
67/68 audit is retained in `development-reference-audit`. The development-only
revision changes that reference formatting and its corpus-version identifier;
`../issue323-development-data/derivation.json` records the exact changes and hashes.
Neither holdout file was changed. The revision's independent reference audit in
`development-reference-audit-revision2` achieved 68/68.

`development-baseline-reference2` captures released 2.7.1 gateway behavior on the
revised development bundle. Its source snapshot and provenance identify the
released Git blob. No interpreter or grading calls were run for this capture;
its purpose is to supply the baseline payloads for a later contemporaneous
four-arm comparison.

`development-candidate-1` is a failed development privacy gate, not a task-score
result or a holdout evaluation. Its independent frequency vocabulary and bounded
morphology reduce public-token overmasking but introduce new private exposures.

| Development measure | Released baseline | Candidate 1 |
| --- | ---: | ---: |
| Privacy-suite protected occurrences | 751/786 | 703/786 |
| Fully exposed occurrences | 35 | 83 |
| Ambiguous possible exposures (not protected credit) | 0 | 2 |
| Overmasked annotated public occurrences | 110/186 | 95/186 |
| Semantic round trips | 100/102 | 101/102 |
| Task-payload protected occurrences | 70/71 | 64/71 |
| Task-payload semantic round trips | 17/17 | 17/17 |

There are 61 newly exposed privacy-suite occurrences and 7 newly exposed
task-payload occurrences, as recorded in the two comparison JSON files. Net
improvement in unrelated cases does not cancel these regressions. Frequency
membership does not establish that a token is public in its current role;
proper-name coverage, ordinary-word name homonyms and derived capitalized
compounds remain unresolved. The candidate was rejected before paid native task
calls. No holdout candidate use has been consumed and no new vocabulary policy
has been enabled in a host gateway.

Next candidates must use new output directories, preserve this failure record,
pass development privacy checks, and then satisfy the original #324 holdout
protocol. Development results cannot establish adoption eligibility.
