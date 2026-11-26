# Claude Code direct and gateway pilot for #355

The follow-up measured both CLIs, long prompts, session resume, concurrency,
transport, audit and stream timing. See [Expanded measurement](EXPANDED.md).

The live pilot on 2026-11-26 produced one successful matched pair. Both paths
read the synthetic fixture and returned the expected value. The second gateway
attempt returned without calling Read, so the pilot stopped and the final direct
attempt was skipped. No invocation in this small workload took minutes.

| Attempt | Path | First text (s) | Client result (s) | Process exit (s) | CLI API time (s) | Read calls/results | Task |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Direct | 2.660 | 2.682 | 2.720 | 1.784 | 1/1 | Pass |
| 2 | Gateway | 5.188 | 5.203 | 5.238 | 4.677 | 1/1 | Pass |
| 3 | Gateway | 3.234 | 3.672 | 3.708 | 3.160 | 0/0 | Fail |
| 4 | Direct | | | | | | Skipped |

The successful gateway run took 2.528 seconds longer to emit first text and
2.521 seconds longer to emit the result. This is one paired observation. The
CLI reported different cache-token and output-token counts between paths, and
the gateway forwards a masked payload and adds a model instruction. The timing
difference includes those workload differences and upstream variability, so it
cannot be attributed entirely to gateway overhead.

The successful gateway attempt recorded two inference requests. Their input
masking took 481.61 and 78.94 ms, upstream headers took 2190.49 and 662.44 ms,
and snapshot saving took 94.36 and 10.59 ms. The measured session lock wait
rounded to zero in all gateway requests. Header timing includes upstream wait
along with transport and cannot distinguish those components. Gateway
`first_event_ms` measures the first relayed event, which may be metadata. The
first-text column measures the first nonempty text delta received from the
CLI; it is not the gateway's inbound first-text time. Per-invocation counts,
client times and gateway stage records are in [samples.json](samples.json).

## Setup and limits

- Windows, CPython 3.11.15, Claude Code 2.1.332 and SecureGateway 2.21.3
  at `e7ead1c9ca1fed0cc5ac3dde01661ef4915e2483`. The CLI resolved the
  `haiku` alias to `claude-haiku-5-5` in all three attempts.
- One independent CLI invocation at a time with the existing subscription
  login. Each used the same temporary working directory, synthetic fixture,
  prompt, system prompt and Read tool selection. CLI session persistence was
  disabled and the local gateway used temporary state, default masking,
  metadata-only audit and its standard Anthropic upstream. Its dictionary
  was preloaded before starting the timed invocations.
- Planned order was direct, gateway, gateway, direct. The limits were four
  invocations, 45 seconds and three CLI turns per invocation, plus a CLI budget
  cap of USD 0.15 per invocation. The CLI budget cap is not a billed-cost
  measurement. The pilot used three invocations and the CLI reported five
  turns in total. The stop rule ended the pilot after the first failed task,
  without a retry or a replacement sample.
- The report retains timing and token counts, tool counts, and pass/fail
  outcomes. It does not retain prompt/response capture, credential values,
  local paths, session IDs or alias mappings.

From the repository root, an operator can explicitly repeat the live pilot:

```powershell
uv run --locked --all-extras python docs/evaluations/issue355-claude-live/measure.py
```

The replay uses the same fixture and route sequence and also checks that exactly
one Read call and one successful tool result are present. It makes real model
calls on the current Claude Code subscription and prints only structured
measurements.

## What remains open

The unsuccessful run had CLI status `success` but did not complete the task.
An offline reconstruction of the Anthropic request confirmed that both the
filename and output marker are masked, while the Read tool name and the
surrounding instructions are preserved. In one gateway session the synthetic
request transformed identically on repeat and the prompt round-tripped exactly.
This verifies deterministic transformation for that reconstruction, without
establishing why the live model skipped Read.

Only a short English task and one local session at a time were exercised. No
distribution or p95 is reported from one successful pair. Codex, long or
resumed sessions, concurrent requests, DNS/TLS decomposition, audit timing,
and separate timestamps for the gateway's inbound first text were unmeasured.
The pilot narrows the conditions under which the reported multi-minute delay
was absent. It does not establish its cause or close #355.
