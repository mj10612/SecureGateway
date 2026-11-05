"""Execute SQL before/after masking so type semantics cannot hide behind round trips."""
from contextlib import closing
import sqlite3

import pytest

from secure_gateway.engine.code_parser import CodeParser
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.gateway import GatewaySession
from secure_gateway.models import SurrogateStrategy, TokenType
from secure_gateway.session import PrivacySession


SOURCES = [
    "SELECT CAST(3.14 AS INT);",
    "SELECT CAST(CAST(3.14 AS DECIMAL(10,2)) AS DOUBLE PRECISION);",
    "SELECT CAST((SELECT 7) AS INTEGER);",
    'SELECT CAST(3.14 AS "INTEGER");',
    "CREATE TABLE t(x INTEGER PRIMARY KEY); INSERT INTO t DEFAULT VALUES; SELECT x FROM t;",
    "CREATE TABLE IF NOT EXISTS t(x INTEGER PRIMARY KEY); INSERT INTO t DEFAULT VALUES; SELECT x FROM t;",
    'CREATE TABLE "privateTable"("privateValue" INTEGER PRIMARY KEY); INSERT INTO "privateTable" DEFAULT VALUES; SELECT "privateValue" FROM "privateTable";',
    "CREATE TEMPORARY TABLE t(x INTEGER PRIMARY KEY AUTOINCREMENT); INSERT INTO t DEFAULT VALUES; SELECT x FROM t;",
    'CREATE TABLE t(x "INTEGER" PRIMARY KEY); INSERT INTO t DEFAULT VALUES; SELECT x FROM t;',
    "CREATE TABLE t(x 'INTEGER' PRIMARY KEY); INSERT INTO t DEFAULT VALUES; SELECT x FROM t;",
    'CREATE TABLE t("cast" INTEGER, integer TEXT, text REAL); INSERT INTO t VALUES(3,4,5); SELECT "cast",integer,text FROM t;',
    "CREATE TABLE t(integer INTEGER CHECK(integer>0), text TEXT, CONSTRAINT integer UNIQUE(integer)); INSERT INTO t VALUES(7,8); SELECT integer,text FROM t;",
    "CREATE TABLE t(x INTEGER, y NUMERIC(10,2), CONSTRAINT privateName PRIMARY KEY(x,y)); INSERT INTO t VALUES(1,2); SELECT x,y FROM t;",
    "CREATE /* private comment */ TABLE t(x /* private type */ INTEGER PRIMARY KEY); INSERT INTO t DEFAULT VALUES; SELECT x FROM t;",
    "CREATE TABLE t(integer INTEGER); INSERT INTO t VALUES(7); SELECT CAST(integer AS INTEGER) FROM t;",
]


def run(source):
    with closing(sqlite3.connect(":memory:")) as db:
        result = []
        for statement in source.split(";"):
            if statement.strip():
                cursor = db.execute(statement)
                if cursor.description:
                    result.append(cursor.fetchall())
        return result


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("source", SOURCES)
def test_sql_structural_types_keep_native_results_and_exact_restore(strategy, source):
    engine = MaskingEngine()
    session = PrivacySession("sql-types", strategy=strategy)
    masked = engine.mask_code(source, session.session_id, session.generator,
                              session.forward_store, session.reverse_store,
                              language="sql", sql_dialect="sqlite").masked_text
    assert run(masked) == run(source), masked
    assert engine.unmask(masked, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize("source", SOURCES)
def test_gateway_fenced_sql_keeps_native_results_and_restores(source):
    gateway = GatewaySession()
    fenced = "```sql\n" + source + "\n```"
    masked = gateway.mask(fenced)
    assert run(masked.split("\n", 1)[1].rsplit("\n", 1)[0]) == run(source)
    assert gateway.restore(masked) == fenced


@pytest.mark.parametrize("word", ["cast", "integer", "text", "precision", "varchar"])
def test_type_like_column_names_remain_private(word):
    identifier = f'"{word}"' if word == "cast" else word
    source = f"CREATE TABLE t({identifier} INTEGER); SELECT {identifier} FROM t;"
    tokens = CodeParser().tokenize(source, "sql")
    matches = [kind for raw, kind, _ in tokens if raw == identifier]
    assert matches and all(kind == TokenType.IDENTIFIER for kind in matches)


def test_type_sized_values_preserved_while_unknown_types_are_private():
    tokens = CodeParser().tokenize("CREATE TABLE t(x privateType, y VARCHAR(20));", "sql")
    assert ("privateType", TokenType.IDENTIFIER, "identifier") in tokens
    assert ("VARCHAR", TokenType.GRAMMAR, "keyword") in tokens
    # SELECT aliases, function arguments and quoted column names are not type declarations.
    tokens = CodeParser().tokenize('SELECT integer AS text, privateFunction(varchar), "INTEGER" FROM t;', "sql")
    for raw, kind, _ in tokens:
        if raw in {"integer", "text", "varchar", '"INTEGER"'}:
            assert kind == TokenType.IDENTIFIER
