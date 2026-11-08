"""The artifact gate must isolate homes and fail a required native skip."""

import importlib.util
from pathlib import Path
import sys

import pytest


@pytest.fixture
def smoke():
    path = Path(__file__).resolve().parents[1] / "scripts/package_smoke.py"
    spec = importlib.util.spec_from_file_location("package_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_isolated_environment_drops_user_credentials(smoke, tmp_path, monkeypatch):
    for key in ("ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "OPENAI_API_KEY",
                "ORCA_CODEX_HOME", "PYTHONPATH", "PYTHONHOME"):
        monkeypatch.setenv(key, "private-user-setting")
    env = smoke.isolated_environment(tmp_path)
    assert not any("private-user-setting" == value for value in env.values())
    for key in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_CONFIG_HOME",
                "CODEX_HOME", "CLAUDE_CONFIG_DIR"):
        assert Path(env[key]).is_relative_to(tmp_path)


@pytest.mark.parametrize("env", [{}, {"SECURE_GATEWAY_CODEX_BINARY": "unavailable-native-binary"}])
def test_required_native_binaries_cannot_silently_skip(smoke, env):
    with pytest.raises(SystemExit, match="Required native host unavailable"):
        smoke.native_binaries(env)


def test_required_native_accepts_existing_executables(smoke):
    result = smoke.native_binaries({"SECURE_GATEWAY_CLAUDE_BINARY": sys.executable,
                                    "SECURE_GATEWAY_CODEX_BINARY": sys.executable})
    assert set(result) == {"claude", "codex"}


@pytest.mark.parametrize("case_xml", ["<testcase><skipped/></testcase>" * 4,
                                     "<testcase/>" * 3, "<testcase><failure/></testcase>" * 4])
def test_required_native_rejects_incomplete_test_evidence(smoke, tmp_path, monkeypatch, case_xml):
    root = tmp_path / "source"
    (root / "tests").mkdir(parents=True)
    (root / "tests/test_gateway_hosts.py").write_text("# synthetic native gate fixture")
    (tmp_path / "native-release.xml").write_text("<testsuite>" + case_xml + "</testsuite>")
    monkeypatch.setattr(smoke.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(smoke.subprocess, "check_output", lambda *args, **kwargs: "configured-version")
    with pytest.raises(SystemExit, match="requires four completed"):
        smoke.verify_native(Path(sys.executable), tmp_path, {}, root, {"claude": sys.executable,
                                                                    "codex": sys.executable})


def test_installed_lifecycle_outside_repository(smoke, tmp_path):
    # The artifact command runs this same proof in clean wheel/sdist venvs.
    # Here the test interpreter is editable-installed; do not call this a
    # distribution-build or cross-version upgrade result.
    env = smoke.isolated_environment(tmp_path)
    smoke.verify_lifecycle(Path(sys.executable), tmp_path, env)
    assert not (tmp_path / "home/state/installation.json").exists()
