"""Runtime-provided names and Lua local attribute regression checks."""
import shutil
import subprocess

import pytest

from secure_gateway.encrypted_session import load_session, save_session
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import SurrogateStrategy
from secure_gateway.session import PrivacySession


def mask(engine, session, source, language):
    return engine.mask_code(source, session.session_id, session.generator,
                            session.forward_store, session.reverse_store,
                            language=language).masked_text


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", [
    "switch (7) { 7 { if ($_ -ne 7) { exit 1 } } }; exit 0",
    "function privateFunction { if (-not ($args -contains 7)) { throw 1 } }; privateFunction 7",
    "function privateFunction { if (-not (${ArGs} -contains 7)) { throw 1 } }; privateFunction 7",
    "switch (7) { 7 { if (${PSItem} -ne 7) { exit 1 } } }; exit 0",
])
def test_powershell_automatic_bindings(strategy, source):
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell required for native binding check")
    engine = MaskingEngine()
    session = PrivacySession("automatic", strategy=strategy)
    masked = mask(engine, session, source, "powershell")
    for program in (source, masked):
        result = subprocess.run([executable, "-NoProfile", "-NonInteractive", "-Command", program],
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
    assert engine.unmask(masked, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_powershell_scopes_and_ordinary_variables(strategy):
    engine = MaskingEngine()
    session = PrivacySession("automatic-scopes", strategy=strategy)
    source = "$global:PID; ${local:ArGs}; $script:PSItem; $env:args; $privateArgs; ${args-extra}"
    masked = mask(engine, session, source, "powershell")
    assert "$global:PID" in masked and "${local:ArGs}" in masked
    assert "$script:PSItem" in masked
    assert "$env:args" not in masked and "$privateArgs" not in masked and "args-extra" not in masked
    assert engine.unmask(masked, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", [
    "local privateValue <const> = 7",
    "local privateHandle <close> = nil",
    "local privateValue <const>, privateHandle <close> = 7, nil",
    "local privateValue < -- attribute\n const > = 7",
])
def test_lua_attributes_and_snapshot(strategy, source, tmp_path):
    engine = MaskingEngine()
    session = PrivacySession("lua-attributes", strategy=strategy)
    masked = mask(engine, session, source, "lua")
    for attribute in ("const", "close"):
        if attribute in source:
            assert attribute in masked
    assert engine.unmask(masked, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source
    path = tmp_path / "session.enc"
    save_session(path, session, "test-password")
    restored = load_session(path, "test-password")
    assert engine.unmask(masked, restored.session_id, restored.reverse_store,
                         strategy, strict=True).unmasked_text == source
    ordinary = mask(engine, restored, "local const = 7; local close = const; return close", "lua")
    assert " const " not in ordinary and " close " not in ordinary


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_lua_relational_names_are_not_attributes(strategy):
    engine = MaskingEngine()
    session = PrivacySession("lua-relational", strategy=strategy)
    source = "local const = 7; local close = 8; local result = 1 < const and close > 2"
    masked = mask(engine, session, source, "lua")
    assert "const" not in masked and "close" not in masked
    assert engine.unmask(masked, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source



@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_lua54_native_attributes_when_available(strategy):
    lua54 = pytest.importorskip("lupa.lua54", reason="Optional Lua 5.4 runtime")
    engine = MaskingEngine()
    session = PrivacySession("lua-native-attributes", strategy=strategy)
    for source in ("local privateValue <const> = 7",
                   "local privateHandle <close> = nil",
                   "local privateValue <const>, privateHandle <close> = 7, nil"):
        masked = mask(engine, session, source, "lua")
        lua54.LuaRuntime().execute(source)
        lua54.LuaRuntime().execute(masked)
