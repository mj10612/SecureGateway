"""Reliability gates use synthetic mock workers; these are not LLM scores.

Native CLI discovery and every model call are mocked: these tests prove
bookkeeping, freezing and gating only, never model comprehension.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from secure_gateway.cli import main
from secure_gateway.evaluation import digest, write_json
from secure_gateway.evaluation_comprehension import _grade_request
import secure_gateway.evaluation_reliable as reliable

MOCK_CLI = 'codex-cli unit-mock'


@pytest.fixture(autouse=True)
def mocked_native_cli(monkeypatch):
    """CI has no native Codex; discovery is mocked and never runs inference."""
    monkeypatch.setattr(reliable, 'native_cli_version', lambda: MOCK_CLI)


def case(language='en', split='holdout', kind='tasks', number=0):
    text = 'Review SyntheticPrivateQzx. Ask before deleting.'
    if kind == 'privacy':
        text += ' SyntheticPrivateQzx' * 4
    start = text.index('SyntheticPrivateQzx')
    span = {'path': ['input', 0, 'content'], 'start': start, 'end': start + 19,
            'label': 'project', 'fragments': [], 'policy': 'contextual', 'severity': 'high'}
    return {'id': f'{split}-{kind}-{language}-{number}', 'language': language, 'domain': 'general',
            'dialect': 'codex', 'split': split, 'template_group': f'{split}-{kind}-{language}-{number}',
            'family': f'{split}-{kind}-{number}', 'smoke': False,
            'language_mode': 'explicit' if number % 2 else 'auto',
            'payload': {'model': 'fixture', 'input': [{'role': 'user', 'content': text}]},
            'echo_path': ['input', 0, 'content'], 'task_path': ['input', 0, 'content'],
            'secrets': [span] if kind == 'tasks' else [
                {**span, 'start': pos, 'end': pos + 19}
                for pos in range(len(text)) if text.startswith('SyntheticPrivateQzx', pos)],
            'public': [{'path': ['input', 0, 'content'], 'start': 0, 'end': 6, 'label': 'action'}],
            'forced_terms': [], 'human_text': 'Review private_symbol_1. Ask before deleting.',
            'rubric': [{'id': key, 'description': key} for key in ['intent', 'conditions', 'prohibition', 'scope']] if kind == 'tasks' else [],
            'reference_response': 'OWNER_REFERENCE_NEVER_INTERPRETER',
            'rubric_notes': 'Missing facts allow a targeted clarification and conditional plan.'}


def corpus(cases):
    return {'schema_version': 1, 'synthetic': True, 'corpus_version': 'unit-only-1', 'cases': cases}


def report(data):
    """Mock HTTP capture report: integrity fully passing, no exposures."""
    n = len(data['cases'])
    return {'schema_version': 1, 'suite': 'privacy', 'status': 'completed', 'run_id': 'mock',
            'metadata': {'corpus_hash': digest(data), 'settings_hash': 'unit-settings', 'code_sha': 'unit',
                         'scoring_version': 2, 'profile': 'release'},
            'cases': [{**{k: c[k] for k in ['id', 'language', 'domain', 'dialect', 'split', 'template_group']},
                       'status': 'completed', 'outbound': deepcopy(c['payload']), 'secrets': [],
                       'roundtrip': True, 'semantic_roundtrip': True, 'replay': True,
                       'grading_alias_bindings': {'private_symbol_1': 'SyntheticPrivateQzx'}} for c in data['cases']],
            'metrics': {'privacy': {}, 'integrity': {'semantic_roundtrip_passed': n, 'replay_passed': n,
                                                     'session_isolation': True, 'snapshot_restart': True}},
            'breakdown': {}}


def mock_capture(monkeypatch):
    monkeypatch.setattr(reliable, 'run_privacy', lambda data, *, output_dir, **kw: (
        write_json(Path(output_dir) / 'report.json', report(data)) or report(data)))


def make_bundle(root):
    for split in reliable.SPLITS:
        for kind in ['tasks', 'privacy']:
            rows = [case(language, split, kind, n) for language in sorted(reliable.LANGUAGES)
                    for n in range(1 if kind == 'tasks' else 6)]
            write_json(root / f'{kind}-{split}.json', corpus(rows))


def worker_metadata(request):
    return {'requested_model': request['model'], 'requested_reasoning_effort': request.get('reasoning_effort'),
            'adapter_source_sha256': reliable.adapter_hash(), 'cli_version': MOCK_CLI, 'tool_events': 0,
            'task_response_mode': 'answer_visible_task' if request['role'] == 'interpret' else 'independent_grade'}


def fake_worker(request, failing=frozenset()):
    """Mock worker; ``failing`` holds (job_id, criterion) pairs graded False."""
    result = {'job_id': request['job_id'], 'model': request['model'], 'usage': {'total_tokens': 3, 'output_tokens': 1},
              'metadata': worker_metadata(request)}
    if request['role'] == 'interpret':
        result['response'] = 'Unit mock answer, not a model evaluation.'
    else:
        result['grades'] = [{'id': c['id'], 'passed': (request['job_id'], c['id']) not in failing,
                             'evidence': 'Mock accounting only.'} for c in request['criteria']]
    return result


def make_audit(source, root, monkeypatch, split='holdout'):
    monkeypatch.setattr(reliable, 'run_codex_worker', fake_worker)
    result = reliable.audit_references(source, root, execute=True, split=split)
    assert result['status'] == 'passed'
    return root


def prepared_run(tmp_path, monkeypatch, *, name='run', baseline_dir=None, audit=None, **options):
    source = tmp_path / 'data'
    if not source.exists():
        make_bundle(source)
    mock_capture(monkeypatch)
    if audit is None:
        audit = tmp_path / 'audit'
        if not audit.exists():
            make_audit(source, audit, monkeypatch)
    output = tmp_path / name
    reliable.prepare_reliable(source, output, baseline_dir=baseline_dir, reference_audit_dir=audit, **options)
    return output


def test_bundle_validates_all_languages_counts_and_cross_split_families(tmp_path):
    make_bundle(tmp_path)
    result = reliable.load_bundle(tmp_path)
    assert result['summaries']['tasks-holdout.json']['max_task_points_per_repeat'] == 68
    assert result['summaries']['privacy-holdout.json']['private_occurrences'] == 510
    path = tmp_path / 'tasks-holdout.json'
    value = json.loads(path.read_bytes())
    value['cases'][0]['family'] = 'development-tasks-0'
    write_json(path, value)
    with pytest.raises(ValueError, match='crosses'):
        reliable.load_bundle(tmp_path)


def test_preparation_freezes_153_blind_jobs_without_gold_or_reference(tmp_path, monkeypatch):
    output = prepared_run(tmp_path, monkeypatch)
    state = json.loads((output / 'comprehension/manifest.json').read_bytes())
    frozen = json.loads((output / 'freeze.json').read_bytes())
    assert len(state['jobs']) == 153
    assert frozen['prepared'] is True and frozen['cli_version'] == MOCK_CLI
    assert reliable._verify_freeze(output, frozen) == []
    result = json.loads((output / 'report.json').read_bytes())
    assert set(result['repeated_statistics']['holdout_eligibility']['variants']) == {'original', 'human', 'baseline'}
    for job in state['jobs']:
        request = job['request']
        assert set(request) == {'role', 'job_id', 'model', 'max_output_tokens', 'messages', 'reasoning_effort'}
        assert 'OWNER_REFERENCE_NEVER_INTERPRETER' not in json.dumps(request)
        assert request['reasoning_effort'] == 'medium'
        grade = _grade_request(job, {'response': 'A saved first answer'})
        # Reference answers are audited separately, never shown to graders.
        assert 'OWNER_REFERENCE_NEVER_INTERPRETER' not in json.dumps(grade)
        assert 'Deferring only that decision' in grade['messages'][0]['content']
    with pytest.raises(ValueError, match='empty'):
        reliable.prepare_reliable(tmp_path / 'data', output, reference_audit_dir=tmp_path / 'audit')


def test_actual_runner_phase_order_and_immutable_budget_accounting(tmp_path, monkeypatch):
    output = prepared_run(tmp_path, monkeypatch)
    roles = []
    def worker(request):
        roles.append(request['role'])
        return fake_worker(request)
    monkeypatch.setattr(reliable, 'run_codex_worker', worker)
    result = reliable.execute_reliable(output, execute=True, max_calls=306, max_tokens=10_000, workers=1)
    assert result['status'] == 'completed'
    assert roles == ['interpret'] * 153 + ['grade'] * 153
    journal = json.loads((output / 'execution-journal.json').read_bytes())
    assert len(journal['calls']) == 306 and all(c['status'] == 'completed' for c in journal['calls'])
    assert result['execution']['reported_tokens'] == 918 and result['execution']['max_in_flight'] == 1
    assert result['adoption']['review_eligible'] is False  # Baseline-only; no candidate, no adoption.
    with pytest.raises(ValueError, match='immutable'):
        reliable.execute_reliable(output, execute=True, max_calls=307, max_tokens=10_000, workers=1)


def test_interrupted_reserved_attempt_cannot_be_retried(tmp_path, monkeypatch):
    output = prepared_run(tmp_path, monkeypatch)
    monkeypatch.setattr(reliable, 'run_codex_worker', fake_worker)
    write_json(output / 'execution-journal.json', {'budget': {'max_calls': 306, 'max_seconds': 7200,
               'max_reported_tokens': 1000, 'workers': 1}, 'calls': [{'job_id': 'interrupted', 'phase': 'interpret', 'status': 'running'}],
               'stopped': False, 'elapsed_seconds': 0, 'deadline_unix': 1e12})
    result = reliable.execute_reliable(output, execute=True, max_calls=306, max_tokens=1000, workers=1)
    assert result['status'] == 'incomplete'
    journal = json.loads((output / 'execution-journal.json').read_bytes())
    assert journal['stopped'] and len(journal['calls']) == 1


def test_unknown_usage_stops_without_starting_graders(tmp_path, monkeypatch):
    output = prepared_run(tmp_path, monkeypatch)
    def missing_usage(request):
        result = fake_worker(request)
        del result['usage']
        return result
    monkeypatch.setattr(reliable, 'run_codex_worker', missing_usage)
    result = reliable.execute_reliable(output, execute=True, max_calls=306, workers=1)
    journal = json.loads((output / 'execution-journal.json').read_bytes())
    assert journal['stopped'] and len(journal['calls']) == 1
    assert journal['calls'][0]['phase'] == 'interpret'
    assert result['execution']['unknown_usage_calls'] == 1


def test_cli_requires_explicit_execute_before_any_model_call(tmp_path, monkeypatch):
    output = prepared_run(tmp_path, monkeypatch)
    monkeypatch.setattr(reliable, 'run_codex_worker', fake_worker)
    result = CliRunner().invoke(main, ['evaluate', 'reliable', 'run', '--output-dir', str(output)])
    assert result.exit_code != 0 and 'Explicit execution' in result.output
    assert not (output / 'execution-journal.json').exists()


def test_explicit_language_and_ambiguous_exposure_are_measured_separately(tmp_path):
    from secure_gateway.evaluation import _privacy_metrics, run_privacy
    data = corpus([case(language='ar')])
    data['cases'][0]['language_mode'] = 'explicit'
    data['cases'][0]['forced_terms'] = ['SyntheticPrivateQzx']
    data['cases'][0]['secrets'][0]['policy'] = 'explicit'
    result = run_privacy(data, output_dir=tmp_path, profile='release')
    assert result['status'] == 'completed'
    assert result['metadata']['languages_measured'] == ['ar']
    assert result['metadata']['settings']['case_language_modes'][data['cases'][0]['id']] == 'explicit'
    assert result['breakdown']['policy']['explicit']['total_sensitive'] == 1
    measured = {'status': 'completed', 'sensitive_count': 1, 'secrets': [{'full_exposure': False,
                'partial_exposure': False, 'alignment_ambiguous': True}], 'public': [],
                'roundtrip': True, 'semantic_roundtrip': True, 'replay': True}
    assert _privacy_metrics([measured])['privacy']['fully_protected'] == 0


def test_duplicate_annotations_cannot_inflate_privacy_denominators():
    from secure_gateway.evaluation import validate_corpus
    data = corpus([case()])
    data['cases'][0]['secrets'] *= 2
    with pytest.raises(ValueError, match='Duplicate source span'):
        validate_corpus(data)


def test_provider_capture_survives_response_restore_failure_without_roundtrip_credit(tmp_path, monkeypatch):
    from secure_gateway.evaluation import run_privacy
    from secure_gateway.gateway import GatewaySession
    def fail_restore(*args, **kwargs):
        raise ValueError('Synthetic restore failure')
    monkeypatch.setattr(GatewaySession, 'response', fail_restore)
    data = corpus([case()])
    data['cases'][0]['forced_terms'] = ['SyntheticPrivateQzx']
    data['cases'][0]['secrets'][0]['policy'] = 'explicit'
    result = run_privacy(data, output_dir=tmp_path, profile='release')
    assert result['status'] == 'completed'  # Measurement completed, integrity did not pass.
    assert result['metrics']['privacy']['fully_protected'] == 1
    assert result['metrics']['integrity']['response_failures'] == 1
    assert result['metrics']['integrity']['roundtrip_passed'] == 0
    assert result['metrics']['integrity']['replay_passed'] == 0
    assert result['cases'][0]['response_status'] == 502
    assert result['cases'][0]['payload_replay'] is True
