"""Native syntax and binding regressions for issues 245, 246, 254 and 255."""
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from secure_gateway.encrypted_session import load_session, save_session
from secure_gateway.engine.code_parser import CodeParser
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import SurrogateStrategy, TokenType
from secure_gateway.session import PrivacySession


def mask(engine, session, source, language):
    return engine.mask_code(source, session.session_id, session.generator,
                            session.forward_store, session.reverse_store,
                            language=language).masked_text


def roundtrip(engine, session, masked, source):
    assert engine.unmask(masked, session.session_id, session.reverse_store,
                         session.strategy, strict=True).unmasked_text == source


def compile_csharp(source, tmp_path):
    dotnet = shutil.which("dotnet")
    if not dotnet:
        pytest.skip("Roslyn SDK required for native C# verification")
    root = Path(dotnet).resolve().parent
    compilers = sorted(root.glob("sdk/*/Roslyn/bincore/csc.dll"))
    refs = sorted(root.glob("packs/Microsoft.NETCore.App.Ref/*/ref/net*/System.Runtime.dll"))
    if not compilers or not refs:
        pytest.skip("Roslyn SDK reference assemblies unavailable")
    source_file = tmp_path / "fixture.cs"
    source_file.write_text(source, encoding="utf-8")
    result = subprocess.run([dotnet, str(compilers[-1]), "/nologo", "/target:library",
                             f"/out:{tmp_path / 'fixture.dll'}", f"/reference:{refs[-1]}",
                             f"/reference:{refs[-1].parent / 'System.Collections.dll'}",
                             str(source_file)], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", [
    "class C { async *f() { yield 1; } }",
    "var obj = { async *f() { yield 1; } };",
    'class C { static async *["privateMethod"]() { yield 1; } }',
    "class C { async *#f() { yield 1; } }",
    "var async = 2; var f = 3; var result = async * f;",
    "class C { async() {} }",
])
def test_javascript_async_generator_native_syntax(strategy, source):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for native JavaScript verification")
    engine = MaskingEngine()
    session = PrivacySession("async-generator", strategy=strategy)
    masked = mask(engine, session, source, "javascript")
    for program in (source, masked):
        checked = subprocess.run([node, "--check"], input=program,
                                 capture_output=True, text=True, timeout=60)
        assert checked.returncode == 0, checked.stderr
    if "async *" not in source:
        assert not re.search(r"\basync\b", masked)
    roundtrip(engine, session, masked, source)


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("body", [
    "static bool M(int x) => x is (not 0);",
    "static bool M(int x) => x is (((not 0)));",
    "static bool M(int x) => x is (not 0 and (not 1));",
    "static bool M(int x) { switch(x) { case (not 0): return true; default: return false; } }",
    "static bool M(bool not) { return (not); }",
])
def test_csharp_parenthesized_not_patterns_compile(strategy, body, tmp_path):
    source = "class C { " + body + " }"
    engine = MaskingEngine()
    session = PrivacySession("not-pattern", strategy=strategy)
    masked = mask(engine, session, source, "csharp")
    compile_csharp(source, tmp_path)
    compile_csharp(masked, tmp_path)
    if "bool not" in source:
        assert not re.search(r"\bnot\b", masked)
    roundtrip(engine, session, masked, source)


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("target", ["get", "set", "field", "param", "setparam", "delegate", "property", "receiver", "file"])
def test_kotlin_annotation_targets_and_identifier_control(strategy, target):
    source = f"@{target}:PrivateAnnotation\nval privateName = 1\n"
    engine = MaskingEngine()
    session = PrivacySession("annotation-target", strategy=strategy)
    masked = mask(engine, session, source, "kotlin")
    assert masked.startswith(f"@{target}:")
    assert "PrivateAnnotation" not in masked and "privateName" not in masked
    roundtrip(engine, session, masked, source)
    control = "fun get() = 1\nfun set() = get()\n"
    second = mask(engine, session, control, "kotlin")
    assert not re.search(r"\b(?:get|set)\b", second)
    roundtrip(engine, session, second, control)


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_kotlin_use_site_independent_grammar(strategy):
    if os.environ.get("SECURE_GATEWAY_NATIVE_PARSERS") != "1":
        pytest.skip("Independent language grammar gate is opt-in")
    import tree_sitter_language_pack
    parser = tree_sitter_language_pack.get_parser("kotlin")
    source = "annotation class PrivateAnnotation\n@get:PrivateAnnotation\nval privateName = 1\n"
    engine = MaskingEngine()
    session = PrivacySession("annotation-grammar", strategy=strategy)
    masked = mask(engine, session, source, "kotlin")
    for program in (source, masked):
        assert not parser.parse(program.encode()).root_node.has_error, program


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("body", [
    "var a = new { value }; p = a.value;",
    "var a = new { value }; var b = a; p = b.value;",
    "var a = new { value }; var b = ((a)); p = ((b)).value;",
    "var a = new { value }; p = (a).value;",
    "p = (new { value }).value;",
    "var a = new { value }; p = a.value; a = new { value }; p = a.value;",
    "{ var a = new { value }; p = a.value; } { var a = new C { value = 1 }; p = a.value; }",
    "var a = new { value = value }; p = a.value;",
    "var a = new { value }; var b = new C { value = 1 }; p = a.value + b.value;",
    "var a = new { value }; p = a.value + this.a.value;",
])
def test_csharp_inferred_accessor_members_native_snapshot(strategy, body, tmp_path):
    source = "class C { int p; int value; C a; int P { set { " + body + " } } }"
    engine = MaskingEngine()
    session = PrivacySession("inferred-property", strategy=strategy)
    masked = mask(engine, session, source, "csharp")
    compile_csharp(source, tmp_path)
    compile_csharp(masked, tmp_path)
    roundtrip(engine, session, masked, source)
    path = tmp_path / "projection.enc"
    save_session(path, session, "synthetic-password")
    loaded = load_session(path, "synthetic-password", session.session_id)
    roundtrip(engine, loaded, masked, source)
    assert mask(engine, loaded, source, "csharp") == masked


def test_unrelated_csharp_value_member_remains_identifier():
    source = "class C { int value; int P { set { var a = new C { value = 1 }; value = a.value; } } }"
    tokens = CodeParser.tokenize(source, "csharp")
    assert any(raw == "value" and kind == TokenType.IDENTIFIER for raw, kind, _ in tokens)
