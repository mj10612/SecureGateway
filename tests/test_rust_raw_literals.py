"""Rust raw delimiters and exact restoration, including zero hashes."""
import pytest

from secure_mcp.engine.code_parser import CodeParser, literal_parts
from secure_mcp.engine.masking_engine import MaskingEngine
from secure_mcp.models import SurrogateStrategy, TokenType
from secure_mcp.session import PrivacySession


@pytest.mark.parametrize('prefix', ['r', 'br'])
@pytest.mark.parametrize('hashes', ['', '#', '##'])
@pytest.mark.parametrize('body', ['C:\\PrivateCustomer\\', 'PrivateCustomer\nsecond line', '', 'PrivateCustomer"quoted' ])
@pytest.mark.parametrize('strategy', list(SurrogateStrategy))
def test_rust_raw_literals_mask_and_restore(prefix, hashes, body, strategy):
    if not hashes and '"' in body:
        pytest.skip('An interior quote needs a hash delimiter')
    opening, closing = prefix + hashes + '"', '"' + hashes
    literal = opening + body + closing
    source = 'let privateValue = ' + literal + ';'
    tokens = CodeParser.tokenize(source, 'rust')
    assert (literal, TokenType.LITERAL, 'string') in tokens
    assert literal_parts(literal, 'string') == (opening, closing)
    session = PrivacySession('rust-raw', strategy=strategy)
    engine = MaskingEngine()
    result = engine.mask_code(source, session.session_id, session.generator,
                              session.forward_store, session.reverse_store, language='rust')
    assert 'PrivateCustomer' not in result.masked_text
    assert 'privateValue' not in result.masked_text
    assert any(kind == TokenType.LITERAL and value.startswith(opening) and value.endswith(closing)
               for value, kind, _ in CodeParser.tokenize(result.masked_text, 'rust'))
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize('prefix', ['r', 'br'])
def test_rust_unterminated_zero_hash_raw_literal_is_rejected(prefix):
    with pytest.raises(ValueError, match='Unterminated'):
        CodeParser.tokenize('let privateValue = ' + prefix + '"PrivateCustomer', 'rust')


def test_python_raw_literal_still_uses_python_quote_rules():
    source = 'value = r"PrivateCustomer\\"quoted"'
    assert ('r"PrivateCustomer\\"quoted"', TokenType.LITERAL, 'string') in CodeParser.tokenize(source, 'python')


def test_python_raw_triple_literal_keeps_complete_delimiters():
    assert literal_parts('r"""PrivateCustomer"""', "string") == ('r"""', '"""')
