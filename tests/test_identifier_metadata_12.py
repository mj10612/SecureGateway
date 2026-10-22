"""Authenticated snapshots still validate the identifier spelling contract."""

import pytest

from secure_gateway.engine.code_identifiers import valid_identifier_alias
from secure_gateway.models import TokenMapping, TokenType


def mapping(**updates):
    values = dict(original='privatename', surrogate='smcp_id_1',
                  token_type=TokenType.IDENTIFIER, context='code',
                  identifier_base='smcp_ID_1', identifier_language='sql:standard',
                  identifier_key='privatename', identifier_quoted=True)
    return TokenMapping(**(values | updates))


def test_quoted_standard_identifier_alias_has_canonical_case():
    assert valid_identifier_alias(mapping())
    assert not valid_identifier_alias(mapping(surrogate='SMCP_ID_1'))


def test_sqlite_identifier_alias_comparison_is_ascii_case_insensitive():
    assert valid_identifier_alias(mapping(identifier_language='sql:sqlite', surrogate='SMCP_ID_1'))


@pytest.mark.parametrize('updates', [
    {'identifier_language': 'not-a-language'},
    {'identifier_language': 'sql:mysql'},
    {'context': 'text'},
    {'token_type': TokenType.LITERAL},
    {'identifier_key': 'another-name'},
    {'identifier_base': 'unregistered_alias'},
])
def test_invalid_binding_metadata_is_not_a_valid_snapshot_alias(updates):
    assert not valid_identifier_alias(mapping(**updates))


def test_quoted_alias_base_is_reserved_after_snapshot_reload(tmp_path):
    from secure_gateway.encrypted_session import load_session, save_session
    from secure_gateway.engine.masking_engine import MaskingEngine
    from secure_gateway.session import PrivacySession

    engine = MaskingEngine()
    session = PrivacySession('quoted-allocation')
    def mask(session, name):
        return engine.mask_code(f'SELECT "{name}";', session.session_id, session.generator,
                                session.forward_store, session.reverse_store,
                                language='sql', sql_dialect='standard').masked_text
    first = mask(session, 'firstTable')
    path = tmp_path / 'session.enc'
    save_session(path, session, 'synthetic-password')
    loaded = load_session(path, 'synthetic-password', session.session_id)
    second = mask(loaded, 'secondTable')
    assert first != second
    assert engine.unmask(first, loaded.session_id, loaded.reverse_store,
                         strict=True).unmasked_text == 'SELECT "firstTable";'
    assert engine.unmask(second, loaded.session_id, loaded.reverse_store,
                         strict=True).unmasked_text == 'SELECT "secondTable";'
