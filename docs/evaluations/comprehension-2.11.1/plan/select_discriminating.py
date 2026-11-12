import json,os,pathlib,subprocess,sys,tempfile,shutil,importlib.util,random,collections,hashlib
n=int(sys.argv[1]);root=pathlib.Path.cwd();base=root/'docs/evaluations/comprehension-2.11.1';plan=base/str(n)/'plan';source=pathlib.Path(os.environ['TEMP'])/f'secure_author_targeted_{n}.json';validator=base/'plan/validate_cases.py'
original=json.loads((plan/'cases.json').read_text(encoding='utf-8'));old=original['cases']
with tempfile.TemporaryDirectory(prefix='secure-eval-select-') as temp:
 temp_root=pathlib.Path(temp);dst=temp_root/'docs/evaluations/comprehension-2.11.1'/str(n)/'plan';dst.mkdir(parents=True);shutil.copyfile(source,dst/'authored.json')
 process=subprocess.run([sys.executable,str(validator),str(n)],cwd=temp_root,capture_output=True)
 if process.returncode:print(n,'selection: target validation failed');sys.exit(1)
 newdoc=json.loads((dst/'cases.json').read_text(encoding='utf-8'))
spec=importlib.util.spec_from_file_location('preflight_compare',base/'plan/preflight_compare.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
candidates=[];seen=set();reasons=collections.Counter()
for origin,cases in [('original',old),('targeted',newdoc['cases'])]:
 for item in cases:
  c=dict(item)
  if n==311 and origin=='targeted':
   c['forced_terms']=[x['text'] for x in c['sensitive_spans']]
   if c['private_category']:
    from secure_gateway.experiment_profiles import _ROLE_FIELD
    c['forced_terms']+=list(dict.fromkeys(m['role'] for m in _ROLE_FIELD.finditer(c['original'])))
  if n==312 and not c['negative_control'] and 'code_review' not in c['applicable']:
   reasons['missing_code_review_task']+=1;continue
  if c['original'] in seen:reasons['duplicate_source_text']+=1;continue
  seen.add(c['original'])
  if origin=='targeted':c['source_case_id']=c['id'];c['id']='targeted-'+c['id'];c['author_source']='targeted-authored.json'
  else:c['author_source']=c.get('author_source','authored.json')
  try:
   baseline,_=mod.capture(c,n,None);diff=[]
   for variant in mod.variants[n]:
    candidate,_=mod.capture(c,n,variant);diff.append(baseline!=candidate)
   if c['negative_control'] and any(diff):reasons['control_changed']+=1;continue
   candidates.append((c,diff))
  except Exception as e:
   reasons['capture_'+type(e).__name__]+=1
rng=random.Random(20261111+n);controls=[x for x in candidates if x[0]['negative_control']];changed=[x for x in candidates if not x[0]['negative_control'] and all(x[1])];unchanged=[x for x in candidates if not x[0]['negative_control'] and not all(x[1])];rng.shuffle(controls);rng.shuffle(changed);rng.shuffle(unchanged)
if n==311:controls.sort(key=lambda x:(not x[0].get('private_category',False),x[0].get('author_source')!='targeted-authored.json'))
max_total=48 if n in (310,312,316,318) else 88 if n in (309,313) else 80;min_total=24 if n in (310,312,316,318) else 40
selected_control=controls[:8];target_n=max_total-len(selected_control);selected_changed=changed[:target_n];same_limit=min(len(unchanged),target_n-len(selected_changed),(len(selected_changed)*3)//7);selected_unchanged=unchanged[:same_limit]
selected=selected_changed+selected_unchanged+selected_control;ratio=len(selected_changed)/max(1,len(selected_changed)+len(selected_unchanged));good=len(selected)>=min_total and (len(selected_control)>=8 if n in (309,311,313,314,315,317) else True) and ratio>=.70 and (n not in (309,313) or len(selected_changed)>=80)
report={'issue':n,'source_old_valid':len(old),'source_new_generated':newdoc['generated'],'source_new_valid':len(newdoc['cases']),'new_validation_discard_reasons':newdoc['discard_reasons'],'source_controls':len(controls),'source_both_variant_changed_noncontrols':len(changed),'source_other_noncontrols':len(unchanged),'source_rejections':dict(reasons),'selected_total':len(selected),'selected_controls':len(selected_control),'selected_discriminating_noncontrols':len(selected_changed),'selected_other_noncontrols':len(selected_unchanged),'selected_ratio':ratio,'meets_size_and_preflight':good,'method':'Prioritize independently authored cases where all relevant candidate payloads differ; keep up to eight unchanged controls and a predeclared share of unchanged noncontrols. Discriminating-input enrichment limits generalization. Seed 20261111 + issue.','analysis_set_discriminating':'pending A grading; not measured'}
(plan/'preflight-targeted-screen.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
if not good:
 print(n,'selection incomplete',json.dumps({k:report[k] for k in ('source_controls','source_both_variant_changed_noncontrols','source_other_noncontrols','selected_total','selected_ratio')}));sys.exit(2)
shutil.copyfile(source,plan/'targeted-authored.json');(plan/'preflight-original-cases.json').write_text(json.dumps(original,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
result={'issue':n,'status':'PREFLIGHT SELECTED; model evaluation not run','provenance':'Two independent fresh Codex case-author calls, issue body and case-format only. Targeted corpus enriched offline on candidate discrimination as recorded separately.','synthetic_checks':original['synthetic_checks'],'generated':original['generated']+newdoc['generated'],'accepted':len(selected),'discarded':len(old)+newdoc['accepted']-len(selected)+original['discarded']+newdoc['discarded'],'discard_reasons':{'original_prevalidation':original['discarded'],'targeted_prevalidation':newdoc['discarded'],'post_preflight_not_selected':len(old)+newdoc['accepted']-len(selected)},'negative_controls':len(selected_control),'minimum_count_met':True,'negative_control_minimum_met':True,'preflight_discrimination':report,'cases':[c for c,_ in selected]}
(plan/'cases.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(n,'selection complete',len(selected),'discriminating',len(selected_changed),'controls',len(selected_control),'ratio',round(ratio,3))
