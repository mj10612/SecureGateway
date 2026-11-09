"""Frozen multilingual task/PII cohorts; holdout-only review, never adoption."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from hashlib import sha256
import inspect
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import time
import uuid

from secure_gateway.encrypted_session import session_file_lock
from secure_gateway.engine.natural_languages import SUPPORTED_LANGUAGES
from secure_gateway.evaluation import at, compare_reports, digest, load_corpus, run_privacy, write_json
from secure_gateway import evaluation_codex_worker as _adapter_module
from secure_gateway.evaluation_diagnostics import diagnostic_worker as run_codex_worker, ObservedWorkerFailure
from secure_gateway.evaluation_comprehension import (
    GRADING_POLICY_V2, _grade_request, _validate_grades, _validate_response, continue_comprehension, prepare_comprehension,
)
from secure_gateway.evaluation_worker import capture_worker_process, validate_result


LANGUAGES = SUPPORTED_LANGUAGES - {'auto'}
SPLITS = ('development', 'holdout')
CRITERIA = {'intent', 'conditions', 'prohibition', 'scope'}
FREEZE_SCHEMA = 2
# Net per-criterion regressions on these criteria block review eligibility.
BLOCKING_CRITERIA = ('conditions', 'prohibition')
REQUIRED_FREEZE_KEYS = (
    'schema_version', 'prepared', 'split', 'model', 'repeats', 'reasoning_effort', 'max_output_tokens',
    'grading_policy_version', 'grading_policy_sha256', 'corpus_byte_hashes', 'adapter_source_sha256',
    'cli_version', 'jobs_sha256', 'reference_audit_verified', 'reference_audit_evidence', 'baseline_evidence',
    'holdout_use',
)
AUDIT_FILES = ('freeze.json', 'requests.json', 'first-grades.json', 'journal.json', 'report.json')
BASELINE_FILES = ('freeze.json', 'task-capture/report.json', 'privacy/report.json')
EXECUTION_NOTE = ('Budgets are checked before each batch. Calls already in flight (at most the worker count) '
                  'can exceed call/token/time budgets; the adapter has a fixed per-call timeout and the provider '
                  'offers no hard token cap. Reported usage is actual CLI-reported usage only.')
ARTIFACT_SCOPE = ('Capture reports retain synthetic alias-to-original source maps for owner-side grading. They are '
                  'synthetic evaluation artifacts for owner review, not production privacy data or shareable results.')


def _retry_transient(function, *args, attempts=6, **kwargs):
    """Retry an idempotent file transaction on transient Windows sharing violations.

    Antivirus/indexer handles can briefly block an atomic replace. Without a retry,
    a failed journal or manifest write would stop the run permanently. Other errors,
    and every error on other platforms, are re-raised immediately.
    """
    for attempt in range(attempts):
        try:
            return function(*args, **kwargs)
        except PermissionError:
            if os.name != 'nt' or attempt == attempts - 1:
                raise
            time.sleep(0.05 * 2 ** attempt)


def _write_json(path, value):
    return _retry_transient(write_json, path, value)


def grading_policy_hash():
    return sha256(GRADING_POLICY_V2.encode('utf8')).hexdigest()


def adapter_hash():
    # Hash the adapter module itself, not whatever callable is currently bound.
    return sha256(Path(inspect.getfile(_adapter_module)).read_bytes()).hexdigest()


def _file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def native_cli_version():
    """Discover the native Codex CLI version without any model inference."""
    codex = shutil.which('codex')
    if codex is None:
        raise ValueError('Codex CLI is not installed.')
    env = {k: v for k, v in os.environ.items()
           if k in {'PATH', 'HOME', 'USERPROFILE', 'CODEX_HOME', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'TMPDIR'}}
    with TemporaryDirectory(prefix='secure-gateway-cli-version-') as directory:
        version = capture_worker_process([codex, '--version'], b'', timeout=10, cwd=Path(directory), env=env).stdout
    text = version.decode('utf-8').strip()
    if not text or len(text) > 200:
        raise ValueError('Codex CLI returned an invalid version.')
    return text


def load_bundle(directory):
    """Validate both splits without printing private text or holdout questions."""
    directory = Path(directory)
    data, hashes, summaries = {}, {}, {}
    ownership: dict[str, str] = {}
    ids: set[str] = set()
    for split in SPLITS:
        for kind in ('tasks', 'privacy'):
            name = f'{kind}-{split}.json'
            path = directory / name
            corpus = load_corpus(path)
            cases = corpus['cases']
            if {c['language'] for c in cases} != LANGUAGES:
                raise ValueError('Every corpus must cover all 17 supported languages.')
            for case in cases:
                if case['split'] != split or case['id'] in ids:
                    raise ValueError('Split mismatch or duplicate corpus case identity.')
                ids.add(case['id'])
                for key in ('template_group', 'family'):
                    family = case.get(key)
                    if not isinstance(family, str) or not family:
                        raise ValueError('Missing independent family provenance.')
                    old = ownership.setdefault(key + ':' + family, split)
                    if old != split:
                        raise ValueError('A family/translation crosses development and holdout.')
                if kind == 'tasks':
                    if {r['id'] for r in case['rubric']} != CRITERIA or len(case['rubric']) != 4:
                        raise ValueError('Each task requires exactly the four task-response criteria.')
                    if not isinstance(case.get('reference_response'), str) or not case['reference_response'].strip():
                        raise ValueError('Each task requires an owner-only full-credit reference.')
                elif case['rubric'] or len(case['secrets']) < 5 or not case['public']:
                    raise ValueError('Privacy scenarios need five private occurrences, public controls and no task rubric.')
            for language in LANGUAGES:
                selected = [c for c in cases if c['language'] == language]
                if kind == 'tasks' and len(selected) != 1:
                    raise ValueError('One task per language yields the declared 68-point ceiling.')
                if kind == 'privacy' and (len(selected) < 6 or {c.get('language_mode', 'auto') for c in selected} != {'auto', 'explicit'}):
                    raise ValueError('Privacy coverage requires six scenarios and both language modes per language.')
            data[name] = corpus
            hashes[name] = sha256(path.read_bytes()).hexdigest()
            summaries[name] = {'cases': len(cases), 'languages': sorted({c['language'] for c in cases}),
                               'private_occurrences': sum(len(c['secrets']) for c in cases),
                               'public_spans': sum(len(c['public']) for c in cases),
                               'max_task_points_per_repeat': sum(len(c['rubric']) for c in cases)}
    return {'corpora': data, 'hashes': hashes, 'summaries': summaries}


# --- Provenance of returned worker records -----------------------------------------------------

def _check_provenance(record, *, model, reasoning_effort, adapter, cli_version, mode):
    """Every returned record must come from the frozen model/effort/adapter/native CLI."""
    meta = record.get('metadata')
    if not isinstance(meta, dict):
        raise ValueError('Worker record lacks provenance metadata.')
    expected = {'requested_model': model, 'requested_reasoning_effort': reasoning_effort,
                'adapter_source_sha256': adapter, 'task_response_mode': mode, 'tool_events': 0}
    if cli_version is not None:
        expected['cli_version'] = cli_version
    for key, value in expected.items():
        if meta.get(key) != value:
            raise ValueError('Worker record provenance differs from the freeze: ' + key)
    if record.get('model') != model:
        raise ValueError('Worker record model differs from the freeze.')


# --- Reference audit ---------------------------------------------------------------------------

def _reference_requests(bundle, split, model, reasoning_effort):
    """Deterministic reference-audit grade requests reconstructed from the frozen bundle."""
    requests = []
    for case in bundle['corpora'][f'tasks-{split}.json']['cases']:
        job = {'job_id': digest({'case': case['id'], 'audit': 'reference'}), 'request': {'model': model, 'max_output_tokens': 2048,
               'messages': [], 'reasoning_effort': reasoning_effort}, 'original': at(case['payload'], case['task_path']),
               'criteria': case['rubric'], 'grading_policy_version': 2,
               'grading_context': {k: case[k] for k in ('rubric_notes', 'missing_original_facts') if k in case}}
        requests.append({'case_id': case['id'], 'language': case['language'],
                         'request': _grade_request(job, {'response': case['reference_response']})})
    return requests


def verify_reference_audit(audit_dir, bundle, *, split, model, reasoning_effort):
    """Independently recompute an audit from its saved records; never trust report.json alone.

    Works for audits that predate request-hash/CLI freezing: requests are compared with
    the deterministic reconstruction from the frozen bundle and current grading policy.
    """
    audit_dir = Path(audit_dir)
    missing = [name for name in AUDIT_FILES if not (audit_dir / name).is_file()]
    if missing:
        raise ValueError('Reference audit evidence is incomplete: ' + ', '.join(missing))
    evidence = {name: _file_hash(audit_dir / name) for name in AUDIT_FILES}
    frozen = json.loads((audit_dir / 'freeze.json').read_bytes())
    if (frozen.get('corpus_byte_hashes') != bundle['hashes'] or frozen.get('split') != split
            or frozen.get('model') != model or frozen.get('reasoning_effort') != reasoning_effort
            or frozen.get('grading_policy_version') != 2 or frozen.get('grading_policy_sha256') != grading_policy_hash()):
        raise ValueError('Reference audit does not match this corpus/configuration.')
    if frozen.get('adapter_source_sha256') != adapter_hash():
        raise ValueError('Reference audit adapter differs from the current adapter.')
    if 'requests_sha256' in frozen and frozen['requests_sha256'] != evidence['requests.json']:
        raise ValueError('Reference audit requests changed after preparation.')
    requests = json.loads((audit_dir / 'requests.json').read_bytes())
    expected = _reference_requests(bundle, split, model, reasoning_effort)
    if digest(requests) != digest(expected):
        raise ValueError('Reference audit requests differ from the deterministic reconstruction.')
    by_id = {item['request']['job_id']: item['request'] for item in expected}
    results = json.loads((audit_dir / 'first-grades.json').read_bytes())
    if not isinstance(results, list) or any(not isinstance(r, dict) for r in results):
        raise ValueError('Reference audit grades must be a list of records.')
    ids = [r.get('job_id') for r in results]
    if len(set(ids)) != len(ids) or set(ids) - set(by_id):
        raise ValueError('Reference audit grades have duplicate or unknown job ids.')
    cli_versions = set()
    for record in results:
        request = by_id[record['job_id']]
        validate_result(deepcopy(record), request)
        _check_provenance(record, model=model, reasoning_effort=reasoning_effort,
                          adapter=frozen['adapter_source_sha256'], cli_version=frozen.get('cli_version'),
                          mode='independent_grade')
        cli_versions.add(record['metadata'].get('cli_version'))
    if len(cli_versions) > 1 or None in cli_versions or '' in cli_versions:
        raise ValueError('Reference audit records do not share one native CLI version.')
    journal = json.loads((audit_dir / 'journal.json').read_bytes())
    calls = journal.get('calls', [])
    budget = journal.get('budget', {})
    by_result = {r['job_id']: r for r in results}
    completed = [c for c in calls if c.get('status') == 'completed']
    if ({c['job_id'] for c in completed} != set(by_result) or len(completed) != len(results)
            or any(c.get('usage') != by_result[c['job_id']].get('usage') for c in completed)):
        raise ValueError('Reference audit journal does not account for exactly its saved grades.')
    reported = sum(c.get('usage', {}).get('total_tokens', 0) for c in calls)
    unknown = sum('total_tokens' not in c.get('usage', {}) for c in calls)
    if len(calls) > budget.get('max_calls', 0) or reported > budget.get('max_reported_tokens', 0):
        raise ValueError('Reference audit exceeded its recorded budget.')
    total = sum(len(request['criteria']) for request in by_id.values())
    passed = sum(g['passed'] for r in results for g in r['grades'])
    complete = (len(results) == len(expected) and len(calls) == len(completed) and not unknown
                and not journal.get('stopped'))
    status = 'passed' if complete and passed == total else 'needs_review' if complete else 'incomplete'
    report = json.loads((audit_dir / 'report.json').read_bytes())
    if (report.get('status') != status or report.get('total_criteria') != total
            or report.get('passed_criteria') != passed or report.get('graded_references') != len(results)):
        raise ValueError('Reference audit report disagrees with its recomputed grades.')
    return {'verified': status == 'passed' and total == passed == 4 * len(LANGUAGES),
            'recomputed': {'status': status, 'total_criteria': total, 'passed_criteria': passed,
                           'graded_references': len(results), 'calls': len(calls),
                           'reported_tokens': reported, 'unknown_usage_calls': unknown},
            'cli_versions': sorted(cli_versions), 'evidence_sha256': evidence,
            'requests_reconstructed': True,
            'predates_request_and_cli_freeze': 'requests_sha256' not in frozen or 'cli_version' not in frozen,
            'scope': 'Attainable-rubric reference audit, recomputed from saved records; not a comprehension score.'}


# --- Holdout use ledger ------------------------------------------------------------------------

def holdout_ledger_path(data_dir):
    """Durable ledger beside (not inside) the frozen data directory."""
    data_dir = Path(data_dir).resolve()
    return data_dir.parent / (data_dir.name + '.holdout-ledger.json')


def _holdout_key(bundle):
    return digest({name: bundle['hashes'][name] for name in ('tasks-holdout.json', 'privacy-holdout.json')})


def _entry_hash(entry):
    return digest({k: v for k, v in entry.items() if k != 'entry_sha256'})


def read_holdout_ledger(path):
    path = Path(path)
    if not path.exists():
        return []
    entries = json.loads(path.read_bytes())
    previous = None
    if not isinstance(entries, list):
        raise ValueError('Holdout ledger is malformed.')
    for entry in entries:
        if (not isinstance(entry, dict) or entry.get('previous_sha256') != previous
                or entry.get('entry_sha256') != _entry_hash(entry)):
            raise ValueError('Holdout ledger chain is broken; it is append-only evidence.')
        previous = entry['entry_sha256']
    return entries


def _package_source_hash():
    package = Path(inspect.getfile(compare_reports)).parent
    return digest({str(p.relative_to(package)): sha256(p.read_bytes()).hexdigest()
                   for p in sorted(package.rglob('*')) if p.is_file() and p.suffix in {'.py', '.json'}})


def _candidate_uses(entries, key):
    return [e for e in entries if e['holdout_key'] == key and e['kind'] == 'candidate']


def _append_holdout_use(path, entry):
    path = Path(path)
    with session_file_lock(path.with_name(path.name + '.lock')):
        entries = read_holdout_ledger(path)
        prior = _candidate_uses(entries, entry['holdout_key'])
        entry = {**entry, 'prior_candidate_uses': len(prior),
                 'first_candidate': entry['kind'] == 'candidate' and not prior,
                 'previous_sha256': entries[-1]['entry_sha256'] if entries else None}
        if entry['kind'] == 'candidate' and prior and not entry.get('reuse_reason'):
            raise ValueError('Holdout already used by a candidate; record an explicit reuse reason.')
        entry['entry_sha256'] = _entry_hash(entry)
        _write_json(path, entries + [entry])
    return entry


def _holdout_use_status(frozen):
    """Review requires this run to be the ledger's first candidate use of the holdout."""
    use = frozen.get('holdout_use')
    if not use:
        return False, 'No holdout use recorded.'
    try:
        entries = read_holdout_ledger(frozen['holdout_ledger'])
    except (ValueError, OSError, KeyError) as exc:
        return False, 'Holdout ledger unavailable: ' + type(exc).__name__
    candidates = _candidate_uses(entries, use['holdout_key'])
    if use['kind'] != 'candidate' or not candidates or candidates[0]['entry_sha256'] != use['entry_sha256']:
        return False, 'Not the first recorded candidate use of this holdout.'
    return True, 'First recorded candidate use.'


# --- Freeze verification -----------------------------------------------------------------------

def _verify_freeze(output, frozen, *, check_native_cli=False):
    """Return problems with a prepared run; every check is mandatory."""
    output = Path(output)
    problems = [f'missing freeze key: {key}' for key in REQUIRED_FREEZE_KEYS if key not in frozen]
    if problems:
        return problems
    if frozen['schema_version'] != FREEZE_SCHEMA or frozen['prepared'] is not True:
        return ['freeze is not a completed preparation']
    if frozen['grading_policy_sha256'] != grading_policy_hash():
        problems.append('grading policy changed')
    if frozen['adapter_source_sha256'] != adapter_hash():
        problems.append('adapter changed')
    try:
        if load_bundle(output / 'corpora')['hashes'] != frozen['corpus_byte_hashes']:
            problems.append('frozen corpus bytes changed')
    except (ValueError, OSError, KeyError, TypeError):
        problems.append('frozen corpus unreadable')
    try:
        if digest(json.loads((output / 'comprehension/manifest.json').read_bytes())['jobs']) != frozen['jobs_sha256']:
            problems.append('frozen jobs changed')
    except (ValueError, OSError, KeyError):
        problems.append('frozen jobs unreadable')
    for group, folder in (('baseline_evidence', 'baseline-evidence'), ('reference_audit_evidence', 'reference-audit-evidence')):
        for name, value in (frozen[group] or {}).items():
            path = output / folder / name
            if not path.is_file() or _file_hash(path) != value:
                problems.append(f'{group} changed: {name}')
    if check_native_cli:
        try:
            if native_cli_version() != frozen['cli_version']:
                problems.append('native CLI version changed')
        except (ValueError, OSError):
            problems.append('native CLI unavailable')
    return problems


# --- Preparation --------------------------------------------------------------------------------

def prepare_reliable(data_dir, output_dir, *, split='holdout', model='gpt-6.1-sol', repeats=3,
                     reasoning_effort='medium', max_output_tokens=2048, baseline_dir=None, max_seconds=1200,
                     reference_audit_dir=None, holdout_ledger=None, holdout_reuse_reason=None):
    if split not in SPLITS or type(repeats) is not int or not 3 <= repeats <= 10:
        raise ValueError('Select a development/holdout split and at least three repeats.')
    bundle = load_bundle(data_dir)
    cli_version = native_cli_version()
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new empty output directory; frozen runs cannot be overwritten.')
    audit = None
    if reference_audit_dir:
        audit = verify_reference_audit(reference_audit_dir, bundle, split=split, model=model, reasoning_effort=reasoning_effort)
        if not audit['verified']:
            raise ValueError('Reference-response audit has not established attainable full credit.')
        if audit['cli_versions'] != [cli_version]:
            raise ValueError('Reference audit used a different native CLI version.')
    prior = None
    if baseline_dir:
        previous = Path(baseline_dir)
        prior = json.loads((previous / 'freeze.json').read_bytes())
        problems = _verify_freeze(previous, prior)
        if problems:
            raise ValueError('Baseline run is not an intact frozen preparation: ' + '; '.join(problems))
        for key in ('split', 'model', 'repeats', 'reasoning_effort', 'max_output_tokens', 'grading_policy_version',
                    'grading_policy_sha256', 'corpus_byte_hashes'):
            current = {'split': split, 'model': model, 'repeats': repeats, 'reasoning_effort': reasoning_effort,
                       'max_output_tokens': max_output_tokens, 'grading_policy_version': 2,
                       'grading_policy_sha256': grading_policy_hash(), 'corpus_byte_hashes': bundle['hashes']}[key]
            if prior[key] != current:
                raise ValueError('Baseline cohort/configuration differs: ' + key)
    ledger_path = Path(holdout_ledger) if holdout_ledger else holdout_ledger_path(data_dir)
    kind = 'candidate' if baseline_dir else 'baseline'
    if split == 'holdout' and kind == 'candidate' and not holdout_reuse_reason:
        if _candidate_uses(read_holdout_ledger(ledger_path), _holdout_key(bundle)):
            raise ValueError('Holdout already used by a candidate; record an explicit reuse reason.')

    output.mkdir(parents=True, exist_ok=True)
    for name in bundle['corpora']:
        destination = output / 'corpora' / name
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes((Path(data_dir) / name).read_bytes())
    baseline_evidence = {}
    if baseline_dir:
        for name in BASELINE_FILES:
            destination = output / 'baseline-evidence' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((Path(baseline_dir) / name).read_bytes())
            baseline_evidence[name] = _file_hash(destination)
    audit_evidence = {}
    if reference_audit_dir:
        for name in AUDIT_FILES:
            destination = output / 'reference-audit-evidence' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((Path(reference_audit_dir) / name).read_bytes())
            audit_evidence[name] = _file_hash(destination)
        if audit is None or audit_evidence != audit['evidence_sha256']:
            raise ValueError('Reference audit evidence changed while it was copied.')
    frozen = {'schema_version': FREEZE_SCHEMA, 'prepared': False, 'split': split, 'model': model, 'repeats': repeats,
              'reasoning_effort': reasoning_effort, 'max_output_tokens': max_output_tokens,
              'grading_policy_version': 2, 'corpus_byte_hashes': bundle['hashes'], 'coverage': bundle['summaries'],
              'grading_policy_sha256': grading_policy_hash(), 'adapter_source_sha256': adapter_hash(),
              'cli_version': cli_version, 'requires_reference_audit': True,
              'reference_audit_verified': bool(audit and audit['verified']),
              'reference_audit_root': str(Path(reference_audit_dir).resolve()) if reference_audit_dir else None,
              'reference_audit_verification': audit, 'reference_audit_evidence': audit_evidence,
              'baseline_root': str(Path(baseline_dir).resolve()) if baseline_dir else None,
              'baseline_evidence': baseline_evidence, 'holdout_use': None, 'holdout_ledger': None,
              'scope': 'Synthetic fresh task responses + loopback privacy, not real-world risk estimates.'}
    _write_json(output / 'freeze.json', frozen)  # Incomplete marker before any capture or model call.
    if split == 'holdout':
        frozen['holdout_ledger'] = str(ledger_path.resolve())
        frozen['holdout_use'] = _append_holdout_use(ledger_path, {
            'use_id': uuid.uuid4().hex, 'kind': kind, 'holdout_key': _holdout_key(bundle),
            'output_dir': str(output.resolve()), 'prepared_at_unix': time.time(),
            'package_source_hash': _package_source_hash(),
            'baseline_freeze_sha256': baseline_evidence.get('freeze.json'),
            'reuse_reason': holdout_reuse_reason})
        _write_json(output / 'freeze.json', frozen)
    tasks = bundle['corpora'][f'tasks-{split}.json']
    privacy = run_privacy(bundle['corpora'][f'privacy-{split}.json'], output_dir=output / 'privacy',
                          profile='release', max_seconds=max_seconds)
    task_capture = run_privacy(tasks, output_dir=output / 'task-capture', profile='release', max_seconds=max_seconds)
    if privacy['status'] != 'completed' or task_capture['status'] != 'completed':
        _write_json(output / 'report.json', {'status': 'incomplete', 'reason': 'HTTP capture incomplete',
                                           'privacy_status': privacy['status'], 'task_capture_status': task_capture['status']})
        return {'status': 'incomplete'}
    base = task_capture
    variants: tuple[str, ...] = ('original', 'human', 'baseline')
    if baseline_dir:
        evidence = output / 'baseline-evidence'
        base = json.loads((evidence / 'task-capture/report.json').read_bytes())
        old_privacy = json.loads((evidence / 'privacy/report.json').read_bytes())
        _write_json(output / 'privacy-comparison.json', compare_reports(old_privacy, privacy))
        _write_json(output / 'task-privacy-comparison.json', compare_reports(base, task_capture))
        variants = ('original', 'human', 'baseline', 'candidate')
    prepare_comprehension(tasks, base, task_capture, output_dir=output / 'comprehension', model=model,
                          profile='release', repeats=repeats, max_output_tokens=max_output_tokens,
                          all_tasks=True, variants=variants, grading_policy_version=2, reasoning_effort=reasoning_effort)
    state = json.loads((output / 'comprehension/manifest.json').read_bytes())
    frozen.update(jobs_sha256=digest(state['jobs']), prepared=True)
    _write_json(output / 'freeze.json', frozen)  # Completed preparation marker is written last.
    return joint_report(output)


# --- Reporting ----------------------------------------------------------------------------------

def _criterion_regressions(task):
    paired = task.get('paired') or {}
    counts: dict[str, dict[str, int]] = {}
    for name in ('improved', 'regressed'):
        for item in paired.get(name, []):
            counts.setdefault(item['criterion'], {'improved': 0, 'regressed': 0})[name] += 1
    for value in counts.values():
        value['net_regressed'] = value['regressed'] - value['improved']
    blocking = sorted(c for c in BLOCKING_CRITERIA if counts.get(c, {}).get('net_regressed', 0) > 0)
    return counts, blocking


def _execution_summary(output):
    path = Path(output) / 'execution-journal.json'
    rejected_path = Path(output) / 'comprehension/rejected-records.json'
    rejected = json.loads(rejected_path.read_bytes()) if rejected_path.exists() else []
    if not path.exists():
        return {'status': 'not_started', 'rejected_records': len(rejected), 'note': EXECUTION_NOTE}
    journal = json.loads(path.read_bytes())
    calls = journal['calls']
    return {'status': 'stopped' if journal.get('stopped') else 'open', 'stop_reason': journal.get('stop_reason'),
            'budget': journal['budget'], 'calls': len(calls),
            'by_status': {s: sum(c['status'] == s for c in calls) for s in sorted({c['status'] for c in calls})},
            'reported_tokens': sum(c.get('usage', {}).get('total_tokens', 0) for c in calls),
            'unknown_usage_calls': sum('total_tokens' not in c.get('usage', {}) for c in calls),
            'max_in_flight': max((b['in_flight'] for b in journal.get('batches', [])), default=0),
            'rejected_records': len(rejected), 'elapsed_seconds': journal.get('elapsed_seconds'), 'note': EXECUTION_NOTE}


def joint_report(output_dir):
    output = Path(output_dir)
    frozen = json.loads((output / 'freeze.json').read_bytes())
    freeze_problems = _verify_freeze(output, frozen)
    privacy = json.loads((output / 'privacy/report.json').read_bytes())
    task_capture = json.loads((output / 'task-capture/report.json').read_bytes())
    task = _retry_transient(continue_comprehension, output / 'comprehension')
    complete = all(r['status'] == 'completed' for r in (privacy, task_capture, task)) and not freeze_problems
    comparison_path = output / 'privacy-comparison.json'
    comparison = json.loads(comparison_path.read_bytes()) if comparison_path.exists() else None
    task_comparison_path = output / 'task-privacy-comparison.json'
    task_comparison = json.loads(task_comparison_path.read_bytes()) if task_comparison_path.exists() else None
    integrity_ok = True
    for capture in (privacy, task_capture):
        integrity = capture['metrics']['integrity']
        integrity_ok &= all(integrity.get(k) == len(capture['cases'])
                            for k in ('semantic_roundtrip_passed', 'replay_passed'))
        integrity_ok &= all(integrity.get(k) is True for k in ('session_isolation', 'snapshot_restart'))
    stats = task.get('repeated_statistics') or {}
    paired = stats.get('paired', [])
    gain = any(p['split'] == 'holdout' and p['language'] is None and p['eligible']
               and p['statistics']['passed_criteria_diff']['mean'] > 0 for p in paired)
    regressions, blocking = _criterion_regressions(task)
    first_use, use_reason = _holdout_use_status(frozen) if frozen.get('split') == 'holdout' else (False, 'Development split.')
    review_eligible = bool(complete and frozen.get('split') == 'holdout'
                           and comparison is not None and not comparison['regression']
                           and task_comparison is not None and not task_comparison['regression']
                           and frozen.get('reference_audit_verified') and integrity_ok and gain
                           and stats.get('holdout_eligibility', {}).get('paired_eligible')
                           and first_use and not blocking)
    report = {'schema_version': 1, 'status': 'completed' if complete else 'incomplete', 'freeze': frozen,
              'freeze_problems': freeze_problems,
              'privacy': privacy['metrics'], 'privacy_breakdown': privacy['breakdown'],
              'task_payload_privacy': task_capture['metrics'], 'task_response': task['metrics'],
              'repeated_statistics': task.get('repeated_statistics'), 'privacy_comparison': comparison,
              'task_privacy_comparison': task_comparison, 'execution': _execution_summary(output),
              'artifact_scope': ARTIFACT_SCOPE,
              'adoption': {'decision': None, 'review_eligible': review_eligible,
                           'integrity_passed': bool(integrity_ok), 'observed_task_gain': gain,
                           'holdout_first_candidate_use': first_use, 'holdout_use_status': use_reason,
                           'criterion_regressions': regressions, 'blocking_criterion_regressions': blocking,
                           'reason': 'Holdout only; inspect privacy, repeat distributions and hard failures. Nothing is automatically enabled.'},
              'artifacts': {'privacy': 'privacy/report.json', 'tasks': 'comprehension/report.json',
                            'first_answers': 'comprehension/first-responses.json', 'grades': 'comprehension/first-grades.json',
                            'rejected_records': 'comprehension/rejected-records.json'}}
    _write_json(output / 'report.json', report)
    lines = ['# Reliable multilingual evaluation', '', f"Status: {report['status']}",
             f"Split: {frozen.get('split')}; repeats: {frozen.get('repeats')}; grading policy: 2", '',
             'Privacy and task-response scores are separate. Development scores cannot authorize adoption.',
             ARTIFACT_SCOPE, '',
             '```json', json.dumps({'privacy': report['privacy'], 'repeated_statistics': report['repeated_statistics'],
                                    'execution': report['execution']}, ensure_ascii=False, indent=2), '```', '']
    (output / 'summary.md').write_text('\n'.join(lines), encoding='utf8', newline='\n')
    return report


# --- Execution ----------------------------------------------------------------------------------

def _append_rejected(path, item):
    rows = json.loads(path.read_bytes()) if path.exists() else []
    rows.append(item)
    _write_json(path, rows)


def execute_reliable(output_dir, *, execute=False, max_calls=306, max_seconds=7200, max_tokens=12_000_000, workers=3):
    """Persist first answers before independent grades; failed/unknown usage stops."""
    if not execute or type(workers) is not int or not 1 <= workers <= 3:
        raise ValueError('Explicit execution and 1..3 workers required.')
    if type(max_calls) is not int or max_calls < 1 or max_seconds <= 0 or max_tokens < 1:
        raise ValueError('Positive execution budgets required.')
    output = Path(output_dir)
    with session_file_lock(output / 'execution'):
        frozen = json.loads((output / 'freeze.json').read_bytes())
        problems = _verify_freeze(output, frozen, check_native_cli=True)
        if problems:
            raise ValueError('Frozen run verification failed: ' + '; '.join(problems))
        if not frozen['reference_audit_verified']:
            raise ValueError('Verify the reference-response audit before starting task-performance calls.')
        directory = output / 'comprehension'
        state = json.loads((directory / 'manifest.json').read_bytes())
        journal_path = output / 'execution-journal.json'
        rejected_path = directory / 'rejected-records.json'
        saved_evidence = (state['responses'] or state['grades'] or rejected_path.exists()
                          or (directory / 'first-responses.json').exists() or (directory / 'first-grades.json').exists())
        if not journal_path.exists() and saved_evidence:
            raise ValueError('Execution journal is missing while saved records exist; refusing to continue.')
        budget = {'max_calls': max_calls, 'max_seconds': max_seconds, 'max_reported_tokens': max_tokens, 'workers': workers}
        journal = json.loads(journal_path.read_bytes()) if journal_path.exists() else {
            'budget': budget, 'started_at_unix': time.time(), 'deadline_unix': time.time() + max_seconds,
            'calls': [], 'batches': [], 'elapsed_seconds': 0.0, 'stopped': False}
        if journal['budget'] != budget:
            raise ValueError('Execution budgets are immutable across resume.')
        # A crash after saving but before journaling leaves the call 'running';
        # that is accounted for and stops below rather than being retried.
        completed = {(c.get('phase'), c['job_id']) for c in journal['calls'] if c['status'] in {'completed', 'running'}}
        if (any(('interpret', job_id) not in completed for job_id in state['responses'])
                or any(('grade', job_id) not in completed for job_id in state['grades'])):
            raise ValueError('Saved records are not accounted for by the execution journal.')
        if any(c['status'] == 'running' for c in journal['calls']):
            journal['stopped'] = True
            journal['stop_reason'] = 'Interrupted call has unknown usage; no automatic retry.'
            _write_json(journal_path, journal)
        if journal['stopped']:
            return joint_report(output)
        _write_json(journal_path, journal)
        started = time.monotonic()
        jobs = state['jobs']
        provenance = {'model': frozen['model'], 'reasoning_effort': frozen['reasoning_effort'],
                      'adapter': frozen['adapter_source_sha256'], 'cli_version': frozen['cli_version']}
        for phase, target, filename in (('interpret', 'responses', 'first-responses.json'), ('grade', 'grades', 'first-grades.json')):
            state = json.loads((directory / 'manifest.json').read_bytes())
            if phase == 'grade' and len(state['responses']) != len(jobs):
                break  # Never start grading until every first answer is frozen.
            pending = [j for j in jobs if j['job_id'] not in state[target]]
            with ThreadPoolExecutor(max_workers=workers) as pool:
                while pending and not journal['stopped']:
                    usage = sum(c.get('usage', {}).get('total_tokens', 0) for c in journal['calls'])
                    elapsed = journal['elapsed_seconds'] + time.monotonic() - started
                    remaining = max_calls - len(journal['calls'])
                    if remaining <= 0 or usage >= max_tokens or elapsed >= max_seconds or time.time() >= journal['deadline_unix']:
                        journal['stop_reason'] = 'Budget exhausted before the next batch.'
                        break
                    batch, pending = pending[:min(workers, remaining)], pending[min(workers, remaining):]
                    requests = {j['job_id']: j['request'] if phase == 'interpret' else _grade_request(j, state['responses'][j['job_id']]) for j in batch}
                    entries = {j['job_id']: {'job_id': j['job_id'], 'phase': phase, 'status': 'running'} for j in batch}
                    journal['calls'].extend(entries.values())
                    journal.setdefault('batches', []).append({'phase': phase, 'in_flight': len(batch),
                                                              'reported_tokens_before': usage})
                    _write_json(journal_path, journal)  # Reserve attempts before starting children.
                    futures = {pool.submit(run_codex_worker, requests[j['job_id']]): j for j in batch}
                    for future in as_completed(futures):
                        job = futures[future]
                        entry = entries[job['job_id']]
                        result = None
                        try:
                            result = future.result()
                            entry['usage'] = result.get('usage', {}) if isinstance(result, dict) else {}
                            _check_provenance(result, mode='answer_visible_task' if phase == 'interpret' else 'independent_grade',
                                              **provenance)
                            result['execution'] = {'kind': 'actual_llm_subagent', 'fresh_context': True,
                                'runner': 'Codex CLI ephemeral child', 'isolation': 'Fresh cwd/context, tool events rejected; same OS user, not a hard filesystem jail.'}
                            if phase == 'interpret':
                                _validate_response(result, job)
                            else:
                                result['response_hash'] = digest(state['responses'][job['job_id']]['response'])
                                _validate_grades(result, job, state['responses'][job['job_id']])
                            path = directory / filename
                            saved = json.loads(path.read_bytes()) if path.exists() else []
                            if any(r['job_id'] == result['job_id'] for r in saved):
                                raise ValueError('First answer/grade already saved.')
                            saved.append(result)
                            _write_json(path, saved)
                            _retry_transient(continue_comprehension, directory, **{'responses_path' if phase == 'interpret' else 'grades_path': path})
                            state[target][job['job_id']] = result
                            entry['status'] = 'completed'
                            if 'total_tokens' not in entry['usage']:
                                journal['stopped'] = True
                                journal['stop_reason'] = 'Unknown reported usage.'
                                entry['usage_unknown'] = True
                        except Exception as exc:
                            entry.update(status='error', error=type(exc).__name__)
                            if isinstance(exc, ObservedWorkerFailure):
                                entry.update(error=exc.diagnostics['code'], diagnostics=exc.diagnostics,
                                             usage=exc.usage or {}, usage_unknown=exc.usage is None)
                            journal['stopped'] = True
                            journal['stop_reason'] = 'Worker error or rejected record.'
                            if result is not None:
                                # Preserve what the model actually returned; it is never retried.
                                _append_rejected(rejected_path, {'job_id': job['job_id'], 'phase': phase,
                                                                 'error': type(exc).__name__, 'record_sha256': digest(result),
                                                                 'record': result})
                        _write_json(journal_path, journal)
        journal['elapsed_seconds'] += time.monotonic() - started
        _write_json(journal_path, journal)
        return joint_report(output)


# --- Reference audit execution -----------------------------------------------------------------

def prepare_reference_audit(data_dir, output_dir, *, split='holdout', model='gpt-6.1-sol', reasoning_effort='medium'):
    """Owner reference answers validate attainable rubrics; not interpretation scores."""
    bundle = load_bundle(data_dir)
    output = Path(output_dir)
    if split not in SPLITS or output.exists():
        raise ValueError('Select a split and new reference-audit directory.')
    cli_version = native_cli_version()
    output.mkdir(parents=True)
    requests = _reference_requests(bundle, split, model, reasoning_effort)
    _write_json(output / 'requests.json', requests)
    _write_json(output / 'freeze.json', {'schema_version': 2, 'split': split, 'corpus_byte_hashes': bundle['hashes'],
                                       'model': model, 'reasoning_effort': reasoning_effort, 'grading_policy_version': 2,
                                       'grading_policy_sha256': grading_policy_hash(),
                                       'adapter_source_sha256': adapter_hash(), 'cli_version': cli_version,
                                       'requests_sha256': _file_hash(output / 'requests.json'),
                                       'scope': 'Reference rubric audit only; not actual task understanding.'})
    return requests


def audit_references(data_dir, output_dir, *, execute=False, split='holdout', model='gpt-6.1-sol',
                     reasoning_effort='medium', max_calls=17, max_seconds=900, max_tokens=600000):
    output = Path(output_dir)
    if not output.exists():
        requests = prepare_reference_audit(data_dir, output, split=split, model=model, reasoning_effort=reasoning_effort)
    else:
        requests = json.loads((output / 'requests.json').read_bytes())
    frozen = json.loads((output / 'freeze.json').read_bytes())
    bundle = load_bundle(data_dir)
    if (frozen['corpus_byte_hashes'] != bundle['hashes'] or frozen['split'] != split or frozen['model'] != model
            or frozen['reasoning_effort'] != reasoning_effort or frozen.get('grading_policy_sha256') != grading_policy_hash()):
        raise ValueError('Reference audit inputs are immutable.')
    if requests != _reference_requests(bundle, split, model, reasoning_effort) or (
            'requests_sha256' in frozen and frozen['requests_sha256'] != _file_hash(output / 'requests.json')):
        raise ValueError('Reference audit requests changed after preparation.')
    if not execute:
        return {'status': 'prepared', 'requests': len(requests), 'scope': 'Reference audit, not performance scores.'}
    if adapter_hash() != frozen['adapter_source_sha256']:
        raise ValueError('Reference adapter changed after preparation.')
    if 'cli_version' in frozen and native_cli_version() != frozen['cli_version']:
        raise ValueError('Native CLI version changed after reference-audit preparation.')
    budget = {'max_calls': max_calls, 'max_seconds': max_seconds, 'max_reported_tokens': max_tokens}
    journal_path = output / 'journal.json'
    result_path = output / 'first-grades.json'
    rejected_path = output / 'rejected-records.json'
    if not journal_path.exists() and (result_path.exists() or rejected_path.exists()):
        raise ValueError('Reference audit journal is missing while saved records exist.')
    journal = json.loads(journal_path.read_bytes()) if journal_path.exists() else {
        'budget': budget, 'deadline_unix': time.time() + max_seconds, 'calls': [], 'stopped': False}
    if journal['budget'] != budget:
        raise ValueError('Reference audit budgets are immutable.')
    if any(row['status'] == 'running' for row in journal['calls']):
        journal['stopped'] = True
    results = json.loads(result_path.read_bytes()) if result_path.exists() else []
    done = {row['job_id'] for row in results}
    _write_json(journal_path, journal)
    for item in requests:
        request = item['request']
        usage = sum(row.get('usage', {}).get('total_tokens', 0) for row in journal['calls'])
        if journal['stopped'] or len(journal['calls']) >= max_calls or usage >= max_tokens or time.time() >= journal['deadline_unix']:
            break
        if request['job_id'] in done:
            continue
        entry = {'job_id': request['job_id'], 'status': 'running'}
        journal['calls'].append(entry)
        _write_json(journal_path, journal)
        result = None
        try:
            result = run_codex_worker(request)
            entry['usage'] = result.get('usage', {}) if isinstance(result, dict) else {}
            _check_provenance(result, model=model, reasoning_effort=reasoning_effort, adapter=frozen['adapter_source_sha256'],
                              cli_version=frozen.get('cli_version'), mode='independent_grade')
            results.append(result)
            _write_json(result_path, results)
            entry.update(status='completed')
            if 'total_tokens' not in entry['usage']:
                journal['stopped'] = True  # Unknown usage stays incomplete by budget policy.
        except Exception as exc:
            entry.update(status='error', error=type(exc).__name__)
            if isinstance(exc, ObservedWorkerFailure):
                entry.update(error=exc.diagnostics['code'], diagnostics=exc.diagnostics,
                             usage=exc.usage or {}, usage_unknown=exc.usage is None)
            journal['stopped'] = True
            if result is not None:
                _append_rejected(rejected_path, {'job_id': request['job_id'], 'error': type(exc).__name__,
                                                 'record_sha256': digest(result), 'record': result})
        _write_json(journal_path, journal)
    total = sum(len(row['request']['criteria']) for row in requests)
    passed = sum(g['passed'] for row in results for g in row['grades'])
    complete = len(results) == len(requests) and not journal['stopped']
    report = {'status': 'passed' if complete and passed == total else 'needs_review' if complete else 'incomplete',
              'total_criteria': total, 'passed_criteria': passed, 'graded_references': len(results),
              'failed_reference_ids': [row['job_id'] for row in results if not all(g['passed'] for g in row['grades'])],
              'scope': 'Attainable-rubric reference audit. Not actual task interpretation or an adoption score.'}
    _write_json(output / 'report.json', report)
    return report
