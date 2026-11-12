"""Measure gateway-side latency per stage with synthetic data and a loopback mock upstream.

Issues #355/#356. No provider account, API key, model or external network is used.
The mock upstream answers immediately (unless ``--upstream-delay-ms`` is given), so the
numbers describe gateway work only: they never include model inference, real TLS,
DNS or Internet latency.

Run:
    uv run --locked --all-extras python scripts/benchmark_gateway_latency.py --repeat 3
    uv run --locked --all-extras python scripts/benchmark_gateway_latency.py --profile

Stages (milliseconds, per request, measured inside the gateway process):
    lock_wait      session lock wait before input masking (gateway timing)
    mask           GatewaySession.request: validation + input masking (gateway timing)
    serialize      strict_json_dumps of the masked request in the handler
    upstream_send  connect + send + mock upstream headers (gateway timing)
    first_event    stream relay start -> first restored event written (gateway timing)
    restore        EventRestorer.feed/finish (restore + tool-argument groups, incl. lock waits)
    save           encrypted snapshot save (gateway timing)
    audit_begin / audit_finish   metadata audit ledger writes (separate samples)
    client_first_content  client request start -> first text_delta frame received
    client_total          client request start -> stream end
Only synthetic, generated text is used; output contains timings and counts only.
"""
from __future__ import annotations

import argparse
import cProfile
from collections import deque
import datetime as dt
import http.client
import io
import json
import os
from pathlib import Path
import platform
import pstats
import random
import statistics
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Lock, Thread, local
import time
from typing import Any

from secure_gateway import __version__
import secure_gateway.gateway as gateway_module
from secure_gateway.gateway import GatewayHandler, PrivacyGateway
from secure_gateway.gateway_audit import AuditStore
import secure_gateway.engine.strategies as strategies
import secure_gateway.gateway_stream as stream_module

TOKEN = "local-benchmark-token"
AUTH = "Bearer sk-ant-oat-synthetic-benchmark"
LENGTHS = {"short": 2, "medium": 8, "long": 24}
LANGUAGES = ("en", "ko", "mixed")

# --------------------------------------------------------------------------- data

EN_NAMES = ["Halvorsen", "Quistgaard", "Okonkwo", "Marchetti", "Lindqvist", "Brightwater", "Ravensholm"]
KO_NAMES = ["박서연", "최도윤", "한지민", "윤태호", "은하수", "푸른숲"]
PROJECTS = ["Brightwater Ledger", "Ravensholm Billing", "Quist Atlas", "Northwind Payroll"]
EN_SENTENCES = [
    "Customer {name} reported that invoice {inv} for project {project} was rounded twice.",
    "Please check why the reconciliation job skips refunds older than {days} days.",
    "The nightly export for {project} failed after the schema migration on ticket {inv}.",
    "{name} asked us to keep the audit trail but hide the account number {acct}.",
    "Explain the failing test and propose a minimal fix without changing the public API.",
]
KO_SENTENCES = [
    "고객 {name}님이 프로젝트 {project}의 청구서 {inv} 금액이 두 번 반올림되었다고 알려왔습니다.",
    "{days}일보다 오래된 환불 건을 정산 작업이 건너뛰는 이유를 확인해 주세요.",
    "스키마 변경 이후 {project} 야간 내보내기가 실패했고 관련 티켓은 {inv}입니다.",
    "{name}님은 감사 기록은 유지하되 계좌 번호 {acct}는 숨겨 달라고 요청했습니다.",
    "실패하는 테스트를 설명하고 공개 API를 바꾸지 않는 최소 수정안을 제안해 주세요.",
]
CODE = '''```python
def reconcile_{slug}_ledger(invoice_total, tax_rate, refunds):
    """Return the settled amount for {project}."""
    settled_{slug} = round(invoice_total * (1 + tax_rate), 2)
    for refund in refunds:
        if refund.age_days > {days}:
            continue
        settled_{slug} -= refund.amount
    return settled_{slug}
```'''


def _sentence(rng: random.Random, language: str) -> str:
    pick = language if language != "mixed" else rng.choice(("en", "ko"))
    template = rng.choice(EN_SENTENCES if pick == "en" else KO_SENTENCES)
    return template.format(
        name=rng.choice(EN_NAMES if pick == "en" else KO_NAMES), project=rng.choice(PROJECTS),
        inv=f"INV-{rng.randint(10000, 99999)}", days=rng.randint(10, 90),
        acct=f"{rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(100000, 999999)}")


def _prose(rng: random.Random, language: str, sentences: int) -> str:
    return " ".join(_sentence(rng, language) for _ in range(sentences))


def build_turns(language: str, turns: int, seed: int) -> list[list[dict[str, Any]]]:
    """Return per-turn message lists; request ``i`` resends turns ``0..i`` (history)."""
    rng = random.Random(seed)
    result = []
    for turn in range(turns):
        slug = rng.choice(["brightwater", "ravensholm", "quist", "northwind"])
        project = rng.choice(PROJECTS)
        days = rng.randint(10, 90)
        user_text = _prose(rng, language, 4) + "\n\n" + CODE.format(slug=slug, project=project, days=days)
        call_id = f"toolu_{seed:04d}{turn:04d}"
        command = f"grep -rn reconcile_{slug}_ledger src/billing/{slug}_ledger.py"
        tool_output = json.dumps({"matches": [
            {"path": f"src/billing/{slug}_ledger.py", "line": rng.randint(1, 400),
             "text": f"def reconcile_{slug}_ledger(invoice_total, tax_rate, refunds):"},
            {"path": f"tests/test_{slug}.py", "line": rng.randint(1, 200), "text": _sentence(rng, "en")},
        ], "total": 2}, ensure_ascii=False)
        assistant_text = _prose(rng, language, 2)
        result.append([
            {"role": "user", "content": [{"type": "text", "text": user_text}]},
            {"role": "assistant", "content": [
                {"type": "text", "text": assistant_text},
                {"type": "tool_use", "id": call_id, "name": "Bash",
                 "input": {"command": command, "timeout": 30000}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": call_id, "content": tool_output},
                {"type": "text", "text": _prose(rng, language, 1)},
            ]},
        ])
    return result


TOOLS = [{"name": "Bash", "description": "Run a shell command.",
          "input_schema": {"type": "object", "properties": {"command": {"type": "string"}},
                           "required": ["command"]}}]


def payload_for(turns: list[list[dict[str, Any]]], index: int) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    for turn in turns[:index]:
        messages.extend(turn)
    # The final request turn ends with the user message only.
    messages.append(turns[index][0])
    return {"model": "claude-synthetic", "max_tokens": 1024, "stream": True,
            "system": "You are a careful coding assistant.", "tools": TOOLS, "messages": messages}


# ------------------------------------------------------------------- mock upstream

def _split(text: str, size: int) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


class MockUpstream(BaseHTTPRequestHandler):
    """Split SSE response echoing the masked last user text (aliases) and a tool call."""
    delay = 0.0
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        request = json.loads(body)
        last = request["messages"][-1]["content"][0]["text"]
        echo = last + " Done."
        events: list[dict[str, Any]] = [
            {"type": "message_start", "message": {"id": "msg_synthetic", "type": "message", "role": "assistant",
                                                   "model": "claude-synthetic", "content": [],
                                                   "stop_reason": None, "stop_sequence": None,
                                                   "usage": {"input_tokens": 1, "output_tokens": 1}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        ]
        events += [{"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": part}}
                   for part in _split(echo, 7)]
        events.append({"type": "content_block_stop", "index": 0})
        command = None
        for message in reversed(request["messages"]):
            for block in message["content"] if isinstance(message["content"], list) else []:
                if block.get("type") == "tool_use":
                    command = block["input"]["command"]
                    break
            if command:
                break
        if command:
            arguments = json.dumps({"command": command}, ensure_ascii=False)
            events.append({"type": "content_block_start", "index": 1,
                           "content_block": {"type": "tool_use", "id": "toolu_mock", "name": "Bash", "input": {}}})
            events += [{"type": "content_block_delta", "index": 1,
                        "delta": {"type": "input_json_delta", "partial_json": part}}
                       for part in _split(arguments, 9)]
            events.append({"type": "content_block_stop", "index": 1})
        events += [{"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                    "usage": {"output_tokens": 1}},
                   {"type": "message_stop"}]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "close")
        self.end_headers()
        for event in events:
            frame = "event: " + event["type"] + "\ndata: " + json.dumps(event, ensure_ascii=False) + "\n\n"
            self.wfile.write(frame.encode())
            self.wfile.flush()
            if self.delay:
                time.sleep(self.delay)
        self.close_connection = True


# -------------------------------------------------------------- instrumentation

_tls = local()


def _extra() -> dict[str, float]:
    extra = getattr(_tls, "extra", None)
    if extra is None:
        extra = _tls.extra = {"serialize_ms": 0.0, "restore_ms": 0.0}
    return extra


class _Instrumented:
    """Wrap gateway internals for the duration of the benchmark (restored on exit)."""

    def __init__(self):
        self.audit: dict[str, list[float]] = {"audit_begin_ms": [], "audit_finish_ms": [],
                                              "lock_wait_restore_ms": []}
        self.lock = Lock()
        self._saved: list[tuple[Any, str, Any]] = []

    def _patch(self, owner, name, value):
        self._saved.append((owner, name, getattr(owner, name)))
        setattr(owner, name, value)

    def __enter__(self):
        original_dumps = gateway_module.strict_json_dumps
        handler_code = GatewayHandler._do_POST.__code__

        def dumps(*args, **kwargs):
            if sys._getframe(1).f_code is not handler_code:
                return original_dumps(*args, **kwargs)
            started = time.perf_counter()
            try:
                return original_dumps(*args, **kwargs)
            finally:
                _extra()["serialize_ms"] += (time.perf_counter() - started) * 1000

        self._patch(gateway_module, "strict_json_dumps", dumps)
        original_post = GatewayHandler._do_POST

        def do_post(handler):
            _tls.extra = None
            _tls.request_key = handler.headers.get("X-Benchmark-Request")
            try:
                return original_post(handler)
            finally:
                _tls.request_key = None
        self._patch(GatewayHandler, "_do_POST", do_post)
        for method in ("feed", "finish"):
            original = getattr(stream_module.EventRestorer, method)

            def timed(self_, *args, __original=original, **kwargs):
                started = time.perf_counter()
                try:
                    return __original(self_, *args, **kwargs)
                finally:
                    _extra()["restore_ms"] += (time.perf_counter() - started) * 1000
            self._patch(stream_module.EventRestorer, method, timed)
        for method in ("begin", "finish"):
            original = getattr(AuditStore, method)
            bucket = self.audit["audit_" + method + "_ms"]

            def audited(self_, *args, __original=original, __bucket=bucket, **kwargs):
                started = time.perf_counter()
                try:
                    return __original(self_, *args, **kwargs)
                finally:
                    with self.lock:
                        __bucket.append((time.perf_counter() - started) * 1000)
            self._patch(AuditStore, method, audited)
        return self

    def __exit__(self, *_exc):
        for owner, name, value in reversed(self._saved):
            setattr(owner, name, value)


class TimingLog(deque):
    """Replacement for ``PrivacyGateway.recent_timings`` merging thread-local stage times."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.by_request: dict[str, dict[str, Any]] = {}

    def append(self, timings):
        extra = _extra()
        timings = dict(timings, **{key: round(value, 3) for key, value in extra.items()})
        _tls.extra = None
        key = getattr(_tls, "request_key", None)
        if key:
            self.by_request[key] = timings
        super().append(timings)


class MemorySampler:
    def __init__(self, interval=0.005):
        self.interval = interval
        self.stop = Event()
        self.peak = 0
        self.available = False
        try:
            import psutil
            self.process = psutil.Process()
            self.available = True
        except ImportError:  # psutil is optional (context-eval extra)
            self.process = None

    def __enter__(self):
        if self.available:
            self.base = self.process.memory_info().rss
            self.peak = self.base
            self.thread = Thread(target=self._run, daemon=True)
            self.thread.start()
        return self

    def _run(self):
        while not self.stop.wait(self.interval):
            self.peak = max(self.peak, self.process.memory_info().rss)

    def __exit__(self, *_exc):
        self.stop.set()
        if self.available:
            self.thread.join()


# ------------------------------------------------------------------- client side

def send(port: int, payload: dict[str, Any], conversation: str, request_key: str = "") -> dict[str, float]:
    data = json.dumps(payload, ensure_ascii=False).encode()
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=120)
    started = time.perf_counter()
    connection.request("POST", "/claude/v1/messages", body=data, headers={
        "X-SecureGateway-Token": TOKEN, "Content-Type": "application/json", "Authorization": AUTH,
        "X-SecureGateway-Session": conversation, "anthropic-version": "2023-06-01",
        "X-Benchmark-Request": request_key or conversation})
    response = connection.getresponse()
    if response.status != 200:
        raise RuntimeError(f"gateway status {response.status}")
    first_content = None
    restored_text = []
    while True:
        line = response.fp.readline()
        if not line:
            break
        if line.startswith(b"data:"):
            event = json.loads(line[5:])
            if event.get("type") == "content_block_delta" and event["delta"].get("type") == "text_delta":
                if first_content is None:
                    first_content = (time.perf_counter() - started) * 1000
                restored_text.append(event["delta"]["text"])
    total = (time.perf_counter() - started) * 1000
    connection.close()
    expected = payload["messages"][-1]["content"][0]["text"] + " Done."
    if "".join(restored_text) != expected:
        raise RuntimeError("restored stream differs from the synthetic original")
    return {"client_first_content_ms": first_content or float("nan"), "client_total_ms": total,
            "request_bytes": len(data)}


# --------------------------------------------------------------------- statistics

def summarize(values: list[float]) -> dict[str, float | int]:
    values = sorted(value for value in values if value == value)
    if not values:
        return {"n": 0}
    p95 = values[min(len(values) - 1, max(0, round(0.95 * len(values) + 0.5) - 1))]
    return {"n": len(values), "median": round(statistics.median(values), 3),
            "p95": round(p95, 3), "max": round(values[-1], 3)}


STAGES = [("lock_wait", "mask_lock_wait_ms"), ("mask", "mask_ms"), ("serialize", "serialize_ms"),
          ("upstream_send", "upstream_headers_ms"), ("first_event", "first_event_ms"),
          ("restore", "restore_ms"), ("save", "save_ms"), ("gateway_total", "total_ms"),
          ("client_first_content", "client_first_content_ms"), ("client_total", "client_total_ms")]


def run_workload(port: int, gateway: PrivacyGateway, language: str, length: str, concurrency: int,
                 repeat: int, seed: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows_lock = Lock()
    errors: list[BaseException] = []

    def conversation(worker: int, run: int):
        conv_seed = seed * 1000 + worker * 37 + run
        turns = build_turns(language, LENGTHS[length], conv_seed)
        name = f"bench-{language}-{length}-{concurrency}-{worker}-{run}-{seed}"
        try:
            for index in range(len(turns)):
                key = f"{name}#{index}"
                client = send(port, payload_for(turns, index), name, key)
                with rows_lock:
                    rows.append({"turn": index, "worker": worker, "key": key, **client})
        except BaseException as exc:  # reported, never hidden
            errors.append(exc)

    log = gateway.recent_timings
    for run in range(repeat):
        threads = [Thread(target=conversation, args=(worker, run)) for worker in range(concurrency)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if errors:
            detail = str(errors[0]) if isinstance(errors[0], RuntimeError) else type(errors[0]).__name__
            raise RuntimeError(f"benchmark request failed ({language}/{length}/c{concurrency}): {detail}")
    for row in rows:
        # The handler appends its timings in a finally block that may finish just
        # after the client has read the closed stream.
        deadline = time.monotonic() + 5
        while row["key"] not in log.by_request and time.monotonic() < deadline:
            time.sleep(0.001)
        row.update({key: value for key, value in log.by_request.pop(row["key"]).items() if key != "provider"})
    return rows


def code_sha() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "src"], capture_output=True, text=True,
                               check=True).stdout.strip()
        return sha + ("+dirty-src" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def environment() -> dict[str, Any]:
    info: dict[str, Any] = {
        "code_sha": code_sha(), "package_version": __version__, "python": sys.version.split()[0],
        "package_from_checkout": Path(gateway_module.__file__).resolve().is_relative_to(
            (Path(__file__).resolve().parents[1] / "src")),
        "implementation": platform.python_implementation(), "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(), "cpu_count": os.cpu_count(),
        "measured_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    try:
        import psutil
        info["memory_total_bytes"] = psutil.virtual_memory().total
        info["cpu_physical"] = psutil.cpu_count(logical=False)
    except ImportError:
        pass
    return info


def start_gateway(root: Path, origin: str, rules: int = 0) -> tuple[PrivacyGateway, Thread]:
    gateway = PrivacyGateway(("127.0.0.1", 0), TOKEN, upstreams={"claude": origin},
                             state_dir=root / "state", audit_path=root / "audit" / "logs.sqlite3",
                             max_provider_requests=16)
    gateway.recent_timings = TimingLog(maxlen=1_000_000)
    if rules:
        gateway.set_mask_rules(synthetic_rules(rules))
    thread = Thread(target=gateway.serve_forever, daemon=True)
    thread.start()
    gateway.domain_catalog  # wait for the dictionary preload outside measured requests
    return gateway, thread


def benchmark(args) -> dict[str, Any]:
    results: dict[str, Any] = {"environment": environment(), "parameters": vars(args).copy(), "workloads": []}
    MockUpstream.delay = args.upstream_delay_ms / 1000
    with tempfile.TemporaryDirectory(prefix="gateway-latency-bench-") as temp, _Instrumented() as probes:
        root = Path(temp)
        (root / "audit").mkdir()
        upstream = ThreadingHTTPServer(("127.0.0.1", 0), MockUpstream)
        upstream.daemon_threads = True
        upstream_thread = Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        try:
            started = time.perf_counter()
            gateway, thread = start_gateway(root, f"http://127.0.0.1:{upstream.server_port}", args.mask_rules)
            results["gateway_start_with_dictionary_preload_ms"] = round((time.perf_counter() - started) * 1000, 2)
            try:
                cold_turns = build_turns("mixed", 1, 99)
                cold = send(gateway.server_port, payload_for(cold_turns, 0), "bench-cold")
                time.sleep(0.05)
                results["cold_first_request"] = {"client_total_ms": round(cold["client_total_ms"], 2),
                                                 **{k: v for k, v in gateway.recent_timings.by_request.pop(
                                                     "bench-cold").items() if k != "provider"}}
                matrix = [(language, length, 1) for length in args.lengths for language in args.languages]
                matrix += [(args.concurrency_language, args.concurrency_length, c)
                           for c in args.concurrency if c != 1]
                if 1 in args.concurrency and (args.concurrency_language, args.concurrency_length, 1) not in matrix:
                    matrix.append((args.concurrency_language, args.concurrency_length, 1))
                for language, length, concurrency in matrix:
                    probes.audit["audit_begin_ms"].clear()
                    probes.audit["audit_finish_ms"].clear()
                    with MemorySampler() as memory:
                        wall = time.perf_counter()
                        rows = run_workload(gateway.server_port, gateway, language, length, concurrency,
                                            args.repeat, args.seed)
                        wall = time.perf_counter() - wall
                    last_turn = LENGTHS[length] - 1
                    entry = {
                        "language": language, "length": length, "turns": LENGTHS[length],
                        "concurrency": concurrency, "conversations": concurrency * args.repeat,
                        "requests": len(rows), "wall_s": round(wall, 3),
                        "throughput_rps": round(len(rows) / wall, 2) if wall else None,
                        "request_bytes": summarize([row["request_bytes"] for row in rows]),
                        "stages": {name: summarize([row.get(key, float("nan")) for row in rows])
                                   for name, key in STAGES},
                        "last_turn_stages": {name: summarize([row.get(key, float("nan")) for row in rows
                                                              if row["turn"] == last_turn])
                                             for name, key in STAGES},
                        "audit": {key: summarize(list(values)) for key, values in probes.audit.items()
                                  if key.startswith("audit_")},
                    }
                    if memory.available:
                        entry["memory"] = {"rss_before_bytes": memory.base, "rss_peak_bytes": memory.peak,
                                           "rss_peak_delta_bytes": memory.peak - memory.base}
                    results["workloads"].append(entry)
                    print(f"done {language}/{length}/c{concurrency}: {len(rows)} requests in {wall:.2f}s",
                          file=sys.stderr)
            finally:
                gateway.shutdown()
                thread.join()
                gateway.server_close()
        finally:
            upstream.shutdown()
            upstream_thread.join()
            upstream.server_close()
    return results


def synthetic_rules(count: int) -> list[str]:
    """Forced masking rules: a few that occur in the synthetic prose, the rest absent."""
    # Digit-bearing rules (#363): a JSON number in tool input (timeout), a
    # number inside prose/tool output, and a protocol-equal value (1024).
    present = ["Northwind", "정산", "Quist Atlas", "환불", "30000", "INV-1", "2", "1024"]
    return (present + [f"synthetic-rule-{index:03d}" for index in range(count)])[:count]


class _SeededSecrets:
    """Deterministic stand-in for ``secrets`` used only by the profile digest runs."""

    def __init__(self, seed: int):
        self._random = random.Random(seed)

    def randbelow(self, bound: int) -> int:
        return self._random.randrange(bound)

    def token_hex(self, size: int = 32) -> str:
        return self._random.randbytes(size).hex()

    def choice(self, values):
        return self._random.choice(values)


def paired_dependency_scan(gateway: PrivacyGateway, turns, repeat: int) -> dict[str, Any] | None:
    """Same process, alternating order: memoized dependency scan vs the full embedded scan.

    ``full_scan`` replaces ``embedded_originals`` with the pre-#356 call
    ``originals_in(text, embedded=True)``; everything else is identical. Time in
    ``_mask_cache_key`` and in whole requests is summed per conversation
    (perf_counter; Windows thread CPU clocks tick at 15.6 ms), alternating the
    order so machine load affects both modes alike.
    """
    from secure_gateway.gateway import GatewaySession
    from secure_gateway.session import SessionMappings

    if not hasattr(SessionMappings, "embedded_originals"):
        return None
    original_key = GatewaySession._mask_cache_key
    result: dict[str, dict[str, list[float]]] = {mode: {"key_ms": [], "request_ms": []}
                                                 for mode in ("memo", "full_scan")}
    key_cpu = [0.0]

    def timed_key(self, *args, **kwargs):
        started = time.perf_counter()
        try:
            return original_key(self, *args, **kwargs)
        finally:
            key_cpu[0] += time.perf_counter() - started

    GatewaySession._mask_cache_key = timed_key  # type: ignore[method-assign]
    try:
        for run in range(repeat):
            for mode in (("memo", "full_scan") if run % 2 == 0 else ("full_scan", "memo")):
                session = gateway.get_session("claude", f"profile-paired-{mode}-{run}")
                store = session.session.forward_store
                if mode == "full_scan":
                    store.embedded_originals = lambda text, store=store: frozenset(  # type: ignore[method-assign]
                        store.originals_in(text, embedded=True))
                key_cpu[0] = 0.0
                started = time.perf_counter()
                for index in range(len(turns)):
                    with session.lock:
                        session.request(payload_for(turns, index))
                result[mode]["request_ms"].append((time.perf_counter() - started) * 1000)
                result[mode]["key_ms"].append(key_cpu[0] * 1000)
    finally:
        GatewaySession._mask_cache_key = original_key  # type: ignore[method-assign]
    return {mode: {name: summarize(values) for name, values in data.items()} for mode, data in result.items()}


def profile(args) -> dict[str, Any]:
    """cProfile GatewaySession.request on the long-conversation workload (in process, no HTTP).

    The same workload first runs without the profiler in fresh sessions; the
    digest of every masked request (and of the final alias table) lets a
    before/after comparison prove byte-identical output without printing it.
    """
    import hashlib

    turns = build_turns(args.profile_language, LENGTHS[args.profile_length], args.seed)
    real_secrets = strategies.secrets
    plain: list[list[float]] = []
    cpu: list[float] = []
    digests = set()
    with tempfile.TemporaryDirectory(prefix="gateway-profile-") as temp:
        gateway = PrivacyGateway(("127.0.0.1", 0), TOKEN, upstreams={"claude": "http://127.0.0.1:9"},
                                 state_dir=Path(temp) / "state")
        try:
            if args.mask_rules:
                gateway.set_mask_rules(synthetic_rules(args.mask_rules))
            gateway.domain_catalog
            warm = gateway.get_session("claude", "profile-warmup")
            warm.request(payload_for(build_turns("mixed", 1, 98), 0))
            for run in range(args.repeat):
                # Numeric aliases use ``secrets``; a seeded stand-in makes the
                # digest reproducible (with PYTHONHASHSEED=0) for comparisons.
                strategies.secrets = _SeededSecrets(args.seed)
                session = gateway.get_session("claude", f"profile-plain-{run}")
                digest = hashlib.sha256()
                timings = []
                for index in range(len(turns)):
                    payload = payload_for(turns, index)
                    started = time.perf_counter()
                    cpu_started = time.thread_time()
                    with session.lock:
                        masked = session.request(payload)
                    timings.append((time.perf_counter() - started) * 1000)
                    cpu.append((time.thread_time() - cpu_started) * 1000)
                    digest.update(json.dumps(masked, ensure_ascii=False, sort_keys=True).encode())
                for key, mapping in sorted(session.session.forward_store.items()):
                    digest.update(f"{key}\0{mapping.original}\0{mapping.surrogate}\0".encode())
                digests.add(digest.hexdigest())
                plain.append(timings)
            strategies.secrets = real_secrets
            paired = paired_dependency_scan(gateway, turns, args.repeat)
            session = gateway.get_session("claude", "profile-session")
            profiler = cProfile.Profile()
            per_request = []
            for index in range(len(turns)):
                payload = payload_for(turns, index)
                started = time.perf_counter()
                profiler.enable()
                with session.lock:
                    session.request(payload)
                profiler.disable()
                per_request.append(round((time.perf_counter() - started) * 1000, 2))
        finally:
            strategies.secrets = real_secrets
            gateway.server_close()
    totals = [sum(run) for run in plain]
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs()
    report: dict[str, Any] = {"environment": environment(), "workload": {
        "language": args.profile_language, "length": args.profile_length, "turns": len(turns),
        "mask_rules": args.mask_rules},
        "masked_output_sha256": sorted(digests),
        "digest_reproducible": os.environ.get("PYTHONHASHSEED") == "0",
        "unprofiled_conversation_ms": summarize(totals),
        "unprofiled_request_ms": summarize([value for run in plain for value in run]),
        "unprofiled_last_turn_ms": summarize([run[-1] for run in plain]),
        "unprofiled_request_thread_cpu_ms": summarize(cpu),
        "unprofiled_thread_cpu_total_ms": round(sum(cpu), 2),
        "paired_dependency_scan": paired,
        "request_ms_under_profiler": per_request, "total_ms_under_profiler": round(sum(per_request), 2)}
    raw = stats.stats  # type: ignore[attr-defined]
    total = sum(value[2] for value in raw.values())
    rows = [{"function": f"{Path(file).name}:{line}({name})", "ncalls": value[1], "tottime_s": round(value[2], 4),
             "cumtime_s": round(value[3], 4), "tottime_share": round(value[2] / total, 4) if total else 0}
            for (file, line, name), value in raw.items()]
    report["top_tottime"] = sorted(rows, key=lambda row: row["tottime_s"], reverse=True)[:args.top]
    report["top_cumtime"] = sorted(rows, key=lambda row: row["cumtime_s"], reverse=True)[:args.top]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repeat", type=int, default=3, help="conversations per workload and worker")
    parser.add_argument("--seed", type=int, default=356)
    parser.add_argument("--languages", nargs="+", default=list(LANGUAGES), choices=LANGUAGES)
    parser.add_argument("--lengths", nargs="+", default=list(LENGTHS), choices=list(LENGTHS))
    parser.add_argument("--concurrency", nargs="+", type=int, default=[1, 2, 4])
    parser.add_argument("--concurrency-language", default="mixed", choices=LANGUAGES)
    parser.add_argument("--concurrency-length", default="medium", choices=list(LENGTHS))
    parser.add_argument("--upstream-delay-ms", type=float, default=0.0, help="mock delay per SSE event")
    parser.add_argument("--profile", action="store_true", help="cProfile input masking instead of the HTTP run")
    parser.add_argument("--profile-language", default="mixed", choices=LANGUAGES)
    parser.add_argument("--profile-length", default="long", choices=list(LENGTHS))
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--mask-rules", type=int, default=0, help="number of synthetic forced masking rules (0-256)")
    parser.add_argument("--output", type=Path, help="write the JSON report here as well")
    parser.add_argument("--label", default="", help="free-form run label stored in the report (e.g. before/after)")
    args = parser.parse_args()
    if not 1 <= args.repeat <= 50 or any(not 1 <= c <= 16 for c in args.concurrency) or not 0 <= args.mask_rules <= 256:
        parser.error("--repeat must be 1..50, --concurrency values 1..16 and --mask-rules 0..256")
    report = profile(args) if args.profile else benchmark(args)
    report["label"] = args.label
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
