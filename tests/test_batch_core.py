"""Regression proof for the core issues in the 0.6 release."""

from threading import Event, Thread

import pytest

from secure_gateway.client import LocalPrivacyClient
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import SurrogateStrategy
from secure_gateway.session import PrivacySession, SessionVault


@pytest.mark.parametrize("text", ["123비밀고객정보", "123secret비밀", "100만원비밀고객"])
def test_numeric_tail_is_not_a_public_particle(text):
    session = PrivacySession("tail")
    engine = MaskingEngine()
    result = engine.mask_text(text, "tail", session.generator,
                              session.forward_store, session.reverse_store)
    assert "비밀" not in result.masked_text
    assert engine.unmask(result.masked_text, "tail", session.reverse_store).unmasked_text == text


def test_unrelated_session_lookup_does_not_wait_for_cleanup():
    vault = SessionVault()
    a = vault.create("a")
    vault.create("b")
    done = Event()
    worker = Thread(target=lambda: (vault.get_session("b"), done.set()))
    try:
        with a.operation():
            worker.start()
            assert done.wait(1)
        worker.join(2)
    finally:
        vault.close()


@pytest.mark.parametrize("lookup", ["get_session", "get_or_create"])
def test_waiting_for_one_session_does_not_hold_the_registry(lookup):
    vault = SessionVault()
    a = vault.create("a")
    vault.create("b")
    attempted, done = Event(), Event()
    original_touch, original_operation = a.touch, a.operation
    if lookup == "get_session":
        def touch():
            attempted.set()
            original_touch()
        a.touch = touch
    else:
        def operation():
            attempted.set()
            return original_operation()
        a.operation = operation
    first = Thread(target=lambda: getattr(vault, lookup)("a"))
    second = Thread(target=lambda: (vault.get_session("b"), done.set()))
    try:
        with a.generator.lock:
            first.start()
            assert attempted.wait(1)
            second.start()
            assert done.wait(1)
        first.join(2)
        second.join(2)
    finally:
        vault.close()


def test_provider_call_pins_local_session():
    with LocalPrivacyClient() as client:
        def provider(masked):
            session = next(iter(client.vault._sessions.values()))
            session.last_accessed -= 90000
            assert client.vault.active_count == 1
            return masked
        assert client.request("ConfidentialCustomer", provider).unmasked_text == "ConfidentialCustomer"


def test_directly_invalidated_session_does_not_leave_a_retry_loop():
    vault = SessionVault()
    try:
        original = vault.create("invalidated")
        original.clear()
        assert vault.get_session("invalidated") is None
        replacement = vault.get_or_create("invalidated")
        assert replacement is not original and not replacement.generator.closed
    finally:
        vault.close()


def test_unknown_code_alias_with_korean_particle_is_strict():
    session = PrivacySession("strict", strategy=SurrogateStrategy.UNICODE)
    with pytest.raises(ValueError, match="Unrecognized"):
        MaskingEngine().unmask("private_symbol_999가", "strict", session.reverse_store,
                               SurrogateStrategy.UNICODE, strict=True)


def test_configurable_core_resource_limits_preserve_existing_aliases():
    vault = SessionVault(max_sessions=1, mapping_limit=1)
    engine = MaskingEngine(max_input_bytes=16)
    try:
        session = vault.create("one")
        with pytest.raises(ValueError, match="Session limit"):
            vault.create("two")
        args = ("one", session.generator, session.forward_store, session.reverse_store)
        first = engine.mask_text("Confidential", *args)
        assert engine.mask_text("Confidential", *args).masked_text == first.masked_text
        with pytest.raises(ValueError, match="Mapping limit"):
            engine.mask_text("AnotherSecret", *args)
        with pytest.raises(ValueError, match="Input size"):
            engine.mask_text("x" * 17, *args)
    finally:
        vault.close()


def test_hangul_masking_uses_only_relevant_mapping_lookup():
    session = PrivacySession("lookup")
    class NoFullScan(type(session.forward_store)):
        def values(self):
            raise AssertionError("must not enumerate all mappings")
        def originals_in(self, text):
            return set()
    session.forward_store = NoFullScan(session.generator)
    MaskingEngine().mask_text("비밀고객 정보", "lookup", session.generator,
                              session.forward_store, session.reverse_store)


@pytest.mark.parametrize("language, source", [
    ("rust", "fn main() { let secret_char = '\\n'; }"),
    ("java", "class Secret { char value = 'Z'; }"),
    ("c", "char secret = 'Z';"),
    ("go", "package main\nvar secret = 'Z'"),
])
def test_character_literals_are_opaque_expressions_and_restore_exactly(language, source):
    session = PrivacySession("character")
    engine = MaskingEngine()
    result = engine.mask_code(source, "character", session.generator,
                              session.forward_store, session.reverse_store, language=language)
    assert "'" not in result.masked_text
    assert engine.unmask(result.masked_text, "character", session.reverse_store,
                         strict=True).unmasked_text == source
