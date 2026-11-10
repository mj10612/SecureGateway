# ADR 0003: Privacy-safe diagnostics with fixed categories and no exception text

- Status: Accepted
- Date: 2026-11-10 (reconstructed)
- Sources: `docs/ARCHITECTURE.md`, `docs/GATEWAY.md`, gateway/audit/stream error-handling code (e.g. `gateway.py` diagnostic logging, `gateway_errors.py`, `gateway_audit.py`).

## Context

Operational failures need to be diagnosable, but logs and public error responses can leak prompts, credentials, file paths, original private values, or upstream details. The gateway handles sensitive request content and local session state.

## Decision

Diagnostics use fixed category strings and exception/type-level information only. Public request errors map to stable codes and guidance; raw exception text, request bodies, tokens, and original mappings are not returned or logged. Optional logging must not change error responses.

## Consequences

- Debugging relies on stable categories, counters, and authenticated local diagnostics rather than raw payload dumps.
- Tests and code review must enforce the no-sensitive-data logging rule.
- Some failures are less immediately descriptive externally, by design, to preserve the privacy boundary.
