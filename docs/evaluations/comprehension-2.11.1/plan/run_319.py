"""Fresh Codex MCP tool evaluator for the frozen #319 holdout."""

def audit_events(events, allow_tool):
    """Accept only ordinary messages and the explicitly allowed local MCP tool."""
    calls=[]; usage=None; completed=False
    for event in events:
        kind=event.get('type')
        if kind in ('error','turn.failed'):raise ValueError('ProviderFailure')
        if isinstance(kind,str) and kind.startswith('item.'):
            item=event.get('item',{});typ=item.get('type')
            if typ=='mcp_tool_call':
                if not allow_tool or item.get('server')!='alias_arithmetic' or item.get('tool')!='local_alias_arithmetic':raise ValueError('UnexpectedTool')
                if kind=='item.completed':calls.append(item)
            elif typ not in ('agent_message','reasoning'):raise ValueError('UnexpectedTool')
        elif kind=='turn.completed':
            if completed:raise ValueError('DuplicateTurn')
            completed=True;usage=event.get('usage')
        elif kind not in ('thread.started','turn.started'):raise ValueError('UnexpectedEvent')
    if not completed or not isinstance(usage,dict) or any(type(usage.get(k)) is not int for k in ('input_tokens','output_tokens')):raise ValueError('MissingUsage')
    return {'calls':len(calls),'tool_events':calls,'usage':usage}


def contains_secret(text, secrets):
    """Find whole original tokens outside symbolic aliases in visible content."""
    import re
    text=re.sub(r'private_symbol_\d+','[ALIAS]',text)
    return any(re.search(r'(?<![\w.])'+re.escape(value)+r'(?![\w.])',text) is not None for value in secrets if value)

import hashlib,importlib.util,json,os,random,re,secrets,shutil,sys,tempfile,time
from pathlib import Path
from secure_gateway import gateway,evaluation
from secure_gateway.encrypted_session import save_session,load_session
from secure_gateway.evaluation_worker import capture_worker_process,strict_json

ROOT=Path('docs/evaluations/comprehension-2.11.1'); OUT=ROOT/'319/comprehension'; MODEL='gpt-6.1-sol'
sp=importlib.util.spec_from_file_location('base319',ROOT/'plan/run_comprehension.py');base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
ENV_KEYS={'PATH','HOME','USERPROFILE','CODEX_HOME','SYSTEMROOT','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL','LC_CTYPE','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy','SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE','NODE_EXTRA_CA_CERTS'}

def prepare():
    OUT.mkdir(parents=True,exist_ok=True); manifest_path=OUT/'manifest.json'
    if manifest_path.exists():
        data=json.loads(manifest_path.read_text(encoding='utf8'))
        if data['run_identity']!=identity():raise ValueError('RunIdentityMismatch')
        return data
    cases=json.loads((ROOT/'319/plan/cases.json').read_text(encoding='utf8'))['cases']; rubric=json.loads((ROOT/'319/plan/rubric.json').read_text(encoding='utf8')); lookup={x['id']:x for x in rubric['criteria']}; entries=[];jobs=[]
    for c in cases:
        s=gateway.GatewaySession(natural_language='auto');s.forced_rules=lambda:tuple(c.get('forced_terms',())); payload=s.request({'model':'fixture','input':[{'role':'user','content':c['original']}]}); aliases={str(v.surrogate):str(v.original) for v in s.session.reverse_store.values()}; masked=payload['input'][0]['content'];instructions=payload.get('instructions','')
        spans=c['sensitive_spans']; selected=[]
        for gold in spans:
            matches=[a for a,original in aliases.items() if original==gold['text']]
            if len(matches)!=1:raise ValueError('UnboundGoldSpan')
            selected.append(matches[0])
        if contains_secret(masked,[x['text'] for x in spans]):raise ValueError('BaselineSecretVisible')
        identifier=base.sha([319,c['id'],'D1'])[:32]; owner=OUT/'owners'/identifier;owner.mkdir(parents=True,exist_ok=False);s.session.session_id='arithmetic-fixture';token=secrets.token_hex(32);save_session(owner/'session.enc',s.session,token)
        unit=c.get('unit');unit=unit if unit in {'USD','EUR','KRW'} else 'USD';operation=str(c.get('operation','')).lower();allowed={}
        for i,alias in enumerate(selected):
            if c['label']!='unsupported_unit':allowed[alias]='count' if operation.startswith('multiply') and i==1 else unit
        config={'token':token,'allowed':allowed,'result_units':{'multiply':unit,'date_difference':'days'},'calls':0,'expires_at':time.time()+86400*30};evaluation.write_json(owner/'fixture.json',config)
        arms={'A':{'instructions':instructions,'input':c['original'],'aliases':{}},'C':{'instructions':instructions,'input':masked,'aliases':aliases},'D1':{'instructions':instructions,'input':masked,'aliases':aliases}}
        entry={'case_id':c['id'],'original':c['original'],'expected':c['expected'],'negative_control':c['negative_control'],'applicable':c['applicable'],'applicable_by_condition':c['applicable_by_condition'],'label':c['label'],'operation':c['operation'],'unit':c.get('unit'),'gold':c.get('gold'),'sensitive_values':[x['text'] for x in spans],'arms':arms};entries.append(entry)
        for label,arm in arms.items():
            req={'role':'interpret','job_id':base.sha([319,c['id'],label])[:32],'model':MODEL,'max_output_tokens':512,'reasoning_effort':'low','messages':[{'role':'system','content':arm['instructions']},{'role':'user','content':arm['input']}]};jobs.append({'case_id':c['id'],'arm':label,'request':req})
    random.Random(20261111319).shuffle(jobs);data={'schema_version':1,'issue':319,'model':MODEL,'cases':entries,'jobs':jobs,'criterion_definitions':lookup,'run_identity':identity(),'disclosure':'Synthetic data only. Same model family interprets and grades. Tool condition permits only the local arithmetic MCP tool.'}
    for name in ('rubric.json','decision.json'):shutil.copyfile(ROOT/'319/plan'/name,OUT/('frozen-'+name))
    evaluation.write_json(manifest_path,data);return data

def identity():
    return base.sha([base.run_identity(319),hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),hashlib.sha256((ROOT/'plan/arithmetic_mcp_fixture.py').read_bytes()).hexdigest()])

def candidate(job,case,baseline):
    request=job['request']; env={k:v for k,v in os.environ.items() if k in ENV_KEYS}; started=time.monotonic();fixture=(OUT/'owners'/job['request']['job_id']/'fixture.json').resolve()
    with tempfile.TemporaryDirectory(prefix='sg-tool-eval-') as directory:
        workspace=Path(directory); last=workspace/'last.txt';command=[shutil.which('codex'),'exec','--ephemeral','--ignore-user-config','--ignore-rules','--skip-git-repo-check','--sandbox','read-only','--model',MODEL,'--json','--output-last-message',str(last),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','-c','project_doc_max_bytes=0','-c','developer_instructions=""','-c','web_search="disabled"','-c','features.multi_agent=false','-c','model_reasoning_effort="low"']
        params={'command':str(Path(sys.executable).resolve()),'args':[str((ROOT/'plan/arithmetic_mcp_fixture.py').resolve()),'--fixture',str(fixture)],'enabled_tools':['local_alias_arithmetic'],'startup_timeout_sec':30,'tool_timeout_sec':30,'tools.local_alias_arithmetic.approval_mode':'approve'}
        for k,v in params.items():command.extend(['-c','mcp_servers.alias_arithmetic.'+k+'='+json.dumps(v)])
        command.append('-');prompt=('Complete the supplied task. Use the local_alias_arithmetic tool only if needed. Do not use other tools, commands, files, browsing, agents or skills. Limit output to 512 tokens.\n'+json.dumps(request['messages'],ensure_ascii=False))
        raw=capture_worker_process(command,prompt.encode('utf8'),timeout=300,cwd=workspace,env=env,new_process_group=True);events=[strict_json(line) for line in raw.stdout.splitlines() if line.strip()];audit=audit_events(events,True);final=last.read_text(encoding='utf8')
    config=json.loads(fixture.read_text(encoding='utf8'));session=gateway.GatewaySession(load_session(fixture.parent/'session.enc',config['token'],'arithmetic-fixture'));restored=session.restore(final);trace=[]
    for item in audit['tool_events']:
        trace.append({'tool':'local_alias_arithmetic','arguments':item.get('arguments'),'result':item.get('result'),'status':item.get('status'),'error':bool(item.get('error'))})
    usage=audit['usage'];numbers=[x['text'] for x in case.get('sensitive_spans',[])] if 'sensitive_spans' in case else case['sensitive_values'];gold=str(case.get('gold') or '');numbers+=re.findall(r'(?<!\w)\d+(?:[.,]\d+)*(?!\w)',gold)
    provider_visible=json.dumps({'task':case['arms']['D1']['input'],'trace':trace,'answer':final},ensure_ascii=False);leak=contains_secret(provider_visible,numbers)
    return {'job_id':job['request']['job_id'],'case_id':job['case_id'],'arm':'D1','status':'completed','result':{'job_id':job['request']['job_id'],'response':final,'restored':restored,'derived_aliases':{str(v.surrogate):str(v.original) for v in session.session.reverse_store.values()},'tool_trace':trace,'tool_calls':audit['calls'],'provider_value_leak':leak,'metadata':{'fresh_session':True,'tool_events':audit['calls'],'tool_allowlist_verified':True},'usage':usage},'elapsed_seconds':time.monotonic()-started,'raw_tokens':usage['input_tokens']+usage['output_tokens'],'content_tokens':usage['input_tokens']-baseline+usage['output_tokens']}

def execute(m):
    path=OUT/'first-responses.jsonl';rows=base.read_rows(path);done={x['job_id'] for x in rows};jobs={x['request']['job_id']:x for x in m['jobs']};cases={x['case_id']:x for x in m['cases']};baseline=base.token_baseline()
    if len(done)!=len(rows) or any(x['status']!='completed' or x['job_id'] not in jobs for x in rows):raise ValueError('InvalidSavedResponses')
    for job in m['jobs']:
        jid=job['request']['job_id']
        if jid in done:continue
        c=cases[job['case_id']]
        try:
            if job['arm']=='D1':row=candidate(job,c,baseline)
            else:
                row={'job_id':jid,'case_id':job['case_id'],'arm':job['arm'],**base.observed(job['request'],baseline)}
                if row['status']=='completed' and job['arm']=='C':
                    secrets=list(c['sensitive_values'])+re.findall(r'(?<!\w)\d+(?:[.,]\d+)*(?!\w)',str(c.get('gold') or ''));row['result']['provider_value_leak']=contains_secret(c['arms']['C']['input']+'\n'+row['result']['response'],secrets)
        except Exception as exc:row={'job_id':jid,'case_id':job['case_id'],'arm':job['arm'],'status':'failed','error_category':type(exc).__name__}
        base.append_row(path,row);print('319 interpretations',len(done)+1,'/',len(jobs),'status',row['status'],flush=True)
        if row['status']!='completed':return False
        done.add(jid)
    return True

def grade_request(m,c,byjob):
    cid=c['case_id'];labels=list(c['arms']);random.Random(int(base.sha([319,cid])[:16],16)).shuffle(labels);blind={f'R{i+1}':x for i,x in enumerate(labels)};responses={};criteria=[]
    for label,arm in blind.items():
        job=next(j for j in m['jobs'] if j['case_id']==cid and j['arm']==arm);result=byjob[job['request']['job_id']]['result'];text=result['response'];trace=result.get('tool_trace',[])
        if trace:text+='\nSANITIZED TOOL TRANSCRIPT: '+json.dumps(trace,ensure_ascii=False,sort_keys=True)
        data=c['arms'][arm];responses[label]={'response':text,'model_visible_input':data['input'],'synthetic_alias_mapping':result.get('derived_aliases',data['aliases'])}
        for criterion in c['applicable_by_condition'][{'A':'A','C':'C','D1':'D'}[arm]]:
            x=m['criterion_definitions'][criterion];criteria.append({'id':label+'::'+criterion,'description':'For '+label+': '+x['pass']+' Failure: '+x['fail']+' Positive example: '+x['positive_example']+' Negative example: '+x['negative_example']})
    msg={'original':c['original'],'expected_case_behavior':c['expected'],'responses':responses};request={'role':'grade','job_id':base.sha([319,cid,'grade'])[:32],'model':MODEL,'max_output_tokens':2048,'reasoning_effort':'low','messages':[{'role':'system','content':'Grade each blinded response independently. Every verdict needs an exact nonempty verbatim excerpt of that answer or its sanitized tool transcript. Do not use tools.'},{'role':'user','content':json.dumps(msg,ensure_ascii=False)}],'criteria':criteria};return request,blind,responses

def grade(m):
    rows=base.read_rows(OUT/'first-responses.jsonl');byjob={x['job_id']:x for x in rows};path=OUT/'first-grades.jsonl';prior=base.read_rows(path);done={x['case_id'] for x in prior};baseline=base.token_baseline()
    if len(byjob)!=len(m['jobs']) or len(done)!=len(prior) or any(x['status']!='completed' for x in prior):raise ValueError('InvalidSavedGrades')
    for c in m['cases']:
        if c['case_id'] in done:continue
        req,blind,responses=grade_request(m,c,byjob);attempts=[base.observed(req,baseline)];last=attempts[-1]
        if last['status']=='completed' and not base.quotes_valid(last['result'],responses):
            retry=dict(req);retry['job_id']=base.sha([319,c['case_id'],'regrade'])[:32];retry['messages']=list(req['messages'])+[{'role':'user','content':'Previous evidence failed validation. Provide exact excerpts from corresponding responses or transcripts.'}];attempts.append(base.observed(retry,baseline));last=attempts[-1]
        status='completed' if last['status']=='completed' and base.quotes_valid(last['result'],responses) else 'ungraded';row={'case_id':c['case_id'],'status':status,'blind_labels':blind,'attempts':attempts};base.append_row(path,row);print('319 grades',len(done)+1,'/',len(m['cases']),'status',status,flush=True)
        if status!='completed':return False
        done.add(c['case_id'])
    return True

def report(m):
    from decimal import Decimal,InvalidOperation
    rows=base.read_rows(OUT/'first-responses.jsonl');grades=base.read_rows(OUT/'first-grades.jsonl');byjob={x['job_id']:x for x in rows};bygrade={x['case_id']:x for x in grades};results={};criterion={}
    for c in m['cases']:
        g=bygrade[c['case_id']];arms={}
        for verdict in g['attempts'][-1]['result']['grades']:
            label,k=verdict['id'].split('::',1);arm=g['blind_labels'][label];arms.setdefault(arm,{})[k]=verdict['passed']
        results[c['case_id']]={'case':c,'arms':arms,'allpass':{a:all(v.values()) for a,v in arms.items()}}
    eligible=[v for v in results.values() if v['allpass']['A']];solvable=[v for v in eligible if v['case']['label']=='tool_solvable'];controls=[v for v in eligible if v['case']['label']!='tool_solvable']; wins=losses=correct=0
    def numeric(value):
        try:return [Decimal(x.replace(',','')) for x in re.findall(r'(?<!\w)\d+(?:,\d{3})*(?:\.\d+)?(?!\w)',str(value))]
        except InvalidOperation:return []
    for v in solvable:
        c=v['case'];dj=next(j for j in m['jobs'] if j['case_id']==c['case_id'] and j['arm']=='D1'); dr=byjob[dj['request']['job_id']]['result']; actual=numeric(dr['restored']);gold=numeric(c['gold']); graded=v['arms']['D1'];ok=bool(gold and gold[0] in actual and dr['tool_calls']>=1 and v['allpass']['D1'] and all(graded.get(k,False) for k in ('operation_aliases','restored_result','unit')));correct+=ok;cv=v['allpass']['C'];wins+=ok and not cv;losses+=cv and not ok
    control_calls=sum(byjob[next(j['request']['job_id'] for j in m['jobs'] if j['case_id']==v['case']['case_id'] and j['arm']=='D1')]['result']['tool_calls']>0 for v in controls); leaks=sum(x['result'].get('provider_value_leak',False) for x in rows if x['arm'] in ('C','D1'));p=base.sign(wins,losses);offline=json.loads((ROOT/'319/offline/local_arithmetic/summary.json').read_text(encoding='utf8')); rate=correct/len(solvable) if solvable else 0
    for k in m['criterion_definitions']:
        criterion[k]={a:{'pass':sum(v['arms'].get(a,{}).get(k) is True for v in eligible),'applicable':sum(k in v['arms'].get(a,{}) for v in eligible)} for a in ('A','C','D1')}
    decision='ADOPT' if offline['protection_gate_passed'] and rate>=.8 and p<.05 and control_calls<=1 and leaks==0 else 'REJECT'; usage=rows+[a for g in grades for a in g['attempts'] if a['status']=='completed'];result={'issue':319,'status':'completed','decision':decision,'eligible':len(eligible),'A_C_D_passes':{a:sum(v['allpass'].get(a,False) for v in eligible) for a in ('A','C','D1')},'solvable_eligible':len(solvable),'correct_restored':correct,'correct_restored_rate':rate,'D_only':wins,'C_only':losses,'p_one_sided':p,'control_cases':len(controls),'unnecessary_or_forbidden_tool_cases':control_calls,'provider_value_leak_trajectories':leaks,'duplicate_inferences':0,'criteria':criterion,'protection':offline,'interpretations':len(rows),'grades':len(grades),'raw_tokens':sum(x.get('raw_tokens',0) for x in usage),'content_tokens':sum(x.get('content_tokens',0) for x in usage),'limitation':'Same model family interpreted and graded; synthetic enriched holdout; same OS user and no hard filesystem jail.'};evaluation.write_json(OUT/'report.json',result);print('319 decision',decision,flush=True)

if __name__=='__main__':
    try:
        m=prepare()
        if '--run' in sys.argv:
            if execute(m) and grade(m):report(m)
            else:print('319 INCOMPLETE',flush=True);sys.exit(1)
        else:print('319 prepared; no model calls',flush=True)
    except Exception as exc:print('319 failure category',type(exc).__name__,flush=True);sys.exit(1)
