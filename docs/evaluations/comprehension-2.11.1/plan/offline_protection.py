import argparse,contextlib,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
from secure_gateway import evaluation
from secure_gateway.experiment_profiles import candidate_profile
root=Path('docs/evaluations/comprehension-2.11.1')
variants={309:['ko_conjugation_split'],313:['segment_language'],315:['instruction_concise','instruction_examples'],317:['doc_structure_policy'],311:[311],312:['numeric_context'],310:[310],316:[316],318:[318],319:['local_arithmetic']}
source={309:(310,'protection-cases.json'),313:(310,'protection-cases.json'),315:(310,'protection-cases.json'),317:(318,'protection-structured-cases.json'),311:(310,'protection-cases.json'),312:(312,'protection-cases-corrected.json'),310:(310,'introducer-cases.json'),316:(316,'protection-scoped-cases.json'),318:(318,'protection-structured-cases.json'),319:(310,'protection-cases.json')}
def case_config(issue,c,variant):
 if issue==311:return {'allow_roles':True,'confidential_roles':False}
 if issue in (316,318):return c['trusted_local_policy']
 if issue==317:return {'field_policy':{s['field']:'always_mask' for s in c['sensitive_spans'] if 'field' in s}}
 return None
def makecase(c):
 field=['input',0,'content'];secrets=[];public=[]
 for s in c['sensitive_spans']:
  text=s['text'];fragments=sorted({text[i:i+2] for i in range(len(text)-1)})
  secrets.append({'path':field,'start':s['start'],'end':s['end'],'fragments':fragments,'label':'synthetic','policy':'contextual','severity':'standard'})
 for s in c['public_spans']:public.append({'path':field,'start':s['start'],'end':s['end'],'label':'synthetic-public'})
 return {'id':c['id'],'language':'en','language_mode':'auto','domain':'general','dialect':'codex','payload':{'model':'fixture','input':[{'role':'user','content':c['original']}]},'echo_path':field,'task_path':field,'secrets':secrets,'public':public,'forced_terms':c.get('forced_terms',[]),'rubric':[],'human_text':'','smoke':True}
def visible(x):return bool(x['full_exposure'] or x['partial_exposure'] or x.get('alignment_ambiguous',False))
def encode_result(raw):
 return {'roundtrip':raw['roundtrip'],'replay':raw['replay'],'payload_sha256':hashlib.sha256(json.dumps(raw['outbound'],sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest(),'secrets':[{'full':x['full_exposure'],'partial':x['partial_exposure'],'ambiguous':x.get('alignment_ambiguous',False)} for x in raw['secrets']],'public':[{'overmasked':x['overmasked'],'ambiguous':x.get('alignment_ambiguous',False)} for x in raw['public']]}
def isexposed(x):return x['full'] or x['partial'] or x['ambiguous']
def selected_ci_policy(issue,variant,cases):
 if issue==311:return {'allow_roles':True,'confidential_roles':False}
 if issue in (316,318):return cases[0]['trusted_local_policy']
 if issue==317:return {'field_policy':{s['field']:'always_mask' for s in cases[0]['sensitive_spans'] if 'field' in s}}
 return None
def ci_gate(issue,variant,cases,out):
 path=out/'ci-candidate';out.mkdir(parents=True,exist_ok=True)
 if (path/'report.json').exists():raise ValueError('Existing report is immutable')
 with candidate_profile(variant,selected_ci_policy(issue,variant,cases)):
  result=evaluation.run_privacy(evaluation.load_corpus(None),output_dir=path,profile='release',max_seconds=600)
 if result['status']!='completed':return {'status':'incomplete','exit_code':None}
 exe=shutil.which('secure-gateway')
 if not exe:return {'status':'incomplete','error_category':'CliUnavailable'}
 proc=subprocess.run([exe,'evaluate','compare','--baseline',str(root/'../issue324-2.7.0/legacy-privacy/report.json'),'--candidate',str(path/'report.json')],capture_output=True,timeout=120)
 try:comparison=json.loads(proc.stdout.decode('utf-8'))
 except (ValueError,UnicodeError):return {'status':'incomplete','exit_code':proc.returncode,'error_category':'ComparisonOutputInvalid'}
 evaluation.write_json(out/'ci-comparison.json',comparison)
 return {'status':'passed' if proc.returncode==0 and comparison.get('comparable') and not comparison.get('regression') else 'failed','exit_code':proc.returncode,'new_exposure_count':len(comparison.get('new_exposures',[])),'integrity_regression_count':len(comparison.get('integrity_regressions',[]))}
def role_category_guard():
 fixtures=json.loads((root/'311/plan/private-role-cases.json').read_text(encoding='utf-8'))['cases'];records=[]
 for c in fixtures:
  try:
   category=c['private_category'];start=c['original'].index(category);spans=[c['secret_span'],{'start':start,'end':start+len(category),'text':category}];fixture={'id':c['id'],'original':c['original'],'sensitive_spans':spans,'public_spans':[],'forced_terms':c['forced_terms']};inp=makecase(fixture)
   with candidate_profile(311,{'allow_roles':True,'confidential_roles':True}):out=evaluation._capture_case(inp,max_seconds=40)
   payload=json.dumps(out['outbound'],ensure_ascii=False);leak=bool(re.search(r'(?<![A-Za-z])'+re.escape(category)+r'(?![A-Za-z])',payload,re.IGNORECASE));records.append({'id':c['id'],'category_leaked':leak,'exact_restore':out['roundtrip']})
  except Exception as e:records.append({'id':c['id'],'error_category':type(e).__name__})
 return {'cases':len(records),'error_count':sum('error_category' in x for x in records),'category_leaks':sum(x.get('category_leaked',False) for x in records),'records':records}
def run(issue,variant):
 src,file=source[issue];cases=json.loads((root/str(src)/'plan'/file).read_text(encoding='utf-8'))['cases'];out=root/str(issue)/'offline'/str(variant)
 if out.exists():raise ValueError('Offline output already exists')
 out.mkdir(parents=True);records=[];incomplete=False
 for c in cases:
  try:
   inp=makecase(c);base=evaluation._capture_case(inp,max_seconds=40)
   with candidate_profile(variant,case_config(issue,c,variant)):cand=evaluation._capture_case(inp,max_seconds=40)
   records.append({'id':c['id'],'C':encode_result(base),'D':encode_result(cand)})
  except Exception as e:
   incomplete=True;records.append({'id':c['id'],'error_category':type(e).__name__})
  evaluation.write_json(out/'occurrences.json',{'status':'incomplete' if incomplete else 'running','cases':records})
 if incomplete:return {'issue':issue,'variant':str(variant),'status':'incomplete','error_category':'CaseCaptureFailed'}
 new_exp=protected=old_exp=new_over=old_over=new_round=old_round=0
 for rec in records:
  old_round+=rec['C']['roundtrip'];new_round+=rec['D']['roundtrip']
  for index,(a,b) in enumerate(zip(rec['C']['secrets'],rec['D']['secrets'])):
   was=isexposed(a);now=isexposed(b);old_exp+=was;new_exp+=now
   if not was and now:rec.setdefault('new_exposed_indices',[]).append(index)
   if was and not now:protected+=1
  old_over+=sum(x['overmasked'] for x in rec['C']['public']);new_over+=sum(x['overmasked'] for x in rec['D']['public'])
 newly_exposed=sum(len(x.get('new_exposed_indices',[])) for x in records)
 role=role_category_guard() if issue==311 else None;ci=ci_gate(issue,variant,cases,out);status='completed' if ci['status']!='incomplete' and (role is None or role['error_count']==0) else 'incomplete';gate=not newly_exposed and new_round>=old_round and ci['status']=='passed' and (role is None or role['category_leaks']==0)
 result={'issue':issue,'variant':str(variant),'status':status,'dataset':f'#{src}/{file}','cases':len(cases),'sensitive_spans':sum(len(x['C']['secrets']) for x in records),'public_spans':sum(len(x['C']['public']) for x in records),'baseline_exposed':old_exp,'candidate_exposed':new_exp,'newly_exposed':newly_exposed,'newly_protected':protected,'baseline_overmasked':old_over,'candidate_overmasked':new_over,'net_overmask_increase':new_over-old_over,'baseline_exact_restore':old_round,'candidate_exact_restore':new_round,'ci':ci,'private_role_guard':role,'protection_gate_passed':gate,'limitations':['Loopback synthetic HTTP only, not real provider certification.','Case-specific trusted policies are local fixtures.','The legacy CI corpus uses one frozen policy for process-local scoped candidates, while the new protection corpus exercises case-specific policies.']}
 evaluation.write_json(out/'occurrences.json',{'status':status,'cases':records});evaluation.write_json(out/'summary.json',result);return result
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--issue',type=int,required=True,choices=sorted(variants));parser.add_argument('--run',action='store_true');args=parser.parse_args()
 if not args.run:print('Offline protection runner prepared; add --run to execute.');return 0
 failures=0
 for v in variants[args.issue]:
  try:
   result=run(args.issue,v);print(args.issue,str(v),'status',result['status'],'protection_gate',result.get('protection_gate_passed'),flush=True);failures+=result['status']!='completed'
  except Exception as e:
   print(args.issue,str(v),'error_category',type(e).__name__,flush=True);failures+=1
 return int(bool(failures))
if __name__=='__main__':sys.exit(main())
