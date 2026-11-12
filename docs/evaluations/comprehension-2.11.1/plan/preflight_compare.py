import json,hashlib,re,contextlib,sys
from pathlib import Path
from secure_gateway import gateway
from secure_gateway.experiment_profiles import candidate_profile
root=Path('docs/evaluations/comprehension-2.11.1');issues=[309,310,311,312,313,314,315,316,317,318,319]
variants={309:['ko_conjugation_split'],310:[310],311:[311],312:['numeric_context'],313:['segment_language'],314:['vocab_calibrated'],315:['instruction_concise','instruction_examples'],316:[316],317:['doc_structure','doc_structure_policy'],318:[318],319:['local_arithmetic']}
def policy(n,case,variant):
 if n==311:return {'allow_roles':True,'confidential_roles':case['private_category']}
 if n in (316,318):return case['trusted_local_policy']
 if n==317 and variant=='doc_structure_policy':return {'field_policy': {label:'always_mask' for label in case.get('sensitive_field_labels',[])}}
 return None
def capture(case,n,variant):
 cm=contextlib.nullcontext() if variant is None else candidate_profile(variant,policy(n,case,variant))
 with cm:
  s=gateway.GatewaySession(natural_language='auto')
  s.forced_rules=lambda:tuple(case.get('forced_terms',()))
  data={'model':'fixture','input':[{'role':'user','content':case['original']}]}
  out=s.request(data)
  mapping=list(s.session.reverse_store.values())
  pairs=[]
  for v in mapping:
   ident=hashlib.sha256((str(v.original)+'\0'+str(v.token_type)+'\0'+str(v.context)).encode('utf-8')).hexdigest()
   pairs.append((v.surrogate,'<ALIAS-'+ident+'>'))
  pairs.sort(key=lambda x:len(x[0]),reverse=True)
  def normalize(v):
   if isinstance(v,str):
    for a,b in pairs:v=v.replace(a,b)
    return v
   if isinstance(v,dict):return {k:normalize(x) for k,x in v.items()}
   if isinstance(v,list):return [normalize(x) for x in v]
   return v
  canonical=normalize(out)
  task_text=json.dumps(out.get('input',[]),ensure_ascii=False)
  bind=sorted((hashlib.sha256((str(m.original)+'\0'+str(m.token_type)+'\0'+str(m.context)).encode('utf-8')).hexdigest()) for m in mapping if m.surrogate in task_text)
  return canonical,bind
if __name__ == "__main__":
    reports=[]
    for n in issues:
     cases=json.loads((root/str(n)/'plan/cases.json').read_text(encoding='utf-8'))['cases']
     for variant in variants[n]:
      counts={'noncontrol':0,'different':0,'control':0,'control_different':0,'errors':0,'noncontrol_task_different':0,'control_task_different':0};rows=[]
      for c in cases:
       try:
        base,bb=capture(c,n,None);cand,cb=capture(c,n,variant);same=base==cand;task_equal=(base.get('input')==cand.get('input') and bb==cb)
        flag='control' if c['negative_control'] else 'noncontrol';counts[flag]+=1
        if not same:counts['control_different' if flag=='control' else 'different']+=1
        if not task_equal:counts['control_task_different' if flag=='control' else 'noncontrol_task_different']+=1
        rows.append({'id':c['id'],'negative_control':c['negative_control'],'full_payload_equal':same,'task_and_bindings_equal':task_equal})
       except Exception as e:
        counts['errors']+=1;rows.append({'id':c['id'],'error_category':type(e).__name__})
      result={'issue':n,'variant':str(variant),'counts':counts,'cases':rows,'comparison':'Actual GatewaySession.request payloads; normalize allocated aliases to deterministic hashes of original, token type and context to avoid counting random alias spelling as a semantic treatment effect. No provider or model call.'}
      out=root/str(n)/'plan'/('preflight-'+str(variant)+'.json');out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');reports.append(result)
      print(n,str(variant),json.dumps(counts),flush=True)
