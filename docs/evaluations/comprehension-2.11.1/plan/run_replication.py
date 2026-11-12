"""Real-LLM runner: frozen first responses, then one blind multi-response grade per case."""
import argparse,concurrent.futures,contextlib,hashlib,json,math,os,random,shutil,sys,tempfile,time,uuid
from pathlib import Path
from secure_gateway import gateway,evaluation
from secure_gateway.experiment_profiles import candidate_profile
from secure_gateway.evaluation_diagnostics import diagnostic_worker,ObservedWorkerFailure
from secure_gateway.evaluation_worker import capture_worker_process
from secure_gateway.evaluation_codex_worker import _parse_events
ROOT=Path('docs/evaluations/comprehension-2.11.1');PLAN='plan-replication';OUT='comprehension-replication';MODEL='gpt-6.1-sol';EFFORT='low';WORKERS=1
VARIANTS={315:['instruction_concise','instruction_examples'],317:['doc_structure_policy'],311:[311],312:['numeric_context'],310:[310],316:[316],318:[318],309:['ko_conjugation_split'],313:['segment_language']}
def sha(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
def config(n,c,v):
 if n==311:return {'allow_roles':True,'confidential_roles':c['private_category']}
 if n in (316,318):return c['trusted_local_policy']
 if n==317:return {'field_policy':{x:'always_mask' for x in c.get('sensitive_field_labels',[])}}
 return None
def capture(n,c,v):
 cm=contextlib.nullcontext() if v is None else candidate_profile(v,config(n,c,v))
 with cm:
  s=gateway.GatewaySession(natural_language='auto');s.forced_rules=lambda:tuple(c.get('forced_terms',()))
  payload=s.request({'model':'fixture','input':[{'role':'user','content':c['original']}]})
  aliases={m.surrogate:m.original for m in s.session.reverse_store.values()}
  return {'instructions':payload.get('instructions',''),'input':payload['input'][0]['content'],'aliases':aliases}
def token_baseline():
 path=ROOT/'plan/overhead-calibration.json'
 if path.exists():return json.loads(path.read_text(encoding='utf-8'))['input_tokens']
 codex=shutil.which('codex')
 if not codex:raise ValueError('CodexUnavailable')
 allowed={'PATH','HOME','USERPROFILE','CODEX_HOME','SYSTEMROOT','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL','LC_CTYPE','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy','SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE','NODE_EXTRA_CA_CERTS'};env={k:v for k,v in os.environ.items() if k in allowed}
 with tempfile.TemporaryDirectory(prefix='secure-eval-overhead-') as t:
  out=Path(t)/'last.txt';cmd=[codex,'exec','--ephemeral','--skip-git-repo-check','--ignore-user-config','--ignore-rules','--sandbox','read-only','--model',MODEL,'--json','--output-last-message',str(out),'-c','forced_login_method="chatgpt"','-c','project_doc_max_bytes=0','-c','developer_instructions=""','-c','web_search="disabled"','-c','features.multi_agent=false','-c','model_reasoning_effort="low"','-']
  result=capture_worker_process(cmd,b'Hi',timeout=300,cwd=Path(t),env=env,new_process_group=True);usage=_parse_events(result.stdout)
 if not usage or type(usage.get('input_tokens')) is not int:raise ValueError('OverheadUsageUnavailable')
 evaluation.write_json(path,{'model':MODEL,'reasoning_effort':EFFORT,'input_tokens':usage['input_tokens'],'reported_usage':usage,'fresh_session':True,'tool_events':0,'method':'Minimal one-word prompt under identical CLI flags; raw input count is the fixed overhead baseline.'});return usage['input_tokens']
def newmanifest(issue):
 if issue==317:cases=json.loads((ROOT/'317/plan/policy-cases.json').read_text(encoding='utf-8'))['cases']
 else:cases=json.loads((ROOT/str(issue)/PLAN/'cases.json').read_text(encoding='utf-8'))['cases']
 rubric=json.loads((ROOT/str(issue)/PLAN/'rubric.json').read_text(encoding='utf-8'));lookup={x['id']:x for x in rubric['criteria']};jobs=[];entries=[]
 for c in cases:
  baseline=capture(issue,c,None);arms={'A':{'instructions':baseline['instructions'],'input':c['original'],'aliases':{}},'C':baseline}
  if issue==309:arms['B']={'instructions':baseline['instructions'],'input':c['human_masked'],'aliases':{}}
  for i,variant in enumerate(VARIANTS[issue],1):
   candidate=capture(issue,c,variant)
   if issue==315:
    # Instruction is the sole treatment: reuse the exact baseline task and
    # alias binding, including any randomly generated numeric surrogates.
    candidate={'instructions':candidate['instructions'],'input':baseline['input'],'aliases':baseline['aliases']}
   arms['D'+str(i)]=candidate
  entry={'case_id':c['id'],'original':c['original'],'expected':c['expected'],'negative_control':c['negative_control'],'applicable':c['applicable'],'arms':arms};entries.append(entry)
  for label,arm in arms.items():
   request={'role':'interpret','job_id':sha([issue,c['id'],label])[:32],'model':MODEL,'max_output_tokens':512,'reasoning_effort':EFFORT,'messages':[{'role':'system','content':arm['instructions']},{'role':'user','content':arm['input']}]};jobs.append({'case_id':c['id'],'arm':label,'request':request})
 random.Random(20261111+issue).shuffle(jobs)
 return {'schema_version':1,'issue':issue,'model':MODEL,'effort':EFFORT,'source_cases_sha256':sha(cases),'rubric_sha256':sha(rubric),'cases':entries,'jobs':jobs,'criterion_definitions':lookup,'repeats':1,'shuffle_seed':20261111+issue,'disclosure':'Model and grader are same model family; per-case alias mappings are synthetic and available only to local grading.'}
def path_for(issue):return ROOT/str(issue)/OUT
def run_identity(issue):
 paths=sorted(Path('src/secure_gateway').rglob('*.py'))+[Path(__file__)]+sorted((ROOT/str(issue)/PLAN).glob('*.json'))
 return sha([[str(p),hashlib.sha256(p.read_bytes()).hexdigest()] for p in paths])
def prepare(issue):
 out=path_for(issue);out.mkdir(parents=True,exist_ok=True);path=out/'manifest.json'
 if path.exists():
  m=json.loads(path.read_text(encoding='utf-8'))
  if m.get('run_identity')!=run_identity(issue):raise ValueError('RunIdentityMismatch')
  return m
 for v in VARIANTS[issue]:
  f=ROOT/str(issue)/'offline'/('318-bundle-table' if issue==318 else str(v))/'summary.json'
  if not f.exists() or json.loads(f.read_text(encoding='utf-8'))['status']!='completed':raise ValueError('OfflineGateMissing')
 m=newmanifest(issue);m['run_identity']=run_identity(issue)
 for name in ('rubric.json','decision.json'):
  shutil.copyfile(ROOT/str(issue)/PLAN/name,out/('frozen-'+name))
 evaluation.write_json(path,m);return m
def read_rows(path):
 if not path.exists():return []
 return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
def append_row(path,row):
 with path.open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def observed(request,baseline):
 start=time.monotonic()
 try:
  result=diagnostic_worker(request);usage=result.get('usage')
  if not usage or 'input_tokens' not in usage or 'output_tokens' not in usage:return {'status':'failed','error_category':'UsageUnavailable','elapsed_seconds':time.monotonic()-start}
  return {'status':'completed','result':result,'elapsed_seconds':time.monotonic()-start,'raw_tokens':usage['input_tokens']+usage['output_tokens'],'content_tokens':usage['input_tokens']-baseline+usage['output_tokens']}
 except ObservedWorkerFailure as exc:
  return {'status':'failed','error_category':exc.diagnostics.get('code','unclassified_failure'),'usage_known':exc.usage is not None,'elapsed_seconds':time.monotonic()-start}
 except Exception as exc:return {'status':'failed','error_category':type(exc).__name__,'usage_known':False,'elapsed_seconds':time.monotonic()-start}
def interpret(m,out,baseline):
 path=out/'first-responses.jsonl';existing=read_rows(path);jobs={x['request']['job_id']:x for x in m['jobs']};done=set()
 for row in existing:
  job=jobs.get(row.get('job_id'));result=row.get('result',{});metadata=result.get('metadata',{});usage=result.get('usage',{})
  if not job or row['job_id'] in done or row.get('case_id')!=job['case_id'] or row.get('arm')!=job['arm'] or row.get('status')!='completed' or result.get('job_id')!=row['job_id'] or not isinstance(result.get('response'),str) or not result['response'] or metadata.get('fresh_session') is not True or metadata.get('tool_events')!=0 or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('input_tokens','output_tokens')):raise ValueError('InvalidSavedResponse')
  done.add(row['job_id'])
 if any(r['status']!='completed' for r in existing):return False
 pending=[x for x in m['jobs'] if x['request']['job_id'] not in done]
 if existing:append_row(out/'resume-log.jsonl',{'event':'resume','run_identity':m['run_identity'],'saved_valid_responses':len(done),'remaining_responses':len(pending),'timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
 for pos in range(0,len(pending),WORKERS):
  batch=pending[pos:pos+WORKERS];failed=False
  with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
   futures={pool.submit(observed,j['request'],baseline):j for j in batch}
   for f in concurrent.futures.as_completed(futures):
    job=futures[f];row={'job_id':job['request']['job_id'],'case_id':job['case_id'],'arm':job['arm'],**f.result()};append_row(path,row);failed|=row['status']!='completed'
  print('interpretation completed',min(pos+len(batch),len(pending)),'of',len(pending),'batch_failed',failed,flush=True)
  if failed:return False
 return True
def grade_request(m,case,byjob):
 cid=case['case_id'];labels=list(case['arms']);random.Random(int(sha([m['issue'],cid])[:16],16)).shuffle(labels);blind={f'R{i+1}':x for i,x in enumerate(labels)};responses={};criteria=[]
 for label,arm in blind.items():
  job=next(j for j in m['jobs'] if j['case_id']==cid and j['arm']==arm);reply=byjob[job['request']['job_id']]['result']['response'];a=case['arms'][arm];responses[label]={'response':reply,'model_visible_input':a['input'],'synthetic_alias_mapping':a['aliases']}
  for criterion in case['applicable']:
   x=m['criterion_definitions'][criterion];criteria.append({'id':label+'::'+criterion,'description':'For '+label+': '+x['pass']+' Failure: '+x['fail']+' Positive example: '+x['positive_example']+' Negative example: '+x['negative_example']})
 msg={'original':case['original'],'expected_case_behavior':case['expected'],'responses':responses};request={'role':'grade','job_id':sha([m['issue'],cid,'grade'])[:32],'model':MODEL,'max_output_tokens':2048,'reasoning_effort':EFFORT,'messages':[{'role':'system','content':'Grade each blinded response independently. Evidence must be a nonempty exact verbatim excerpt of the corresponding response, without added quotation marks; if a violation is absence, quote enough of that actual response to support the judgment. Do not use tools.'},{'role':'user','content':json.dumps(msg,ensure_ascii=False)}],'criteria':criteria};return request,blind,responses
def quotes_valid(result,responses):
 for g in result['grades']:
  label=g['id'].split('::',1)[0]
  if label not in responses or g['evidence'] not in responses[label]['response']:return False
 return True
def grades(m,out,baseline):
 allrows=read_rows(out/'first-responses.jsonl');byjob={x['job_id']:x for x in allrows}
 if len(byjob)!=len(m['jobs']) or any(x['status']!='completed' for x in allrows):return False
 path=out/'first-grades.jsonl';prior=read_rows(path);done=set();cases={x['case_id']:x for x in m['cases']}
 for row in prior:
  case=cases.get(row.get('case_id'))
  if not case or row['case_id'] in done or row.get('status')!='completed':raise ValueError('InvalidSavedGrade')
  request,blind,responses=grade_request(m,case,byjob);attempts=row.get('attempts',[])
  if not attempts or row.get('blind_labels')!=blind or attempts[-1].get('status')!='completed' or not quotes_valid(attempts[-1]['result'],responses):raise ValueError('InvalidSavedGrade')
  expected={x['id'] for x in request['criteria']};actual=[x['id'] for x in attempts[-1]['result']['grades']]
  if len(actual)!=len(expected) or set(actual)!=expected:raise ValueError('InvalidSavedGrade')
  done.add(row['case_id'])
 if any(x['status']!='completed' for x in prior):return False
 pending=[x for x in m['cases'] if x['case_id'] not in done]
 for pos in range(0,len(pending),WORKERS):
  batch=pending[pos:pos+WORKERS];failed=False
  def one(case):
   req,blind,responses=grade_request(m,case,byjob);r=observed(req,baseline);attempts=[r]
   if r['status']=='completed' and not quotes_valid(r['result'],responses):
    retry=dict(req);retry['job_id']=sha([m['issue'],case['case_id'],'regrade'])[:32];retry['messages']=list(req['messages'])+[{'role':'user','content':'The previous quote validation failed. Supply only exact nonempty excerpts from the corresponding response for every verdict.'}];r=observed(retry,baseline);attempts.append(r)
   okay=r['status']=='completed' and quotes_valid(r['result'],responses)
   return {'case_id':case['case_id'],'status':'completed' if okay else 'ungraded','blind_labels':blind,'attempts':attempts}
  with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
   futures={pool.submit(one,c):c for c in batch}
   for f in concurrent.futures.as_completed(futures):
    row=f.result();append_row(path,row);failed|=row['status']!='completed'
  print('grading completed',min(pos+len(batch),len(pending)),'of',len(pending),'batch_failed',failed,flush=True)
  if failed:return False
 return True
def sign(win,loss):
 n=win+loss
 return sum(math.comb(n,k) for k in range(win,n+1))/(2**n) if n else 1.0
def report(m,out):
 rs=read_rows(out/'first-responses.jsonl');gs=read_rows(out/'first-grades.jsonl');bycase={x['case_id']:x for x in gs};scores={}
 for c in m['cases']:
  record=bycase[c['case_id']];attempt=record['attempts'][-1]['result'];blind=record['blind_labels'];arms={}
  for g in attempt['grades']:
   label,criterion=g['id'].split('::',1);arms.setdefault(blind[label],{})[criterion]=g['passed']
  scores[c['case_id']]={'negative_control':c['negative_control'],'arms':arms,'allpass':{k:all(v.values()) for k,v in arms.items()}}
 eligible_ids=[cid for cid,x in scores.items() if x['allpass'].get('A')];eligible=[scores[cid] for cid in eligible_ids];results={}
 for i,variant in enumerate(VARIANTS[m['issue']],1):
  key='D'+str(i);wins=sum(not x['allpass']['C'] and x['allpass'][key] for x in eligible);losses=sum(x['allpass']['C'] and not x['allpass'][key] for x in eligible);p=sign(wins,losses);counts={k:sum(x['allpass'][k] for x in eligible) for k in ('A','C',key)};criterion={}
  for cr in m['criterion_definitions']:
   applicable=[x for x in eligible if cr in x['arms']['C'] and cr in x['arms'][key]]
   if applicable:criterion[cr]={'A':sum(x['arms']['A'].get(cr,False) for x in applicable),'C':sum(x['arms']['C'][cr] for x in applicable),'D':sum(x['arms'][key][cr] for x in applicable),'cases':len(applicable)}
  controls=[x for x in eligible if x['negative_control']];control_loss=sum(x['allpass']['C'] and not x['allpass'][key] for x in controls)-sum(not x['allpass']['C'] and x['allpass'][key] for x in controls);offline=json.loads((ROOT/str(m['issue'])/'offline'/('318-bundle-table' if m['issue']==318 else str(variant))/'summary.json').read_text(encoding='utf-8'));protection=offline['protection_gate_passed'];protection_target=m['issue'] in (310,312,316,318)
  if protection_target:rule=protection and offline['newly_protected']>0 and offline['newly_exposed']==0 and offline['net_overmask_increase']<=2 and losses-wins<=2
  else:rule=protection and wins>losses and p<.05 and all(x['C']-x['D']<2 for x in criterion.values()) and control_loss<=0
  decision='INCOMPLETE' if m['issue']==318 or not eligible else ('ADOPT' if rule else 'REJECT')
  pfname='preflight-doc_structure_policy-selected.json' if m['issue']==317 else 'preflight-'+str(variant)+'.json';pf=json.loads((ROOT/str(m['issue'])/PLAN/pfname).read_text(encoding='utf-8'));pfind={x['id']:x for x in pf['cases']};analysis_diff=sum(pfind[cid]['full_payload_equal'] is False for cid in eligible_ids if cid in pfind);analysis_missing=sum(cid not in pfind for cid in eligible_ids)
  if analysis_missing:decision='INCOMPLETE'
  results[str(variant)]={'decision':decision,'analysis_cases':len(eligible),'analysis_discriminating_cases':analysis_diff,'analysis_discrimination_missing':analysis_missing,'whole_task_passes':counts,'D_only':wins,'C_only':losses,'p_one_sided':p,'per_criterion':criterion,'negative_control_count':len(controls),'negative_control_net_loss':control_loss,'protection':offline,'additional_missing':'independent inference attack' if m['issue']==318 else None}
 usage=[x for row in rs for x in [row] if x['status']=='completed']+[a for row in gs for a in row['attempts'] if a['status']=='completed'];outdoc={'issue':m['issue'],'status':'completed' if all(x['decision']!='INCOMPLETE' for x in results.values()) else 'incomplete','interpretations':len(rs),'grades':len(gs),'raw_tokens':sum(x.get('raw_tokens',0) for x in usage),'content_tokens':sum(x.get('content_tokens',0) for x in usage),'resume_events':read_rows(out/'resume-log.jsonl'),'results':results,'limitation':'Interpreter and grader are the same model family; sample is enriched for observable input differences.'};evaluation.write_json(out/'report.json',outdoc);return outdoc
def main():
 p=argparse.ArgumentParser();p.add_argument('--issue',type=int,choices=sorted(VARIANTS),required=True);p.add_argument('--run',action='store_true');args=p.parse_args();m=prepare(args.issue);out=path_for(args.issue)
 if not args.run:print('Prepared manifest; no model call.');return 0
 baseline=token_baseline()
 if not interpret(m,out,baseline):print('INCOMPLETE: interpretation failure; no grading performed.');return 1
 if not grades(m,out,baseline):print('INCOMPLETE: ungraded case or grader failure.');return 1
 d=report(m,out);print('candidate report status',d['status'],'decisions',','.join(v['decision'] for v in d['results'].values()));return 0 if d['status']=='completed' else 1
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as e:print('runner failure category',type(e).__name__);sys.exit(1)
