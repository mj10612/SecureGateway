"""Regression tests for gateway latency benchmark measurements."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def benchmark():
    path = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_gateway_latency.py"
    spec = importlib.util.spec_from_file_location("gateway_latency_benchmark", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def text_delta(text):
    event = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}}
    return b"data: " + json.dumps(event).encode() + b"\n"


def fake_stream(monkeypatch, benchmark, frames):
    clock = {"now": 0.0}
    iterator = iter(frames)

    class Stream:
        def readline(self):
            clock["now"], line = next(iterator)
            return line

    response = SimpleNamespace(status=200, fp=Stream())
    connection = SimpleNamespace(request=lambda *a, **k: None, getresponse=lambda: response, close=lambda: None)
    monkeypatch.setattr(benchmark.http.client, "HTTPConnection", lambda *a, **k: connection)
    monkeypatch.setattr(benchmark, "time", SimpleNamespace(perf_counter=lambda: clock["now"]))


def test_first_content_waits_for_nonempty_text(monkeypatch, benchmark):
    fake_stream(monkeypatch, benchmark, [
        (0.01, b": heartbeat\n"),
        (0.02, b'data: {"type": "message_start"}\n'),
        (0.03, text_delta("")),
        (0.10, text_delta("Hello")),
        (0.15, text_delta(" Done.")),
        (0.20, b""),
    ])
    result = benchmark.send(12345, {"messages": [{"content": [{"text": "Hello"}]}]}, "synthetic")
    assert result["client_first_content_ms"] == pytest.approx(100)
    assert result["client_total_ms"] == pytest.approx(200)


def test_zero_first_content_latency_is_a_valid_measurement(monkeypatch, benchmark):
    fake_stream(monkeypatch, benchmark, [(0.0, text_delta("Hello Done.")), (0.0, b"")])
    result = benchmark.send(12345, {"messages": [{"content": [{"text": "Hello"}]}]}, "synthetic")
    assert result["client_first_content_ms"] == 0.0


def test_direct_request_uses_mock_route_without_gateway_headers(monkeypatch, benchmark):
    fake_stream(monkeypatch, benchmark, [(0.01, text_delta("Hello Done.")), (0.02, b"")])
    connection = benchmark.http.client.HTTPConnection()
    requests = []
    connection.request = lambda method, path, **kwargs: requests.append((method, path, kwargs))

    result = benchmark.send(
        12345, {"messages": [{"content": [{"text": "Hello"}]}]}, "synthetic", direct=True
    )

    assert result["client_first_content_ms"] == pytest.approx(10)
    method, path, kwargs = requests[0]
    assert (method, path) == ("POST", "/v1/messages")
    assert kwargs["headers"] == {"Content-Type": "application/json"}


def test_direct_comparison_alternates_order_and_pairs_same_inputs(monkeypatch, benchmark):
    calls = []
    log = benchmark.TimingLog()

    def send(port, payload, conversation, request_key, *, direct=False):
        calls.append((port, payload, conversation, request_key))
        if not direct:
            log.by_request[request_key] = {"mask_ms": 2.0, "provider": "claude"}
        return {"client_first_content_ms": 1.0, "client_total_ms": 5.0}

    monkeypatch.setattr(benchmark, "send", send)
    rows, _, direct_rows, _ = benchmark.run_workload(
        1001, SimpleNamespace(recent_timings=log), "en", "short", 1, 2, 356, direct_port=1002
    )

    assert [port for port, *_ in calls] == [1001, 1001, 1002, 1002, 1002, 1002, 1001, 1001]
    assert [call[1:] for call in calls if call[0] == 1001] == [call[1:] for call in calls if call[0] == 1002]
    assert len(rows) == len(direct_rows) == 4
    assert rows[0]["mask_ms"] == 2.0
    assert "mask_ms" not in direct_rows[0]


def test_workload_wall_time_excludes_wait_for_gateway_timings(monkeypatch, benchmark):
    log = benchmark.TimingLog()
    pending = {}
    now = 0.0

    def send(port, payload, conversation, request_key, *, direct=False):
        nonlocal now
        now += 0.25
        if not direct:
            pending[request_key] = {"mask_ms": 2.0}
        return {"client_first_content_ms": 1.0, "client_total_ms": 5.0}

    def publish_timings(_interval):
        nonlocal now
        now += 0.5
        log.by_request.update(pending)
        pending.clear()

    monkeypatch.setattr(benchmark, "send", send)
    monkeypatch.setattr(benchmark, "time", SimpleNamespace(
        perf_counter=lambda: now, monotonic=lambda: now, sleep=publish_timings
    ))
    rows, gateway_wall, direct_rows, direct_wall = benchmark.run_workload(
        1001, SimpleNamespace(recent_timings=log), "en", "short", 1, 2, 356, direct_port=1002
    )

    assert len(rows) == len(direct_rows) == 4
    assert all(row["mask_ms"] == 2.0 for row in rows)
    assert gateway_wall == direct_wall == 1.0


@pytest.mark.parametrize(("count", "expected"), [(1, 1), (19, 19), (20, 19), (21, 20), (60, 57)])
def test_p95_uses_nearest_rank_of_measured_samples(benchmark, count, expected):
    samples = [float(value) for value in range(count, 0, -1)] + [float("nan")]

    summary = benchmark.summarize(samples)

    assert summary["n"] == count
    assert summary["p95"] == expected


def test_cold_request_waits_for_delayed_gateway_timings(monkeypatch, benchmark):
    log = benchmark.TimingLog()
    gateway = SimpleNamespace(
        server_port=12345, recent_timings=log, shutdown=lambda: None, server_close=lambda: None
    )
    now = 0.0

    def sleep(interval):
        nonlocal now
        now += interval
        if now >= 0.075:
            log.by_request["bench-cold"] = {"mask_ms": 2.0, "provider": "claude"}

    monkeypatch.setattr(benchmark, "environment", lambda: {})
    monkeypatch.setattr(benchmark, "start_gateway", lambda *_: (gateway, SimpleNamespace(join=lambda: None)))
    monkeypatch.setattr(benchmark, "send", lambda *_: {"client_total_ms": 12.0})
    monkeypatch.setattr(benchmark, "time", SimpleNamespace(
        perf_counter=lambda: now, monotonic=lambda: now, sleep=sleep
    ))
    args = SimpleNamespace(upstream_delay_ms=0, mask_rules=0, lengths=[], concurrency=[])

    result = benchmark.benchmark(args)

    assert result["cold_first_request"] == {"client_total_ms": 12.0, "mask_ms": 2.0}
    assert not log.by_request
