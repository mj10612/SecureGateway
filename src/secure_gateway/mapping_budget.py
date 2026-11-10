"""Logical UTF-8 mapping budgets; these are not Python heap/RSS limits."""

from contextlib import contextmanager
from typing import Any
DEFAULT_MAPPING_BYTES = 64 * 1024 * 1024
DEFAULT_SNAPSHOT_BYTES = 128 * 1024 * 1024
MAX_SNAPSHOT_FILE_BYTES = 192 * 1024 * 1024


def positive_budget(value: object, name: str) -> int:
    """Validate and return a positive integer budget.

    Args:
        value: Candidate budget; must be an ``int`` (not ``bool``) >= 1.
        name: Setting name used in validation errors.

    Returns:
        The validated integer budget. Never returns ``None``.

    Raises:
        ValueError: If ``value`` is not a positive integer.
    """
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return int(value)


def mapping_size(key: str, mapping: Any) -> int:
    """Estimate logical UTF-8 bytes charged for one mapping entry.

    Counts the key and original text plus a fixed per-entry overhead. The
    overhead is a policy charge, not exact allocator or process memory usage.
    Never returns ``None``.
    """
    # Forward lookup keys include representation/type and sometimes raw names.
    # Count the original and key once per entry, plus a fixed alias allowance.
    # This fixed overhead is a policy charge, not exact allocator accounting.
    return len(key.encode("utf-8")) + len(mapping.original.encode("utf-8")) + 1024


def check_mapping_budget(store: Any, generator: Any, key: str, original: str) -> None:
    """Raise before adding a mapping that would exceed the logical byte budget.

    Does nothing when ``key`` already exists or when the projected usage is
    within ``generator.max_mapping_bytes``. Always returns ``None``.

    Raises:
        ValueError: If the new mapping would exceed the configured budget.
    """
    if key in store:
        return
    usage = getattr(store, "mapping_bytes", None) if getattr(store, "account_bytes", False) else None
    if usage is None:
        usage = sum(mapping_size(k, m) for k, m in store.items())
    cost = len(key.encode("utf-8")) + len(original.encode("utf-8")) + 1024
    if usage + cost > generator.max_mapping_bytes:
        raise ValueError("Mapping byte limit reached; use a new session.")


def snapshot_budget(value: object) -> int:
    """Validate a logical snapshot byte budget.

    Returns the validated budget, capped by policy at :data:`DEFAULT_SNAPSHOT_BYTES`.
    Never returns ``None``.

    Raises:
        ValueError: If ``value`` is not a positive integer or exceeds 128 MiB.
    """
    budget = positive_budget(value, "max_snapshot_bytes")
    if budget > DEFAULT_SNAPSHOT_BYTES:
        raise ValueError("max_snapshot_bytes must not exceed 128 MiB.")
    return budget


class ReservedAliases(set):
    """Record new reservations only while an allocator transaction is active."""
    journal = None

    def add(self, value: str) -> None:
        """Record a surrogate reservation, journaling it when a transaction is active.

        Returns ``None``.
        """
        if self.journal is not None and value not in self:
            self.journal.append(value)
        super().add(value)

    def update(self, *values: Any) -> None:
        """Add multiple surrogate reservations through :meth:`add`.

        Returns ``None``.
        """
        for group in values:
            for value in group:
                self.add(value)


def record_mapping(generator: Any, store: Any, reverse: Any, key: str, mapping: Any) -> None:
    """Append a mapping allocation to the active transaction journal, if any.

    Returns ``None``. No-op when no mapping transaction is active.
    """
    journal = getattr(generator, "_mapping_transaction", None)
    if journal is not None:
        journal.append((store, reverse, key, mapping))


@contextmanager
def mapping_transaction(generator):
    """Roll back newly allocated mappings if the cumulative byte budget fails.

    Nested code/text passes share one journal. Existing sessions are not copied.
    """
    if getattr(generator, "_mapping_transaction", None) is not None:
        yield
        return
    entries: list[Any] = []
    aliases: list[str] = []
    generator._mapping_transaction = entries
    generator.used_surrogates.journal = aliases
    counters = dict(generator._type_counters)
    code_index = generator._code_index
    try:
        yield
    except ValueError as exc:
        if "Mapping byte limit" in str(exc):
            removed = {id(mapping) for _, _, _, mapping in entries}
            for store, reverse, key, mapping in reversed(entries):
                if store.get(key) is mapping:
                    del store[key]
                if reverse.get(mapping.surrogate) is mapping:
                    del reverse[mapping.surrogate]
            for key, variants in list(generator._identifier_groups.items()):
                kept = [m for m in variants if id(m) not in removed]
                if kept:
                    generator._identifier_groups[key] = kept
                else:
                    del generator._identifier_groups[key]
            for alias in aliases:
                generator.used_surrogates.discard(alias)
            generator._type_counters = counters
            generator._code_index = code_index
        raise
    finally:
        generator.used_surrogates.journal = None
        generator._mapping_transaction = None
