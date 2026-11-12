"""Independent synthetic protection author for issue 310; explicit invocation only."""
import json, os, pathlib, shutil, subprocess, tempfile
issue=json.loads(subprocess.check_output(["gh","issue","view","310","--json","title,body"],encoding="utf-8"))
spec="""Create 22 original synthetic independent offline privacy holdout cases as JSON object with key cases, no markdown. Use only fictional values, no real personal information, no tools or prior context. Each case has id, original, sensitive_spans, public_spans. Each original must include exactly six distinct confidential names introduced explicitly by name-role expressions described in the issue, and six distinct ordinary public words used in their literal, non-name sense. Annotate every span with {start,end,text}: zero-based Unicode codepoint offsets, end exclusive, disjoint, exact substrings occurring once in the case. Names should be everyday words and varied across project, company, customer, product, team, and facility names and Korean and English sentences; vary syntax and include adjacent action, conditions, prohibition, and ordering where natural. Do not use forced secret dictionaries. No use of candidate code or prior responses. Return only valid JSON."""
prompt="Issue text:\n"+json.dumps(issue,ensure_ascii=False)+"\n\nCase-format specification:\n"+spec
with tempfile.TemporaryDirectory(prefix="secure-case-author-") as root:
 output=pathlib.Path(root)/"out.json"; events=pathlib.Path(root)/"events.jsonl"
 cmd=[shutil.which("codex"),"exec","--ephemeral","--skip-git-repo-check","--ignore-user-config","--ignore-rules","--sandbox","read-only","--model","gpt-6.1-sol","--json","--output-last-message",str(output),"-c",'forced_login_method="chatgpt"',"-c","project_doc_max_bytes=0","-c",'developer_instructions=""',"-c",'web_search="disabled"',"-c","features.multi_agent=false","-c",'model_reasoning_effort="low"',"-"]
 allowed={"PATH","HOME","USERPROFILE","CODEX_HOME","SYSTEMROOT","WINDIR","TEMP","TMP","TMPDIR","LANG","LC_ALL","LC_CTYPE","HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","NO_PROXY","http_proxy","https_proxy","all_proxy","no_proxy","SSL_CERT_FILE","SSL_CERT_DIR","REQUESTS_CA_BUNDLE","NODE_EXTRA_CA_CERTS"}; env={k:v for k,v in os.environ.items() if k in allowed}
 with events.open("wb") as f:p=subprocess.run(cmd,input=prompt.encode("utf8"),stdout=f,stderr=subprocess.DEVNULL,cwd=root,timeout=600,env=env)
 if p.returncode:raise RuntimeError("author_process_failed")
 usage=None; completed=False
 for line in events.read_text(encoding="utf8").splitlines():
  e=json.loads(line); t=e.get("type")
  if t.startswith("item.") and e.get("item",{}).get("type") not in ("agent_message","reasoning"):raise ValueError("tool_event")
  if t in ("error","turn.failed"):raise ValueError("failed_turn")
  if t=="turn.completed":completed=True;usage=e.get("usage")
 if not completed or not usage:raise ValueError("missing_usage")
 data=json.loads(output.read_text(encoding="utf8")); assert isinstance(data["cases"],list)
 out=pathlib.Path("docs/evaluations/comprehension-2.11.1/310/plan/introducer-authored.json")
 out.write_text(json.dumps({"provenance":"Fresh isolated author received issue title/body and case-format specification only.","format_specification":spec,"reported_usage":usage,"tool_events":0,"cases":data["cases"]},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
 print("Authored cases",len(data["cases"]),"usage",usage)
