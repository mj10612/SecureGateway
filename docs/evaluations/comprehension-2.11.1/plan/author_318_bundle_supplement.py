"""Independently author ten independent pre-measurement replacement cases."""
import json,os,pathlib,shutil,subprocess,tempfile
issue=json.loads(subprocess.check_output(["gh","issue","view","318","--json","title,body"],encoding="utf8"))
spec="""Create exactly 5 original synthetic structured-data cases for an offline protection test. Return JSON with cases array and no markdown. Each case is an object with id, private_fields and public_fields. Each field list must contain four objects with distinct simple English field labels and value strings, for eight fields per case. The four private fields form a combination of contextual attributes which a local policy explicitly treats as confidential together (for example a fictional customer category, broad region, timing category and activity); their individual values must be ordinary lowercase everyday words, no digits, names, personal information or factual secrets. Public fields contain ordinary administrative details unrelated to identifying the target, also ordinary lowercase words. Each field label and value must be distinct within each case, values must not appear inside any other label or value of the same case. Vary the fields and values across cases. No source code, implementation details, earlier responses, tools, files, browsing or external context."""
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
 data=json.loads(out.read_text(encoding="utf8"));assert len(data["cases"])==5
 dest=pathlib.Path("docs/evaluations/comprehension-2.11.1/318/plan/bundle-sensitive-supplement-authored.json");dest.write_text(json.dumps({"provenance":"Fresh isolated author received issue title/body and case-format specification only.","format_specification":spec,"reported_usage":usage,"tool_events":0,"cases":data["cases"]},ensure_ascii=False,indent=2)+"\n",encoding="utf8");print("Bundle-sensitive groups authored; usage",usage)

