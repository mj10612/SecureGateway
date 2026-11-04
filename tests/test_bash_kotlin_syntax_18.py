"""Native/control grammar regressions for Bash comments and Kotlin accessors."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import SurrogateStrategy
from secure_gateway.session import PrivacySession


def masked(source, language, strategy):
    e = MaskingEngine()
    s = PrivacySession("syntax18", strategy=strategy)
    result = e.mask_code(source, s.session_id, s.generator, s.forward_store,
                         s.reverse_store, language=language).masked_text
    assert e.unmask(result, s.session_id, s.reverse_store, strategy,
                    strict=True).unmasked_text == source
    return result


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", [
    "privateValue=private#suffix; exit 7\n",
    "privateValue=private#suffix; # actual private comment\nexit 7\n",
    "privateValue=private\\#suffix; exit 7\n",
    "privateValue='private#suffix'; exit 7\n",
    "privateValue=private\\ #suffix; exit 7\n",
    "privateValue=private\\\n#suffix; exit 7\n",
    "privateValue=private#suffix; privateOther=${privateValue#private}; exit 7\n",
    "# actual private comment; exit 9\nexit 7\n",
])
def test_bash_hash_keeps_following_command(strategy, source):
    bash = Path("C:/Program Files/Git/bin/bash.exe")
    executable = str(bash) if bash.is_file() else shutil.which("bash")
    if not executable:
        pytest.skip("Native Bash required")
    result = masked(source, "bash", strategy)
    assert "exit 7" in result
    for text in (source, result):
        run = subprocess.run([executable, "--noprofile", "--norc", "-c", text],
                             capture_output=True, text=True, timeout=20)
        assert run.returncode == 7, (text, run.stderr)


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("getter", [
    "get() = this", "get() { return this }", "\nget() = this",
    "/* private comment */ get() = this",
])
def test_kotlin_inline_and_multiline_getters(strategy, getter):
    source = "class PrivateClass {\nval privateValue: PrivateClass " + getter + "\n}\n"
    result = masked(source, "kotlin", strategy)
    assert "get()" in result
    if os.environ.get("SECURE_GATEWAY_NATIVE_PARSERS") == "1":
        from tree_sitter_language_pack import get_parser
        parser = get_parser("kotlin")
        for text in (source, result):
            assert not parser.parse(text.encode()).root_node.has_error, text


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", [
    "fun get() = 7\nval privateValue = get()\n",
    "class PrivateClass { fun get() = 7; val privateValue = this.get() }\n",
    "fun privateFunction() { val privateValue = 7; get() }\nfun get() = 7\n",
])
def test_kotlin_ordinary_get_function_remains_private(strategy, source):
    result = masked(source, "kotlin", strategy)
    assert "get" not in result


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_kotlin_explicit_getter_setter_keeps_accessor_context(strategy):
    source = "class PrivateClass {\nvar privateValue: PrivateClass = this\nget() = field\nset(privateArgument) { field = privateArgument }\n}\n"
    result = masked(source, "kotlin", strategy)
    assert "get()" in result and "set(" in result and "field" in result
    if os.environ.get("SECURE_GATEWAY_NATIVE_PARSERS") == "1":
        from tree_sitter_language_pack import get_parser
        parser = get_parser("kotlin")
        for text in (source, result):
            assert not parser.parse(text.encode()).root_node.has_error, text


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_bash_exit_variable_still_masks_and_real_comments_stay_comments(strategy):
    source = "exit=7; privateValue=private#suffix; exit $exit\n"
    result = masked(source, "bash", strategy)
    assert "exit=" not in result and "$exit" not in result and "; exit $" in result
    commented = masked("# private comment\nexit 7\n", "bash", strategy)
    assert commented.startswith("#") and "private comment" not in commented


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_kotlin_inline_typed_getter_and_setter(strategy):
    source = "class PrivateClass {\nvar privateValue: PrivateClass get(): PrivateClass = this; set(privateArgument) {}\n}\n"
    result = masked(source, "kotlin", strategy)
    assert "get():" in result and "set(" in result
    if os.environ.get("SECURE_GATEWAY_NATIVE_PARSERS") == "1":
        from tree_sitter_language_pack import get_parser
        parser = get_parser("kotlin")
        for text in (source, result):
            assert not parser.parse(text.encode()).root_node.has_error, text
