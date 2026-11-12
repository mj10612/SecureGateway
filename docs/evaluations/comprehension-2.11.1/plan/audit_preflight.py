import json,sys
from pathlib import Path
r=Path('docs/evaluations/comprehension-2.11.1');targets=[(309,'ko_conjugation_split'),(310,'310'),(311,'311'),(312,'numeric_context'),(313,'segment_language'),(314,'vocab_calibrated'),(315,'instruction_concise'),(315,'instruction_examples'),(316,'316'),(317,'doc_structure'),(317,'doc_structure_policy-selected'),(318,'318'),(319,'local_arithmetic')];bad=[];out=[]
for n,v in targets:
 p=r/str(n)/'plan';f=p/f'preflight-{v}.json'
 if not f.exists():bad.append(f'{n}:{v}:missing');continue
 d=json.loads(f.read_text(encoding='utf-8'));c=d['counts'];special=n in (315,319);control_bad=c['control_task_different'] if special else c['control_different'];ratio=c['different']/c['noncontrol'] if c['noncontrol'] else 0;minimum=n in (309,311,313,314,315,317);size=ratio>=.7 if minimum else True
 review=p/('semantic-review-policy.json' if v=='doc_structure_policy-selected' else 'semantic-review.json')
 reviewed=json.loads(review.read_text(encoding='utf-8')).get('passes',False) if review.exists() else False
 if control_bad or c['errors'] or not size or not reviewed:bad.append(f'{n}:{v}')
 out.append({'issue':n,'variant':v,'different_noncontrol':c['different'],'noncontrol':c['noncontrol'],'control_regressions':control_bad,'errors':c['errors'],'ratio':ratio,'semantic_review_passed':reviewed,'required_70_percent':minimum,'passes':not(control_bad or c['errors']) and size and reviewed,'analysis_set_different':'pending A grading'})
result={'status':'PASS' if not bad else 'INCOMPLETE','blocked_variants':bad,'candidates':out,'notes':['#315 and #319 compare masked task and active alias bindings on controls; instruction/tool definition deliberately differs.','#317 variants have separate selected case sets.','Analysis-set counts cannot exist before the original-text control has been graded.']};(r/'plan/preflight-status.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('Preflight',result['status'],'blocked',bad);sys.exit(bool(bad))
