"""Public-path regressions for catalog framing, dry-run and hook literals."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from click.testing import CliRunner
import pytest

from secure_gateway.cli import main
from secure_gateway.gateway import PrivacyGateway
from secure_gateway.gateway import GatewaySession
from secure_gateway.gateway_audit import AuditStore
from secure_gateway.gateway_catalog import fetch_catalog
from secure_gateway.hooks import handle_hook


def test_catalog_rejects_short_content_length_over_loopback():
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            body = b'{"data":[{"id":"grok-fixture"}]}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body) + 10))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

    with ThreadingHTTPServer(('127.0.0.1', 0), Fixture) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with pytest.raises(ValueError, match='Incomplete'):
                fetch_catalog(f'http://127.0.0.1:{server.server_port}', 'Bearer xai-fixture')
        finally:
            server.shutdown()
            thread.join(timeout=5)


def test_audit_gc_default_does_not_create_state(tmp_path):
    config = tmp_path / 'custom.json'
    config.write_text(json.dumps({'port': 38117, 'token': 't' * 32}), encoding='utf-8')
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = CliRunner().invoke(main, ['gateway', 'audit-gc', '--config', str(config)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)['dry_run'] is True
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert after == before
    assert not config.with_name('custom.json.state').exists()


def test_gateway_recovers_terminated_audit_owner_and_preserves_live_owner(tmp_path):
    path = tmp_path / 'audit.db'
    stopped = AuditStore(path)
    stopped.begin('fixture', 'fixture', 'fixture', '/fixture', 'local')
    stopped.close()
    live = AuditStore(path)
    live.begin('fixture', 'fixture', 'fixture', '/fixture', 'local')
    try:
        with PrivacyGateway(('127.0.0.1', 0), 'synthetic-token', audit_path=path) as gateway:
            assert gateway.audit.query({'result': 'interrupted'})['summary']['total'] == 1
            assert gateway.audit.query({'result': 'incomplete'})['summary']['total'] == 1
    finally:
        live.close()


@pytest.mark.parametrize('source', ['⟦ENT_999⟧', '⟦ENT-999⟧', 'smcp_ID_999', '732846123456789012'])
def test_hook_unknown_alias_lookalike_survives_snapshot_and_local_restore(tmp_path, source):
    (tmp_path / 'key').write_text('synthetic-password', encoding='ascii')
    masked = handle_hook({'hook_event_name': 'PostToolUse', 'session_id': 'synthetic',
                          'tool_response': source}, tmp_path)['hookSpecificOutput']['updatedToolOutput']
    assert masked != source
    result = handle_hook({'hook_event_name': 'MessageDisplay', 'session_id': 'synthetic',
                          'delta': masked}, tmp_path)
    assert result['hookSpecificOutput']['displayContent'] == source
    echoed = handle_hook({'hook_event_name': 'PostToolUse', 'session_id': 'synthetic',
                          'tool_response': masked}, tmp_path)['hookSpecificOutput']['updatedToolOutput']
    assert echoed == masked


@pytest.mark.parametrize('language,source', [
    ('javascript', r'const privateText = "secret \"quoted\"";'),
    ('python', r'privateText = "secret \"quoted\""'),
    ('sql', 'SELECT "private""Column" FROM "privateTable";'),
])
def test_gateway_restores_literal_escapes_and_quoted_names_separately(tmp_path, language, source):
    from secure_gateway.encrypted_session import load_session, save_session

    gateway = GatewaySession()
    masked = gateway.mask(source, code=True, language=language)
    assert gateway.restore(masked) == source
    path = tmp_path / 'session.enc'
    save_session(path, gateway.session, 'synthetic-password')
    restored = GatewaySession(load_session(path, 'synthetic-password', gateway.session.session_id))
    assert restored.restore(masked) == source
