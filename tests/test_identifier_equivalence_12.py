"""Semantic binding equivalence must coexist with exact source restoration."""
from contextlib import closing
import shutil
import sqlite3
import subprocess

import pytest

from secure_gateway.encrypted_session import load_session, save_session
from secure_gateway.engine.code_identifiers import identifier_key
from secure_gateway.engine.code_parser import CodeParser
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.gateway import GatewaySession
from secure_gateway.models import SurrogateStrategy, TokenType
from secure_gateway.session import PrivacySession


def mask(engine, session, source, language, **kwargs):
    return engine.mask_code(source, session.session_id, session.generator,
                            session.forward_store, session.reverse_store,
                            language=language, **kwargs).masked_text


def restore(engine, session, source):
    return engine.unmask(source, session.session_id, session.reverse_store,
                         session.strategy, strict=True).unmasked_text


def native_python(source):
    namespace = {}
    exec(source, namespace)
    assert [value for key, value in namespace.items() if key != "__builtins__"] == [8, 8]


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", ["K = 7\nK += 1\nresult = K", "café = 7\ncafe\u0301 += 1\nresult = café"])
def test_python_normalized_bindings_execute_and_roundtrip(strategy, source):
    session = PrivacySession("python-equivalence", strategy=strategy)
    engine = MaskingEngine()
    masked = mask(engine, session, source, "python")
    native_python(source)
    native_python(masked)
    assert restore(engine, session, masked) == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_javascript_escaped_binding_native_execution_and_roundtrip(strategy):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for native JavaScript binding verification")
    source = r"var \u0070rivateName = 7; if (privateName !== 7) throw 1;"
    engine = MaskingEngine()
    session = PrivacySession("js-equivalence", strategy=strategy)
    masked = mask(engine, session, source, "javascript")
    for program in [source, masked]:
        checked = subprocess.run([node, "--eval", program], capture_output=True, text=True, timeout=60)
        assert checked.returncode == 0, checked.stderr
    assert restore(engine, session, masked) == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("dialect,quote", [("sqlite", '"'), ("sqlite", "`"), ("sqlite", "["), ("standard", "")])
def test_sql_case_equivalence_runs_real_sqlite_and_roundtrips(strategy, dialect, quote):
    end = "]" if quote == "[" else quote
    source = (f"CREATE TABLE {quote}privateTable{end} ({quote}privateColumn{end} INTEGER); "
              "INSERT INTO PRIVATETABLE (PRIVATECOLUMN) VALUES (1); "
              "SELECT privatecolumn FROM privatetable;")
    engine = MaskingEngine()
    session = PrivacySession("sql-equivalence", strategy=strategy)
    masked = mask(engine, session, source, "sql", sql_dialect=dialect)
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(source)
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(masked)
    assert restore(engine, session, masked) == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_standard_sql_quoted_case_sensitive_names_stay_distinct(strategy):
    engine = MaskingEngine()
    session = PrivacySession("sql-quoted-case", strategy=strategy)
    source = 'SELECT "privateName", "PRIVATENAME";'
    masked = mask(engine, session, source, "sql", sql_dialect="standard")
    identifiers = [raw for raw, kind, _ in CodeParser.tokenize(masked, "sql") if kind == TokenType.IDENTIFIER]
    assert len(identifiers) == 2
    assert identifiers[0] != identifiers[1]
    assert restore(engine, session, masked) == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_standard_sql_quoted_lowercase_name_matches_folded_unquoted_binding(strategy):
    engine = MaskingEngine()
    session = PrivacySession("sql-quoted-folding", strategy=strategy)
    source = 'SELECT privateName, "privateName", "privatename";'
    masked = mask(engine, session, source, "sql", sql_dialect="standard")
    names = []
    for raw, kind, subkind in CodeParser.tokenize(masked, "sql"):
        if kind == TokenType.IDENTIFIER:
            quoted = subkind == "quoted_identifier"
            names.append(identifier_key(raw[1:-1] if quoted else raw, "sql:standard", quoted=quoted))
    assert len(names) == 3
    assert names[0] == names[2]
    assert names[0] != names[1]
    assert restore(engine, session, masked) == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_rust_raw_plain_aliases_remain_one_binding_and_exact_spelling(strategy):
    engine = MaskingEngine()
    session = PrivacySession("rust-equivalence", strategy=strategy)
    source = "let r#privateName = 7; let answer = privateName;"
    masked = mask(engine, session, source, "rust")
    identifiers = [raw for raw, kind, _ in CodeParser.tokenize(masked, "rust") if kind == TokenType.IDENTIFIER]
    assert len(identifiers) == 3
    assert identifier_key(identifiers[0], "rust") == identifier_key(identifiers[2], "rust")
    assert restore(engine, session, masked) == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("language,source,continued", [
    ("python", "K = 7\nK += 1\nresult = K", "Ｋ = 7\nK += 1\nresult = Ｋ"),
    ("javascript", r"var \u0070rivateName=7; var result=privateName;", r"var \u0070\u0072ivateName=7; var result=privateName;"),
    ("sql", "CREATE TABLE privateTable (privateColumn INTEGER); SELECT PRIVATECOLUMN FROM PRIVATETABLE;",
     "SELECT privatecolumn FROM privatetable;"),
    ("rust", "let r#privateName=7; let answer=privateName;", "let privateName=7; let answer=r#privateName;"),
])
def test_encrypted_snapshot_restores_extra_spellings_and_continues_allocation(tmp_path, strategy, language, source, continued):
    engine = MaskingEngine()
    session = PrivacySession("equivalence-snapshot", strategy=strategy)
    first = mask(engine, session, source, language)
    path = tmp_path / "snapshot.enc"
    save_session(path, session, "local-regression-password")
    reloaded = load_session(path, "local-regression-password", session.session_id)
    assert restore(engine, reloaded, first) == source
    second = mask(engine, reloaded, continued, language)
    assert restore(engine, reloaded, second) == continued
    assert restore(engine, reloaded, first) == source
    if language == "python":
        native_python(second)
    elif language == "javascript" and (node := shutil.which("node")):
        checked = subprocess.run([node, "--eval", second], capture_output=True, text=True, timeout=60)
        assert checked.returncode == 0, checked.stderr
    elif language == "sql":
        with closing(sqlite3.connect(":memory:")) as db:
            db.executescript(first + second)
    elif language == "rust":
        names = [raw for raw, kind, _ in CodeParser.tokenize(second, "rust")
                 if kind == TokenType.IDENTIFIER]
        assert identifier_key(names[0], "rust") == identifier_key(names[2], "rust")


@pytest.mark.parametrize("languages", [("python", "javascript"), ("javascript", "python")])
@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_gateway_shared_cross_language_aliases_do_not_split_later_equivalent_binding(languages, strategy):
    gateway = GatewaySession(session=PrivacySession("cross-context", strategy=strategy))
    # Seed an identical raw spelling in a different identifier comparison context.
    first_language, second_language = languages
    gateway.engine.mask_code("privateName", gateway.session.session_id, gateway.session.generator,
                             gateway.session.forward_store, gateway.session.reverse_store,
                             language=first_language)
    source = (r"var privateName=7; if (\u0070rivateName !== 7) throw 1;"
              if second_language == "javascript" else "privateName=7\nｐrivateName += 1\nresult=privateName")
    masked = mask(gateway.engine, gateway.session, source, second_language)
    assert restore(gateway.engine, gateway.session, masked) == source
    if second_language == "python":
        native_python(masked)
    elif node := shutil.which("node"):
        checked = subprocess.run([node, "--eval", masked], capture_output=True, text=True, timeout=60)
        assert checked.returncode == 0, checked.stderr


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_gateway_prose_alias_reused_in_code_still_normalizes_equivalent_spelling(strategy):
    gateway = GatewaySession(session=PrivacySession("prose-context", strategy=strategy))
    gateway.mask("PrivateCustomer")
    source = "PrivateCustomer=7\nＰrivateCustomer += 1\nresult=PrivateCustomer"
    masked = mask(gateway.engine, gateway.session, source, "python")
    native_python(masked)
    assert restore(gateway.engine, gateway.session, masked) == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("reload_before", [False, True])
@pytest.mark.parametrize("language,seed,other_language,other,source", [
    ("python", "K", "javascript", "K", "K=7\nK+=1\nresult=K"),
    ("javascript", r"\u0070rivateName", "python", "privateName",
     r"var \u0070rivateName=7; if(privateName !== 7) throw 1;"),
])
def test_interleaved_foreign_binding_does_not_override_equivalent_group(
    tmp_path, strategy, reload_before, language, seed, other_language, other, source
):
    engine = MaskingEngine()
    session = PrivacySession("interleaved-identifiers", strategy=strategy)
    seed_masked = mask(engine, session, seed, language)
    other_masked = mask(engine, session, other, other_language)
    if reload_before:
        path = tmp_path / "before.enc"
        save_session(path, session, "offline-interleaved-password")
        session = load_session(path, "offline-interleaved-password", session.session_id)
    masked = mask(engine, session, source, language)
    if language == "python":
        native_python(masked)
    elif node := shutil.which("node"):
        checked = subprocess.run([node, "--eval", masked], capture_output=True, text=True, timeout=60)
        assert checked.returncode == 0, checked.stderr
    assert restore(engine, session, seed_masked) == seed
    assert restore(engine, session, other_masked) == other
    assert restore(engine, session, masked) == source
    after = tmp_path / "after.enc"
    save_session(after, session, "offline-interleaved-password")
    reloaded = load_session(after, "offline-interleaved-password", session.session_id)
    assert restore(engine, reloaded, masked) == source
    assert mask(engine, reloaded, source, language) == masked
