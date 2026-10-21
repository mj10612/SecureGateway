"""Trusted command capture bounds bytes before any decoding or masking."""

import subprocess
import sys
import time

import pytest

from secure_gateway.command_capture import capture_command
from secure_gateway import command_capture


def test_group_permission_failure_still_terminates_and_reaps_child(monkeypatch):
    from types import SimpleNamespace

    calls = []

    def denied(*args):
        raise PermissionError("process group unavailable")

    child = SimpleNamespace(
        pid=123,
        poll=lambda: None,
        kill=lambda: calls.append("kill"),
        wait=lambda: calls.append("wait"),
    )
    monkeypatch.setattr(command_capture, "os", SimpleNamespace(name="posix", killpg=denied))
    monkeypatch.setattr(command_capture, "signal", SimpleNamespace(SIGKILL=9))
    command_capture._cancel(child)
    assert calls == ["kill", "wait"]


def command(code):
    return [sys.executable, "-c", code]


def test_binary_capture_preserves_exit_status_and_arguments():
    argv = command(
        "import sys;sys.stdout.buffer.write(bytes([255]));sys.stderr.buffer.write(b'err');sys.exit(7)"
    )
    result = capture_command(argv)
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.args == argv
    assert result.returncode == 7
    assert result.stdout == bytes([255])
    assert result.stderr == b"err"


def test_exact_combined_output_boundary_is_allowed():
    result = capture_command(
        command(
            "import sys;sys.stdout.buffer.write(b'123');sys.stderr.buffer.write(b'45')"
        ),
        max_output_bytes=5,
    )
    assert result.stdout == b"123"
    assert result.stderr == b"45"


def test_combined_output_over_boundary_refuses_without_raw_output():
    with pytest.raises(ValueError, match="^Local command output limit exceeded\\.$"):
        capture_command(
            command(
                "import sys;sys.stdout.buffer.write(b'SECRET');sys.stderr.buffer.write(b'OTHER')"
            ),
            max_output_bytes=10,
        )


def test_both_large_streams_are_consumed_without_pipe_deadlock():
    result = capture_command(
        command(
            "import sys;sys.stdout.buffer.write(b'o'*1000000);sys.stderr.buffer.write(b'e'*1000000)"
        ),
        timeout=5,
        max_output_bytes=2000000,
    )
    assert result.stdout == b"o" * 1000000
    assert result.stderr == b"e" * 1000000


def test_timeout_terminates_and_reaps_child(tmp_path, monkeypatch):
    children = []
    popen = subprocess.Popen

    def tracked(*args, **kwargs):
        child = popen(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", tracked)
    pid_file = tmp_path / "pid"
    argv = command(
        f"import os,time;from pathlib import Path;Path({str(pid_file)!r}).write_text(str(os.getpid()));time.sleep(30)"
    )
    start = time.monotonic()
    with pytest.raises(ValueError, match="^Local command timed out\\.$"):
        capture_command(argv, timeout=0.5)
    assert time.monotonic() - start < 5
    assert pid_file.exists()
    assert children[0].poll() is not None


def test_cap_cancels_and_reaps_running_child(monkeypatch):
    children = []
    popen = subprocess.Popen

    def tracked(*args, **kwargs):
        child = popen(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", tracked)
    with pytest.raises(ValueError, match="output limit exceeded"):
        capture_command(
            command(
                "import sys,time;sys.stdout.buffer.write(b'SECRET'*100);sys.stdout.flush();time.sleep(30)"
            ),
            max_output_bytes=1,
        )
    assert children[0].poll() is not None


def test_inherited_descendant_pipe_cannot_block_timeout(tmp_path):
    pid_file = tmp_path / "descendant"
    code = (
        "import subprocess,sys;from pathlib import Path;"
        "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);"
        f"Path({str(pid_file)!r}).write_text(str(child.pid))"
    )
    start = time.monotonic()
    try:
        with pytest.raises(ValueError, match="timed out"):
            capture_command(command(code), timeout=0.5)
        assert time.monotonic() - start < 5
    finally:
        if pid_file.exists():
            import os
            import signal

            pid = int(pid_file.read_text())
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


@pytest.mark.parametrize(
    "timeout,limit", [(0, 1), (-1, 1), (float("nan"), 1), (1, 0), (1, True)]
)
def test_invalid_bounds_are_refused(timeout, limit):
    with pytest.raises(ValueError):
        capture_command(command("pass"), timeout=timeout, max_output_bytes=limit)
