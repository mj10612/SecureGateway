"""Evaluation-only stdio arithmetic fixture. Never installs host configuration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Literal

from mcp.server.mcpserver import MCPServer

from secure_gateway.encrypted_session import load_session, save_session, session_file_lock
from secure_gateway.gateway import GatewaySession
from secure_gateway.hooks import _atomic_json
from secure_gateway.private_arithmetic import PrivateArithmetic


def server(fixture: Path) -> MCPServer:
    app = MCPServer(name="synthetic_alias_arithmetic", instructions="Restricted local synthetic alias calculations.")

    @app.tool(name="local_alias_arithmetic", description=(
        "Calculate using exactly two issued opaque aliases. Units and operation permission "
        "are validated locally. Returns only a newly issued result alias; never raw values. "
        "Use date_difference with start then end. Unknown aliases or unsupported units are rejected."
    ))
    def local_alias_arithmetic(
        operation: Literal["add", "subtract", "multiply", "date_difference"], aliases: list[str],
    ) -> dict[str, str]:
        try:
            with session_file_lock(fixture):
                if fixture.is_symlink() or fixture.stat().st_size > 65536:
                    raise ValueError("Invalid owner fixture")
                config = json.loads(fixture.read_text(encoding="utf8"))
                if config["expires_at"] < time.time():
                    raise ValueError("Expired owner fixture")
                owner = load_session(fixture.parent / "session.enc", config["token"], "arithmetic-fixture")
                local = GatewaySession(owner)
                tool = PrivateArithmetic(local, allowed=config["allowed"], result_units=config["result_units"], max_calls=4)
                tool.calls = config["calls"]
                start = time.perf_counter()
                result = tool.call(operation, aliases)
                local_ms = (time.perf_counter() - start) * 1000
                save_session(fixture.parent / "session.enc", owner, config["token"])
                config.update(allowed=tool.allowed, calls=tool.calls)
                config.setdefault("transcript", []).append({"operation": operation, "aliases": aliases,
                                                            "result": result, "local_arithmetic_ms": local_ms})
                _atomic_json(fixture, config)
                return result
        except (OSError, ValueError, KeyError, TypeError):
            return {"error": "Local arithmetic request rejected"}

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    server(args.fixture.resolve()).run(transport="stdio")
