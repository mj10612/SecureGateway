# Codex streamed response fix and live retest

SecureGateway 2.21.4 recognizes the existing SSE prefixes on Codex streaming
requests when the provider sends `text/plain` or omits Content-Type. It reads
at most six bytes to identify the prefix and then passes those bytes to the
existing streaming relay. Unrecognized responses still take the bounded
response path. The relay continues to enforce its input and output limits
and to save restored session state at completion.

The HTTP regression tests hold the upstream open until the client receives
the first nonempty restored text. Both the missing-header and plain-text
cases failed before the patch. Both passed after it, including restoration
of a masked email address and receipt of the terminal event.

The live retest used Codex CLI 0.172.0 and GPT-6.2-Sol on the same Windows
host as the earlier matrix. Two concurrent long sessions and one resumed
session ran on each route. All six returned the expected synthetic values.
Client result times are in seconds.

| Case | Direct | Gateway |
| --- | ---: | ---: |
| Two concurrent 15.7 KB prompts | 3.192, 3.137 | 6.263, 7.464 |
| Resumed session | 3.349 | 2.398 |

The live header probe confirmed that the upstream omitted Content-Type on all
three gateway requests. All three used the relay and produced nonempty text
before their final text. Time from first nonempty text parsed to first
restored text flushed was 0.199, 0.134 and 0.135 ms, respectively.
The earlier buffered probe observed a 466.779 ms gap on a different
fixture-read task. The two probes use different workloads, so the numbers
show how the response path changed without estimating a population-wide
latency improvement. [Live retest samples](codex-after.json)

The live retest ran on the 2.21.4 working tree based on
`e7ead1c9ca1fed0cc5ac3dde01661ef4915e2483`. Its report records that base
commit. The tested Git blob IDs were
`77bf315426ff5b1f4eabe7ab5bb7292f7b9bbfcf` for `gateway.py` and
`a98bec2b1cad7585177c8a2c85b487d294b073ce` for `gateway_stream.py`.

No multi-minute delay was reproduced on the measured workloads. The earlier
Codex fixture-read attempts did not verify tool round trips on either route.
The Claude Code pilot verified one Read round trip per route. Direct CLI
connection reuse and cancellation against a live provider were outside the
available measurements. The [expanded report](EXPANDED.md) contains the
standalone transport measurements and the loopback cancellation checks.
