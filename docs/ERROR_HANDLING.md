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
