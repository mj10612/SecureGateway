import importlib.util,json,os,pathlib,shutil,subprocess,sys,tempfile
root=pathlib.Path.cwd();base=root/'docs/evaluations/comprehension-2.11.1';tmp=pathlib.Path(os.environ['TEMP']);spec=importlib.util.spec_from_file_location('pc',base/'plan/preflight_compare.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
for n in (309,313):
 total=changed=controls=0
 for i in range(1,13):
  source=tmp/f'secure_author_expand{i}_{n}.json'
  if not source.exists():continue
  dest=base/str(n)/'plan'/f'expansion-batch{i}-authored.json';shutil.copyfile(source,dest)
  with tempfile.TemporaryDirectory(prefix='secure-expansion-validate-') as t:
   p=pathlib.Path(t)/'docs/evaluations/comprehension-2.11.1'/str(n)/'plan';p.mkdir(parents=True);shutil.copyfile(source,p/'authored.json');run=subprocess.run([sys.executable,str(base/'plan/validate_cases.py'),str(n)],cwd=t,capture_output=True)
   if run.returncode:print(n,'batch',i,'validation failure');continue
   d=json.loads((p/'cases.json').read_text(encoding='utf-8'))
  rows=[]
  for c in d['cases']:
   try:
    a,_=mod.capture(c,n,None);b,_=mod.capture(c,n,mod.variants[n][0]);changedcase=a!=b;rows.append({'id':c['id'],'negative_control':c['negative_control'],'changed':changedcase});
    if not c['negative_control']:total+=1;changed+=changedcase
    elif not changedcase:controls+=1
   except Exception as e:rows.append({'id':c['id'],'error_category':type(e).__name__})
  (base/str(n)/'plan'/f'expansion-batch{i}-screen.json').write_text(json.dumps({'issue':n,'batch':i,'generated':d['generated'],'valid':d['accepted'],'discarded':d['discarded'],'discard_reasons':d['discard_reasons'],'rows':rows},indent=2)+'\n',encoding='utf-8')
 print(n,'expansion noncontrols screened',total,'changed',changed,'unchanged controls',controls,flush=True)
