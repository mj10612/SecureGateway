# ADR 0002: Rule/dictionary engine default; local models optional

- Status: Accepted
- Date: 2026-11-10 (reconstructed)
- Sources: `docs/ARCHITECTURE.md`, `docs/GATEWAY.md` (optional local context model notes), `docs/LANGUAGES.md`, domain dictionary/vocabulary implementation in `src/secure_gateway/`.

## Context

Masking must be predictable, auditable, and runnable offline for the default path. Learned models can help in narrow cases but add installation size, runtime cost, and uncertainty about privacy/behavior.

## Decision

Keep the default masking path rule-, lexer-, and dictionary-driven (tokenization, language/code profiles, reviewed vocabularies, domain dictionaries, explicit sensitive terms). Local model assistance is opt-in and bounded; it does not replace forced rules, domain dictionaries, sensitive patterns, or existing secret mappings.

## Consequences

- Default behavior is deterministic enough to test and explain, with explicit limits.
- Optional models require explicit installation/verification and must not weaken protection.
- Vocabulary and dictionary quality remain ongoing maintenance concerns; false positives/negatives are handled through reviewed policy rather than opaque model decisions.
