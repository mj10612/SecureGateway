"""Default-engine multilingual descriptive study with fresh isolated calls."""
import hashlib,importlib.util,json,random,sys
from pathlib import Path
ROOT=Path("docs/evaluations/comprehension-2.11.1");sp=importlib.util.spec_from_file_location("base",ROOT/"plan/run_comprehension.py");base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
def prepare():
 out=ROOT/"291/comprehension";out.mkdir(parents=True,exist_ok=True);path=out/"manifest.json";identity=base.sha([base.run_identity(291),hashlib.sha256(Path(__file__).read_bytes()).hexdigest()])
 if path.exists():
  result=json.loads(path.read_text(encoding="utf8"))
  if result.get("run_identity")!=identity:raise ValueError("RunIdentityMismatch")
  return result,out
 cases=json.loads((ROOT/"291/plan/cases.json").read_text(encoding="utf8"))["cases"];rubric=json.loads((ROOT/"291/plan/rubric.json").read_text(encoding="utf8"));lookup={x["id"]:x for x in rubric["criteria"]};entries=[];jobs=[]
 for c in cases:
  masked=base.capture(291,c,None);arms={"A":{"instructions":masked["instructions"],"input":c["original"],"aliases":{}},"C":masked};entries.append({"case_id":c["id"],"language":c["language"],"original":c["original"],"expected":c["expected"],"negative_control":c.get("negative_control",False),"applicable":c["applicable"],"arms":arms})
  for label,arm in arms.items():
   request={"role":"interpret","job_id":base.sha([291,c["id"],label])[:32],"model":base.MODEL,"max_output_tokens":512,"reasoning_effort":base.EFFORT,"messages":[{"role":"system","content":arm["instructions"]},{"role":"user","content":arm["input"]}]};jobs.append({"case_id":c["id"],"arm":label,"request":request})
 for name in ("rubric.json","decision.json"):
  (out/("frozen-"+name)).write_bytes((ROOT/"291/plan"/name).read_bytes())
 random.Random(20261111291).shuffle(jobs);result={"schema_version":1,"issue":291,"run_identity":identity,"model":base.MODEL,"effort":base.EFFORT,"cases":entries,"jobs":jobs,"criterion_definitions":lookup,"shuffle_seed":20261111291,"disclosure":"Same model family interprets and grades; default engine only."};base.evaluation.write_json(path,result);return result,out
def run():
 manifest,out=prepare();original=base.grade_request
 def capped(*args):
  req,blind,responses=original(*args);req["max_output_tokens"]=768;return req,blind,responses
 base.grade_request=capped;baseline=base.token_baseline()
 if not base.interpret(manifest,out,baseline):print("INCOMPLETE interpretation");return 1
 if not base.grades(manifest,out,baseline):print("INCOMPLETE grading");return 1
 grades={x["case_id"]:x for x in base.read_rows(out/"first-grades.jsonl")};bylang={}
 for c in manifest["cases"]:
  grade=grades[c["case_id"]];arms={}
  for g in grade["attempts"][-1]["result"]["grades"]:
   label,criterion=g["id"].split("::",1);arms.setdefault(grade["blind_labels"][label],{})[criterion]=g["passed"]
  if set(arms)!={"A","C"}:raise ValueError("MissingArm")
  v=bylang.setdefault(c["language"],{"cases":0,"A_pass":0,"C_pass":0,"eligible":0,"eligible_C_pass":0});v["cases"]+=1;a=all(arms["A"].values());b=all(arms["C"].values());v["A_pass"]+=a;v["C_pass"]+=b;v["eligible"]+=a;v["eligible_C_pass"]+=a and b
 responses=base.read_rows(out/"first-responses.jsonl");usage=responses+[a for g in grades.values() for a in g["attempts"] if a["status"]=="completed"];report={"status":"completed","decision":"DESCRIPTIVE ONLY: no candidate","languages":bylang,"interpretations":len(responses),"grades":len(grades),"raw_tokens":sum(x.get("raw_tokens",0) for x in usage),"content_tokens":sum(x.get("content_tokens",0) for x in usage),"limitation":"Same model family interpreted and graded; two everyday cases per language plus two known controls are not a population estimate."};base.evaluation.write_json(out/"report.json",report);print("291 completed; descriptive only");return 0
if __name__=="__main__":
 try:sys.exit(run())
 except Exception as e:print("runner failure category",type(e).__name__);sys.exit(1)
