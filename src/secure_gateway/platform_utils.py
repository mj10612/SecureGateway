"""Narrow OS boundary for process groups, advisory locks and pipe reads.

POSIX and Windows expose different primitives for the same operation, and type
checkers model the missing ones as ``attr-defined`` failures. Keeping every
difference here gives callers one fully typed API and one reviewed place for
platform behavior; the CI matrix runs the Windows and POSIX branches.
"""

from __future__ import annotations

import importlib
import io
import os
import signal
import subprocess
from typing import Any, BinaryIO, cast

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def child_process_options(*, new_process_group: bool = True) -> dict[str, Any]:
    """Return ``Popen`` keywords that isolate an owned child.

    POSIX starts a new session so a failure can terminate the child's
    descendants; Windows has no equivalent here and only suppresses the console
    window a GUI parent would otherwise flash.
    """
    if os.name == "nt":
        return {"creationflags": _CREATE_NO_WINDOW}
    return {"start_new_session": new_process_group}


def kill_process_group(process: subprocess.Popen[bytes]) -> None:
    """Terminate an owned child's process group on a best-effort basis.

    An already-exited or reparented descendant, a child started outside its own
    group, or a denied kill raises nothing: the caller still kills and reaps the
    directly owned child.
    """
    if os.name == "nt":
        if process.poll() is not None:
            # Best effort only: exited/reparented descendants may no longer be
            # associated with this PID. A Windows job object is not owned here.
            return
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                creationflags=_CREATE_NO_WINDOW,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            # intentional: best-effort tree kill on Windows; process may already have exited
            pass
        return
    # POSIX-only: both names are absent from Windows interpreters and stubs.
    killpg = getattr(os, "killpg", None)
    if killpg is None:
        return
    try:
        killpg(process.pid, getattr(signal, "SIGKILL"))
    except (ProcessLookupError, PermissionError):
        # intentional: group termination can be unavailable even for an owned child
        pass


def cancel_process(process: subprocess.Popen[bytes]) -> None:
    """Cancel and always reap an owned child, including descendants."""
    kill_process_group(process)
    if process.poll() is None:
        process.kill()
    process.wait()


def in_process_group_leader() -> bool:
    """Report whether this process leads its own group; Windows has none."""
    # POSIX-only: Windows exposes neither getpgrp nor process groups here.
    getpgrp = getattr(os, "getpgrp", None)
    return getpgrp is not None and getpgrp() == os.getpid()


def lock_file_exclusive(handle) -> None:
    """Take a non-blocking exclusive advisory lock on one byte, or raise OSError.

    Both primitives lock from the current offset, so the handle is rewound first.
    """
    handle.seek(0)
    if os.name == "nt":
        msvcrt = importlib.import_module("msvcrt")
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        fcntl = importlib.import_module("fcntl")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def read_available(stream: BinaryIO, size: int) -> bytes:
    """Read up to one buffered block without waiting for the full buffer.

    ``subprocess`` pipes are buffered readers, but ``BinaryIO`` does not promise
    ``read1``. The cast keeps that containment in one documented place.
    """
    return cast(io.BufferedIOBase, stream).read1(size)
