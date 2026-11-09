"""Observer unit tests do not invoke a model or change the native adapter."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from secure_gateway import evaluation_diagnostics as observer


def test_success_calls_original_adapter_with_identical_request_and_result(monkeypatch):
    request = {'job_id': 'mock', 'messages': [{'role': 'user', 'content': 'synthetic'}]}
    before = deepcopy(request)
    result = {'job_id': 'mock', 'grades': [], 'metadata': {'cli_version': 'unit'}}
    source = Path(observer.native.__file__)
    original_hash = sha256(source.read_bytes()).hexdigest()
    def worker(actual):
        assert actual is request
        return result
    monkeypatch.setattr(observer.native, 'run_codex_worker', worker)
    assert observer.diagnostic_worker(request) is result
    assert request == before
    assert sha256(source.read_bytes()).hexdigest() == original_hash


def test_failure_preserves_known_usage_and_content_free_first_message_proof(monkeypatch):
    def worker(request):
        usage = {'input_tokens': 10, 'output_tokens': 3, 'total_tokens': 13}
        final = 'SYNTHETIC_REJECTED_FIRST_GRADE'
        assert usage and final
        raise ValueError('Worker returned invalid grades.')
    monkeypatch.setattr(observer.native, 'run_codex_worker', worker)
    with pytest.raises(observer.ObservedWorkerFailure) as caught:
        observer.diagnostic_worker({'job_id': 'mock'})
    error = caught.value
    assert error.usage['total_tokens'] == 13
    assert error.diagnostics['stage'] == 'result_validation'
    assert error.diagnostics['final_message_sha256'] == sha256(b'SYNTHETIC_REJECTED_FIRST_GRADE').hexdigest()
    assert 'SYNTHETIC_REJECTED_FIRST_GRADE' not in str(error.diagnostics)


def test_unknown_error_text_is_never_echoed_and_usage_remains_unknown(monkeypatch):
    def worker(request):
        raise ValueError('SYNTHETIC_SECRET_IN_ARBITRARY_ERROR')
    monkeypatch.setattr(observer.native, 'run_codex_worker', worker)
    with pytest.raises(observer.ObservedWorkerFailure) as caught:
        observer.diagnostic_worker({'job_id': 'mock'})
    assert caught.value.usage is None
    assert caught.value.diagnostics['code'] == 'unclassified_failure'
    assert 'SYNTHETIC_SECRET' not in str(caught.value.diagnostics) + str(caught.value)
