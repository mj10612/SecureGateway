# Expanded live and loopback measurements for #355

On 2026-11-26 on Windows, we ran Claude Code 2.1.332 and Codex CLI 0.172.0 against
SecureGateway 2.21.3 at `e7ead1c9ca1fed0cc5ac3dde01661ef4915e2483` using
CPython 3.11.15. The report contains 18 live CLI invocations, including four
unsuccessful tasks or starts. All 14 successful invocations completed within
6.6 seconds at the CLI result boundary. The longest process ran 10.951 seconds
and failed its output check. This experiment did not reproduce minutes-long
latency.

## Live client timing

Times are seconds from subprocess launch to the CLI result event. The long
input consists of 200 synthetic inventory rows, about 15.7 KB. Resume asks for
a value supplied in the first turn. Each concurrency group starts two clients
together using independent new sessions. Codex uses long inputs in its
concurrency group, while Claude uses short inputs. The two routes within each
row use the same model, prompt(s) and CLI options where transport permits.

| Client and case | Direct | Gateway | Correct |
| --- | ---: | ---: | ---: |
| Claude Haiku 5.5, new long session | 1.157 | 1.861 | 2/2 |
| Claude Haiku 5.5, resume | 1.188 | 1.232 | 2/2 |
| Claude Haiku 5.5, two concurrent short sessions | 1.046, 1.102 | 1.200, 1.333 | 4/4 |
| Codex GPT-6.2-Sol, two concurrent long sessions | 3.156, 4.520 | 6.577, 4.631 | 4/4 |
| Codex GPT-6.2-Sol, resume after long input | 4.064 | 2.985 | 2/2 |
| Codex GPT-6.2-Sol, fixture-read tool task | 5.952 | 10.467 | 0/2 |

The initial Codex direct attempt using GPT-5.4-mini reported that the model was
unsupported. The initial gateway attempt with that model received HTTP 400
from the upstream. Both failures are retained. The six remaining planned
invocations used GPT-6.2-Sol with two concurrent long starts and one resume on
each route. Two follow-up invocations with a fixture-read task and additional
probes were added after discovering the buffered Codex response path. Neither
returned the expected value. The CLI JSONL exposed zero countable tool events
in both runs. Gateway metadata shows three inference requests in the gateway
run, which is insufficient by itself to verify which tool ran. The earlier
Claude pilot contains a verified live Read round trip on each route.

The initial bound was 16 launches, 60 seconds per launch and a 480-second
suite limit. The targeted follow-up added two launches under the same
per-launch limit. The harness checked a 220,000 reported-token ceiling after
each group. All reports together contain 143,756 reported tokens, with
Codex cache hits included in input tokens and Claude cache categories counted
separately. The two rejected starts did not report token usage. The runners
used existing subscription login and temporary gateway state. They did not
save response text, credentials or session IDs in the reports. The start and
resume measurements created disposable CLI sessions using the clients' session
storage.

Claude CLI first/last text uses nonempty text deltas. Codex CLI JSONL exposed
completed agent messages, so its `first_text_s` field is the first such
message and its `last_text_s` field is the last. The live samples are too
small to establish a general p95 or a consistent gateway overhead.
[Initial matrix and rejected starts](expanded-live.json) ·
[Six Codex workload results](expanded-codex.json) ·
[Codex tool task and probes](expanded-codex-tool.json)

## Gateway stage and transport measurements

Across the ten HTTP 200 gateway inference requests, session lock wait rounded
to 0 ms in all samples. Other observed values are in milliseconds.

| Metric | n | Median | Range |
| --- | ---: | ---: | ---: |
| Input masking | 10 | 182.87 | 1.15–1336.64 |
| Upstream headers, including connect and provider wait | 10 | 790.585 | 600.83–1102.12 |
| Combined HTTPS connect | 10 | 25.897 | 10.351–78.934 |
| Encrypted snapshot save | 10 | 10.44 | 6.53–86.46 |
| Audit begin | 10 | 8.108 | 6.478–31.234 |
| Audit finish | 10 | 8.285 | 5.304–8.842 |
| Claude first nonempty upstream text, parsed since receipt of handler request | 4 | 725.026 | 635.030–1216.598 |
| Claude first restored text flushed, same origin | 4 | 725.124 | 635.127–1244.125 |
| Claude streaming restore feed and instrumentation | 4 | 0.916 | 0.870–2.360 |
| Codex buffered restoration | 6 | 20.365 | 18.15–22.60 |

Gateway startup including dictionary preload took 585–651 ms across the
three runs. The gateway and Python harness shared a process, with sampled
peak RSS of 179.5–185.3 MiB. The measurement excludes CLI processes. Eight
additional gateway POSTs in the successful Claude invocations returned
local HTTP 400. The probes did not retain endpoint detail or error bodies
for those requests. The main inference request succeeded in each invocation.

Each of the ten successful gateway inference requests used one new HTTPS
connection. Direct CLI connection reuse and handshake counts were not
observable with this harness. Three standalone IPv4 connections per official
host measured system DNS lookup, TCP and TLS separately. These are fresh
sockets but the OS DNS cache was neither cleared nor controlled. Values are
milliseconds, shown as median and range.

| Host | DNS | TCP | TLS |
| --- | ---: | ---: | ---: |
| api.anthropic.com | 0.362 (0.314–8.342) | 12.602 (2.763–13.483) | 7.511 (7.431–8.207) |
| chatgpt.com | 0.411 (0.345–2.610) | 3.195 (2.949–14.954) | 7.517 (6.877–7.970) |

Probes recorded numeric timings and a small allowlist of media types.
Instrumentation timestamps mark parser or writer boundaries in the Python
server and include observation overhead. [Transport samples](transport.json)

## Codex response buffering reproduced

The targeted Codex gateway run sent `stream: true`. The HTTP header
parser classified all three upstream responses as `text/plain`, which is
also Python's default when the header is missing. The live probe at the
time did not distinguish those two cases. The gateway's current streaming
branch requires an explicit SSE media type, so it read the full upstream
body, restored it and wrote it to the client as one buffered response. On the
request where the chunk probe observed a complete nonempty text event, the
first text was visible to the probe at **1690.508 ms** after handler entry and
the buffered body was written at **2157.287 ms**, a **466.779 ms** gap.
The other two requests in that run yielded no timestamp from the text probe.

A controlled loopback check sent the same two SSE text deltas with a 750 ms
gap and varied only the upstream content type. The client reconstructed the
exact same output in all six trials. With `text/event-stream`, median time to
first text was **14.352 ms** across three runs (2.355–276.707 ms). With
`text/plain`, it was **755.110 ms** across three runs (754.798–767.390 ms).
The first `text/event-stream` sample included initial session setup. The
observed buffering can delay first text until the stream finishes. The
experiment did not establish that it caused the reported multi-minute delay.
[Six controlled samples](mime-loopback.json)

## Slow upstream and cancellation

The existing synthetic loopback benchmark exercised English, Korean and mixed
prompts in 2- and 24-turn conversations, with concurrency 1, 2 and 4 and a
fixed 2 ms delay per SSE event. It returned all 180 matched request pairs.
For mixed 2-turn conversations at concurrency 4, the client completion
gateway-minus-direct median/p95/max was 210.342/310.205/310.205 ms (n=16).
For mixed 24-turn conversations at concurrency 1, the corresponding values
were 106.434/155.110/166.524 ms (n=48). Counts include repeated turns within
conversations. The loopback mock tests the gateway locally and repeats known
events, while the live measurements cover real upstream responses.
[Loopback distributions and RSS](expanded-loopback.json)

Five reproductions of the existing idle-upstream disconnect test used a
50 ms heartbeat. From observed client write failure to relay return,
median latency was 0.487 ms (0.429–0.652 ms). The test verified that admission
was released before the synthetic upstream finished. Sixty-five related
tests passed, covering heartbeat, disconnect, session capacity, audit recovery
and benchmark behavior, plus response restoration and encrypted session
restart. Provider-side disconnect timing was exercised with
the loopback fixture. [Disconnect samples](cancellation.json)

## Reproduce

```powershell
$probe = 'docs/evaluations/issue355-claude-live/matrix.py'
uv run --locked --all-extras python $probe --transport --output transport-replay.json
uv run --locked --all-extras python $probe --live --provider claude --output claude-replay.json
uv run --locked --all-extras python $probe --live --provider codex --grouped --output codex-replay.json
uv run --locked --all-extras python $probe --live --provider codex --codex-tool --output codex-tool-replay.json
uv run --locked --all-extras python scripts/benchmark_gateway_latency.py --compare-direct --repeat 2 --languages en ko mixed --lengths short long --concurrency 1 2 4 --concurrency-language mixed --concurrency-length short --upstream-delay-ms 2 --output loopback-replay.json
```

The current runner uses the supported Codex model, a reduced tool catalog in
text-only cases, and the additional response probes. It now records missing
content types separately. These options differ from the initial
unsupported-model attempts in `expanded-live.json`.
