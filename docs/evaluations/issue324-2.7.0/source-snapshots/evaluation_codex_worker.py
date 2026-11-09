"""Opt-in fresh Codex CLI worker: ``python -m secure_gateway.evaluation_codex_worker``.

Only an explicit call to this module starts inference. The adapter has no API
fallback and does not resume history. The same OS user and subscription auth are
shared; fresh cwd and ignored configuration are not a hard filesystem jail.
"""

import json
from hashlib import sha256
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

from secure_gateway.evaluation_worker import (
    MAX_WORKER_INPUT_BYTES, MAX_WORKER_OUTPUT_BYTES, capture_worker_process,
    strict_json, validate_request, validate_result,
)


def _prompt(request: dict) -> str:
    prompt = (
        "Complete this semantic text task using only the messages supplied below. "
        "Do not use tools, commands, files, browsing, skills, agents or external context. "
        f"Limit your output to {request['max_output_tokens']} tokens.\n"
        "Messages (role labels are part of the supplied task):\n"
        + json.dumps(request["messages"], ensure_ascii=False)
    )
    if request["role"] == "grade":
        prompt += (
            "\nGrade exactly the supplied criteria. Return only a JSON object with "
            'a "grades" array, one object per criterion: {"id": string, "passed": boolean, '
            '"evidence": nonempty string}. Use no other criterion IDs.\nCriteria:\n'
            + json.dumps(request["criteria"], ensure_ascii=False)
        )
    else:
        prompt += (
            "\nReturn only your answer to the supplied task as plain text. "
            "Perform the requested response, including a clarification question when needed; "
            "do not merely paraphrase what the request means. "
            "If an unavailable tool or hidden fact prevents an action, state that specific limitation "
            "and complete the parts supported by the visible messages."
        )
    return prompt


def _parse_events(raw: bytes) -> dict[str, int] | None:
    usage = None
    completed = False
    for line in raw.splitlines():
        if not line.strip():
            continue
        event = strict_json(line)
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise ValueError("Codex returned invalid events.")
        kind = event["type"]
        if kind in ("error", "turn.failed"):
            raise ValueError("Codex inference failed.")
        if kind.startswith("item."):
            item = event.get("item")
            if not isinstance(item, dict) or item.get("type") not in ("agent_message", "reasoning"):
                # Unknown item types fail closed: future tool types must not be
                # accidentally accepted as uncontaminated comprehension work.
                raise ValueError("Codex used a tool during a semantic task.")
        elif kind not in ("thread.started", "turn.started", "turn.completed"):
            raise ValueError("Codex returned an unsupported event.")
        if kind == "turn.completed":
            if completed:
                raise ValueError("Codex returned multiple turns.")
            completed = True
            value = event.get("usage")
            if value is not None:
                if (
                    not isinstance(value, dict)
                    or type(value.get("input_tokens")) is not int
                    or type(value.get("output_tokens")) is not int
                    or any(type(number) is not int or number < 0 for number in value.values())
                ):
                    raise ValueError("Codex returned invalid usage.")
                usage = dict(value)
                usage["total_tokens"] = value["input_tokens"] + value["output_tokens"]
    if not completed:
        raise ValueError("Codex did not complete a turn.")
    return usage


def run_codex_worker(request: dict) -> dict:
    """Run one fresh CLI session; the caller must explicitly authorize inference."""
    validate_request(request)
    codex = shutil.which("codex")
    if codex is None:
        raise ValueError("Codex CLI is not installed.")
    # Preserve auth locations without changing HOME or CODEX_HOME. Environment
    # allowlisting drops conversation/config injection and paid API fallback.
    allowed_env = {
        "PATH", "HOME", "USERPROFILE", "CODEX_HOME", "SYSTEMROOT", "WINDIR",
        "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE",
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy", "all_proxy", "no_proxy",
        "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "NODE_EXTRA_CA_CERTS",
    }
    child_env = {
        key: value for key, value in os.environ.items()
        if key in allowed_env
    }
    inherited_group = (
        os.name != "nt"
        and os.environ.get("SECURE_GATEWAY_EVAL_GROUP") == "1"
        and os.getpgrp() == os.getpid()  # type: ignore[attr-defined]
    )
    with tempfile.TemporaryDirectory(prefix="secure-gateway-eval-") as directory:
        root = Path(directory)
        workspace = root / "workspace"
        workspace.mkdir(mode=0o700)
        version = capture_worker_process(
            [codex, "--version"], b"", timeout=10, cwd=workspace, env=child_env,
            new_process_group=not inherited_group,
        ).stdout.decode("utf-8").strip()
        if not version or len(version) > 200:
            raise ValueError("Codex CLI returned an invalid version.")
        output = root / "last-message.txt"
        command = [
            codex, "exec", "--ephemeral", "--skip-git-repo-check",
            "--ignore-user-config", "--ignore-rules", "--sandbox", "read-only",
            "--model", request["model"], "--json", "--output-last-message", str(output),
            "-c", 'forced_login_method="chatgpt"',
            "-c", "project_doc_max_bytes=0", "-c", "developer_instructions=\"\"",
            "-c", "web_search=\"disabled\"",
            "-c", "features.multi_agent=false", "-",
        ]
        if request.get('reasoning_effort'):
            command[-1:-1] = ['-c', 'model_reasoning_effort=' + json.dumps(request['reasoning_effort'])]
        events = capture_worker_process(
            command, _prompt(request).encode("utf-8"), timeout=300,
            cwd=workspace, env=child_env, new_process_group=not inherited_group,
        )
        usage = _parse_events(events.stdout)
        try:
            with output.open("rb") as stream:
                raw_final = stream.read(MAX_WORKER_OUTPUT_BYTES + 1)
            if len(raw_final) > MAX_WORKER_OUTPUT_BYTES:
                raise ValueError("Codex final output limit exceeded.")
            final = raw_final.decode("utf-8")
        except (OSError, UnicodeError):
            raise ValueError("Codex did not return a valid final message.") from None
    result: dict[str, Any] = {
        "job_id": request["job_id"], "model": request["model"],
        "metadata": {
            "provider": "codex-cli", "cli_version": version,
            "model_source": "requested_cli_setting", "requested_model": request["model"],
            "fresh_session": True, "sandbox": "read-only", "tool_events": 0,
            "authentication": "chatgpt subscription only; no API fallback",
            "isolation_limits": ["same OS user", "shared subscription auth", "no hard filesystem jail"],
            "output_budget_enforcement": "UTF-8 byte guard; reported output-token overages rejected; no provider hard cap",
            "max_output_tokens": request["max_output_tokens"],
            "requested_reasoning_effort": request.get('reasoning_effort', 'cli_default_unverified'),
            "adapter_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "task_response_mode": "answer_visible_task" if request["role"] == "interpret" else "independent_grade",
        },
    }
    if usage is not None:
        result["usage"] = usage
    if request["role"] == "grade":
        grade_result = strict_json(final)
        if not isinstance(grade_result, dict) or set(grade_result) != {"grades"}:
            raise ValueError("Codex returned invalid grading JSON.")
        result["grades"] = grade_result["grades"]
    else:
        result["response"] = final
    return validate_result(result, request)


def main() -> int:
    """Read one bounded request and emit only the JSON protocol result."""
    try:
        raw = sys.stdin.buffer.read(MAX_WORKER_INPUT_BYTES + 1)
        if len(raw) > MAX_WORKER_INPUT_BYTES:
            raise ValueError("Worker input limit exceeded.")
        result = run_codex_worker(strict_json(raw))
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        return 0
    except (ValueError, OSError):
        # Never echo model text, argv, auth, environment, prompts or stderr.
        sys.stderr.write("Codex evaluation worker failed.\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
