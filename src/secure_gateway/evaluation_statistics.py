"""Repeated-run statistics for graded comprehension rows.

The input is a flat list of owner rows, one per scheduled (case, variant,
repeat). Results are reported separately for each split; dev and holdout are
never pooled. The unit of a task-success count is a case, never a criterion:
criteria of one case are correlated and are only summed into per-repeat
passed/possible counts.

A mean and sample standard deviation are reported only when every scheduled
row of every expected repeat is graded and at least ``MINIMUM_REPEATS``
repeats are expected. Anything less is reported as observed partial data with
``eligible: False``. Missing grades are missing, never counted as failures.
This module computes statistics only; it does not adopt or enable anything.
"""

from __future__ import annotations

from statistics import fmean, stdev
from typing import Any, Iterable, Mapping, TypeGuard

SCHEMA_VERSION = 1
MINIMUM_REPEATS = 3
HOLDOUT_SPLIT = 'holdout'
_TEXT_FIELDS = ('case_id', 'language', 'variant', 'split', 'template_group')


def _int(value: Any) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate(rows: Iterable[Mapping[str, Any]], expected_repeats: int) -> tuple[list[dict], dict]:
    if not _int(expected_repeats) or expected_repeats < 1:
        raise ValueError('expected_repeats must be a positive integer.')
    if isinstance(rows, (str, bytes, Mapping)):
        raise ValueError('rows must be a sequence of row objects.')
    cases: dict[str, dict] = {}
    seen: set[tuple] = set()
    clean: list[dict] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f'Row {index} is not an object.')
        for field in _TEXT_FIELDS:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f'Row {index} requires a nonempty string {field}.')
        repeat, count = row.get('repeat'), row.get('criteria_count')
        if not _int(repeat) or not 0 <= repeat < expected_repeats:
            raise ValueError(f'Row {index} has an invalid repeat index {repeat!r}.')
        if not _int(count) or count < 1:
            raise ValueError(f'Row {index} has an invalid criteria_count.')
        status = row.get('status')
        if status is not None and not isinstance(status, str):
            raise ValueError(f'Row {index} has a non-string status.')
        key = (row['case_id'], row['variant'], repeat)
        if key in seen:
            raise ValueError(f'Duplicate row for case/variant/repeat {key!r}.')
        seen.add(key)

        case = cases.setdefault(row['case_id'], {
            'language': row['language'], 'split': row['split'],
            'template_group': row['template_group'], 'criteria_count': count, 'criterion_ids': None})
        for field in ('language', 'split', 'template_group', 'criteria_count'):
            source = count if field == 'criteria_count' else row[field]
            if case[field] != source:
                raise ValueError(f'Case {row["case_id"]!r} has inconsistent {field} across rows.')

        grades = row.get('grades')
        passed = None
        if grades is not None:
            if not isinstance(grades, list) or any(not isinstance(g, Mapping) for g in grades):
                raise ValueError(f'Row {index} grades must be a list of objects.')
            ids = [g.get('id') for g in grades]
            if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
                raise ValueError(f'Row {index} grades need unique nonempty criterion ids.')
            if len(ids) != count:
                raise ValueError(f'Row {index} grade count does not match criteria_count.')
            if case['criterion_ids'] is None:
                case['criterion_ids'] = frozenset(ids)
            elif case['criterion_ids'] != frozenset(ids):
                raise ValueError(f'Case {row["case_id"]!r} has inconsistent criterion ids.')
            if any(type(g.get('passed')) is not bool for g in grades):
                raise ValueError(f'Row {index} has a non-boolean passed value.')
            if any('evidence' in g and not isinstance(g['evidence'], str) for g in grades):
                raise ValueError(f'Row {index} has non-string evidence.')
            passed = sum(g['passed'] for g in grades)
        clean.append({'case_id': row['case_id'], 'variant': row['variant'], 'repeat': repeat,
                      'split': row['split'], 'language': row['language'], 'passed': passed,
                      'criteria_count': count})
    return clean, cases


def _moments(values: list[float]) -> dict:
    return {'mean': fmean(values), 'sample_sd': stdev(values), 'n': len(values)}


def _summarize(rows: list[dict], scheduled: set[str], cases: dict, expected_repeats: int) -> dict:
    """Per-repeat counts and eligibility for one scheduled task selection."""
    by_repeat: dict[int, dict[str, dict]] = {r: {} for r in range(expected_repeats)}
    for row in rows:
        by_repeat[row['repeat']][row['case_id']] = row
    possible = sum(cases[c]['criteria_count'] for c in scheduled)
    repeats = []
    for repeat in range(expected_repeats):
        present = by_repeat[repeat]
        graded = [present[c] for c in sorted(scheduled) if c in present and present[c]['passed'] is not None]
        graded_criteria = sum(r['criteria_count'] for r in graded)
        passed = sum(r['passed'] for r in graded)
        complete = len(graded) == len(scheduled) and bool(scheduled)
        repeats.append({
            'repeat': repeat, 'scheduled_tasks': len(scheduled),
            'rows_present': sum(c in present for c in scheduled), 'graded_tasks': len(graded),
            'missing_tasks': len(scheduled) - len(graded), 'possible_criteria': possible,
            'graded_criteria': graded_criteria, 'passed_criteria': passed,
            'task_success': sum(r['passed'] == r['criteria_count'] for r in graded),
            'complete': complete,
            'accuracy': passed / possible if complete else None,
            'observed_accuracy': passed / graded_criteria if graded_criteria else None,
        })
    reasons = []
    if expected_repeats < MINIMUM_REPEATS:
        reasons.append('underpowered_repeats')
    if any(r['rows_present'] < r['scheduled_tasks'] for r in repeats):
        reasons.append('missing_rows')
    if any(r['graded_tasks'] < r['rows_present'] for r in repeats):
        reasons.append('missing_grades')
    if not scheduled:
        reasons.append('no_scheduled_tasks')
    eligible = not reasons
    complete_repeats = [r for r in repeats if r['complete']]
    observed = [r for r in repeats if r['graded_criteria']]
    return {
        'scheduled_tasks': len(scheduled), 'possible_criteria_per_repeat': possible,
        'repeats': repeats, 'complete_repeats': len(complete_repeats), 'eligible': eligible,
        'ineligible_reasons': reasons,
        'statistics': None if not eligible else {
            'accuracy': _moments([r['accuracy'] for r in repeats]),
            'passed_criteria': _moments([float(r['passed_criteria']) for r in repeats]),
            'task_success': _moments([float(r['task_success']) for r in repeats]),
        },
        'observed_partial': {
            'eligible': False, 'repeats_with_grades': len(observed),
            'graded_criteria': sum(r['graded_criteria'] for r in observed),
            'passed_criteria': sum(r['passed_criteria'] for r in observed),
            'mean_observed_accuracy': fmean(r['observed_accuracy'] for r in observed) if observed else None,
        },
    }


def _paired(base: dict, cand: dict) -> dict:
    repeats = []
    for b, c in zip(base['repeats'], cand['repeats']):
        both = b['complete'] and c['complete']
        repeats.append({
            'repeat': b['repeat'], 'complete': both,
            'passed_criteria_diff': c['passed_criteria'] - b['passed_criteria'] if both else None,
            'accuracy_diff': c['accuracy'] - b['accuracy'] if both else None,
            'task_success_diff': c['task_success'] - b['task_success'] if both else None,
        })
    eligible = base['eligible'] and cand['eligible']
    return {
        'scheduled_tasks': base['scheduled_tasks'], 'possible_criteria_per_repeat': base['possible_criteria_per_repeat'],
        'repeats': repeats, 'eligible': eligible,
        'ineligible_reasons': sorted({f'baseline:{r}' for r in base['ineligible_reasons']}
                                     | {f'candidate:{r}' for r in cand['ineligible_reasons']}),
        'statistics': None if not eligible else {
            key: _moments([float(r[key]) for r in repeats])
            for key in ('passed_criteria_diff', 'accuracy_diff', 'task_success_diff')},
    }


def repeated_statistics(rows: Iterable[Mapping[str, Any]], *, expected_repeats: int = 3,
                        baseline_variant: str = 'baseline', candidate_variant: str = 'candidate') -> dict:
    """Summarize repeated graded rows per split/variant/language and per split/variant.

    Rows: ``case_id, language, variant, repeat (0-based), split, template_group,
    criteria_count`` and optional ``grades [{id, passed, evidence}]`` and ``status``.
    A row without ``grades`` is scheduled but ungraded. Raises ``ValueError`` on
    duplicates, invalid repeats, inconsistent rubric cardinality/ids per case,
    non-boolean results, or misaligned baseline/candidate task selection.
    """
    clean, cases = _validate(rows, expected_repeats)
    selection: dict[tuple, set[str]] = {}
    grouped: dict[tuple, list[dict]] = {}
    for row in clean:
        for key in ((row['split'], row['variant'], row['language']), (row['split'], row['variant'], None)):
            selection.setdefault(key, set()).add(row['case_id'])
            grouped.setdefault(key, []).append(row)
    summaries = {key: _summarize(grouped[key], selection[key], cases, expected_repeats) for key in selection}

    def entry(key):
        split, variant, language = key
        head = {'split': split, 'variant': variant}
        if language is None:
            head['languages'] = sorted({cases[c]['language'] for c in selection[key]})
        else:
            head['language'] = language
        return {**head, **summaries[key]}

    order = sorted(selection, key=lambda k: (k[0], k[1], k[2] or ''))
    paired = []
    for split in sorted({k[0] for k in selection}):
        base_key, cand_key = (split, baseline_variant, None), (split, candidate_variant, None)
        if base_key not in selection or cand_key not in selection:
            continue
        if selection[base_key] != selection[cand_key]:
            raise ValueError(f'Baseline and candidate task selections differ in split {split!r}.')
        for language in [None] + sorted({cases[c]['language'] for c in selection[base_key]}):
            b, c = (split, baseline_variant, language), (split, candidate_variant, language)
            paired.append({'split': split, 'language': language, 'baseline_variant': baseline_variant,
                           'candidate_variant': candidate_variant, **_paired(summaries[b], summaries[c])})

    holdout_aggregates = [entry(k) for k in order if k[0] == HOLDOUT_SPLIT and k[2] is None]
    holdout_paired = [p for p in paired if p['split'] == HOLDOUT_SPLIT and p['language'] is None]
    return {
        'schema_version': SCHEMA_VERSION,
        'expected_repeats': expected_repeats,
        'minimum_repeats': MINIMUM_REPEATS,
        'groups': [entry(k) for k in order if k[2] is not None],
        'aggregates': [entry(k) for k in order if k[2] is None],
        'paired': paired,
        'holdout_eligibility': {
            'split': HOLDOUT_SPLIT,
            'present': bool(holdout_aggregates),
            'variants': {a['variant']: {'eligible': a['eligible'], 'ineligible_reasons': a['ineligible_reasons']}
                         for a in holdout_aggregates},
            'paired_eligible': holdout_paired[0]['eligible'] if holdout_paired else False,
            'decision': None,
            'note': 'Statistical eligibility only; this report adopts and enables nothing.',
        },
    }
