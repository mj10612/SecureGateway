# Issue 332: gateway stream resource cleanup

## Scope

Narrow follow-up for `src/secure_gateway/gateway_stream.py` cleanup/diagnostics.
The coordinator integrated the reviewed narrow follow-up as version 2.7.4,
including the required CLI/MCP/package version metadata.

## Reproduced / proven resource lifetime paths

No new stream resource leak was reproduced as a standalone failing case beyond the
existing bounded-cancellation/ownership risk already addressed by fix 46d031f. The
existing ownership transfer path was verified and cleanup diagnostics were improved.

Verified/proven paths:

1. **Reader-owned buffered-file handoff (detached, missed wakeup model)**: when
   cancellation observes the reader inside `upstream.read1()` and socket wakeup may
   be missed, `relay_stream` detaches `upstream.fp` and hands it to
   `reader_state["owned_file"]`. The reader thread closes that file in its `finally`.
   The owner response close does not wait on the buffered-file lock and does not
   close the detached file again. `tests/test_stream_edges.py` preserves the 46d031f
   regression; `tests/test_stream_resources.py` adds explicit close-count proof.
2. **Ordinary upstream close**: non-detached EOF, reader exception, client disconnect,
   and output-budget paths close the upstream handle exactly once.
3. **Bounded completion**: wakeable/non-detached paths join the reader worker with a
   bounded timeout. Deliberately unwakeable detached reads remain bounded only where
   the OS permits wakeup/timeout expiry; the relay and owner do not block on the
   buffered-file lock in that modeled case.
4. **Cleanup diagnostics**: fixed-category `logging` warnings are emitted for cleanup
   failures (`reader_owned_file_close_failed`, `raw_socket_shutdown_failed`,
   `raw_stream_interrupt_close_failed`, `upstream_close_failed`) without exception
   text, file contents, headers, payloads, or alias maps.

## Actual proof and limits

- **Regression/unit proof**: `tests/test_stream_edges.py` (14 tests, unchanged) plus
  `tests/test_stream_resources.py` (10 tests) cover exactly-once close for detached
  reader-owned and ordinary upstream handles, reader exceptions, EOF, client disconnect,
  output-budget errors, no private exception text in logs, and wakeable/unwakeable
  modeled completion.
- **OS lifetime stress check**: bounded test uses real OS pipes/descriptors (`os.pipe`,
  `os.fdopen`, `os.fstat` after close) over 40 relay iterations and asserts the
  upstream close path releases the actual descriptor. This is lifecycle evidence, not
  a process-wide handle-count leak detector.
- **Primary-failure preservation**: if a stream body failure is already propagating,
  `upstream.close()` cleanup errors are logged but not re-raised, avoiding hiding the
  primary failure. When there is no primary failure and the raw stream was not
  intentionally interrupted, existing `upstream.close()` `OSError`/`ValueError`
  propagation is preserved under the prior contract. Cleanup failures are therefore
  not universally non-fatal.
- **Limitations**: a truly unwakeable kernel `recv` cannot be forcibly terminated from
  userspace; detached reader threads may persist until OS wakeup/socket timeout expiry.
  The fix avoids main-thread deadlock and preserves explicit ownership. Real macOS
  runner behavior was not exercised in this local Windows run; the missed-wakeup case
  is covered by the deliberate unwakeable model plus preserved existing regression.

## Reviewed source paths

- `src/secure_gateway/gateway_stream.py`
- `tests/test_stream_resources.py`
- `docs/research/issue332-stream-cleanup.md`

## Coordinator verification

The combined validation, CLI, hooks, parser, stream, upstream-context and MCP
suite passed **87 tests** on Windows / Python 3.14.7. This includes 14 stream-edge,
10 resource-lifetime and 6 upstream-context tests. Ruff and mypy pass, and CLI,
module, installed package metadata, MCP application and privacy-status agree on
**2.7.4**. These are local focused gates; the new remote CI matrix is separate.

The two selected cleanup regressions fail against released 2.7.2: missing fixed-category
cleanup diagnostics and a cleanup OSError hiding the primary BrokenPipeError.
They pass in the combined final suite above. No new standalone descriptor leak
was claimed from these negative controls.
