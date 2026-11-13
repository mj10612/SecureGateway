"""Offline probe for #372: which tools a Codex evaluation session offers and what a call leaves behind.

No model and no account: the real Codex CLI runs against a local fake Responses
endpoint, with CODEX_HOME set to an empty temporary directory and the provider
overridden on the argv (``forced_login_method`` is dropped only for that reason).
The fake model either answers at once or makes one scripted tool call and then
answers. For each scenario the probe records the tools offered in the first
request, the ``--json`` event shapes, the tool output the CLI sent back, the
CLI's stderr tool-router lines (timestamps removed) and what the lean adapter's
checks decide. Request bodies are not saved (they include the CLI's local skill
list).

    uv run --locked python docs/evaluations/issue372/probe_372_code_mode.py [--write]
"""
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading

from secure_gateway import evaluation_batch as eb

HERE = Path(__file__).resolve().parent
USAGE = {"input_tokens": 11, "input_tokens_details": {"cached_tokens": 0}, "output_tokens": 7,
         "output_tokens_details": {"reasoning_tokens": 0}, "total_tokens": 18}
PATCH = "*** Begin Patch\n*** Add File: probe_written.txt\n+hello\n*** End Patch\n"
OLD_LEAN = {"drop": ["code_mode_host"]}  # 2.15.0-2.17.0 lean argv
NATIVE = {"native": True}  # frozen evaluation_codex_worker argv
SCENARIOS = [
    ("lean-2.17.0", "answer", OLD_LEAN, None),
    ("lean-2.17.0", "exec lists nested tools", OLD_LEAN, ("custom", "exec", "text(JSON.stringify(ALL_TOOLS.map(t => t.name)));")),
    ("lean-2.17.0", "exec calls clock", OLD_LEAN, ("custom", "exec", "text(JSON.stringify(await tools.clock__curr_time({})));")),
    ("lean-2.17.0", "exec probes globals", OLD_LEAN, ("custom", "exec", "text(JSON.stringify([typeof require, typeof process, typeof fetch, typeof Deno]));")),
    ("lean-2.17.0", "exec calls apply_patch", OLD_LEAN, ("custom", "exec", "text(JSON.stringify(await tools.apply_patch(" + json.dumps(PATCH) + ")));")),
    ("lean-2.17.1", "answer", {}, None),
    ("lean-2.17.1", "exec lists nested tools", {}, ("custom", "exec", "text(JSON.stringify(ALL_TOOLS.map(t => t.name)));")),
    ("lean-2.17.1", "exec calls clock", {}, ("custom", "exec", "text(JSON.stringify(await tools.clock__curr_time({})));")),
    ("lean-2.17.1", "wait", {}, ("function", "wait", json.dumps({"cell_id": "1"}))),
    ("lean-2.17.1", "direct apply_patch", {}, ("custom", "apply_patch", PATCH)),
    ("lean-2.17.1", "spawn_agent", {}, ("function", "spawn_agent", json.dumps({"message": "hi"}))),
    ("lean-2.17.1", "request_user_input_async", {}, ("function", "request_user_input_async", json.dumps({"questions": [{"title": "Which one?"}]}))),
    ("native", "answer", NATIVE, None),
    ("native", "exec lists nested tools", NATIVE, ("custom", "exec", "text(JSON.stringify(ALL_TOOLS.map(t => t.name)));")),
    ("native", "exec runs a command", NATIVE, ("custom", "exec", "text(JSON.stringify(await tools.exec_command({cmd: 'echo hi'})));")),
    ("native", "exec views a file outside cwd", NATIVE, ("custom", "exec", "text(JSON.stringify(await tools.view_image({path: '../outside.txt'})));")),
]


def sse(events):
    return "".join("event: " + e["type"] + "\ndata: " + json.dumps(e) + "\n\n" for e in events).encode()


def offered(body):
    names = []

    def walk(tools, prefix=""):
        for tool in tools or []:
            if tool.get("type") == "namespace":
                walk(tool.get("tools"), tool.get("name", "") + "/")
            elif tool.get("name"):
                names.append(prefix + tool["name"])
    walk(body.get("tools"))
    for item in body.get("input") or []:
        if isinstance(item, dict) and item.get("type") == "additional_tools":
            walk(item.get("tools"))
    return names


def make_handler(log, call):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            body = json.dumps({"models": [], "data": []}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            outputs = [i for i in body.get("input") or []
                       if isinstance(i, dict) and str(i.get("type", "")).endswith("_output")]
            log.append({"tools": offered(body), "tool_output": [str(o.get("output"))[:300] for o in outputs]})
            n = len(log)
            if outputs or call is None:
                item = {"type": "message", "role": "assistant", "id": f"msg_{n}",
                        "content": [{"type": "output_text", "text": "done"}]}
            elif call[0] == "custom":
                item = {"type": "custom_tool_call", "id": f"ctc_{n}", "call_id": f"call_{n}",
                        "name": call[1], "input": call[2]}
            else:
                item = {"type": "function_call", "id": f"fc_{n}", "call_id": f"call_{n}",
                        "name": call[1], "arguments": call[2]}
            data = sse([{"type": "response.created", "response": {"id": f"resp_{n}"}},
                        {"type": "response.output_item.done", "item": item},
                        {"type": "response.completed", "response": {"id": f"resp_{n}", "usage": USAGE}}])
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    return Handler


def command(codex, out, instructions, variant):
    if variant.get("native"):
        cmd = [codex, "exec", "--ephemeral", "--skip-git-repo-check", "--ignore-user-config",
               "--ignore-rules", "--sandbox", "read-only", "--model", eb.DEFAULT_EVAL_MODEL, "--json",
               "--output-last-message", str(out), "-c", 'forced_login_method="chatgpt"',
               "-c", "project_doc_max_bytes=0", "-c", 'developer_instructions=""',
               "-c", 'web_search="disabled"', "-c", "features.multi_agent=false", "-"]
    else:
        cmd = eb.lean_command(codex, model=eb.DEFAULT_EVAL_MODEL, output=out, instructions_file=instructions)
    cmd = cmd[:-1]
    for value in ['forced_login_method="chatgpt"', *variant.get("drop", [])]:
        i = cmd.index(value)
        del cmd[i - 1:i + 1]
    return cmd


def run(variant, call):
    log = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), make_handler(log, call))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix="sg-372-probe-") as d:
            root = Path(d)
            home, workspace = root / "codex-home", root / "workspace"
            home.mkdir()
            workspace.mkdir()
            (root / "outside.txt").write_text("synthetic text outside the working directory", encoding="utf-8")
            instructions = root / "instructions.md"
            instructions.write_text(eb.LEAN_BASE_INSTRUCTIONS, encoding="utf-8")
            out = root / "last.txt"
            cmd = command(shutil.which("codex"), out, instructions, variant)
            provider = {"model_provider": "probe", "model_providers.probe.name": "probe",
                        "model_providers.probe.base_url": f"http://127.0.0.1:{server.server_address[1]}/v1",
                        "model_providers.probe.wire_api": "responses",
                        "model_providers.probe.request_max_retries": 0,
                        "model_providers.probe.stream_max_retries": 0, "check_for_update_on_startup": False}
            for key, value in provider.items():
                cmd += ["-c", key + "=" + json.dumps(value)]
            env = {k: v for k, v in os.environ.items() if k in eb._ALLOWED_ENV}
            env["CODEX_HOME"] = str(home)  # empty: no user config, no login
            proc = subprocess.run(cmd + ["-"], input=b"Say hi.", cwd=workspace, env=env,
                                  capture_output=True, timeout=180)
            events = [json.loads(x) for x in proc.stdout.splitlines() if x.strip()]
            try:
                eb.parse_events(proc.stdout)
                verdict = "rejected (stderr tool log)" if eb._TOOL_LOG_MARKER in proc.stderr else "accepted"
            except ValueError as exc:
                verdict = "rejected (events): " + str(exc)
            router = [re.sub(r"^\S+\s+", "", line) for line in proc.stderr.decode("utf-8", "replace").splitlines()
                      if "codex_core::tools" in line]
            return {
                "exit_code": proc.returncode,
                "offered_tools": log[0]["tools"] if log else None,
                "model_requests": len(log),
                "event_shapes": [e["type"] + ("/" + e["item"]["type"] if isinstance(e.get("item"), dict) else "")
                                 for e in events],
                "warning_items": [e["item"]["message"] for e in events
                                  if isinstance(e.get("item"), dict) and e["item"].get("type") == "error"],
                "turn_usage": next((e.get("usage") for e in events if e["type"] == "turn.completed"), None),
                "tool_output_seen_by_model": log[-1]["tool_output"] if len(log) > 1 else [],
                "stderr_tool_router": router,
                "workspace_files_after": sorted(p.name for p in workspace.iterdir()),
                "lean_adapter_2_17_1_checks": verdict,
            }
    finally:
        server.shutdown()


def main():
    codex = shutil.which("codex")
    version = subprocess.run([codex, "--version"], capture_output=True, timeout=30,
                             env={**os.environ, "CODEX_HOME": tempfile.mkdtemp(prefix="sg-372-v-")}).stdout
    results = []
    for config, scenario, variant, call in SCENARIOS:
        result = {"config": config, "scenario": scenario, "fake_model_call": call}
        result.update(run(variant, call))
        results.append(result)
        print(config, "|", scenario, "|", result["event_shapes"], "|", result["lean_adapter_2_17_1_checks"])
    doc = {"probe": "offline fake Responses endpoint; real Codex CLI; empty CODEX_HOME; no model, no account",
           "codex_cli": version.decode().strip().splitlines()[-1], "model_metadata": eb.DEFAULT_EVAL_MODEL,
           "fake_usage_per_model_request": USAGE["input_tokens"], "results": results}
    if "--write" in sys.argv:
        (HERE / "probe-results.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                                                 encoding="utf-8")


if __name__ == "__main__":
    main()
