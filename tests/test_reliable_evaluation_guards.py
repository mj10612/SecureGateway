"""Freeze, audit, ledger, error-accounting and eligibility guards.

Every worker and the native CLI discovery are mocks. These tests prove
bookkeeping and gate logic only; they are not LLM or grading evidence.
"""
import json
import threading

import pytest

from secure_gateway.evaluation import write_json
import secure_gateway.evaluation_reliable as reliable
from test_reliable_evaluation import (  # noqa: F401 - autouse fixture registered by import
    MOCK_CLI, fake_worker, make_audit, make_bundle, mock_capture, mocked_native_cli, prepared_run,
)


def edit_json(path, change):
    value = json.loads(path.read_bytes())
    change(value)
    write_json(path, value)


# --- Reference audit: independent recomputation and tamper detection ---------------------------

def audit_fixture(tmp_path, monkeypatch):
    make_bundle(tmp_path / 'data')
    audit = make_audit(tmp_path / 'data', tmp_path / 'audit', monkeypatch)
    return reliable.load_bundle(tmp_path / 'data'), audit


def verify(bundle, audit):
    return reliable.verify_reference_audit(audit, bundle, split='holdout', model='gpt-6.1-sol', reasoning_effort='medium')


def test_audit_is_recomputed_from_records_and_legacy_freeze_is_reconstructed(tmp_path, monkeypatch):
    bundle, audit = audit_fixture(tmp_path, monkeypatch)
    result = verify(bundle, audit)
    assert result['verified'] and result['recomputed']['passed_criteria'] == 68
    assert result['recomputed']['calls'] == 17 and result['recomputed']['reported_tokens'] == 51
    assert result['cli_versions'] == [MOCK_CLI] and not result['predates_request_and_cli_freeze']
    # An audit frozen before request/CLI pinning is checked by deterministic reconstruction.
    edit_json(audit / 'freeze.json', lambda v: (v.pop('requests_sha256'), v.pop('cli_version'), v.pop('schema_version')))
    legacy = verify(bundle, audit)
    assert legacy['verified'] and legacy['predates_request_and_cli_freeze'] and legacy['requests_reconstructed']


def _flip_first_grade(rows):
    rows[0]['grades'][0]['passed'] = False


@pytest.mark.parametrize('name,change,message', [
    ('requests.json', lambda rows: rows[0]['request']['criteria'][0].update(description='edited'), 'requests'),
    ('first-grades.json', _flip_first_grade, 'disagrees'),
    ('first-grades.json', lambda rows: rows[0]['metadata'].update(cli_version='codex-cli other'), 'provenance'),
    ('first-grades.json', lambda rows: rows[0]['metadata'].update(requested_reasoning_effort='high'), 'provenance'),
    ('first-grades.json', lambda rows: rows.append(dict(rows[0])), 'duplicate'),
    ('report.json', lambda v: v.update(passed_criteria=67), 'disagrees'),
    ('journal.json', lambda v: v['calls'][0]['usage'].update(total_tokens=1), 'journal'),
    ('journal.json', lambda v: v['calls'].pop(), 'journal'),
])
def test_audit_tampering_is_rejected(tmp_path, monkeypatch, name, change, message):
    bundle, audit = audit_fixture(tmp_path, monkeypatch)
    edit_json(audit / name, change)
    with pytest.raises(ValueError, match=message):
        verify(bundle, audit)


def test_legacy_audit_with_edited_requests_fails_reconstruction(tmp_path, monkeypatch):
    bundle, audit = audit_fixture(tmp_path, monkeypatch)
    edit_json(audit / 'freeze.json', lambda v: v.pop('requests_sha256'))
    edit_json(audit / 'requests.json', lambda rows: rows[1]['request'].update(max_output_tokens=4096))
    with pytest.raises(ValueError, match='reconstruction'):
        verify(bundle, audit)


def test_unattained_or_other_cli_audit_blocks_preparation(tmp_path, monkeypatch):
    make_bundle(tmp_path / 'data')
    mock_capture(monkeypatch)
    monkeypatch.setattr(reliable, 'run_codex_worker', lambda request: fake_worker(
        request, failing={(request['job_id'], 'scope')} if request['job_id'] == request['job_id'] else set()))
    assert reliable.audit_references(tmp_path / 'data', tmp_path / 'audit', execute=True)['status'] == 'needs_review'
    with pytest.raises(ValueError, match='attainable'):
        reliable.prepare_reliable(tmp_path / 'data', tmp_path / 'run', reference_audit_dir=tmp_path / 'audit')
    good = make_audit(tmp_path / 'data', tmp_path / 'audit-ok', monkeypatch)
    monkeypatch.setattr(reliable, 'native_cli_version', lambda: 'codex-cli newer')
    with pytest.raises(ValueError, match='different native CLI'):
        reliable.prepare_reliable(tmp_path / 'data', tmp_path / 'run2', reference_audit_dir=good)


# --- Mandatory complete freeze ------------------------------------------------------------------

def _corrupt_corpus(output):
    path = output / 'corpora/tasks-holdout.json'
    path.write_bytes(path.read_bytes() + b'\n')


@pytest.mark.parametrize('mutate,problem', [
    (lambda o, m: edit_json(o / 'freeze.json', lambda v: v.pop('jobs_sha256')), 'missing freeze key: jobs_sha256'),
    (lambda o, m: edit_json(o / 'freeze.json', lambda v: v.pop('corpus_byte_hashes')), 'missing freeze key'),
    (lambda o, m: edit_json(o / 'freeze.json', lambda v: v.update(prepared=False)), 'not a completed preparation'),
    (lambda o, m: _corrupt_corpus(o), 'corpus bytes changed'),
    (lambda o, m: edit_json(o / 'comprehension/manifest.json',
                            lambda v: v['jobs'][0]['request']['messages'][1].update(content='edited')), 'jobs changed'),
    (lambda o, m: edit_json(o / 'reference-audit-evidence/report.json', lambda v: v.update(passed_criteria=0)), 'reference_audit_evidence'),
    (lambda o, m: m.setattr(reliable, 'native_cli_version', lambda: 'codex-cli other'), 'native CLI version changed'),
    (lambda o, m: m.setattr(reliable, 'adapter_hash', lambda: '0' * 64), 'adapter changed'),
    (lambda o, m: m.setattr(reliable, 'grading_policy_hash', lambda: '0' * 64), 'grading policy changed'),
])
def test_execution_requires_an_intact_complete_freeze(tmp_path, monkeypatch, mutate, problem):
    output = prepared_run(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(reliable, 'run_codex_worker', lambda request: calls.append(request) or fake_worker(request))
    mutate(output, monkeypatch)
    with pytest.raises(ValueError, match=problem):
        reliable.execute_reliable(output, execute=True, workers=1)
    assert calls == [] and not (output / 'execution-journal.json').exists()


def test_tampered_run_reports_incomplete(tmp_path, monkeypatch):
    output = prepared_run(tmp_path, monkeypatch)
    _corrupt_corpus(output)
    result = reliable.joint_report(output)
    assert result['status'] == 'incomplete' and 'frozen corpus bytes changed' in result['freeze_problems']


def test_execution_requires_a_verified_reference_audit(tmp_path, monkeypatch):
    make_bundle(tmp_path / 'data')
    mock_capture(monkeypatch)
    reliable.prepare_reliable(tmp_path / 'data', tmp_path / 'run')
    with pytest.raises(ValueError, match='reference-response audit'):
        reliable.execute_reliable(tmp_path / 'run', execute=True, workers=1)


# --- Baseline evidence, four arms and the holdout ledger ----------------------------------------

def test_candidate_freezes_baseline_evidence_runs_four_arms_and_records_first_use(tmp_path, monkeypatch):
    base = prepared_run(tmp_path, monkeypatch, name='base')
    candidate = prepared_run(tmp_path, monkeypatch, name='candidate', baseline_dir=base)
    state = json.loads((candidate / 'comprehension/manifest.json').read_bytes())
    frozen = json.loads((candidate / 'freeze.json').read_bytes())
    assert len(state['jobs']) == 204 and set(state['metadata']['variants']) == {'original', 'human', 'baseline', 'candidate'}
    assert set(frozen['baseline_evidence']) == set(reliable.BASELINE_FILES)
    ledger = reliable.read_holdout_ledger(reliable.holdout_ledger_path(tmp_path / 'data'))
    assert [e['kind'] for e in ledger] == ['baseline', 'candidate']
    assert frozen['holdout_use']['first_candidate'] is True
    assert frozen['holdout_use']['baseline_freeze_sha256'] == frozen['baseline_evidence']['freeze.json']
    assert reliable._holdout_use_status(frozen) == (True, 'First recorded candidate use.')
    # The candidate's own baseline-evidence copy is pinned.
    edit_json(candidate / 'baseline-evidence/task-capture/report.json', lambda v: v.update(run_id='edited'))
    assert 'baseline_evidence changed: task-capture/report.json' in reliable._verify_freeze(candidate, frozen)


def test_holdout_reuse_must_be_explicit_and_is_never_first_use(tmp_path, monkeypatch):
    base = prepared_run(tmp_path, monkeypatch, name='base')
    prepared_run(tmp_path, monkeypatch, name='first', baseline_dir=base)
    with pytest.raises(ValueError, match='reuse reason'):
        prepared_run(tmp_path, monkeypatch, name='second', baseline_dir=base)
    reused = prepared_run(tmp_path, monkeypatch, name='third', baseline_dir=base,
                          holdout_reuse_reason='Regression check after holdout inspection.')
    frozen = json.loads((reused / 'freeze.json').read_bytes())
    assert frozen['holdout_use']['first_candidate'] is False and frozen['holdout_use']['prior_candidate_uses'] == 1
    report = reliable.joint_report(reused)
    assert report['adoption']['holdout_first_candidate_use'] is False
    # Baseline preparations remain allowed and recorded.
    prepared_run(tmp_path, monkeypatch, name='base-again')
    kinds = [e['kind'] for e in reliable.read_holdout_ledger(reliable.holdout_ledger_path(tmp_path / 'data'))]
    assert kinds == ['baseline', 'candidate', 'candidate', 'baseline']


def test_ledger_is_append_only_evidence(tmp_path, monkeypatch):
    prepared_run(tmp_path, monkeypatch, name='base')
    path = reliable.holdout_ledger_path(tmp_path / 'data')
    edit_json(path, lambda rows: rows[0].update(kind='candidate'))
    with pytest.raises(ValueError, match='chain'):
        reliable.read_holdout_ledger(path)


def test_baseline_configuration_must_match_and_development_has_no_ledger(tmp_path, monkeypatch):
    base = prepared_run(tmp_path, monkeypatch, name='base')
    with pytest.raises(ValueError, match='differs: repeats'):
        prepared_run(tmp_path, monkeypatch, name='candidate', baseline_dir=base, repeats=4)
    make_audit(tmp_path / 'data', tmp_path / 'dev-audit', monkeypatch, split='development')
    dev = prepared_run(tmp_path, monkeypatch, name='dev', audit=tmp_path / 'dev-audit', split='development')
    frozen = json.loads((dev / 'freeze.json').read_bytes())
    assert frozen['holdout_use'] is None
    assert reliable.joint_report(dev)['adoption']['review_eligible'] is False


# --- Concurrency and error accounting -----------------------------------------------------------

def test_concurrent_errors_preserve_rejected_records_and_stop(tmp_path, monkeypatch):
    output = prepared_run(tmp_path, monkeypatch)
    jobs = json.loads((output / 'comprehension/manifest.json').read_bytes())['jobs']
    crash, wrong_cli = jobs[1]['job_id'], jobs[2]['job_id']
    lock, started = threading.Lock(), []
    def worker(request):
        with lock:
            started.append(request['role'])
        if request['job_id'] == crash:
            raise RuntimeError('mock transport failure')
        result = fake_worker(request)
        if request['job_id'] == wrong_cli:
            result['metadata']['cli_version'] = 'codex-cli other'
        return result
    monkeypatch.setattr(reliable, 'run_codex_worker', worker)
    result = reliable.execute_reliable(output, execute=True, workers=3)
    journal = json.loads((output / 'execution-journal.json').read_bytes())
    assert started == ['interpret'] * 3 and journal['stopped']
    assert sorted(c['status'] for c in journal['calls']) == ['completed', 'error', 'error']
    assert journal['batches'] == [{'phase': 'interpret', 'in_flight': 3, 'reported_tokens_before': 0}]
    rejected = json.loads((output / 'comprehension/rejected-records.json').read_bytes())
    assert [r['job_id'] for r in rejected] == [wrong_cli] and rejected[0]['record']['response']
    assert result['status'] == 'incomplete' and result['execution']['rejected_records'] == 1
    assert result['execution']['by_status'] == {'completed': 1, 'error': 2}
    # Stopped runs never retry; a missing journal with saved records fails closed.
    assert reliable.execute_reliable(output, execute=True, workers=3)['status'] == 'incomplete'
    assert len(started) == 3
    (output / 'execution-journal.json').unlink()
    with pytest.raises(ValueError, match='journal is missing'):
        reliable.execute_reliable(output, execute=True, workers=3)


def test_budget_boundary_stops_before_next_batch(tmp_path, monkeypatch):
    output = prepared_run(tmp_path, monkeypatch)
    monkeypatch.setattr(reliable, 'run_codex_worker', fake_worker)
    result = reliable.execute_reliable(output, execute=True, workers=3, max_calls=7)
    journal = json.loads((output / 'execution-journal.json').read_bytes())
    assert [b['in_flight'] for b in journal['batches']] == [3, 3, 1]
    assert journal['stop_reason'] == 'Budget exhausted before the next batch.'
    assert result['status'] == 'incomplete' and result['execution']['calls'] == 7
    assert 'in flight' in result['execution']['note']


# --- Review eligibility gates -------------------------------------------------------------------

def run_candidate(tmp_path, monkeypatch, failing_by_variant):
    base = prepared_run(tmp_path, monkeypatch, name='base')
    candidate = prepared_run(tmp_path, monkeypatch, name='candidate', baseline_dir=base)
    jobs = json.loads((candidate / 'comprehension/manifest.json').read_bytes())['jobs']
    failing = {(j['job_id'], criterion) for j in jobs for criterion in failing_by_variant.get(j['variant'], ())}
    monkeypatch.setattr(reliable, 'run_codex_worker', lambda request: fake_worker(request, failing))
    return reliable.execute_reliable(candidate, execute=True, workers=3, max_calls=408)


def test_first_candidate_with_holdout_gain_is_review_eligible_but_not_adopted(tmp_path, monkeypatch):
    result = run_candidate(tmp_path, monkeypatch, {'baseline': ('scope',)})
    adoption = result['adoption']
    assert result['status'] == 'completed' and adoption['observed_task_gain']
    assert adoption['review_eligible'] is True and adoption['decision'] is None
    assert adoption['blocking_criterion_regressions'] == []
    assert adoption['criterion_regressions']['scope']['improved'] == 51


def test_conditions_or_prohibition_regression_blocks_review(tmp_path, monkeypatch):
    result = run_candidate(tmp_path, monkeypatch, {'baseline': ('scope', 'intent'), 'candidate': ('prohibition',)})
    adoption = result['adoption']
    assert adoption['observed_task_gain'] is True  # 102 baseline failures vs 51 candidate failures.
    assert adoption['criterion_regressions']['prohibition']['net_regressed'] == 51
    assert adoption['blocking_criterion_regressions'] == ['prohibition']
    assert adoption['review_eligible'] is False
