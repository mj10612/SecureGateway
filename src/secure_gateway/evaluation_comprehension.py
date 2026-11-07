"""Blind four-arm jobs, immutable first responses and independent grading."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import secrets
from tempfile import TemporaryDirectory
import time
import uuid

from secure_gateway.evaluation import at, digest, save_report, select_cases, write_json
from secure_gateway.evaluation_worker import execute_worker


def _jsonl(path, rows):
    path = Path(path)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
    if __import__('os').name != 'nt':
        path.chmod(0o600)


def prepare_comprehension(data, baseline, candidate, *, output_dir, model, profile='smoke', repeats=1, max_output_tokens=1024):
    from secure_gateway.evaluation import validate_corpus
    validate_corpus(data)
    if not isinstance(model, str) or not model or not 1 <= repeats <= 10 or not 64 <= max_output_tokens <= 8192:
        raise ValueError('Invalid model/repeat/output budget.')
    output_dir = Path(output_dir)
    if (output_dir / 'manifest.json').exists():
        raise ValueError('Prepared run already exists; resume or use a new directory.')
    for report in (baseline, candidate):
        if report.get('suite') != 'privacy' or report.get('status') != 'completed' or report['metadata']['corpus_hash'] != digest(data):
            raise ValueError('Completed compatible HTTP privacy reports are required.')
    if baseline['metadata']['settings_hash'] != candidate['metadata']['settings_hash']:
        raise ValueError('Incompatible privacy settings.')
    limit = {'smoke': 1, 'standard': 4, 'release': 8}[profile]
    cases = [c for c in select_cases(data, profile) if c['rubric']][:limit]
    if not cases:
        raise ValueError('No comprehension tasks in selection.')
    records = [{c['id']: c for c in r['cases']} for r in (baseline, candidate)]
    jobs = []
    for case in cases:
        if any(case['id'] not in arm or arm[case['id']]['status'] != 'completed' for arm in records):
            raise ValueError('Missing captured HTTP task.')
        for repeat in range(repeats):
            for variant in ('original', 'human', 'baseline', 'candidate'):
                text = (at(case['payload'], case['task_path']) if variant == 'original' else case['human_text'] if variant == 'human'
                        else at(records[variant == 'candidate'][case['id']]['outbound'], case['task_path']))
                payload = records[variant == 'candidate'][case['id']]['outbound']
                system = payload.get('system', payload.get('instructions', ''))
                if isinstance(system, list):
                    system = '\n'.join(s.get('text', '') for s in system)
                if not isinstance(system, str):
                    raise ValueError('Unsupported captured system instruction.')
                messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': text}]
                request = {'role': 'interpret', 'job_id': uuid.uuid4().hex, 'model': model,
                           'max_output_tokens': max_output_tokens, 'messages': messages}
                jobs.append({'job_id': request['job_id'], 'case_id': case['id'], 'variant': variant, 'repeat': repeat,
                             'request': request, 'input_hash': digest(request), 'original': at(case['payload'], case['task_path']),
                             'criteria': case['rubric'], 'language': case['language'], 'domain': case['domain']})
    secrets.SystemRandom().shuffle(jobs)
    state = {'schema_version': 1, 'jobs': jobs, 'responses': {}, 'grades': {}, 'errors': [], 'attempts': 0,
             'metadata': {**candidate['metadata'], 'profile': profile, 'model': model, 'repeats': repeats,
                          'worker_protocol': 1, 'baseline_code_sha': baseline['metadata']['code_sha'],
                          'candidate_code_sha': candidate['metadata']['code_sha'],
                          'same_engine_capture': baseline['run_id'] == candidate['run_id'],
                          'max_output_tokens': max_output_tokens,
                          'token_limit': 'Output byte guard and reported usage; provider hard cap unavailable for Codex CLI.',
                          'import_provenance': 'External records are caller-attested, not cryptographically verified.',
                          'isolation': 'Fresh context/cwd; same OS user, no hard filesystem jail.'}}
    write_json(output_dir / 'manifest.json', state)
    _jsonl(output_dir / 'interpret-jobs.jsonl', [j['request'] for j in jobs])
    return state


def _read_records(path):
    raw = Path(path).read_bytes()
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Response import exceeds limit.')
    rows = json.loads(raw)
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Import must be a JSON array of records.')
    if len({r.get('job_id') for r in rows}) != len(rows):
        raise ValueError('Duplicate imported job ids.')
    return rows


def _provenance(record, model):
    execution = record.get('execution', {})
    if (record.get('model') != model or execution.get('kind') != 'actual_llm_subagent'
            or execution.get('fresh_context') is not True or not execution.get('runner') or not execution.get('isolation')):
        raise ValueError('Actual fresh LLM subagent execution metadata is required.')


def _validate_response(record, job):
    _provenance(record, job['request']['model'])
    response = record.get('response')
    if not isinstance(response, str) or not response.strip() or len(response.encode()) > 4 * job['request']['max_output_tokens']:
        raise ValueError('Invalid or over-budget first response.')


def _validate_grades(record, job, response):
    if record.get('response_hash') != digest(response['response']):
        raise ValueError('Grade must reference the saved first response hash.')
    _provenance(record, job['request']['model'])
    grades = record.get('grades')
    expected = {g['id'] for g in job['criteria']}
    if (not isinstance(grades, list) or any(not isinstance(g, dict) for g in grades)
            or len(grades) != len(expected) or {g.get('id') for g in grades} != expected):
        raise ValueError('Grade criteria must exactly match the rubric.')
    if any(type(g.get('passed')) is not bool or not isinstance(g.get('evidence'), str) or not g['evidence'].strip() for g in grades):
        raise ValueError('Every criterion requires a boolean result and actual response evidence.')


def _grade_request(job, response):
    return {'role': 'grade', 'job_id': job['job_id'], 'model': job['request']['model'],
            'max_output_tokens': job['request']['max_output_tokens'], 'criteria': job['criteria'],
            'messages': [{'role': 'system', 'content': 'Grade the saved response against each supplied criterion. '
                          'Judge semantic correctness, actions, conditions and prohibitions. Opaque aliases need not reveal originals. '
                          'Do not improve or regenerate the response. Return JSON with grades [{id,passed,evidence}]. '
                          'Evidence must cite the actual response or explain its omission. Do not use tools.'},
                         {'role': 'user', 'content': json.dumps({'original': job['original'], 'criteria': job['criteria'],
                                                               'model_input': job['request']['messages'], 'response': response['response']}, ensure_ascii=False)}]}


def _metrics(rows):
    grades = [g for row in rows for g in row.get('grades', [])]
    total = sum(row['criteria_count'] for row in rows)
    graded = [row for row in rows if row.get('grades')]
    passed = sum(g['passed'] for g in grades)
    complete = len(graded) == len(rows)
    return {'status': 'measured' if complete else 'partially_measured' if grades else 'not_measured',
            'scheduled_requests': len(rows), 'responses_received': sum('response' in row for row in rows),
            'graded_requests': len(graded), 'missing_or_failed_requests': len(rows) - len(graded),
            'total_criteria': total, 'graded_criteria': len(grades), 'passed_criteria': passed,
            'accuracy': passed / total if complete and total else None,
            'observed_accuracy': passed / len(grades) if grades else None,
            'all_required_passed': sum(all(g['passed'] for g in row['grades']) for row in graded),
            'intent_passed': sum(g['passed'] for row in graded for g in row['grades'] if g['id'] == 'intent')}


def continue_comprehension(output_dir, *, responses_path=None, grades_path=None, command=None,
                           max_calls=64, max_seconds=300, max_tokens=65536):
    output_dir = Path(output_dir)
    state = json.loads((output_dir / 'manifest.json').read_text(encoding='utf-8'))
    jobs = {j['job_id']: j for j in state['jobs']}
    begin = time.monotonic()
    for kind, path in (('responses', responses_path), ('grades', grades_path)):
        if path is None:
            continue
        staged = deepcopy(state[kind])
        for record in _read_records(path):
            job_id = record.get('job_id')
            if job_id not in jobs:
                raise ValueError('Unknown imported job id.')
            if kind == 'responses':
                _validate_response(record, jobs[job_id])
                if job_id in staged and staged[job_id] != record:
                    raise ValueError('Cannot replace a saved first response.')
            else:
                if job_id not in state['responses']:
                    raise ValueError('Cannot grade without a saved response.')
                _validate_grades(record, jobs[job_id], state['responses'][job_id])
                if job_id in staged and staged[job_id] != record:
                    raise ValueError('Cannot replace saved grades.')
            staged[job_id] = record
        state[kind] = staged
        write_json(output_dir / 'manifest.json', state)

    if command:
        # Interpretation phase is persisted before any grader is invoked.
        for role in ('interpret', 'grade'):
            for job_id, job in jobs.items():
                target = 'responses' if role == 'interpret' else 'grades'
                if job_id in state[target] or role == 'grade' and job_id not in state['responses']:
                    continue
                elapsed = time.monotonic() - begin
                reported_tokens = sum(r.get('usage', {}).get('total_tokens', 0) for name in ('responses', 'grades') for r in state[name].values())
                if (state['attempts'] >= max_calls or elapsed >= max_seconds or reported_tokens >= max_tokens
                        or state['metadata'].get('token_usage_unknown')):
                    break
                request = job['request'] if role == 'interpret' else _grade_request(job, state['responses'][job_id])
                state['attempts'] += 1
                try:
                    with TemporaryDirectory(prefix='secure-gateway-blind-worker-') as cwd:
                        record = execute_worker(command, request, timeout=max_seconds - elapsed, cwd=Path(cwd))
                    record['execution'] = {'kind': 'actual_llm_subagent', 'fresh_context': True, 'runner': command[0],
                                           'isolation': 'New empty cwd/context; same OS user, no hard filesystem jail.'}
                    if role == 'interpret':
                        _validate_response(record, job)
                    else:
                        record['response_hash'] = digest(state['responses'][job_id]['response'])
                        _validate_grades(record, job, state['responses'][job_id])
                    state[target][job_id] = record
                    if 'total_tokens' not in record.get('usage', {}):
                        state['metadata']['token_usage_unknown'] = True
                except (ValueError, OSError) as exc:
                    state['errors'].append({'job_id': job_id, 'role': role, 'error': type(exc).__name__})
                    # A rejected/failed inference may still consume tokens.
                    # Without trusted usage, stop rather than reset its cost to 0.
                    state['metadata']['token_usage_unknown'] = True
                write_json(output_dir / 'manifest.json', state)

    grade_jobs = []
    rows = []
    for job_id, job in jobs.items():
        row = {'id': f"{job['case_id']}:{job['variant']}:{job['repeat']}",
               **{k: job[k] for k in ('job_id', 'case_id', 'variant', 'repeat', 'language', 'domain')},
               'criteria_count': len(job['criteria']), 'input_hash': job['input_hash'], 'status': 'not_measured'}
        if job_id in state['responses']:
            response = state['responses'][job_id]
            row.update(response=response['response'], response_hash=digest(response['response']), execution=response['execution'], status='ungraded')
            if job_id in state['grades']:
                row.update(grades=state['grades'][job_id]['grades'], status='completed')
            else:
                grade_jobs.append({**_grade_request(job, response), 'response_hash': row['response_hash']})
        rows.append(row)
    if grade_jobs:
        _jsonl(output_dir / 'grade-jobs.jsonl', grade_jobs)
    elif (output_dir / 'grade-jobs.jsonl').exists():
        _jsonl(output_dir / 'grade-jobs.jsonl', [])
    rows.sort(key=lambda row: row['id'])
    metrics = _metrics(rows)
    report = {'schema_version': 1, 'suite': 'comprehension', 'status': 'completed' if metrics['status'] == 'measured' else 'incomplete',
              'metadata': state['metadata'], 'cases': rows, 'errors': state['errors'], 'attempts': state['attempts'],
              'metrics': {'privacy': {'status': 'measured_separately_in_HTTP_reports'}, 'comprehension': metrics,
                          'variants': {v: _metrics([r for r in rows if r['variant'] == v]) for v in ('original', 'human', 'baseline', 'candidate')}}}
    paired: dict = {'improved': [], 'regressed': [], 'unchanged': [], 'unmeasured_pairs': 0}
    grouped = {(r['case_id'], r['repeat'], r['variant']): r for r in rows}
    for key in {(r['case_id'], r['repeat']) for r in rows}:
        a, b = grouped[key + ('baseline',)], grouped[key + ('candidate',)]
        if not a.get('grades') or not b.get('grades'):
            paired['unmeasured_pairs'] += 1
            continue
        ag = {g['id']: g['passed'] for g in a['grades']}
        for grade in b['grades']:
            name = 'unchanged' if ag[grade['id']] == grade['passed'] else 'improved' if grade['passed'] else 'regressed'
            paired[name].append({'case_id': key[0], 'repeat': key[1], 'criterion': grade['id']})
    report['paired'] = paired
    report['elapsed_seconds'] = time.monotonic() - begin
    save_report(report, output_dir)
    return report
