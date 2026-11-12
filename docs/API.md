# Public API Reference

This document describes the supported public Python surface, CLI entry points, and MCP tools for **SecureGateway 2.16.0**. It is checked by `tests/test_api_doc_331.py` against the real package exports.

## Package exports (`secure_gateway.__all__`)

The package root exports the primary local masking/restoration types and helpers:

- `MaskMode` ??masking policy enum (`content_words`, `entities_only`, `uncommon_words`, `code_aware`, `aggressive`).
- `SurrogateStrategy` ??surrogate representation enum (`bracket`, `unicode`, `pseudoword`, `hash`).
- `TokenType` ??token classification enum used in mappings.
- `TokenMapping` ??immutable mapping record between an original value and surrogate.
- `MaskResult` ??result of a mask operation (masked text, counters, policy metadata).
- `UnmaskResult` ??result of restoration (unmasked text, restored counts, unmatched surrogates).
- `SessionStats` ??sanitized session metrics (no original values or mapping entries).
- `MaskingEngine` ??core engine for masking/restoring text and code with session stores.
- `SessionVault` ??registry for bounded, expiring `PrivacySession` instances.
- `LocalPrivacyClient` ??trusted local boundary that masks before a provider callback and restores after.

```python
from secure_gateway import LocalPrivacyClient, MaskMode

def provider(masked_payload: str) -> str:
    return masked_payload

with LocalPrivacyClient() as client:
    result = client.request("Patient John Doe received 50mg.", provider, mode=MaskMode.CONTENT_WORDS)
    print(result.unmasked_text)
```

## Core Python classes

### `LocalPrivacyClient`

`LocalPrivacyClient(max_sessions=1000, mapping_limit=100_000, max_input_bytes=16*1024*1024, max_restore_input_bytes=16*1024*1024, max_restore_output_bytes=16*1024*1024, max_mapping_bytes=DEFAULT_MAPPING_BYTES, max_snapshot_bytes=DEFAULT_SNAPSHOT_BYTES)`

- `request(text, provider, mode=MaskMode.CONTENT_WORDS, strategy=SurrogateStrategy.BRACKET, sensitive_terms=None, language="auto", normalize_particles=False, mask_numbers=False, code_language="auto", sql_dialect="sqlite", common_vocabulary=None) -> UnmaskResult` ??masks locally, passes only masked text to `provider`, restores the response locally.
- `close()` ??releases vault/session references. Use as a context manager.

### `MaskingEngine`

`MaskingEngine(...)` (see source for budget/restore limits) provides `mask_text(...)`, `mask_code(...)`, and `unmask(...)` for trusted local use. Engine operations expect the session/generator/store locking contract documented in `docs/ARCHITECTURE.md`.

```python
from secure_gateway import MaskingEngine, MaskMode, SurrogateStrategy
from secure_gateway.session import PrivacySession

engine = MaskingEngine()
session = PrivacySession("example", mode=MaskMode.CONTENT_WORDS, strategy=SurrogateStrategy.BRACKET)
masked = engine.mask_text("Alice from Acme", session.session_id, session.generator, session.forward_store, session.reverse_store)
restored = engine.unmask(masked.masked_text, session.session_id, session.reverse_store)
```

### `SessionVault` and `PrivacySession`

`SessionVault` manages bounded sessions with TTL cleanup. `PrivacySession` holds forward/reverse stores and generator state; custom mutations require `session.operation()`.

```python
from secure_gateway import SessionVault, MaskMode, SurrogateStrategy

vault = SessionVault(default_ttl=3600)
session = vault.create(mode=MaskMode.CONTENT_WORDS, strategy=SurrogateStrategy.BRACKET)
stats = session.get_stats()
vault.clear_session(session.session_id)
vault.close()
```

### `GatewaySession`

`GatewaySession(...)` (from `secure_gateway.gateway`) is the per-conversation masking/restoration state used by the loopback gateway. It is not re-exported from the package root; import it from `secure_gateway.gateway` when integrating with gateway internals.

```python
from secure_gateway.gateway import GatewaySession

session = GatewaySession()
masked = session.mask("Review private_symbol_1 handling")
restored = session.restore(masked)
```

Opt-in masking features (#354) are passed per session as an immutable
`GatewayFeatures` value from `secure_gateway.gateway_features`; the default
enables nothing. Sessions with different feature sets can run in one process
at the same time. See "Opt-in masking features" in `docs/GATEWAY.md`.

```python
from secure_gateway.gateway import GatewaySession
from secure_gateway.gateway_features import GatewayFeatures

session = GatewaySession(features=GatewayFeatures(ko_conjugation_split=True, contextual_name_spans=True))
```

## CLI commands (`secure-gateway`)

The CLI is exposed as `secure-gateway` / `python -m secure_gateway`. Common commands:

- `secure-gateway mask <text>` / `--input-file` ??mask text or code locally; supports encrypted `--session-file` transfer.
- `secure-gateway unmask <masked>` / `--input-file` ??restore masked text locally for display.
- `secure-gateway serve` ??run local MCP utilities over stdio (no unauthenticated network transports).
- `secure-gateway gateway install` ??configure the loopback subscription gateway and user-login startup.
- `secure-gateway gateway run` ??run the configured gateway in the foreground.
- `secure-gateway gateway features` — show opt-in feature defaults, sources and the state the next start would use; `gateway run`/`api-run` accept `--feature NAME=on|off` and `--features-off`.
- `secure-gateway gateway status` / `stop` / `uninstall` / `reset` / `admin` ??gateway lifecycle and diagnostics.
- `secure-gateway gateway audit-gc` / `audit-export` ??inspect/apply audit retention or export bounded metadata.
- `secure-gateway doctor`, `init`, `uninstall`, `stats`, `state`, `restore`, `exec` ??hook/integration and local session utilities.

```bash
secure-gateway mask "Patient John Doe" --sensitive-term "John Doe" --json-output
secure-gateway gateway install
secure-gateway gateway status
```

## MCP tools

When running `secure-gateway serve` (stdio MCP), the server registers local masking utilities. Tool arguments are provider-visible to the model host; confidential data must be pre-masked by a trusted local client before provider use.

- `mask_text` ??mask text with mode/strategy/language/sensitive-term options.
- `mask_code` ??mask identifiers/literals in code with an explicit or detected language profile.
- `create_privacy_session` ??create an isolated session with mode/strategy/TTL.
- `get_session_stats` ??return sanitized session counters (no originals or mappings).
- `clear_privacy_session` ??release a session's mapping references.

Restoration is intentionally **not** exposed as an MCP tool; use the local Python API or CLI (`unmask` / `restore`) in the trusted host.

## Related docs

- [Architecture](ARCHITECTURE.md)
- [Gateway integration](GATEWAY.md)
- [Local integration](LOCAL_INTEGRATION.md)
- [ADRs](adr/README.md)
