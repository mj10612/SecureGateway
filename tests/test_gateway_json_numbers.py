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
