"""Session operation locks, bounded lifetimes, and periodic idle cleanup."""

from __future__ import annotations

from contextlib import contextmanager
from collections import deque
import math
import re
from threading import TIMEOUT_MAX, Event, RLock, Thread
import time
import uuid
import weakref

from secure_gateway.engine.strategies import StrategyGenerator
from secure_gateway.models import MaskMode, SessionStats, SurrogateStrategy, TokenMapping


def validate_ttl(ttl: float) -> None:
    if isinstance(ttl, bool) or not math.isfinite(ttl) or not 0 < ttl <= 86400:
        raise ValueError("ttl_seconds must be positive and at most 86400 (one day).")


class SessionMappings(dict[str, TokenMapping]):
    """Public stores must be accessed inside session.operation() when mutated."""

    def __init__(self, generator: StrategyGenerator):
        super().__init__()
        self.generator = generator
        self._original_trie: dict | None = None
        self._original_automaton: tuple[list[dict[str, int]], list[int], list[str | None], list[int]] | None = None
        self.nonstandard_surrogates: set[str] = set()

    def __setitem__(self, key, mapping):
        self._original_automaton = None
        if key in self:
            self._original_trie = None
            previous = self[key]
            if isinstance(previous, TokenMapping):
                self.nonstandard_surrogates.discard(previous.surrogate)
        super().__setitem__(key, mapping)
        if not isinstance(mapping, TokenMapping):
            return
        if not StrategyGenerator.get_pattern(self.generator.strategy).fullmatch(mapping.surrogate):
            self.nonstandard_surrogates.add(mapping.surrogate)
        if self._original_trie is not None:
            self._index_original(mapping.original)

    def _index_original(self, original):
        node = self._original_trie
        assert node is not None
        for char in original:
            node = node.setdefault(char, {})
        node[None] = original

    def originals_in(self, text: str) -> set[str]:
        """Scan existing originals using cached failure transitions."""
        if self._original_automaton is None:
            if self._original_trie is None:
                self._original_trie = {}
                for mapping in self.values():
                    if isinstance(mapping, TokenMapping):
                        self._index_original(mapping.original)
            edges: list[dict[str, int]] = [{}]
            failure = [0]
            terminal: list[str | None] = [None]
            output = [0]
            stack = [(self._original_trie, 0)]
            while stack:
                node, state = stack.pop()
                terminal[state] = node.get(None) or None
                for char, child in node.items():
                    if char is None:
                        continue
                    index = len(edges)
                    edges[state][char] = index
                    edges.append({})
                    failure.append(0)
                    terminal.append(None)
                    output.append(0)
                    stack.append((child, index))
            queue = deque(edges[0].values())
            while queue:
                state = queue.popleft()
                for char, child in edges[state].items():
                    queue.append(child)
                    fallback = failure[state]
                    while fallback and char not in edges[fallback]:
                        fallback = failure[fallback]
                    failure[child] = edges[fallback].get(char, 0)
                    target = failure[child]
                    output[child] = target if terminal[target] is not None else output[target]
            self._original_automaton = edges, failure, terminal, output
        edges, failure, terminal, output = self._original_automaton
        found = set()
        state = 0
        for position, char in enumerate(text):
            while state and char not in edges[state]:
                state = failure[state]
            state = edges[state].get(char, 0)
            match = state if terminal[state] is not None else output[state]
            while match:
                original = terminal[match]
                assert original is not None
                start = position + 1 - len(original)
                if not text[start].isspace() and (start == 0 or not re.match(r"\w", text[start - 1])):
                    found.add(original)
                match = output[match]
        return found

    def __delitem__(self, key):
        self._original_automaton = None
        mapping = self[key]
        super().__delitem__(key)
        if isinstance(mapping, TokenMapping):
            self.nonstandard_surrogates.discard(mapping.surrogate)
        self._original_trie = None

    def clear(self):
        self._original_automaton = None
        super().clear()
        self.nonstandard_surrogates.clear()
        self._original_trie = None

    def update(self, *args, **kwargs):
        for key, mapping in dict(*args, **kwargs).items():
            self[key] = mapping

    def pop(self, key, *default):
        if key not in self:
            return super().pop(key, *default)
        mapping = self[key]
        del self[key]
        return mapping

    def popitem(self):
        self._original_automaton = None
        key, mapping = super().popitem()
        if isinstance(mapping, TokenMapping):
            self.nonstandard_surrogates.discard(mapping.surrogate)
        self._original_trie = None
        return key, mapping

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    # Unlike dict.__or__, in-place updates retain the TokenMapping value type.
    def __ior__(self, other) -> SessionMappings:  # type: ignore[override, misc]
        self.update(other)
        return self


class PrivacySession:
    def __init__(
        self,
        session_id: str,
        mode: MaskMode = MaskMode.CONTENT_WORDS,
        strategy: SurrogateStrategy = SurrogateStrategy.BRACKET,
        ttl_seconds: float = 3600,
        salt: str = "",
        mapping_limit: int = 100_000,
    ):
        validate_ttl(ttl_seconds)
        if type(mapping_limit) is not int or mapping_limit < 1:
            raise ValueError("mapping_limit must be a positive integer.")
        self.session_id = session_id
        self.mode = mode
        self.strategy = strategy
        self.ttl_seconds = ttl_seconds
        self.created_at = self.last_accessed = time.time()
        self.total_mask_calls = self.total_unmask_calls = 0
        self.generator = StrategyGenerator(strategy=strategy, salt=salt)
        self.generator.max_mappings = mapping_limit
        self.active_pins = 0
        self.forward_store = SessionMappings(self.generator)
        self.reverse_store = SessionMappings(self.generator)

    def operation(self):
        """Use this context for counters, settings, and custom store mutations."""
        return self.generator.operation()

    @contextmanager
    def pin(self):
        """Keep a provider request alive without holding its mapping lock."""
        with self.operation():
            self.active_pins += 1
            self.last_accessed = time.time()
        try:
            yield self
        finally:
            with self.generator.lock:
                self.active_pins -= 1
                if not self.generator.closed:
                    self.last_accessed = time.time()

    def is_expired(self) -> bool:
        with self.generator.lock:
            return time.time() - self.last_accessed > self.ttl_seconds

    def touch(self) -> None:
        with self.generator.operation():
            self.last_accessed = time.time()

    def clear(self) -> None:
        with self.generator.lock:
            self.generator.closed = True
            self.forward_store.clear()
            self.reverse_store.clear()
            self.generator.used_surrogates.clear()
            self.generator._type_counters.clear()
            if hasattr(self.generator, "_identifier_groups"):
                self.generator._identifier_groups.clear()
            self.generator.salt = ""

    def get_stats(self) -> SessionStats:
        with self.operation():
            counts: dict[str, int] = {}
            for mapping in self.forward_store.values():
                name = mapping.token_type.value
                counts[name] = counts.get(name, 0) + 1
            return SessionStats(
                session_id=self.session_id,
                created_at=self.created_at,
                last_accessed=self.last_accessed,
                total_unique_mappings=len(self.forward_store),
                total_mask_calls=self.total_mask_calls,
                total_unmask_calls=self.total_unmask_calls,
                mode=self.mode,
                strategy=self.strategy,
                type_distribution=counts,
            )


class SessionVault:
    """Registry is locked; built-in engine operations share each session's RLock."""

    def __init__(
        self, default_ttl: float = 3600, cleanup_interval: float | None = None,
        max_sessions: int = 1000, mapping_limit: int = 100_000,
    ):
        validate_ttl(default_ttl)
        for name, value in (("max_sessions", max_sessions), ("mapping_limit", mapping_limit)):
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer.")
        self.max_sessions = max_sessions
        self.mapping_limit = mapping_limit
        self.default_ttl = default_ttl
        self.default_session_id = f"sess_{uuid.uuid4().hex}"
        self._sessions: dict[str, PrivacySession] = {}
        self._lock = RLock()
        self._stop = Event()
        self._closed = False
        self._thread: Thread | None = None
        self.cleanup_interval = (
            min(1.0, default_ttl / 2) if cleanup_interval is None else cleanup_interval
        )
        if (
            isinstance(self.cleanup_interval, bool)
            or not math.isfinite(self.cleanup_interval)
            or not 0 < self.cleanup_interval <= TIMEOUT_MAX
        ):
            raise ValueError(
                "cleanup_interval must be finite, positive, and at most threading.TIMEOUT_MAX"
            )

    def _sid(self, session_id: str | None) -> str:
        return (
            session_id.strip()
            if session_id and session_id.strip()
            else self.default_session_id
        )

    def _start_cleanup_locked(self) -> None:
        if self._thread is None:
            self._thread = Thread(
                target=self._sweep,
                args=(weakref.ref(self), self._stop, self.cleanup_interval),
                daemon=True,
            )
            self._thread.start()

    @staticmethod
    def _sweep(
        reference: weakref.ReferenceType[SessionVault], stop: Event, interval: float
    ) -> None:
        while not stop.wait(interval):
            vault = reference()
            if vault is None:
                return
            with vault._lock:
                vault._cleanup_expired_locked()
            del vault

    def get_or_create(
        self,
        session_id: str | None = None,
        mode: MaskMode = MaskMode.CONTENT_WORDS,
        strategy: SurrogateStrategy = SurrogateStrategy.BRACKET,
    ) -> PrivacySession:
        while True:
            with self._lock:
                if self._closed:
                    raise ValueError("Session vault is closed.")
                self._cleanup_expired_locked()
                sid = self._sid(session_id)
                session = self._sessions.get(sid)
                if session is None:
                    return self.create(sid, mode, strategy, self.default_ttl)
            # Waiting for one session must not stall unrelated registry users.
            try:
                with session.operation():
                    if session.strategy != strategy:
                        raise ValueError(
                            f"Session '{sid}' uses strategy '{session.strategy.value}'; cannot switch to '{strategy.value}'. Use a new session ID."
                        )
                    # mode is a last-used policy, not an immutable allocation format.
                    session.mode = mode
                    session.touch()
                    return session
            except ValueError:
                if not session.generator.closed:
                    raise
                # A concurrent clear invalidated this generation before entry.

    def create(
        self,
        session_id: str | None = None,
        mode: MaskMode = MaskMode.CONTENT_WORDS,
        strategy: SurrogateStrategy = SurrogateStrategy.BRACKET,
        ttl_seconds: float | None = None,
    ) -> PrivacySession:
        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        validate_ttl(ttl)
        with self._lock:
            if self._closed:
                raise ValueError("Session vault is closed.")
            self._cleanup_expired_locked()
            sid = self._sid(session_id)
            if sid in self._sessions:
                raise ValueError(
                    f"Session '{sid}' already exists. Use a new ID or clear it first."
                )
            if len(self._sessions) >= self.max_sessions:
                raise ValueError("Session limit reached; clear an idle session before creating another.")
            session = PrivacySession(sid, mode, strategy, ttl, mapping_limit=self.mapping_limit)
            self._sessions[sid] = session
            self._start_cleanup_locked()
            return session

    def get_session(self, session_id: str) -> PrivacySession | None:
        with self._lock:
            self._cleanup_expired_locked()
            session = self._sessions.get(self._sid(session_id))
        if session:
            try:
                session.touch()
            except ValueError:
                if session.generator.closed:
                    return None
                raise
        return session

    @property
    def active_count(self) -> int:
        with self._lock:
            self._cleanup_expired_locked()
            return len(self._sessions)

    def clear_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.pop(self._sid(session_id), None)
        if session:
            session.clear()  # waits for this generation, outside the registry lock
            return True
        return False

    def clear_all(self) -> int:
        with self._lock:
            sessions = tuple(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.clear()
        return len(sessions)

    def close(self) -> None:
        self._stop.set()
        with self._lock:
            self._closed = True
            sessions = tuple(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.clear()
        if self._thread:
            self._thread.join(timeout=2)

    def _cleanup_expired_locked(self) -> None:
        for sid in list(self._sessions):
            session = self._sessions[sid]
            if not session.generator.lock.acquire(blocking=False):
                continue
            try:
                if session.generator.closed or (not session.active_pins and session.is_expired()):
                    session.clear()
                    del self._sessions[sid]
            finally:
                session.generator.lock.release()
