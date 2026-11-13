import json
import sys
import textwrap

import pytest

from secure_gateway import evaluation_batch as batch
from secure_gateway.evaluation_worker import validate_request


def interpret_request(text="Explain the supplied sentence."):
    return {
        "role": "interpret", "job_id": "job-1", "model": "test-model", "max_output_tokens": 64,
        "messages": [{"role": "system", "content": "Be brief."}, {"role": "user", "content": text}],
    }


def fake_codex(tmp_path, monkeypatch, source):
    path = tmp_path / "codex"
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    capture = batch.capture_worker_process

    def fixture_capture(command, *args, **kwargs):
        assert command[0] == str(path), "test attempted to launch a non-fixture CLI"
        return capture([sys.executable, str(path), *command[1:]], *args, **kwargs)

    monkeypatch.setattr(batch.shutil, "which", lambda name: str(path) if name == "codex" else None)
    monkeypatch.setattr(batch, "capture_worker_process", fixture_capture)
    return path


CLI_HEADER = """
    import json, os, pathlib, sys
    if '--version' in sys.argv:
        print('codex-cli 9.9.9')
        sys.exit(0)
    args = sys.argv[1:]
    prompt = sys.stdin.read()
    out = pathlib.Path(args[args.index('--output-last-message') + 1])
"""


def test_lean_worker_overrides_only_its_own_argv(tmp_path, monkeypatch):
    home = tmp_path / "codex-home"
    home.mkdir()
    config = home / "config.toml"
    config.write_text('model = "user-choice"\n', encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setenv("OPENAI_API_KEY", "UNAUTHORIZED_PAID_FALLBACK")
    fake_codex(tmp_path, monkeypatch, CLI_HEADER + """
    assert args[0] == 'exec'
    for flag in ['--ephemeral', '--skip-git-repo-check', '--ignore-user-config', '--ignore-rules', '--json']:
        assert flag in args
    assert args[args.index('--sandbox') + 1] == 'read-only'
    assert 'forced_login_method="chatgpt"' in args
    disabled = [args[i + 1] for i, a in enumerate(args) if a == '--disable']
    assert 'shell_tool' in disabled and 'code_mode_host' in disabled
    setting = next(a for a in args if a.startswith('model_instructions_file='))
    instructions = pathlib.Path(json.loads(setting.split('=', 1)[1]))
    assert instructions.read_text(encoding='utf-8').startswith('You are a careful assistant.')
    assert instructions.parent != pathlib.Path.cwd()
    assert not list(pathlib.Path.cwd().iterdir())
    assert 'OPENAI_API_KEY' not in os.environ
    assert os.environ['CODEX_HOME'].endswith('codex-home')
    assert 'Return only your answer to the supplied task as plain text.' in prompt
    out.write_text('Meaning preserved.', encoding='utf-8')
    print(json.dumps({'type': 'thread.started', 'thread_id': 't'}))
    print(json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'x'}}))
    print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 20, 'output_tokens': 7}}))
    """)
    result = batch.run_lean_worker(interpret_request())
    assert result["response"] == "Meaning preserved."
    assert result["usage"]["total_tokens"] == 27
    meta = result["metadata"]
    assert meta["adapter"] == "lean-batch" and meta["tool_events"] == 0
    assert meta["adapter_source_sha256"] == batch.adapter_hash()
    assert meta["task_response_mode"] == "answer_visible_task"
    # The user's own Codex configuration is never touched.
    assert config.read_text(encoding="utf-8") == 'model = "user-choice"\n'
    assert sorted(p.name for p in home.iterdir()) == ["config.toml"]


@pytest.mark.parametrize("message", [
    "You've hit your usage limit. Try again later.",
    "Your workspace is out of credits. Add credits to continue.",
])
def test_usage_limit_is_a_distinct_error(tmp_path, monkeypatch, message):
    # The real CLI exits 1 after a limit; the stream must still be classified.
    fake_codex(tmp_path, monkeypatch, CLI_HEADER + f"""
    print(json.dumps({{'type': 'error', 'message': {message!r}}}))
    print(json.dumps({{'type': 'turn.failed', 'error': {{'message': {message!r}}}}}))
    sys.exit(1)
    """)
    with pytest.raises(batch.UsageLimitReached) as caught:
        batch.run_lean_worker(interpret_request())
    assert str(caught.value) == batch.USAGE_LIMIT_ERROR
    assert "credits" not in str(caught.value)


def test_nonzero_exit_without_limit_fails_closed(tmp_path, monkeypatch):
    fake_codex(tmp_path, monkeypatch, CLI_HEADER + """
    out.write_text('looks fine', encoding='utf-8')
    print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 1, 'output_tokens': 1}}))
    sys.exit(2)
    """)
    with pytest.raises(ValueError) as caught:
        batch.run_lean_worker(interpret_request())
    assert str(caught.value) == "Worker executable failed."
    assert not isinstance(caught.value, batch.UsageLimitReached)


def test_other_failures_and_warning_items_fail_closed():
    with pytest.raises(ValueError) as caught:
        batch.parse_events(b'{"type":"turn.failed","error":{"message":"server exploded"}}\n')
    assert not isinstance(caught.value, batch.UsageLimitReached)
    warning = json.dumps({"type": "item.completed", "item": {"type": "error", "message": "w"}})
    with pytest.raises(ValueError, match="tool"):
        batch.parse_events((warning + "\n").encode())
    with pytest.raises(ValueError, match="complete"):
        batch.parse_events(b'{"type":"thread.started"}\n')


def events(*lines):
    return ("\n".join(json.dumps(line) for line in lines) + "\n").encode()


THREAD = {"type": "thread.started", "thread_id": "t"}
TURN = {"type": "turn.started"}
MESSAGE = {"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": "x"}}
DONE = {"type": "turn.completed", "usage": {"input_tokens": 3, "output_tokens": 1}}


def code_mode_warning(message=batch.CODE_MODE_HOST_DISABLED_WARNING, **extra):
    return {"type": "item.completed", "item": {"id": "item_0", "type": "error", "message": message, **extra}}


def test_only_the_exact_code_mode_host_warning_is_accepted_once_before_the_turn():
    # Shape recorded from codex-cli 0.167.2 with --disable code_mode_host (issue #372).
    assert batch.parse_events(events(THREAD, code_mode_warning(), TURN, MESSAGE, DONE))["total_tokens"] == 4
    for stream in [
        events(THREAD, TURN, code_mode_warning(), MESSAGE, DONE),  # inside the turn
        events(THREAD, code_mode_warning(), code_mode_warning(), TURN, MESSAGE, DONE),  # repeated
        events(THREAD, code_mode_warning(batch.CODE_MODE_HOST_DISABLED_WARNING + " "), TURN, DONE),
        events(THREAD, code_mode_warning("Code Mode is unavailable."), TURN, DONE),
        events(THREAD, code_mode_warning(extra="x"), TURN, DONE),
        events(THREAD, {"type": "item.started", "item": code_mode_warning()["item"]}, TURN, DONE),
    ]:
        with pytest.raises(ValueError, match="tool"):
            batch.parse_events(stream)


def test_tool_router_log_fails_closed_even_with_clean_events(tmp_path, monkeypatch):
    # codex-cli 0.167.2 emits no event for a rejected exec/apply_patch/unsupported call,
    # only this stderr line (offline probe, issue #372).
    fake_codex(tmp_path, monkeypatch, CLI_HEADER + f"""
    out.write_text('looks fine', encoding='utf-8')
    for line in {[THREAD, code_mode_warning(), TURN, MESSAGE, DONE]!r}:
        print(json.dumps(line))
    sys.stderr.write('2026-11-12T22:50:38.300015Z ERROR codex_core::tools::router: '
                     'error=code-mode host is disabled\\n')
    """)
    with pytest.raises(ValueError) as caught:
        batch.run_lean_worker(interpret_request())
    assert str(caught.value) == "Codex used a tool during a semantic task."


def test_code_mode_warning_alone_is_accepted_and_recorded(tmp_path, monkeypatch):
    fake_codex(tmp_path, monkeypatch, CLI_HEADER + f"""
    out.write_text('Meaning preserved.', encoding='utf-8')
    for line in {[THREAD, code_mode_warning(), TURN, MESSAGE, DONE]!r}:
        print(json.dumps(line))
    sys.stderr.write('WARNING: proceeding, even though we could not create PATH aliases\\n')
    """)
    result = batch.run_lean_worker(interpret_request())
    assert result["response"] == "Meaning preserved."
    assert "code_mode_host" in result["metadata"]["disabled_features"]
    assert "cli tool-router log" in result["metadata"]["tool_call_checks"]


def items(count):
    return [{"key": f"case-{i}::C", "instructions": f"rules {i}", "input": f"task {i}"} for i in range(count)]


def test_interpret_batch_is_shuffled_opaque_and_round_trips():
    request, labels = batch.build_interpret_batch(
        items(6), job_id="b1", model="m", max_output_tokens_per_item=100, seed=7,
        reasoning_effort="low")
    validate_request(request)
    assert request["max_output_tokens"] == 664 and request["reasoning_effort"] == "low"
    payload = json.loads(request["messages"][1]["content"])
    assert [t["task"] for t in payload["tasks"]] == [f"T{i}" for i in range(1, 7)]
    assert [labels[t["task"]] for t in payload["tasks"]] != [i["key"] for i in items(6)]
    assert "case-" not in request["messages"][1]["content"]
    again, again_labels = batch.build_interpret_batch(
        items(6), job_id="b1", model="m", max_output_tokens_per_item=100, seed=7, reasoning_effort="low")
    assert again == request and again_labels == labels
    answer = json.dumps({"answers": [{"task": t, "answer": "ok " + t} for t in reversed(list(labels))]})
    split = batch.parse_interpret_batch(answer, labels, max_output_tokens_per_item=100)
    assert set(split) == {i["key"] for i in items(6)}
    task_by_key = {key: label for label, key in labels.items()}
    assert all(split[key] == "ok " + task_by_key[key] for key in split)


@pytest.mark.parametrize("answers", [
    [{"task": "T1", "answer": "a"}],
    [{"task": "T1", "answer": "a"}, {"task": "T1", "answer": "b"}],
    [{"task": "T1", "answer": "a"}, {"task": "T9", "answer": "b"}],
    [{"task": "T1", "answer": "a"}, {"task": "T2", "answer": " "}],
    [{"task": "T1", "answer": "a"}, {"task": "T2", "answer": "x" * 41}],
    [{"task": "T1", "answer": "a", "extra": 1}, {"task": "T2", "answer": "b"}],
])
def test_interpret_batch_rejects_incomplete_or_malformed_answers(answers):
    labels = {"T1": "a", "T2": "b"}
    with pytest.raises(ValueError):
        batch.parse_interpret_batch(json.dumps({"answers": answers}), labels, max_output_tokens_per_item=10)
    with pytest.raises(ValueError):
        batch.parse_interpret_batch("not json", labels, max_output_tokens_per_item=10)


def test_interpret_batch_rejects_bad_items():
    with pytest.raises(ValueError):
        batch.build_interpret_batch([], job_id="b", model="m", max_output_tokens_per_item=1, seed=1)
    with pytest.raises(ValueError):
        batch.build_interpret_batch(items(2) + items(1), job_id="b", model="m",
                                    max_output_tokens_per_item=1, seed=1)
    with pytest.raises(ValueError):
        batch.build_interpret_batch(items(batch.MAX_BATCH_ITEMS + 1), job_id="b", model="m",
                                    max_output_tokens_per_item=1, seed=1)


def grade_request(case, rules="Grade blind.", model="m"):
    return {
        "role": "grade", "job_id": "g-" + case, "model": model, "max_output_tokens": 100,
        "reasoning_effort": "low",
        "messages": [{"role": "system", "content": rules},
                     {"role": "user", "content": json.dumps({"original": case})}],
        "criteria": [{"id": "R1::intent", "description": "intent kept"},
                     {"id": "R2::intent", "description": "intent kept"}],
    }


def test_grade_batch_prefixes_criteria_and_splits_back():
    cases = {c: grade_request(c) for c in ("alpha", "beta", "gamma")}
    request, labels = batch.build_grade_batch(cases, job_id="gb", seed=3)
    validate_request(request)
    assert request["max_output_tokens"] == 300 and len(request["criteria"]) == 6
    assert {c["id"].split("::")[0] for c in request["criteria"]} == {"K1", "K2", "K3"}
    assert "alpha" not in request["messages"][0]["content"]
    grades = [{"id": c["id"], "passed": True, "evidence": "q"} for c in request["criteria"]]
    split = batch.split_grade_batch(grades, labels)
    assert set(split) == set(cases)
    assert all(sorted(g["id"] for g in split[c]) == ["R1::intent", "R2::intent"] for c in cases)
    with pytest.raises(ValueError):
        batch.split_grade_batch([{"id": "K9::R1::intent", "passed": True, "evidence": "q"}], labels)


def test_grade_batch_requires_shared_rules_and_model():
    with pytest.raises(ValueError):
        batch.build_grade_batch({"a": grade_request("a"), "b": grade_request("b", rules="Other")},
                                job_id="g", seed=1)
    with pytest.raises(ValueError):
        batch.build_grade_batch({"a": grade_request("a"), "b": grade_request("b", model="x")},
                                job_id="g", seed=1)


def test_budget_and_agreement():
    single = batch.estimate_budget(
        interpret_jobs=264, grade_cases=88, interpret_batch=1, grade_batch=1,
        fixed_input_tokens=15100, interpret_content_tokens=400, grade_content_tokens=2500,
        regrade_rate=0)
    lean = batch.estimate_budget(
        interpret_jobs=264, grade_cases=88, interpret_batch=8, grade_batch=4,
        fixed_input_tokens=7070, interpret_content_tokens=400, grade_content_tokens=2500,
        regrade_rate=0)
    assert single["total_calls"] == 352 and lean["total_calls"] == 55
    assert lean["raw_tokens"] < 0.3 * single["raw_tokens"]
    result = batch.agreement({("a", "C"): True, ("a", "D"): False}, {("a", "C"): True, ("a", "D"): True})
    assert result["rate"] == 0.5 and result["candidate_only"] == 1 and result["reference_only"] == 0
    with pytest.raises(ValueError):
        batch.agreement({"a": True}, {"b": True})
    with pytest.raises(ValueError):
        batch.estimate_budget(interpret_jobs=1, grade_cases=1, interpret_batch=0, grade_batch=1,
                              fixed_input_tokens=1, interpret_content_tokens=1, grade_content_tokens=1)
