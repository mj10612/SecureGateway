"""Build the frozen #309 replication case set from independently authored batches.

Reads replacement-batch{n}-authored.json / -screen.json, keeps every distinct
activating non-control case (C != D), keeps eight unchanged negative controls,
validates the merged set with the existing validator, generates the preflight
comparison inside the new plan directory, and copies the approved rubric and
decision files verbatim.
"""
import collections, hashlib, importlib.util, json, os, pathlib, random, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path('docs/evaluations/comprehension-2.11.1')
PLAN_NAME = 'plan-replication'
MAX_BATCH = int(sys.argv[1]) if len(sys.argv) > 1 else 7
SEED = 20261112
issue = 309
base = ROOT / str(issue)
plan = base / PLAN_NAME
if plan.exists():
    raise SystemExit('plan already frozen: ' + str(plan))

pilot = json.loads((ROOT / 'pilot/309-underpowered/manifest.json').read_text(encoding='utf-8-sig'))
pilot_originals = {c['original'] for c in pilot['cases']}

authored_total = 0
activating = []
activating_ids = set()
controls = []
for n in range(1, MAX_BATCH + 1):
    apath = base / 'plan' / f'replacement-batch{n}-authored.json'
    spath = base / 'plan' / f'replacement-batch{n}-screen.json'
    if not apath.exists():
        continue
    doc = json.loads(apath.read_text(encoding='utf-8-sig'))
    screen = json.loads(spath.read_text(encoding='utf-8-sig'))
    rows = {r['id']: r for r in screen['rows']}
    authored_total += len(doc['cases'])
    for c in doc['cases']:
        r = rows.get(c['id'], {})
        if c['original'] in pilot_originals:
            continue
        case = dict(c)
        case['id'] = f'b{n}-{c["id"]}'
        case['author_batch'] = n
        case['author_source'] = f'replacement-batch{n}-authored.json'
        case['source_case_id'] = c['id']
        if c['negative_control']:
            if r.get('changed') is False:
                controls.append(case)
        elif r.get('changed') is True:
            activating.append(case)

# Distinct by original text; keep first occurrence in batch order.
seen = set()
distinct = []
for c in activating:
    if c['original'] in seen:
        continue
    seen.add(c['original'])
    distinct.append(c)

rng = random.Random(SEED)
rng.shuffle(controls)
selected_controls = []
control_texts = set()
for c in controls:
    if c['original'] in control_texts or c['original'] in seen:
        continue
    control_texts.add(c['original'])
    selected_controls.append(c)
    if len(selected_controls) == 8:
        break

print('authored_total', authored_total)
print('distinct_activating_noncontrols', len(distinct))
print('unchanged_controls_available', len(controls), 'selected', len(selected_controls))
print('activation_rate', round(len(distinct) / authored_total, 4))
if len(distinct) < 80:
    print('INSUFFICIENT: need at least 80 distinct discriminating non-controls')
    sys.exit(2)
if len(selected_controls) < 8:
    print('INSUFFICIENT: need at least 8 unchanged controls')
    sys.exit(2)

merged = distinct + selected_controls
for c in merged:
    c['negative_control'] = bool(c['negative_control'])

# Validate with the existing validator in an isolated tree.
with tempfile.TemporaryDirectory(prefix='secure-309-replication-') as t:
    tplan = pathlib.Path(t) / 'docs/evaluations/comprehension-2.11.1' / str(issue) / 'plan'
    tplan.mkdir(parents=True)
    shutil.copyfile(base / 'plan/rubric.json', tplan / 'rubric.json')
    (tplan / 'authored.json').write_text(json.dumps({'cases': merged}, ensure_ascii=False, indent=2), encoding='utf-8')
    proc = subprocess.run([sys.executable, str((ROOT / 'plan/validate_cases.py').resolve()), str(issue)], cwd=t, capture_output=True, text=True)
    if proc.returncode != 0:
        print('validation failed', proc.returncode)
        print(proc.stdout[-2000:])
        print(proc.stderr[-3000:])
        sys.exit(1)
    validated = json.loads((tplan / 'cases.json').read_text(encoding='utf-8'))
    shutil.copyfile(tplan / 'cases.json', pathlib.Path(t) / 'validated-cases.json')

cases = validated['cases']
print('validated', len(cases), 'controls', sum(c['negative_control'] for c in cases),
      'discard_reasons', validated['discard_reasons'])

# Preflight comparison in the frozen plan directory.
spec = importlib.util.spec_from_file_location('preflight', ROOT / 'plan/preflight_compare.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
rows = []
counts = collections.Counter()
for c in cases:
    try:
        base_payload, base_bind = mod.capture(c, issue, None)
        cand_payload, cand_bind = mod.capture(c, issue, 'ko_conjugation_split')
        same = base_payload == cand_payload
        task_equal = base_payload.get('input') == cand_payload.get('input') and base_bind == cand_bind
        rows.append({'id': c['id'], 'negative_control': c['negative_control'],
                     'full_payload_equal': same, 'task_and_bindings_equal': task_equal})
        counts['control' if c['negative_control'] else 'noncontrol'] += 1
        if not same:
            counts['control_different' if c['negative_control'] else 'different'] += 1
    except Exception as exc:
        rows.append({'id': c['id'], 'error_category': type(exc).__name__})
        counts['errors'] += 1

preflight = {'issue': issue, 'variant': 'ko_conjugation_split', 'counts': dict(counts), 'cases': rows,
             'comparison': 'Actual GatewaySession.request payloads; aliases normalized to deterministic hashes of original, token type and context. No provider or model call.'}

plan.mkdir(parents=True)
(plan / 'preflight-ko_conjugation_split.json').write_text(json.dumps(preflight, indent=2) + '\n', encoding='utf-8')
shutil.copyfile(base / 'plan/rubric.json', plan / 'rubric.json')
shutil.copyfile(base / 'plan/decision.json', plan / 'decision.json')
shutil.copyfile(base / 'plan/conditions.json', plan / 'conditions.json')

common = {}
for name in ('rubric.json', 'decision.json'):
    common[name] = hashlib.sha256((plan / name).read_bytes()).hexdigest()

noncontrol = [c for c in cases if not c['negative_control']]
changed = [r for r in rows if not r.get('negative_control') and r.get('full_payload_equal') is False]
doc = {
    'issue': issue,
    'status': 'FROZEN before interpretation; replication of the underpowered pilot',
    'provenance': 'Six independent fresh Codex case-author calls, issue body and case-format only; '
                  'discriminating cases pooled from independently authored replacement batches 1-%d. '
                  'The 27 pilot cases are not reused.' % MAX_BATCH,
    'authored_total': authored_total,
    'activation_rate': round(len(distinct) / authored_total, 6),
    'generated': authored_total,
    'accepted': len(cases),
    'discarded': 0,
    'discard_reasons': validated['discard_reasons'],
    'negative_controls': sum(c['negative_control'] for c in cases),
    'minimum_count_met': len(noncontrol) >= 80,
    'negative_control_minimum_met': sum(c['negative_control'] for c in cases) >= 8,
    'preflight_discrimination': {
        'noncontrols': len(noncontrol),
        'discriminating_noncontrols': len(changed),
        'change_rate': round(len(changed) / max(1, len(noncontrol)), 6),
        'controls': sum(c['negative_control'] for c in cases),
        'changed_controls': sum(1 for r in rows if r.get('negative_control') and r.get('full_payload_equal') is False),
        'meets_size_and_preflight': len(changed) >= 80 and all(
            r.get('full_payload_equal') is not False for r in rows if r.get('negative_control')),
        'method': 'Every distinct activating independently authored case kept; eight unchanged controls; '
                  'seed %d. Discriminating-input enrichment limits generalization.' % SEED,
    },
    'frozen_files_sha256': common,
    'cases': cases,
}
(plan / 'cases.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

n = len(cases)
budget = {
    'issue': issue,
    'planned_cases': n,
    'interpretation_conditions': 4,
    'interpretation_calls': 4 * n,
    'fresh_grading_calls': n,
    'optional_regrades_max': n,
    'expected_initial_calls': 5 * n,
    'maximum_calls_including_one_regrade_per_case': 6 * n,
    'interpretation_output_cap': 512,
    'grading_output_cap': 2048,
    'model': 'gpt-6.1-sol',
    'reasoning_effort': 'low',
    'estimate_basis': 'Pilot #309 means: 15424 raw / 331 content per interpretation, 16145 raw / 1052 content per one-response grade.',
    'accounting': 'Per-call content recorded from reported usage minus same-session minimal-prompt overhead.',
    'authoring': 'Independent fresh author calls, reported separately in replacement-batch*-metadata.json.',
}
(plan / 'budget.json').write_text(json.dumps(budget, indent=2) + '\n', encoding='utf-8')
(plan / 'model.json').write_text(json.dumps({'model': 'gpt-6.1-sol', 'reasoning_effort': 'low',
                                            'login_method': 'chatgpt', 'interpreter_grader_family': 'same model family'},
                                           indent=2) + '\n', encoding='utf-8')
print('FROZEN', plan, 'cases', n, 'discriminating', len(changed))
