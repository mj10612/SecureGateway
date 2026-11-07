"""Executable protocol fixtures; these are not actual-LLM comprehension tests."""

import importlib
import os
import sys
import textwrap
import time

import pytest


@pytest.fixture
def request_payload():
    return {
        "role": "interpret",
        "job_id": "8bf1a1b9-4545-4aba-a25a-9a5fdf79f914",
        "model": "test-model",
        "max_output_tokens": 100,
        "messages": [{"role": "user", "content": "Explain the supplied sentence."}],
    }


@pytest.fixture
def workspace(tmp_path):
    path = tmp_path / "private"
    path.mkdir(mode=0o700)
    return path


def executable(tmp_path, source):
    path = tmp_path / "worker.py"
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return [sys.executable, str(path)]


def run_worker(command, request, workspace, timeout=3):
    module = importlib.import_module("secure_gateway.evaluation_worker")
    return module.execute_worker(command, request, timeout=timeout, cwd=workspace)


def result_script(tmp_path, changes=None):
    changes = changes or {}
    return executable(tmp_path, f"""
        import json, sys
        request = json.load(sys.stdin)
        result = {{'job_id': request['job_id'], 'model': 'test-model', 'response': 'Meaning preserved.'}}
        result.update({changes!r})
        print(json.dumps(result))
    """)


def test_executes_argv_in_empty_workspace_with_json_stdin(tmp_path, workspace, request_payload):
    command = executable(tmp_path, """
        import json, os, sys
        request = json.load(sys.stdin)
        assert not os.listdir('.')
        assert sys.argv[1] == 'literal;$(touch untrusted)'
        assert request['messages'][0]['content'] == 'Explain the supplied sentence.'
        print(json.dumps({'job_id': request['job_id'], 'model': request['model'],
                          'response': 'Meaning preserved.', 'usage': {'total_tokens': 12}}))
    """)
    result = run_worker(command + ["literal;$(touch untrusted)"], request_payload, workspace)
    assert result == {
        "job_id": "8bf1a1b9-4545-4aba-a25a-9a5fdf79f914",
        "model": "test-model", "response": "Meaning preserved.",
        "usage": {"total_tokens": 12},
    }


@pytest.mark.parametrize("changes", [
    {"job_id": "other"}, {"model": " "}, {"response": " "}, {"response": 42},
    {"usage": {"total_tokens": -1}}, {"usage": {"total_tokens": True}},
    {"usage": {"total_tokens": 12, "output_tokens": 101}},
    {"error": "provider failed"}, {"response": "x" * 401},
])
def test_rejects_invalid_result(tmp_path, workspace, request_payload, changes):
    with pytest.raises(ValueError):
        run_worker(result_script(tmp_path, changes), request_payload, workspace)


@pytest.mark.parametrize("output", ["[]", "{}", "null", "not json", '{"model":"a","model":"b"}', '{"value":NaN}'])
def test_rejects_malformed_json(tmp_path, workspace, request_payload, output):
    command = executable(tmp_path, f"print({output!r})")
    with pytest.raises(ValueError):
        run_worker(command, request_payload, workspace)


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_output_is_bounded_while_process_is_running(tmp_path, workspace, request_payload, stream):
    command = executable(tmp_path, f"""
        import sys, time
        sys.{stream}.write('x' * (2 * 1024 * 1024))
        sys.{stream}.flush()
        time.sleep(10)
    """)
    start = time.monotonic()
    with pytest.raises(ValueError, match="output limit"):
        run_worker(command, request_payload, workspace)
    assert time.monotonic() - start < 2


def test_timeout_does_not_wait_for_worker_to_read_stdin(tmp_path, workspace, request_payload):
    command = executable(tmp_path, "import time; time.sleep(10)")
    request_payload["messages"][0]["content"] = "a" * 200000
    with pytest.raises(ValueError, match="timed out"):
        run_worker(command, request_payload, workspace, timeout=0.15)


@pytest.mark.skipif(os.name == "nt", reason="POSIX process-group guarantee")
def test_timeout_kills_descendants(tmp_path, workspace, request_payload):
    marker = tmp_path / "escaped"
    child_source = f"import pathlib,time; time.sleep(.6); pathlib.Path({str(marker)!r}).touch()"
    command = executable(tmp_path, f"""
        import subprocess, sys, time
        subprocess.Popen([sys.executable, '-c', {child_source!r}])
        time.sleep(10)
    """)
    with pytest.raises(ValueError, match="timed out"):
        run_worker(command, request_payload, workspace, timeout=0.15)
    time.sleep(0.7)
    assert not marker.exists()


def test_worker_failure_does_not_disclose_stderr(tmp_path, workspace, request_payload):
    command = executable(tmp_path, "import sys; print('AUTH_SECRET', file=sys.stderr); sys.exit(2)")
    with pytest.raises(ValueError) as caught:
        run_worker(command, request_payload, workspace)
    assert "AUTH_SECRET" not in str(caught.value)


@pytest.mark.parametrize("changes", [
    {"role": "unknown"}, {"model": ""}, {"job_id": ""},
    {"max_output_tokens": 0}, {"max_output_tokens": True},
    {"messages": [{"role": "tool", "content": "x"}]}, {"messages": []},
    {"criteria": [{"id": "invented", "description": "no"}]},
])
def test_rejects_invalid_request_before_launch(tmp_path, workspace, request_payload, changes):
    request_payload.update(changes)
    with pytest.raises(ValueError):
        run_worker([str(tmp_path / "missing")], request_payload, workspace)


def test_refuses_nonempty_workspace(tmp_path, workspace, request_payload):
    (workspace / "answer-key").write_text("secret", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        run_worker(result_script(tmp_path), request_payload, workspace)


@pytest.mark.parametrize("grades", [
    [{"id": "c1", "passed": True, "evidence": "The answer states the relationship."}],
    [],
    [{"id": "invented", "passed": True, "evidence": "x"}],
    [{"id": "c1", "passed": "yes", "evidence": "x"}],
    [{"id": "c1", "passed": True, "evidence": ""}],
    [{"id": "c1", "passed": True, "evidence": "x"}] * 2,
])
def test_grader_requires_exact_criteria(tmp_path, workspace, request_payload, grades):
    request_payload.update(role="grade", criteria=[{"id": "c1", "description": "States the relationship."}])
    command = executable(tmp_path, f"""
        import json,sys
        request = json.load(sys.stdin)
        print(json.dumps({{'job_id': request['job_id'], 'model': 'test-model', 'grades': {grades!r}}}))
    """)
    if len(grades) == 1 and type(grades[0]["passed"]) is bool and grades[0]["id"] == "c1" and grades[0]["evidence"]:
        assert run_worker(command, request_payload, workspace)["grades"] == grades
    else:
        with pytest.raises(ValueError):
            run_worker(command, request_payload, workspace)


def fake_codex(tmp_path, source):
    path = tmp_path / "codex"
    path.write_text("#!" + sys.executable + "\n" + textwrap.dedent(source), encoding="utf-8")
    path.chmod(0o700)
    return path


def test_codex_adapter_uses_fresh_context_and_records_usage(tmp_path, monkeypatch, request_payload):
    fake_codex(tmp_path, """
        import json, os, pathlib, sys
        if '--version' in sys.argv:
            print('codex-cli 9.9.9')
            sys.exit(0)
        args = sys.argv[1:]
        assert args[0] == 'exec'
        assert all(flag in args for flag in ['--ephemeral', '--skip-git-repo-check', '--ignore-user-config', '--ignore-rules', '--json'])
        assert args[args.index('--sandbox') + 1] == 'read-only'
        assert args[args.index('--model') + 1] == 'test-model'
        assert 'forced_login_method="chatgpt"' in args
        assert not list(pathlib.Path.cwd().iterdir())
        assert 'CODEX_THREAD_ID' not in os.environ
        assert 'OPENAI_API_KEY' not in os.environ
        prompt = sys.stdin.read()
        assert 'Explain the supplied sentence.' in prompt
        assert 'SECRET_ANSWER_KEY' not in prompt
        assert 'AUTH_SECRET' not in prompt
        pathlib.Path(args[args.index('--output-last-message') + 1]).write_text('Meaning preserved.', encoding='utf-8')
        print(json.dumps({'type':'thread.started','thread_id':'new-thread'}))
        print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'Meaning preserved.'}}))
        print(json.dumps({'type':'turn.completed','usage':{'input_tokens':20,'cached_input_tokens':5,'output_tokens':7}}))
    """)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("CODEX_THREAD_ID", "existing-thread")
    monkeypatch.setenv("OPENAI_API_KEY", "UNAUTHORIZED_PAID_FALLBACK")
    adapter = importlib.import_module("secure_gateway.evaluation_codex_worker")
    result = adapter.run_codex_worker(request_payload)
    assert result["response"] == "Meaning preserved."
    assert result["model"] == "test-model"
    assert result["usage"] == {"input_tokens": 20, "cached_input_tokens": 5, "output_tokens": 7, "total_tokens": 27}
    assert result["metadata"]["cli_version"] == "codex-cli 9.9.9"
    assert result["metadata"]["model_source"] == "requested_cli_setting"
    assert result["metadata"]["tool_events"] == 0
    assert "no hard filesystem jail" in result["metadata"]["isolation_limits"]


@pytest.mark.parametrize("event", [
    {"type": "item.started", "item": {"type": "command_execution", "command": "ls"}},
    {"type": "item.completed", "item": {"type": "mcp_tool_call"}},
    {"type": "item.completed", "item": {"type": "web_search"}},
    {"type": "item.completed", "item": {"type": "future_tool_kind"}},
    {"type": "turn.failed", "error": {"message": "secret"}},
])
def test_codex_adapter_rejects_tool_use_and_failed_turns(tmp_path, monkeypatch, request_payload, event):
    fake_codex(tmp_path, f"""
        import json, pathlib, sys
        if '--version' in sys.argv:
            print('codex-cli 9.9.9'); sys.exit(0)
        pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1]).write_text('Looks valid.', encoding='utf-8')
        print(json.dumps({event!r}))
        print(json.dumps({{'type':'turn.completed','usage':{{'input_tokens':1,'output_tokens':1}}}}))
    """)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    adapter = importlib.import_module("secure_gateway.evaluation_codex_worker")
    with pytest.raises(ValueError):
        adapter.run_codex_worker(request_payload)


def test_codex_adapter_grades_only_supplied_criteria(tmp_path, monkeypatch, request_payload):
    request_payload.update(role="grade", criteria=[{"id": "c1", "description": "States the relationship."}])
    fake_codex(tmp_path, """
        import json, pathlib, sys
        if '--version' in sys.argv:
            print('codex-cli 9.9.9'); sys.exit(0)
        prompt = sys.stdin.read()
        assert 'States the relationship.' in prompt
        assert '"id": "c1"' in prompt
        final = {'grades':[{'id':'c1','passed':True,'evidence':'The answer states the relationship.'}]}
        pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1]).write_text(json.dumps(final), encoding='utf-8')
        print(json.dumps({'type':'turn.completed','usage':{'input_tokens':3,'output_tokens':12}}))
    """)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    result = importlib.import_module("secure_gateway.evaluation_codex_worker").run_codex_worker(request_payload)
    assert result["grades"] == [{"id": "c1", "passed": True, "evidence": "The answer states the relationship."}]


@pytest.mark.skipif(os.name == "nt", reason="POSIX process-group guarantee")
def test_outer_timeout_kills_nested_codex_inference(tmp_path, monkeypatch, request_payload, workspace):
    marker = tmp_path / "inference-continued"
    fake_codex(tmp_path, f"""
        import pathlib, sys, time
        if '--version' in sys.argv:
            print('codex-cli 9.9.9'); sys.exit(0)
        time.sleep(.8)
        pathlib.Path({str(marker)!r}).touch()
        time.sleep(10)
    """)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    with pytest.raises(ValueError, match="timed out"):
        run_worker([sys.executable, "-m", "secure_gateway.evaluation_codex_worker"],
                   request_payload, workspace, timeout=.3)
    time.sleep(.9)
    assert not marker.exists()
