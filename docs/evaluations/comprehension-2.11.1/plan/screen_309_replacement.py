import pathlib,tempfile,subprocess,sys,shutil,json,os,importlib.util,hashlib
number=int(sys.argv[1]); base=pathlib.Path('docs/evaluations/comprehension-2.11.1').resolve(); plan=base/'309/plan'; src=pathlib.Path(os.environ['TEMP'])/'secure_author_clean_309.json'; dest=plan/f'replacement-batch{number}-authored.json'
if dest.exists():raise SystemExit('batch already exists')
shutil.copyfile(src,dest)
with tempfile.TemporaryDirectory(prefix='secure-replacement-validation-') as t:
 p=pathlib.Path(t)/'docs/evaluations/comprehension-2.11.1/309/plan';p.mkdir(parents=True);shutil.copyfile(src,p/'authored.json')
 r=subprocess.run([sys.executable,str(base/'plan/validate_cases.py'),'309'],cwd=t,capture_output=True)
 if r.returncode:raise SystemExit('validation failure')
 d=json.loads((p/'cases.json').read_text(encoding='utf8'))
spec=importlib.util.spec_from_file_location('preflight',base/'plan/preflight_compare.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
previous=json.loads((base/'pilot/309-underpowered/manifest.json').read_text(encoding='utf8')); old={c['original'] for c in previous['cases']}; rows=[]
for c in d['cases']:
 try:
  a,_=m.capture(c,309,None); b,_=m.capture(c,309,m.variants[309][0]); rows.append({'id':c['id'],'control':c['negative_control'],'changed':a!=b,'duplicate_pilot':c['original'] in old})
 except Exception as e:rows.append({'id':c['id'],'error_category':type(e).__name__})
result={'generated':d['generated'],'accepted':d['accepted'],'discarded':d['discarded'],'discard_reasons':d['discard_reasons'],'authored_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'rows':rows};(plan/f'replacement-batch{number}-screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('generated',d['generated'],'validated',d['accepted'],'discarded',d['discarded'],'discriminating noncontrols',sum(not x.get('control',True) and x.get('changed',False) and not x.get('duplicate_pilot',False) for x in rows),'unchanged controls',sum(x.get('control',False) and not x.get('changed',True) and not x.get('duplicate_pilot',False) for x in rows),'duplicates',sum(x.get('duplicate_pilot',False) for x in rows))
