"""AST guard for issue #337: every assert statement in src/secure_gateway must carry an '# invariant:' comment."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "secure_gateway"


def test_assert_statements_have_invariant_marker():
    """Every Assert node in src/secure_gateway must carry an '# invariant:' comment."""
    unclassified: list[str] = []

    for path in sorted(ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source, filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                start = node.lineno
                end = getattr(node, "end_lineno", node.lineno)
                # Check preceding line or any line within the assert node span
                span_lines = [lines[i] for i in range(max(0, start - 2), min(len(lines), end))]
                if not any("# invariant:" in line for line in span_lines):
                    rel = path.relative_to(ROOT.parent.parent)
                    unclassified.append(f"{rel}:{start}")

    assert not unclassified, (
        f"Found {len(unclassified)} unclassified assert statements in src/:\n"
        + "\n".join(unclassified)
    )
