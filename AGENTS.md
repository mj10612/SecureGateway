# Repository instructions

@C:\Users\user\.codex\RTK.md

## Versioning

- Every change committed to this repository must include a new package version.
  Do not commit another change under the previously committed version.
- Increment the patch version for fixes, documentation, tests and configuration;
  use a minor version for new features and a major version for breaking changes.
- Update `pyproject.toml`, `src/secure_gateway/__init__.py`, the local package entry in
  `uv.lock`, and documentation that states the current version in the same commit.
- Preserve historical version references and parser test fixtures.
- Verify CLI/MCP version reporting and package metadata before committing.
- Preserve published tags and commit history; do not move an existing release tag
  to include a later fix.
