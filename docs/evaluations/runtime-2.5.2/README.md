# Runtime integrity and release evidence — 2.5.2

Date: 2026-11-09. Windows, Python 3.11.15. Synthetic data, isolated temporary
host homes and loopback providers only. No user gateway installation or real
subscription inference was performed.

## Changes and decisions

- #293: incremental Claude/Codex text, bounded alias/tool/thinking buffers,
  immediate headers/heartbeats, session-local dependency-aware masking cache,
  timing summaries and completion persistence barriers. HTTP connection pooling
  is not introduced; these tests do not assert faster provider inference.
- #294: account/conversation-scoped Codex tables, snapshots and reasoning
  provenance; provider reset and diagnostics include scoped tables. Legacy
  clients without conversation identity retain the documented provider table.
  Idle read timeout is 600 seconds, not an end-to-end deadline. Windows raw
  socket cancellation is tested before the upstream completes.
- #295: fixed diagnostic codes/guidance for unknown signed reasoning,
  attachments, fields, attribution and generic validation failures. Unknown
  signed history and images remain blocked; silently deleting history or
  permitting unmasked image passthrough is rejected as an unsafe compatibility
  shortcut. Attribution remains bounded to verified public formats.
- #296: strict original-input checks reject altered/prefixed/suffixed aliases,
  without scanning restored originals or guessing shorter aliases. Exact valid
  alias 10 still refers to alias 10; spelling cannot identify a model's intended
  alias 1 plus digit. The existing whole-path/lexical-shell representations are
  retained; malformed combinations are rejected instead of guessing a path.
- #299: corrupt runtime data no longer prevents manifest recovery. New private
  manifests retain validated identity for selective cleanup. An unavailable
  authenticated shutdown is explicitly warned about, not reported as success.
- #301: install/remove share a crash-released OS lock and inode ownership
  journal. Unknown preexisting partials are retained with explicit recovery
  instructions. Actual child-process kill/retry/remove is covered.
- #302: installed wheel/sdist lifecycle and cross-version upgrade, actual native
  host/tool gate with skip rejection, daemon health version, and a pinned
  three-OS CI job. Cross-platform CI execution is separate from local evidence.

## Checks

- Full source suite: **4,329 passed, 287 skipped, 2 failed** in 658.40 seconds.
  Both failures were POSIX-only executable fixtures in the Codex evaluation
  adapter tests. They were fixed to pin the fixture and execute it with Python,
  rejecting non-fixture launches. The worker suite then passed **42 tests,
  2 skipped**. This is not described as a clean rerun of the entire suite.
- New/affected runtime, recovery, diagnostics and release gates: **82 passed**
  with warnings as errors. Additional focused installation, parser, snapshot
  and restoration gates were run while implementing the fixes.
- Native offline clients: Claude Code **2.1.319**, Codex CLI **0.167.0**;
  all **4 request/tool cases passed** from the source environment.
- Both final wheel and sdist were installed into fresh environments outside the
  source tree. Each upgraded an immutable `aa18f93` / 2.5.1 wheel, restarted,
  verified daemon/package versions, executed a real loopback masking/file-tool
  roundtrip, preserved host edits/login fixtures, and uninstalled. Each also
  passed all **4 native offline cases** with no skipped native cases.
- Final wheel Python source bytes match the working source. CLI, MCP, module
  and installed package metadata all report **2.5.2**. Ruff/mypy/diff checks pass.

## Privacy baseline

The [actual loopback capture](privacy/report.json) was rerun on the unchanged
32-case release corpus. Sensitive occurrences: **57/66 protected, 9 existing
full exposures**, no partial/ambiguous exposures. Public spans: **30/117
overmasked**. Exact restoration 31/32 (the known JSON-spacing difference),
semantic restoration and replay 32/32; session isolation/restart passed.
Comparison with the 2.5.0 baseline reports no new exposures or integrity
regressions. These are synthetic-corpus results, not production probabilities.
Comprehension was not remeasured for this runtime-only change.

Real provider behavior, macOS/Linux execution and an actual three-minute model
generation are not claimed by the local run. Bounded barrier tests prove early
delivery/cancellation independently of arbitrary wall-clock sleeps. The separate
dictionary and accuracy experiments remain tracked in OPEN_ISSUE_EXECUTION.md.
