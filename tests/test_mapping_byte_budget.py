"""Logical mapping accounting and bounded encrypted state regressions."""
from concurrent.futures import ThreadPoolExecutor
import json

import pytest

from secure_gateway.encrypted_session import load_session, save_session
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.gateway import GatewaySession, PrivacyGateway
from secure_gateway.models import SurrogateStrategy
from secure_gateway.session import PrivacySession, SessionVault


def mask(session, text, engine=None):
    return (engine or MaskingEngine()).mask_text(text, session.session_id, session.generator,
                                                session.forward_store, session.reverse_store)


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_exact_budget_reuse_failure_and_restore(strategy):
    source = "private"
    cost = len("text:noun:private".encode()) + len(source.encode()) + 1024
    s = PrivacySession("bytes", strategy=strategy, max_mapping_bytes=cost)
    result = mask(s, source)
    assert s.forward_store.mapping_bytes == cost
    assert mask(s, source).masked_text == result.masked_text
    before = (dict(s.forward_store), dict(s.reverse_store), set(s.generator.used_surrogates))
    with pytest.raises(ValueError, match="Mapping byte limit"):
        mask(s, "zorblyx")
    assert (dict(s.forward_store), dict(s.reverse_store), s.generator.used_surrogates) == before
    assert MaskingEngine().unmask(result.masked_text, s.session_id, s.reverse_store, strategy, strict=True).unmasked_text == source


def test_utf8_accounting_deletion_clear_and_concurrent_reuse():
    s = PrivacySession("unicode", max_mapping_bytes=5000)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: mask(s, "비밀이름"), range(20)))
    assert len(s.forward_store) == 1
    key, mapping = next(iter(s.forward_store.items()))
    assert s.forward_store.mapping_bytes == len(key.encode()) + len(mapping.original.encode()) + 1024
    s.forward_store.pop(key)
    assert s.forward_store.mapping_bytes == 0
    s.clear()
    assert s.forward_store.mapping_bytes == 0


def test_snapshot_preserves_budget_and_old_snapshot_is_compatible(tmp_path):
    s = PrivacySession("saved", max_mapping_bytes=2200, max_snapshot_bytes=10000)
    result = mask(s, "private")
    path = tmp_path / "state.enc"
    save_session(path, s, "password")
    loaded = load_session(path, "password")
    assert loaded.generator.max_mapping_bytes == 2200 and loaded.max_snapshot_bytes == 10000
    assert loaded.forward_store.mapping_bytes == s.forward_store.mapping_bytes
    mask(loaded, "second")
    with pytest.raises(ValueError, match="Mapping byte limit"):
        mask(loaded, "third")
    assert MaskingEngine().unmask(result.masked_text, loaded.session_id, loaded.reverse_store, strict=True).unmasked_text == "private"
    # Legacy v2 optional fields absent: use documented conservative defaults.
    from secure_gateway.encrypted_session import SnapshotEncryption, _MAGIC, _SALT_SIZE, _cipher
    data = path.read_bytes()
    salt = data[len(_MAGIC):len(_MAGIC) + _SALT_SIZE]
    payload = json.loads(_cipher("password", salt).decrypt(data[len(_MAGIC) + _SALT_SIZE:]))
    payload.pop("max_mapping_bytes")
    payload.pop("max_snapshot_bytes")
    path.write_bytes(SnapshotEncryption("password").encrypt(json.dumps(payload).encode()))
    assert load_session(path, "password").generator.max_mapping_bytes == 64 * 1024 * 1024


def test_failed_snapshot_save_is_atomic_and_read_is_bounded(tmp_path, monkeypatch):
    import secure_gateway.encrypted_session as encrypted
    path = tmp_path / "state.enc"
    s = PrivacySession("snapshot")
    mask(s, "private")
    save_session(path, s, "password")
    before = path.read_bytes()
    s.max_snapshot_bytes = 1
    with pytest.raises(ValueError, match="snapshot payload limit"):
        save_session(path, s, "password")
    assert path.read_bytes() == before
    monkeypatch.setattr(encrypted, "MAX_SNAPSHOT_FILE_BYTES", 10)
    with pytest.raises(ValueError, match="snapshot file limit"):
        load_session(path, "password")


def test_gateway_effective_byte_limit_and_metadata_only_diagnostics():
    with PrivacyGateway(("127.0.0.1", 0), "synthetic-token", max_mapping_bytes=1200) as g:
        s = g.get_session("codex")
        s._mask_prose("private")
        report = g.session_diagnostics()["providers"]["codex"]
        assert report["max_mapping_bytes"] == 1200 and 0 < report["mapping_bytes"] <= 1200
        assert "private" not in json.dumps(report)
        with pytest.raises(ValueError, match="Mapping byte limit"):
            s._mask_prose("zorblyx")
    saved = PrivacySession("gateway", max_mapping_bytes=1500)
    wrapped = GatewaySession(saved, max_mapping_bytes=1200)
    assert wrapped.session.generator.max_mapping_bytes == 1200


@pytest.mark.parametrize("invalid", [0, -1, True, "100"])
def test_invalid_budgets_are_rejected(invalid):
    with pytest.raises(ValueError):
        PrivacySession("invalid", max_mapping_bytes=invalid)
    with pytest.raises(ValueError):
        SessionVault(max_snapshot_bytes=invalid)


def test_sdk_vault_propagates_byte_policy():
    from secure_gateway.client import LocalPrivacyClient
    with LocalPrivacyClient(max_mapping_bytes=1) as client:
        with pytest.raises(ValueError, match="Mapping byte limit"):
            client.request("private", lambda text: text)


def test_plain_dict_budget_and_snapshot_decrypted_budget(tmp_path, monkeypatch):
    from secure_gateway.engine.strategies import StrategyGenerator
    from secure_gateway.models import SurrogateStrategy
    import secure_gateway.encrypted_session as encrypted
    gen = StrategyGenerator(SurrogateStrategy.BRACKET)
    gen.max_mapping_bytes = 1100
    forward, reverse = {}, {}
    engine = MaskingEngine()
    first = engine.mask_text("private", "plain", gen, forward, reverse)
    with pytest.raises(ValueError, match="Mapping byte limit"):
        engine.mask_text("zorblyx", "plain", gen, forward, reverse)
    assert len(forward) == len(reverse) == 1
    assert engine.unmask(first.masked_text, "plain", reverse, strict=True).unmasked_text == "private"
    session = PrivacySession("snapshot")
    mask(session, "private")
    path = tmp_path / "snapshot.enc"
    save_session(path, session, "password")
    monkeypatch.setattr(encrypted, "DEFAULT_SNAPSHOT_BYTES", 10)
    with pytest.raises(ValueError, match="password or damaged"):
        load_session(path, "password")


def test_cli_enforces_budget_without_publishing_snapshot(tmp_path):
    from click.testing import CliRunner
    from secure_gateway.cli import main
    path = tmp_path / "state.enc"
    result = CliRunner().invoke(main, ["mask", "private", "--max-mapping-bytes", "1", "--session-file", str(path),
                                       "--session-password", "password", "--json-output"])
    assert result.exit_code != 0 and "Mapping byte limit" in result.output
    assert not path.exists()


def test_replacement_popitem_and_clear_release_accounted_bytes():
    from secure_gateway.models import TokenMapping, TokenType
    session = PrivacySession("editing", max_mapping_bytes=3000)
    store = session.forward_store
    store["one"] = TokenMapping(original="private", surrogate="[NOUN_1]", token_type=TokenType.NOUN)
    original_cost = store.mapping_bytes
    store["one"] = TokenMapping(original="longerprivate", surrogate="[NOUN_2]", token_type=TokenType.NOUN)
    assert store.mapping_bytes == original_cost + 6
    store.popitem()
    assert store.mapping_bytes == 0
    mask(session, "private")
    store.clear()
    assert store.mapping_bytes == 0


@pytest.mark.parametrize("code", [False, True])
def test_byte_failure_rolls_back_new_allocations_and_reservations(code):
    s = PrivacySession("transaction", max_mapping_bytes=1200)
    e = MaskingEngine()
    before = (dict(s.forward_store), dict(s.reverse_store), set(s.generator.used_surrogates))
    with pytest.raises(ValueError, match="Mapping byte limit"):
        if code:
            e.mask_code("privateName = privateOther", s.session_id, s.generator, s.forward_store, s.reverse_store)
        else:
            mask(s, "private zorblyx", e)
    assert (dict(s.forward_store), dict(s.reverse_store), s.generator.used_surrogates) == before
    assert s.forward_store.mapping_bytes == 0 and not s.generator._identifier_groups
    assert s.generator._type_counters == {} and s.generator._code_index == 0
    mask(s, "private", e)


def test_failed_wrapper_does_not_mutate_supplied_session():
    s = PrivacySession("gateway", max_mapping_bytes=5000)
    mask(s, "private")
    with pytest.raises(ValueError):
        GatewaySession(s, max_mapping_bytes=1)
    assert s.generator.max_mapping_bytes == 5000
    with pytest.raises(ValueError):
        GatewaySession(s, max_mapping_bytes=2000, max_snapshot_bytes=0)
    assert s.generator.max_mapping_bytes == 5000
    mask(s, "zorblyx")


def test_mutated_original_cannot_publish_unreloadable_snapshot(tmp_path):
    s = PrivacySession("mutated", max_mapping_bytes=1200)
    mask(s, "private")
    # Deliberate unsupported bypass: saving still revalidates corrupted state.
    object.__setattr__(next(iter(s.forward_store.values())), "original", "x" * 10000)
    path = tmp_path / "state.enc"
    with pytest.raises(ValueError, match="Mapping byte limit"):
        save_session(path, s, "password")
    assert not path.exists()
