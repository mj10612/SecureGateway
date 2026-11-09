"""Synthetic, offline HTTP evaluation; quality axes are never combined."""
from __future__ import annotations

from contextlib import contextmanager
from difflib import SequenceMatcher
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
import os
from pathlib import Path
import platform
import re
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread
import time
from urllib.request import ProxyHandler, Request, build_opener
from urllib.error import HTTPError
import uuid

from secure_gateway import __version__
from secure_gateway.gateway import PrivacyGateway
from secure_gateway.engine.natural_languages import SUPPORTED_LANGUAGES

SCHEMA_VERSION = 1
SCORING_VERSION = 2
PROFILES = ('smoke', 'standard', 'release')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def at(value, path):
    for key in path:
        value = value[key]
    return value


def load_corpus(path=None):
    raw = Path(path).read_bytes() if path else files('secure_gateway').joinpath('evaluation_corpus.json').read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('Corpus exceeds 2 MiB.')
    data = json.loads(raw)
    validate_corpus(data)
    return data


def validate_corpus(data):
    if not isinstance(data, dict) or data.get('schema_version') != 1 or data.get('synthetic') is not True:
        raise ValueError('A versioned synthetic corpus is required.')
    if not isinstance(data.get('corpus_version'), str) or not data['corpus_version']:
        raise ValueError('Missing corpus version.')
    cases = data.get('cases')
    if not isinstance(cases, list) or not 1 <= len(cases) <= 256:
        raise ValueError('Corpus must contain 1..256 cases.')
    ids: set[str] = set()
    groups: dict[str, str] = {}
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get('id'), str) or case['id'] in ids:
            raise ValueError('Duplicate or invalid case id.')
        ids.add(case['id'])
        group, split = case.get('template_group'), case.get('split')
        if not isinstance(group, str) or split not in {'development', 'regression', 'holdout'}:
            raise ValueError('Invalid template split.')
        if group in groups and groups[group] != split:
            raise ValueError('A template group crosses corpus splits.')
        groups[group] = split
        if case.get('language') not in SUPPORTED_LANGUAGES - {'auto'} or case.get('domain') not in {'general', 'defense', 'automotive', 'semiconductor'}:
            raise ValueError('Unsupported corpus language/domain.')
        if case.get('language_mode', 'auto') not in {'auto', 'explicit'}:
            raise ValueError('Unsupported corpus language mode.')
        if case.get('dialect') not in {'claude', 'codex'} or not isinstance(case.get('payload'), dict):
            raise ValueError('Invalid request dialect/payload.')
        if len(json.dumps(case['payload']).encode()) > 128 * 1024:
            raise ValueError('Case payload exceeds limit.')
        for name in ('echo_path', 'task_path'):
            try:
                target = at(case['payload'], case[name])
            except (KeyError, IndexError, TypeError):
                raise ValueError('Invalid source path.') from None
            if not isinstance(target, str) or len(target) > 32768:
                raise ValueError('Source path must identify bounded text.')
        for name in ('secrets', 'public'):
            if not isinstance(case.get(name), list):
                raise ValueError('Missing source spans.')
            span_keys = set()
            for span in case[name]:
                try:
                    text = at(case['payload'], span['path'])
                    start, end = span['start'], span['end']
                    valid = (isinstance(text, str) and type(start) is int and type(end) is int
                             and 0 <= start < end <= len(text) and len(text) <= 32768)
                except (KeyError, IndexError, TypeError):
                    valid = False
                if not valid:
                    raise ValueError('Invalid source span.')
                identity = (tuple(span['path']), start, end)
                if identity in span_keys:
                    raise ValueError('Duplicate source span occurrence.')
                span_keys.add(identity)
                if name == 'secrets':
                    fragments = span.get('fragments')
                    if (not isinstance(fragments, list) or any(not isinstance(s, str) or len(s) < 2 or s not in text[start:end] for s in fragments)
                            or span.get('policy') not in {'explicit', 'contextual', 'pattern'}):
                        raise ValueError('Invalid sensitive span fragments/policy.')
        terms = case.get('forced_terms')
        explicit = {at(case['payload'], s['path'])[s['start']:s['end']] for s in case['secrets'] if s['policy'] == 'explicit'}
        if not isinstance(terms, list) or any(not isinstance(t, str) or t not in explicit for t in terms):
            raise ValueError('Forced terms must be explicit source policy, not hidden gold.')
        rubric = case.get('rubric')
        if not isinstance(rubric, list) or len({r.get('id') for r in rubric}) != len(rubric):
            raise ValueError('Invalid rubric.')
        if any(not isinstance(r.get('id'), str) or not isinstance(r.get('description'), str) for r in rubric):
            raise ValueError('Invalid rubric criterion.')
        if not isinstance(case.get('human_text'), str) or type(case.get('smoke')) is not bool:
            raise ValueError('Missing human control/profile selection.')


def select_cases(data, profile):
    if profile not in PROFILES:
        raise ValueError('Unknown evaluation profile.')
    cases = data['cases']
    return [c for c in cases if c['smoke']] if profile == 'smoke' else cases[:24] if profile == 'standard' else cases[:]


def score_field(source, outgoing, secrets, public, *, aliases=None):
    """Attribute unchanged full/curated-fragment spans to source occurrences.

    Alignment is deliberately conservative and limited to small synthetic fields;
    it is not a semantic reidentification or arbitrary encoding detector.
    """
    ranges = [(b.a, b.a + b.size) for b in SequenceMatcher(None, source, outgoing, autojunk=False).get_matching_blocks()]
    exact_provenance = False
    if aliases:
        present = {a: original for a, original in aliases.items() if a and a != original and a in outgoing}
        if present:
            pattern = re.compile('|'.join(re.escape(a) for a in sorted(present, key=len, reverse=True)))
            expanded = []
            known_ranges = []
            cursor = offset = 0
            for match in pattern.finditer(outgoing):
                literal = outgoing[cursor:match.start()]
                expanded.append(literal)
                known_ranges.append((offset, offset + len(literal)))
                offset += len(literal)
                original = present[match.group()]
                expanded.append(original)
                offset += len(original)
                cursor = match.end()
            literal = outgoing[cursor:]
            expanded.append(literal)
            known_ranges.append((offset, offset + len(literal)))
            if ''.join(expanded) == source:
                ranges = known_ranges
                exact_provenance = True

    def visible(start, end):
        return any(left <= start and end <= right for left, right in ranges)

    measured = []
    for span in secrets:
        spelling = source[span['start']:span['end']]
        ambiguous = not exact_provenance and source.count(spelling) > outgoing.count(spelling) > 0 and source.count(spelling) > 1
        # Equal spellings at public and secret positions cannot be uniquely
        # attributed by string alignment. Count possible exposure conservatively.
        full = visible(span['start'], span['end'])
        partial = False
        for fragment in span.get('fragments', []):
            offset = source.find(fragment, span['start'], span['end'])
            while offset >= 0:
                partial |= visible(offset, offset + len(fragment))
                offset = source.find(fragment, offset + 1, span['end'])
        full = full or ambiguous and not partial
        measured.append({**span, 'full_exposure': full, 'partial_exposure': bool(partial and not full),
                         'alignment_ambiguous': ambiguous})
    public_results = []
    for span in public:
        spelling = source[span['start']:span['end']]
        ambiguous = not exact_provenance and source.count(spelling) > outgoing.count(spelling) > 0 and source.count(spelling) > 1
        public_results.append({**span, 'overmasked': not visible(span['start'], span['end']) or ambiguous,
                               'alignment_ambiguous': ambiguous})
    return {'secrets': measured, 'public': public_results}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as stream:
            if os.name != 'nt':
                temporary.chmod(0o600)
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _metadata(data, profile):
    from secure_gateway.domain_dictionaries import catalog, DEFAULTS
    try:
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL,
                                      cwd=Path(__file__).parent, timeout=3).decode().strip()
    except (OSError, subprocess.SubprocessError):
        sha = None
    settings = {'natural_language': 'auto', 'prose_mode': 'content_words', 'mask_numbers': False,
                'forced_terms': {c['id']: c['forced_terms'] for c in select_cases(data, profile)},
                'domain_dictionary_toggles': dict(DEFAULTS), 'domain_dictionary_manifest': catalog().version}
    if any('language_mode' in c for c in select_cases(data, profile)):
        settings['case_language_modes'] = {c['id']: c.get('language_mode', 'auto') for c in select_cases(data, profile)}
    source_hash = digest({str(p.relative_to(Path(__file__).parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(Path(__file__).parent.rglob('*')) if p.is_file() and p.suffix in {'.py', '.json'}})
    return {'package_version': __version__, 'code_sha': sha, 'source_hash': source_hash,
            'scoring_version': SCORING_VERSION, 'corpus_version': data['corpus_version'],
            'corpus_hash': digest(data), 'settings': settings, 'settings_hash': digest(settings),
            'profile': profile, 'python': platform.python_version(), 'platform': platform.platform(),
            'languages_measured': sorted({c['language'] for c in select_cases(data, profile)}),
            'languages_not_measured': sorted((SUPPORTED_LANGUAGES - {'auto'}) - {c['language'] for c in select_cases(data, profile)}),
            'other_languages': 'not_measured',
            'scope': 'synthetic loopback HTTP; not native client/provider certification'}


@contextmanager
def _serving(server):
    thread = Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(5)
        server.server_close()


def _source_keys(value, session):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            original = session.restore(key)
            if original in result:
                raise ValueError('Restored source keys collide.')
            result[original] = _source_keys(item, session)
        return result
    if isinstance(value, list):
        return [_source_keys(item, session) for item in value]
    return value


def _capture_case(case, max_seconds=40):
    captured = []
    echo_path = case['echo_path']
    deadline = time.monotonic() + max_seconds

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            captured.append(payload)
            text = at(payload, echo_path)
            body = json.dumps({'content': [{'type': 'text', 'text': text}]}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with _serving(ThreadingHTTPServer(('127.0.0.1', 0), Provider)) as provider:
        origin = f'http://127.0.0.1:{provider.server_port}'
        gateway = PrivacyGateway(('127.0.0.1', 0), uuid.uuid4().hex, {'claude': origin, 'codex': origin},
                                 natural_language=case['language'] if case.get('language_mode') == 'explicit' else 'auto')
        gateway.mask_rules = tuple(case['forced_terms'])
        session = gateway.get_session(case['dialect'])
        timings: dict[str, list[float]] = {'request_transform': [], 'response_restore': []}

        def timed(name, method):
            def wrapped(*args, **kwargs):
                begin = time.monotonic()
                try:
                    return method(*args, **kwargs)
                finally:
                    timings[name].append(time.monotonic() - begin)
            return wrapped

        session.request = timed('request_transform', session.request)
        session.response = timed('response_restore', session.response)
        with _serving(gateway):
            agent = case['dialect']
            path = '/claude/v1/messages' if agent == 'claude' else '/codex/responses'
            request = Request(f'http://127.0.0.1:{gateway.server_port}{path}',
                              json.dumps(case['payload']).encode(),
                              {'Content-Type': 'application/json', 'X-SecureGateway-Token': gateway.token,
                               'Authorization': 'Bearer sk-ant-oat01-synthetic' if agent == 'claude' else 'Bearer eyJsynthetic'})
            opener = build_opener(ProxyHandler({}))
            def receive():
                try:
                    with opener.open(request, timeout=max(.001, min(20, deadline - time.monotonic()))) as response:
                        return json.load(response), response.status
                except HTTPError as exc:
                    # Privacy is still measurable when the actual provider
                    # received a payload but local restoration/save failed.
                    # Preserve that integrity failure instead of discarding
                    # the capture or certifying a roundtrip.
                    with exc:
                        if not captured:
                            raise
                        return None, exc.code
            begin = time.monotonic()
            answer, response_status = receive()
            first_seconds = time.monotonic() - begin
            if time.monotonic() >= deadline:
                raise TimeoutError('Case budget exhausted.')
            replay_answer, replay_status = receive()
            if len(captured) != 2:
                raise ValueError('Provider capture missing.')
            view = _source_keys(captured[0], gateway.get_session(agent))
            alias_originals = {m.surrogate: m.original for m in session.session.reverse_store.values()}
            restored = answer['content'][0]['text'] if answer is not None else None
            source_echo = at(case['payload'], echo_path)
            exact = response_status == 200 and restored == source_echo
            semantic = exact
            if not exact and isinstance(restored, str) and echo_path[-1] == 'arguments':
                try:
                    semantic = json.loads(restored) == json.loads(source_echo)
                except (ValueError, TypeError):
                    semantic = False
            result = {'outbound': captured[0], 'restored_echo': restored, 'roundtrip': exact,
                      'semantic_roundtrip': semantic,
                      'replay': response_status == replay_status == 200 and captured[0] == captured[1] and answer == replay_answer,
                      'payload_replay': captured[0] == captured[1], 'response_status': response_status,
                      'replay_response_status': replay_status, 'http_seconds': first_seconds,
                      'timings_seconds': timings, 'grading_alias_bindings': alias_originals}
            scores: dict[str, list] = {'secrets': [], 'public': []}
            paths = {tuple(s['path']) for s in case['secrets'] + case['public']}
            # Preserve annotation ordering so comparisons identify the same occurrence.
            by_key = {}
            for field in paths:
                source, outgoing = at(case['payload'], field), at(view, field)
                if not isinstance(outgoing, str):
                    raise ValueError('Source field changed type.')
                scored = score_field(source, outgoing, [s for s in case['secrets'] if tuple(s['path']) == field],
                                     [s for s in case['public'] if tuple(s['path']) == field], aliases=alias_originals)
                for kind in ('secrets', 'public'):
                    for span in scored[kind]:
                        by_key[(kind, field, span['start'], span['end'])] = span
            for kind in ('secrets', 'public'):
                scores[kind] = [by_key[(kind, tuple(s['path']), s['start'], s['end'])] for s in case[kind]]
            return {**result, **scores}


def _session_checks():
    with TemporaryDirectory(prefix='secure-gateway-eval-state-') as root:
        state = Path(root)
        token = uuid.uuid4().hex
        first = PrivacyGateway(('127.0.0.1', 0), token, state_dir=state)
        try:
            session = first.get_session('claude')
            alias = session.mask('SyntheticPrivateEvalQzx', code=True)
            isolated = all(m.original != 'SyntheticPrivateEvalQzx' for m in first.get_session('codex').session.forward_store.values())
            first.save('claude', session)
        finally:
            first.server_close()
        second = PrivacyGateway(('127.0.0.1', 0), token, state_dir=state)
        try:
            resumed = second.get_session('claude')
            restarted = resumed.restore(alias) == 'SyntheticPrivateEvalQzx' and resumed.mask('SyntheticPrivateEvalQzx', code=True) == alias
        finally:
            second.server_close()
    return {'session_isolation': isolated, 'snapshot_restart': restarted}


def _privacy_metrics(cases):
    measured = [c for c in cases if c['status'] == 'completed']
    secrets = [s for c in measured for s in c['secrets']]
    public = [s for c in measured for s in c['public']]
    total = sum(c['sensitive_count'] for c in cases)
    protected = sum(not s['full_exposure'] and not s['partial_exposure'] and not s.get('alignment_ambiguous', False) for s in secrets)
    return {'privacy': {'total_sensitive': total, 'measured_sensitive': len(secrets), 'unmeasured_sensitive': total - len(secrets),
                        'fully_protected': protected, 'full_exposures': sum(s['full_exposure'] for s in secrets),
                        'partial_exposures': sum(s['partial_exposure'] for s in secrets),
                        'ambiguous_possible_exposures': sum(s.get('alignment_ambiguous', False) for s in secrets),
                        'accuracy': protected / total if total and len(secrets) == total else None,
                        'observed_accuracy': protected / len(secrets) if secrets else None,
                        'requests_with_leak': sum(any(s['full_exposure'] or s['partial_exposure'] for s in c['secrets']) for c in measured),
                        'measured_requests': len(measured), 'total_requests': len(cases)},
            'overmasking': {'measured_public': len(public), 'overmasked': sum(s['overmasked'] for s in public),
                            'rate': sum(s['overmasked'] for s in public) / len(public) if public else None},
            'integrity': {'roundtrip_passed': sum(c['roundtrip'] for c in measured),
                          'semantic_roundtrip_passed': sum(c['semantic_roundtrip'] for c in measured),
                          'replay_passed': sum(c['replay'] for c in measured), 'measured_requests': len(measured),
                          'response_failures': sum(c.get('response_status', 200) != 200 for c in measured),
                          'payload_replay_passed': sum(c.get('payload_replay', c['replay']) for c in measured)},
            'comprehension': {'status': 'not_measured'}}


def save_report(report, output_dir):
    output_dir = Path(output_dir)
    write_json(output_dir / 'report.json', report)
    summary = [f"# {report['suite']} evaluation", '', f"Status: {report['status']}", '',
               'The two quality axes are independent. Missing measurements are not successes.', '',
               '```json', json.dumps(report['metrics'], ensure_ascii=False, indent=2), '```', '',
               'Synthetic corpus only; results are not real-world disclosure probabilities.',
               'Recorded domain settings apply to this run only; untested languages and native-client paths are not certified.']
    (output_dir / 'summary.md').write_text('\n'.join(summary) + '\n', encoding='utf-8')


def run_privacy(data, *, output_dir, profile='smoke', max_seconds=300):
    validate_corpus(data)
    output_dir = Path(output_dir)
    if (output_dir / 'report.json').exists():
        raise ValueError('Output already contains a report; use a new directory.')
    begin = time.monotonic()
    results: list[dict] = []
    report = {'schema_version': 1, 'suite': 'privacy', 'run_id': uuid.uuid4().hex,
              'metadata': _metadata(data, profile), 'cases': results, 'status': 'running'}
    for case in select_cases(data, profile):
        result = {k: case[k] for k in ('id', 'language', 'domain', 'dialect', 'split', 'template_group')}
        result['language_mode'] = case.get('language_mode', 'auto')
        result['sensitive_annotations'] = [{k: span.get(k) for k in ('label', 'policy', 'severity')} for span in case['secrets']]
        result['sensitive_count'] = len(case['secrets'])
        result['status'] = 'budget_exhausted'
        if time.monotonic() - begin < max_seconds:
            try:
                result.update(_capture_case(case, max_seconds=max_seconds - (time.monotonic() - begin)), status='completed')
            except (ValueError, OSError, KeyError, IndexError, TypeError) as exc:
                result.update(status='error', error=type(exc).__name__)
        results.append(result)
        report['metrics'] = _privacy_metrics(results)
        write_json(output_dir / 'progress.json', report)
    report['status'] = 'completed' if all(c['status'] == 'completed' for c in results) else 'incomplete'
    report['metrics'] = _privacy_metrics(results)
    try:
        report['metrics']['integrity'].update(_session_checks())
    except (ValueError, OSError):
        report['metrics']['integrity'].update(session_isolation=None, snapshot_restart=None)
        report['status'] = 'incomplete'
    report['elapsed_seconds'] = time.monotonic() - begin
    report['performance'] = {}
    for name in ('request_transform', 'response_restore'):
        for phase, index in (('first_mapping_pass', 0), ('replay', 1)):
            values = sorted(c['timings_seconds'][name][index] for c in results
                            if c['status'] == 'completed' and len(c['timings_seconds'][name]) > index)
            if values:
                report['performance'][name + '_' + phase] = {
                    'n': len(values), **{p: values[min(len(values) - 1, int((len(values) - 1) * q))]
                                        for p, q in [('p50', .5), ('p95', .95), ('p99', .99)]}}
    report['breakdown'] = {name: {value: _privacy_metrics([c for c in results if c[name] == value])
                                for value in sorted({c[name] for c in results})} for name in ('language', 'domain', 'dialect', 'split', 'language_mode')}
    for name in ('policy', 'label'):
        values = sorted({s[name] for c in results for s in c['sensitive_annotations'] if isinstance(s.get(name), str)})
        report['breakdown'][name] = {}
        for value in values:
            subset = []
            for case in results:
                count = sum(s.get(name) == value for s in case['sensitive_annotations'])
                if count:
                    subset.append({**case, 'sensitive_count': count,
                                   'secrets': [s for s in case.get('secrets', []) if s.get(name) == value]})
            report['breakdown'][name][value] = _privacy_metrics(subset)['privacy']
    save_report(report, output_dir)
    return report


def compare_reports(baseline, candidate):
    if baseline.get('schema_version') != 1 or candidate.get('schema_version') != 1 or baseline.get('suite') != candidate.get('suite'):
        raise ValueError('Incompatible report schemas/suites.')
    if baseline.get('metadata', {}).get('scoring_version') != candidate.get('metadata', {}).get('scoring_version'):
        raise ValueError('Incompatible reports: scoring_version')
    for key in ('corpus_hash', 'settings_hash', 'profile'):
        if (not isinstance(baseline.get('metadata', {}).get(key), str) or not baseline['metadata'][key]
                or baseline['metadata'].get(key) != candidate.get('metadata', {}).get(key)):
            raise ValueError('Incompatible reports: ' + key)
    if [c['id'] for c in baseline['cases']] != [c['id'] for c in candidate['cases']]:
        raise ValueError('Incompatible case selection.')
    new: list[dict] = []
    existing: list[dict] = []
    resolved: list[dict] = []
    integrity_regressions: list[dict] = []
    if baseline['suite'] == 'privacy':
        for before, after in zip(baseline['cases'], candidate['cases']):
            if before['status'] != 'completed' or after['status'] != 'completed':
                continue
            if len(before['secrets']) != len(after['secrets']):
                raise ValueError('Incompatible occurrence annotations.')
            for check in ('roundtrip', 'semantic_roundtrip', 'replay'):
                if before.get(check) is True and after.get(check) is not True:
                    integrity_regressions.append({'case_id': after['id'], 'check': check})
            for i, (a, b) in enumerate(zip(before['secrets'], after['secrets'])):
                was = a['full_exposure'] or a['partial_exposure'] or a.get('alignment_ambiguous', False)
                now = b['full_exposure'] or b['partial_exposure'] or b.get('alignment_ambiguous', False)
                item = {'case_id': after['id'], 'occurrence': i}
                if now:
                    (existing if was else new).append(item)
                elif was:
                    resolved.append(item)
        for check in ('session_isolation', 'snapshot_restart'):
            if baseline['metrics']['integrity'].get(check) is True and candidate['metrics']['integrity'].get(check) is not True:
                integrity_regressions.append({'check': check})
    else:
        for key in ('model', 'repeats', 'worker_protocol', 'max_output_tokens'):
            if baseline['metadata'].get(key) != candidate['metadata'].get(key):
                raise ValueError('Incompatible LLM reports: ' + key)
        for before, after in zip(baseline['cases'], candidate['cases']):
            if before.get('grades') and after.get('grades'):
                old = {g['id']: g['passed'] for g in before['grades']}
                if set(old) != {g['id'] for g in after['grades']}:
                    raise ValueError('Incompatible rubric criteria.')
                for grade in after['grades']:
                    if grade['id'] not in old:
                        raise ValueError('Incompatible rubric criteria.')
                    item = {'case_id': after['id'], 'criterion': grade['id']}
                    if old[grade['id']] and not grade['passed']:
                        new.append(item)
                    elif not old[grade['id']] and grade['passed']:
                        resolved.append(item)
    complete = baseline['status'] == candidate['status'] == 'completed'
    return {'schema_version': 1, 'suite': baseline['suite'], 'comparable': complete,
            'regression': bool(new or integrity_regressions) or not complete,
            'integrity_regressions': integrity_regressions,
            'new_exposures' if baseline['suite'] == 'privacy' else 'regressed_criteria': new,
            'existing_exposures': existing, 'resolved_exposures' if baseline['suite'] == 'privacy' else 'improved_criteria': resolved,
            'baseline_metrics': baseline['metrics'], 'candidate_metrics': candidate['metrics']}
