import collections,hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];issues=[291,309,310,311,312,313,314,315,316,317,318,319];failures=[]
def check(test,category):
 if not test:failures.append(category)
for n in issues:
 p=root/str(n)/'plan';cases=json.loads((p/'cases.json').read_text(encoding='utf-8'));rubric=json.loads((p/'rubric.json').read_text(encoding='utf-8'));author=json.loads((p/'author-metadata.json').read_text(encoding='utf-8'));allowed={x['id'] for x in rubric['criteria']};data=cases['cases']
 check(len(data)==cases['accepted'] and cases['minimum_count_met'] and cases['negative_control_minimum_met'],f'{n}:size_or_controls')
 check(all(all(x.get(k) for k in ('id','pass','fail','positive_example','negative_example')) for x in rubric['criteria']),f'{n}:rubric')
 run=next((x for x in author['runs'] if x['status']=='current_holdout'),{});check(run.get('completed_and_no_tool_events_verified') and run.get('sha256')==hashlib.sha256((p/'authored.json').read_bytes()).hexdigest(),f'{n}:author_provenance')
 for item in author['runs']:
  if item.get('status') in ('targeted_source','targeted_policy'):
   check(item.get('completed_and_no_tool_events_verified') and item.get('sha256')==hashlib.sha256((p/item['file']).read_bytes()).hexdigest(),f'{n}:targeted_provenance')
  elif item.get('status')=='derived_targeted':
   check(item.get('sha256')==hashlib.sha256((p/item['file']).read_bytes()).hexdigest() and all((p/x).exists() for x in item.get('sources',[])),f'{n}:derived_provenance')
 for c in data:
  check(set(c['applicable'])<=allowed,f'{n}:criterion_id')
  for values in c.get('applicable_by_condition',{}).values():check(set(values)<=allowed,f'{n}:condition_criterion_id')
  for kind in ('sensitive_spans','public_spans'):
   for span in c[kind]:check(c['original'][span['start']:span['end']]==span['text'],f'{n}:offset')
 if n==291:
  expected={'ar','bn','de','en','es','fr','hi','id','ja','ko','mr','pt','ru','te','tr','ur','zh'};counts=collections.Counter(c.get('language') for c in data if not c['id'].startswith('known-'));check(set(counts)==expected and all(v==2 for v in counts.values()),'291:language_coverage')
 if n==311:check(sum(c['private_category'] for c in data)>=8 and sum(c['role_relation_applicable'] for c in data)>=20,'311:role_coverage')
 if n==315:
  tags=collections.Counter(t for c in data for t in c['subtypes']);check(all(tags[x]>=8 for x in ('solvable_without_original','hidden_value_limit','alias_identity','tool_alias','injection_resistance')),'315:subtype_coverage')
 if n==317:
  tags=collections.Counter(t for c in data for t in c['applicability']);check(tags['cell_identity']>=20 and tags['cell_prohibition']>=8 and tags['missing_cell']>=8,'317:subtype_coverage')
 if n==319:
  tags=collections.Counter(c['label'] for c in data);check(tags['tool_solvable']>=8 and tags['no_calculation']>=4 and tags['impossible']>=4,'319:case_mix')
for name in ('cases.json','rubric.json'):
 shared=json.loads((root/'306'/'plan'/name).read_text(encoding='utf-8'))
 check(shared['shared_source_sha256']==hashlib.sha256((root/'309'/'plan'/name).read_bytes()).hexdigest(),f'306:shared_{name}')
for n,name in [(310,'protection-cases.json'),(312,'protection-cases.json'),(316,'protection-scoped-cases.json'),(318,'protection-structured-cases.json')]:
 d=json.loads((root/str(n)/'plan'/name).read_text(encoding='utf-8'));ss=pp=0
 for c in d['cases']:
  for kind in ('sensitive_spans','public_spans'):
   for span in c[kind]:check(c['original'][span['start']:span['end']]==span['text'],f'{n}:protection_offset')
  ss+=len(c['sensitive_spans']);pp+=len(c['public_spans'])
 check(ss>=100 and pp>=100,f'{n}:protection_minimum')
 if n==318:
  check(all(c['trusted_local_policy']['document_sha256']==hashlib.sha256(c['original'].encode('utf-8')).hexdigest() for c in d['cases']),'318:policy_hash')
print('Plan audit:', 'PASS' if not failures else 'FAIL', '; issues:',len(issues),'; failure categories:',dict(collections.Counter(failures)))
sys.exit(bool(failures))
