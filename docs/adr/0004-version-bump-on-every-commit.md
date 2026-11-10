# ADR 0004: Version bump on every commit

- Status: Accepted
- Date: 2026-11-10 (reconstructed)
- Sources: `AGENTS.md`, repository release/versioning practice reflected in commit history and versioned metadata files.

## Context

This repository uses package/version metadata and tags as part of delivery. Commits that change behavior, docs, tests, or configuration need an unambiguous version identity so artifacts, diagnostics, and release history do not conflate different states.

## Decision

Every committed change increments the package version in the same commit (patch for fixes/docs/tests/config, minor for new features, major only when explicitly requested). Update `pyproject.toml`, `src/secure_gateway/__init__.py`, the local package entry in `uv.lock`, and docs stating the current version; preserve historical references and fixtures.

## Consequences

- Each commit has a distinct version for traceability and release packaging.
- Parallel work may require merge-time renumbering, but each branch still carries an explicit version.
- Version-reporting surfaces (CLI/MCP/package metadata) must stay consistent with the bumped version.
