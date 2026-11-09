# Domain dictionaries and runtime verification — 2.6.0

Date: 2026-11-09. Windows 11 build 26200, CPython 3.11.15, shared AMD64 host.
This report separates source coverage, matcher performance, payload protection,
model comprehension and installed host execution.

## Packaged data

The frozen manifest hash is
`21633eedb169f5e50061d4b935120c8930ddb67f4f9c608b6e0828873cba11c3`.
Source records, concept counts, matching forms, categories and review status are
documented in [DICTIONARY_SOURCES.md](../../DICTIONARY_SOURCES.md). The offline
candidate snapshot contains 46,234 records; generated synthetic performance
strings do not increase this count.

| Domain | Active concepts | Active forms | Browse-only concepts |
| --- | ---: | ---: | ---: |
| Defense, default On | 19,473 | 21,317 | 93 |
| Automotive, default Off | 6,510 | 7,680 | 678 |
| Semiconductor, default Off | 2,191 | 2,721 | 139 |

Defense includes 149 explicitly compiled subcomponent concepts and 785 explicit
project/program concepts, in addition to the named platform/model source labels.
Sources retain stable IDs, licensing and non-specialist review labels. A label's
presence is a user-selected protection policy, not certification that every
source label/translation is correct or that every occurrence is a secret.

## Performance evidence

`performance-final.json` measures the actual catalog plus separate synthetic
1,000/10,000/100,000-string indexes. On this run the actual catalog loaded and
built in 1,053.5 ms; a 1KiB English no-hit scan had p95 0.241 ms and a 1MiB scan
had p95 163.213 ms across 20 repetitions. p99 is deliberately null. These are
matcher times, not total gateway or provider response latency. The older
`performance.json` and `performance-expanded.json` retain their earlier manifest
hashes and are not relabeled as final results.

`performance-matrix.json` measures **288 combinations × three warm repetitions**:
eight active-policy combinations, 1/10/100KiB/1MiB, English/Korean/mixed inputs,
and no deliberately inserted match/sparse/dense matches. Three samples cannot
estimate p95/p99; both remain null. An English fixture phrase was found not to
be an admitted exact form; 64 affected rows were remeasured with active `AESA`,
and that correction is recorded. This was fixture calibration, not an untouched
performance comparison. All scheduled rows are retained, including safe errors.

Default-defense no-hit p50 was approximately 0.157/0.330/0.584 ms for 1KiB
English/Korean/mixed inputs and 152.8/328.1/576.8 ms for 1MiB inputs.
Instrumented 1MiB Unicode scanning peaked at 9.67MiB allocated memory; tracemalloc
overhead is excluded from the ordinary timing rows. That is not whole-process RSS.
Seven enabled-policy dense English 1MiB rows exceeded the 100,000-match budget
and raised a fixed error rather than returning a partial protection result.
Additional probes cover crossing overlaps, long shared prefixes, the 16MiB
input boundary and rejection above it. A 16MiB no-hit scan took about 2.44 seconds.
The production masking path still has its own transformation/mapping/output
budgets. No constant-time or arbitrary-size latency guarantee is claimed.

Reproduce with:

```sh
uv run python scripts/benchmark_domain_dictionaries.py --output /tmp/domain-performance.json --repeats 20
uv run python scripts/benchmark_domain_matrix.py --output /tmp/domain-matrix.json
```

## Protection and host checks

`privacy-harness-corrected/report.json` is the final-source 32-request loopback HTTP
regression: 57/66 sensitive occurrences fully protected, nine existing full
exposures, zero partial exposures, 30/117 overmasked public spans, 32/32 decoded
JSON roundtrips/replays, and session isolation/encrypted restart passing. Exact
text roundtrip is 31/32 because one restored JSON string has different whitespace.
It does not measure LLM comprehension. The earlier `privacy/` and `privacy-final/`
captures, including `privacy-release/`, retain their own source fingerprints.

Dictionary/API tests exercise all eight combinations, retained old aliases,
manual-rule precedence, Unicode normalization/hyphens/particles, crossing opaque
spans, persisted explicit Off, restart, active-request refusal, save failure,
missing data, auth/origin restrictions and actual outbound/restored payloads.

Runtime regressions separately verify:

- Issued aliases inside ASCII letter/underscore-derived names restore; complete
  unknown numbers remain errors. Alias 10 is never interpreted as alias 1 + `0`.
- A 320-message conversation adds one item without retransforming its old items;
  newly private input-relevant values and changed policies still invalidate cache.
- The 257th persisted conversation evicts idle state and resumes exact aliases
  and reasoning provenance. Active requests stay pinned, storage failure keeps
  live state, and cleanup authenticates expiry before deleting own files.

Installed wheel and sdist independently pass temporary install → inference/tool
roundtrip → stop → upgrade from 2.5.2 → restart → uninstall, preserving intervening
user edits. Native offline clients Claude Code 2.1.319 and Codex CLI 0.167.0 pass
four tests for each installed artifact. Package metadata, CLI, MCP application,
privacy-status and daemon health report 2.6.0. The built wheel's 53 Python files
and four dictionary JSON files exactly match the tested source bytes.

An additional **actual subscription** run on Windows passed four English/Korean
read/mask/restore tool-roundtrip tests using those native clients. It used a
temporary loopback gateway and synthetic files; user host settings were unchanged.
It does not certify real-account file edits, concurrent long reasoning or actual
account behavior on macOS/Linux. CI covers separate offline platform matrices.

The initial full suite passed 4,428 tests (287 skipped, coverage 88.76%). After the
runtime additions, a full run passed 4,456 tests and found one test double that
did not accept the new `pin` keyword; correcting that double preserved its
intended I/O-error assertion, and all 82 batch tests then passed. Subsequent
targeted gates passed 73 audit/Java, 35 connection/stream, and 56 evaluation tests
(two evaluation tests skipped). Final Ruff, mypy and JavaScript syntax checks
passed. CI runs the final committed matrix separately; these local runs do not
claim an already-green remote matrix.

Actual candidate interpretations and independent grades are documented in
[accuracy-20261109](../accuracy-20261109/README.md). Existing general-word private
names and missing task semantics remain limitations; no rejected experimental
disclosure policy is silently enabled by this release.
