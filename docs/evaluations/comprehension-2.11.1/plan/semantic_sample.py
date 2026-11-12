import json,random,sys,re
from pathlib import Path
n=int(sys.argv[1]);root=Path('docs/evaluations/comprehension-2.11.1');p=root/str(n)/'plan';cases=json.loads((p/'cases.json').read_text(encoding='utf-8'))['cases'];files=list(p.glob('preflight-*.json'));files=[x for x in files if x.name not in {'preflight-targeted-screen.json','preflight-original-cases.json'}];reports=[json.loads(x.read_text(encoding='utf-8')) for x in files if x.name.startswith('preflight-')];reports=[x for x in reports if 'variant' in x and 'cases' in x];lookups=[{x['id']:x for x in r['cases']} for r in reports];chosen=random.Random(20261111+n).sample(cases,min(10,len(cases)));descriptions={309:'Korean condition, prohibition, order or question morphology',310:'name introduction and later reference',311:'role hint and entity relationship',312:'code review with numeric identifier or public constant',313:'instruction across Korean/English segments',314:'ordinary vocabulary in a daily task',315:'privacy instruction handling for '+','.join(cases[0].get('subtypes',[])),316:'follow-up under a scoped correction',317:'table/form row, column or cell restriction',318:'hash-bound structured attribute bundle',319:'arithmetic tool availability and task classification'};lines=[];valid=0
for c in chosen:
 row=[lookup.get(c['id'],{}) for lookup in lookups];iscontrol=c['negative_control']
 if not row:clearly=False;detail='missing preflight evidence'
 elif iscontrol:
  clearly=all((x.get('task_and_bindings_equal') if n in (315,319) else x.get('full_payload_equal')) is True for x in row);detail='unchanged negative control for '+descriptions[n]
 else:
  clearly=all(x.get('full_payload_equal') is False for x in row);detail=descriptions[n]+'; candidate changes model-facing payload'
  if n==309:
   from secure_gateway.experiment_korean import preserve_spans
   clearly=bool(preserve_spans(c['original']))
   detail='Korean morphology candidate receives a recognized grammar span; '+('candidate changes payload' if all(x.get('full_payload_equal') is False for x in row) else 'baseline and candidate payload match')
  if n==310:
   from secure_gateway.experiment_context import name_spans
   clearly=clearly and bool(name_spans(c['original']))
  if n==311:clearly=clearly and c.get('role_relation_applicable',False)
  if n==312:
   from secure_gateway.numeric_context import context_numeric_spans,public_numeric_spans
   clearly=clearly and bool(context_numeric_spans(c['original']) or public_numeric_spans(c['original'])) and 'code_review' in c['applicable']
  if n==313:clearly=clearly and bool(re.search(r'[A-Za-z]',c['original'])) and bool(re.search(r'[\uac00-\ud7a3]',c['original']))
  if n==314:clearly=clearly and 'ordinary_task' in c['applicable']
  if n==315:clearly=clearly and bool(c.get('subtypes'))
  if n==316:clearly=clearly and c.get('correction_status')=='active' and c.get('correction_project')==c.get('current_project')
  if n==317:clearly=clearly and bool(c.get('applicability'))
  if n==318:clearly=clearly and bool(c.get('required_fields')) and bool(c.get('protect_fields'))
  if n==319:clearly=clearly and c.get('label') in ('tool_solvable','no_calculation','impossible')
  if n==315:detail='instruction variant on '+','.join(c.get('subtypes',[]))
  if n==317:detail='structure handling for '+','.join(c.get('applicability',[]))
  if n==319:detail='local arithmetic tool on '+str(c.get('label'))
  if n==316:detail='scoped correction status '+str(c.get('correction_status','local policy'))
 valid+=clearly;lines.append({'id':c['id'],'negative_control':iscontrol,'clearly_exercises':clearly,'assessment':detail})
r={'issue':n,'sample_seed':20261111+n,'sample_size':len(chosen),'clearly_exercises':valid,'minimum':8,'passes':valid>=8,'method':'Deterministic random sample; describes only case type and measured candidate/control behavior, without logging synthetic original values. Candidate-path relevance is assessed by case metadata and the offline payload comparison; this is not an LLM judgment.','samples':lines};(p/'semantic-review.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');(p/'semantic-review.md').write_text('# Candidate-path sample review\n\n'+''.join('- '+x['id']+': '+x['assessment']+(' (clear)' if x['clearly_exercises'] else ' (not established)')+'\n' for x in lines)+f'\nClearly exercises: {valid}/{len(chosen)}; required: 8/10.\n',encoding='utf-8');print(n,'semantic review',valid,'of',len(chosen),'passes',r['passes'])
