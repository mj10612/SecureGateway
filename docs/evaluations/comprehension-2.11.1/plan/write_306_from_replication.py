"""Derive the #306 descriptive A/B/C/D summary from the shared #309 replication run.

#306 has no separate candidate: its budget records zero interpretation calls and
shares #309's cases and grader. This script only re-reads the frozen #309
replication manifest, first responses and grades; it makes no model call.
"""
import json, pathlib, sys

ROOT = pathlib.Path('docs/evaluations/comprehension-2.11.1')
src = ROOT / '309/comprehension-replication'
dst = ROOT / '306/comprehension-replication'
manifest = json.loads((src / 'manifest.json').read_text(encoding='utf-8'))
grades = [json.loads(x) for x in (src / 'first-grades.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
by_case = {g['case_id']: g for g in grades}
cases = {c['case_id']: c for c in manifest['cases']}

rows = []
for cid, case in cases.items():
    g = by_case.get(cid)
    if not g or g.get('status') != 'completed':
        rows.append({'case_id': cid, 'status': 'ungraded'})
        continue
    arms = {}
    for verdict in g['attempts'][-1]['result']['grades']:
        label, criterion = verdict['id'].split('::', 1)
        arms.setdefault(g['blind_labels'][label], {})[criterion] = verdict['passed']
    rows.append({'case_id': cid, 'negative_control': case['negative_control'],
                 'arms': arms, 'allpass': {k: all(v.values()) for k, v in arms.items()}})

eligible = [r for r in rows if r.get('allpass', {}).get('A')]
controls = [r for r in eligible if r['negative_control']]
summary = {
    'issue': 306,
    'status': 'descriptive only; no separate candidate or decision',
    'shared_run': str(src),
    'cases': len(manifest['cases']),
    'graded': sum(1 for r in rows if 'allpass' in r),
    'ungraded': sum(1 for r in rows if 'allpass' not in r),
    'analysis_set': len(eligible),
    'whole_task_passes': {arm: sum(r['allpass'].get(arm, False) for r in eligible) for arm in ('A', 'B', 'C', 'D1')},
    'negative_control_passes': {arm: sum(r['allpass'].get(arm, False) for r in controls) for arm in ('A', 'B', 'C', 'D1')},
    'B_vs_C': {
        'B_only': sum(not r['allpass'].get('C') and r['allpass'].get('B') for r in eligible),
        'C_only': sum(r['allpass'].get('C') and not r['allpass'].get('B') for r in eligible),
    },
    'frozen_rubric_sha256': __import__('hashlib').sha256((src / 'frozen-rubric.json').read_bytes()).hexdigest(),
    'frozen_decision_sha256': __import__('hashlib').sha256((src / 'frozen-decision.json').read_bytes()).hexdigest(),
    'limitation': 'Interpreter and grader are the same model family; cases are enriched for observable C/D differences. '
                  'Human-minimal B masking is author-provided, not engine output.',
}
dst.mkdir(parents=True, exist_ok=True)
(dst / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for name in ('frozen-rubric.json', 'frozen-decision.json'):
    (dst / name).write_bytes((src / name).read_bytes())
print(json.dumps(summary, ensure_ascii=False, indent=2))
