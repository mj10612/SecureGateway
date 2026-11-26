"""Bounded live Claude Code/Codex measurement for SecureGateway issue #355."""

import argparse
import concurrent.futures
import http.client
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch
from uuid import uuid4

import psutil

import secure_gateway.gateway as gateway_module
import secure_gateway.gateway_stream as stream_module
from secure_gateway import __version__
from secure_gateway.evaluation_batch import LEAN_DISABLED_FEATURES
from secure_gateway.gateway import GatewayHandler, GatewaySession, PrivacyGateway
from secure_gateway.gateway_audit import AuditStore


CLI_LIMIT = 60
SUITE_LIMIT = 480
TOKEN_LIMIT = 220_000  # Reported tokens, checked after each group. In-flight calls may cross it.
MAX_INVOCATIONS = 16
CLAUDE_MODEL = "haiku"
CODEX_MODEL = "gpt-6.2-sol"
CLOCK = time.perf_counter
TLS = threading.local()
CONTENTS = {"response.output_text.delta", "response.refusal.delta"}


def has_text(frame):
    data = "\n".join(line[5:].lstrip() for line in frame.splitlines() if line.startswith("data:"))
    if not data or data == "[DONE]":
        return False
    try:
        event = json.loads(data)
    except ValueError:
        return False
    if not isinstance(event, dict):
        return False
    delta = event.get("delta")
    if event.get("type") in CONTENTS:
        return isinstance(delta, str) and bool(delta)
    return isinstance(delta, dict) and delta.get("type") == "text_delta" and bool(delta.get("text"))


class TimedHandler(GatewayHandler):
    def capture_response_headers(self, headers):
        row = getattr(TLS, "row", None)
        if row is not None:
            mime = headers.get_content_type() if headers.get("Content-Type") is not None else "missing"
            known = {"application/json", "text/event-stream", "text/plain", "missing"}
            row["upstream_mime"] = mime if mime in known else "other"
        return super().capture_response_headers(headers)

    def send_body(self, status, body, content_type="application/json"):
        result = super().send_body(status, body, content_type)
        row = getattr(TLS, "row", None)
        if row is not None and status == 200:
            row["buffered_body_written_ms"] = round((CLOCK() - TLS.rx_at) * 1000, 3)
        return result

    def do_POST(self):
        label = self.headers.get("X-Benchmark-Run")
        TLS.row = {} if label in self.server.samples else None
        TLS.rx_at = CLOCK()
        TLS.partial = b""
        try:
            return super().do_POST()
        finally:
            row = TLS.row
            TLS.row = None
            TLS.partial = b""
            if row is not None:
                row["handler_complete_ms"] = round((CLOCK() - TLS.rx_at) * 1000, 3)
                meta = getattr(self, "audit_metadata", None) or {}
                row.update({k: meta[k] for k in (
                    "status", "outcome", "upstream_attempted", "input_bytes", "masked_bytes", "output_bytes",
                ) if k in meta})
                with self.server.admission:
                    if label in self.server.samples:
                        self.server.samples[label].append(row)
                    self.server.admission.notify_all()


class TimingLog(list):
    def append(self, timings):
        if TLS.row is not None:
            TLS.row.update({k: v for k, v in timings.items() if k.endswith("_ms")})


class TimedWriter:
    def __init__(self, writer, row):
        self.writer = writer
        self.row = row
        self.pending_text = False

    def write(self, data):
        if any(has_text(frame) for frame in data.decode("utf-8").split("\n\n")):
            self.pending_text = True
        return self.writer.write(data)

    def flush(self):
        self.writer.flush()
        if self.pending_text:
            elapsed = round((CLOCK() - TLS.rx_at) * 1000, 3)
            self.row.setdefault("gateway_first_text_flushed_ms", elapsed)
            self.row["gateway_last_text_flushed_ms"] = elapsed
            self.pending_text = False


def instrument(stack):
    old_feed = stream_module.EventRestorer.feed
    old_relay = gateway_module.relay_stream
    old_connect = http.client.HTTPSConnection.connect
    old_safe_read = http.client.HTTPResponse._safe_read
    old_request = GatewaySession.request

    def mask_request(session, *args, **kwargs):
        masked = old_request(session, *args, **kwargs)
        row = getattr(TLS, "row", None)
        if row is not None:
            row["request_stream_true"] = masked.get("stream") is True
        return masked

    def read_chunk(response, amount):
        data = old_safe_read(response, amount)
        row = getattr(TLS, "row", None)
        if row is not None and response.chunked and "gateway_first_chunk_text_ms" not in row:
            merged = (TLS.partial + data).replace(b"\r\n", b"\n")
            *frames, TLS.partial = merged.split(b"\n\n")
            if len(TLS.partial) > 262144:
                TLS.partial = b""
            if any(has_text(frame.decode("utf-8", errors="replace")) for frame in frames):
                row["gateway_first_chunk_text_ms"] = round((CLOCK() - TLS.rx_at) * 1000, 3)
        return data

    def relay(handler, *args, **kwargs):
        row = TLS.row
        if row is None:
            return old_relay(handler, *args, **kwargs)
        writer = handler.wfile
        handler.wfile = TimedWriter(writer, row)
        try:
            return old_relay(handler, *args, **kwargs)
        finally:
            handler.wfile = writer

    def feed(restorer, frame):
        start = CLOCK()
        row = TLS.row
        try:
            if row is not None and has_text(frame):
                elapsed = round((start - TLS.rx_at) * 1000, 3)
                row.setdefault("gateway_first_text_parsed_ms", elapsed)
                row["gateway_last_text_parsed_ms"] = elapsed
            return old_feed(restorer, frame)
        finally:
            if row is not None:
                row["relay_feed_ms"] = round(row.get("relay_feed_ms", 0) + (CLOCK() - start) * 1000, 3)

    def connect(connection):
        start = CLOCK()
        try:
            return old_connect(connection)
        finally:
            row = getattr(TLS, "row", None)
            if row is not None:
                row["https_connect_calls"] = row.get("https_connect_calls", 0) + 1
                row["https_connect_ms"] = round(row.get("https_connect_ms", 0) + (CLOCK() - start) * 1000, 3)

    def audit(method):
        original = getattr(AuditStore, method)

        def measured(*args, **kwargs):
            start = CLOCK()
            try:
                return original(*args, **kwargs)
            finally:
                if getattr(TLS, "row", None) is not None:
                    TLS.row[f"audit_{method}_ms"] = round((CLOCK() - start) * 1000, 3)

        return measured

    stack.enter_context(patch.object(gateway_module, "relay_stream", relay))
    stack.enter_context(patch.object(stream_module.EventRestorer, "feed", feed))
    stack.enter_context(patch.object(http.client.HTTPSConnection, "connect", connect))
    stack.enter_context(patch.object(http.client.HTTPResponse, "_safe_read", read_chunk))
    stack.enter_context(patch.object(GatewaySession, "request", mask_request))
    for method in ("begin", "finish"):
        stack.enter_context(patch.object(AuditStore, method, audit(method)))


def cli_args(provider, route, work_dir, port, token, label, resume, use_tools=False):
    env = os.environ.copy()
    for key in (
        "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_CUSTOM_HEADERS", "CLAUDE_CODE_OAUTH_TOKEN",
        "CLAUDECODE", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
        "OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL",
    ):
        env.pop(key, None)
    if provider == "claude":
        env.update(DISABLE_TELEMETRY="1", DISABLE_ERROR_REPORTING="1",
                   ANTHROPIC_BASE_URL="https://api.anthropic.com")
        if route == "gateway":
            env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{port}/claude"
            env["ANTHROPIC_CUSTOM_HEADERS"] = f"X-SecureGateway-Token: {token}\nX-Benchmark-Run: {label}"
        arguments = [
            "claude", "--print", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
            "--setting-sources", "", "--strict-mcp-config", "--model", CLAUDE_MODEL,
            "--max-turns", "2", "--max-budget-usd", "0.15", "--tools", "", "--permission-mode", "dontAsk",
            "--system-prompt", "Answer the synthetic benchmark question with only the requested value. Do not use tools.",
        ]
        if resume:
            arguments += ["--resume", resume]
        return arguments, env
    arguments = ["codex", "exec"]
    if resume:
        arguments += ["resume"]
    else:
        arguments += ["--sandbox", "read-only"]
    arguments += [
        "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check", "--json", "--model", CODEX_MODEL,
        "-c", 'forced_login_method="chatgpt"', "-c", 'approval_policy="never"',
        "-c", 'sandbox_mode="read-only"', "-c", 'web_search="disabled"', "-c", 'model_reasoning_effort="low"',
        "-c", "skills.include_instructions=false", "-c", "project_doc_max_bytes=0",
        "-c", "model_instructions_file=" + json.dumps(str(work_dir / "instructions.txt")),
    ]
    disabled = set(LEAN_DISABLED_FEATURES)
    if use_tools:
        disabled -= {"code_mode_host", "shell_tool", "unified_exec"}
    for feature in sorted(disabled):
        arguments += ["--disable", feature]
    if route == "gateway":
        values = {
            "name": "SecureGateway subscription",
            "base_url": f"http://127.0.0.1:{port}/codex",
            "wire_api": "responses",
            "requires_openai_auth": True,
            "supports_websockets": False,
            "http_headers": {"X-SecureGateway-Token": token, "X-Benchmark-Run": label},
        }
        provider_value = ("{ " + ", ".join(
            f'{k} = ' + ("{ " + ", ".join(f'{json.dumps(h)} = {json.dumps(v)}' for h, v in value.items()) + " }"
                         if isinstance(value, dict) else json.dumps(value))
            for k, value in values.items()) + " }")
        arguments += ["-c", 'model_provider="benchmark_gateway"',
                      "-c", "model_providers.benchmark_gateway=" + provider_value]
    if resume:
        arguments += [resume]
    return arguments, env


def read_events(process, events):
    for line in process.stdout:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.put((CLOCK(), event))
    events.put((CLOCK(), None))


def write_prompt(process, prompt):
    try:
        with process.stdin:
            process.stdin.write(prompt)
    except (OSError, ValueError):
        pass


def classify(text):
    text = str(text).lower()
    tags = ("401", "403", "429", "usage limit", "capacity", "unsupported", "not found",
            "not supported", "authentication", "invalid", "connection", "timeout", "unexpected status")
    return next((tag for tag in tags if tag in text), "other")


def execute(provider, route, scenario, task, work, port, token, label, deadline, persist=False, resume=None):
    prompt, expected = task
    use_tools = scenario == "tool_round_trip"
    args, env = cli_args(provider, route, work, port, token, label, resume, use_tools)
    if not persist and not resume:
        args += ["--no-session-persistence" if provider == "claude" else "--ephemeral"]
    if provider == "codex":
        args += ["-"]
    events = queue.Queue()
    row = dict(provider=provider, route=route, scenario=scenario, prompt_bytes=len(prompt.encode("utf-8")),
               first_text_s=None, last_text_s=None, result_s=None, correct=False, tools=0)
    session = None
    answer = None
    start = CLOCK()
    with subprocess.Popen(args, cwd=work, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace") as proc:
        reader = threading.Thread(target=read_events, args=(proc, events), daemon=True)
        reader.start()
        threading.Thread(target=write_prompt, args=(proc, prompt), daemon=True).start()
        try:
            while True:
                remaining = min(start + CLI_LIMIT, deadline) - CLOCK()
                if remaining <= 0:
                    raise queue.Empty
                stamp, event = events.get(timeout=remaining)
                if event is None:
                    break
                elapsed = round(stamp - start, 3)
                kind = event.get("type")
                if provider == "claude":
                    if kind == "system" and event.get("subtype") == "init":
                        row["client_init_s"] = elapsed
                        row["model"] = event.get("model")
                        session = event.get("session_id")
                    if kind == "stream_event":
                        delta = event.get("event", {}).get("delta", {})
                        if delta.get("type") == "text_delta" and delta.get("text"):
                            if row["first_text_s"] is None:
                                row["first_text_s"] = elapsed
                            row["last_text_s"] = elapsed
                    if kind == "assistant":
                        row["tools"] += sum(block.get("type") == "tool_use"
                                            for block in event.get("message", {}).get("content", [])
                                            if isinstance(block, dict))
                    if kind == "result":
                        row["result_s"] = elapsed
                        row["api_s"] = round(event.get("duration_api_ms", 0) / 1000, 3)
                        row["usage"] = event.get("usage", {})
                        row["turns"] = event.get("num_turns")
                        answer = event.get("result", "")
                        if event.get("is_error"):
                            row["error_class"] = classify(answer)
                else:
                    if kind == "thread.started":
                        row["client_init_s"] = elapsed
                        session = event.get("thread_id")
                    if kind == "item.completed":
                        item = event.get("item", {})
                        if item.get("type") == "agent_message":
                            answer = item.get("text")
                            if row["first_text_s"] is None:
                                row["first_text_s"] = elapsed
                            row["last_text_s"] = elapsed
                        if item.get("type") in {"command_execution", "mcp_tool_call", "web_search", "file_change"}:
                            row["tools"] += 1
                    if kind == "turn.completed":
                        row["result_s"] = elapsed
                        row["usage"] = event.get("usage", {})
                    if kind in {"error", "turn.failed"}:
                        row["error_class"] = classify(event.get("message") or event.get("error"))
            row["exit_code"] = proc.wait(timeout=max(0.001, min(start + CLI_LIMIT, deadline) - CLOCK()))
        except (queue.Empty, subprocess.TimeoutExpired):
            proc.kill()
            row["error_class"] = "timeout"
    row["process_s"] = round(CLOCK() - start, 3)
    row["correct"] = (isinstance(answer, str) and answer.strip().rstrip(".") == expected
                      and (use_tools or not row["tools"]))
    if provider == "codex":
        row["model_requested"] = CODEX_MODEL
    usage = row.pop("usage", {})
    row["usage"] = {key: usage[key] for key in (
        "input_tokens", "output_tokens", "cached_input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
    ) if isinstance(usage.get(key), int)}
    return row, session


def transport():
    context = ssl.create_default_context()
    rows = []
    for hostname in ("api.anthropic.com", "chatgpt.com"):
        for attempt in range(1, 4):
            row = dict(host=hostname, attempt=attempt)
            start = CLOCK()
            try:
                addresses = socket.getaddrinfo(hostname, 443, socket.AF_INET, socket.SOCK_STREAM)
                row["dns_ms"] = round((CLOCK() - start) * 1000, 3)
                start = CLOCK()
                with socket.create_connection(addresses[0][4], timeout=5) as connection:
                    row["tcp_ms"] = round((CLOCK() - start) * 1000, 3)
                    start = CLOCK()
                    with context.wrap_socket(connection, server_hostname=hostname) as secure:
                        row["tls_ms"] = round((CLOCK() - start) * 1000, 3)
                        row["tls_version"] = secure.version()
            except OSError as exc:
                row["error_class"] = type(exc).__name__
            rows.append(row)
    return rows


def token_count(rows):
    # Codex input already includes cache hits; Claude reports them separately.
    return sum(sum(value for key, value in row.get("usage", {}).items()
                   if row["provider"] == "claude" or key != "cached_input_tokens") for row in rows)


def workload_tasks():
    lines = [f"Inventory row {number:03d}. The paper ledger stores a normal delivery on a blue shelf."
             for number in range(1, 201)]
    long_prompt = ("Remember that the reference value is amber garden.\n" + "\n".join(lines)
                   + "\nReturn only the reference value from the first line.")
    return (long_prompt, "amber garden"), ("Return only the reference value from the first turn.", "amber garden")


def run_suite(root, providers, plan, output, grouped, codex_tool):
    import contextlib

    token = secrets.token_urlsafe(32)
    rss = psutil.Process()
    baseline = rss.memory_info().rss
    peak = [baseline]
    stop = threading.Event()

    def monitor():
        while not stop.wait(0.005):
            peak[0] = max(peak[0], rss.memory_info().rss)

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    start = CLOCK()
    gateway = PrivacyGateway(("127.0.0.1", 0), token, state_dir=root / "state", audit_path=root / "audit.sqlite3")
    gateway.RequestHandlerClass = TimedHandler
    gateway.recent_timings = TimingLog()
    gateway.samples = {}
    thread = threading.Thread(target=gateway.serve_forever, daemon=True)
    thread.start()
    gateway.domain_catalog
    start_ms = round((CLOCK() - start) * 1000, 3)
    deadline = CLOCK() + SUITE_LIMIT
    max_invocations = 2 if codex_tool else 6 if grouped else MAX_INVOCATIONS
    rows = []
    skips = []
    if output.exists():
        raise FileExistsError("Choose a new report path.")
    basic, resumed = workload_tasks()

    def checkpoint():
        output.write_text(json.dumps({
            "package_version": __version__,
            "code_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "gateway_start_and_preload_ms": start_ms,
            "gateway_harness_rss": {"baseline_bytes": baseline, "peak_sampled_bytes": peak[0]},
            "budget": {"max_cli_invocations": max_invocations, "per_cli_seconds": CLI_LIMIT,
                       "wall_seconds": SUITE_LIMIT, "reported_token_ceiling": TOKEN_LIMIT},
            "reported_tokens": token_count(rows),
            "plan": plan,
            "samples": rows, "skips": skips,
        }, indent=2) + "\n", encoding="utf-8")

    def record(provider, route, scenario, task, work, persist=False, resume=None):
        label = "bench-" + uuid4().hex
        with gateway.admission:
            gateway.samples[label] = []
        row, session = execute(provider, route, scenario, task, work, gateway.server_port,
                               token, label, deadline, persist=persist, resume=resume)
        if route == "gateway":
            with gateway.admission:
                gateway.admission.wait_for(lambda: gateway.active_audit_handlers == 0, timeout=2)
                row["gateway_requests"] = gateway.samples.pop(label)
        else:
            gateway.samples.pop(label)
        return row, session

    try:
        with contextlib.ExitStack() as stack, concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            instrument(stack)
            for provider in providers:
                work = root / provider
                work.mkdir()
                (work / "instructions.txt").write_text(
                    "Answer only the requested synthetic value. Do not use tools.", encoding="utf-8")
                if shutil.which(provider) is None:
                    skips.append({"provider": provider, "reason": "client_missing"})
                    continue
                if codex_tool:
                    (work / "fixture.txt").write_text("CODE=quartz-lantern\n", encoding="utf-8")
                    (work / "instructions.txt").write_text(
                        "Read only the requested synthetic fixture in the current directory. "
                        "Use PowerShell Get-Content and return the requested value.", encoding="utf-8")
                    task = ("Run Get-Content -LiteralPath fixture.txt to read the local synthetic file. "
                            "Return only the value following CODE=.", "quartz-lantern")
                    for route in ("direct", "gateway"):
                        if CLOCK() >= deadline or token_count(rows) >= TOKEN_LIMIT:
                            skips.append({"provider": provider, "route": route, "reason": "budget"})
                            continue
                        row, _ = record(provider, route, "tool_round_trip", task, work)
                        rows.append(row)
                        checkpoint()
                    continue
                if grouped:
                    for route in ("gateway", "direct"):
                        if token_count(rows) >= TOKEN_LIMIT or CLOCK() >= deadline:
                            skips.append({"provider": provider, "route": route, "reason": "budget"})
                            continue
                        barrier = threading.Barrier(2)
                        second = (basic[0].replace("amber garden", "silver harbor"), "silver harbor")

                        def start_concurrent(task):
                            barrier.wait(timeout=2)
                            return record(provider, route, "long_concurrent_two", task, work, persist=True)

                        pair = list(pool.map(start_concurrent, (basic, second)))
                        rows.extend(row for row, _ in pair)
                        checkpoint()
                        initial, session = pair[0]
                        if (not initial["correct"] or not session or not initial["usage"]
                                or CLOCK() >= deadline or token_count(rows) >= TOKEN_LIMIT):
                            skips.append({"provider": provider, "route": route, "scenario": "resume",
                                          "reason": "no_verified_resumable_session_or_budget"})
                            continue
                        followup, _ = record(provider, route, "resume", resumed, work, resume=session)
                        rows.append(followup)
                        checkpoint()
                    continue
                route_ready = {}
                for route in ("direct", "gateway"):
                    if token_count(rows) >= TOKEN_LIMIT or CLOCK() >= deadline:
                        skips.append({"provider": provider, "route": route, "reason": "budget"})
                        continue
                    initial, session = record(provider, route, "long_start", basic, work, persist=True)
                    rows.append(initial)
                    checkpoint()
                    usage_known = bool(initial["usage"])
                    route_ready[route] = initial.get("exit_code") == 0 and "error_class" not in initial and usage_known
                    if not route_ready[route] or not session:
                        skips.append({"provider": provider, "route": route, "scenario": "resume",
                                      "reason": "no_resumable_session_or_usage"})
                        continue
                    if token_count(rows) >= TOKEN_LIMIT or CLOCK() >= deadline:
                        skips.append({"provider": provider, "route": route, "scenario": "resume", "reason": "budget"})
                        continue
                    followup, _ = record(provider, route, "resume", resumed, work, resume=session)
                    rows.append(followup)
                    checkpoint()
                    route_ready[route] = followup.get("exit_code") == 0 and "error_class" not in followup and bool(followup["usage"])
                for route in ("gateway", "direct"):
                    if not route_ready.get(route) or token_count(rows) >= TOKEN_LIMIT or CLOCK() >= deadline:
                        skips.append({"provider": provider, "route": route, "scenario": "concurrent_two",
                                      "reason": "route_unavailable_or_budget"})
                        continue
                    tasks = [
                        (f"Return only these words: {value}.", value) for value in ("violet ferry", "silver harbor")
                    ]
                    barrier = threading.Barrier(2)

                    def concurrent_task(task):
                        barrier.wait(timeout=2)
                        return record(provider, route, "concurrent_two", task, work)[0]

                    rows.extend(pool.map(concurrent_task, tasks))
                    checkpoint()
    finally:
        gateway.shutdown()
        thread.join()
        gateway.server_close()
        stop.set()
        monitor_thread.join()
    checkpoint()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--transport", action="store_true")
    parser.add_argument("--provider", choices=("claude", "codex", "both"), default="both")
    parser.add_argument("--grouped", action="store_true", help="Run six Codex invocations with concurrent long starts.")
    parser.add_argument("--codex-tool", action="store_true", help="Run two Codex fixture-read comparisons.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.live == args.transport:
        parser.error("Choose exactly one of --live and --transport.")
    if args.grouped and (not args.live or args.provider != "codex"):
        parser.error("--grouped requires --live --provider codex.")
    if args.codex_tool and (not args.live or args.provider != "codex" or args.grouped):
        parser.error("--codex-tool requires --live --provider codex without --grouped.")
    if args.output.exists():
        parser.error("Choose a new output path.")
    if args.transport:
        args.output.write_text(json.dumps(transport(), indent=2) + "\n", encoding="utf-8")
        return
    providers = ("claude", "codex") if args.provider == "both" else (args.provider,)
    with tempfile.TemporaryDirectory(prefix="sg-355-matrix-") as tmp:
        if args.codex_tool:
            plan = "one read-only Codex tool task per route with buffered response instrumentation"
        elif args.grouped:
            plan = "two concurrent long starts and one resume per route"
        else:
            plan = "long start + same-client resume; two concurrent fresh sessions"
        run_suite(Path(tmp), providers, plan, args.output, args.grouped, args.codex_tool)


if __name__ == "__main__":
    main()
