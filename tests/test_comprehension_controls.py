"""Real loopback control prompts must remain independent of gateway instructions."""
from copy import deepcopy
import json

from secure_gateway.evaluation import load_corpus, run_privacy
from secure_gateway.evaluation_comprehension import _grade_request, prepare_comprehension
from secure_gateway.gateway import PRIVACY_INSTRUCTION


def test_controls_use_source_system_while_masked_arm_uses_captured_system(tmp_path):
    data = deepcopy(load_corpus())
    data['cases'] = [next(c for c in data['cases'] if c['rubric'] and c['dialect'] == 'codex')]
    data['cases'][0]['payload']['instructions'] = 'Source system instruction.'
    data['cases'][0]['reference_response'] = 'OWNER_REFERENCE_DO_NOT_GRADE_BY_SIMILARITY'
    captured = run_privacy(data, output_dir=tmp_path / 'capture', profile='release')
    assert captured['status'] == 'completed'
    state = prepare_comprehension(data, captured, captured, output_dir=tmp_path / 'jobs',
                                  model='unit-only', profile='release', all_tasks=True,
                                  variants=('original', 'human', 'baseline'), grading_policy_version=2)
    for job in state['jobs']:
        system = job['request']['messages'][0]['content']
        if job['variant'] in {'original', 'human'}:
            assert system == 'Source system instruction.'
            assert PRIVACY_INSTRUCTION not in system
        else:
            assert PRIVACY_INSTRUCTION in system
        grade = _grade_request(job, {'response': 'Synthetic saved answer'})
        assert 'OWNER_REFERENCE_DO_NOT_GRADE_BY_SIMILARITY' not in json.dumps(grade)
