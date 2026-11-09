"""Experimental local dispatcher; explicit alias/unit policy, no provider tools."""

from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import re
import time
import secrets

from secure_gateway.models import TokenType


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

    def call(self, operation, aliases):
        if operation not in {"add", "subtract", "multiply", "date_difference"} or not isinstance(aliases, list) or len(aliases) != 2:
            raise ValueError("Unsupported local arithmetic operation")
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
