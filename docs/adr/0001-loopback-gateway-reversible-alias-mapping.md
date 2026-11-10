# ADR 0001: Loopback gateway with reversible alias mapping

- Status: Accepted
- Date: 2026-11-10 (reconstructed)
- Sources: `docs/ARCHITECTURE.md`, `docs/GATEWAY.md`, README gateway overview, gateway implementation history in `src/secure_gateway/gateway.py`.

## Context

Subscription CLI traffic contains confidential text and code but must continue to use the CLI's existing authentication flow. Protection needs to cover request masking and local restoration without requiring provider-side changes or API-key substitution.

## Decision

Use an authenticated local loopback gateway that masks configured inference requests before forwarding and restores responses/local tool arguments before the CLI consumes them. Sensitive values are replaced with reversible session-local aliases (mappings) so the model can reason over stable opaque references while the trusted host restores originals.

## Consequences

- The trust boundary stays local: only masked payloads cross to the upstream provider path.
- Alias stability and restoration correctness become core invariants; unknown/altered aliases must fail safely.
- Unsupported binary/remote payloads and some client traffic remain outside the protection boundary and must be documented or blocked explicitly.
