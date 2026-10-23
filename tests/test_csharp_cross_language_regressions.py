"""Native binding regressions for issues 233, 234 and 235."""
import shutil
import subprocess
from pathlib import Path

import pytest

from secure_gateway.encrypted_session import load_session, save_session
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import SurrogateStrategy
from secure_gateway.session import PrivacySession


def mask(engine, session, source, language):
    return engine.mask_code(source, session.session_id, session.generator,
                            session.forward_store, session.reverse_store,
                            language=language).masked_text


def restored(engine, session, text):
    return engine.unmask(text, session.session_id, session.reverse_store,
                         session.strategy, strict=True).unmasked_text


def compile_csharp(source, tmp_path):
    dotnet = shutil.which("dotnet")
    if not dotnet:
        pytest.skip("Roslyn SDK required for independent C# compile verification")
    root = Path(dotnet).resolve().parent
    compilers = sorted(root.glob("sdk/*/Roslyn/bincore/csc.dll"))
    refs = sorted(root.glob("packs/Microsoft.NETCore.App.Ref/*/ref/net*/System.Runtime.dll"))
    if not compilers or not refs:
        pytest.skip("Roslyn SDK reference assemblies unavailable")
    source_file = tmp_path / "fixture.cs"
    source_file.write_text(source, encoding="utf-8")
    checked = subprocess.run([dotnet, str(compilers[-1]), "/nologo", "/target:library",
                              f"/out:{tmp_path / 'fixture.dll'}", f"/reference:{refs[-1]}",
                              f"/reference:{refs[-1].parent / 'System.Collections.dll'}",
                              str(source_file)], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=60)
    assert checked.returncode == 0, checked.stdout + checked.stderr


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("accessors", [
    "int P { get { return p; } set { if (value > 0) { p = value; } } }",
    "int P { set => p = value; }",
    "public int P { get => p; private set { p = value; } }",
    "int P { init { p = value; } }",
    "int P { set { p = M(value: value); p = value > 0 ? 1 + value : value; } } int M(int value) { return value; }",
    "int P { set { var a = new { value = 1 }; p = a.value + value; value = 2; } }",
    "int value; int P { set { var a = new C() { value = 1 }; p = a.value + value; } }",
    "event D E { add { p = value == null ? 0 : 1; } remove => p = value == null ? 0 : 1; }",
])
def test_accessor_value_compiles_and_local_value_is_masked(strategy, accessors, tmp_path):
    source = "delegate void D(); class C { int p; " + accessors + " int Run() { int value = 42; return value; } }"
    engine = MaskingEngine()
    session = PrivacySession("accessor", strategy=strategy)
    masked = mask(engine, session, source, "csharp")
    compile_csharp(source, tmp_path)
    compile_csharp(masked, tmp_path)
    assert "int value = 42" not in masked
    assert restored(engine, session, masked) == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("reference", ["va\u200blue", r"va\u200Blue", r"@va\u200Blue"])
def test_csharp_format_characters_binding_snapshot(strategy, reference, tmp_path):
    source = "class C { static int Run() { int value = 42; return " + reference + "; } }"
    engine = MaskingEngine()
    session = PrivacySession("format-identifier", strategy=strategy)
    masked = mask(engine, session, source, "csharp")
    compile_csharp(source, tmp_path)
    compile_csharp(masked, tmp_path)
    path = tmp_path / "session.enc"
    save_session(path, session, "local-regression-password")
    loaded = load_session(path, "local-regression-password", session.session_id)
    assert restored(engine, loaded, masked) == source
    continued = "class C { static int Run() { int value = 42; return @value; } }"
    second = mask(engine, loaded, continued, "csharp")
    compile_csharp(second, tmp_path)
    assert restored(engine, loaded, second) == continued
    assert restored(engine, loaded, masked) == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("snapshot", [False, True])
@pytest.mark.parametrize("javascript", ["var K = 7; if (K !== 7) throw 1;",
                                       r"var K = 7; if (\u004b !== 7) throw 1;"])
def test_cross_language_alias_native_execution(strategy, reverse, snapshot, javascript, tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for independent binding verification")
    python = "\uff2b = 7\nK += 1"
    programs = [(python, "python"), (javascript, "javascript")]
    if reverse:
        programs.reverse()
    engine = MaskingEngine()
    session = PrivacySession("cross-native", strategy=strategy)
    first = mask(engine, session, *programs[0])
    if snapshot:
        path = tmp_path / "session.enc"
        save_session(path, session, "local-regression-password")
        session = load_session(path, "local-regression-password", session.session_id)
    second = mask(engine, session, *programs[1])
    for output, (source, language) in zip([first, second], programs):
        assert restored(engine, session, output) == source
        if language == "python":
            namespace = {}
            exec(output, namespace)
            assert 8 in namespace.values()
        else:
            checked = subprocess.run([node, "--eval", output], capture_output=True, text=True, timeout=60)
            assert checked.returncode == 0, checked.stderr
    # A second encrypted round-trip must retain both language contexts.
    path = tmp_path / "both.enc"
    save_session(path, session, "local-regression-password")
    loaded = load_session(path, "local-regression-password", session.session_id)
    for output, (source, language) in zip([first, second], programs):
        assert restored(engine, loaded, output) == source
        continued = mask(engine, loaded, source, language)
        assert continued == output
        assert restored(engine, loaded, continued) == source
