"""Independently author ten independent pre-measurement replacement cases."""
import json,os,pathlib,shutil,subprocess,tempfile
issue=json.loads(subprocess.check_output(["gh","issue","view","319","--json","title,body"],encoding="utf8"))
spec="""Author exactly ten original synthetic, self-contained holdout cases: 5 tool_solvable, 2 no_calculation, and 3 impossible. Return a JSON object with cases array and no markdown. Use fictional scenarios and confidential numeric operands. Tool-solvable examples should ask addition in USD; no-calculation cases should request no arithmetic, and impossible cases should lack required information or prohibit the operation. Include id, original, human_masked (replace the confidential operands with neutral [PRIVATE_1] and [PRIVATE_2]), negative_control=true for no_calculation, otherwise false, applicable array chosen from intent, action, conditions, prohibition, order, clarification, scope; expected specific correct task behavior, label chosen from tool_solvable, no_calculation, impossible; operation and unit appropriate to the case; gold as a string stating the correct expected result or limitation; sensitive_spans and public_spans arrays of {start,end,text}, zero-based Unicode character offsets, end exclusive. Public spans must be ordinary task words, not numeric values or private identifiers. Each span text must occur exactly once in original, spans must not overlap. No real personal information, no prior context, no tools, no implementation code."""
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
 data=json.loads(out.read_text(encoding="utf8"));assert len(data["cases"])==10
 dest=pathlib.Path("docs/evaluations/comprehension-2.11.1/319/plan/ten-replacements-authored.json");dest.write_text(json.dumps({"provenance":"Fresh isolated author received issue title/body and case-format specification only.","format_specification":spec,"reported_usage":usage,"tool_events":0,"cases":data["cases"]},ensure_ascii=False,indent=2)+"\n",encoding="utf8");print("Ten replacement cases authored; usage",usage)

