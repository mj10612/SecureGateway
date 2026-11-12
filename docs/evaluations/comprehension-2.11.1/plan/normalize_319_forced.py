"""Declare each authored confidential operand as a forced rule, then re-check binding.

The author declares gold numeric spans; the gateway only binds them if the span is
recognized as confidential. Forced rules are the approved mechanism for that
declaration and take priority over any keep-public logic.
"""
import json, pathlib, sys

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
doc = json.loads(src.read_text(encoding='utf-8'))
cases = doc['cases'] if isinstance(doc, dict) else doc
changed = 0
for c in cases:
    spans = [x['text'] for x in c.get('sensitive_spans', [])]
    if spans and c.get('forced_terms') != spans:
        c['forced_terms'] = spans
        changed += 1
out = doc if isinstance(doc, dict) else {'cases': cases}
if isinstance(doc, dict):
    out['forced_rule_normalization'] = 'Each declared gold numeric operand is declared as a forced rule; no value was altered.'
out.setdefault('cases', cases)
dst.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('normalized', changed, 'cases ->', dst)
