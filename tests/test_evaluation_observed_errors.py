"""Prospective native-error accounting; all workers are mocks."""
import json

import pytest

from secure_gateway.evaluation_diagnostics import ObservedWorkerFailure
import secure_gateway.evaluation_reliable as reliable
from test_reliable_evaluation import mocked_native_cli, prepared_run  # noqa: F401


@pytest.mark.parametrize('usage', [None, {'input_tokens': 10, 'output_tokens': 3, 'total_tokens': 13}])
def test_primary_run_preserves_safe_failure_reason_and_available_usage(tmp_path, monkeypatch, usage):
    output = prepared_run(tmp_path, monkeypatch)
    def fail(request):
        raise ObservedWorkerFailure({'stage': 'events', 'code': 'provider_failed',
                                     'job_id': request['job_id']}, usage=usage)
    monkeypatch.setattr(reliable, 'run_codex_worker', fail)
    result = reliable.execute_reliable(output, execute=True, workers=1)
    journal = json.loads((output / 'execution-journal.json').read_bytes())
    assert result['status'] == 'incomplete' and journal['stopped']
    assert len(journal['calls']) == 1
    call = journal['calls'][0]
    assert call['error'] == 'provider_failed' and call['diagnostics']['stage'] == 'events'
    assert result['execution']['reported_tokens'] == (13 if usage else 0)
    assert result['execution']['unknown_usage_calls'] == (0 if usage else 1)
