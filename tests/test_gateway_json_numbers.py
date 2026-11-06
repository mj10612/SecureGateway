import json

import pytest

from secure_gateway.gateway import GatewaySession, strict_json_dumps, strict_json_loads


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_strict_json_loads_rejects_nonfinite_numbers(number):
    with pytest.raises(ValueError):
        strict_json_loads('{"input":{"amount":' + number + "}}")


def test_strict_json_loads_preserves_supported_numbers():
    value = strict_json_loads(
        '{"large_integer":123456789012345678901234567890,"exponent":1.25e200}'
    )

    assert value["large_integer"] == 123456789012345678901234567890
    assert value["exponent"] == 1.25e200


def test_strict_json_dumps_rejects_nested_nonfinite_numbers():
    with pytest.raises(ValueError):
        strict_json_dumps({"tool": {"arguments": [float("nan")]}})


@pytest.mark.parametrize("content_type", ["application/json", "text/event-stream"])
def test_gateway_response_rejects_nonfinite_upstream_numbers(content_type):
    session = object.__new__(GatewaySession)
    session.engine = type(
        "EngineLimits",
        (),
        {"max_restore_input_bytes": 1024, "max_restore_output_bytes": 1024},
    )()

    body = b'{"usage":{"total_tokens":NaN}}'
    if content_type == "text/event-stream":
        body = b'data: {"usage":{"total_tokens":NaN}}\n\n'

    with pytest.raises(ValueError):
        session.response(body, content_type)


def test_gateway_response_emits_standard_json_for_finite_numbers():
    session = object.__new__(GatewaySession)
    session.engine = type(
        "EngineLimits",
        (),
        {"max_restore_input_bytes": 1024, "max_restore_output_bytes": 1024},
    )()
    session.walk = lambda value, restore=False: value

    result = session.response(b'{"value":1.25e200}', "application/json")

    assert json.loads(result) == {"value": 1.25e200}


def argument_events(arguments, dialect):
    fragments = [arguments[:8], arguments[8:]]
    if dialect == 'claude':
        return [{'type': 'content_block_delta', 'index': 0,
                 'delta': {'type': 'input_json_delta', 'partial_json': part}}
                for part in fragments]
    if dialect == 'chat_completions':
        return [{'choices': [{'index': 0, 'delta': {'tool_calls': [
            {'index': 0, 'function': {'arguments': part}}]}}]}
                for part in fragments]
    return [{'type': 'response.function_call_arguments.delta',
             'item_id': 'call', 'delta': part} for part in fragments]


@pytest.mark.parametrize('number', ['NaN', 'Infinity', '-Infinity', '1e400'])
@pytest.mark.parametrize('path', ['request', 'json', 'responses', 'claude', 'chat_completions'])
def test_encoded_tool_arguments_reject_nonfinite_numbers(number, path):
    session = GatewaySession()
    arguments = '{"limit":' + number + '}'
    call = {'type': 'function_call', 'name': 'exec_command',
            'call_id': 'call', 'arguments': arguments}
    with pytest.raises(ValueError):
        if path == 'request':
            session.request({'model': 'gpt-5', 'input': [call]})
        elif path == 'json':
            session.response(json.dumps({'output': [call]}).encode(), 'application/json')
        else:
            body = ''.join('data: ' + json.dumps(event) + '\n\n'
                           for event in argument_events(arguments, path)).encode()
            session.response(body, 'text/event-stream',
                             dialect='chat_completions' if path == 'chat_completions' else None)


@pytest.mark.parametrize('dialect', ['responses', 'claude', 'chat_completions'])
def test_encoded_tool_arguments_preserve_supported_numbers(dialect):
    session = GatewaySession()
    arguments = '{"limit":1.25e200,"count":123456789012345678901234567890}'
    body = ''.join('data: ' + json.dumps(event) + '\n\n'
                   for event in argument_events(arguments, dialect)).encode()
    restored = session.response(body, 'text/event-stream',
                                dialect='chat_completions' if dialect == 'chat_completions' else None)
    events = [json.loads(frame[6:]) for frame in restored.decode().split('\n\n') if frame]
    if dialect == 'claude':
        combined = ''.join(e['delta']['partial_json'] for e in events)
    elif dialect == 'chat_completions':
        combined = ''.join(e['choices'][0]['delta']['tool_calls'][0]['function']['arguments'] for e in events)
    else:
        combined = ''.join(e['delta'] for e in events)
    assert json.loads(combined) == {'limit': 1.25e200, 'count': 123456789012345678901234567890}
