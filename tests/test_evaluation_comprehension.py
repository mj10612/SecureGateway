"""Comprehension harness tests; these fixture responses are not LLM evidence."""
import copy
import json

import pytest

from test_evaluation import corpus


def prepared(tmp_path):
    from secure_gateway.evaluation import run_privacy
    from secure_gateway.evaluation_comprehension import prepare_comprehension
    data = corpus()
    privacy = run_privacy(data, output_dir=tmp_path / 'privacy')
    return prepare_comprehension(data, privacy, privacy, output_dir=tmp_path / 'llm', model='test-model')


def test_blind_jobs_hide_labels_and_grades_only_follow_saved_responses(tmp_path):
    state = prepared(tmp_path)
    jobs = state['jobs']
    assert {j['variant'] for j in jobs} == {'original', 'human', 'baseline', 'candidate'}
    public = [json.loads(line) for line in (tmp_path / 'llm' / 'interpret-jobs.jsonl').read_text().splitlines()]
    assert len(public) == 4
    for job in public:
        assert set(job) == {'role', 'job_id', 'model', 'max_output_tokens', 'messages'}
        assert 'criteria' not in job and 'variant' not in job
        if next(j for j in jobs if j['job_id'] == job['job_id'])['variant'] != 'original':
            assert 'KeplerQzx' not in json.dumps(job)
    assert not (tmp_path / 'llm' / 'grade-jobs.jsonl').exists()


def test_missing_answers_are_unmeasured_and_cannot_be_graded(tmp_path):
    from secure_gateway.evaluation_comprehension import continue_comprehension
    state = prepared(tmp_path)
    report = continue_comprehension(tmp_path / 'llm')
    assert report['status'] == 'incomplete'
    assert report['metrics']['comprehension']['status'] == 'not_measured'
    assert report['metrics']['comprehension']['scheduled_requests'] == 4
    grade = {'job_id': state['jobs'][0]['job_id'], 'model': 'test-model', 'response_hash': 'fake',
             'grades': [{'id': 'intent', 'passed': True, 'evidence': 'fixture'}]}
    path = tmp_path / 'grades.json'
    path.write_text(json.dumps([grade]))
    with pytest.raises(ValueError, match='response'):
        continue_comprehension(tmp_path / 'llm', grades_path=path)


def test_imports_real_response_contract_and_rejects_replacement(tmp_path):
    from secure_gateway.evaluation import digest
    from secure_gateway.evaluation_comprehension import continue_comprehension
    state = prepared(tmp_path)
    job_id = state['jobs'][0]['job_id']
    response = {'job_id': job_id, 'model': 'test-model', 'response': 'Review the project; preserve the original.',
                'execution': {'kind': 'actual_llm_subagent', 'fresh_context': True, 'runner': 'unit-fixture', 'isolation': 'fixture only'}}
    path = tmp_path / 'responses.json'
    path.write_text(json.dumps([response]))
    report = continue_comprehension(tmp_path / 'llm', responses_path=path)
    assert report['metrics']['comprehension']['responses_received'] == 1
    grades = [json.loads(line) for line in (tmp_path / 'llm' / 'grade-jobs.jsonl').read_text().splitlines()]
    assert len(grades) == 1
    assert 'KeplerQzx' in json.dumps(grades[0])
    assert grades[0]['response_hash'] == digest(response['response'])
    replacement = copy.deepcopy(response)
    replacement['response'] = 'Changed after learning the answer'
    path.write_text(json.dumps([replacement]))
    with pytest.raises(ValueError, match='first response'):
        continue_comprehension(tmp_path / 'llm', responses_path=path)
    path.write_text(json.dumps([response]))
    grade_path = tmp_path / 'grades.json'
    grade_path.write_text(json.dumps([{'job_id': job_id, 'model': 'test-model', 'response_hash': digest(response['response']),
                                     'execution': response['execution'],
                                     'grades': [{'id': 'intent', 'passed': True, 'evidence': 'Review'},
                                                {'id': 'negation', 'passed': True, 'evidence': 'preserve'}]}]))
    report = continue_comprehension(tmp_path / 'llm', grades_path=grade_path)
    metrics = report['metrics']['comprehension']
    assert metrics['graded_requests'] == 1
    assert metrics['passed_criteria'] == 2
    assert metrics['total_criteria'] == 8
    assert metrics['accuracy'] is None  # incomplete runs do not get a complete accuracy
    assert metrics['observed_accuracy'] == 1.0


def test_rejects_unknown_jobs_without_inventing_success(tmp_path):
    from secure_gateway.evaluation_comprehension import continue_comprehension
    prepared(tmp_path)
    path = tmp_path / 'responses.json'
    path.write_text(json.dumps([{'job_id': 'invented', 'response': 'ok', 'model': 'test-model'}]))
    with pytest.raises(ValueError, match='Unknown'):
        continue_comprehension(tmp_path / 'llm', responses_path=path)


def test_cli_resume_rejects_changed_model(tmp_path):
    from click.testing import CliRunner
    from secure_gateway.cli import main
    prepared(tmp_path)
    result = CliRunner().invoke(main, ['evaluate', '--suite', 'comprehension', '--real-llm', '--prepare-only',
                                      '--output-dir', str(tmp_path / 'llm'), '--model', 'different-model'])
    assert result.exit_code == 1
    assert 'immutable' in result.output


def test_unknown_usage_after_failed_inference_stops_further_calls(tmp_path):
    import sys
    from secure_gateway.evaluation_comprehension import continue_comprehension
    prepared(tmp_path)
    counter = tmp_path / 'calls.txt'
    worker = tmp_path / 'bad_worker.py'
    worker.write_text('import json,sys\nfrom pathlib import Path\np=Path(' + repr(str(counter)) + ')\np.write_text(p.read_text()+"x" if p.exists() else "x")\nr=json.load(sys.stdin)\nprint(json.dumps({"job_id":r["job_id"],"model":r["model"],"response":"x","usage":{"total_tokens":100000,"output_tokens":100000}}))\n')
    report = continue_comprehension(tmp_path / 'llm', command=[sys.executable, str(worker)], max_tokens=1)
    assert counter.read_text() == 'x'
    assert report['status'] == 'incomplete'
    assert report['metadata']['token_usage_unknown'] is True


def test_automatic_worker_persists_all_first_responses_before_independent_grading(tmp_path):
    import sys
    from secure_gateway.evaluation_comprehension import continue_comprehension
    prepared(tmp_path)
    manifest = tmp_path / 'llm' / 'manifest.json'
    worker = tmp_path / 'fixture_worker.py'
    worker.write_text('''import json,sys
from pathlib import Path
r=json.load(sys.stdin)
if r['role']=='interpret':
    assert 'criteria' not in r
    result={'response':'Review the project; preserve the original.'}
else:
    state=json.loads(Path(MANIFEST).read_text())
    assert len(state['responses'])==4
    result={'grades':[{'id':c['id'],'passed':True,'evidence':'unit fixture evidence, not actual LLM evaluation'} for c in r['criteria']]}
print(json.dumps(dict(job_id=r['job_id'],model=r['model'],usage={'total_tokens':10,'output_tokens':5},**result)))
'''.replace('MANIFEST', repr(str(manifest))))
    report = continue_comprehension(tmp_path / 'llm', command=[sys.executable, str(worker)], max_calls=4)
    assert report['metrics']['comprehension']['responses_received'] == 4
    assert report['metrics']['comprehension']['graded_requests'] == 0
    report = continue_comprehension(tmp_path / 'llm', command=[sys.executable, str(worker)], max_calls=8)
    assert report['status'] == 'completed'
    assert report['attempts'] == 8
    assert report['metrics']['comprehension']['graded_requests'] == 4
    assert report['metrics']['comprehension']['accuracy'] == 1.0
