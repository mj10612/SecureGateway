"""Native shell bindings and bounded-copy lexical regression checks."""
from pathlib import Path
import shutil
import subprocess

import pytest

from secure_gateway.encrypted_session import load_session, save_session
from secure_gateway.engine.code_parser import CodeParser
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import SurrogateStrategy
from secure_gateway.session import PrivacySession


def mask(engine, session, source, language):
    return engine.mask_code(source, session.session_id, session.generator,
                            session.forward_store, session.reverse_store,
                            language=language).masked_text


def restore(engine, session, source):
    return engine.unmask(source, session.session_id, session.reverse_store,
                         session.strategy, strict=True).unmasked_text


def shell_program(source, language):
    if language == "bash":
        git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        executable = str(git_bash) if git_bash.exists() else shutil.which("bash")
        if not executable:
            pytest.skip("Bash required for independent binding verification")
        args = [executable, "--noprofile", "--norc", "-c", source]
    else:
        executable = shutil.which("pwsh") or shutil.which("powershell")
        if not executable:
            pytest.skip("PowerShell required for independent constant verification")
        args = [executable, "-NoProfile", "-NonInteractive", "-Command", source]
    result = subprocess.run(args, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", [
    'done=7\n[[ "$done" == 7 ]]\n',
    'done=7\nif=8\n[[ "$done" == 7 && "$if" == 8 ]]\n',
    'function privateFunction() { local done if; done=7; if=8; [[ "$done" == 7 && "$if" == 8 ]]; }\nprivateFunction\n',
    'export done=7\n[[ "${done}" == 7 ]]\n',
    'for done in 7; do [[ "$done" == 7 ]]; done\n',
    'done=7\n((done+=1))\n((done == 8))\n',
    'for ((done=7; done<8; done++)); do [[ "$done" == 7 ]]; done\n',
    'done[0]=7; [[ "${done[0]}" == 7 ]]\n',
])
def test_bash_reserved_assignment_names_keep_bindings(strategy, source):
    engine = MaskingEngine()
    session = PrivacySession("bash-keyword-binding", strategy=strategy)
    masked = mask(engine, session, source, "bash")
    shell_program(source, "bash")
    shell_program(masked, "bash")
    assert "$done" not in masked and "${done}" not in masked
    assert restore(engine, session, masked) == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", [
    'private\\\nName=7\n[[ "$privateName" == 7 ]]\n',
    'private\\\nName=7\n((privateName+=1))\n[[ "$pri\\\nvateName" == 8 ]]\n',
    'privateName=7\n[[ "${private\\\nName}" == 7 ]]\n',
    'privateName=7\n[[ "$\\\nprivateName" == 7 ]]\n',
])
def test_bash_spliced_identifiers_execute_and_survive_snapshot(strategy, source, tmp_path):
    engine = MaskingEngine()
    session = PrivacySession("bash-spliced-binding", strategy=strategy)
    masked = mask(engine, session, source, "bash")
    shell_program(source, "bash")
    shell_program(masked, "bash")
    assert restore(engine, session, masked) == source
    path = tmp_path / "session.enc"
    save_session(path, session, "synthetic-shell-password")
    loaded = load_session(path, "synthetic-shell-password", session.session_id)
    assert restore(engine, loaded, masked) == source
    continuation = 'privateName=7\n[[ "$priva\\\nteName" == 7 ]]\n'
    second = mask(engine, loaded, continuation, "bash")
    shell_program(second, "bash")
    assert restore(engine, loaded, second) == continuation
    assert restore(engine, loaded, masked) == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", [
    'if (-not $true) { exit 7 }; if ($false) { exit 8 }; if ($null -ne $null) { exit 9 }; exit 0',
    'if (-not ${TRUE}) { exit 7 }; if (${False}) { exit 8 }; if (${Null} -ne $NULL) { exit 9 }; exit 0',
    '$privateValue=$true; if (-not $privateValue) { exit 7 }; if ($FALSE) { exit 8 }; exit 0',
    'if (-not $global:true) { exit 7 }; if (-not $local:TRUE) { exit 8 }; if (-not ${script:true}) { exit 9 }; if ($private:false) { exit 10 }; exit 0',
])
def test_powershell_constants_preserve_native_values(strategy, source):
    engine = MaskingEngine()
    session = PrivacySession("powershell-constants", strategy=strategy)
    masked = mask(engine, session, source, "powershell")
    shell_program(source, "powershell")
    shell_program(masked, "powershell")
    assert "privateValue" not in masked
    assert restore(engine, session, masked) == source


def test_powershell_scoped_or_extended_names_are_not_intrinsic_constants():
    engine = MaskingEngine()
    session = PrivacySession("powershell-real-variables")
    source = '$env:true; ${true?}; $env:false'
    masked = mask(engine, session, source, "powershell")
    assert "true" not in masked and "false" not in masked
    assert restore(engine, session, masked) == source


class SliceObservedSource(str):
    """Account for cumulative full suffix copies, independent of CPU speed."""
    def __new__(cls, text):
        result = super().__new__(cls, text)
        result.suffix_characters = 0
        return result

    def __getitem__(self, key):
        if isinstance(key, slice) and key.stop is None and isinstance(key.start, int):
            self.suffix_characters += max(0, len(self) - key.start)
        return super().__getitem__(key)


@pytest.mark.parametrize("language", [
    "bash", "csharp", "powershell", "php", "kotlin", "lua", "nasm", "swift",
    "ruby", "dart", "r", "nix", "gdscript", "vbnet", "vba",
])
@pytest.mark.parametrize("repetitions", [200, 400])
def test_extended_lexing_does_not_repeatedly_copy_remaining_source(language, repetitions):
    source = SliceObservedSource("privateName = 1;\n" * repetitions)
    tokens = CodeParser.tokenize(source, language)
    assert "".join(raw for raw, _, _ in tokens) == source
    assert len(tokens) >= repetitions * 3
    assert source.suffix_characters <= len(source) * 2
