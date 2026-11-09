"""Tests for issue #330: validation guards and invariant behavior under normal and -O Python.

Verifications use targeted subprocesses running with both normal Python and
python -O (optimized mode) so that the test runner itself does not depend on
assertions inside -O.
"""

from __future__ import annotations

import subprocess
import sys
import pytest

from secure_gateway.engine.code_parser import literal_parts


def _run_subprocess(args: list[str], code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args + ["-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


@pytest.mark.parametrize("opt_flag", [[], ["-O"]])
def test_literal_parts_regex_validation_normal_and_optimized(opt_flag):
    """literal_parts must raise ValueError on invalid regex literals under both normal and -O."""
    snippet = """
import sys
from secure_gateway.engine.code_parser import literal_parts

# Valid regex literals
p1, s1 = literal_parts("/test[a-z]+/gi", "regex")
if (p1, s1) != ("/", "/gi"):
    raise RuntimeError(f"Unexpected valid parts: {p1}, {s1}")

p2, s2 = literal_parts("/simple/", "regex")
if (p2, s2) != ("/", "/"):
    raise RuntimeError(f"Unexpected valid parts: {p2}, {s2}")

# Invalid regex literal (no trailing regex slash/pattern)
try:
    literal_parts("invalid_regex", "regex")
    print("FAILED: Did not raise on invalid_regex")
    sys.exit(10)
except ValueError as exc:
    if "Unsupported regex literal" not in str(exc):
        raise RuntimeError("Unexpected regex validation message")
    print("SUCCESS: ValueError caught")
except Exception as exc:
    print(f"FAILED: Unexpected exception {type(exc).__name__}: {exc}")
    sys.exit(11)

# Another invalid regex literal (trailing digits instead of regex flags)
try:
    literal_parts("/pattern/123", "regex")
    print("FAILED: Did not raise on /pattern/123")
    sys.exit(12)
except ValueError as exc:
    if "Unsupported regex literal" not in str(exc):
        raise RuntimeError("Unexpected regex validation message")
    print("SUCCESS: Second ValueError caught")
except Exception as exc:
    print(f"FAILED: Unexpected exception {type(exc).__name__}: {exc}")
    sys.exit(13)
"""
    result = _run_subprocess([sys.executable] + opt_flag, snippet)
    assert result.returncode == 0, f"Subprocess failed (exit {result.returncode}):\n{result.stderr}\n{result.stdout}"
    assert "SUCCESS: ValueError caught" in result.stdout
    assert "SUCCESS: Second ValueError caught" in result.stdout


def test_literal_parts_direct():
    """Direct unit tests for literal_parts."""
    assert literal_parts("/abc/i", "regex") == ("/", "/i")
    assert literal_parts("/[0-9]+/", "regex") == ("/", "/")
    with pytest.raises(ValueError, match="Unsupported regex literal"):
        literal_parts("not_a_regex", "regex")
    with pytest.raises(ValueError, match="Unsupported regex literal"):
        literal_parts("/pattern/123", "regex")
    with pytest.raises(ValueError, match="Unsupported string literal"):
        literal_parts("unsupported_string", "string")


@pytest.mark.parametrize("opt_flag", [[], ["-O"]])
def test_cli_demo_roundtrip_verification_normal_and_optimized(opt_flag):
    """secure-gateway demo must succeed under normal and -O, and fail if restoration mismatches."""
    # 1. Normal run succeeds under both normal and -O
    snippet_demo_ok = """
import sys
from click.testing import CliRunner
from secure_gateway.cli import main

runner = CliRunner()
result = runner.invoke(main, ["demo"])
if result.exit_code != 0:
    print(f"FAILED: demo failed: {result.output}")
    sys.exit(1)
print("SUCCESS: demo passed")
"""
    result_ok = _run_subprocess([sys.executable] + opt_flag, snippet_demo_ok)
    assert result_ok.returncode == 0, f"Demo failed under {opt_flag}:\n{result_ok.stderr}\n{result_ok.stdout}"
    assert "SUCCESS: demo passed" in result_ok.stdout

    # 2. Corrupted unmask must raise ClickException (exit code 1) under both normal and -O
    snippet_demo_corrupt = """
import sys
from unittest.mock import patch
from click.testing import CliRunner
from secure_gateway.cli import main
from secure_gateway.models import UnmaskResult

def fake_unmask(*args, **kwargs):
    return UnmaskResult(unmasked_text="CORRUPTED_TEXT", session_id="test", restored_tokens_count=0)

runner = CliRunner()
with patch("secure_gateway.cli.engine.unmask", side_effect=fake_unmask):
    result = runner.invoke(main, ["demo"])
    if result.exit_code != 0 and "Demo restoration mismatch" in (result.output or ""):
        print("SUCCESS: Caught mismatch error")
        sys.exit(0)
    else:
        print(f"FAILED: exit={result.exit_code}, output={result.output}")
        sys.exit(2)
"""
    result_corrupt = _run_subprocess([sys.executable] + opt_flag, snippet_demo_corrupt)
    assert result_corrupt.returncode == 0, (
        f"Corrupted demo check failed under {opt_flag}:\n{result_corrupt.stderr}\n{result_corrupt.stdout}"
    )
    assert "SUCCESS: Caught mismatch error" in result_corrupt.stdout


@pytest.mark.parametrize("opt_flag", [[], ["-O"]])
def test_cli_exec_masked_session_failure_normal_and_optimized(opt_flag):
    """exec_masked must raise ClickException (not unhandled AttributeError) when session is None."""
    snippet_exec = """
import sys
from contextlib import contextmanager
from unittest.mock import patch
from click.testing import CliRunner
from secure_gateway.cli import main

@contextmanager
def fake_session_none(*args, **kwargs):
    yield None

runner = CliRunner()
with patch("secure_gateway.hooks.HookStore.session", side_effect=fake_session_none):
    result = runner.invoke(main, ["exec", "--session-id", "s1", "--", "echo", "hello"])
    # Must fail cleanly with ClickException message, not unhandled AttributeError
    if result.exit_code != 0 and "Local execution/masking failed" in (result.output or str(result.exception)):
        print("SUCCESS: Clean failure caught")
        sys.exit(0)
    else:
        print(f"FAILED: exit={result.exit_code}, output={result.output}")
        sys.exit(3)
"""
    result = _run_subprocess([sys.executable] + opt_flag, snippet_exec)
    assert result.returncode == 0, f"exec_masked check failed under {opt_flag}:\n{result.stderr}\n{result.stdout}"
    assert "SUCCESS: Clean failure caught" in result.stdout


@pytest.mark.parametrize("opt_flag", [[], ["-O"]])
def test_handle_hook_session_failure_normal_and_optimized(opt_flag, tmp_path_factory):
    """handle_hook must raise ValueError when session is None under both normal and -O."""
    state_dir = tmp_path_factory.mktemp("state")
    key_file = state_dir / "key"
    key_file.write_text("dummy-key", encoding="ascii")

    snippet_hook = f"""
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from secure_gateway.hooks import handle_hook

@contextmanager
def fake_session_none(*args, **kwargs):
    yield None

payload = {{
    "hook_event_name": "PostToolUse",
    "session_id": "test-sid",
    "tool_response": "sample output",
}}

with patch("secure_gateway.hooks.HookStore.session", side_effect=fake_session_none):
    try:
        handle_hook(payload, Path(r"{state_dir}"), agent="claude")
        print("FAILED: Did not raise")
        sys.exit(4)
    except ValueError as exc:
        if "Session could not be initialized" in str(exc):
            print("SUCCESS: ValueError caught")
            sys.exit(0)
        else:
            print(f"FAILED: Unexpected ValueError: {{exc}}")
            sys.exit(5)
    except Exception as exc:
        print(f"FAILED: Unexpected exception {{type(exc).__name__}}: {{exc}}")
        sys.exit(6)
"""
    result = _run_subprocess([sys.executable] + opt_flag, snippet_hook)
    assert result.returncode == 0, f"handle_hook check failed under {opt_flag}:\n{result.stderr}\n{result.stdout}"
    assert "SUCCESS: ValueError caught" in result.stdout


@pytest.mark.parametrize("opt_flag", [[], ["-O"]])
def test_retained_invariants_code_parser_normal_and_optimized(opt_flag):
    """Parser invariants (raw strings, numbers, identifiers) must execute identically under normal and -O."""
    snippet_parser = """
import sys
from secure_gateway.engine.code_parser import CodeParser

code_samples = [
    ('cpp', 'R"(raw \\" string)"'),
    ('rust', 'r#"raw " rust"#'),
    ('python', 'x = 0x1F + 42.5 + .75e-3'),
    ('javascript', 'const val = 123; // comment'),
    ('sql', 'SELECT "col" FROM [table] WHERE `id` = 1'),
]

for lang, sample in code_samples:
    tokens = CodeParser.tokenize(sample, lang)
    if not tokens:
        print(f"FAILED: empty tokens for {lang}")
        sys.exit(7)

print("SUCCESS: code_parser invariant passed")
"""
    result = _run_subprocess([sys.executable] + opt_flag, snippet_parser)
    assert result.returncode == 0, f"code_parser invariants failed under {opt_flag}:\n{result.stderr}\n{result.stdout}"
    assert "SUCCESS: code_parser invariant passed" in result.stdout


@pytest.mark.parametrize("opt_flag", [[], ["-O"]])
def test_retained_invariants_extended_code_normal_and_optimized(opt_flag):
    """Extended code parser invariants (escapes, indentation) must execute identically under normal and -O."""
    snippet_extended = """
import sys
from secure_gateway.engine.extended_code import tokenize

# Tests escape parsing in _payload and NASM indentation in _contextual_keywords
nasm_sample = '''
section .text
    global _start
_start:
    mov rax, 60
    mov rdi, 0
    syscall
'''
tokens_nasm = tokenize(nasm_sample, "nasm")
if not tokens_nasm:
    raise RuntimeError("No tokens from NASM")

dart_sample = 'String s = "\\\\u{1F600} \\\\x41 hello";'
tokens_dart = tokenize(dart_sample, "dart")
if not tokens_dart:
    raise RuntimeError("No tokens from Dart")

print("SUCCESS: extended_code invariant passed")
"""
    result = _run_subprocess([sys.executable] + opt_flag, snippet_extended)
    assert result.returncode == 0, f"extended_code invariants failed under {opt_flag}:\n{result.stderr}\n{result.stdout}"
    assert "SUCCESS: extended_code invariant passed" in result.stdout


@pytest.mark.parametrize("opt_flag", [[], ["-O"]])
def test_antigravity_install_and_status_normal_and_optimized(opt_flag, tmp_path_factory):
    """Antigravity installation/uninstallation and status must work under normal and -O."""
    test_dir = tmp_path_factory.mktemp("ag_test")
    config_path = test_dir / "antigravity.json"

    snippet_ag = f"""
import sys
from pathlib import Path
from secure_gateway.antigravity_install import configure_antigravity, antigravity_status

path = Path(r"{config_path}")
# 1. Fresh install
backup = configure_antigravity(path, install=True)
status = antigravity_status(path)
if status["ready"] is not True:
    raise RuntimeError(f"Status not ready: {{status}}")

# 2. Re-install is idempotent
configure_antigravity(path, install=True)
status = antigravity_status(path)
if status["ready"] is not True:
    raise RuntimeError(f"Status not ready after reinstall: {{status}}")

# 3. Uninstall
configure_antigravity(path, install=False)
status = antigravity_status(path)
if status["ready"] is not False:
    raise RuntimeError(f"Status still ready after uninstall: {{status}}")

# 4. Uninstall when already uninstalled returns None
ret = configure_antigravity(path, install=False)
if ret is not None:
    raise RuntimeError(f"Expected None on duplicate uninstall, got: {{ret}}")

print("SUCCESS: antigravity install invariant passed")
"""
    result = _run_subprocess([sys.executable] + opt_flag, snippet_ag)
    assert result.returncode == 0, f"antigravity test failed under {opt_flag}:\n{result.stderr}\n{result.stdout}"
    assert "SUCCESS: antigravity install invariant passed" in result.stdout


@pytest.mark.parametrize("opt_flag", [[], ["-O"]])
def test_session_and_automaton_normal_and_optimized(opt_flag):
    """Session original trie and Aho-Corasick automaton invariants work under normal and -O."""
    snippet_session = """
import sys
from secure_gateway.models import MaskMode, SurrogateStrategy, TokenMapping, TokenType
from secure_gateway.session import PrivacySession

session = PrivacySession("test_s", MaskMode.CONTENT_WORDS, SurrogateStrategy.UNICODE)
m1 = TokenMapping(
    original="secret_token",
    surrogate="SURROGATE_1",
    token_type=TokenType.IDENTIFIER,
    generator_index=0,
)
session.forward_store["secret_token"] = m1

# Trigger index and originals_in
found = session.forward_store.originals_in("here is secret_token in text")
if "secret_token" not in found:
    raise RuntimeError(f"Expected secret_token in found: {found}")

# Embedded search
found_embedded = session.forward_store.originals_in("prefix_secret_token_suffix", embedded=True)
if "secret_token" not in found_embedded:
    raise RuntimeError(f"Expected secret_token embedded: {found_embedded}")

print("SUCCESS: session invariant passed")
"""
    result = _run_subprocess([sys.executable] + opt_flag, snippet_session)
    assert result.returncode == 0, f"session test failed under {opt_flag}:\n{result.stderr}\n{result.stdout}"
    assert "SUCCESS: session invariant passed" in result.stdout
