"""Offline transport probe for the #319 replication: no model, no account.

Runs the real Codex CLI with the exact run_319_replication D argv (lean and
native variants) against a local fake Responses endpoint, with CODEX_HOME set to
an empty temporary directory so no user configuration or login is read. The fake
model requests the MCP tool exactly once with the case's issued aliases and then
answers with the tool's output. The probe records whether the MCP tool is
offered, whether Codex executes it through the real stdio fixture, the event
shapes the fail-closed audit sees, and the size of each request (a proxy for the
fixed per-call overhead). Only the provider endpoint differs from a real run.

    uv run --locked python docs/evaluations/comprehension-2.11.1/plan/probe_319_codex_mcp.py
"""
import http.server
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run_319_replication", HERE / "run_319_replication.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


FIRST_RESPONSE_DELAY = float(os.environ.get("PROBE_DELAY", "10"))


def sse(events):
    return "".join("event: " + e["type"] + "\ndata: " + json.dumps(e) + "\n\n" for e in events).encode()


def usage():
    return {"input_tokens": 11, "input_tokens_details": {"cached_tokens": 0}, "output_tokens": 7,
            "output_tokens_details": {"reasoning_tokens": 0}, "total_tokens": 18}


def make_handler(log, aliases, operation, tag=""):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            log.append({"method": "GET", "path": self.path})
            body = json.dumps({"models": [], "data": []}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if not log:
                time.sleep(FIRST_RESPONSE_DELAY)  # a real model takes seconds; MCP startup is asynchronous
            body = json.loads(raw)
            if os.environ.get("PROBE_DUMP"):
                Path(os.environ["PROBE_DUMP"], f"{tag}req{len(log)}.json").write_bytes(raw)
            items = body.get("input") or []
            names = []

            def walk(tools, prefix=""):
                for t in tools or []:
                    name = t.get("name") or (t.get("function") or {}).get("name")
                    if t.get("type") == "namespace":
                        walk(t.get("tools"), (name or "") + "/")
                    elif name:
                        names.append(prefix + name)
            walk(body.get("tools"))
            for i in items:
                if isinstance(i, dict) and i.get("type") == "additional_tools":
                    walk(i.get("tools"))
            mcp = [n for n in names if "local_alias_arithmetic" in n]
            exec_offered = "functions/exec" in names or "exec" in names
            # Is the MCP tool named in any tool definition (e.g. inside the exec description)?
            definitions = json.dumps([body.get("tools")] + [i for i in items if isinstance(i, dict)
                                                             and i.get("type") == "additional_tools"])
            described = definitions.count(r.TOOL)
            outputs = [i for i in items if isinstance(i, dict)
                       and i.get("type") in ("function_call_output", "custom_tool_call_output")]
            log.append({"method": "POST", "path": self.path, "request_bytes": len(raw),
                        "instructions_chars": len(body.get("instructions") or ""), "tools": names,
                        "mcp_tool_offered_directly": bool(mcp), "mcp_tool_named_in_request": described,
                        "has_tool_output": bool(outputs)})
            n = len(log)
            arguments = {"operation": operation, "aliases": aliases}
            if outputs or not (mcp or exec_offered):
                text = json.dumps(outputs[-1].get("output"), ensure_ascii=False) if outputs else "no tool offered"
                found = re.findall("⟦?private_symbol_\\d+⟧?", text)
                answer = ("Protected result alias: " + found[-1]) if found else "No result: " + text[:300]
                item = {"type": "message", "role": "assistant", "id": f"msg_{n}",
                        "content": [{"type": "output_text", "text": answer}]}
            elif mcp:
                item = {"type": "function_call", "id": f"fc_{n}", "call_id": f"call_{n}", "name": mcp[0].split("/")[-1],
                        "arguments": json.dumps(arguments, ensure_ascii=False)}
            else:  # code mode: the nested MCP tool is reachable only from the exec tool
                js = ("text(JSON.stringify(ALL_TOOLS.map(t => t.name)));\n"
                      f"const fn = Object.keys(tools).find(k => k.includes('{r.TOOL}'));\n"
                      "text(String(fn));\n"
                      f"if (fn) text(JSON.stringify(await tools[fn]({json.dumps(arguments, ensure_ascii=False)})));\n")
                item = {"type": "custom_tool_call", "id": f"ctc_{n}", "call_id": f"call_{n}", "name": "exec",
                        "input": js}
            events = [{"type": "response.created", "response": {"id": f"resp_{n}"}},
                      {"type": "response.output_item.done", "item": item},
                      {"type": "response.completed", "response": {"id": f"resp_{n}", "usage": usage()}}]
            data = sse(events)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    return Handler


def probe(case, lean, arm, required=True):
    r.LEAN = lean
    order = case["expected_operand_order"]
    aliases = [case["operand_aliases"][i] for i in order]
    log = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), make_handler(log, aliases, case["operation"], f"{lean}-{arm}-"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    provider = {"model_provider": "probe", "model_providers.probe.name": "probe",
                "model_providers.probe.base_url": f"http://127.0.0.1:{server.server_address[1]}/v1",
                "model_providers.probe.wire_api": "responses", "model_providers.probe.request_max_retries": 0,
                "model_providers.probe.stream_max_retries": 0, "check_for_update_on_startup": False}
    try:
        with tempfile.TemporaryDirectory(prefix="sg-319r-codexprobe-") as d:
            root = Path(d)
            home, ws, owner = root / "codex-home", root / "workspace", root / "owner"
            for p in (home, ws, owner):
                p.mkdir()
            instructions = root / "instructions.md"
            instructions.write_text(r.eb.LEAN_BASE_INSTRUCTIONS, encoding="utf-8")
            fixture = token = None
            if arm == "D":
                session, payload = r.capture(case)
                selected, _ = r.bind(case, session, payload)
                fixture, token = r.write_owner(owner, case, selected, session)
            out = root / "last.txt"
            command = r.codex_command(shutil.which("codex"), out, instructions, fixture, provider=provider)
            if not required:  # control: the run_319 argv without the required-server setting
                i = command.index("mcp_servers." + r.SERVER + ".required=true")
                del command[i - 1:i + 1]
            env = {k: v for k, v in os.environ.items() if k in r.ENV_KEYS}
            env["CODEX_HOME"] = str(home)  # empty: no user config, no login
            prompt = (r.wrapper(arm) + json.dumps(job_messages(case, arm), ensure_ascii=False)).encode()
            proc = r.run_process(command, prompt, ws, env)
            events = [json.loads(x) for x in proc.stdout.splitlines() if x.strip()]
            shapes = sorted({e.get("type") + ("/" + e["item"]["type"] if isinstance(e.get("item"), dict) else "")
                             for e in events})
            result = {"lean": lean, "arm": arm, "mcp_required": required if arm == "D" else None,
                      "exit_code": proc.returncode, "event_shapes": shapes, "requests": log,
                      "final_answer": out.read_text(encoding="utf-8") if out.exists() else None}
            try:
                calls, _usage = r.audit_events(proc.stdout, arm == "D")
                result["audit"] = "accepted"
                result["mcp_tool_calls"] = len(calls)
                result["mcp_results"] = [c.get("result") for c in calls]
                result["mcp_errors"] = [bool(c.get("error")) for c in calls]
            except Exception as exc:
                result["audit"] = "rejected:" + type(exc).__name__
                result["error_messages"] = [str((e.get("error") or e).get("message", ""))[:300]
                                            for e in events if e.get("type") in ("error", "turn.failed")]
            if fixture is not None and out.exists():
                owner_session = r.gateway.GatewaySession(r.load_session(owner / "session.enc", token, "arithmetic-fixture"))
                restored = owner_session.restore(out.read_text(encoding="utf-8"))
                result["restored_equals_gold"] = r.numeric(case["gold"])[:1] == r.numeric(restored)[-1:]
                result["fixture_calls"] = json.loads(fixture.read_text(encoding="utf-8")).get("calls")
            if proc.returncode and not events:
                result["stderr_tail"] = proc.stderr.decode("utf-8", "replace")[-600:]
            return result
    finally:
        server.shutdown()


def job_messages(case, arm):
    a = case["arms"][arm]
    return [{"role": "system", "content": a["instructions"]}, {"role": "user", "content": a["input"]}]


def main():
    manifest = r.load(r.PLAN / "manifest.json")
    case = next(c for c in manifest["cases"] if c["label"] == "tool_solvable" and c["operation"] == "add")
    results = [probe(case, lean, arm) for lean in (True, False) for arm in ("D", "C")]
    results.append(probe(case, True, "D", required=False))
    results.append(probe(case, False, "D", required=False))
    for x in results:
        for q in x["requests"]:
            q["tools_count"] = len(q.get("tools") or [])
    doc = {"probe": "offline fake Responses endpoint; real Codex CLI, real stdio MCP fixture; no model, no account",
           "codex_cli": r.capture_worker_process([shutil.which("codex"), "--version"], b"", timeout=30,
                                                 cwd=Path(tempfile.gettempdir())).stdout.decode().strip(),
           "case": case["case_id"], "first_response_delay_seconds": FIRST_RESPONSE_DELAY,
           "fake_model": ("If the MCP tool is offered directly it is called; otherwise the fake calls the code-mode "
                          "exec tool with JavaScript that lists ALL_TOOLS and calls the nested MCP tool if present; "
                          "it then answers with the tool output."),
           "results": results}
    out = r.PLAN / "transport-probe.json"
    if "--write" in sys.argv:
        r.dump(out, doc)
    print(json.dumps(doc, ensure_ascii=False, indent=1)[:12000])


if __name__ == "__main__":
    main()
