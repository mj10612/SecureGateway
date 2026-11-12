"""Independently author ten independent pre-measurement replacement cases."""
import json,os,pathlib,shutil,subprocess,tempfile
issue=json.loads(subprocess.check_output(["gh","issue","view","316","--json","title,body"],encoding="utf8"))
spec="""Create exactly 26 independent synthetic correction groups for an offline protection test. Return JSON with cases array, no markdown. Each group needs id, term, correction_input, correction_project, language (en or ko), followups and controls. Choose term as a common ordinary lowercase word in the group language used as a fictional confidential project or customer name; no real persons, contact details or secrets. correction_input must explicitly declare that term confidential in the named synthetic project, and contain the exact term once. Each followups list must contain four distinct new standalone sentences, each containing the exact term once as that confidential name. Each controls list must contain four distinct new standalone everyday sentences where the same exact term occurs once as an ordinary non-confidential word in a different project; never refer to the correction in a follow-up or control. Make sentences varied and natural, avoid other private values. correction_project should be a synthetic project identifier distinct per group. Ensure terms are unique across groups. No earlier responses, source code, implementation details, tools, files or external context."""
prompt="Issue text:\n"+json.dumps(issue,ensure_ascii=False)+"\n\nCase-format specification:\n"+spec
with tempfile.TemporaryDirectory(prefix="secure-case-author-") as root:
 out=pathlib.Path(root)/"out.json";ev=pathlib.Path(root)/"events.jsonl"
 cmd=[shutil.which("codex"),"exec","--ephemeral","--skip-git-repo-check","--ignore-user-config","--ignore-rules","--sandbox","read-only","--model","gpt-6.1-sol","--json","--output-last-message",str(out),"-c",'forced_login_method="chatgpt"',"-c","project_doc_max_bytes=0","-c",'developer_instructions=""',"-c",'web_search="disabled"',"-c","features.multi_agent=false","-c",'model_reasoning_effort="low"',"-"]
 allowed={"PATH","HOME","USERPROFILE","CODEX_HOME","SYSTEMROOT","WINDIR","TEMP","TMP","TMPDIR","LANG","LC_ALL","LC_CTYPE","HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","NO_PROXY","http_proxy","https_proxy","all_proxy","no_proxy","SSL_CERT_FILE","SSL_CERT_DIR","REQUESTS_CA_BUNDLE","NODE_EXTRA_CA_CERTS"};env={k:v for k,v in os.environ.items() if k in allowed}
 with ev.open("wb") as f:p=subprocess.run(cmd,input=prompt.encode("utf8"),stdout=f,stderr=subprocess.DEVNULL,cwd=root,timeout=600,env=env)
 if p.returncode:raise RuntimeError("AuthorProcessFailed")
 usage=None;completed=False
 for line in ev.read_text(encoding="utf8").splitlines():
  event=json.loads(line);kind=event.get("type")
  if kind.startswith("item.") and event.get("item",{}).get("type") not in ("agent_message","reasoning"):raise ValueError("ToolEvent")
  if kind in ("error","turn.failed"):raise ValueError("FailedTurn")
  if kind=="turn.completed":completed=True;usage=event.get("usage")
 if not completed or not usage:raise ValueError("MissingUsage")
 data=json.loads(out.read_text(encoding="utf8"));assert len(data["cases"])==26
 dest=pathlib.Path("docs/evaluations/comprehension-2.11.1/316/plan/correction-sensitive-authored.json");dest.write_text(json.dumps({"provenance":"Fresh isolated author received issue title/body and case-format specification only.","format_specification":spec,"reported_usage":usage,"tool_events":0,"cases":data["cases"]},ensure_ascii=False,indent=2)+"\n",encoding="utf8");print("Correction-sensitive groups authored; usage",usage)

