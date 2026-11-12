import collections,contextlib,hashlib,importlib.util,json,os,re,subprocess,sys,tempfile,shutil
from pathlib import Path
from secure_gateway import gateway
from secure_gateway.experiment_profiles import candidate_profile
from secure_gateway.structure_parser import parse_structure
root=Path('docs/evaluations/comprehension-2.11.1');spec=importlib.util.spec_from_file_location('pc',root/'plan/preflight_compare.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def validated(issue,source):
 with tempfile.TemporaryDirectory(prefix='secure-eval-review-') as t:
  d=Path(t)/'docs/evaluations/comprehension-2.11.1'/str(issue)/'plan';d.mkdir(parents=True);shutil.copyfile(source,d/'authored.json');p=subprocess.run([sys.executable,str((root/'plan/validate_cases.py').resolve()),str(issue)],cwd=t,capture_output=True)
  if p.returncode:raise ValueError('CaseValidationFailed')
  return json.loads((d/'cases.json').read_text(encoding='utf-8'))['cases']
def shape(c,n):
 text=c['original'];letters=re.findall(r'[A-Za-z]+|[\uac00-\ud7a3]+',text);types=[]
 for label,pat in [('organize_or_sort',r'organiz|sort|categor|classif|arrang'),('plan_or_schedule',r'plan|schedul|prepar|decid'),('summarize_or_transform',r'summar|translat|rewrite|draft'),('compare_or_select',r'compar|select|choose')]:
  if re.search(pat,text,re.I):types.append(label)
 if not types:types=['other_everyday_request']
 topics=[]
 for label,pat in [('food_or_cooking',r'food|meal|cook|kitchen|grocery|recipe'),('home_or_cleaning',r'home|room|clean|house|laundry|shelf'),('gardening',r'garden|plant|flower|soil'),('travel_or_transport',r'travel|trip|train|bus|journey|route'),('work_or_documents',r'work|project|document|meeting|file|review'),('shopping_or_inventory',r'shop|store|list|item|inventory')]:
  if re.search(pat,text,re.I):topics.append(label)
 if not topics:topics=['other_ordinary_context']
 def mapping(on):
  cm=candidate_profile(v) if on else contextlib.nullcontext()
  with cm:
   sess=gateway.GatewaySession();sess.request({'model':'fixture','input':[{'role':'user','content':text}]});return {hashlib.sha256(str(x.original).encode('utf-8')).hexdigest() for x in sess.session.reverse_store.values()}
 before=mapping(False);after=mapping(True)
 ans={'case_id':c['id'],'task_categories':types,'topics':topics,'newly_masked_mapping_count':len(after-before),'newly_unmasked_mapping_count':len(before-after),'script':'mixed_korean_english' if re.search(r'[A-Za-z]',text) and re.search(r'[\uac00-\ud7a3]',text) else 'korean' if re.search(r'[\uac00-\ud7a3]',text) else 'english_or_other','word_count':len(letters),'sensitive_span_count':len(c['sensitive_spans']),'public_span_count':len(c['public_spans'])}
 if n==317:
  parsed=parse_structure(text);ans.update(document_shape='markdown_table' if '|' in text else 'form_or_prose',parsed_cell_count=len(parsed.cells),applicable_cell_criteria=c.get('applicability',[]))
 return ans
for n,v,expected in [(314,'vocab_calibrated',6),(317,'doc_structure',4)]:
 plan=root/str(n)/'plan';initial=json.loads((plan/'cases.json').read_text(encoding='utf-8'))['cases'];sources=[('original',initial)]
 if n==314:sources.append(('targeted',validated(n,Path(os.environ['TEMP'])/'secure_author_targeted_314.json')))
 else:sources.append(('targeted',validated(n,plan/'targeted-first-authored.json')))
 activated=[]
 for origin,cases in sources:
  for c in cases:
   if c['negative_control']:continue
   a,_=mod.capture(c,n,None);b,_=mod.capture(c,n,v)
   if a!=b:
    item=shape(c,n);item['source_batch']=origin;item['synthetic_input_sha256']=hashlib.sha256(c['original'].encode('utf-8')).hexdigest();activated.append(item)
 if len(activated)!=expected:print(n,'activation mismatch',len(activated),'expected',expected);sys.exit(1)
 if n==314:denom=309;review=json.loads((plan/'semantic-review.json').read_text(encoding='utf-8'))
 else:denom=165;review=json.loads((plan/'semantic-review.json').read_text(encoding='utf-8'))
 out={'issue':n,'candidate':v,'decision':'REJECT','decision_basis':'Coordinator-directed operational decision using observed low preflight activation; this is a later protocol amendment, not the originally predeclared paired sign-test result.','reason':'Mechanism activates too rarely to deliver a material benefit in these independently authored cases.','activated_noncontrol':len(activated),'screened_noncontrol':denom,'activation_rate':len(activated)/denom,'llm_comprehension':'not measured; no A/C/D interpretation or grade calls','original_paired_sign_test':'not performed; formal comprehension evaluation remains incomplete','relevance_review':review,'activated_case_descriptions':activated,'limitations':['Activation is measured on these synthetic cases only.','Preflight selection and the coordinator decision were made after the original decision protocol; do not describe this as a sign-test result.']}
 output=root/str(n)/'preflight-decision';output.mkdir(exist_ok=True);(output/(v+'.json')).write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(n,v,'preflight REJECT',len(activated),'of',denom,'LLM comprehension unmeasured')
