"""AST guard: every public module-level function/class/method in secure_gateway has a docstring."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "secure_gateway"
EXEMPT_METHODS = {
    "__init__",
    "__repr__",
    "__str__",
    "__eq__",
    "__hash__",
    "__len__",
    "__iter__",
    "__next__",
    "__enter__",
    "__exit__",
    "__getattr__",
    "__getitem__",
    "__setitem__",
    "__delitem__",
    "__contains__",
    "__call__",
    "__bool__",
    "__lt__",
    "__le__",
    "__gt__",
    "__ge__",
    "__ior__",
    "__or__",
    "__ror__",
    "__add__",
    "__radd__",
    "__post_init__",
    "__del__",
}


def _public_defs(tree: ast.AST, *, module: bool = False):
    body = getattr(tree, "body", [])
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield node
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        yield child, node


def _missing(module_path: Path) -> list[str]:
    text = module_path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(module_path))
    rel = module_path.relative_to(ROOT.parent.parent)
    missing: list[str] = []
    for item in _public_defs(tree, module=True):
        owner = None
        if isinstance(item, tuple):
            node, owner = item
        else:
            node = item
        name = node.name
        if owner is None:
            if name.startswith("_"):
                continue
            qual = name
        else:
            if owner.name.startswith("_"):
                continue
            if name.startswith("_") and name not in EXEMPT_METHODS:
                continue
            if name in EXEMPT_METHODS:
                continue
            qual = f"{owner.name}.{name}"
        if ast.get_docstring(node) is None:
            missing.append(f"{rel}:{node.lineno}:{qual}")
    return missing


def test_public_api_has_docstrings() -> None:
    missing: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        missing.extend(_missing(path))
    assert not missing, "Missing public docstrings:\n" + "\n".join(missing)
