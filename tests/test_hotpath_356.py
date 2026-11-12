"""Issue #356 hot-path fast paths must be exact: memo invalidation and rule caches."""

import random
import unicodedata

import pytest

from secure_gateway import gateway as gateway_module
from secure_gateway import session as session_module
from secure_gateway.gateway import GatewaySession
from secure_gateway.models import TokenMapping, TokenType
from secure_gateway.session import PrivacySession


def _mapping(original, surrogate):
    return TokenMapping(original=original, surrogate=surrogate, token_type=TokenType.IDENTIFIER)


def _store():
    return PrivacySession("hotpath").forward_store


def _fresh(store, text):
    return frozenset(store.originals_in(text, embedded=True))


TEXTS = ["Alpha met Beta at Gamma", "AlphaBeta", "the plan's report", "고객은하수정산", "", "Gam"]


def test_memo_matches_full_scan_after_additions():
    store = _store()
    store["k:alpha"] = _mapping("Alpha", "smcp_ID_1")
    assert {text: store.embedded_originals(text) for text in TEXTS} == {text: _fresh(store, text) for text in TEXTS}
    # Added after the memo entry exists: found without a full rescan.
    store["k:beta"] = _mapping("Beta", "smcp_ID_2")
    store["k:poss"] = _mapping("'s", "smcp_ID_3")
    store["k:ko"] = _mapping("은하수", "smcp_ID_4")
    for text in TEXTS:
        assert store.embedded_originals(text) == _fresh(store, text)
    assert store.embedded_originals("AlphaBeta") == {"Alpha", "Beta"}
    assert store.embedded_originals("the plan's report") == {"'s"}


@pytest.mark.parametrize("remove", [
    lambda store: store.__delitem__("k:beta"),
    lambda store: store.pop("k:beta"),
    lambda store: store.popitem(),
    lambda store: store.clear(),
    lambda store: store.__setitem__("k:beta", _mapping("Delta", "smcp_ID_9")),
])
def test_memo_is_invalidated_by_removal_or_replacement(remove):
    store = _store()
    store["k:alpha"] = _mapping("Alpha", "smcp_ID_1")
    store["k:beta"] = _mapping("Beta", "smcp_ID_2")
    assert store.embedded_originals("AlphaBeta Delta") == {"Alpha", "Beta"}
    remove(store)
    assert store.embedded_originals("AlphaBeta Delta") == _fresh(store, "AlphaBeta Delta")
    assert "Beta" not in store.embedded_originals("AlphaBeta Delta")


def test_memo_ignores_empty_and_non_mapping_values_like_the_scan():
    store = _store()
    store.embedded_originals("anything")
    store["k:other"] = "not a mapping"
    assert store.embedded_originals("anything") == _fresh(store, "anything") == frozenset()


def test_memo_is_bounded_and_skips_large_texts(monkeypatch):
    monkeypatch.setattr(session_module, "_EMBEDDED_MEMO_ENTRIES", 3)
    monkeypatch.setattr(session_module, "_EMBEDDED_MEMO_CHARS", 40)
    monkeypatch.setattr(session_module, "_EMBEDDED_MEMO_TEXT_CHARS", 20)
    store = _store()
    store["k:alpha"] = _mapping("Alpha", "smcp_ID_1")
    for index in range(5):
        assert store.embedded_originals(f"Alpha {index}") == {"Alpha"}
    assert len(store._embedded_memo) == 3
    large = "Alpha " + "x" * 30
    assert store.embedded_originals(large) == {"Alpha"}
    assert large not in store._embedded_memo
    for text in ["Alpha " + "y" * 12, "Alpha " + "z" * 12, "Alpha " + "w" * 12]:
        store.embedded_originals(text)
    assert store._embedded_memo_chars <= 40
    assert store._embedded_memo_chars == sum(len(text) for text in store._embedded_memo)


def test_memo_randomized_against_full_scan():
    rng = random.Random(356)
    alphabet = "ab가나 '"
    store = _store()
    texts = ["".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12))) for _ in range(40)]
    for step in range(400):
        operation = rng.random()
        keys = list(store)
        if operation < 0.55 or not keys:
            original = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 3)))
            store[f"k:{step}"] = _mapping(original, f"smcp_ID_{step}")
        elif operation < 0.7:
            del store[rng.choice(keys)]
        elif operation < 0.8:
            original = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 3)))
            store[rng.choice(keys)] = _mapping(original, f"smcp_ID_r{step}")
        elif operation < 0.82:
            store.clear()
        text = rng.choice(texts)
        assert store.embedded_originals(text) == _fresh(store, text)


def test_mask_cache_key_is_unchanged_by_memo():
    session = GatewaySession()
    session.mask("please review hidden_customer_ledger()", code=True)
    text = "Ask hidden_customer_ledger owner about the plan's status"
    key = session._mask_cache_key(text, False, "auto")
    session.session.forward_store._embedded_memo.clear()
    assert session._mask_cache_key(text, False, "auto") == key


def test_sessions_do_not_share_dependency_memos():
    first, second = GatewaySession(), GatewaySession()
    text = "please read the report"
    assert first.mask(text) == text and second.mask(text) == text
    first.mask("read", code=True)
    assert "read" not in first.mask(text)
    assert second.mask(text) == text
    assert first.session.forward_store._embedded_memo is not second.session.forward_store._embedded_memo


def test_cached_pattern_after_mapping_removal_matches_fresh_session():
    session = GatewaySession()
    text = "please read the report"
    session.mask("read", code=True)
    assert "read" not in session.mask(text)
    store = session.session.forward_store
    with session.session.operation():
        for key in [key for key, mapping in store.items() if mapping.original == "read"]:
            del store[key]
    assert session.mask(text) == GatewaySession().mask(text) == text


@pytest.mark.parametrize("rule, text", [
    ("Café", "visit Café today"),
    ("Café", "visit Café today"),
])
def test_cached_forced_rule_pattern_keeps_nfc_and_nfd_spellings(rule, text):
    session = GatewaySession()
    session.forced_rules = lambda: (rule,)
    masked = session.mask(text)
    assert unicodedata.normalize("NFC", "Café") not in unicodedata.normalize("NFC", masked)
    assert session.restore(masked) == text
    session.forced_rules = lambda: ()
    other = GatewaySession()
    assert other.mask(text) == text


def test_forced_rule_cache_never_holds_per_call_terms():
    gateway_module._configured_rule_pattern.cache_clear()
    session = GatewaySession()
    session.forced_rules = lambda: ("Configured",)
    session._force_mask("Configured SchemaOnlyTerm", ("SchemaOnlyTerm",))
    session._force_mask("Configured", ())
    info = gateway_module._configured_rule_pattern.cache_info()
    assert info.currsize == 1
    session._force_mask("Configured again", ())
    assert gateway_module._configured_rule_pattern.cache_info().hits == info.hits + 1


@pytest.mark.parametrize("rules", [("4",), ("2032-02-28", "-3.25"), ("1,234", "12.40", "Name"), ("Café",)])
def test_cached_rule_pattern_equals_uncached_pattern(rules):
    cached = gateway_module._configured_rule_pattern(rules)
    fresh = gateway_module.forced_rule_pattern(rules)
    assert cached is not None and fresh is not None and cached.pattern == fresh.pattern


@pytest.mark.parametrize("rules, text", [
    (("2032-02-28", "4"), "Ship 4 units on 2032-02-28, not 12.40 or 1,234."),
    (("-3.25",), "The delta was -3.25 and later 3.25."),
    (("4096",), "Use 4096 tokens; see `limit = 4096` in config."),
])
def test_digit_rules_mask_identically_with_and_without_pattern_cache(rules, text, monkeypatch):
    from secure_gateway.engine import strategies

    def run(cached):
        counter = {"value": 7}

        def draw(limit):
            counter["value"] += 1
            return counter["value"] % limit

        monkeypatch.setattr(strategies.secrets, "randbelow", draw)
        if not cached:
            monkeypatch.setattr(gateway_module, "_configured_rule_pattern", gateway_module.forced_rule_pattern)
        session = GatewaySession(natural_language="en")
        session.forced_rules = lambda: rules
        payload = {"model": "fixture", "max_output_tokens": 4096,
                   "input": [{"role": "user", "content": text}]}
        masked = session.request(payload, dialect="responses")
        restored = session.restore(masked["input"][0]["content"])
        monkeypatch.undo()
        return masked, restored, sorted((key, m.original, m.surrogate) for key, m in session.session.forward_store.items())

    cached, uncached = run(True), run(False)
    assert cached == uncached
    assert cached[1] == text

@pytest.mark.parametrize("features", ["none", 309, 310, 316, 318, 319, "all"])
def test_memo_is_identical_for_sessions_with_features_enabled(features, monkeypatch):
    """#354 feature-flag sessions: memoized key path equals the pre-#356 full scan."""
    from test_gateway_features import (ALL_ON, BUNDLE, CORRECTION, FOLLOW, KO, NAMES, SINGLE,
                                       request)
    from secure_gateway.engine import strategies

    selected = None if features == "none" else ALL_ON if features == "all" else SINGLE[features][0]
    texts = [KO, NAMES, FOLLOW, CORRECTION, BUNDLE, NAMES + " " + FOLLOW]

    def run(full_scan):
        counter = {"value": 100000}

        def draw(limit):
            counter["value"] += 1
            return counter["value"] % limit

        monkeypatch.setattr(strategies.secrets, "randbelow", draw)
        session = GatewaySession(natural_language="auto", features=selected)
        session.forced_rules = lambda: ("publication",)
        store = session.session.forward_store
        if full_scan:
            monkeypatch.setattr(store, "embedded_originals",
                                lambda text: frozenset(store.originals_in(text, embedded=True)))
        output = []
        history: list[str] = []
        for text in texts:
            history.append(text)
            # Resend the whole history each turn, as clients do.
            payload = request(history[0])
            payload["input"] = [{"role": "user", "content": item} for item in history]
            output.append(session.request(payload))
        return output, sorted((key, mapping.original, mapping.surrogate) for key, mapping in store.items())

    assert run(full_scan=False) == run(full_scan=True)