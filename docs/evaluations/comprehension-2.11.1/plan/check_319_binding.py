"""Verify #319 alias binding for a candidate case file without any model call.

Binding rule (from the binding pre-check): every declared gold numeric span must
correspond to exactly one gateway alias in the baseline payload, and no gold
value may remain visible in the masked task text.
"""
import json, pathlib, sys
from secure_gateway import gateway

ROOT = pathlib.Path('docs/evaluations/comprehension-2.11.1')
path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / '319/plan/cases.json'
doc = json.loads(path.read_text(encoding='utf-8'))
cases = doc['cases'] if isinstance(doc, dict) else doc

passed, failed = [], []
for c in cases:
    reason = None
    try:
        s = gateway.GatewaySession(natural_language='auto')
        s.forced_rules = lambda: tuple(c.get('forced_terms', ()))
        payload = s.request({'model': 'fixture', 'input': [{'role': 'user', 'content': c['original']}]})
        aliases = {str(v.surrogate): str(v.original) for v in s.session.reverse_store.values()}
        masked = payload['input'][0]['content']
        gold = [x['text'] for x in c['sensitive_spans']]
        for text in gold:
            matches = [a for a, original in aliases.items() if original == text]
            if len(matches) != 1:
                reason = 'unbound_gold_span'
                break
            if text in masked:
                reason = 'gold_value_visible'
                break
        if reason is None and any(x['text'] not in c['original'] for x in c['sensitive_spans']):
            reason = 'gold_span_not_substring'
    except Exception as exc:
        reason = 'exception_' + type(exc).__name__
    (failed if reason else passed).append(c['id'] if not reason else (c['id'], reason))

total_noncontrol = sum(1 for c in cases if not c['negative_control'])
print(json.dumps({'file': str(path), 'cases': len(cases), 'noncontrols': total_noncontrol,
                  'bound': len(passed), 'failed': len(failed), 'failures': failed[:40]}, ensure_ascii=False, indent=2))
