import json, os, pathlib, shutil, subprocess, tempfile, sys
issue=json.loads(subprocess.check_output(['gh','issue','view','312','--json','title,body'],encoding='utf-8'))
spec='''Author a new synthetic holdout for offline public-number measurements. No tools, no prior context. Return JSON object {cases:[...]}. Produce exactly 8 distinct short examples of fenced source code, each containing a genuine for or while loop with ordinary numeric iteration bounds and/or numeric indexing and constants. Each case has id, context_type code_loop_index, original, and public_spans. Every case must contain exactly five public numeric spans in original, annotated as objects {start,end,text} with exact zero-based Unicode code point offsets and end exclusive. Each annotated text must occur exactly once in original. Disjoint spans only. Every number must be a public loop count, index, or ordinary code constant; none is an identifier, contact, token, credential, or private value. Use distinct fictional examples, no personal data. Return valid JSON only without markdown.'''
prompt='Issue text:\n'+json.dumps(issue,ensure_ascii=False)+'\n\nCase format specification:\n'+spec
with tempfile.TemporaryDirectory(prefix='secure-number-author-') as root:
 output=pathlib.Path(root)/'out.json'; events=pathlib.Path(root)/'events.jsonl'; cmd=[shutil.which('codex'),'exec','--ephemeral','--skip-git-repo-check','--ignore-user-config','--ignore-rules','--sandbox','read-only','--model','gpt-6.1-sol','--json','--output-last-message',str(output),'-c','forced_login_method="chatgpt"','-c','project_doc_max_bytes=0','-c','developer_instructions=""','-c','web_search="disabled"','-c','features.multi_agent=false','-c','model_reasoning_effort="low"','-']
 with events.open('wb') as f: p=subprocess.run(cmd,input=prompt.encode('utf8'),stdout=f,stderr=subprocess.DEVNULL,cwd=root,timeout=600)
 if p.returncode: print('author_failed_exit',p.returncode);sys.exit(1)
 usage=None
 for line in events.read_text(encoding='utf8').splitlines():
  e=json.loads(line)
  if e.get('type','').startswith('item.') and e.get('item',{}).get('type') not in ('agent_message','reasoning'):raise ValueError('tool event')
  if e.get('type') in ('error','turn.failed'):raise ValueError('failed turn')
  if e.get('type')=='turn.completed':usage=e.get('usage')
 data=json.loads(output.read_text(encoding='utf8')); out=pathlib.Path('docs/evaluations/comprehension-2.11.1/312/plan/public-loops-authored.json');out.write_text(json.dumps({'provenance':'Fresh isolated Codex author received only issue title/body and the case-format specification.','format_specification':spec,'reported_usage':usage,'tool_events':0,'cases':data['cases']},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('authored cases',len(data['cases']),'reported_usage',usage)
