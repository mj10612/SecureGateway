"""Native compiler/SQLite proof for Java escapes and SQL grammar bindings."""
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import subprocess

import pytest

from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import SurrogateStrategy
from secure_gateway.session import PrivacySession
from secure_gateway.encrypted_session import load_session, save_session


def mask(engine, session, source, language):
    return engine.mask_code(source, session.session_id, session.generator,
                            session.forward_store, session.reverse_store,
                            language=language).masked_text


def exact(engine, session, masked, source):
    assert engine.unmask(masked, session.session_id, session.reverse_store,
                         session.strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", [
    r'class PrivateClass { int priv\u0061teValue = 7; int privateMethod(){return privateValue;} }',
    r'cl\uuuu0061ss PrivateClass { int privateValue = 7; int privateMethod(){return priv\u0061teValue;} }',
    r'class PrivateClass { int privateValue = 7; int privateMethod(){return priv\u0061teValue + priv\uu0061teValue;} }',
    r'class PrivateClass { int private$Value=7; int get(){return private\u0024Value;} }',
])
def test_java_unicode_identifiers_native_and_snapshot(strategy, source, tmp_path):
    javac = shutil.which("javac") or r"C:\Program Files\Java\jdk1.8.0_202\bin\javac.exe"
    if not Path(javac).exists():
        pytest.skip("Native javac required")
    e = MaskingEngine()
    s = PrivacySession("java", strategy=strategy)
    masked = mask(e, s, source, "java")
    for index, code in enumerate((source, masked)):
        work = tmp_path / str(index)
        work.mkdir()
        path = work / "Probe.java"
        path.write_text(code, encoding="utf-8")
        result = subprocess.run([javac, str(path)], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
    exact(e, s, masked, source)
    path = tmp_path / "java.enc"
    save_session(path, s, "test-password")
    s = load_session(path, "test-password")
    exact(e, s, masked, source)
    more = r'class AnotherClass { int privateValue=7; int read(){return priv\uu0061teValue;} }'
    exact(e, s, mask(e, s, more, "java"), more)


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", [
    "WITH privateCte AS (SELECT 7) SELECT * FROM privateCte;",
    "CREATE TABLE privateTable(privateValue DEFAULT 7); INSERT INTO privateTable DEFAULT VALUES; SELECT privateValue FROM privateTable;",
    "CREATE TABLE privateTable(privateValue); INSERT INTO privateTable VALUES (7) RETURNING privateValue;",
    "CREATE TABLE privateTable(key); INSERT INTO privateTable(key) VALUES (7); SELECT [key] FROM privateTable;",
    "CREATE TABLE privateTable(key PRIMARY KEY); INSERT INTO privateTable(key) VALUES (7); SELECT key FROM privateTable;",
    "CREATE TABLE privateParent(key PRIMARY KEY); CREATE TABLE privateChild(key, FOREIGN KEY(key) REFERENCES privateParent(key)); INSERT INTO privateParent(key) VALUES(7); INSERT INTO privateChild(key) VALUES(7); SELECT [key] FROM privateChild;",
    'CREATE TABLE privateTable("with", "default", "returning"); INSERT INTO privateTable VALUES(7,8,9); SELECT "with", "default", "returning" FROM privateTable;',
])
def test_sql_native_grammar_and_binding(strategy, source, tmp_path):
    e = MaskingEngine()
    s = PrivacySession("sql", strategy=strategy)
    masked = mask(e, s, source, "sql")
    def run(code):
        with closing(sqlite3.connect(":memory:")) as db:
            rows = []
            for statement in code.split(";"):
                if statement.strip():
                    rows = db.execute(statement).fetchall()
            return rows
    assert run(masked) == run(source)
    if "privateTable(key)" in source:
        assert "(key)" not in masked
    exact(e, s, masked, source)
    path = tmp_path / "sql.enc"
    save_session(path, s, "test-password")
    s = load_session(path, "test-password")
    exact(e, s, masked, source)


@pytest.mark.parametrize("source", [r'class PrivateClass { int privateValue\u003b }', r'// comment\u000aclass PrivateClass {}', r'class PrivateClass { String x="\u0022"; }'])
def test_java_structural_escapes_are_rejected_before_allocation(source):
    e = MaskingEngine()
    s = PrivacySession("java-structural")
    with pytest.raises(ValueError, match="structural Java Unicode"):
        mask(e, s, source, "java")
    assert not s.forward_store


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_java_string_backslash_eligibility_and_identifier_dollar(strategy):
    source = r'class PrivateClass { int private$Value=7; int get(){return private\u0024Value;} String text="\\u0061"; }'
    e = MaskingEngine()
    s = PrivacySession("java-escape-eligibility", strategy=strategy)
    masked = mask(e, s, source, "java")
    names = [m for m in s.forward_store.values() if m.original in {"private$Value", r"private\u0024Value"}]
    assert len(names) == 2 and names[0].identifier_base == names[1].identifier_base
    exact(e, s, masked, source)


def test_gateway_fenced_sql_uses_fixed_keyword_context():
    from secure_gateway.gateway import GatewaySession
    source = "CREATE TABLE privateTable(key); INSERT INTO privateTable(key) VALUES(7); SELECT [key] FROM privateTable;"
    session = GatewaySession()
    masked = session.mask("```sql\n" + source + "\n```")
    with closing(sqlite3.connect(":memory:")) as db:
        for statement in masked.split("\n", 1)[1][:-3].split(";"):
            if statement.strip():
                rows = db.execute(statement).fetchall()
        assert rows == [(7,)]
    assert session.restore(masked) == "```sql\n" + source + "\n```"


def test_cross_language_session_java_spelling_binding():
    e = MaskingEngine()
    s = PrivacySession("mixed-languages")
    first = mask(e, s, "privateValue=7", "python")
    java = r'class PrivateClass { int privateValue=7; int read(){return priv\u0061teValue;} }'
    masked = mask(e, s, java, "java")
    exact(e, s, first, "privateValue=7")
    exact(e, s, masked, java)
    from secure_gateway.engine.code_identifiers import identifier_key
    mappings = [m for m in s.reverse_store.values() if m.original in {"privateValue", r"priv\u0061teValue"}]
    assert len({identifier_key(m.surrogate, "java") for m in mappings}) == 1


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_java_unicode_literal_payload_is_masked_without_normalizing_source(strategy):
    source = r'class PrivateClass { String text="priv\u0061te"; }'
    e = MaskingEngine()
    s = PrivacySession("java-literal", strategy=strategy)
    masked = mask(e, s, source, "java")
    assert r"priv\u0061te" not in masked
    exact(e, s, masked, source)
