import json,collections,sys,re
from pathlib import Path
n=int(sys.argv[1]);root=Path('docs/evaluations/comprehension-2.11.1')/str(n)/'plan';data=json.loads((root/'protection-authored.json').read_text(encoding='utf-8'))['cases'];good=[];errors=collections.Counter();ids=set();texts=set()
for c in data:
 error=None
 if not isinstance(c,dict) or not isinstance(c.get('original'),str) or not isinstance(c.get('id'),str) or c['id'] in ids or c['original'] in texts:error='missing_or_duplicate'
 elif re.search(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b',c['original']):error='email_requires_synthetic_review'
 else:
  spans=[];text=c['original']
  for key in ('sensitive_spans','public_spans'):
   if not isinstance(c.get(key),list):error='invalid_span_list';break
   for span in c[key]:
    if not isinstance(span,dict) or type(span.get('start')) is not int or type(span.get('end')) is not int or not isinstance(span.get('text'),str) or span['start']<0 or span['end']<=span['start'] or text[span['start']:span['end']]!=span['text']:
     error='offset_mismatch';break
    spans.append((span['start'],span['end']))
   if error:break
  if not error:
   spans.sort()
   if any(a[1]>b[0] for a,b in zip(spans,spans[1:])):error='overlapping_gold'
 if error:errors[error]+=1;continue
 ids.add(c['id']);texts.add(c['original']);good.append(c)
ns=sum(len(c['sensitive_spans']) for c in good);np=sum(len(c['public_spans']) for c in good)
result={'issue':n,'status':'DRAFT: independent policy and synthetic-only review required before freezing','origin':'Independent fresh Codex author call using issue body and case format, with no candidate implementation or previous responses.','generated_cases':len(data),'accepted_cases':len(good),'discarded_cases':sum(errors.values()),'discard_reasons':dict(errors),'sensitive_span_count':ns,'public_span_count':np,'span_minima_met':ns>=100 and np>=100,'cases':good}
(root/'protection-cases.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{n}: accepted={len(good)} discarded={sum(errors.values())} sensitive={ns} public={np} minima_met={result["span_minima_met"]}')
