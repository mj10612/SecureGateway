"""Stable public diagnostics; exception values and request contents stay private."""


class GatewayRequestError(ValueError):
    """A gateway request error with a stable public diagnostic code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(GUIDANCE[code])


GUIDANCE = {
    "unsupported_attachment": "Images and binary/remote attachments are not supported; send text without attachments.",
    "unknown_reasoning_provenance": "Start a new conversation after enabling this gateway; existing signed reasoning cannot be safely replayed.",
    "unsupported_request_fields": "The client sent unsupported request fields; update the gateway or use a supported client version.",
    "unsupported_claude_attribution": "The Claude client attribution format is unsupported; use a supported client version.",
    "invalid_request": "The request failed privacy validation; inspect supported request formats without sharing private payloads.",
    "conversation_capacity": "All conversation slots are busy, or persistent session storage is unavailable; retry after active requests finish or reset idle sessions.",
}

_REASONS = {
    "Unrecognized signed/encrypted reasoning; start a new conversation.": "unknown_reasoning_provenance",
    "Binary/remote attachments are unsupported by the privacy gateway.": "unsupported_attachment",
    "Unsupported request fields; request was not forwarded.": "unsupported_request_fields",
    "Unrecognized Claude attribution; request was not forwarded.": "unsupported_claude_attribution",
    "Claude attribution must be a separate first system block.": "unsupported_claude_attribution",
    "Unrecognized attribution cache control.": "unsupported_claude_attribution",
}


def public_request_error(exc: BaseException) -> dict[str, str]:
    """Map an internal exception to a fixed public error payload.

    Returns a JSON-serializable dict with stable ``error``/``code``/``guidance``
    fields. Internal exception text is not exposed except through known reason
    mappings. Never returns ``None``.
    """
    code = exc.code if isinstance(exc, GatewayRequestError) else _REASONS.get(str(exc), "invalid_request")
    return {"error": "Privacy gateway could not safely process this request; nothing bypassed masking",
            "code": code, "guidance": GUIDANCE[code]}
