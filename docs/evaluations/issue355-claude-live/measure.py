"""Run the subscription-only Claude Code pilot described in README.md.

Run this file explicitly. It makes at most four live Claude Code invocations.
"""

import json
import os
import queue
import secrets
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from secure_gateway.gateway import PrivacyGateway

def run(route, work, gateway, token):
    env = os.environ.copy()
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_CUSTOM_HEADERS",
                "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDECODE", "CLAUDE_CODE_USE_BEDROCK",
                "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"):
        env.pop(key, None)
    env["ANTHROPIC_BASE_URL"] = "https://api.anthropic.com"
    env["DISABLE_TELEMETRY"] = "1"
    env["DISABLE_ERROR_REPORTING"] = "1"
    if route == "gateway":
        env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{gateway.server_port}/claude"
        env["ANTHROPIC_CUSTOM_HEADERS"] = f"X-SecureGateway-Token: {token}"
    args = [
        "claude", "--print", "--output-format", "stream-json", "--verbose",
        "--include-partial-messages", "--no-session-persistence", "--setting-sources", "",
        "--strict-mcp-config", "--model", "haiku", "--max-turns", "3",
        "--max-budget-usd", "0.15", "--tools", "Read", "--allowedTools", "Read",
        "--permission-mode", "dontAsk", "--system-prompt",
        "Use only the Read tool and follow the user's output format.", "--",
        "Read the local file fixture.txt once using Read. Return only the value following CODE=.",
    ]
    results = {"path": route, "first_text_s": None, "read_calls": 0, "tool_results": 0}
    events = queue.Queue()
    start = time.perf_counter()
    with subprocess.Popen(args, cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          text=True, encoding="utf-8", errors="replace") as proc:
        def consume():
            for line in proc.stdout:
                events.put((time.perf_counter(), line))
            events.put((time.perf_counter(), None))
        reader = threading.Thread(target=consume, daemon=True)
        reader.start()
        try:
            while True:
                remaining = 45 - (time.perf_counter() - start)
                if remaining <= 0:
                    raise queue.Empty
                stamp, line = events.get(timeout=remaining)
                if line is None:
                    break
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                kind = event.get("type")
                if kind == "stream_event":
                    delta = event.get("event", {}).get("delta", {})
                    if delta.get("type") == "text_delta" and delta.get("text") and results["first_text_s"] is None:
                        results["first_text_s"] = round(stamp - start, 3)
                if kind in {"assistant", "user"}:
                    message = event.get("message", {})
                    for block in message.get("content", []):
                        if isinstance(block, dict):
                            if kind == "assistant" and block.get("type") == "tool_use" and block.get("name") == "Read":
                                results["read_calls"] += 1
                            if kind == "user" and block.get("type") == "tool_result" and not block.get("is_error"):
                                results["tool_results"] += 1
                if kind == "result":
                    results["result_s"] = round(stamp - start, 3)
                    results["result_subtype"] = event.get("subtype")
                    results["correct"] = event.get("result", "").strip() == "quartz-lantern"
                    results["api_s"] = round(event.get("duration_api_ms", 0) / 1000, 3)
                    results["num_turns"] = event.get("num_turns")
                    results["model_usage"] = {
                        model: {k: v for k, v in usage.items() if k in (
                            "inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens",
                        )}
                        for model, usage in event.get("modelUsage", {}).items()
                    }
                    if event.get("is_error"):
                        error = str(event.get("result", "")).lower()
                        results["error_class"] = next((tag for tag in (
                            "401", "403", "429", "oauth", "login", "rate limit", "connection",
                            "not found", "invalid", "budget",
                        ) if tag in error), "other")
            results["exit_code"] = proc.wait(timeout=max(0.001, 45 - (time.perf_counter() - start)))
        except (queue.Empty, subprocess.TimeoutExpired):
            proc.kill()
            results["timeout"] = True
    results["process_s"] = round(time.perf_counter() - start, 3)
    return results

def main():
    with tempfile.TemporaryDirectory(prefix="sg-live-355-") as tmp:
        root = Path(tmp)
        work = root / "task"
        work.mkdir()
        (work / "fixture.txt").write_text("CODE=quartz-lantern\n", encoding="utf-8")
        (root / "audit").mkdir()
        token = secrets.token_urlsafe(32)
        gateway = PrivacyGateway(("127.0.0.1", 0), token, state_dir=root / "state",
                                 audit_path=root / "audit" / "logs.sqlite3")
        thread = threading.Thread(target=gateway.serve_forever, daemon=True)
        thread.start()
        try:
            gateway.domain_catalog
            for index, route in enumerate(("direct", "gateway", "gateway", "direct"), 1):
                with gateway.admission:
                    gateway.recent_timings.clear()
                run_result = run(route, work, gateway, token)
                with gateway.admission:
                    run_result["gateway_timings"] = [
                        {key: value for key, value in row.items() if key.endswith("_ms")}
                        for row in gateway.recent_timings if "mask_ms" in row
                    ]
                run_result["attempt"] = index
                print(json.dumps(run_result), flush=True)
                if (run_result.get("exit_code") != 0 or not run_result.get("correct")
                        or run_result["read_calls"] != 1 or run_result["tool_results"] != 1):
                    break
        finally:
            gateway.shutdown()
            thread.join()
            gateway.server_close()


if __name__ == "__main__":
    main()
