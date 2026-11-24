# Gateway performance measurement (issues #355 and #356)

This page reports **gateway-side** time only. Every number below comes from
synthetic data, a loopback mock upstream that answers immediately, and no real
model, account, DNS, TLS or Internet path. Model inference, provider queueing,
network latency and client-side (Claude Code/Codex) work are **not measured**.

## How to reproduce

```bash
# Per-stage HTTP benchmark: short/medium/long conversations (history resent on
# every turn), en/ko/mixed prose with code blocks, tool_use/tool_result JSON,
# split SSE responses with a split tool-argument stream, 1/2/4 concurrent sessions.
PYTHONHASHSEED=0 uv run --locked --all-extras python scripts/benchmark_gateway_latency.py --repeat 3 --output report.json

# Compare matched requests through the gateway and directly to the loopback mock.
uv run --locked --all-extras python scripts/benchmark_gateway_latency.py --compare-direct --repeat 4 --output paired.json

# cProfile of input masking on the long (24-turn) conversation, in process.
# Also reports an output digest and a paired memo-vs-full-scan comparison.
PYTHONHASHSEED=0 uv run --locked --all-extras python scripts/benchmark_gateway_latency.py --profile --repeat 8 \
    --profile-language mixed [--mask-rules 64]
```

The report records the code SHA, package version, Python version, OS, CPU and
memory size. Each request is checked: the client must receive exactly the
original synthetic text back after restoration, otherwise the run fails.

From 2.21.2, p95 uses the nearest-rank method. For `n` measured samples it
selects the `ceil(0.95 × n)`th value in ascending order. Missing samples
are excluded from the count. Historical results below retain their original
calculation.

Stages per request (median/p95/max with sample counts in the JSON report):

| Stage | Source |
| --- | --- |
| `lock_wait` | session lock wait before input masking (gateway timing) |
| `mask` | `GatewaySession.request`: validation and input masking |
| `serialize` | `strict_json_dumps` of the masked request |
| `upstream_send` | connect, send, mock upstream response headers |
| `first_event` | stream relay start to the first restored event written |
| `restore` | `EventRestorer.feed/finish`: text restoration and tool-argument groups |
| `save` | encrypted session snapshot save |
| `audit_begin/finish` | metadata audit ledger writes (separate samples) |
| `client_first_content` / `client_total` | client start to first nonempty `text_delta` / stream end |

From 2.20.1, an empty text delta does not count as first content, and a measured
zero-millisecond delay remains zero instead of being discarded as missing. SSE
comments and non-text lifecycle events also do not count as content. This corrects
the benchmark's measurement; it does not change gateway streaming or demonstrate
a latency improvement. Historical results below are preserved, not recomputed.

Not measured: real upstream connection reuse, TLS, DNS, model time, heartbeat
gaps of a slow model, client cancellation, process start and Claude Code/Codex
internal time. `--upstream-delay-ms` adds a fixed per-event mock delay only.

From 2.21.0, `--compare-direct` runs each synthetic workload through the gateway
and directly against the same loopback mock. The paths run one at a time at the
same concurrency and alternate which path goes first on each repetition. Use an
even repeat count to balance the order. Both paths receive the same generated
client payloads and must return the expected synthetic text. The mock receives
the gateway's masked request on one path and the original synthetic request on
the other. Masking can change the size and number of SSE chunks, especially with
`--upstream-delay-ms`.

Each workload's `direct` section reports first nonempty text and completion
times, throughput, and gateway-minus-direct differences matched by worker,
repetition and turn. Positive differences mean the gateway path took longer.
From 2.21.1, `wall_s` sums the time from worker setup through worker completion
in each repetition for the given path. `throughput_rps` divides request count
by that time. Gateway timing records collected after the workers finish still
contribute to the stage summaries, outside the throughput measurement.
The process-level RSS sample covers both paths in this mode. This comparison
measures the loopback setup and cannot quantify real provider, network or host
client latency.

## Environment of the numbers below

- AMD Ryzen 9 5900X (12 cores/24 threads), Windows 11 Pro 10.0.26200, CPython 3.14.7.
- Before: `bb074bb` (2.15.0). After: this change on the same base, same machine and workloads;
  re-checked after rebasing onto 2.16.1 (released as 2.16.2), see the end of this page.
- The machine was shared with other jobs (about 77% CPU load reported during the
  runs). Absolute wall-clock numbers vary by up to about 2x between identical runs;
  before/after conclusions below rely on interleaved runs and same-process paired
  comparisons, not on single wall-clock runs.

## Where the gateway spends time (HTTP benchmark, mock upstream)

Medians (ms) of two interleaved rounds each, `--repeat 3`; n = requests per row and round.

| Workload | n | mask | save | restore | upstream_send | gateway_total | client_first_content | client_total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| en short, 1 session (before) | 6 | 16-18 | 56-129 | 7.6 | 1.7-1.8 | 118-175 | 49-89 | 142-262 |
| mixed long (24 turns), 1 session (before) | 72 | 67-82 | 18-39 | 7-8 | 2.3-2.7 | 159-176 | 151-156 | 232-275 |
| mixed long, 1 session (after) | 72 | 59-68 | 37-39 | 7 | 1.7-2.1 | 145-161 | 141-148 | 251-261 |
| mixed medium, 2 sessions (before/after) | 48 | 53-72 / 50-54 | 22-58 / 22-57 | 8-9 | 2.5-3.9 / 2.1-2.6 | 192-239 / 173-180 | 133-143 / 116-119 | 307-321 / 269-289 |
| mixed medium, 4 sessions (before/after) | 96 | 55-67 / 58-62 | 54-75 / 68-69 | 8-10 | 3.1-5.8 / 3.9-4.2 | 223-289 / 250-269 | 226-246 / 220-233 | 561-574 / 532-562 |

Other measured values:

- `lock_wait` was 0.0 ms in every row: concurrent sessions use separate session
  locks and did not wait for each other. With 4 sessions the per-request time
  still roughly doubles because masking is CPU-bound Python work sharing one
  interpreter (GIL); throughput stayed at about 6-7 requests/s.
- `serialize` was 0.04-0.26 ms; `first_event` about 1 ms (p95 up to 25 ms with
  4 sessions).
- Metadata audit writes (SQLite ledger) are **not** inside `gateway_total`:
  `audit_begin` runs before masking and `audit_finish` after the stream. With one
  session each took 12-57 ms (median), p95 up to 155 ms; with 4 sessions the
  medians were 97-135 ms and p95 up to 385 ms. `audit_begin` therefore adds
  directly to the time to first content.
- Peak RSS growth during a workload was 0.3-7.6 MB for one session and
  16-18 MB with 4 sessions.
- Gateway start with dictionary preload took 0.8-1.4 s; the first (cold)
  request took 0.4-0.7 s (270-424 ms masking, 83-177 ms first snapshot save).

So, per request, the gateway adds roughly 0.15-0.4 s with one session and up to
about 0.5-1 s (p95 above 1 s) with four concurrent sessions on this loaded
machine. The largest gateway stages are input masking, the encrypted snapshot
save and the two audit ledger writes.
**These numbers do not explain a task taking several minutes** (#355): a task
of tens of model round trips would accumulate seconds, not minutes, of gateway
time. That report must be attributed with real host/model measurements, which
this benchmark does not perform.

## Masking profile (cProfile, long mixed conversation, 24 requests)

Before this change (2.15.0, under the profiler, total 4.64 s):

| Function | cumulative share | note |
| --- | ---: | --- |
| `_mask_prose` (cache misses only) | 70% | includes Korean morphology below |
| `gateway_morphology.is_ordinary_form` | 31% | Korean stem/ending candidates |
| `GatewaySession._mask_cache_key` | 17% | full embedded `originals_in` scan for every cache lookup (4,796 calls; 4,324 were cache hits) |
| `MaskingEngine._chunks` regex compile | 9% | one pattern per distinct term set |
| `SessionMappings.originals_in` automaton rebuild | about 8% (unprofiled: 0.13-0.15 s of 1.6-2.0 s) | 88 rebuilds after new mappings |
| `_request` forced-rule protocol check (64 rules) | 5% | rules re-normalized for every string |
| `deepcopy`, request JSON serialization | below 1% | not in the top functions |

## Changes made (#356 candidates 1 and 3)

1. **Dependency-scan memo for the mask cache key** (`SessionMappings.embedded_originals`).
   The cache key still contains the same digest of the originals embedded in the
   text. The store memoizes that set per text: it is exact while no mapping is
   removed or replaced (any `__delitem__`, `pop`, `popitem`, `clear` or replacing
   `__setitem__` discards all entries), and originals added since the entry was
   computed are checked with a substring test, which is what embedded matching
   (no boundary rule) means. The memo is per store, so per conversation; it is
   bounded (4,096 entries, 4 Mi characters, texts above 1 Mi characters are not
   memoized) and dropped with `clear()`/reset, like the existing mask cache.
2. **Forced-rule pattern cache**: the compiled NFC/NFD pattern for the configured
   rule tuple is reused (`lru_cache`, 8 entries). Per-call schema terms are
   never put in this process-wide cache.
3. **Rules normalized once per request** in the forced-rule protocol-field check.

Results, same machine, interleaved or same-process paired:

- `_mask_cache_key` time per 24-turn conversation, same process, alternating
  order, 8 conversations each: mixed 231 to 121 ms, Korean 236 to 138 ms,
  English 221 to 113 ms, mixed with 64 rules 312 to 172 ms (medians).
- Whole input masking per conversation in the same paired runs: mixed 1,286 to
  1,172 ms (-9%), Korean 1,395 to 1,309 ms (-6%), English 939 to 829 ms (-12%),
  64 rules 1,631 to 1,557 ms (-5%).
- Forced-rule protocol check share under the profiler with 64 rules: about 5%
  before, about 3% after.
- In the HTTP benchmark the change is within the machine's run-to-run noise.
- Output is byte-identical: with `PYTHONHASHSEED=0` and seeded numeric aliases,
  the digest of every masked request plus the final alias table is the same
  before and after for en, ko, mixed and mixed-with-64-rules long conversations.

## Candidates not changed, with the measured reason

- **(2) merge `_mask_prose` with engine chunking**: the duplicated scan is not
  the dominant part of `_mask_prose`; the regex compile in `_chunks` is about 9%
  and Python's regex cache already hits where the term set repeats. Merging
  would change forced-span/possessive/particle handling and could not be shown
  identical with low risk.
- **(4) incremental automaton updates**: rebuilds cost 0.13-0.15 s per 24-turn
  conversation (about 8%); not dominant, and the memo already avoids most scans.
- **(5) `deepcopy`/JSON**: request serialization is 0.04-0.26 ms and deepcopy
  does not appear among the top functions; nothing to gain.
- Not part of #356 but larger: Korean morphology (`is_ordinary_form`, up to 45%
  of masking for Korean text), the encrypted snapshot `save` (median 14-129 ms
  per request, p95 up to 236 ms with 4 sessions) and the per-request audit
  writes (12-135 ms median each). These belong to #355/#352 follow-up work. A process-wide morphology cache would keep prose words
  in memory beyond a session reset, so it needs a retention decision first.

## Re-check on the 2.16.1 base (after #366 feature flags and #363 forced numeric binding)

The hot path changed in 2.16.0 (per-session feature flags) and 2.16.1 (forced
numeric/date binding, outgoing leak check), so the comparison was repeated:
before = `f36be21` (2.16.1), after = this change rebased on it (2.16.2), default
features (all off), `--repeat 6`, two interleaved rounds per workload. The tool
calls now carry a JSON number (`timeout: 30000`), and the 64-rule workload
includes digit-bearing rules (`30000`, `INV-1`, `2`, `1024`): a JSON-number
rule, rules inside prose and tool output, and a value equal to a protocol number.

| Workload (24 turns) | conversation median before / after (ms) | `_mask_cache_key` per conversation, paired full scan / memo (ms) | masking per conversation, paired full scan / memo (ms) | output digest |
| --- | ---: | ---: | ---: | --- |
| en | 873 / 775 | 200-203 / 101 | 859-862 / 757-768 | identical |
| ko | 1,249 / 1,146 | 196-205 / 111-117 | 1,199-1,246 / 1,114-1,139 | identical |
| mixed | 1,184 / 1,070 | 205-208 / 112 | 1,144-1,155 / 1,070-1,120 | identical |
| mixed, 64 rules incl. numeric | 1,319 / 1,184 | 211-219 / 136-138 | 1,228-1,277 / 1,157-1,215 | identical |

The digest covers every masked request and the final alias table. With
`PYTHONHASHSEED=0` and seeded numeric aliases it is the same for 2.16.1 and
this change.
`tests/test_hotpath_356.py` also replays a resent history with each #354 feature
enabled alone and all together, comparing the memoized path with the full scan.
It also checks that #363 digit rules give identical output and aliases with
and without the pattern cache.


## Korean morphology within-fragment memo (#355, 2.20.3)

The gateway memoizes public and private Korean morphology decisions separately
within a single prose fragment, up to 4,096 entries per decision type. Entries
are discarded after that fragment; they are not shared across requests or
sessions. Private-rule and existing-mapping checks still take precedence. This
does not change the provider or model and does not cache whole conversations.

On 2026-11-20, CPython 3.11.15 on Linux x86-64 (6 logical CPUs, about 8 GiB
RAM), the existing `benchmark_gateway_latency.py --profile --profile-language
ko --profile-length medium --repeat 8` ran against base commit `9a1daf8` and
this change in base/new/new/base order, each with `PYTHONHASHSEED=0`, eight
synthetic turns, and no forced rules. Per-run median conversation times in ms:

| Order | Base | New | New | Base |
| --- | ---: | ---: | ---: | ---: |
| Median ms | 546.412 | 581.137 | 489.421 | 575.669 |
| Total request-thread CPU ms, 8 runs | 4637.85 | 4712.92 | 4078.42 | 4797.84 |

Under profiling, `is_ordinary_form` calls were 872 per base run and 677 per new
run; the masked-output digest was identical in all four runs. Timing varies
substantially and this small synthetic sample does not establish a reliable
real-world speedup or explain multi-minute delays. It excludes actual client,
network and model inference latency. #355 remains open for the remaining
end-to-end, memory, concurrency and real-host measurements.
