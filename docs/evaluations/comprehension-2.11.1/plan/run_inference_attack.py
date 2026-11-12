"""Frozen synthetic catalogue attack: isolated calls, paired analysis and resumable evidence."""
import argparse,hashlib,importlib.util,json,random,sys,time
from pathlib import Path
ROOT=Path("docs/evaluations/comprehension-2.11.1")
spec=importlib.util.spec_from_file_location("comprehension",ROOT/"plan/run_comprehension.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def prepare():
 source=m.prepare(318);cases=json.loads((ROOT/"318/plan/cases.json").read_text(encoding="utf8"))["cases"];byid={c["id"]:c for c in cases};jobs=[];gold={}
 for c in source["cases"]:
  case=byid[c["case_id"]]; catalogue=case["catalogue"];rows=list(catalogue["rows"]); random.Random(int(m.sha([318,c["case_id"],"catalogue"])[:16],16)).shuffle(rows); ids=[r[0] for r in rows];target=case["target_id"]
  if len(ids)!=8 or len(set(ids))!=8 or target not in ids:raise ValueError("InvalidCatalogue")
  gold[c["case_id"]]={"target":target,"ids":ids}
  for arm in ("prior","C","D1"):
   task={"catalogue":{"columns":catalogue["columns"],"rows":rows},"question":"Which catalogue identifier best matches the subject? Rank up to three identifiers, or abstain if insufficient evidence."}
   if arm!="prior":task["provider_visible_payload"]={k:v for k,v in c["arms"][arm].items() if k in ("instructions","input")}
   req={"role":"interpret","job_id":m.sha([318,c["case_id"],"attack",arm])[:32],"model":m.MODEL,"max_output_tokens":512,"reasoning_effort":m.EFFORT,"messages":[{"role":"system","content":"Use only the provided information. Return JSON only: {\"ranking\": [identifier, ...], \"rationale\": string}. Rank at most three distinct catalogue identifiers. Use an empty ranking to abstain. Do not use tools."},{"role":"user","content":json.dumps(task,ensure_ascii=False)}]};jobs.append({"case_id":c["case_id"],"arm":arm,"request":req})
 random.Random(20261111318).shuffle(jobs)
 return {"source_run_identity":source["run_identity"],"seed":20261111318,"cases":gold,"jobs":jobs,"protocol":"catalogue-only prior and paired C/D; rows identically permuted per case; gold never passed to attacker"}
def run():
 out=ROOT/"318/inference-attack";out.mkdir(parents=True,exist_ok=True);path=out/"manifest.json";new=prepare()
 if path.exists():
  manifest=json.loads(path.read_text(encoding="utf8"))
  if manifest!=new:raise ValueError("AttackManifestMismatch")
 else:manifest=new;m.evaluation.write_json(path,manifest)
 jobs={j["request"]["job_id"]:j for j in manifest["jobs"]};f=out/"first-responses.jsonl";rows=m.read_rows(f);seen=set()
 for r in rows:
  j=jobs.get(r.get("job_id"));result=r.get("result",{});meta=result.get("metadata",{})
  if not j or r["job_id"] in seen or r["case_id"]!=j["case_id"] or r["arm"]!=j["arm"] or r["status"]!="completed" or result.get("job_id")!=r["job_id"] or meta.get("fresh_session") is not True or meta.get("tool_events")!=0:raise ValueError("InvalidSavedAttack")
  seen.add(r["job_id"])
 baseline=m.token_baseline()
 for job in manifest["jobs"]:
  if job["request"]["job_id"] in seen:continue
  result=m.observed(job["request"],baseline);row={"job_id":job["request"]["job_id"],"case_id":job["case_id"],"arm":job["arm"],**result};m.append_row(f,row);rows.append(row);print("attack calls saved",len(rows),"of",len(jobs),"status",row["status"],flush=True)
  if result["status"]!="completed":return 1
 counts={a:{"top1":0,"top3":0,"abstained":0,"unsupported":0,"malformed":0} for a in ("prior","C","D1")};records=[]
 for row in rows:
  arm=row["arm"];case=manifest["cases"][row["case_id"]];raw=row["result"]["response"]
  try:
   parsed=json.loads(raw);ranking=parsed["ranking"];rationale=parsed["rationale"]
   if not isinstance(ranking,list) or len(ranking)>3 or not all(isinstance(x,str) for x in ranking) or len(set(ranking))!=len(ranking) or not isinstance(rationale,str):raise ValueError("InvalidRanking")
  except (ValueError,TypeError,KeyError):counts[arm]["malformed"]+=1;continue
  unsupported=any(x not in case["ids"] for x in ranking)
  if unsupported:counts[arm]["unsupported"]+=1;counts[arm]["malformed"]+=1;continue
  first=bool(ranking and ranking[0]==case["target"]);top3=case["target"] in ranking;counts[arm]["top1"]+=first;counts[arm]["top3"]+=top3;counts[arm]["abstained"]+=not ranking;records.append({"case_id":row["case_id"],"arm":arm,"top1":first,"top3":top3,"abstained":not ranking})
 valid=not any(v["malformed"] for v in counts.values());offline=json.loads((ROOT/"318/offline/318-bundle-table/summary.json").read_text(encoding="utf8"));summary={"status":"completed" if valid else "incomplete","cases":len(manifest["cases"]),"counts":counts,"top1_decreased":counts["D1"]["top1"]<counts["C"]["top1"] if valid else None,"direct_exposure_increase":offline["newly_exposed"],"attack_gate_passed":valid and counts["D1"]["top1"]<counts["C"]["top1"] and offline["newly_exposed"]==0,"records":records,"raw_tokens":sum(x.get("raw_tokens",0) for x in rows),"content_tokens":sum(x.get("content_tokens",0) for x in rows),"limitation":"Synthetic catalogue, one model family and one fresh attacker per condition; not a real-world inference estimate."};m.evaluation.write_json(out/"report.json",summary);print("attack",summary["status"],"gate",summary["attack_gate_passed"]);return 0 if valid else 1
if __name__=="__main__":
 try:sys.exit(run())
 except Exception as e:print("attack failure category",type(e).__name__);sys.exit(1)
