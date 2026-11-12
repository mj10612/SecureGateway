"""Summarize a completed paired comprehension report without changing scores."""
import json,sys
from pathlib import Path
n=int(sys.argv[1]); root=Path('docs/evaluations/comprehension-2.11.1')/str(n); out=root/('comprehension-policy' if n==317 else 'comprehension'); r=json.loads((out/'report.json').read_text(encoding='utf8'))
t=[f'# #{n} real-LLM comprehension','','The interpreter and grader use the same model family. These synthetic cases were enriched for observable candidate differences and do not estimate population rates.']
for variant,x in r['results'].items():
 p=x['protection']; counts=x['whole_task_passes']; t += ['',f"## {variant}: {x['decision']}",'',f"A-eligible cases: {x['analysis_cases']}. Whole-task pass counts: "+', '.join(f'{a}={b}' for a,b in counts.items())+f"; D-only={x['D_only']}, C-only={x['C_only']}, one-sided p={x['p_one_sided']}. Negative controls: {x['negative_control_count']}; net loss={x['negative_control_net_loss']}.",'',f"Protection: {p['newly_protected']} newly protected of {p['sensitive_spans']} spans, {p['newly_exposed']} newly exposed; public overmask C/D={p['baseline_overmasked']}/{p['candidate_overmasked']} of {p['public_spans']}; exact restore C/D={p['baseline_exact_restore']}/{p['candidate_exact_restore']} of {p['cases']}; CI={p['ci']['status']}.",'','| Criterion | A | C | D | Cases |','| --- | ---: | ---: | ---: | ---: |']
 for k,v in x['per_criterion'].items():t.append(f"| {k} | {v['A']} | {v['C']} | {v['D']} | {v['cases']} |")
 if x.get('additional_missing'):t+=['',f"Missing: {x['additional_missing']}."]
t += ['',f"Fresh interpretations: {r['interpretations']}; blinded quote-verified grades: {r['grades']}; successful-call raw tokens: {r['raw_tokens']}; content tokens: {r['content_tokens']}.",'','See the manifest, first responses, first grades, frozen rubric and decision, and report JSON for isolation, per-case evidence, usage, and reproducibility.']
(out/'summary.md').write_text('\n'.join(t)+'\n',encoding='utf8')
