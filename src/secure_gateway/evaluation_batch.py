"""Opt-in lean and batched Codex evaluation transport (issue #364).

The frozen native adapter (``evaluation_codex_worker``) stays byte-identical so
saved evidence and reference audits that pin its hash remain valid. This module
is a second, explicitly selected adapter that lowers Codex subscription usage:

* lean session: per-call command-line overrides disable tool features that a
  semantic task never needs and replace the long default agent instructions with
  a short neutral one. Nothing is written to the user's Codex configuration; the
  overrides exist only on the argv of the evaluation subprocess, so ordinary CLI
  use keeps its own settings.
* batching: several independent interpretation tasks (same model and condition)
  or several grading cases share one fresh call. Tasks inside one call can see
  each other; originals, gold behaviour and other conditions' answers still never
  reach an interpreter. Order is shuffled with a recorded seed and tasks get
  opaque labels.

Isolation is unchanged: fresh ephemeral session, empty working directory,
read-only sandbox, ChatGPT subscription login only (no API key fallback) and any
non-message event fails closed. A usage/credit limit is reported as a distinct
fixed error so runners can stop cleanly and resume later.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
import os
from pathlib import Path
import random
import shutil
import tempfile
from typing import Any

from secure_gateway.evaluation_worker import (
    MAX_WORKER_OUTPUT_BYTES, capture_worker_process, strict_json, validate_request,
    validate_result,
)
from secure_gateway.platform_utils import in_process_group_leader


# Codex CLI feature flags a semantic task never needs. Measured on codex-cli
# 0.167.1 (docs/EVALUATION_COST.md): together with LEAN_BASE_INSTRUCTIONS the
# fixed input per call fell from about 15,100 to about 7,070 tokens.
# ``code_mode_host`` is deliberately kept: disabling it emits a warning item that
# the fail-closed event filter would (correctly) treat as a non-message event.
LEAN_DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "apps", "plugins", "image_generation", "view_image",
    "goals", "skill_search", "tool_suggest", "sleep_tool", "computer_use", "browser_use",
    "browser_use_external", "in_app_browser", "hooks", "remote_plugin",
    "plugin_discovery_prefetch", "incremental_tools", "deferred_tool_world_state",
    "memories", "fast_mode", "ultrafast_mode", "guardian_approval", "mentions_v2",
    "workspace_dependencies", "in_app_chat", "multi_agent",
)
LEAN_BASE_INSTRUCTIONS = "You are a careful assistant. Answer only from the user's message."

# Model for NEW preregistered runs (owner's choice, 2026-11-12). Runs frozen with
# another model keep that model; never mix models inside one comparison.
DEFAULT_EVAL_MODEL = "gpt-6-luna"
MAX_BATCH_ITEMS = 32
USAGE_LIMIT_ERROR = "Codex usage limit reached."
_LIMIT_MARKERS = ("usage limit", "out of credits", "rate limit", "quota")

_ALLOWED_ENV = {
    "PATH", "HOME", "USERPROFILE", "CODEX_HOME", "SYSTEMROOT", "WINDIR",
    "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE",
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
    "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "NODE_EXTRA_CA_CERTS",
}

_BATCH_INTERPRET_RULES = (
    "The user message contains several independent tasks. Treat each task as if it were the only "
    "message you received: follow that task's own instructions and input only, and never carry "
    "facts, names or decisions from one task into another. For each task perform the requested "
    "response, including a clarification question when needed; do not merely paraphrase what the "
    "request means. If an unavailable tool or hidden fact prevents an action, state that specific "
    "limitation and complete the parts supported by that task's input."
)


class UsageLimitReached(ValueError):
    """The subscription refused the call because of a usage or credit limit."""

    def __init__(self) -> None:
        super().__init__(USAGE_LIMIT_ERROR)


def adapter_hash() -> str:
    """Byte hash of this adapter, recorded in every result's metadata."""
    return sha256(Path(__file__).read_bytes()).hexdigest()


def lean_command(
    codex: str, *, model: str, output: Path, instructions_file: Path,
    reasoning_effort: str | None = None,
) -> list[str]:
    """Return the per-call argv; every override is local to this subprocess."""
    command = [
        codex, "exec", "--ephemeral", "--skip-git-repo-check",
        "--ignore-user-config", "--ignore-rules", "--sandbox", "read-only",
        "--model", model, "--json", "--output-last-message", str(output),
        "-c", 'forced_login_method="chatgpt"',
        "-c", "project_doc_max_bytes=0", "-c", 'developer_instructions=""',
        "-c", 'web_search="disabled"',
        "-c", "model_instructions_file=" + json.dumps(str(instructions_file)),
    ]
    for feature in LEAN_DISABLED_FEATURES:
        command += ["--disable", feature]
    if reasoning_effort:
        command += ["-c", "model_reasoning_effort=" + json.dumps(reasoning_effort)]
    return command + ["-"]


def parse_events(raw: bytes) -> dict[str, int] | None:
    """Accept only message/reasoning events; classify subscription limits."""
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
            detail = event.get("error") if kind == "turn.failed" else event
            message = detail.get("message") if isinstance(detail, dict) else None
            if isinstance(message, str) and any(m in message.lower() for m in _LIMIT_MARKERS):
                raise UsageLimitReached()
            raise ValueError("Codex inference failed.")
        if kind.startswith("item."):
            item = event.get("item")
            if not isinstance(item, dict) or item.get("type") not in ("agent_message", "reasoning"):
                # Unknown item types, including CLI warnings, fail closed.
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


def _prompt(request: dict, batch: bool) -> str:
    prompt = (
        "Complete this semantic text task using only the messages supplied below. "
        "Do not use tools, commands, files, browsing, skills, agents or external context. "
        f"Limit your output to {request['max_output_tokens']} tokens.\n"
        "Messages (role labels are part of the supplied task):\n"
        + json.dumps(request["messages"], ensure_ascii=False)
    )
    if request["role"] == "grade":
        return prompt + (
            "\nGrade exactly the supplied criteria. Return only a JSON object with "
            'a "grades" array, one object per criterion: {"id": string, "passed": boolean, '
            '"evidence": nonempty string}. Use no other criterion IDs.\nCriteria:\n'
            + json.dumps(request["criteria"], ensure_ascii=False)
        )
    if batch:
        return prompt + (
            "\n" + _BATCH_INTERPRET_RULES + ' Return only a JSON object {"answers": [{"task": '
            'string, "answer": nonempty string}]} with exactly one answer per task label and '
            "the answer as the plain text you would have sent for that task alone."
        )
    return prompt + (
        "\nReturn only your answer to the supplied task as plain text. "
        "Perform the requested response, including a clarification question when needed; "
        "do not merely paraphrase what the request means. "
        "If an unavailable tool or hidden fact prevents an action, state that specific limitation "
        "and complete the parts supported by the visible messages."
    )


def run_lean_worker(request: dict, *, batch: bool = False) -> dict:
    """Run one fresh lean CLI session; the caller must explicitly authorize inference.

    ``batch=True`` asks an interpretation call for the JSON answer list produced by
    :func:`build_interpret_batch`; the raw JSON is returned as ``response`` and must
    be split with :func:`parse_interpret_batch`.
    """
    validate_request(request)
    if batch and request["role"] != "interpret":
        raise ValueError("Invalid worker request.")
    codex = shutil.which("codex")
    if codex is None:
        raise ValueError("Codex CLI is not installed.")
    child_env = {key: value for key, value in os.environ.items() if key in _ALLOWED_ENV}
    inherited_group = (
        os.environ.get("SECURE_GATEWAY_EVAL_GROUP") == "1" and in_process_group_leader()
    )
    with tempfile.TemporaryDirectory(prefix="secure-gateway-eval-") as directory:
        root = Path(directory)
        workspace = root / "workspace"
        workspace.mkdir(mode=0o700)
        instructions = root / "instructions.md"
        instructions.write_text(LEAN_BASE_INSTRUCTIONS, encoding="utf-8")
        version = capture_worker_process(
            [codex, "--version"], b"", timeout=10, cwd=workspace, env=child_env,
            new_process_group=not inherited_group,
        ).stdout.decode("utf-8").strip()
        if not version or len(version) > 200:
            raise ValueError("Codex CLI returned an invalid version.")
        output = root / "last-message.txt"
        command = lean_command(
            codex, model=request["model"], output=output, instructions_file=instructions,
            reasoning_effort=request.get("reasoning_effort"),
        )
        events = capture_worker_process(
            command, _prompt(request, batch).encode("utf-8"), timeout=600,
            cwd=workspace, env=child_env, new_process_group=not inherited_group, check=False,
        )
        # Classify the event stream first so a usage/credit limit (which also exits
        # nonzero) stops the run cleanly; any other nonzero exit still fails closed.
        usage = parse_events(events.stdout)
        if events.returncode:
            raise ValueError("Worker executable failed.")
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
            "max_output_tokens": request["max_output_tokens"],
            "requested_reasoning_effort": request.get("reasoning_effort", "cli_default_unverified"),
            "adapter": "lean-batch", "adapter_source_sha256": adapter_hash(),
            "disabled_features": list(LEAN_DISABLED_FEATURES),
            "base_instructions_sha256": sha256(LEAN_BASE_INSTRUCTIONS.encode("utf-8")).hexdigest(),
            "task_response_mode": (
                "independent_grade" if request["role"] == "grade"
                else "answer_visible_tasks_batched" if batch else "answer_visible_task"
            ),
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


def _check_batch_size(count: int) -> None:
    if not 1 <= count <= MAX_BATCH_ITEMS:
        raise ValueError("Invalid batch size.")


def build_interpret_batch(
    items: list[dict], *, job_id: str, model: str, max_output_tokens_per_item: int,
    seed: int, reasoning_effort: str | None = None,
) -> tuple[dict, dict[str, str]]:
    """Combine independent interpretation tasks into one request.

    ``items`` are ``{"key", "instructions", "input"}`` — exactly what a single
    interpreter would have seen (its system and user message). Returns the request
    and the opaque label -> key map needed to split the answers.
    """
    _check_batch_size(len(items))
    keys = [item.get("key") for item in items]
    if len(set(keys)) != len(keys) or any(
        not isinstance(item, dict) or set(item) != {"key", "instructions", "input"}
        or not all(isinstance(item[name], str) for name in item) or not item["key"]
        for item in items
    ):
        raise ValueError("Invalid batch items.")
    order = list(items)
    random.Random(seed).shuffle(order)
    labels = {f"T{index + 1}": item["key"] for index, item in enumerate(order)}
    tasks = [
        {"task": label, "instructions": item["instructions"], "input": item["input"]}
        for label, item in zip(labels, order)
    ]
    request: dict[str, Any] = {
        "role": "interpret", "job_id": job_id, "model": model,
        "max_output_tokens": max_output_tokens_per_item * len(items) + 64,
        "messages": [
            {"role": "system", "content": _BATCH_INTERPRET_RULES},
            {"role": "user", "content": json.dumps({"tasks": tasks}, ensure_ascii=False)},
        ],
    }
    if reasoning_effort:
        request["reasoning_effort"] = reasoning_effort
    validate_request(request)
    return request, labels


def parse_interpret_batch(
    response: str, labels: dict[str, str], *, max_output_tokens_per_item: int,
) -> dict[str, str]:
    """Split a batched answer into per-key answers; any defect rejects the batch."""
    data = strict_json(response.strip())
    answers = data.get("answers") if isinstance(data, dict) and set(data) == {"answers"} else None
    if not isinstance(answers, list):
        raise ValueError("Codex returned an invalid batch answer.")
    result: dict[str, str] = {}
    for entry in answers:
        if (
            not isinstance(entry, dict) or set(entry) != {"task", "answer"}
            or entry["task"] not in labels or labels[entry["task"]] in result
            or not isinstance(entry["answer"], str) or not entry["answer"].strip()
            or len(entry["answer"].encode("utf-8")) > 4 * max_output_tokens_per_item
        ):
            raise ValueError("Codex returned an invalid batch answer.")
        result[labels[entry["task"]]] = entry["answer"]
    if len(result) != len(labels):
        raise ValueError("Codex omitted batch answers.")
    return result


def build_grade_batch(
    case_requests: dict[str, dict], *, job_id: str, seed: int,
) -> tuple[dict, dict[str, str]]:
    """Combine per-case grade requests that share model, effort and system rules.

    Each case keeps its own material and criteria; criterion IDs are prefixed with
    an opaque case label (``K1::<original id>``). Returns the request and the
    label -> case key map for :func:`split_grade_batch`.
    """
    _check_batch_size(len(case_requests))
    requests = list(case_requests.items())
    for _key, request in requests:
        validate_request(request)
        if request["role"] != "grade" or [m["role"] for m in request["messages"]] != ["system", "user"]:
            raise ValueError("Invalid batch items.")
    first = requests[0][1]
    shared = (first["model"], first.get("reasoning_effort"), first["messages"][0]["content"])
    if any((r["model"], r.get("reasoning_effort"), r["messages"][0]["content"]) != shared
           for _key, r in requests):
        raise ValueError("Batched grade requests must share model, effort and rules.")
    random.Random(seed).shuffle(requests)
    labels = {f"K{index + 1}": key for index, (key, _r) in enumerate(requests)}
    cases, criteria = [], []
    for label, (_key, request) in zip(labels, requests):
        cases.append({"case": label, "material": request["messages"][1]["content"]})
        for criterion in request["criteria"]:
            criteria.append({
                "id": label + "::" + criterion["id"],
                "description": "Case " + label + ". " + criterion["description"],
            })
    combined: dict[str, Any] = {
        "role": "grade", "job_id": job_id, "model": first["model"],
        "max_output_tokens": sum(r["max_output_tokens"] for _key, r in requests),
        "messages": [
            {"role": "system", "content": first["messages"][0]["content"] + (
                " Several independent cases follow; grade each case only against its own "
                "material, and quote evidence only from that case's responses.")},
            {"role": "user", "content": json.dumps({"cases": cases}, ensure_ascii=False)},
        ],
        "criteria": criteria,
    }
    if first.get("reasoning_effort"):
        combined["reasoning_effort"] = first["reasoning_effort"]
    validate_request(combined)
    return combined, labels


def split_grade_batch(grades: list[dict], labels: dict[str, str]) -> dict[str, list[dict]]:
    """Return each case's grades with its original criterion IDs.

    The caller must still verify every quote against that case's own responses
    and re-grade a failing case on its own (one retry), exactly as for single calls.
    """
    result: dict[str, list[dict]] = {key: [] for key in labels.values()}
    for grade in grades:
        label, _, original = grade["id"].partition("::")
        if label not in labels or not original:
            raise ValueError("Worker returned invalid grades.")
        result[labels[label]].append({**grade, "id": original})
    return result


def estimate_budget(
    *, interpret_jobs: int, grade_cases: int, interpret_batch: int, grade_batch: int,
    fixed_input_tokens: int, interpret_content_tokens: int, grade_content_tokens: int,
    regrade_rate: float = 0.05,
) -> dict[str, int]:
    """Predict calls and raw tokens before a run; inputs are per-item averages."""
    if (min(interpret_jobs, grade_cases, fixed_input_tokens, interpret_content_tokens,
            grade_content_tokens) < 0 or interpret_batch < 1 or grade_batch < 1
            or not 0 <= regrade_rate <= 1):
        raise ValueError("Invalid budget input.")
    interpret_calls = math.ceil(interpret_jobs / interpret_batch)
    grade_calls = math.ceil(grade_cases / grade_batch)
    regrade_calls = math.ceil(grade_cases * regrade_rate)
    raw = (
        interpret_calls * fixed_input_tokens + interpret_jobs * interpret_content_tokens
        + (grade_calls + regrade_calls) * fixed_input_tokens
        + (grade_cases + regrade_calls) * grade_content_tokens
    )
    return {
        "interpret_calls": interpret_calls, "grade_calls": grade_calls,
        "regrade_calls": regrade_calls,
        "total_calls": interpret_calls + grade_calls + regrade_calls, "raw_tokens": raw,
        "raw_tokens_per_case": math.ceil(raw / grade_cases) if grade_cases else raw,
    }


def agreement(reference: dict[Any, bool], candidate: dict[Any, bool]) -> dict[str, Any]:
    """Pass/fail agreement between two runs over the same keys (case, arm[, criterion])."""
    if set(reference) != set(candidate) or not reference:
        raise ValueError("Agreement requires the same nonempty keys.")
    same = sum(reference[key] == candidate[key] for key in reference)
    return {
        "items": len(reference), "agree": same, "rate": same / len(reference),
        "reference_passes": sum(reference.values()), "candidate_passes": sum(candidate.values()),
        "reference_only": sum(reference[k] and not candidate[k] for k in reference),
        "candidate_only": sum(candidate[k] and not reference[k] for k in reference),
    }
