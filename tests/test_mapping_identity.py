"""Mapping identity cannot invalidate store budgets or indexes through assignment."""
import pytest
from pydantic import ValidationError

from secure_gateway.models import TokenMapping, TokenType
from secure_gateway.session import PrivacySession


@pytest.mark.parametrize("warm_cache", [False, True])
def test_original_change_rejected_without_corrupting_budget_or_indexes(warm_cache):
    session = PrivacySession("immutable", max_mapping_bytes=1100)
    with session.operation():
        mapping = TokenMapping(original="OldSecret", surrogate="[[NOUN_0001]]")
        session.forward_store["key"] = mapping
        session.reverse_store[mapping.surrogate] = mapping
        if warm_cache:
            assert session.forward_store.originals_in("OldSecret") == {"OldSecret"}
        before = session.forward_store.mapping_bytes
        for replacement in ("NewSecret", "x" * 10000):
            with pytest.raises(ValidationError, match="frozen"):
                mapping.original = replacement
            assert mapping.original == "OldSecret"
            assert session.forward_store.mapping_bytes == before <= 1100
            assert session.forward_store.originals_in("OldSecret") == {"OldSecret"}
            assert session.forward_store.originals_in(replacement) == set()
        mapping.occurrence_count += 1
        assert mapping.occurrence_count == 2
        assert session.reverse_store[mapping.surrogate] is mapping


@pytest.mark.parametrize("field,value", [
    ("surrogate", "[[NOUN_0002]]"), ("token_type", TokenType.NOUN),
    ("context", "code"), ("lookup_key", "different"),
    ("identifier_base", "Other"), ("identifier_language", "ruby"),
    ("identifier_key", "other"), ("identifier_quoted", True),
    ("code_literal", True), ("format_version", 1),
    ("is_capitalized", True), ("is_all_caps", True),
])
def test_identity_fields_reject_assignment_and_deletion(field, value):
    mapping = TokenMapping(original="private", surrogate="[[NOUN_0001]]")
    original = mapping.model_dump()
    with pytest.raises(ValidationError, match="frozen"):
        setattr(mapping, field, value)
    with pytest.raises(ValidationError, match="frozen"):
        delattr(mapping, field)
    assert mapping.model_dump() == original


def test_identity_remains_immutable_after_serialization():
    original = TokenMapping(original="private", surrogate="[[NOUN_0001]]")
    loaded = TokenMapping.model_validate_json(original.model_dump_json())
    with pytest.raises(ValidationError, match="frozen"):
        loaded.original = "changed"
    loaded.occurrence_count += 1
    assert loaded.occurrence_count == 2
