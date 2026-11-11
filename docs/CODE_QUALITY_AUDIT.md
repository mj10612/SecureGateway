# Code quality audit roadmap

Snapshot: 2026-11-10; GitHub issue state checked with `gh issue view`.
Closed denotes the issue's GitHub state, not proof that every historical
aspiration is achieved on this branch. Logging, exception and documentation work is merged (PRs #344 and #346).

| Phase | Issue | GitHub state | Evidence or boundary |
| --- | --- | --- | --- |
| 1 | [#327](https://github.com/mj10612/SecureGateway/issues/327) silent handlers | Closed | [diagnostics](https://github.com/mj10612/SecureGateway/commit/45db478ac3753623c710dfbc19c083e9b67ada96), [PR 341](https://github.com/mj10612/SecureGateway/pull/341); additional cleanup events on this branch |
| 1 | [#330](https://github.com/mj10612/SecureGateway/issues/330) validation | Closed | [boundary validation](https://github.com/mj10612/SecureGateway/commit/82646da); remaining asserts require individual classification |
| 1 | [#329](https://github.com/mj10612/SecureGateway/issues/329) experiments | Closed | [evaluation implementation](https://github.com/mj10612/SecureGateway/commit/46d031f); incomplete markers have recovery semantics |
| 2 | [#328](https://github.com/mj10612/SecureGateway/issues/328) logging | Open | [PR 344](https://github.com/mj10612/SecureGateway/pull/344) merged opt-in package logging; 11 `except ...: pass` handlers remain package-wide, and repository-wide migration, rotation and overhead measurement remain open |
| 2 | [#336](https://github.com/mj10612/SecureGateway/issues/336) exceptions | Closed | [PR 344](https://github.com/mj10612/SecureGateway/pull/344) introduced categories and attached existing custom exceptions while retaining prior base classes |
| 2 | [#332](https://github.com/mj10612/SecureGateway/issues/332) stream resources | Closed | [stream cleanup](https://github.com/mj10612/SecureGateway/commit/14dbd05) |
| 3 | [#331](https://github.com/mj10612/SecureGateway/issues/331) documentation | Closed | [PR 346](https://github.com/mj10612/SecureGateway/pull/346): public docstrings enforced by `tests/test_docstrings_331.py`, `docs/API.md`, ADRs |
| 3 | [#334](https://github.com/mj10612/SecureGateway/issues/334) context tests | Closed | [context tests](https://github.com/mj10612/SecureGateway/commit/56e9883) |
| 3 | [#333](https://github.com/mj10612/SecureGateway/issues/333) dependencies | Closed | [locked installs](https://github.com/mj10612/SecureGateway/commit/64f60e3) |
| 4 | [#335](https://github.com/mj10612/SecureGateway/issues/335) platform support | Closed | [PR 339](https://github.com/mj10612/SecureGateway/pull/339) |

Metrics measured using Python AST on this branch compared with its starting
HEAD: literal exception handlers whose sole statement is `pass` in the four
assigned modules fell from 3 to 0 (gateway 1, install 2, stream 0, command
capture 0). Across the entire package 8 such handlers remain, so the global
zero target is open. Fourteen `assert` statements remain in the package, both
before and after; their use for validation was not classified, so the zero
validation-assert target is unproven. These simple counts do not include other
forms of swallowed failures.

The targets of all exceptions logged, 100% public docstrings, all critical
modules over 90% coverage, and all dependencies pinned were not separately
measured on this branch and remain open. A one-hour resource stress test,
logging overhead, cross-platform CI and live provider comprehension were not
run. Locked dependencies and automated tests are not substitutes for those
measurements. CLI program output is intentionally retained.

Update after merge (2026-11-11): the table above reflects the merged state. Counted on main after
PR #344, 11 handlers whose sole statement is `pass` remain across the package (some are intentional,
such as `FileExistsError`); they were not individually classified. Public docstring coverage is now
enforced by test. The other unmeasured targets listed above are unchanged.

## Resolution on fix/328-remaining-silent-handlers (v2.13.2)

### Summary of metrics

- **Unjustified single-`pass` exception handlers in `src/secure_gateway`**: 21 -> 0.
  All 21 handlers have been individually classified and annotated with `# intentional: <reason>`. Exception types were narrowed where applicable (`domain_dictionaries.py`). Enforced by AST guard `tests/test_silent_handlers_328.py`.
- **Unclassified `assert` statements in `src/secure_gateway`**: 20 -> 0.
  All 20 assert statements were classified. Zero are used for external input validation (all validation uses explicit checks raising standard or domain exceptions). All 20 represent internal invariants or type narrowing, and each carries an `# invariant: <reason>` comment. Enforced by AST guard `tests/test_assert_invariants_337.py`.

### Single-pass exception handler classification table

| File:Line | Caught Exception | Classification | Justification |
| --- | --- | --- | --- |
| `audit_retry.py:118` | `(sqlite3.Error, ValueError, TypeError, OverflowError, OSError)` | `intentional` | Retry only the ledger write; failures are recorded in the subsystem diagnostic counter `self._errors` |
| `content_audit.py:89` | `FileExistsError` | `intentional` | Audit store database file may already exist from previous runs or concurrent workers |
| `content_audit_capture.py:111` | `Exception` | `intentional` | Best-effort fallback begin before marking request failed |
| `content_audit_capture.py:119` | `Exception` | `intentional` | Best-effort fail notification when audit writer is already broken |
| `content_audit_writer.py:204` | `queue.Full` | `intentional` | Wake-up marker dropped because queue is full; pending states will be drained |
| `content_audit_writer.py:312` | `Exception` | `intentional` | Diagnostic logging must never raise into caller or recurse |
| `content_audit_writer.py:319` | `Exception` | `intentional` | Diagnostic logging must never raise into caller or recurse |
| `domain_dictionaries.py:79` | `(ValueError, KeyError)` | `intentional` | Language may not have packaged vocabulary; fallback to empty common words (narrowed from `Exception`) |
| `domain_dictionaries.py:83` | `(ValueError, KeyError)` | `intentional` | Language may not have public vocabulary; fallback to empty common words (narrowed from `Exception`) |
| `encrypted_session.py:278` | `FileExistsError` | `intentional` | Concurrent process already linked the lock file atomically |
| `evaluation_worker.py:227` | `(BrokenPipeError, OSError, ValueError)` | `intentional` | Worker process may exit or close stdin before input completes |
| `evaluation_worker.py:232` | `(BrokenPipeError, OSError)` | `intentional` | Best-effort close of stdin during teardown |
| `experiment_profiles.py:484` | `ValueError` | `intentional` | Unclosed markdown backticks fall back safely to unblocked text |
| `gateway.py:148` | `Exception` | `intentional` | Diagnostic logger handler teardown must not raise or recurse |
| `gateway.py:3484` | `(ValueError, TypeError, UnicodeError)` | `intentional` | Non-JSON or malformed payload skips JSON content audit capture |
| `gateway_audit.py:59` | `FileExistsError` | `intentional` | Another gateway created the same database concurrently |
| `gateway_audit.py:131` | `OSError` | `intentional` | Best-effort cleanup of owner lock file during audit close |
| `gateway_install.py:356` | `Exception` | `intentional` | Optional diagnostics must not reverse a successful stop |
| `gateway_stream.py:224` | `Exception` | `intentional` | Content capture failure notification must not interrupt streaming |
| `platform_utils.py:54` | `(OSError, subprocess.TimeoutExpired)` | `intentional` | Best-effort tree kill on Windows; process may already have exited |
| `platform_utils.py:63` | `(ProcessLookupError, PermissionError)` | `intentional` | Group termination can be unavailable even for an owned child |

### Assert statements classification table

| File:Line | Assert Expression | Classification | Invariant Basis |
| --- | --- | --- | --- |
| `antigravity_install.py:111` | `assert record is not None` | `invariant` | Guarded by early return on missing record when `not install` |
| `command_capture.py:81` | `assert process.stdout is not None and process.stderr is not None` | `invariant` | Process spawned with `stdout=PIPE` and `stderr=PIPE` |
| `content_audit.py:253` | `assert wrapping is not None` | `invariant` | Guarded by preceding `_require_unlocked` |
| `content_audit.py:255` | `assert params is not None` | `invariant` | Guarded by preceding `_require_unlocked` |
| `content_audit_admin.py:239` | `assert self.store is not None` | `invariant` | Initialized by `get_request` via `_ensure_store` |
| `content_audit_export.py:82` | `assert passphrase is not None` | `invariant` | Validated earlier in function when `not plaintext` |
| `domain_dictionaries.py:244` | `assert isinstance(root, dict)` | `invariant` | Root `edges[0]` is always initialized to dict in `__init__` |
| `domain_dictionaries.py:291` | `assert isinstance(root, dict)` | `invariant` | Root `edges[0]` is always initialized to dict in `__init__` |
| `encrypted_session.py:230` | `assert mapping.identifier_language is not None and mapping.identifier_key is not None` | `invariant` | Validated by preceding call to `valid_identifier_alias` |
| `engine/code_parser.py:664` | `assert match is not None` | `invariant` | Guarded by `elif cpp or rust:` branch condition |
| `engine/code_parser.py:701` | `assert match is not None` | `invariant` | Guarded by `elif string or prefixed:` branch condition |
| `engine/code_parser.py:711` | `assert number is not None` | `invariant` | `NUMBER` regex is guaranteed to match digit or leading dot digit prefix |
| `engine/extended_code.py:77` | `assert escape is not None` | `invariant` | Escape pattern with fallback dot matches any trailing character |
| `engine/extended_code.py:1174` | `assert indentation is not None` | `invariant` | Zero-or-more whitespace pattern always matches |
| `evaluation_worker.py:223` | `assert process.stdin is not None` | `invariant` | Process spawned with `stdin=PIPE` |
| `evaluation_worker.py:235` | `assert process.stdout is not None and process.stderr is not None` | `invariant` | Process spawned with `stdout=PIPE` and `stderr=PIPE` |
| `gateway.py:1294` | `assert prefix is not None` | `invariant` | Guarded by broader "Follow instructions" regex match |
| `gateway.py:3130` | `assert audit is not None` | `invariant` | Caller verified `self.server.audit is not None` |
| `session.py:65` | `assert node is not None` | `invariant` | `_original_trie` is initialized before `_index_original` call |
| `session.py:120` | `assert original is not None` | `invariant` | Output links only point to terminal states with patterns |
