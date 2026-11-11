# Error handling and logging

`SecureGatewayError` is the base for application errors. `ConfigurationError`
represents invalid configuration or request validation and also inherits
`ValueError` for existing callers. `ResourceError`, `ProcessError`, and
`StreamError` represent resource, child process, and stream failures. Existing
`GatewayRequestError` retains its public import path and `ValueError` contract.
Existing custom exceptions inherit from the hierarchy while retaining their original base classes. Built-in exceptions remain in use.
HTTP boundaries retain their existing status codes and sanitized bodies; the CLI
translates uncaught hierarchy errors to a fixed Click error.

Logging is configured only by gateway process entry points. Importing the
library adds a `NullHandler` and leaves application handlers alone. Set
`SECURE_GATEWAY_LOG_LEVEL` to DEBUG, INFO, WARNING, ERROR or CRITICAL; the
fallback is WARNING. Events use a timestamp, level, logger name and message.
Libraries may configure the package logger themselves. The configuration helper
accepts a stream or file; it does not provide rotation, concurrent file handling,
or permission hardening, so file logging requires operator management.

Messages must contain only fixed event/category strings and bounded safe scalar
metadata such as counts, durations, port, status class or exception type name.
Never log exception text, traceback, request content, credentials, aliases,
headers or paths. Use `log_failure(logger, "fixed_event", exc)` at a failure
boundary; it emits only the event and exception type. Avoid recording the same
failure at multiple layers. Use DEBUG for bounded diagnostics, INFO for normal
operation, WARNING for recoverable faults, ERROR for failed operations and
CRITICAL for process-threatening conditions. The existing gateway diagnostic
counters and fixed categories remain the source for snapshot and upstream
recovery events. CLI `click.echo` and intentional prints in CLI and
`private_arithmetic.py` are user-facing program output, not logs.

## Handler and invariant markers

Silent exception handlers (`except ...: pass`) are classified into three forms:
- `intentional`: The exception is expected control flow (such as `FileExistsError` on atomic file creation, optional fallback vocabulary, best-effort close during teardown, or diagnostic logging handlers that must not raise or recurse). Such handlers must narrow the exception type where feasible and include an `# intentional: <reason>` comment on the handler line or immediately preceding line. AST enforcement (`tests/test_silent_handlers_328.py`) forbids unannotated single-`pass` handlers.
- `observable`: A failure that should be reported without interrupting best-effort control flow. Reported using `log_failure(logger, "<fixed_event>", exc)` or the subsystem's bounded diagnostic counter.
- `wrong`: Swallowing hides a real error; must propagate or be converted to a `SecureGatewayError` subclass.

`assert` statements in `src/` must not be used for external input validation (which must use explicit checks surviving `python -O`). Internal invariants and type-narrowing assertions must carry an `# invariant: <reason>` comment, enforced by AST testing (`tests/test_assert_invariants_337.py`).
