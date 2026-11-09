# Production Assertion Audit and Validation Guard Verification (Issue #330)

Status: **Audited and fixed in version 2.7.3.**
Investigated against release base `7e5d9f79d79380090626ea5978d031f67a2df67e` (2.7.2).

---

## 1. Executive Summary & Purpose

Issue #330 raised concerns regarding the use of Python `assert` statements in production code, highlighting the risk that `python -O` (optimized bytecode execution) strips all assertion statements.

An initial, naive implementation plan proposed introducing a generic `require()`, `require_type()`, `require_positive()` helper framework across the codebase and replacing all grep-matched `assert` statements with `ValueError`. Following architectural review, that generic framework was rejected:
1. **Subclass Pitfalls:** In Python, `bool` is a subclass of `int` (`isinstance(True, (int, float))` is `True`). Naive numeric checkers accept boolean values unless specifically handled.
2. **Type Signature Flaws:** Primitive `require_type(val, Type)` helpers break when validating union tuples (e.g., `(int, float)`).
3. **Destruction of Error Contracts:** Indiscriminately converting every invariant to `ValueError` breaks CLI error presentation (`click.ClickException`), system diagnostics, and existing exception handling contracts.
4. **Flawed Premise:** Not all production assertions represent input validation. The repository distinguishes three distinct categories of assertions:
   - **Category A (Input & Boundary Validation):** Public or boundary API checks that must enforce valid input regardless of optimization flags. These must raise explicit, suitable exceptions (`ValueError`, `ClickException`, etc.).
   - **Category B (Programmer Invariants):** Internal sanity checks where preceding logic or standard library contracts (e.g., `subprocess.Popen(..., stdout=PIPE)`) guarantee the condition.
   - **Category C (Proven Optional Attributes / Type Narrowing):** Control flow has already proven non-nullity, but `assert` was used to narrow static types for `mypy`.

This investigation audited all 18 `assert` statements across the codebase, fixed real boundary validation issues that disappeared under `-O`, preserved existing error contracts, documented retained proven invariants, and verified normal and `-O` execution with targeted subprocess tests.

---

## 2. Complete Repository Audit Matrix

Every `ast.Assert` node across `src/secure_gateway/` was audited:

| # | File and Line | Expression | Category | Behavior Under `python -O` | Disposition / Action Taken |
|---|---|---|---|---|---|
| 1 | `engine/code_parser.py:375` | `assert suffix is not None` | **Category A** (Boundary validation) | `assert` stripped; subsequent `suffix[0]` raised unhandled `TypeError: 'NoneType' object is not subscriptable` | **Fixed**: Replaced with explicit `if suffix is None: raise ValueError("Unsupported regex literal")`. Preserves `ValueError` contract matching string literal errors. |
| 2 | `cli.py:592` | `assert restored.unmasked_text == text` | **Category A** (Verification) | `assert` stripped; `demo` command printed success and exited with code 0 despite roundtrip corruption | **Fixed**: Replaced with `if restored.unmasked_text != text: raise click.ClickException("Demo restoration mismatch: roundtrip text does not match original.")`. |
| 3 | `cli.py:387` | `assert session is not None` | **Category A/B** (Boundary guard) | `assert` stripped; if session was None, `store.mask` raised `AttributeError`, escaping `(ValueError, OSError, AssertionError)` handler | **Fixed**: Replaced with `if session is None: raise ValueError("Session could not be initialized.")`. Caught cleanly by line 390. |
| 4 | `hooks.py:580` | `assert session is not None` | **Category A/B** (Boundary guard) | `assert` stripped; if session was None, raised `AttributeError` instead of documented `ValueError` | **Fixed**: Replaced with `if session is None: raise ValueError("Session could not be initialized.")`. Preserves `handle_hook`'s `ValueError` contract. |
| 5 | `antigravity_install.py:111` | `assert record is not None` | **Category C** (Proven by control flow) | Stripped cleanly; `record` is guaranteed to be a `dict` by line 90 (`if not install and record is None: return None`) | **Retained**: Proven internal invariant; no behavioral difference under `-O`. |
| 6 | `engine/code_parser.py:650` | `assert match is not None` | **Category C** (Proven by control flow) | Stripped cleanly; guaranteed truthy by `elif cpp or rust:` | **Retained**: Proven internal invariant (type narrowing for mypy). |
| 7 | `engine/code_parser.py:687` | `assert match is not None` | **Category C** (Proven by control flow) | Stripped cleanly; guaranteed truthy by `elif string or prefixed:` | **Retained**: Proven internal invariant (type narrowing for mypy). |
| 8 | `engine/code_parser.py:697` | `assert number is not None` | **Category C** (Proven by regex) | Stripped cleanly; `NUMBER` pattern guaranteed to match when starting with digit or `.\d` | **Retained**: Proven internal invariant (type narrowing for mypy). |
| 9 | `engine/extended_code.py:77` | `assert escape is not None` | **Category C** (Proven by regex) | Stripped cleanly; escape regex guaranteed to match 2+ characters starting with `\` or `` ` `` | **Retained**: Proven internal invariant (type narrowing for mypy). |
| 10 | `engine/extended_code.py:1174` | `assert indentation is not None` | **Category C** (Proven by regex) | Stripped cleanly; `[ \t]*` (0 or more) matches at any valid string index | **Retained**: Proven internal invariant (type narrowing for mypy). |
| 11 | `command_capture.py:109` | `assert process.stdout is not None and process.stderr is not None` | **Category B** (Stdlib contract) | Stripped cleanly; `subprocess.Popen(..., stdout=PIPE, stderr=PIPE)` guarantees streams exist | **Retained**: Proven internal invariant (typeshed type narrowing). |
| 12 | `evaluation_worker.py:226` | `assert process.stdin is not None` | **Category B** (Stdlib contract) | Stripped cleanly; `Popen(..., stdin=PIPE)` guarantees stream exists | **Retained**: Proven internal invariant (typeshed type narrowing). |
| 13 | `evaluation_worker.py:238` | `assert process.stdout is not None and process.stderr is not None` | **Category B** (Stdlib contract) | Stripped cleanly; `Popen(..., stdout=PIPE, stderr=PIPE)` guarantees streams exist | **Retained**: Proven internal invariant (typeshed type narrowing). |
| 14 | `encrypted_session.py:224` | `assert mapping.identifier_language is not None and mapping.identifier_key is not None` | **Category C** (Proven by validation) | Stripped cleanly; `valid_identifier_alias` verified both fields immediately prior | **Retained**: Proven internal invariant (type narrowing). |
| 15 | `session.py:61` | `assert node is not None` | **Category C** (Proven by caller) | Stripped cleanly; `self._original_trie` is checked or initialized to `{}` before calling `_index_original` | **Retained**: Proven internal invariant (type narrowing). |
| 16 | `session.py:116` | `assert original is not None` | **Category B/C** (Automaton invariant) | Stripped cleanly; Aho-Corasick automaton `match` only transitions to terminal nodes | **Retained**: Proven internal invariant (type narrowing). |
| 17 | `gateway.py:960` | `assert prefix is not None` | **Category C** (Proven by outer regex) | Stripped cleanly; outer `if re.match(r"\s*Follow (?:its|the) instructions\b", sentence):` guarantees match | **Retained**: Owned by #338 (do not edit); reported for coordinator integration. |
| 18 | `gateway.py:2523` | `assert audit is not None` | **Category B** (Server invariant) | Stripped cleanly; `_audited_POST` is invoked only when audit server is active | **Retained**: Owned by #338 (do not edit); reported for coordinator integration. |

---

## 3. Analysis of Changed Sites

### 3.1. `src/secure_gateway/engine/code_parser.py`: `literal_parts`
- **Location:** Line 375.
- **Problem:** When `literal_parts(value, "regex")` was called with a malformed regex literal (e.g. missing trailing slash, or containing invalid trailing characters such as `/pattern/123`), `re.search(r"/[A-Za-z]*$", value)` returned `None`. Under normal Python, this raised `AssertionError`. Under `python -O`, the assertion was stripped, and line 376 evaluated `suffix[0]`, raising an unhandled `TypeError: 'NoneType' object is not subscriptable`.
- **Fix:**
  ```python
  if subkind == "regex":
      suffix = re.search(r"/[A-Za-z]*$", value)
      if suffix is None:
          raise ValueError("Unsupported regex literal")
      return "/", suffix[0]
  ```
- **Error Contract:** Preserved. Line 394 already raises `ValueError("Unsupported string literal")` on unparseable string literals; raising `ValueError("Unsupported regex literal")` maintains consistency for all literal parsing.

### 3.2. `src/secure_gateway/cli.py`: `demo`
- **Location:** Line 592.
- **Problem:** The CLI command `secure-gateway demo` executes actual token allocations and unmasks them, verifying that roundtrip restoration matches the original text. Under normal Python, `assert restored.unmasked_text == text` failed on corruption with `AssertionError`. Under `python -O`, this verification was stripped, meaning any regression in roundtrip masking would silently print success panels and exit 0.
- **Fix:**
  ```python
  if restored.unmasked_text != text:
      raise click.ClickException(
          "Demo restoration mismatch: roundtrip text does not match original."
      )
  ```
- **Error Contract:** Formatted as a user-facing Click exception with exit code 1 under both normal and `-O` execution.

### 3.3. `src/secure_gateway/cli.py`: `exec_masked`
- **Location:** Line 387.
- **Problem:** The `exec_masked` command captures command execution and masks the output inside a session context. The exception block at line 390 caught `(ValueError, OSError, AssertionError)`. Under `python -O`, `assert session is not None` was stripped. If session initialization failed (yielding `None`), subsequent access in `store.mask` raised `AttributeError: 'NoneType' object has no attribute 'session_id'`. Because `AttributeError` was not in the caught tuple, an unhandled traceback escaped to the user terminal.
- **Fix:**
  ```python
  with store.session(session_id, create=True) as session:
      if session is None:
          raise ValueError("Session could not be initialized.")
      stdout = store.mask(completed.stdout.decode("utf-8"), session)
      stderr = store.mask(completed.stderr.decode("utf-8"), session)
  ```
- **Error Contract:** Preserved. `ValueError` is caught by line 390 and converted into `click.ClickException("Local execution/masking failed; no raw output was returned.")`.

### 3.4. `src/secure_gateway/hooks.py`: `handle_hook`
- **Location:** Line 580.
- **Problem:** Similar to `exec_masked`, `handle_hook` manages session creation for `PostToolUse` events. Under normal Python, `assert session is not None` raised `AssertionError`. Under `python -O`, a `None` session caused `AttributeError` deep inside `_walk`.
- **Fix:**
  ```python
  with store.session(sid, create=True) as session:
      if session is None:
          raise ValueError("Session could not be initialized.")
      replacement = _walk(...)
  ```
- **Error Contract:** Preserved. All failure modes in `handle_hook` raise `ValueError`.

---

## 4. Retained Proven Invariants & Non-Vulnerabilities

### 4.1. Invariant: `antigravity_install.py:111`
In `configure_antigravity(path: Path, install=True)`:
```python
if not install and record is None:
    return None
...
if install:
    ...
else:
    assert record is not None
```
If `install` is `False` and `record` is `None`, line 90 returns `None` immediately. When the execution reaches the `else` branch of `if install:`, `install` is guaranteed to be `False`, which implies `record` cannot be `None`. The `assert record is not None` statement exists purely as a type hint for static analyzers. Under `-O`, omitting this assert introduces zero risk of null dereference.

### 4.2. Invariant: `engine/code_parser.py:650, 687, 697`
- Line 650 is preceded by `elif cpp or rust: match = cpp or rust`. Control flow guarantees that `match` is not `None`.
- Line 687 is preceded by `elif string or prefixed: match = string or prefixed`. Control flow guarantees that `match` is not `None`.
- Line 697 is preceded by `elif c.isdigit() or (c == "." and i + 1 < len(code) and code[i + 1].isdigit()): number = NUMBER.match(code, i)`. The `NUMBER` regular expression starts with alternatives matching `\d` or `\.\d`. Control flow guarantees that `number` matches at least one character and cannot be `None`.

### 4.3. Invariant: `engine/extended_code.py:77, 1174`
- Line 77 is guarded by `if raw[position] in {"\\", "`"} and position + 1 < len(raw):`. The regex contains fallback alternatives `\\.` and `` `.` `` with `re.DOTALL`, which match any two characters beginning with `\` or `` ` ``. The match cannot be `None`.
- Line 1174 matches `r"[ \t]*"`. Because the quantifier `*` matches zero or more occurrences, matching against any valid string offset always succeeds with a non-null `Match` object.

### 4.4. Invariant: Subprocess Pipe Streams
- `command_capture.py:109`: `assert process.stdout is not None and process.stderr is not None`
- `evaluation_worker.py:226, 238`: `assert process.stdin is not None`, `assert process.stdout is not None and process.stderr is not None`
In both files, processes are spawned using `subprocess.Popen(..., stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)`. The Python standard library `subprocess` module unconditionally attaches `io.BufferedReader` / `io.BufferedWriter` streams when `PIPE` is requested. The assertions exist solely to satisfy typeshed's `IO[bytes] | None` type definition.

### 4.5. Retained Guards in External Ownership Files
- `src/secure_gateway/gateway.py:960`: `assert prefix is not None` (guarded by outer `re.match(r"\s*Follow (?:its|the) instructions\b", sentence)`).
- `src/secure_gateway/gateway.py:2523`: `assert audit is not None` (guarded by `server.admission` check in `_audited_POST`).
As `gateway.py` is owned by #338, these guards remain unmodified and are confirmed safe proven invariants for coordinator integration.

---

## 5. Security Bypass Investigation & Negative Proof

Issue #330 suggested that assertions in production could allow security bypasses under `python -O`.

We systematically evaluated whether any unauthenticated user or remote client could bypass security controls under `python -O`:
1. **Network & Gateway Boundaries:** In `gateway.py`, proxy request admission, token substitution, and TLS/HTTP loopback filters rely on explicit conditional checks that raise `ValueError` or return HTTP 400/403/502. None of these boundaries rely on `assert`.
2. **Session Decryption & Deserialization:** In `encrypted_session.py`, input payload verification (`load_session`) uses explicit `KeyError`, `TypeError`, `ValueError`, and `OverflowError` checks. The single assert at line 224 is preceded by `valid_identifier_alias(mapping)` which enforces key and language presence.
3. **Targeted result:** No such security bypass was reproduced in the inspected paths and focused checks. This audit is not exhaustive proof that no optimized-mode security bug can exist.

Claiming a "critical security bypass" for internal `mypy` type-narrowing asserts is technically unfounded.

---

## 6. Performance scope

No independent repeated performance benchmark was established for this change.
The worker reported exploratory single-pair timings without retained raw samples;
these are not used to assert statistical significance, zero overhead, or a
less-than-one-percent regression bound. The production diff replaces four local
assertions with explicit checks and does not add a validation framework.

---

## 7. Testing Methodology

### 7.1. Subprocess Isolation for `-O` Verification
The coordinator keeps the pytest verifier in normal Python and runs the target snippets in separate normal/optimized child processes. This avoids relying on assertion rewriting or assertions inside optimized target code.

To prevent this, tests in `tests/test_validation_guards_330.py`:
1. Execute inside standard pytest (normal Python where pytest assertions remain fully functional).
2. Spawn isolated target subprocesses using both `sys.executable` (normal mode) and `[sys.executable, "-O"]` (optimized mode).
3. Directly verify exit codes, standard output messages, and exception diagnostics from the subprocesses.

### 7.2. Test Coverage Matrix (`test_validation_guards_330.py`)
- `test_literal_parts_regex_validation_normal_and_optimized`: Confirms `ValueError("Unsupported regex literal")` is raised on invalid regex inputs under both normal and `-O`.
- `test_literal_parts_direct`: Unit tests verifying prefix/suffix splitting and error messages.
- `test_cli_demo_roundtrip_verification_normal_and_optimized`: Confirms `demo` exits 0 on valid roundtrips, and exits 1 with `ClickException` on simulated restoration mismatch under both normal and `-O`.
- `test_cli_exec_masked_session_failure_normal_and_optimized`: Confirms `exec_masked` catches session failures cleanly under both normal and `-O`.
- `test_handle_hook_session_failure_normal_and_optimized`: Confirms `handle_hook` raises `ValueError` on session initialization failure under both normal and `-O`.
- `test_retained_invariants_code_parser_normal_and_optimized`: Confirms code parser invariants (C++, Rust raw literals, numbers, SQL identifiers) work identically under normal and `-O`.
- `test_retained_invariants_extended_code_normal_and_optimized`: Confirms extended code invariants (escapes, NASM indentation) work identically under normal and `-O`.
- `test_antigravity_install_and_status_normal_and_optimized`: Confirms Antigravity install/uninstall and status invariants work identically under normal and `-O`.
- `test_session_and_automaton_normal_and_optimized`: Confirms session trie and Aho-Corasick automaton invariants work identically under normal and `-O`.

The test file has 17 parametrized cases spanning both execution modes. The coordinator strengthened child snippet checks to explicit exceptions so they remain active under `-O`, and bounded each child process to 30 seconds. Final integration results are recorded below after execution.

## 8. Coordinator integration verification

The four selected regex/demo regressions fail against released 2.7.2 in both
normal and optimized target subprocesses. With this fix, the strengthened
validation guards plus CLI, hooks and code-parser suites pass: **51 passed**.
Ruff and mypy pass. CLI, module, installed metadata, MCP application and
privacy-status all agree on **2.7.3**. This is focused validation proof, not a
claim of exhaustive security analysis, a measured zero performance penalty,
or a completed remote OS/Python CI matrix.
