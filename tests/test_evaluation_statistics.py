"""Repeated-run statistics over synthetic graded rows (no corpus or LLM data)."""
import copy

import pytest

from secure_gateway.evaluation_statistics import repeated_statistics


def row(case_id, repeat, passed=None, *, variant='baseline', language='en', split='dev',
        criteria=4, group='g1', status=None):
    """``passed`` is the number of passing criteria; None leaves the row ungraded."""
    data = {'case_id': case_id, 'language': language, 'variant': variant, 'repeat': repeat,
            'split': split, 'template_group': group, 'criteria_count': criteria}
    if passed is not None:
        data['grades'] = [{'id': f'c{i}', 'passed': i < passed, 'evidence': 'quoted response'}
                          for i in range(criteria)]
    if status is not None:
        data['status'] = status
    return data


def known_rows(variant='baseline', split='dev'):
    # Two tasks (4 + 2 criteria = 6 possible). Passed per repeat: 3, 4, 5.
    plan = {0: (2, 1), 1: (2, 2), 2: (4, 1)}
    return [row(case, r, passed, variant=variant, split=split, criteria=size)
            for r, (a, b) in plan.items()
            for case, passed, size in (('t1', a, 4), ('t2', b, 2))]


def find(items, **keys):
    matches = [i for i in items if all(i.get(k) == v for k, v in keys.items())]
    assert len(matches) == 1, matches
    return matches[0]


def test_three_complete_repeats_report_known_mean_and_sample_sd():
    report = repeated_statistics(known_rows())
    group = find(report['groups'], split='dev', variant='baseline', language='en')
    assert group['eligible'] and group['ineligible_reasons'] == []
    assert [r['passed_criteria'] for r in group['repeats']] == [3, 4, 5]
    assert {r['possible_criteria'] for r in group['repeats']} == {6}
    stats = group['statistics']
    assert stats['passed_criteria'] == {'mean': 4.0, 'sample_sd': 1.0, 'n': 3}
    assert stats['accuracy']['mean'] == pytest.approx(4 / 6)
    assert stats['accuracy']['sample_sd'] == pytest.approx(1 / 6)  # ddof=1
    # Task success counts tasks with every criterion passed, not criteria.
    assert [r['task_success'] for r in group['repeats']] == [0, 1, 1]
    assert stats['task_success']['mean'] == pytest.approx(2 / 3)


def test_missing_grades_are_missing_not_zero_and_block_statistics():
    rows = known_rows()
    rows[-1].pop('grades')  # t2, repeat 2 is scheduled but ungraded
    group = find(repeated_statistics(rows)['groups'], language='en')
    last = group['repeats'][2]
    assert not group['eligible'] and group['statistics'] is None
    assert group['ineligible_reasons'] == ['missing_grades']
    assert last['complete'] is False and last['accuracy'] is None
    assert last['missing_tasks'] == 1 and last['graded_criteria'] == 4 and last['passed_criteria'] == 4
    assert last['observed_accuracy'] == 1.0  # not diluted by the ungraded task
    assert group['complete_repeats'] == 2
    partial = group['observed_partial']
    assert partial['eligible'] is False and partial['repeats_with_grades'] == 3
    assert partial['graded_criteria'] == 16 and partial['passed_criteria'] == 11


def test_missing_rows_in_a_repeat_are_reported_as_missing():
    rows = [r for r in known_rows() if not (r['case_id'] == 't1' and r['repeat'] == 1)]
    group = find(repeated_statistics(rows)['groups'], language='en')
    assert group['ineligible_reasons'] == ['missing_rows']
    assert group['repeats'][1]['rows_present'] == 1 and group['repeats'][1]['missing_tasks'] == 1
    assert group['repeats'][1]['possible_criteria'] == 6  # denominator stays scheduled


def test_fewer_than_three_expected_repeats_is_underpowered():
    rows = [r for r in known_rows() if r['repeat'] < 2]
    group = find(repeated_statistics(rows, expected_repeats=2)['groups'], language='en')
    assert all(r['complete'] for r in group['repeats'])
    assert not group['eligible'] and group['ineligible_reasons'] == ['underpowered_repeats']
    assert group['statistics'] is None


def test_missing_whole_repeat_is_ineligible():
    rows = [r for r in known_rows() if r['repeat'] < 2]  # repeat 2 never ran
    group = find(repeated_statistics(rows)['groups'], language='en')
    assert not group['eligible'] and 'missing_rows' in group['ineligible_reasons']
    assert group['repeats'][2]['rows_present'] == 0 and group['repeats'][2]['observed_accuracy'] is None


def test_empty_input():
    report = repeated_statistics([])
    assert report['groups'] == [] and report['aggregates'] == [] and report['paired'] == []
    assert report['holdout_eligibility']['present'] is False
    assert report['holdout_eligibility']['paired_eligible'] is False


def test_splits_are_never_pooled_and_holdout_metadata_uses_holdout_only():
    dev = known_rows()
    holdout = [dict(r, case_id='h' + r['case_id'], split='holdout') for r in known_rows()]
    holdout[0].pop('grades')
    report = repeated_statistics(dev + holdout)
    assert {(a['split'], a['variant']) for a in report['aggregates']} == {('dev', 'baseline'), ('holdout', 'baseline')}
    assert find(report['aggregates'], split='dev')['eligible'] is True
    held = find(report['aggregates'], split='holdout')
    assert held['eligible'] is False and held['scheduled_tasks'] == 2
    meta = report['holdout_eligibility']
    assert meta['present'] and meta['variants'] == {'baseline': {'eligible': False, 'ineligible_reasons': ['missing_grades']}}
    assert meta['decision'] is None and 'adopt' not in meta


def test_one_case_cannot_appear_in_two_splits():
    rows = known_rows() + [dict(r, split='holdout', variant='candidate') for r in known_rows()]
    with pytest.raises(ValueError, match='inconsistent split'):
        repeated_statistics(rows)


def test_aggregate_uses_actual_denominators_without_renormalizing():
    languages = ['en', 'ko', 'es', 'fr', 'pt', 'de', 'id', 'tr', 'ru', 'hi', 'mr', 'bn', 'ur', 'te', 'ar', 'zh', 'ja']
    rows = [row(f'{lang}-1', r, 4, language=lang) for lang in languages for r in range(3)]
    rows += [row('extra', r, 1, language='en', variant='candidate', criteria=3) for r in range(3)]
    rows += [row(f'{lang}-1', r, 2, language=lang, variant='candidate') for lang in languages[1:] for r in range(3)]
    rows += [row('en-1', r, 2, language='en', variant='candidate') for r in range(3)]
    with pytest.raises(ValueError, match='task selections differ'):
        repeated_statistics(rows)
    base_only = [r for r in rows if r['variant'] == 'baseline']
    base_only += [dict(r, variant='other') for r in rows if r['case_id'] == 'extra']
    report = repeated_statistics(base_only)
    base = find(report['aggregates'], split='dev', variant='baseline')
    assert base['scheduled_tasks'] == 17 and base['possible_criteria_per_repeat'] == 68
    assert base['statistics']['accuracy'] == {'mean': 1.0, 'sample_sd': 0.0, 'n': 3}
    assert len(base['languages']) == 17
    other = find(report['aggregates'], split='dev', variant='other')
    assert other['possible_criteria_per_repeat'] == 3  # not rescaled to 68
    assert other['statistics']['accuracy']['mean'] == pytest.approx(1 / 3)


def test_paired_candidate_minus_baseline_per_repeat():
    rows = known_rows() + [dict(r, variant='candidate') for r in known_rows()]
    for r in rows:
        if r['variant'] == 'candidate' and r['case_id'] == 't1':
            r['grades'] = [dict(g, passed=True) for g in r['grades']]  # t1: 4/4 every repeat
    report = repeated_statistics(rows)
    pair = find(report['paired'], split='dev', language=None)
    assert [p['passed_criteria_diff'] for p in pair['repeats']] == [2, 2, 0]
    assert [p['task_success_diff'] for p in pair['repeats']] == [1, 1, 0]
    assert pair['eligible'] and pair['statistics']['passed_criteria_diff']['mean'] == pytest.approx(4 / 3)
    assert find(report['paired'], split='dev', language='en')['repeats'] == pair['repeats']
    assert report['holdout_eligibility']['paired_eligible'] is False


def test_paired_ineligible_when_one_arm_incomplete():
    rows = known_rows() + [dict(r, variant='candidate') for r in known_rows()]
    rows[-1].pop('grades')
    pair = find(repeated_statistics(rows)['paired'], language=None)
    assert not pair['eligible'] and pair['statistics'] is None
    assert pair['ineligible_reasons'] == ['candidate:missing_grades']
    assert pair['repeats'][2]['passed_criteria_diff'] is None and pair['repeats'][0]['passed_criteria_diff'] == 0


def test_misaligned_paired_selection_is_rejected():
    rows = known_rows() + [dict(r, variant='candidate') for r in known_rows() if r['case_id'] == 't1']
    with pytest.raises(ValueError, match='task selections differ'):
        repeated_statistics(rows)


def test_duplicate_task_variant_repeat_is_rejected():
    rows = known_rows()
    rows.append(copy.deepcopy(rows[0]))
    with pytest.raises(ValueError, match='Duplicate'):
        repeated_statistics(rows)


@pytest.mark.parametrize('repeat', [3, -1, True, 1.0, None])
def test_invalid_repeat_index(repeat):
    rows = known_rows()
    rows[0]['repeat'] = repeat
    with pytest.raises(ValueError, match='repeat'):
        repeated_statistics(rows)


def test_non_boolean_passed_is_rejected():
    rows = known_rows()
    rows[0]['grades'][0]['passed'] = 1
    with pytest.raises(ValueError, match='non-boolean'):
        repeated_statistics(rows)


def test_inconsistent_rubric_cardinality_is_rejected():
    rows = known_rows()
    rows[2] = row('t1', 1, 2, criteria=5)
    with pytest.raises(ValueError, match='criteria_count'):
        repeated_statistics(rows)


def test_grade_count_must_match_criteria_count():
    rows = known_rows()
    rows[0]['grades'].pop()
    with pytest.raises(ValueError, match='grade count'):
        repeated_statistics(rows)


def test_inconsistent_criterion_ids_are_rejected():
    rows = known_rows()
    rows[2]['grades'][0]['id'] = 'other'
    with pytest.raises(ValueError, match='criterion ids'):
        repeated_statistics(rows)


def test_duplicate_criterion_ids_are_rejected():
    rows = known_rows()
    rows[0]['grades'][1]['id'] = 'c0'
    with pytest.raises(ValueError, match='unique'):
        repeated_statistics(rows)


@pytest.mark.parametrize('field,value', [('case_id', ''), ('split', None), ('criteria_count', 0),
                                          ('criteria_count', True), ('status', 3)])
def test_invalid_row_fields(field, value):
    rows = known_rows()
    rows[0][field] = value
    with pytest.raises(ValueError):
        repeated_statistics(rows)


@pytest.mark.parametrize('expected', [0, True, 2.0])
def test_invalid_expected_repeats(expected):
    with pytest.raises(ValueError, match='expected_repeats'):
        repeated_statistics([], expected_repeats=expected)


def test_status_is_informational_and_input_is_not_mutated():
    rows = known_rows()
    rows[0]['status'] = 'graded'
    snapshot = copy.deepcopy(rows)
    report = repeated_statistics(rows)
    assert rows == snapshot
    assert find(report['groups'], language='en')['eligible'] is True
