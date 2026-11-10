# Release evidence checklist

Release commit: ______  Wheel / sdist hashes: ______  Date: ______

The following gates must pass on the release commit and its actual artifacts.
Record the workflow run, operating systems, Python and pinned host versions, and
any failures. A successful CI run does not establish live host compatibility.

- [ ] CI test, lint and type-check jobs: ______
- [ ] Wheel and sdist install, upgrade, restart and uninstall lifecycle on Linux,
      Windows and macOS, including installed-daemon inference, tool roundtrip and daemon PID termination: ______
- [ ] Pinned Claude and Codex native offline host/tool cases on applicable OSes,
      with no missing binaries or skipped cases: ______
- [ ] Failure atomicity and uninstall recovery: ______
- [ ] Long inference/concurrency, conversation compatibility and tool integrity: ______
- [ ] Separate optional-model gate and independent pinned-model corpus: ______
- [ ] Installed package, CLI, MCP and daemon versions agree: ______

## Manual real-account evidence

**수동 확인 필요 — 미실행**. Use explicitly authorized test accounts and synthetic
files. Record the exact release artifact, OS/version, CLI/version, features and
results, and all skipped cases and their reasons.

| Platform and version | Host and version | Feature | Result / skipped reason | Evidence |
| --- | --- | --- | --- | --- |
| ______ | ______ | English/Korean file read | 수동 확인 필요 — 미실행 | ______ |
| ______ | ______ | File edit and shell tool roundtrip | 수동 확인 필요 — 미실행 | ______ |
| ______ | ______ | Two concurrent conversations | 수동 확인 필요 — 미실행 | ______ |
| ______ | ______ | Long inference and resume existing conversation | 수동 확인 필요 — 미실행 | ______ |
| ______ | ______ | Upgrade and uninstall | 수동 확인 필요 — 미실행 | ______ |

Previous release source: `v2.4.0` is checked against the immutable commit
pinned in `scripts/build_upgrade_source.py`; its wheel is rebuilt with raw Git
archive bytes. Published wheel/sdist upgrade coverage: **미측정 — none exists**.
Once artifacts are published, use the actual prior published artifact as the
release input and retain its immutable digest as evidence.

The v2.4.0 tag has a known digit-leading path restoration defect. Its
pre-upgrade roundtrip uses a fixed ordinary relative path; digit-leading,
Korean and space-containing paths are exercised against the upgraded candidate.
The workspace is temporary and random parent names are not sent as tool paths.
