"""Grade-only supplement of a stopped run. Mocks only: no native CLI, no model calls.

These tests prove scheduling, freezing, accounting and reporting rules; they are
not LLM or grading evidence.
"""
from hashlib import sha256
import json
import shutil

import pytest
from click.testing import CliRunner

from secure_gateway.cli import main
from secure_gateway import evaluation_diagnostics
import secure_gateway.evaluation_reliable as reliable
import secure_gateway.evaluation_supplemental as supplemental
from secure_gateway.evaluation import write_json
from test_reliable_evaluation import (  # noqa: F401 - autouse fixture registered by import
    MOCK_CLI, fake_worker, make_audit, make_bundle, mock_capture, mocked_native_cli,
)


def tree(root):
    return {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}


@pytest.fixture(scope='module')
def stopped_parent_template(tmp_path_factory):
    """A mock parent: 153 first answers, 29 first grades, the 30th grade raised with unknown usage."""
    root = tmp_path_factory.mktemp('parent')
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(reliable, 'native_cli_version', lambda: MOCK_CLI)
        make_bundle(root / 'data')
        mock_capture(patch)
        make_audit(root / 'data', root / 'audit', patch)
        reliable.prepare_reliable(root / 'data', root / 'run', reference_audit_dir=root / 'audit')
        grades = []
        def worker(request):
            if request['role'] == 'grade':
                grades.append(request['job_id'])
                if len(grades) == 30:
                    raise ValueError('Codex inference failed.')
            return fake_worker(request)
        patch.setattr(reliable, 'run_codex_worker', worker)
        result = reliable.execute_reliable(root / 'run', execute=True, workers=1, max_calls=306)
    assert result['status'] == 'incomplete'
    return root / 'run', grades[29]


@pytest.fixture
def parent(stopped_parent_template, tmp_path):
    template, failed = stopped_parent_template
    copy = tmp_path / 'parent'
    shutil.copytree(template, copy)
    return copy, failed


def grader(monkeypatch, failing=frozenset(), roles=None, behaviour=None):
    """Mock the unchanged native adapter behind the real diagnostic observer."""
    def worker(request):
        if roles is not None:
            roles.append(request['role'])
        if behaviour is not None:
            outcome = behaviour(request)
            if outcome is not None:
                return outcome
        return fake_worker(request, failing)
    monkeypatch.setattr(evaluation_diagnostics.native, 'run_codex_worker', worker)


def manifest(path):
    return json.loads((path / 'comprehension/manifest.json').read_bytes())


def test_default_schedule_never_retries_the_failed_grade_and_keeps_parent_bytes(parent, tmp_path, monkeypatch):
    run, failed = parent
    before = tree(run)
    frozen = supplemental.prepare_supplemental(run, tmp_path / 'supp')
    assert len(frozen['scheduled']) == 123 and {s['kind'] for s in frozen['scheduled']} == {'missing'}
    assert failed not in {s['job_id'] for s in frozen['scheduled']}
    assert frozen['parent_failed_calls'] == [{'journal_index': 182, 'job_id': failed, 'phase': 'grade', 'status': 'error',
                                              'error': 'ValueError', 'usage_unknown': True}]
    assert frozen['first_answers'] == 153 and frozen['first_grades'] == 29 and frozen['parent_unknown_usage_calls'] == 1
    roles = []
    grader(monkeypatch, roles=roles)
    report = supplemental.execute_supplemental(tmp_path / 'supp', execute=True, workers=3)
    assert roles == ['grade'] * 123  # Never an interpretation; never the failed job.
    assert report['primary_status'] == 'incomplete' and report['supplemental_status'] == 'completed'
    assert report['combined_status'] == 'incomplete'
    assert report['grade_sources'] == {'first': 29, 'supplemental': 123, 'supplemental_explicit_reattempt': 0, 'missing': 1}
    tokens = report['tokens']
    assert tokens['parent_unknown_usage_calls'] == 1 and tokens['known_total'] is False
    assert tokens['reported_tokens_lower_bound'] == frozen['parent_reported_tokens'] + 123 * 3
    assert report['adoption'] == {'decision': None, 'review_eligible': False,
                                  'reason': 'Baseline supplement only; it cannot authorize adoption or review eligibility.'}
    failed_variant = next(j['variant'] for j in manifest(run)['jobs'] if j['job_id'] == failed)
    aggregate = next(a for a in report['repeated_statistics']['aggregates'] if a['variant'] == failed_variant)
    assert not aggregate['eligible'] and 'missing_grades' in aggregate['ineligible_reasons']
    assert tree(run) == before  # Parent, including its incomplete report, is byte-identical.
    # A resumed run has nothing left to attempt and makes no call.
    supplemental.execute_supplemental(tmp_path / 'supp', execute=True, workers=3)
    assert len(roles) == 123
    result = CliRunner().invoke(main, ['evaluate', 'reliable', 'supplement-grades', 'report', '--output-dir', str(tmp_path / 'supp')])
    assert result.exit_code == 2 and '"combined_status": "incomplete"' in result.output


def test_explicit_reattempt_is_recorded_and_completes_three_repeat_statistics(parent, tmp_path, monkeypatch):
    run, failed = parent
    state = manifest(run)
    graded = next(iter(state['grades']))
    never = next(j['job_id'] for j in state['jobs'] if j['job_id'] not in state['grades'] and j['job_id'] != failed)
    for ids, reason, message in [((failed,), None, 'both'), ((), 'reason only', 'both'),
                                 ((graded,), 'graded job', 'Only failed'), ((never,), 'never attempted', 'Only failed')]:
        with pytest.raises(ValueError, match=message):
            supplemental.prepare_supplemental(run, tmp_path / ('bad-' + message.split()[0] + str(len(ids))),
                                              reattempt_job_ids=ids, reattempt_reason=reason)
    cli = CliRunner().invoke(main, ['evaluate', 'reliable', 'supplement-grades', 'prepare', '--parent-dir', str(run),
                                    '--output-dir', str(tmp_path / 'supp'), '--reattempt-job-id', failed,
                                    '--reattempt-reason', 'Owner-approved: parent call failed with unknown usage.'])
    assert cli.exit_code == 0, cli.output
    frozen = json.loads((tmp_path / 'supp/freeze.json').read_bytes())
    assert frozen['reattempt'] == {'job_ids': [failed], 'reason': 'Owner-approved: parent call failed with unknown usage.'}
    assert [s for s in frozen['scheduled'] if s['kind'] == 'reattempt'][0]['job_id'] == failed
    jobs = {j['job_id']: j for j in state['jobs']}
    scheduled = {s['job_id'] for s in frozen['scheduled']}
    # Supplemental graders fail 'scope' on repeat-2 jobs: known per-repeat sums.
    failing = {(job_id, 'scope') for job_id in scheduled if jobs[job_id]['repeat'] == 2}
    grader(monkeypatch, failing)
    result = CliRunner().invoke(main, ['evaluate', 'reliable', 'supplement-grades', 'run', '--output-dir',
                                       str(tmp_path / 'supp'), '--execute', '--workers', '2'])
    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / 'supp/report.json').read_bytes())
    assert report['combined_status'] == 'completed_with_supplement' and report['primary_status'] == 'incomplete'
    assert report['grade_sources'] == {'first': 29, 'supplemental': 123, 'supplemental_explicit_reattempt': 1, 'missing': 0}
    for aggregate in report['repeated_statistics']['aggregates']:
        variant = aggregate['variant']
        lost = sum(1 for job_id in scheduled if jobs[job_id]['variant'] == variant and jobs[job_id]['repeat'] == 2)
        assert aggregate['eligible'] and [r['passed_criteria'] for r in aggregate['repeats']] == [68, 68, 68 - lost]
        assert aggregate['statistics']['passed_criteria']['n'] == 3
        assert aggregate['statistics']['passed_criteria']['mean'] == pytest.approx((204 - lost) / 3)
    assert report['tokens']['known_total'] is False  # The parent's unknown call never becomes known.


def test_diagnostic_failures_are_accounted_and_stop_without_retry(parent, tmp_path, monkeypatch):
    run, _ = parent
    supplemental.prepare_supplemental(run, tmp_path / 'supp')
    calls = []
    def timeout_on_fifth(request):
        calls.append(request['job_id'])
        if len(calls) == 5:
            raise ValueError('Worker execution timed out.')
    grader(monkeypatch, behaviour=timeout_on_fifth)
    report = supplemental.execute_supplemental(tmp_path / 'supp', execute=True, workers=1)
    journal = json.loads((tmp_path / 'supp/supplemental-journal.json').read_bytes())
    failure = journal['calls'][-1]
    assert journal['stopped'] and len(journal['calls']) == 5
    assert failure['diagnostics']['stage'] == 'timeout' and failure['usage_unknown'] is True
    assert report['supplemental_status'] == 'stopped' and report['tokens']['supplemental_unknown_usage_calls'] == 1
    assert report['supplemental_execution']['failures'][0]['error'] == 'process_timeout'
    supplemental.execute_supplemental(tmp_path / 'supp', execute=True, workers=1)
    assert len(calls) == 5  # Stopped supplements never retry.
    result = CliRunner().invoke(main, ['evaluate', 'reliable', 'supplement-grades', 'run', '--output-dir',
                                       str(tmp_path / 'supp'), '--execute', '--workers', '1'])
    assert result.exit_code == 2


def test_known_failure_usage_is_counted_and_rejected_records_are_preserved(parent, tmp_path, monkeypatch):
    run, _ = parent
    supplemental.prepare_supplemental(run, tmp_path / 'a')
    def invalid_grades(request):
        usage = {'input_tokens': 10, 'output_tokens': 3, 'total_tokens': 13}
        final = 'SYNTHETIC_REJECTED_GRADE'
        assert usage and final
        raise ValueError('Worker returned invalid grades.')
    monkeypatch.setattr(evaluation_diagnostics.native, 'run_codex_worker', invalid_grades)
    report = supplemental.execute_supplemental(tmp_path / 'a', execute=True, workers=1)
    entry = json.loads((tmp_path / 'a/supplemental-journal.json').read_bytes())['calls'][0]
    assert entry['usage']['total_tokens'] == 13 and 'usage_unknown' not in entry
    assert entry['diagnostics']['final_message_bytes'] == len('SYNTHETIC_REJECTED_GRADE')
    assert 'SYNTHETIC_REJECTED_GRADE' not in json.dumps(entry)
    assert report['tokens']['supplemental_reported'] == 13
    supplemental.prepare_supplemental(run, tmp_path / 'b')
    def other_cli(request):
        result = fake_worker(request)
        result['metadata']['cli_version'] = 'codex-cli other'
        return result
    grader(monkeypatch, behaviour=other_cli)
    supplemental.execute_supplemental(tmp_path / 'b', execute=True, workers=1)
    rejected = json.loads((tmp_path / 'b/rejected-records.json').read_bytes())
    assert len(rejected) == 1 and rejected[0]['record']['metadata']['cli_version'] == 'codex-cli other'
    assert not (tmp_path / 'b/supplemental-grades.json').exists()


def _edit(path, change):
    value = json.loads(path.read_bytes())
    change(value)
    write_json(path, value)


@pytest.mark.parametrize('mutate,problem', [
    (lambda r, s, m: _edit(r / 'comprehension/first-grades.json', lambda v: v[0]['grades'][0].update(passed=False)), 'parent evidence changed'),
    (lambda r, s, m: _edit(r / 'execution-journal.json', lambda v: v.update(stopped=False)), 'parent evidence changed'),
    (lambda r, s, m: _edit(s / 'parent-evidence/comprehension/manifest.json', lambda v: v['responses'].clear()), 'copied parent evidence changed'),
    (lambda r, s, m: _edit(s / 'grade-requests.json', lambda v: v[0]['request'].update(max_output_tokens=64)), 'grade requests changed'),
    (lambda r, s, m: m.setattr(reliable, 'native_cli_version', lambda: 'codex-cli other'), 'native CLI version changed'),
    (lambda r, s, m: m.setattr(supplemental, 'observer_hash', lambda: '0' * 64), 'observer changed'),
    (lambda r, s, m: m.setattr(reliable, 'adapter_hash', lambda: '0' * 64), 'adapter changed'),
])
def test_tampering_blocks_execution_before_any_call(parent, tmp_path, monkeypatch, mutate, problem):
    run, _ = parent
    supplemental.prepare_supplemental(run, tmp_path / 'supp')
    calls = []
    grader(monkeypatch, roles=calls)
    mutate(run, tmp_path / 'supp', monkeypatch)
    with pytest.raises(ValueError, match=problem):
        supplemental.execute_supplemental(tmp_path / 'supp', execute=True)
    assert calls == [] and not (tmp_path / 'supp/supplemental-journal.json').exists()


def test_budgets_are_explicit_immutable_and_bound_batches(parent, tmp_path, monkeypatch):
    run, _ = parent
    supplemental.prepare_supplemental(run, tmp_path / 'supp')
    grader(monkeypatch)
    with pytest.raises(ValueError, match='Explicit execution'):
        supplemental.execute_supplemental(tmp_path / 'supp')
    report = supplemental.execute_supplemental(tmp_path / 'supp', execute=True, workers=3, max_calls=5)
    journal = json.loads((tmp_path / 'supp/supplemental-journal.json').read_bytes())
    assert [b['in_flight'] for b in journal['batches']] == [3, 2]
    assert journal['stop_reason'] == 'Budget exhausted before the next batch.'
    assert report['supplemental_status'] == 'incomplete' and report['grade_sources']['supplemental'] == 5
    with pytest.raises(ValueError, match='immutable'):
        supplemental.execute_supplemental(tmp_path / 'supp', execute=True, workers=3, max_calls=6)
    (tmp_path / 'supp/supplemental-journal.json').unlink()
    with pytest.raises(ValueError, match='journal is missing'):
        supplemental.execute_supplemental(tmp_path / 'supp', execute=True, workers=3, max_calls=5)


def test_prepare_refuses_unsafe_parents(parent, tmp_path):
    run, _ = parent
    (tmp_path / 'used').mkdir()
    (tmp_path / 'used/x').write_text('x')
    with pytest.raises(ValueError, match='new empty'):
        supplemental.prepare_supplemental(run, tmp_path / 'used')
    _edit(run / 'execution-journal.json', lambda v: v.update(stopped=False))
    with pytest.raises(ValueError, match='stopped parent'):
        supplemental.prepare_supplemental(run, tmp_path / 'a')
    _edit(run / 'execution-journal.json', lambda v: v.update(stopped=True))
    _edit(run / 'comprehension/manifest.json', lambda v: v['responses'].pop(next(iter(v['responses']))))
    with pytest.raises(ValueError, match='first answer'):
        supplemental.prepare_supplemental(run, tmp_path / 'b')
    assert not (tmp_path / 'a').exists() and not (tmp_path / 'b').exists()
