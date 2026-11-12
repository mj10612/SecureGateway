import json,os,pathlib,subprocess,sys,tempfile,shutil,importlib.util,random,collections
n=317;root=pathlib.Path.cwd();base=root/'docs/evaluations/comprehension-2.11.1';plan=base/'317/plan';source=pathlib.Path(os.environ['TEMP'])/'secure_author_targeted3_317.json';old=json.loads((plan/'cases.json').read_text(encoding='utf-8'))['cases']
with tempfile.TemporaryDirectory(prefix='secure-eval-select-') as temp:
 dest=pathlib.Path(temp)/'docs/evaluations/comprehension-2.11.1/317/plan';dest.mkdir(parents=True);shutil.copyfile(source,dest/'authored.json');p=subprocess.run([sys.executable,str(base/'plan/validate_cases.py'),'317'],cwd=temp,capture_output=True)
 if p.returncode:print('317 policy validation failed');sys.exit(1)
 doc=json.loads((dest/'cases.json').read_text(encoding='utf-8'))
spec=importlib.util.spec_from_file_location('pc',base/'plan/preflight_compare.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);groups={'changed':[],'unchanged':[],'control':[]};reject=collections.Counter();seen=set()
for origin,rows in [('old',old),('targeted',doc['cases'])]:
 for item in rows:
  c=dict(item)
  if c['original'] in seen:reject['duplicate']+=1;continue
  seen.add(c['original'])
  if origin=='targeted':c['author_original_id']=c['id'];c['id']='policy-targeted-'+c['id'];c['author_source']='targeted-third-authored.json'
  try:
   a,_=mod.capture(c,n,None);b,_=mod.capture(c,n,'doc_structure_policy');changed=a!=b
   if c['negative_control']:
    if changed:reject['control_changed']+=1
    else:groups['control'].append(c)
   elif changed:groups['changed'].append(c)
   else:groups['unchanged'].append(c)
  except Exception as e:reject['capture_'+type(e).__name__]+=1
rng=random.Random(20261111+n);[rng.shuffle(x) for x in groups.values()];groups['control'].sort(key=lambda c:c.get('author_source')!='targeted-third-authored.json');controls=groups['control'][:8];positives=groups['changed'][:72];same=[];selected=positives+same+controls;ratio=len(positives)/max(1,len(positives)+len(same));okay=len(selected)>=40 and len(controls)>=8 and ratio>=.7
report={'variant':'doc_structure_policy','generated_targeted':doc['generated'],'validated_targeted':doc['accepted'],'validation_discards':doc['discard_reasons'],'positive_changed':len(positives),'positive_unchanged':len(same),'negative_unchanged':len(controls),'ratio':ratio,'passed':okay,'unselected_or_invalid':dict(reject),'note':'Independent per-candidate set; local confidential-field policy comes from the author-provided sensitive_field_labels. Results are conditional on offline discrimination.'};(plan/'preflight-policy-selection.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
if not okay:print('317 policy selection incomplete',json.dumps(report));sys.exit(2)
shutil.copyfile(source,plan/'targeted-third-authored.json');result={'issue':317,'variant':'doc_structure_policy','status':'PREFLIGHT SELECTED; model evaluation not run','accepted':len(selected),'negative_controls':len(controls),'minimum_count_met':True,'negative_control_minimum_met':True,'preflight':report,'cases':selected};(plan/'policy-cases.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('317 policy selected',len(selected),'changed',len(positives),'unchanged controls',len(controls),'ratio',round(ratio,3))
