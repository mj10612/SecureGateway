"""Explicitly invoked, bounded subprocess transport for evaluation workers.

Workers run as the caller's OS user. An empty working directory separates task
context; it is not a filesystem jail or a security boundary for an untrusted
executable. Worker commands must be explicitly selected by the caller.
"""

import json
import math
import os
from pathlib import Path
import subprocess
from threading import Event, Lock, Thread
import time
from typing import Any, BinaryIO

from secure_gateway.command_capture import _cancel


MAX_WORKER_INPUT_BYTES = 1024 * 1024
MAX_WORKER_OUTPUT_BYTES = 1024 * 1024


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _integer(value: Any) -> bool:
    return type(value) is int and value >= 0


def strict_json(raw: str | bytes) -> Any:
    """Parse protocol JSON without duplicate keys or nonstandard constants."""
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict:
        result: dict = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Worker JSON contains duplicate keys.")
            result[key] = value
        return result

    def reject_constant(_value: str) -> None:
        raise ValueError("Worker JSON contains an invalid constant.")

    try:
        return json.loads(raw, object_pairs_hook=object_pairs, parse_constant=reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("Worker returned invalid JSON.") from None


def validate_request(request: dict) -> bytes:
    """Validate the transport contract before launching any executable."""
    allowed = {"role", "job_id", "model", "max_output_tokens", "messages", "criteria", "reasoning_effort"}
    if (
        not isinstance(request, dict)
        or set(request) - allowed
        or request.get("role") not in ("interpret", "grade")
        or not _nonempty(request.get("job_id"))
        or not _nonempty(request.get("model"))
        or not _integer(request.get("max_output_tokens"))
        or not 1 <= request["max_output_tokens"] <= 131072
        or not isinstance(request.get("messages"), list)
        or not 1 <= len(request["messages"]) <= 128
    ):
        raise ValueError("Invalid worker request.")
    if 'reasoning_effort' in request and request['reasoning_effort'] not in {'low', 'medium', 'high', 'xhigh'}:
        raise ValueError("Invalid reasoning effort.")
    for message in request["messages"]:
        if (
            not isinstance(message, dict)
            or set(message) != {"role", "content"}
            or message["role"] not in ("system", "user", "assistant")
            or not isinstance(message["content"], str)
        ):
            raise ValueError("Invalid worker messages.")
    if request["role"] == "grade":
        criteria = request.get("criteria")
        if not isinstance(criteria, list) or not 1 <= len(criteria) <= 128:
            raise ValueError("Invalid worker criteria.")
        seen: set[str] = set()
        for criterion in criteria:
            if (
                not isinstance(criterion, dict)
                or set(criterion) != {"id", "description"}
                or not _nonempty(criterion["id"])
                or not _nonempty(criterion["description"])
                or criterion["id"] in seen
            ):
                raise ValueError("Invalid worker criteria.")
            seen.add(criterion["id"])
    elif "criteria" in request:
        raise ValueError("Interpretation workers cannot receive grading criteria.")
    try:
        encoded = json.dumps(request, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ValueError("Invalid worker request encoding.") from None
    if len(encoded) > MAX_WORKER_INPUT_BYTES:
        raise ValueError("Worker input limit exceeded.")
    return encoded


def validate_result(result: Any, request: dict) -> dict:
    """Validate job correlation, identity, evidence and reported token usage.

    Four UTF-8 bytes per requested output token is an output-size guard, not an
    exact tokenizer count or provider-side generation cap. Reported output token
    overages fail closed. Total usage includes input and may exceed that limit.
    """
    allowed = {"job_id", "model", "response", "grades", "usage", "metadata"}
    if (
        not isinstance(result, dict)
        or set(result) - allowed
        or result.get("job_id") != request["job_id"]
        or not _nonempty(result.get("model"))
    ):
        raise ValueError("Worker returned an invalid identity or result.")
    if "metadata" in result and not isinstance(result["metadata"], dict):
        raise ValueError("Worker returned invalid metadata.")
    if "usage" in result:
        usage = result["usage"]
        if (
            not isinstance(usage, dict)
            or not _integer(usage.get("total_tokens"))
            or any(not _integer(value) for value in usage.values())
            or usage.get("output_tokens", 0) > request["max_output_tokens"]
            or usage.get("output_tokens", 0) > usage["total_tokens"]
        ):
            raise ValueError("Worker returned invalid or excessive token usage.")
    if request["role"] == "interpret":
        if "grades" in result or not _nonempty(result.get("response")):
            raise ValueError("Worker returned an invalid interpretation.")
        text = result["response"]
    else:
        grades = result.get("grades")
        if "response" in result or not isinstance(grades, list):
            raise ValueError("Worker returned invalid grades.")
        expected = {criterion["id"] for criterion in request["criteria"]}
        seen: set[str] = set()
        for grade in grades:
            if (
                not isinstance(grade, dict)
                or set(grade) != {"id", "passed", "evidence"}
                or not isinstance(grade["id"], str)
                or grade["id"] not in expected
                or grade["id"] in seen
                or type(grade["passed"]) is not bool
                or not _nonempty(grade["evidence"])
            ):
                raise ValueError("Worker returned invalid grades.")
            seen.add(grade["id"])
        if seen != expected:
            raise ValueError("Worker omitted grading criteria.")
        text = json.dumps(grades, ensure_ascii=False)
    try:
        over_budget = len(text.encode("utf-8")) > 4 * request["max_output_tokens"]
    except UnicodeError:
        raise ValueError("Worker returned invalid text encoding.") from None
    if over_budget:
        raise ValueError("Worker response output limit exceeded.")
    return result


def capture_worker_process(
    command: list[str], input_bytes: bytes, *, timeout: float, cwd: Path,
    env: dict[str, str] | None = None,
    new_process_group: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    """Bound both output pipes and a potentially blocked stdin writer."""
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
        or not isinstance(command, list)
        or not command
        or any(not isinstance(arg, str) or "\0" in arg for arg in command)
        or not command[0]
    ):
        raise ValueError("Invalid worker execution arguments.")
    options = (
        {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
        if os.name == "nt" else {"start_new_session": new_process_group}
    )
    deadline = time.monotonic() + timeout
    try:
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=cwd, env=env, **options,
        )
    except OSError:
        raise ValueError("Worker executable could not be started.") from None
    chunks: list[list[bytes]] = [[], []]
    lock = Lock()
    changed = Event()
    total = 0
    finished = 0
    failure: str | None = None

    def read_stream(stream: BinaryIO, index: int) -> None:
        nonlocal total, finished, failure
        try:
            while True:
                block = stream.read1(65536)  # type: ignore[attr-defined]
                if not block:
                    break
                with lock:
                    if failure is not None:
                        break
                    total += len(block)
                    if total > MAX_WORKER_OUTPUT_BYTES:
                        failure = "Worker output limit exceeded."
                        changed.set()
                        break
                    chunks[index].append(block)
                changed.set()
        except (OSError, ValueError):
            with lock:
                failure = failure or "Worker output could not be captured."
        finally:
            stream.close()
            with lock:
                finished += 1
            changed.set()

    def write_input() -> None:
        assert process.stdin is not None
        try:
            process.stdin.write(input_bytes)
            process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            pass
        finally:
            try:
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass

    assert process.stdout is not None and process.stderr is not None
    threads = [
        Thread(target=read_stream, args=(stream, index), daemon=True)
        for index, stream in enumerate((process.stdout, process.stderr))
    ] + [Thread(target=write_input, daemon=True)]
    try:
        for thread in threads:
            thread.start()
        while True:
            changed.clear()
            with lock:
                error, drained = failure, finished == 2
            if error is not None:
                raise ValueError(error)
            if drained and process.poll() is not None:
                if process.returncode:
                    raise ValueError("Worker executable failed.")
                return subprocess.CompletedProcess(
                    command, process.returncode, b"".join(chunks[0]), b"".join(chunks[1])
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("Worker execution timed out.")
            changed.wait(min(remaining, 0.05))
    except BaseException:
        if new_process_group or os.name == "nt":
            _cancel(process)
        else:
            # An outer evaluation runner owns the group. Keep nested inference
            # in that group so its deadline also cancels provider activity.
            if process.poll() is None:
                process.kill()
            process.wait()
        raise
    finally:
        for thread in threads:
            if thread.ident is not None:
                thread.join(timeout=0.1)


def execute_worker(command: list[str], request: dict, *, timeout: float, cwd: Path) -> dict:
    """Run one explicitly selected JSON worker in an existing empty workspace.

    Authentication/environment remain available to the selected executable. No
    stdout, stderr, command, environment or request content enters error messages.
    """
    encoded = validate_request(request)
    try:
        empty = cwd.is_dir() and not any(cwd.iterdir())
    except OSError:
        empty = False
    if not empty:
        raise ValueError("Worker workspace must be an existing empty directory.")
    child_env = dict(os.environ)
    child_env["SECURE_GATEWAY_EVAL_GROUP"] = "1"
    completed = capture_worker_process(command, encoded, timeout=timeout, cwd=cwd, env=child_env)
    return validate_result(strict_json(completed.stdout), request)
