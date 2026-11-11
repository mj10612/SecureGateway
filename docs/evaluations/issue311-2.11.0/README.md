# Issue 311 evidence (2.11.0)

The committed [replay protocol](../issue310-2.11.0/FREEZE.md) uses the existing synthetic development and already-inspected holdout corpora. Per-case raw payloads, source offsets, baseline and candidate reports, saved interpretation jobs, first responses and errors are under [`regression-replay/`](regression-replay/). The older independent run is under `../accuracy-20261109/holdout-task-response-retest/311/`; it measured older code, not this candidate.

| Measure (baseline -> candidate) | Development | Previously inspected holdout |
| --- | --- | --- |
| Fully exposed sensitive spans / measured | 0/4 -> 0/4 | 4/4 -> 4/4 |
| Overmasked public spans / measured | 0/5 -> 0/5 | 1/12 -> 1/12 |

There were zero partial exposures in both arms, and exact restoration passed 2/2 per arm in each split. These are small regression samples, not an untouched holdout or real-world accuracy estimates. The real-LLM runner received two ungraded first responses (29,724 reported tokens); it stopped before completing the 8 jobs under its 16,384-token per-case threshold. Both actual responses are in the manifest, but no comprehension score is available.

Engine-only cold/warm timings and Windows process peak-working-set deltas are in `performance-by-issue.json`; see `../../ISSUE_RESOLUTION.md` for the guard result, memory limits and the #311 bounded-scan retest. The public-exception C and combined profiles were not benchmarked. Decision: **hold**; the candidate stays off by default and the acceptance gaps are listed in `../../ISSUE_RESOLUTION.md`.

New preregistered synthetic holdout (two cases, en/ko; candidate and cases share an author): full exposures baseline 5/5, candidate 5/5; public overmasking 0/2 and 0/2; partial exposure 0 in both arms; exact restoration 2/2 in both arms. Raw per-case captures are under `new-holdout-run/`. These cases do not establish independent or real-world generalization.

The bounded-scan follow-up retest and its source hashes are in `performance-retest.json`; it covers only 10/100 KiB prose and does not rerun the full workload matrix.

After the bounded #311 scan, the same new synthetic cases were replayed as regression cases; full-exposure counts were unchanged. Raw captures are under `final-regression-run/` (the #310 directory retains its issue-number subdirectory).
