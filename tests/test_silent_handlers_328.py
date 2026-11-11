"""AST guard for issue #328: every single-pass exception handler must carry an '# intentional:' justification."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "secure_gateway"


def test_single_pass_exception_handlers_have_intentional_marker():
    """Every ExceptHandler whose sole statement is Pass must carry '# intentional:' justification."""
    unjustified: list[str] = []

    for path in sorted(ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source, filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    pass_line = node.body[0].lineno
                    line_same = lines[pass_line - 1] if pass_line <= len(lines) else ""
                    line_prev = lines[pass_line - 2] if pass_line >= 2 else ""
                    if "# intentional:" not in line_same and "# intentional:" not in line_prev:
                        rel = path.relative_to(ROOT.parent.parent)
                        unjustified.append(f"{rel}:{pass_line}")

    assert not unjustified, (
        f"Found {len(unjustified)} unjustified single-pass exception handlers:\n"
        + "\n".join(unjustified)
    )
