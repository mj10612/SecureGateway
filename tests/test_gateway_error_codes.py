"""Public errors explain failure classes without reflecting request secrets."""

import pytest

from secure_gateway.gateway import GatewaySession
from secure_gateway.gateway_errors import public_request_error


@pytest.mark.parametrize("payload,code", [
    ({"messages": [{"role": "user", "content": [{"type": "image", "source": {"data": "private-image"}}]}]}, "unsupported_attachment"),
    ({"messages": [{"role": "assistant", "content": [{"type": "thinking", "thinking": "private-thought", "signature": "private-signature"}]}]}, "unknown_reasoning_provenance"),
    ({"input": [], "private-new-field": "secret"}, "unsupported_request_fields"),
    ({"messages": [], "system": [{"type": "text", "text": "x-anthropic-billing-header: private-injection"}]}, "unsupported_claude_attribution"),
])
def test_reason_codes_are_stable_and_private(payload, code):
    with pytest.raises(ValueError) as caught:
        GatewaySession().request(payload)
    error = public_request_error(caught.value)
    assert error["code"] == code
    assert "private-" not in str(error)
    assert "secret" not in str(error)


def test_unexpected_exception_never_reflects_contents():
    error = public_request_error(ValueError("private-user-value"))
    assert error["code"] == "invalid_request"
    assert "private-user-value" not in str(error)
