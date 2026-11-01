"""Encoded literal data must stay private without merging adjacent aliases (#269)."""

import pytest

from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.gateway import GatewaySession
from secure_gateway.models import SurrogateStrategy
from secure_gateway.session import PrivacySession


CASES = [
    ('csharp', r'var message = $"\u0041\u006c\u0069\u0063\u0065 {user}";', r'\u0041'),
    ('csharp', r'var message = $"{user}\x41\x6c\x69\x63\x65";', r'\x41'),
    ('kotlin', r'val message = "\u0041\u006c\u0069\u0063\u0065 $user"', r'\u0041'),
    ('kotlin', r'val message = "$user\u0041tail"', r'\u0041'),
    ('ruby', r'message = "\x41\x6c\x69\x63\x65 #{user}"', r'\x41'),
    ('ruby', r'message = "\101\154\151\143\145 #{user}"', r'\101'),
    ('swift', r'let message = "\u{41}\u{6c}\u{69}\u{63}\u{65} \(user)"', r'\u{41}'),
    ('powershell', r'$message = "`u{41}`u{6c}`u{69}`u{63}`u{65} $user"', '`u{41}'),
    ('bash', 'cat <<EOF\n' + r'\u0041\u006c\u0069\u0063\u0065 $user' + '\nEOF\n', r'\u0041'),
]


@pytest.mark.parametrize('strategy', list(SurrogateStrategy))
@pytest.mark.parametrize('language,source,escape', CASES)
def test_encoded_interpolation_is_private_and_exact(language, source, escape, strategy):
    engine = MaskingEngine()
    session = PrivacySession('encoded', strategy=strategy)
    masked = engine.mask_code(source, session.session_id, session.generator,
                              session.forward_store, session.reverse_store,
                              language=language).masked_text
    assert escape not in masked
    assert 'user' not in masked
    assert engine.unmask(masked, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize('language,source,escape', CASES)
def test_gateway_encoded_interpolation_roundtrip(language, source, escape):
    session = GatewaySession()
    source = f'```{language}\n{source}\n```'
    masked = session.mask(source)
    assert escape not in masked
    assert session.restore(masked) == source


def test_structural_escapes_keep_existing_interpolation_bindings():
    engine = MaskingEngine()
    session = PrivacySession('structural')
    source = r'var message = $"hello\n{user}\t world";'
    masked = engine.mask_code(source, session.session_id, session.generator,
                              session.forward_store, session.reverse_store,
                              language='csharp').masked_text
    assert r'\n' in masked and r'\t' in masked
    assert '{smcp_ID_' in masked
    assert engine.unmask(masked, session.session_id, session.reverse_store,
                         strict=True).unmasked_text == source
