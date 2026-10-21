"""Bounded binary capture for explicitly trusted local command arguments."""

import math
import os
import signal
import subprocess
from threading import Event, Lock, Thread
import time
from typing import BinaryIO, Sequence


def _cancel(process: subprocess.Popen[bytes]) -> None:
    """Cancel the owned process, including descendants where the OS permits."""
    if os.name == "nt":
        if process.poll() is None:
            # Best effort only: exited/reparented descendants may no longer be
            # associated with this PID. A Windows job object is not owned here.
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)  # type: ignore[attr-defined]
        except (ProcessLookupError, PermissionError):
            # Group termination can be unavailable even for an owned child.
            # Still terminate and reap the child through its direct handle.
            pass
    if process.poll() is None:
        process.kill()
    process.wait()  # Always reap the directly owned child.


def capture_command(
    argv: Sequence[str],
    *,
    timeout: float = 180.0,
    max_output_bytes: int = 16 * 1024 * 1024,
) -> subprocess.CompletedProcess[bytes]:
    """Return complete binary stdout/stderr, or fail with a fixed error.

    The byte limit is shared across both streams; its exact boundary is valid.
    Timeout includes draining captured output. POSIX cancellation kills the new
    process group. Windows tree termination is best effort while the child is
    alive; detached descendants are outside this helper's ownership. Readers are
    daemon threads with bounded joins, so inherited descendant pipes cannot make
    cancellation block. No partial output is returned on capture failure.
    """
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
        or isinstance(max_output_bytes, bool)
        or not isinstance(max_output_bytes, int)
        or max_output_bytes <= 0
    ):
        raise ValueError("Invalid local command capture limits.")
    options = (
        {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    process = subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **options
    )
    chunks: list[list[bytes]] = [[], []]
    lock = Lock()
    changed = Event()
    total = 0
    error = None
    finished = 0

    def read_stream(stream: BinaryIO, index: int) -> None:
        nonlocal total, error, finished
        try:
            while True:
                block = stream.read1(65536)  # type: ignore[attr-defined]
                if not block:
                    break
                with lock:
                    if error is not None:
                        break
                    total += len(block)
                    if total > max_output_bytes:
                        error = "Local command output limit exceeded."
                        changed.set()
                        break
                    chunks[index].append(block)
                changed.set()
        except (OSError, ValueError):
            with lock:
                error = error or "Local command output could not be captured."
        finally:
            # The reader owns closing its stream. Main-thread close can wait
            # forever on a buffered-reader lock held by an inherited pipe read.
            stream.close()
            with lock:
                finished += 1
            changed.set()

    assert process.stdout is not None and process.stderr is not None
    readers = [
        Thread(target=read_stream, args=(stream, index), daemon=True)
        for index, stream in enumerate((process.stdout, process.stderr))
    ]
    deadline = time.monotonic() + timeout
    try:
        for reader in readers:
            reader.start()
        while True:
            changed.clear()
            with lock:
                failure, drained = error, finished == 2
            if failure is not None:
                raise ValueError(failure)
            if drained and process.poll() is not None:
                return subprocess.CompletedProcess(
                    argv, process.returncode, b"".join(chunks[0]), b"".join(chunks[1])
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("Local command timed out.")
            changed.wait(min(remaining, 0.05))
    except BaseException:
        _cancel(process)
        raise
    finally:
        for reader in readers:
            if reader.ident is not None:
                reader.join(timeout=0.1)
