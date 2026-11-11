"""Experimental field-level capture adapter, disabled unless explicitly attached."""

from __future__ import annotations

import json
import threading
from typing import Any

from secure_gateway.content_audit_writer import ContentAuditWriter

_TRAVERSAL_FIELDS = frozenset({
    "messages", "input", "instructions", "system", "content", "text", "output", "choices",
    "message", "delta", "content_block", "item", "tool_calls", "function", "refusal",
})
_TOOL_ARGS = frozenset({"tool_use", "function_call", "custom_tool_call"})
_TOOL_RESULTS = frozenset({"tool_result", "function_call_output", "custom_tool_call_output"})


def extract_content(value: Any, kind: str) -> list[Any]:
    """Extract content without retaining whole protocol envelopes or headers."""
    found: list[Any] = []

    def visit(item: Any) -> None:
        if isinstance(item, str):
            if kind in {"input", "sent", "response"}:
                found.append(item)
            return
        if isinstance(item, list):
            for child in item:
                visit(child)
            return
        if not isinstance(item, dict):
            return
        item_type = item.get("type")
        if not isinstance(item_type, str):
            item_type = ""
        if item_type in _TOOL_ARGS:
            if kind == "tool_args":
                for key in ("arguments", "input"):
                    if key in item:
                        argument = item[key]
                        if isinstance(argument, str) and item_type == "function_call":
                            try:
                                argument = json.loads(argument)
                            except ValueError:
                                continue
                        found.append(argument)
            return
        if item_type in _TOOL_RESULTS or item.get("role") == "tool":
            if kind == "tool_result":
                for key in ("output", "content"):
                    if key in item:
                        found.append(item[key])
            return
        if item_type in {"response.function_call_arguments.delta", "response.custom_tool_call_input.delta"}:
            if kind == "tool_args" and isinstance(item.get("delta"), str):
                found.append(item["delta"])
            return
        if item_type == "input_json_delta":
            if kind == "tool_args" and isinstance(item.get("partial_json"), str):
                found.append(item["partial_json"])
            return
        for key, child in item.items():
            if key in _TRAVERSAL_FIELDS:
                visit(child)

    visit(value)
    return found


class ContentAuditCapture:
    """Opt-in adapter between gateway observations and an isolated audit writer."""

    def __init__(self, writer: ContentAuditWriter, *, enabled: bool = False, paused: bool = False,
                 policy: str = "continue", kinds: set[str] | None = None,
                 providers: set[str] | None = None, agents: set[str] | None = None):
        self.writer = writer
        self.enabled, self.paused, self.policy = enabled, paused, policy
        self.kinds = set(kinds or ())
        self.providers = providers
        self.agents = agents
        self._stream_lock = threading.Lock()
        self._streams: dict[str, dict[str, Any]] = {}

    def applies(self, provider: str, exclusion: str | None, agent: str | None = None) -> bool:
        """Return whether this request is selected for content auditing."""
        return self.intent(provider, exclusion, agent) == "capture"

    def intent(self, provider: str, exclusion: str | None, agent: str | None = None) -> str:
        """Return a fixed, content-free admission reason."""
        if not self.enabled:
            return "off"
        if self.paused:
            return "paused"
        if ((exclusion or "").strip().lower() == "off"
                or self.providers is not None and provider not in self.providers
                or self.agents is not None and agent not in self.agents):
            return "excluded"
        return "capture"

    def begin(self, request_id: str, payload: dict[str, Any]) -> bool:
        """Admit the request after extracting selected input content."""
        with self._stream_lock:
            self._streams[request_id] = {"events": 0, "buffers": {}, "sizes": {}, "discarded": set()}
        try:
            content = extract_content(payload, "input") if "input" in self.kinds else None
            return self.writer.begin(request_id, self.policy, content)
        except Exception:
            try:
                self.writer.begin(request_id, "continue", None)
            except Exception:
                pass
            self._failed(request_id)
            return self.policy == "continue"

    def _failed(self, request_id: str) -> None:
        try:
            self.writer.fail(request_id)
        except Exception:
            pass

    def observe(self, request_id: str, kind: str, value: Any, phase: str, *, stream: bool = False) -> None:
        """Queue only the selected, observed fields from one transformation stage."""
        if self.paused:
            try:
                self.writer.omit(request_id, event_count=1)
            except Exception:
                self._failed(request_id)
            return
        try:
            if kind in self.kinds:
                content = extract_content(value, kind)
                if content:
                    self.writer.capture(request_id, kind, {"phase": phase, "fields": content}, stream=stream)
        except Exception:
            self._failed(request_id)

    def observe_sse(self, request_id: str, data: str, phase: str) -> None:
        """Queue selected fields from a parsed event, never raw SSE or error text."""
        if self.paused:
            try:
                self.writer.omit(request_id, event_count=1)
            except Exception:
                self._failed(request_id)
            return
        try:
            self._observe_sse(request_id, data, phase)
        except Exception:
            self._failed(request_id)

    def _observe_sse(self, request_id: str, data: str, phase: str) -> None:
        if not data or data == "[DONE]":
            return
        try:
            event = json.loads(data)
        except (ValueError, TypeError):
            return
        with self._stream_lock:
            state = self._streams[request_id]
            if state["events"] >= self.writer.stream_limit:
                if state["buffers"]:
                    self.writer.omit(request_id, byte_count=sum(state["sizes"].values()))
                    state["buffers"].clear()
                    state["sizes"].clear()
                    state["discarded"].update({"response", "tool_args"})
                self.writer.omit(request_id, event_count=1)
                return
            state["events"] += 1
            for kind in ("response", "tool_args"):
                if kind not in self.kinds:
                    continue
                fields = extract_content(event, kind)
                if not fields:
                    continue
                text = "".join(field if isinstance(field, str) else json.dumps(field, ensure_ascii=False)
                               for field in fields)
                size = len(text.encode("utf-8"))
                key = (kind, phase)
                if kind in state["discarded"]:
                    self.writer.omit(request_id, byte_count=size)
                    continue
                previous_size = state["sizes"].get(kind, 0)
                if previous_size + size > self.writer.kind_limit:
                    # Discard the entire kind so an incomplete credential prefix is never persisted.
                    for existing in list(state["buffers"]):
                        if existing[0] == kind:
                            del state["buffers"][existing]
                    state["discarded"].add(kind)
                    self.writer.omit(request_id, byte_count=previous_size + size)
                    state["sizes"][kind] = 0
                    continue
                state["sizes"][kind] = previous_size + size
                state["buffers"].setdefault(key, []).append(text)

    def finish(self, request_id: str, *, uncertain: bool, interrupted: bool) -> None:
        """Queue the lifecycle marker for this observed request."""
        try:
            self._finish(request_id, uncertain=uncertain, interrupted=interrupted)
        except Exception:
            self._failed(request_id)

    def _finish(self, request_id: str, *, uncertain: bool, interrupted: bool) -> None:
        interrupted = interrupted or self.paused
        with self._stream_lock:
            stream = self._streams.pop(request_id)
        if interrupted and stream["buffers"]:
            self.writer.omit(request_id, byte_count=sum(stream["sizes"].values()))
            stream["buffers"].clear()
        for (kind, phase), fragments in stream["buffers"].items():
            combined = "".join(fragments)
            content: Any = combined
            if kind == "tool_args":
                try:
                    content = json.loads(combined)
                except ValueError:
                    self.writer.omit(request_id, byte_count=len(combined.encode("utf-8")))
                    continue
            self.writer.capture(request_id, kind, {"phase": phase, "fields": [content]})
        self.writer.finish(request_id, uncertain=uncertain, interrupted=interrupted)
