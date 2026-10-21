"""Code numbers are preserved by default; masking requires explicit opt-in."""
import pytest
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import SurrogateStrategy, TokenType
from secure_gateway.session import PrivacySession


@pytest.mark.parametrize('strategy', list(SurrogateStrategy))
@pytest.mark.parametrize('source,language', [
    ('limit = -100\nratio = 3.14\nvalue = 1e-3\nmask = 0xFF\nbits = 0b101\ncount = 1_000', 'python'),
    ('for (let privateIndex = 0; privateIndex < 10; privateIndex++) privateData[privateIndex + 1]; const privateBig = 123n;', 'javascript'),
    ('unsigned privateCount = 42UL; double privateRatio = 1.5e-2;', 'cpp'),
])
@pytest.mark.parametrize('mask_numbers', [False, True])
def test_number_policy_and_roundtrip(strategy, source, language, mask_numbers):
    from secure_gateway.engine.code_parser import CodeParser
    session = PrivacySession('number-policy', strategy=strategy)
    engine = MaskingEngine()
    numbers = [raw for raw, kind, _ in CodeParser.tokenize(source, language) if kind == TokenType.NUMBER]
    result = engine.mask_code(source, session.session_id, session.generator, session.forward_store,
                              session.reverse_store, language=language, mask_numbers=mask_numbers)
    actual = [raw for raw, kind, _ in CodeParser.tokenize(result.masked_text, language) if kind == TokenType.NUMBER]
    assert (actual == numbers) is (not mask_numbers)
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source


def test_default_preserves_reserved_looking_number_and_detects_old_alias_collision():
    engine = MaskingEngine()
    session = PrivacySession('reserved-number')
    def mask(source, **options):
        return engine.mask_code(source, session.session_id, session.generator,
                                session.forward_store, session.reverse_store, language='python', **options).masked_text
    source = 'value = 732846000000000001'
    result = mask(source)
    assert result.endswith('732846000000000001')
    assert engine.unmask(result, session.session_id, session.reverse_store, strict=True).unmasked_text == source
    alias = mask('42', mask_numbers=True)
    assert engine.unmask(alias, session.session_id, session.reverse_store, strict=True).unmasked_text == '42'
    with pytest.raises(ValueError, match='conflicts'):
        mask(alias)

@pytest.mark.parametrize('mask_numbers', [False, True])
def test_mcp_cli_client_and_gateway_policy(mask_numbers, monkeypatch):
    from secure_gateway.engine import strategies
    # A masked alias may end in the original digits; compare complete tokens.
    monkeypatch.setattr(strategies.secrets, "randbelow", lambda _: 42)
    import json
    from click.testing import CliRunner
    from secure_gateway.cli import main
    from secure_gateway.client import LocalPrivacyClient
    from secure_gateway.gateway import GatewaySession
    from secure_gateway.models import MaskMode
    from secure_gateway.server import mask_code, mask_text, vault

    source = 'privateLimit = 42'
    for function, options in [(mask_code, {'language': 'python'}),
                              (mask_text, {'mode': 'code_aware', 'code_language': 'python'})]:
        result = json.loads(function(source, strategy='bracket', mask_numbers=mask_numbers, **options))
        try:
            assert (result['masked_text'].rsplit('=', 1)[-1].strip() == '42') is (not mask_numbers)
        finally:
            vault.clear_session(result['session_id'])
    args = ['mask', source, '--mode', 'code_aware', '--code-language', 'python', '--json-output']
    if mask_numbers:
        args.append('--mask-numbers')
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    assert (json.loads(result.output)['masked_text'].rsplit('=', 1)[-1].strip() == '42') is (not mask_numbers)
    seen = []
    with LocalPrivacyClient() as client:
        result = client.request(source, lambda masked: (seen.append(masked) or masked),
                                mode=MaskMode.CODE_AWARE, mask_numbers=mask_numbers)
        assert result.unmasked_text == source
    assert (seen[0].rsplit('=', 1)[-1].strip() == '42') is (not mask_numbers)
    gateway = GatewaySession(mask_numbers=mask_numbers)
    masked = gateway.mask(source, code=True, language='python')
    assert (masked.rsplit('=', 1)[-1].strip() == '42') is (not mask_numbers)
    assert gateway.restore(masked) == source


def test_number_identity_entries_and_legacy_aliases_survive_snapshots(tmp_path):
    from secure_gateway.encrypted_session import save_session, load_session
    engine = MaskingEngine()
    session = PrivacySession('number-snapshot')
    def mask(source, mask_numbers=False):
        return engine.mask_code(source, session.session_id, session.generator,
                                session.forward_store, session.reverse_store,
                                language='python', mask_numbers=mask_numbers).masked_text
    source = 'privateValue = 732846000000000001'
    preserved = mask(source)
    legacy = mask('42', mask_numbers=True)
    path = tmp_path / 'numbers.enc'
    save_session(path, session, 'offline-test-password')
    loaded = load_session(path, 'offline-test-password', session.session_id)
    assert engine.unmask(preserved, loaded.session_id, loaded.reverse_store, strict=True).unmasked_text == source
    assert engine.unmask(legacy, loaded.session_id, loaded.reverse_store, strict=True).unmasked_text == '42'


def test_default_preserves_code_numbers_but_prose_policy_is_unchanged():
    from secure_gateway.models import MaskMode
    engine = MaskingEngine()
    for mode in [MaskMode.CODE_AWARE, MaskMode.CONTENT_WORDS]:
        session = PrivacySession('number-mode')
        result = engine.mask_text('42', session.session_id, session.generator,
                                  session.forward_store, session.reverse_store, mode=mode)
        assert (result.masked_text == '42') is (mode == MaskMode.CODE_AWARE)

@pytest.mark.parametrize('command', ['run', 'api-run'])
@pytest.mark.parametrize('configured', [False, True])
@pytest.mark.parametrize('flag,expected', [(None, None), ('--mask-numbers', True), ('--preserve-numbers', False)])
def test_gateway_cli_config_and_explicit_override(tmp_path, monkeypatch, command, configured, flag, expected):
    from click.testing import CliRunner
    from secure_gateway.cli import main
    from secure_gateway import gateway, gateway_install, xai_install
    captured = []
    settings = {'port': 8765, 'token': 'x' * 32, 'mask_numbers': configured}
    monkeypatch.setattr(gateway_install, 'load_config', lambda _: settings)
    monkeypatch.setattr(xai_install, 'load_api_config', lambda _: settings)
    class Server:
        def __init__(self, *args, **kwargs):
            captured.append(kwargs)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def serve_forever(self):
            pass
    monkeypatch.setattr(gateway, 'PrivacyGateway', Server)
    args = ['gateway', command, '--config', str(tmp_path / 'gateway.json')]
    if flag:
        args.append(flag)
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    assert captured[0]['mask_numbers'] is (configured if expected is None else expected)


def test_gateway_numeric_collision_is_not_retried_as_prose():
    from secure_gateway.gateway import GatewaySession
    session = GatewaySession(mask_numbers=True)
    alias = session.mask('42', code=True)
    session.mask_numbers = False
    with pytest.raises(ValueError, match='conflicts'):
        session.mask(alias, code=True)
