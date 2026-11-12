import importlib.util,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
n=int(sys.argv[1]);repo=Path.cwd();plan=repo/'docs/evaluations/comprehension-2.11.1/plan';target=Path(os.environ['TEMP'])/f'secure_author_targeted_{n}.json'
with tempfile.TemporaryDirectory(prefix='secure-case-validation-') as t:
 root=Path(t);p=root/'docs/evaluations/comprehension-2.11.1'/str(n)/'plan';p.mkdir(parents=True);shutil.copyfile(target,p/'authored.json')
 proc=subprocess.run([sys.executable,str(plan/'validate_cases.py'),str(n)],cwd=root,capture_output=True)
 if proc.returncode:
  print(n,'target validation failed');sys.exit(1)
 val=json.loads((p/'cases.json').read_text(encoding='utf-8'))
spec=importlib.util.spec_from_file_location('preflight_compare',plan/'preflight_compare.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
counts={'control':0,'control_invariant':0,'noncontrol':0,'different_all':0,'errors':0};details=[]
for c in val['cases']:
 if n==311:c['forced_terms']=[x['text'] for x in c['sensitive_spans']]
 try:
  base,bb=mod.capture(c,n,None);changed=[]
  for variant in mod.variants[n]:
   candidate,cb=mod.capture(c,n,variant);changed.append(base!=candidate)
  iscontrol=c['negative_control'];counts['control' if iscontrol else 'noncontrol']+=1
  if iscontrol and not any(changed):counts['control_invariant']+=1
  if not iscontrol and all(changed):counts['different_all']+=1
  details.append({'id':c['id'],'negative_control':iscontrol,'differences':changed})
 except Exception as e:
  counts['errors']+=1;details.append({'id':c['id'],'error_category':type(e).__name__})
result={'issue':n,'generated':val['generated'],'valid':val['accepted'],'validation_discards':val['discard_reasons'],'counts':counts,'rows':details}
p=Path(os.environ['TEMP'])/f'secure_target_screen_{n}.json';p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(n,json.dumps(counts), 'validation_discarded',val['discarded'])
