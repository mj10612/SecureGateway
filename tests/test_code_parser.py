"""Tests for code syntax and keyword preservation parser."""

from secure_mcp.engine.code_parser import CodeParser, literal_parts
from secure_mcp.models import TokenType


def test_keyword_preservation():
    code = "def process(user_id):\n    return user_id * 2"
    tokens = CodeParser.tokenize(code)

    keywords = [val for val, t_type, sub in tokens if sub == "keyword"]
    assert "def" in keywords
    assert "return" in keywords

    identifiers = [val for val, t_type, sub in tokens if t_type == TokenType.IDENTIFIER]
    assert "process" in identifiers
    assert "user_id" in identifiers


def test_sql_keywords():
    code = "SELECT user_name, email FROM accounts WHERE id = 101;"
    tokens = CodeParser.tokenize(code)

    keywords = [val for val, t_type, sub in tokens if sub == "keyword"]
    assert "SELECT" in keywords
    assert "FROM" in keywords
    assert "WHERE" in keywords


def test_string_literal_parsing():
    code = 'secret_key = "sk-live-supersecret123"'
    tokens = CodeParser.tokenize(code)

    literals = [val for val, t_type, sub in tokens if t_type == TokenType.LITERAL]
    assert len(literals) == 1
    assert "supersecret" in literals[0]


def test_javascript_hashbang_and_regular_comment_are_lexed_as_comments():
    source = "#!/Users/PrivateCustomer/bin/node\nconst pattern = /PrivateCustomer/;"
    tokens = CodeParser.tokenize(source, "javascript")

    assert tokens[0] == (
        "#!/Users/PrivateCustomer/bin/node",
        TokenType.LITERAL,
        "comment",
    )
    assert literal_parts(tokens[0][0], tokens[0][2]) == ("#!", "")
    assert any(kind == "regex" for _, _, kind in tokens)

    ordinary_comment = CodeParser.tokenize(
        "// /Users/PrivateCustomer/bin/node\nconst pattern = /PrivateCustomer/;",
        "javascript",
    )
    assert ordinary_comment[0][0] == "// /Users/PrivateCustomer/bin/node"
    assert ordinary_comment[0][2] == "comment"
    assert any(kind == "regex" for _, _, kind in ordinary_comment)
