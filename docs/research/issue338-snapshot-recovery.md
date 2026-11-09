# Issue 338: corrupt snapshot/provenance recovery

## Scope

Owned fix in `PrivacyGateway` snapshot/provenance load/save/recovery methods in
`src/secure_gateway/gateway.py`, dedicated regression tests, and version
documentation integrated in 2.7.12. No changes to `GatewaySession._mask_prose`, vocabulary
integration, frozen evaluation evidence, `evaluation_codex_worker.py`, host
settings, or release tags.

## Reproduction (before fix)

Against the pre-fix request path (`get_session`), a corrupted per-conversation
encrypted snapshot file (`<key>-symbols-v2.enc`) caused `load_session()` to raise
`ValueError` (`Invalid encrypted session file.`). The active HTTP request path in
`GatewayHandler._do_POST` catches `ValueError` and returns a generic 400
privacy-validation error, so the affected conversation stayed unavailable until
the local snapshot files were removed manually. The same failure class applied to
invalid paired `.opaque.json` reasoning-provenance metadata (invalid JSON, wrong
shape, or non-hex digests).

## Fix

- `PrivacyGateway._recover_snapshot(key, opaque_only=False)` quarantines
  proven-corrupt local snapshot state by renaming the affected file to a bounded
  `*.quarantined` sibling (one quarantined copy per file). It never follows
  symlinks (active snapshot symlinks are rejected before reading; the target is never modified), operates
  only within the gateway's own `state_dir` key namespace, and raises a fixed
  `OSError("Snapshot recovery failed.")` on quarantine failure without
  exception text, snapshot contents, or tokens.
- `get_session()` catches the invalid-envelope error from `load_session()`, quarantines the snapshot pair,
  and starts a fresh in-memory session. `SessionExpiredError` still removes the
  expired snapshot. `OSError` from snapshot load is not treated as proven
  corruption and propagates (transient read/permission failure). Authentication failures are ambiguous with wrong passwords and preserve state.
- If the encrypted mapping snapshot loads successfully but
  `<key>-symbols-v2.opaque.json` is malformed/invalid, only opaque provenance is
  quarantined. Encrypted alias mappings remain usable, but `session.opaque` stays
  empty so old signed/encrypted reasoning blocks cannot be replayed without fresh
  provenance. `OSError` reading the opaque file is treated as transient and
  propagates without quarantine.

## Safety properties

- Bounded quarantine: at most one `*.quarantined` file per affected path; no
  unbounded growth.
- Isolation preserved: recovery applies only to the requested conversation key;
  other conversations retain their mappings.
- No provenance bypass: invalid historical opaque blocks remain explicit failures
  (`Unrecognized signed/encrypted reasoning; start a new conversation.`).
- No symlink following / no foreign file deletion: symlinks are unlinked; regular
  files are renamed only inside the gateway state directory.
- No secret leakage in recovery diagnostics: quarantine failure raises a fixed
  message; HTTP error responses remain the existing sanitized public form.
- Cleanup/reset behavior unchanged: `cleanup_expired_snapshots()` still preserves
  damaged/foreign snapshots conservatively; reset removes files explicitly.

## Tests

`tests/test_gateway_snapshot_recovery.py` (16 passed, 1 skip on platforms without
symlink support) covers corrupt encrypted snapshot reload recovery, invalid opaque
JSON/shape/non-hex digests, fake loopback HTTP provider verifies success, masking and persistence with no
secret leakage, other conversations retaining mappings, transient `OSError` not
quarantined, symlink target not followed/modified, and safe fixed diagnostics on
quarantine failure.

## Limitations / coordination

- Existing alias/provenance state for the affected conversation is not
  recoverable once its authenticated snapshot/provenance is corrupt; recovery is
  availability-focused and requires a fresh conversation for historical opaque
  reasoning replay.
- No cross-project logging rewrite and no new user-facing diagnostics beyond the
  bounded quarantine behavior; the fixed quarantine-failure `OSError` is internal
  and handled by existing safe HTTP error paths.
- Authentication failure is indistinguishable from a wrong password, so affected
  snapshots are preserved and require explicit operator recovery.
