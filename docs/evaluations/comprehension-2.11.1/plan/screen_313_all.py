import json,importlib.util,collections
from pathlib import Path
p=Path('docs/evaluations/comprehension-2.11.1/313/plan');files=[p/'authored.json',p/'targeted-first-authored.json',p/'targeted-second-authored.json']+sorted(p.glob('expansion-batch*-authored.json'));spec=importlib.util.spec_from_file_location('pc',p.parents[1]/'plan/preflight_compare.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);stats=collections.Counter()
for f in files:
 for c in json.loads(f.read_text(encoding='utf-8'))['cases']:
  if c.get('negative_control') is not False:continue
  try:
   a,_=m.capture(c,313,None);b,_=m.capture(c,313,'segment_language');stats['screened_noncontrol']+=1;stats['changed']+=a!=b
  except Exception as e:stats['error_'+type(e).__name__]+=1
result={'issue':313,'independent_author_batches':len(files),'authored_noncontrols':sum(1 for f in files for c in json.loads(f.read_text(encoding='utf-8'))['cases'] if c.get('negative_control') is False),**dict(stats),'note':'Includes cases excluded later for invalid gold/duplicates, solely to characterize authored-input activation. No LLM responses involved.'};(p/'overall-activation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('313 overall activation',result['changed'],'/',result['screened_noncontrol'],'authored noncontrols',result['authored_noncontrols'])
