"""Prospectively frozen grade-only supplement for a stopped #324 reliable run.

The parent run stays stopped and incomplete: its files are pinned, copied and
never written. Saved first answers and first grades are reused unchanged. Only
never-attempted missing grades are scheduled by default; a failed parent attempt
is graded again only when named explicitly with a recorded reason. Every call is
reserved before launch, there are no automatic retries, and unknown usage stops.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import inspect
import json
from pathlib import Path
import time
from typing import Any

from secure_gateway import evaluation_diagnostics
from secure_gateway import evaluation_reliable as reliable
from secure_gateway.encrypted_session import session_file_lock
from secure_gateway.evaluation import digest
from secure_gateway.evaluation_comprehension import _grade_request, _validate_grades, continue_comprehension
from secure_gateway.evaluation_diagnostics import ObservedWorkerFailure, diagnostic_worker

SCHEMA = 1
# Parent files pinned and copied before any supplemental call.
PARENT_FILES = (
    'freeze.json', 'execution-journal.json', 'report.json',
    'privacy/report.json', 'task-capture/report.json',
    'comprehension/manifest.json', 'comprehension/first-responses.json',
    'comprehension/first-grades.json', 'comprehension/report.json',
)
LOWER_BOUND_NOTE = ('Reported tokens are a lower bound: calls with unknown usage are counted as calls, '
                    'not tokens. The original run did not complete and did not meet a known total budget.')


def observer_hash():
    return sha256(Path(inspect.getfile(evaluation_diagnostics)).read_bytes()).hexdigest()


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _load(path):
    return json.loads(Path(path).read_bytes())


def _parent_files(parent):
    names = list(PARENT_FILES) + sorted('corpora/' + p.name for p in (parent / 'corpora').glob('*.json'))
    missing = [name for name in names if not (parent / name).is_file()]
    if missing:
        raise ValueError('Parent run evidence is missing: ' + ', '.join(missing))
    return names


def prepare_supplemental(parent_dir, output_dir, *, reattempt_job_ids=(), reattempt_reason=None):
    """Freeze parent evidence and the exact grade requests; makes no model calls."""
    parent, output = Path(parent_dir), Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new empty supplemental output directory.')
    reattempt = tuple(dict.fromkeys(reattempt_job_ids))
    if bool(reattempt) != bool(reattempt_reason and reattempt_reason.strip()):
        raise ValueError('A reattempt requires both named job ids and a reattempt reason.')
    frozen_parent = _load(parent / 'freeze.json')
    problems = reliable._verify_freeze(parent, frozen_parent)
    if problems:
        raise ValueError('Parent run is not an intact frozen preparation: ' + '; '.join(problems))
    names = _parent_files(parent)
    before = {name: _hash(parent / name) for name in names}
    journal = _load(parent / 'execution-journal.json')
    if not journal.get('stopped'):
        raise ValueError('Supplemental grading applies only to a stopped parent run.')
    state = _load(parent / 'comprehension/manifest.json')
    jobs = {job['job_id']: job for job in state['jobs']}
    if set(state['responses']) != set(jobs):
        raise ValueError('Every first answer must be saved; interpretations are never repeated.')
    saved_answers = {r['job_id']: r for r in _load(parent / 'comprehension/first-responses.json')}
    saved_grades = {r['job_id']: r for r in _load(parent / 'comprehension/first-grades.json')}
    if saved_answers != state['responses'] or saved_grades != state['grades']:
        raise ValueError('Parent first-answer/grade records disagree with its manifest.')
    for job_id, record in state['grades'].items():
        _validate_grades(record, jobs[job_id], state['responses'][job_id])
    failed = [{'journal_index': index, 'job_id': call['job_id'], 'phase': call.get('phase'),
               'status': call['status'], 'error': call.get('error'),
               'usage_unknown': 'total_tokens' not in call.get('usage', {})}
              for index, call in enumerate(journal['calls']) if call['status'] != 'completed']
    attempted = {c['job_id'] for c in journal['calls'] if c.get('phase') == 'grade'}
    failed_grades = {f['job_id'] for f in failed if f['phase'] == 'grade'} - set(state['grades'])
    if set(reattempt) - failed_grades:
        raise ValueError('Only failed, ungraded parent grade attempts can be named for reattempt.')
    missing = [job_id for job_id in sorted(jobs) if job_id not in state['grades'] and job_id not in attempted]
    scheduled = [{'job_id': job_id, 'kind': 'missing'} for job_id in missing]
    scheduled += [{'job_id': job_id, 'kind': 'reattempt'} for job_id in reattempt]
    requests = []
    for item in scheduled:
        job, response = jobs[item['job_id']], state['responses'][item['job_id']]
        request = _grade_request(job, response)
        requests.append({**item, 'request': request, 'request_sha256': digest(request),
                         'response_hash': digest(response['response'])})
    cli_version = reliable.native_cli_version()
    if cli_version != frozen_parent['cli_version']:
        raise ValueError('Native CLI version differs from the parent freeze.')

    output.mkdir(parents=True, exist_ok=True)
    for name in names:
        destination = output / 'parent-evidence' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((parent / name).read_bytes())
    copied = {name: _hash(output / 'parent-evidence' / name) for name in names}
    if copied != before or {name: _hash(parent / name) for name in names} != before:
        raise ValueError('Parent evidence changed while it was being frozen.')
    reliable._write_json(output / 'grade-requests.json', requests)
    parent_calls = journal['calls']
    frozen = {
        'schema_version': SCHEMA, 'prepared': True, 'kind': 'grade_only_supplement',
        'parent_dir': str(parent.resolve()), 'parent_evidence_sha256': before,
        'parent_status': _load(parent / 'report.json').get('status'),
        'parent_stop_reason': journal.get('stop_reason'), 'parent_failed_calls': failed,
        'parent_calls': len(parent_calls),
        'parent_reported_tokens': sum(c.get('usage', {}).get('total_tokens', 0) for c in parent_calls),
        'parent_unknown_usage_calls': sum('total_tokens' not in c.get('usage', {}) for c in parent_calls),
        'first_answers': len(state['responses']), 'first_grades': len(state['grades']),
        'scheduled': [{k: r[k] for k in ('job_id', 'kind', 'request_sha256', 'response_hash')} for r in requests],
        'reattempt': {'job_ids': list(reattempt), 'reason': reattempt_reason if reattempt else None},
        'grade_requests_sha256': _hash(output / 'grade-requests.json'),
        'model': frozen_parent['model'], 'reasoning_effort': frozen_parent['reasoning_effort'],
        'max_output_tokens': frozen_parent['max_output_tokens'], 'cli_version': cli_version,
        'adapter_source_sha256': frozen_parent['adapter_source_sha256'],
        'grading_policy_sha256': frozen_parent['grading_policy_sha256'],
        'observer_source_sha256': observer_hash(),
        'observer': 'secure_gateway.evaluation_diagnostics.diagnostic_worker (calls the unchanged native adapter)',
        'prepared_at_unix': time.time(),
        'scope': 'Grade-only supplement of saved first answers; no interpretation, no adoption decision.',
    }
    reliable._write_json(output / 'freeze.json', frozen)
    return frozen


def _verify(output, frozen, *, check_cli=False):
    problems = []
    if frozen.get('schema_version') != SCHEMA or frozen.get('prepared') is not True:
        return ['supplement is not a completed preparation']
    parent = Path(frozen['parent_dir'])
    for name, value in frozen['parent_evidence_sha256'].items():
        for root, label in ((parent, 'parent'), (output / 'parent-evidence', 'copied parent')):
            if not (root / name).is_file() or _hash(root / name) != value:
                problems.append(f'{label} evidence changed: {name}')
    if not (output / 'grade-requests.json').is_file() or _hash(output / 'grade-requests.json') != frozen['grade_requests_sha256']:
        problems.append('frozen grade requests changed')
    if reliable.adapter_hash() != frozen['adapter_source_sha256']:
        problems.append('native adapter changed')
    if reliable.grading_policy_hash() != frozen['grading_policy_sha256']:
        problems.append('grading policy changed')
    if observer_hash() != frozen['observer_source_sha256']:
        problems.append('diagnostic observer changed')
    if check_cli:
        try:
            if reliable.native_cli_version() != frozen['cli_version']:
                problems.append('native CLI version changed')
        except (ValueError, OSError):
            problems.append('native CLI unavailable')
    return problems


def execute_supplemental(output_dir, *, execute=False, max_calls=124, max_seconds=3600, max_tokens=4_000_000, workers=3):
    """Run only frozen grade requests; reserve each attempt, never retry, stop on errors."""
    if not execute or type(workers) is not int or not 1 <= workers <= 3:
        raise ValueError('Explicit execution and 1..3 workers required.')
    if type(max_calls) is not int or max_calls < 1 or max_seconds <= 0 or type(max_tokens) is not int or max_tokens < 1:
        raise ValueError('Positive execution budgets required.')
    output = Path(output_dir)
    with session_file_lock(output / 'supplement-execution'):
        frozen = _load(output / 'freeze.json')
        problems = _verify(output, frozen, check_cli=True)
        if problems:
            raise ValueError('Supplement verification failed: ' + '; '.join(problems))
        evidence = output / 'parent-evidence'
        state = _load(evidence / 'comprehension/manifest.json')
        jobs = {job['job_id']: job for job in state['jobs']}
        requests = {r['job_id']: r for r in _load(output / 'grade-requests.json')}
        for item in frozen['scheduled']:
            request = requests[item['job_id']]
            if (digest(request['request']) != item['request_sha256']
                    or digest(_grade_request(jobs[item['job_id']], state['responses'][item['job_id']])) != item['request_sha256']
                    or digest(state['responses'][item['job_id']]['response']) != item['response_hash']):
                raise ValueError('A frozen grade request no longer matches its saved first answer.')
        journal_path, grades_path = output / 'supplemental-journal.json', output / 'supplemental-grades.json'
        rejected_path = output / 'rejected-records.json'
        if not journal_path.exists() and (grades_path.exists() or rejected_path.exists()):
            raise ValueError('Supplemental journal is missing while saved records exist.')
        budget = {'max_calls': max_calls, 'max_seconds': max_seconds, 'max_reported_tokens': max_tokens, 'workers': workers}
        journal = _load(journal_path) if journal_path.exists() else {
            'budget': budget, 'started_at_unix': time.time(), 'deadline_unix': time.time() + max_seconds,
            'calls': [], 'batches': [], 'elapsed_seconds': 0.0, 'stopped': False}
        if journal['budget'] != budget:
            raise ValueError('Supplemental budgets are immutable across resume.')
        saved = _load(grades_path) if grades_path.exists() else []
        done = {r['job_id'] for r in saved}
        accounted = {c['job_id'] for c in journal['calls'] if c['status'] in {'completed', 'running'}}
        if done - accounted:
            raise ValueError('Saved supplemental grades are not accounted for by the journal.')
        if any(c['status'] == 'running' for c in journal['calls']):
            journal['stopped'] = True
            journal['stop_reason'] = 'Interrupted call has unknown usage; no automatic retry.'
        attempted = {c['job_id'] for c in journal['calls']}
        pending = [item for item in frozen['scheduled'] if item['job_id'] not in attempted]
        reliable._write_json(journal_path, journal)
        started = time.monotonic()
        provenance = {'model': frozen['model'], 'reasoning_effort': frozen['reasoning_effort'],
                      'adapter': frozen['adapter_source_sha256'], 'cli_version': frozen['cli_version']}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            while pending and not journal['stopped']:
                usage = sum(c.get('usage', {}).get('total_tokens', 0) for c in journal['calls'])
                elapsed = journal['elapsed_seconds'] + time.monotonic() - started
                remaining = max_calls - len(journal['calls'])
                if remaining <= 0 or usage >= max_tokens or elapsed >= max_seconds or time.time() >= journal['deadline_unix']:
                    journal['stop_reason'] = 'Budget exhausted before the next batch.'
                    break
                batch, pending = pending[:min(workers, remaining)], pending[min(workers, remaining):]
                entries = {item['job_id']: {'job_id': item['job_id'], 'kind': item['kind'], 'status': 'running',
                                            'request_sha256': item['request_sha256'], 'started_at_unix': time.time()}
                           for item in batch}
                journal['calls'].extend(entries.values())
                journal['batches'].append({'in_flight': len(batch), 'reported_tokens_before': usage})
                reliable._write_json(journal_path, journal)  # Reserve attempts before starting children.
                futures = {pool.submit(diagnostic_worker, requests[item['job_id']]['request']): item for item in batch}
                for future in as_completed(futures):
                    item = futures[future]
                    entry, job_id = entries[item['job_id']], item['job_id']
                    result = None
                    try:
                        result = future.result()
                        entry['usage'] = result.get('usage', {}) if isinstance(result, dict) else {}
                        reliable._check_provenance(result, mode='independent_grade', **provenance)
                        result['response_hash'] = digest(state['responses'][job_id]['response'])
                        if result['response_hash'] != item['response_hash']:
                            raise ValueError('Grade does not reference the frozen saved answer.')
                        result['execution'] = {'kind': 'actual_llm_subagent', 'stage': 'supplemental_grade',
                                               'schedule_kind': item['kind'], 'fresh_context': True,
                                               'runner': 'Codex CLI ephemeral child via diagnostic observer',
                                               'isolation': 'Fresh cwd/context, tool events rejected; same OS user, not a hard filesystem jail.',
                                               'observer_source_sha256': frozen['observer_source_sha256']}
                        _validate_grades(result, jobs[job_id], state['responses'][job_id])
                        current = _load(grades_path) if grades_path.exists() else []
                        if any(r['job_id'] == job_id for r in current):
                            raise ValueError('First supplemental grade already saved.')
                        reliable._write_json(grades_path, current + [result])
                        entry['status'] = 'completed'
                        if 'total_tokens' not in entry['usage']:
                            journal['stopped'] = True
                            journal['stop_reason'] = 'Unknown reported usage.'
                            entry['usage_unknown'] = True
                    except ObservedWorkerFailure as exc:
                        entry.update(status='error', error=exc.diagnostics['code'], diagnostics=exc.diagnostics)
                        if exc.usage is not None:
                            entry['usage'] = exc.usage
                        else:
                            entry['usage_unknown'] = True
                        journal['stopped'] = True
                        journal['stop_reason'] = 'Native worker failure.'
                    except Exception as exc:
                        entry.update(status='error', error=type(exc).__name__)
                        entry.setdefault('usage', {})
                        if 'total_tokens' not in entry['usage']:
                            entry['usage_unknown'] = True
                        journal['stopped'] = True
                        journal['stop_reason'] = 'Rejected record or worker error.'
                        if result is not None:
                            rows = _load(rejected_path) if rejected_path.exists() else []
                            reliable._write_json(rejected_path, rows + [{'job_id': job_id, 'error': type(exc).__name__,
                                                                         'record_sha256': digest(result), 'record': result}])
                    entry['finished_at_unix'] = time.time()
                    reliable._write_json(journal_path, journal)
        journal['elapsed_seconds'] += time.monotonic() - started
        reliable._write_json(journal_path, journal)
    return supplemental_report(output)


def supplemental_report(output_dir):
    """Derive a combined report without touching the parent or its incomplete report."""
    output = Path(output_dir)
    frozen = _load(output / 'freeze.json')
    problems = _verify(output, frozen)
    evidence = output / 'parent-evidence'
    state = _load(evidence / 'comprehension/manifest.json')
    journal_path, grades_path = output / 'supplemental-journal.json', output / 'supplemental-grades.json'
    journal: dict[str, Any] = _load(journal_path) if journal_path.exists() else {'calls': [], 'stopped': False}
    supplemental = {r['job_id']: r for r in (_load(grades_path) if grades_path.exists() else [])}
    kinds = {item['job_id']: item['kind'] for item in frozen['scheduled']}
    if set(supplemental) - set(kinds) or set(supplemental) & set(state['grades']):
        problems.append('supplemental grades outside the frozen schedule')
    derived = output / 'combined-comprehension'
    combined = dict(state, grades={**state['grades'], **supplemental}, errors=[],
                    metadata={**state['metadata'], 'derived_from_parent': frozen['parent_dir'],
                              'supplement': 'grade-only; first answers and first grades unchanged'})
    reliable._write_json(derived / 'manifest.json', combined)
    task = reliable._retry_transient(continue_comprehension, derived)
    sources = {'first': len(state['grades']),
               'supplemental': sum(kinds[j] == 'missing' for j in supplemental),
               'supplemental_explicit_reattempt': sum(kinds[j] == 'reattempt' for j in supplemental)}
    sources['missing'] = len(state['jobs']) - sum(sources.values())
    calls = journal['calls']
    supplement_done = all(item['job_id'] in supplemental for item in frozen['scheduled'])
    supplemental_status = ('not_started' if not calls else 'completed' if supplement_done and not journal.get('stopped')
                           else 'stopped' if journal.get('stopped') else 'incomplete')
    combined_status = ('completed_with_supplement' if sources['missing'] == 0 and not problems
                       and task['status'] == 'completed' else 'incomplete')
    supplement_tokens = sum(c.get('usage', {}).get('total_tokens', 0) for c in calls)
    supplement_unknown = sum(c.get('usage_unknown', False) or c['status'] == 'running' for c in calls)
    privacy = _load(evidence / 'privacy/report.json')
    report = {
        'schema_version': 1, 'kind': 'grade_only_supplement',
        'primary_status': 'incomplete', 'parent_report_status': frozen['parent_status'],
        'supplemental_status': supplemental_status, 'combined_status': combined_status,
        'verification_problems': problems, 'grade_sources': sources,
        'reattempt': frozen['reattempt'], 'parent_failed_calls': frozen['parent_failed_calls'],
        'tokens': {'parent_reported': frozen['parent_reported_tokens'],
                   'parent_unknown_usage_calls': frozen['parent_unknown_usage_calls'],
                   'supplemental_reported': supplement_tokens, 'supplemental_unknown_usage_calls': supplement_unknown,
                   'reported_tokens_lower_bound': frozen['parent_reported_tokens'] + supplement_tokens,
                   'known_total': False if frozen['parent_unknown_usage_calls'] or supplement_unknown else True,
                   'note': LOWER_BOUND_NOTE},
        'supplemental_execution': {'calls': len(calls), 'stopped': journal.get('stopped', False),
                                   'stop_reason': journal.get('stop_reason'), 'budget': journal.get('budget'),
                                   'by_status': {s: sum(c['status'] == s for c in calls) for s in sorted({c['status'] for c in calls})},
                                   'failures': [{k: c[k] for k in ('job_id', 'error', 'diagnostics') if k in c}
                                                for c in calls if c['status'] == 'error']},
        'provenance': {k: frozen[k] for k in ('adapter_source_sha256', 'observer_source_sha256', 'cli_version', 'model',
                                              'reasoning_effort', 'grading_policy_sha256', 'parent_dir')},
        'task_response': task['metrics'], 'repeated_statistics': task.get('repeated_statistics'),
        'privacy': privacy['metrics'], 'privacy_breakdown': privacy.get('breakdown'),
        'adoption': {'decision': None, 'review_eligible': False,
                     'reason': 'Baseline supplement only; it cannot authorize adoption or review eligibility.'},
        'artifact_scope': reliable.ARTIFACT_SCOPE,
    }
    reliable._write_json(output / 'report.json', report)
    lines = ['# Grade-only supplement', '', f"Primary (parent) status: {report['primary_status']}",
             f"Supplemental status: {supplemental_status}; combined status: {combined_status}", '',
             LOWER_BOUND_NOTE, '', '```json',
             json.dumps({'grade_sources': sources, 'tokens': report['tokens']}, ensure_ascii=False, indent=2), '```', '']
    (output / 'summary.md').write_text('\n'.join(lines), encoding='utf8', newline='\n')
    return report
