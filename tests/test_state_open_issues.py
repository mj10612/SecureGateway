from threading import Event, Thread
import time

import pytest

from secure_gateway import hooks
from secure_gateway.encrypted_session import save_session
from secure_gateway.session import PrivacySession, SessionVault
from secure_gateway.models import TokenMapping, TokenType


def test_interrupted_key_initialization_can_retry(tmp_path, monkeypatch):
    state = tmp_path / "state"
    settings = tmp_path / "settings.json"
    original = hooks.secrets.token_urlsafe
    monkeypatch.setattr(hooks.secrets, "token_urlsafe", lambda _: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        hooks.configure(settings, state, True)
    assert not (state / "key").exists()
    monkeypatch.setattr(hooks.secrets, "token_urlsafe", original)
    hooks.configure(settings, state, True)
    assert hooks.installation_status(settings, state)["ready"]


def test_empty_key_is_diagnosed_and_not_replaced_with_snapshots(tmp_path):
    state = tmp_path / "state"
    settings = tmp_path / "settings.json"
    hooks.configure(settings, state, True)
    (state / "key").write_bytes(b"")
    assert not hooks.installation_status(settings, state)["ready"]
    (state / ("a" * 64 + ".enc")).write_bytes(b"existing encrypted state")
    with pytest.raises(ValueError, match="existing snapshots"):
        hooks.configure(settings, state, True)
    assert (state / "key").read_bytes() == b""


def test_empty_key_without_snapshots_recovers_and_preserves_valid_key(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    key = state / "key"
    key.write_bytes(b"")
    settings = tmp_path / "settings.json"
    hooks.configure(settings, state, True)
    original = key.read_bytes()
    assert original
    hooks.configure(settings, state, True)
    assert key.read_bytes() == original
    assert hooks.installation_status(settings, state)["ready"]


def test_retired_snapshot_deletion_is_retried(tmp_path, monkeypatch):
    (tmp_path / "key").write_text("fixture-password", encoding="ascii")
    store = hooks.HookStore(tmp_path)
    path = store.path("fixture")
    session = PrivacySession("fixture", ttl_seconds=1)
    session.last_accessed = time.time() - 10
    save_session(path, session, "fixture-password")
    original = type(path).unlink
    def fail(target, *args, **kwargs):
        if target == path:
            raise PermissionError("fixture")
        return original(target, *args, **kwargs)
    monkeypatch.setattr(type(path), "unlink", fail)
    assert store.gc(False)["removed"] == 0
    assert store._retired(path).exists()
    monkeypatch.setattr(type(path), "unlink", original)
    assert store.gc()["candidates"] == 1
    assert store.gc(False)["removed"] == 1
    assert not path.exists()
    assert store._retired(path).exists()


@pytest.mark.parametrize("corrupt", [False, True])
def test_retired_marker_does_not_allow_deleting_changed_snapshot(tmp_path, corrupt):
    (tmp_path / "key").write_text("fixture-password", encoding="ascii")
    store = hooks.HookStore(tmp_path)
    path = store.path("fixture")
    save_session(path, PrivacySession("fixture"), "fixture-password")
    if corrupt:
        path.write_bytes(b"invalid ciphertext")
    store._retired(path).write_bytes(b"retired")
    before = path.read_bytes()
    assert store.gc(False)["removed"] == 0
    assert path.read_bytes() == before


@pytest.mark.parametrize("close", [False, True])
def test_bulk_clear_does_not_hold_registry_while_waiting(close):
    vault = SessionVault(cleanup_interval=60)
    session = vault.create("held")
    entered, holder_ready, done = Event(), Event(), Event()
    original = session.clear
    def announced_clear():
        entered.set()
        original()
    session.clear = announced_clear
    def holder():
        with session.operation():
            holder_ready.set()
            assert entered.wait(3)
            assert vault.active_count == 0
        done.set()
    worker = Thread(target=holder, daemon=True)
    worker.start()
    assert holder_ready.wait(3)
    clearer = Thread(target=vault.close if close else vault.clear_all, daemon=True)
    clearer.start()
    assert done.wait(3)
    worker.join(3)
    clearer.join(3)
    assert not clearer.is_alive()
    assert session.generator.closed
    vault.close()


def test_original_scan_failure_links_and_mutation():
    session = PrivacySession("scan")
    store = session.forward_store
    def add(original, number):
        store[original] = TokenMapping(original=original, surrogate=f"alias{number}", token_type=TokenType.ENTITY)
    add("a " * 2000 + "z", 1)
    add("Customer", 2)
    add("PrivateCustomer", 3)
    text = "a " * 12000 + " PrivateCustomer Customer! xCustomer"
    assert store.originals_in(text) == {"Customer", "PrivateCustomer"}
    cached = store._original_automaton
    assert store.originals_in("Customer") == {"Customer"}
    assert store._original_automaton is cached
    add("NewCustomer", 4)
    assert store.originals_in("NewCustomer") == {"NewCustomer"}
    del store["NewCustomer"]
    assert store.originals_in("NewCustomer") == set()
