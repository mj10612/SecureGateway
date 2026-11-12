import importlib.util,json,random
from pathlib import Path
from secure_gateway.structure_parser import parse_structure
r=Path('docs/evaluations/comprehension-2.11.1');p=r/'317/plan';cases=json.loads((p/'policy-cases.json').read_text(encoding='utf-8'))['cases'];sp=importlib.util.spec_from_file_location('pc',r/'plan/preflight_compare.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);counts={'noncontrol':0,'different':0,'control':0,'control_different':0,'errors':0};rows=[]
for c in cases:
 try:
  b,_=m.capture(c,317,None);d,_=m.capture(c,317,'doc_structure_policy');changed=b!=d;k='control' if c['negative_control'] else 'noncontrol';counts[k]+=1
  if changed:counts['control_different' if k=='control' else 'different']+=1
  rows.append({'id':c['id'],'negative_control':c['negative_control'],'full_payload_equal':not changed})
 except Exception as e:counts['errors']+=1;rows.append({'id':c['id'],'error_category':type(e).__name__})
(p/'preflight-doc_structure_policy-selected.json').write_text(json.dumps({'issue':317,'variant':'doc_structure_policy','counts':counts,'cases':rows},indent=2)+'\n',encoding='utf-8');index={x['id']:x for x in rows};sample=random.Random(20261111+317).sample(cases,10);reviews=[]
for c in sample:
 entry=index[c['id']];neg=c['negative_control'];cells=len(parse_structure(c['original']).cells);labels=c.get('sensitive_field_labels',[]);clear=(entry.get('full_payload_equal') is True if neg else bool(cells and labels and entry.get('full_payload_equal') is False));detail='unchanged unstructured negative control' if neg else ('structured cell with explicit confidential field policy; candidate differs' if clear else 'structured field path or candidate effect not established');reviews.append({'id':c['id'],'clearly_exercises':clear,'assessment':detail})
k=sum(x['clearly_exercises'] for x in reviews);out={'issue':317,'variant':'doc_structure_policy','sample_seed':20261111+317,'clearly_exercises':k,'sample_size':10,'passes':k>=8,'samples':reviews};(p/'semantic-review-policy.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');(p/'semantic-review-policy.md').write_text('# Structure-policy sample review\n\n'+''.join('- '+x['id']+': '+x['assessment']+'\n' for x in reviews)+f'\nClearly exercises: {k}/10.\n',encoding='utf-8');print('317 policy preflight',json.dumps(counts),'semantic sample',k,'of 10')
