"""CLI forwarding and failure codes; mocked audit results are not evaluation scores."""
from click.testing import CliRunner

from secure_gateway.cli import main
import secure_gateway.evaluation_reliable as reliable


def test_explicit_holdout_ledger_and_reuse_reason_reach_preparation(tmp_path, monkeypatch):
    received = {}
    def prepare(**options):
        received.update(options)
        return {'status': 'incomplete'}
    monkeypatch.setattr(reliable, 'prepare_reliable', prepare)
    result = CliRunner().invoke(main, ['evaluate', 'reliable', 'prepare', '--data-dir', str(tmp_path),
        '--output-dir', str(tmp_path / 'run'), '--holdout-ledger', str(tmp_path / 'ledger.json'),
        '--holdout-reuse-reason', 'Regression diagnosis; no adoption claim.'])
    assert result.exit_code == 0, result.output
    assert received['holdout_ledger'] == tmp_path / 'ledger.json'
    assert received['holdout_reuse_reason'] == 'Regression diagnosis; no adoption claim.'


def test_executed_incomplete_reference_audit_has_nonzero_exit_status(tmp_path, monkeypatch):
    monkeypatch.setattr(reliable, 'audit_references', lambda **options: {'status': 'needs_review'})
    result = CliRunner().invoke(main, ['evaluate', 'reliable', 'audit-references',
        '--data-dir', str(tmp_path), '--output-dir', str(tmp_path / 'audit'), '--execute'])
    assert result.exit_code == 2 and 'needs_review' in result.output
