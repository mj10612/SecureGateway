"""Inspect real Codex requests locally; no account, model, or raw prompt saved.

Run: uv run --locked python docs/evaluations/issue380/probe_skills.py --write
The host's skill files are never changed. Only aggregate request measurements
are saved, because the control request can contain private skill descriptions.
"""

import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

from secure_gateway import evaluation_batch as batch


def probe(setting=None):
    requests = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            data = b'{"models": [], "data": []}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            body = json.loads(raw)
            text = json.dumps(body, ensure_ascii=False)
            markers = ["### Available skills", "<available_skills>", "<skills_instructions>"]
            requests.append({
                "request_bytes": len(raw),
                "instructions_chars": len(body.get("instructions") or ""),
                "skill_catalog_markers": {marker: text.count(marker) for marker in markers},
                "host_skill_path_mentions": text.count(".agents/skills") + text.count(".agents\\\\skills"),
            })
            item = {"type": "message", "role": "assistant", "id": "msg_probe",
                    "content": [{"type": "output_text", "text": "done"}]}
            events = [
                {"type": "response.created", "response": {"id": "resp_probe"}},
                {"type": "response.output_item.done", "item": item},
                {"type": "response.completed", "response": {"id": "resp_probe", "usage": {
                    "input_tokens": 11, "output_tokens": 1, "total_tokens": 12,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                }}},
            ]
            data = "".join("event: " + e["type"] + "\ndata: " + json.dumps(e) + "\n\n"
                           for e in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix="sg-380-probe-") as directory:
            root = Path(directory)
            home, workspace = root / "codex-home", root / "workspace"
            home.mkdir()
            workspace.mkdir()
            instructions = root / "instructions.md"
            instructions.write_text(batch.LEAN_BASE_INSTRUCTIONS, encoding="utf-8")
            command = batch.lean_command(shutil.which("codex"), model=batch.DEFAULT_EVAL_MODEL,
                                         output=root / "last.txt", instructions_file=instructions)[:-1]
            login = command.index('forced_login_method="chatgpt"')
            del command[login - 1:login + 1]  # local fake provider needs no login
            # Keep the control identical even after the adapter adopts the fix.
            isolation_setting = "skills.include_instructions=false"
            if isolation_setting in command:
                index = command.index(isolation_setting)
                del command[index - 1:index + 1]
            if setting:
                command += ["-c", setting]
            provider = {
                "model_provider": "probe", "model_providers.probe.name": "probe",
                "model_providers.probe.base_url": f"http://127.0.0.1:{server.server_port}/v1",
                "model_providers.probe.wire_api": "responses",
                "model_providers.probe.request_max_retries": 0,
                "model_providers.probe.stream_max_retries": 0,
                "check_for_update_on_startup": False,
            }
            for key, value in provider.items():
                command += ["-c", key + "=" + json.dumps(value)]
            env = {key: value for key, value in os.environ.items() if key in batch._ALLOWED_ENV}
            env["CODEX_HOME"] = str(home)
            proc = subprocess.run(command + ["-"], input=b"Say done.", cwd=workspace,
                                  env=env, capture_output=True, timeout=60)
            return {"setting": setting,
                    "exit_code": proc.returncode, "requests": requests,
                    "completed": (root / "last.txt").exists()}
    finally:
        server.shutdown()
        server.server_close()


def main():
    results = [probe(), probe("features.skip_host_skill_discovery=true"),
               probe("skills.include_instructions=false")]
    doc = {
        "probe": "local fake Responses endpoint; empty CODEX_HOME; no account or model call",
        "codex_cli": subprocess.check_output([shutil.which("codex"), "--version"], text=True).strip(),
        "usage_note": "Endpoint usage values are synthetic; request bytes are measured, not tokens.",
        "results": results,
    }
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if "--write" in sys.argv:
        Path(__file__).with_name("probe-results.json").write_text(text, encoding="utf-8")
    print(text)
    assert all(row["exit_code"] == 0 and row["completed"] and row["requests"] for row in results)
    assert any(results[0]["requests"][0]["skill_catalog_markers"].values()), "Control has no skill catalog"
    assert not any(results[-1]["requests"][0]["skill_catalog_markers"].values()), "Skills still transmitted"
    assert results[-1]["requests"][0]["host_skill_path_mentions"] == 0, "Host skill paths still transmitted"


if __name__ == "__main__":
    main()
