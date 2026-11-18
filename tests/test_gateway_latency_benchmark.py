"""First-content measurements exclude empty deltas without losing zero latency."""

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
