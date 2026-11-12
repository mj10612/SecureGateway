"""Resume the frozen #309 replication with A/C/D only (owner-approved scope reduction).

Condition B (human-minimal masking) is removed from this run before measurement
because only #306 needed it and the owner asked to save Codex usage. The frozen
runner, manifest, rubric and decision are not modified: this wrapper imports
them, re-verifies the frozen inputs by hash, filters the in-memory job list to
A/C/D1, and reuses the runner's grading and decision code unchanged. Any stored
B responses stay on disk and are ignored.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_replication as R  # noqa: E402

ISSUE = 309
KEEP = ('A', 'C', 'D1')


def verify_frozen(plan, out):
    frozen = {}
    for name in ('rubric.json', 'decision.json'):
        plan_bytes = (plan / name).read_bytes()
        frozen_bytes = (out / ('frozen-' + name)).read_bytes()
        plan_hash = hashlib.sha256(plan_bytes).hexdigest()
        frozen_hash = hashlib.sha256(frozen_bytes).hexdigest()
        if plan_hash != frozen_hash:
            raise ValueError('FrozenInputMismatch')
        frozen[name] = plan_hash
    return frozen


def filter_to_keep(m):
    m['jobs'] = [j for j in m['jobs'] if j['arm'] in KEEP]
    for case in m['cases']:
        case['arms'] = {k: v for k, v in case['arms'].items() if k in KEEP}
        if set(case['arms']) != set(KEEP):
            raise ValueError('UnexpectedArmSet')
    return m


def interpret_kept(m, out, baseline):
    path = out / 'first-responses.jsonl'
    existing = R.read_rows(path)
    jobs = {x['request']['job_id']: x for x in m['jobs']}
    done = set()
    ignored = 0
    for row in existing:
        job = jobs.get(row.get('job_id'))
        if job is None:
            ignored += 1
            continue
        result = row.get('result', {})
        metadata = result.get('metadata', {})
        usage = result.get('usage', {})
        if (row['job_id'] in done or row.get('case_id') != job['case_id']
                or row.get('arm') != job['arm'] or row.get('status') != 'completed'
                or result.get('job_id') != row['job_id']
                or not isinstance(result.get('response'), str) or not result['response']
                or metadata.get('fresh_session') is not True
                or metadata.get('tool_events') != 0
                or any(type(usage.get(k)) is not int or usage[k] < 0
                       for k in ('input_tokens', 'output_tokens'))):
            raise ValueError('InvalidSavedResponse')
        done.add(row['job_id'])
    pending = [x for x in m['jobs'] if x['request']['job_id'] not in done]
    R.append_row(out / 'resume-log.jsonl', {
        'event': 'resume-drop-condition-b', 'run_identity': m['run_identity'],
        'saved_valid_responses': len(done), 'remaining_responses': len(pending),
        'stored_responses_outside_kept_arms': ignored,
        'kept_arms': list(KEEP),
        'timestamp_utc': __import__('time').strftime('%Y-%m-%dT%H:%M:%SZ', __import__('time').gmtime()),
    })
    for pos in range(0, len(pending), R.WORKERS):
        batch = pending[pos:pos + R.WORKERS]
        failed = False
        with __import__('concurrent.futures').futures.ThreadPoolExecutor(max_workers=R.WORKERS) as pool:
            futures = {pool.submit(R.observed, j['request'], baseline): j for j in batch}
            for f in __import__('concurrent.futures').futures.as_completed(futures):
                job = futures[f]
                row = {'job_id': job['request']['job_id'], 'case_id': job['case_id'],
                       'arm': job['arm'], **f.result()}
                R.append_row(path, row)
                failed |= row['status'] != 'completed'
        print('interpretation completed', min(pos + len(batch), len(pending)), 'of',
              len(pending), 'batch_failed', failed, flush=True)
        if failed:
            return False
    return True


def grades_kept(m, out, baseline):
    allrows = R.read_rows(out / 'first-responses.jsonl')
    jobs = {j['request']['job_id'] for j in m['jobs']}
    byjob = {x['job_id']: x for x in allrows if x['job_id'] in jobs}
    if len(byjob) != len(m['jobs']) or any(x['status'] != 'completed' for x in byjob.values()):
        return False
    path = out / 'first-grades.jsonl'
    prior = R.read_rows(path)
    done = set()
    cases = {x['case_id']: x for x in m['cases']}
    for row in prior:
        case = cases.get(row.get('case_id'))
        if not case or row['case_id'] in done or row.get('status') != 'completed':
            raise ValueError('InvalidSavedGrade')
        request, blind, responses = R.grade_request(m, case, byjob)
        attempts = row.get('attempts', [])
        if (not attempts or row.get('blind_labels') != blind
                or attempts[-1].get('status') != 'completed'
                or not R.quotes_valid(attempts[-1]['result'], responses)):
            raise ValueError('InvalidSavedGrade')
        expected = {x['id'] for x in request['criteria']}
        actual = [x['id'] for x in attempts[-1]['result']['grades']]
        if len(actual) != len(expected) or set(actual) != expected:
            raise ValueError('InvalidSavedGrade')
        done.add(row['case_id'])
    pending = [x for x in m['cases'] if x['case_id'] not in done]
    for pos in range(0, len(pending), R.WORKERS):
        batch = pending[pos:pos + R.WORKERS]
        failed = False

        def one(case):
            req, blind, responses = R.grade_request(m, case, byjob)
            r = R.observed(req, baseline)
            attempts = [r]
            if r['status'] == 'completed' and not R.quotes_valid(r['result'], responses):
                retry = dict(req)
                retry['job_id'] = R.sha([m['issue'], case['case_id'], 'regrade'])[:32]
                retry['messages'] = list(req['messages']) + [{
                    'role': 'user',
                    'content': ('The previous quote validation failed. Supply only exact '
                                'nonempty excerpts from the corresponding response for every verdict.')}]
                r = R.observed(retry, baseline)
                attempts.append(r)
            okay = r['status'] == 'completed' and R.quotes_valid(r['result'], responses)
            return {'case_id': case['case_id'], 'status': 'completed' if okay else 'ungraded',
                    'blind_labels': blind, 'attempts': attempts}

        with __import__('concurrent.futures').futures.ThreadPoolExecutor(max_workers=R.WORKERS) as pool:
            futures = {pool.submit(one, c): c for c in batch}
            for f in __import__('concurrent.futures').futures.as_completed(futures):
                row = f.result()
                R.append_row(path, row)
                failed |= row['status'] != 'completed'
        print('grading completed', min(pos + len(batch), len(pending)), 'of',
              len(pending), 'batch_failed', failed, flush=True)
        if failed:
            return False
    return True


def main():
    plan = R.ROOT / str(ISSUE) / R.PLAN
    out = R.ROOT / str(ISSUE) / R.OUT
    frozen = verify_frozen(plan, out)
    m = filter_to_keep(R.prepare(ISSUE))
    if len(m['cases']) != 93:
        raise ValueError('UnexpectedCaseCount')
    deviation = {
        'issue': ISSUE,
        'kind': 'approved pre-measurement deviation',
        'owner_decision': 'Drop condition B (human-minimal masking) to save Codex usage; only #306 needed it.',
        'condition_b_jobs_not_run': 93,
        'kept_arms': list(KEEP),
        'stored_condition_b_responses_retained_unused': sum(
            1 for r in R.read_rows(out / 'first-responses.jsonl') if r.get('arm') == 'B'),
        'frozen_inputs_sha256': frozen,
        'frozen_runner': 'plan/run_replication.py (unmodified)',
        'frozen_manifest': 'comprehension-replication/manifest.json (unmodified)',
        'decision_rule': 'unchanged; evaluated over A/C/D1 only',
        'timestamp_utc': __import__('time').strftime('%Y-%m-%dT%H:%M:%SZ', __import__('time').gmtime()),
    }
    from secure_gateway import evaluation
    evaluation.write_json(out / 'deviation-drop-condition-b.json', deviation)
    print('frozen inputs verified', json.dumps(frozen, sort_keys=True), flush=True)
    print('kept jobs', len(m['jobs']), 'cases', len(m['cases']), flush=True)
    baseline = R.token_baseline()
    if not interpret_kept(m, out, baseline):
        print('INCOMPLETE: interpretation failure; no grading performed.')
        return 1
    if not grades_kept(m, out, baseline):
        print('INCOMPLETE: ungraded case or grader failure.')
        return 1
    d = R.report(m, out)
    # Correct the usage/count fields so they describe the measured A/C/D1 arms only.
    kept_rows = [r for r in R.read_rows(out / 'first-responses.jsonl')
                 if r['job_id'] in {j['request']['job_id'] for j in m['jobs']}]
    d['interpretations'] = len(kept_rows)
    d['deviation'] = deviation
    d['condition_b'] = 'not measured (owner-approved scope reduction; stored B responses unused)'
    evaluation.write_json(out / 'report.json', d)
    print('candidate report status', d['status'], 'decisions',
          ','.join(v['decision'] for v in d['results'].values()))
    return 0 if d['status'] == 'completed' else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print('runner failure category', type(e).__name__)
        sys.exit(1)
