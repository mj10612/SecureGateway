"""Experimental local dispatcher; explicit alias/unit policy, no provider tools."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import json
import re
import secrets
import time
from typing import Any

from secure_gateway.models import TokenType

LOCAL_ARITHMETIC_TOOL_NAME = "local_alias_arithmetic"

# Accepted operand spellings (#375): an alias exactly as the model sees it in
# masked text. Forced/partial-word aliases are displayed wrapped in U+27E6/U+27E7
# (``⟦private_symbol_N⟧``, see ``GatewaySession._forced_alias``); the wrapped
# and bare spellings name the same alias. Nothing else is normalized.
ALIASES_DESCRIPTION = (
    "Exactly two issued private aliases as operands, copied exactly as they appear in the conversation. "
    "An alias displayed between ⟦ and ⟧ may be passed with those brackets (⟦alias⟧) "
    "or without them (alias); both name the same alias. Any other spelling, partial alias or extra text is rejected."
)
_DISPLAYED_ALIAS = re.compile(r"⟦(private_symbol_[0-9]+)⟧")


def canonical_alias(alias: Any) -> Any:
    """Return the issued alias named by a displayed operand spelling.

    ``⟦private_symbol_N⟧`` (the exact form the gateway emits) becomes
    ``private_symbol_N``; any other value is returned unchanged so the normal
    authorization and session checks accept or reject it.
    """
    if isinstance(alias, str):
        match = _DISPLAYED_ALIAS.fullmatch(alias)
        if match:
            return match[1]
    return alias

LOCAL_ARITHMETIC_TOOL_OPENAI = {
    "type": "function",
    "function": {
        "name": LOCAL_ARITHMETIC_TOOL_NAME,
        "description": "Perform restricted local arithmetic or date difference on issued private aliases without disclosing originals.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "date_difference"],
                    "description": "Arithmetic or date operation to perform locally."
                },
                "aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": ALIASES_DESCRIPTION
                }
            },
            "required": ["operation", "aliases"]
        }
    }
}

LOCAL_ARITHMETIC_TOOL_CLAUDE = {
    "name": LOCAL_ARITHMETIC_TOOL_NAME,
    "description": "Perform restricted local arithmetic or date difference on issued private aliases without disclosing originals.",
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "date_difference"],
                "description": "Arithmetic or date operation to perform locally."
            },
            "aliases": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 2,
                "description": ALIASES_DESCRIPTION
            }
        },
        "required": ["operation", "aliases"]
    }
}


def get_arithmetic_tool_spec(dialect: str | None = None) -> dict[str, Any]:
    """Return tool specification matching requested API dialect."""
    if dialect in {"claude", "anthropic"}:
        return deepcopy(LOCAL_ARITHMETIC_TOOL_CLAUDE)
    return deepcopy(LOCAL_ARITHMETIC_TOOL_OPENAI)


def inject_arithmetic_tool(payload: dict[str, Any], dialect: str | None = None) -> tuple[dict[str, Any], bool]:
    """Inject local arithmetic tool into request payload if not already present.

    Validates that user tools do not collide with the local arithmetic tool name.
    """
    result = deepcopy(payload)
    spec = get_arithmetic_tool_spec(dialect)
    tools = result.setdefault("tools", [])
    if not isinstance(tools, list):
        raise ValueError("Payload tools must be a list")

    for tool in tools:
        if isinstance(tool, dict):
            name = tool.get("name") or (
                tool.get("function", {}).get("name")
                if isinstance(tool.get("function"), dict)
                else None
            )
            if name == LOCAL_ARITHMETIC_TOOL_NAME:
                raise ValueError("User tool name collides with local arithmetic tool.")

    tools.append(spec)
    return result, True


def intercept_response_tool_calls(
    payload: dict[str, Any],
    tool_instance: PrivateArithmetic,
    dialect: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Intercept and execute local arithmetic tool calls, removing them from host view.

    Returns (transformed_payload, executed_calls).
    """
    result = deepcopy(payload)
    executed: list[dict[str, Any]] = []

    # Chat Completions / OpenAI format
    if "choices" in result and isinstance(result["choices"], list):
        for choice in result["choices"]:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if not isinstance(message, dict):
                continue
            tool_calls = message.get("tool_calls")
            if not isinstance(tool_calls, list):
                continue
            remaining_calls: list[dict[str, Any]] = []
            for call in tool_calls:
                if not isinstance(call, dict):
                    remaining_calls.append(call)
                    continue
                func = call.get("function", {})
                if isinstance(func, dict) and func.get("name") == LOCAL_ARITHMETIC_TOOL_NAME:
                    raw_args = func.get("arguments", "{}")
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        op = args.get("operation")
                        alias_list = args.get("aliases")
                        res = tool_instance.call(op, alias_list)
                        executed.append({"call_id": call.get("id"), "operation": op, "aliases": alias_list, "result": res})
                        # If content was empty, populate with result alias
                        if not message.get("content"):
                            message["content"] = res["alias"]
                    except (ValueError, KeyError, TypeError) as exc:
                        raise ValueError("Local arithmetic execution failed") from exc
                else:
                    remaining_calls.append(call)

            if remaining_calls:
                message["tool_calls"] = remaining_calls
            else:
                message.pop("tool_calls", None)

    # Claude format
    if "content" in result and isinstance(result["content"], list):
        remaining_blocks: list[dict[str, Any]] = []
        for block in result["content"]:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == LOCAL_ARITHMETIC_TOOL_NAME:
                raw_input = block.get("input", {})
                try:
                    op = raw_input.get("operation")
                    alias_list = raw_input.get("aliases")
                    res = tool_instance.call(op, alias_list)
                    executed.append({"call_id": block.get("id"), "operation": op, "aliases": alias_list, "result": res})
                    remaining_blocks.append({"type": "text", "text": res["alias"]})
                except (ValueError, KeyError, TypeError) as exc:
                    raise ValueError("Local arithmetic execution failed") from exc
            else:
                remaining_blocks.append(block)
        result["content"] = remaining_blocks

    return result, executed


class LocalArithmeticDispatcher:
    """Local dispatcher intercepting local arithmetic tool calls in gateway session."""

    def __init__(self, session, *, allowed=None, result_units=None, max_calls=16):
        self.session = session
        self.tool = PrivateArithmetic(session, allowed=allowed or {}, result_units=result_units, max_calls=max_calls)
        self.executed_calls: list[dict[str, Any]] = []

    def inject_tool(self, payload: dict[str, Any], dialect: str | None = None) -> tuple[dict[str, Any], bool]:
        """Inject local arithmetic tool specification into upstream request payload."""
        return inject_arithmetic_tool(payload, dialect=dialect)

    def intercept_payload(self, payload: dict[str, Any], dialect: str | None = None) -> dict[str, Any]:
        """Intercept and execute local arithmetic tool calls from response payload, returning sanitized payload."""
        transformed, executed = intercept_response_tool_calls(payload, self.tool, dialect=dialect)
        self.executed_calls.extend(executed)
        return transformed


class PrivateArithmetic:
    """A trusted host owns this object. Only operation and aliases cross its API.

    This is not enabled by gateway installation. A host must opt in, provide the
    session and explicit unit policy, and return only the result alias to a model.
    Comparisons, division, arbitrary expressions, file/network access are absent.
    """

    def __init__(self, session, *, allowed, result_units=None, max_calls=16):
        if not isinstance(allowed, dict) or len(allowed) > 256 or type(max_calls) is not int or not 1 <= max_calls <= 100:
            raise ValueError("Invalid local arithmetic policy")
        if any(not isinstance(key, str) or value not in {"USD", "EUR", "KRW", "count", "date", "days"} for key, value in allowed.items()):
            raise ValueError("Invalid alias unit policy")
        self.session, self.allowed = session, dict(allowed)
        self.result_units = dict(result_units or {})
        self.max_calls, self.calls = max_calls, 0
        self._owner = secrets.token_hex(16)

    def call(self, operation: str, aliases: list[str]) -> dict[str, str]:
        """Compute an allowed operation over two authorized aliases.

        Args:
            operation: One of ``add``, ``subtract``, ``multiply``, or
                ``date_difference``.
            aliases: Exactly two session aliases authorized by the unit policy,
                each bare (``private_symbol_N``) or exactly as displayed in
                masked text (``⟦private_symbol_N⟧``).

        Returns:
            ``{"alias": <result_alias>}`` containing a new session-local alias
            for the computed result. Never returns ``None``.

        Raises:
            ValueError: For unsupported operations, unauthorized aliases, policy
                violations, budget limits, or invalid operand formats.
        """
        if operation not in {"add", "subtract", "multiply", "date_difference"} or not isinstance(aliases, list) or len(aliases) != 2:
            raise ValueError("Unsupported local arithmetic operation")
        aliases = [canonical_alias(alias) for alias in aliases]
        if any(not isinstance(alias, str) or alias not in self.allowed for alias in aliases):
            raise ValueError("Unknown or unauthorized arithmetic alias")
        with self.session.lock:
            if self.session.session.is_expired():
                raise ValueError("Local arithmetic session expired")
            if self.calls >= self.max_calls:
                raise ValueError("Local arithmetic call budget exceeded")
            self.calls += 1
            started = time.perf_counter()
            values = []
            units = [self.allowed[alias] for alias in aliases]
            for alias in aliases:
                mapping = self.session.session.reverse_store.get(alias)
                if mapping is None:
                    raise ValueError("Arithmetic alias is absent from this session")
                values.append(mapping.original)
            if operation == "date_difference":
                if units != ["date", "date"] or self.result_units.get(operation) != "days" or any(not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) for value in values):
                    raise ValueError("Explicit ISO date and day policy required")
                try:
                    result = str((date.fromisoformat(values[1]) - date.fromisoformat(values[0])).days)
                except ValueError:
                    raise ValueError("Invalid ISO date") from None
                result_unit = "days"
            else:
                if any(not re.fullmatch(r"-?(?:0|[1-9]\d{0,31})(?:\.\d{1,16})?", value) for value in values):
                    raise ValueError("Unsupported bounded decimal format")
                if operation in {"add", "subtract"}:
                    if units[0] != units[1] or units[0] == "date":
                        raise ValueError("Arithmetic units do not match")
                    result_unit = units[0]
                else:
                    if "count" not in units or self.result_units.get(operation) != units[1 - units.index("count")]:
                        raise ValueError("Explicit multiplication result unit required")
                    result_unit = self.result_units[operation]
                try:
                    with localcontext() as context:
                        context.prec = 100
                        left, right = map(Decimal, values)
                        if any(len(number.as_tuple().digits) > 18 or abs(number) > Decimal("1e12") for number in (left, right)):
                            raise ValueError("Arithmetic operand budget exceeded")
                        value = left + right if operation == "add" else left - right if operation == "subtract" else left * right
                        if not value.is_finite() or len(value.as_tuple().digits) > 28:
                            raise ValueError("Arithmetic result budget exceeded")
                        result = format(value, "f")
                except InvalidOperation:
                    raise ValueError("Invalid decimal arithmetic") from None
            if time.perf_counter() - started > .1:
                raise ValueError("Local arithmetic time budget exceeded")
            alias = self.session.engine._get_or_create_surrogate(
                result, TokenType.LITERAL, self.session.session.generator,
                self.session.session.forward_store, self.session.session.reverse_store,
                lookup_key=f"local-arithmetic:{self._owner}:{self.calls}")
            self.allowed[alias] = result_unit
            return {"alias": alias}


def main():
    """Explicit experimental local host fixture, never installed as a tool.

    The local owner creates the private encrypted session/config. Child agents
    receive only its dispatcher path and aliases. Same-user shell access is not
    a hard sandbox; the evaluation report must disclose that limitation.
    """
    import argparse
    import json
    from pathlib import Path
    from secure_gateway.encrypted_session import load_session, save_session, session_file_lock
    from secure_gateway.gateway import GatewaySession
    from secure_gateway.hooks import _atomic_json
    parser = argparse.ArgumentParser(description="Restricted local synthetic alias arithmetic dispatcher")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("operation", choices=["add", "subtract", "multiply", "date_difference"])
    parser.add_argument("aliases", nargs=2)
    args = parser.parse_args()
    try:
        with session_file_lock(args.fixture):
            if args.fixture.is_symlink() or args.fixture.stat().st_size > 65536:
                raise ValueError("Invalid fixture")
            config = json.loads(args.fixture.read_text(encoding="utf8"))
            session_path = args.fixture.parent / "session.enc"
            owner = load_session(session_path, config["token"], "arithmetic-fixture")
            session = GatewaySession(owner)
            tool = PrivateArithmetic(session, allowed=config["allowed"], result_units=config.get("result_units"), max_calls=config["max_calls"])
            tool.calls = config["calls"]
            result = tool.call(args.operation, args.aliases)
            save_session(session_path, owner, config["token"])
            config.update(allowed=tool.allowed, calls=tool.calls)
            config.setdefault("transcript", []).append({"operation": args.operation, "aliases": args.aliases, "result": result})
            _atomic_json(args.fixture, config)
            print(json.dumps(result))
    except (OSError, ValueError, KeyError, TypeError):
        print('{"error":"Local arithmetic request rejected"}')
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
