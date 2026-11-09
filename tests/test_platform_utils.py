"""#335: the OS boundary stays typed and keeps its platform differences local."""

import io
from types import SimpleNamespace

import pytest

from secure_gateway import platform_utils


def test_posix_children_start_their_own_session_by_default(monkeypatch):
    monkeypatch.setattr(platform_utils, "os", SimpleNamespace(name="posix"))
    assert platform_utils.child_process_options() == {"start_new_session": True}
    assert platform_utils.child_process_options(new_process_group=False) == {
        "start_new_session": False
    }


def test_windows_children_only_suppress_the_console_window(monkeypatch):
    monkeypatch.setattr(platform_utils, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(platform_utils, "_CREATE_NO_WINDOW", 0x08000000)
    assert platform_utils.child_process_options() == {"creationflags": 0x08000000}


def test_windows_group_termination_targets_only_a_live_child(monkeypatch):
    commands = []
    monkeypatch.setattr(platform_utils, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        platform_utils.subprocess, "run", lambda argv, **_kwargs: commands.append(argv)
    )
    platform_utils.kill_process_group(SimpleNamespace(pid=1234, poll=lambda: None))
    platform_utils.kill_process_group(SimpleNamespace(pid=99, poll=lambda: 0))
    assert commands == [["taskkill", "/PID", "1234", "/T", "/F"]]


@pytest.mark.parametrize("error", [ProcessLookupError, PermissionError])
def test_posix_group_termination_ignores_an_unavailable_group(monkeypatch, error):
    def unavailable(*_args):
        raise error

    monkeypatch.setattr(
        platform_utils, "os", SimpleNamespace(name="posix", killpg=unavailable)
    )
    monkeypatch.setattr(platform_utils, "signal", SimpleNamespace(SIGKILL=9))
    platform_utils.kill_process_group(SimpleNamespace(pid=1, poll=lambda: None))


def test_process_group_leader_is_never_reported_on_windows(monkeypatch):
    monkeypatch.setattr(
        platform_utils, "os",
        SimpleNamespace(name="posix", getpgrp=lambda: 7, getpid=lambda: 7),
    )
    assert platform_utils.in_process_group_leader() is True
    monkeypatch.setattr(
        platform_utils, "os",
        SimpleNamespace(name="posix", getpgrp=lambda: 8, getpid=lambda: 7),
    )
    assert platform_utils.in_process_group_leader() is False
    monkeypatch.setattr(platform_utils, "os", SimpleNamespace(name="nt"))
    assert platform_utils.in_process_group_leader() is False


def test_exclusive_lock_rejects_a_second_holder(tmp_path):
    path = tmp_path / "owner"
    path.write_bytes(b"1")
    with path.open("r+b") as first, path.open("r+b") as second:
        platform_utils.lock_file_exclusive(first)
        with pytest.raises(OSError):
            platform_utils.lock_file_exclusive(second)


def test_read_available_stops_at_one_buffered_block():
    stream = io.BytesIO(b"abcdef")
    assert platform_utils.read_available(stream, 4) == b"abcd"
    assert platform_utils.read_available(stream, 4) == b"ef"
    assert platform_utils.read_available(stream, 4) == b""
