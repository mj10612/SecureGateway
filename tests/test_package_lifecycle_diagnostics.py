"""Content-free diagnostics for the artifact lifecycle proof."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_smoke", ROOT / "scripts/package_smoke.py")
assert spec is not None and spec.loader is not None
package_smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_smoke)
diagnostic = package_smoke.lifecycle_http_diagnostic


@pytest.mark.parametrize("error", [
    "Upstream response could not be safely restored",
    "Upstream transport unavailable",
    "Privacy gateway local I/O failed; request could not be completed",
])
def test_fixed_gateway_error_strings_are_reported(error):
    body = json.dumps({"error": error}).encode()
    summary = diagnostic("tool_call", 502, body, 1, "securegateway-package-89_8lzey")
    assert summary == {"step": "tool_call", "status": 502, "gateway_error": error,
                       "provider_requests": 1}


@pytest.mark.parametrize("body", [
    b"not json",
    b"\xff\xfe",
    json.dumps(["error"]).encode(),
    json.dumps({"error": "leaked ConfidentialCustomer value"}).encode(),
    json.dumps({"error": "mail alice@example.invalid"}).encode(),
    json.dumps({"error": "x" * 121}).encode(),
    json.dumps({"error": "an unrelated private customer value"}).encode(),
    json.dumps({"error": 7}).encode(),
])
def test_unrecognized_or_content_bearing_bodies_are_withheld(body):
    summary = diagnostic("tool_result", 500, body, 2, "work")
    assert summary["gateway_error"] == "unavailable"
    assert "ConfidentialCustomer" not in json.dumps(summary)
    assert "alice@example.invalid" not in json.dumps(summary)


def test_sanitized_upstream_rejection_keeps_only_its_type():
    body = json.dumps({"error": {"type": "invalid_request_error",
                                 "message": "provider text ConfidentialCustomer"}}).encode()
    assert diagnostic("tool_call", 400, body, 1, "w")["gateway_error"] == "upstream:invalid_request_error"
    body = json.dumps({"error": {"message": "provider text"}}).encode()
    assert diagnostic("tool_call", 400, body, 1, "w")["gateway_error"] == "upstream"
    body = json.dumps({"error": {"type": "private-provider-label"}}).encode()
    assert diagnostic("tool_call", 400, body, 1, "w")["gateway_error"] == "upstream"


def test_child_proof_embeds_the_tested_helper_and_labels_both_requests():
    proof = package_smoke.LIFECYCLE_PROOF
    assert proof.startswith(package_smoke.LIFECYCLE_DIAGNOSTICS)
    compile(proof, "<lifecycle-proof>", "exec")
    assert "send(payload, 'tool_call')" in proof and "send(payload, 'tool_result')" in proof
    assert "LIFECYCLE_DIAGNOSTIC " in proof and "file=sys.stderr" in proof


def test_lifecycle_failures_hide_exception_content_and_paths():
    import subprocess
    import sys
    source = package_smoke.sanitized_child_source("raise ValueError('private content and path')")
    result = subprocess.run([sys.executable, '-c', source], capture_output=True, text=True, timeout=30)
    assert result.returncode == 1
    assert result.stderr.strip().startswith('Lifecycle failure: ValueError line=')
    assert not result.stdout


def test_lifecycle_process_check_detects_an_owned_child_exit():
    import subprocess
    import sys
    import time

    namespace = {}
    exec(package_smoke.LIFECYCLE_PROCESSES, namespace)
    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    try:
        assert namespace['process_alive'](process.pid)
        process.terminate()
        process.wait(timeout=10)
        deadline = time.monotonic() + 10
        while namespace['process_alive'](process.pid) and time.monotonic() < deadline:
            time.sleep(.05)
        assert not namespace['process_alive'](process.pid)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


def test_lifecycle_environment_is_confined_and_discards_host_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv('ORCA_CODEX_HOME', 'untrusted-host-home')
    monkeypatch.setenv('PYTHONPATH', 'untrusted-import-path')
    env = package_smoke.isolated_environment(tmp_path)
    assert 'ORCA_CODEX_HOME' not in env and 'PYTHONPATH' not in env
    for key in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'XDG_CONFIG_HOME',
                'CODEX_HOME', 'CLAUDE_CONFIG_DIR'):
        assert Path(env[key]).resolve().is_relative_to(tmp_path.resolve())
