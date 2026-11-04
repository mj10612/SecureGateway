"""Logical UTF-8 mapping budgets; these are not Python heap/RSS limits."""

from contextlib import contextmanager
from typing import Any
DEFAULT_MAPPING_BYTES = 64 * 1024 * 1024
DEFAULT_SNAPSHOT_BYTES = 128 * 1024 * 1024
MAX_SNAPSHOT_FILE_BYTES = 192 * 1024 * 1024


def positive_budget(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def mapping_size(key, mapping):
    # Forward lookup keys include representation/type and sometimes raw names.
    # Count the original and key once per entry, plus a fixed alias allowance.
    # This fixed overhead is a policy charge, not exact allocator accounting.
    return len(key.encode("utf-8")) + len(mapping.original.encode("utf-8")) + 1024


def check_mapping_budget(store, generator, key, original):
    if key in store:
        return
    usage = getattr(store, "mapping_bytes", None) if getattr(store, "account_bytes", False) else None
    if usage is None:
        usage = sum(mapping_size(k, m) for k, m in store.items())
    cost = len(key.encode("utf-8")) + len(original.encode("utf-8")) + 1024
    if usage + cost > generator.max_mapping_bytes:
        raise ValueError("Mapping byte limit reached; use a new session.")


def snapshot_budget(value):
    positive_budget(value, "max_snapshot_bytes")
    if value > DEFAULT_SNAPSHOT_BYTES:
        raise ValueError("max_snapshot_bytes must not exceed 128 MiB.")
    return value


class ReservedAliases(set):
    """Record new reservations only while an allocator transaction is active."""
    journal = None

    def add(self, value):
        if self.journal is not None and value not in self:
            self.journal.append(value)
        super().add(value)

    def update(self, *values):
        for group in values:
            for value in group:
                self.add(value)


def record_mapping(generator, store, reverse, key, mapping):
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
