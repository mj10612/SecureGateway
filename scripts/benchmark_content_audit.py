"""Measure synthetic loopback gateway overhead; no provider account or API key is used.

Run: uv run python scripts/benchmark_content_audit.py --requests 20
Numbers are machine-specific, sequential and not production capacity estimates.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import statistics
import tempfile
from threading import Thread
import time
import urllib.request

import psutil

from secure_gateway.content_audit import ContentAuditStore
from secure_gateway.content_audit_capture import ContentAuditCapture
from secure_gateway.content_audit_writer import ContentAuditWriter
from secure_gateway.gateway import PrivacyGateway


class SyntheticProvider(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        events = [
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "text_delta", "text": "Synthetic response " * 16}},
            {"type": "message_stop"},
        ]
        body = "".join("data: " + json.dumps(event) + "\n\n" for event in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def measure(mode: str, count: int, root: Path, origin: str) -> dict:
    path = root / mode
    path.mkdir()
    store = writer = None
    audit_path = None if mode == "off" else path / "logs.sqlite3"
    first, total = [], []
    process = psutil.Process()
    with PrivacyGateway(("127.0.0.1", 0), "local-test-token", upstreams={"claude": origin},
                        audit_path=audit_path) as gateway:
        if mode == "content":
            store = ContentAuditStore(path / "content.sqlite3")
            store.initialize("synthetic-passphrase")
            writer = ContentAuditWriter(store)
            gateway.content_audit = ContentAuditCapture(writer, enabled=True,
                                                         kinds={"input", "sent", "response"})
        thread = Thread(target=gateway.serve_forever, daemon=True)
        thread.start()
        try:
            payload = json.dumps({"model": "fixture", "stream": True,
                                  "messages": [{"role": "user", "content": "Synthetic input " * 16}]}).encode()
            memory_before = cpu_before = 0
            for index in range(count + 1):
                if index == 1:
                    memory_before = process.memory_info().rss
                    cpu_before = time.process_time()
                request = urllib.request.Request(
                    f"http://127.0.0.1:{gateway.server_port}/claude/v1/messages", data=payload,
                    headers={"X-SecureGateway-Token": "local-test-token", "Content-Type": "application/json",
                             "Authorization": "Bearer sk-ant-oat-synthetic"})
                start = time.perf_counter()
                with urllib.request.urlopen(request, timeout=30) as response:
                    response.readline()
                    first_byte = (time.perf_counter() - start) * 1000
                    response.read()
                if index:
                    first.append(first_byte)
                    total.append((time.perf_counter() - start) * 1000)
            if writer:
                writer.drain()
        finally:
            gateway.shutdown()
            thread.join()
            if writer:
                writer.close()
            if store:
                store.close()
    return {"first_byte_mean_ms": statistics.mean(first), "total_mean_ms": statistics.mean(total),
            "cpu_seconds": time.process_time() - cpu_before,
            "rss_delta_bytes": process.memory_info().rss - memory_before,
            "disk_bytes": sum(p.stat().st_size for p in path.rglob("*") if p.is_file())}


def preflight(count: int, root: Path) -> float:
    store = ContentAuditStore(root / "preflight.sqlite3")
    store.initialize("synthetic-passphrase")
    writer = ContentAuditWriter(store)
    durations = []
    try:
        for index in range(count):
            request_id = f"preflight{index}"
            start = time.perf_counter()
            if not writer.begin(request_id, "block", ["Synthetic input " * 16]):
                raise RuntimeError("Synthetic preflight refused")
            durations.append((time.perf_counter() - start) * 1000)
            writer.finish(request_id)
        writer.drain()
    finally:
        writer.close()
        store.close()
    return statistics.mean(durations)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.requests <= 500:
        parser.error("--requests must be between 1 and 500")
    with tempfile.TemporaryDirectory(prefix="content-audit-bench-") as temp:
        root = Path(temp)
        with ThreadingHTTPServer(("127.0.0.1", 0), SyntheticProvider) as upstream:
            thread = Thread(target=upstream.serve_forever, daemon=True)
            thread.start()
            try:
                origin = f"http://127.0.0.1:{upstream.server_port}"
                results = {mode: measure(mode, args.requests, root, origin)
                           for mode in ("off", "metadata", "content")}
                results["block_preflight_mean_ms"] = preflight(args.requests, root)
            finally:
                upstream.shutdown()
                thread.join()
    print(json.dumps({"requests_per_mode": args.requests, "concurrency": 1,
                      "note": "Loopback synthetic SSE; one warmup per mode; RSS is before/after delta, not peak.",
                      "results": results}, indent=2))


if __name__ == "__main__":
    main()
