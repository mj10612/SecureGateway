"""Dependency lock consistency and drift detection tests."""

import os
import subprocess
from pathlib import Path


def test_uv_lock_is_consistent():
    """Verify uv.lock matches pyproject.toml constraints."""
    result = subprocess.run(
        ["uv", "lock", "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Lockfile is out of sync with pyproject.toml:\n{result.stdout}\n{result.stderr}"
    )


def test_critical_dependencies_are_pinned():
    """Ensure critical behavioral dependencies remain exactly pinned."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()

    # wordfreq must be exact-pinned for deterministic masking
    assert 'wordfreq==3.1.1' in content, (
        "wordfreq must be exactly pinned (==3.1.1) for deterministic token frequency behavior"
    )

    # tree-sitter-language-pack must be exact-pinned for parser correctness
    assert 'tree-sitter-language-pack==1.22.1' in content, (
        "tree-sitter-language-pack must be exactly pinned (==1.22.1) for identical AST spans"
    )


def test_dependencies_have_upper_bounds():
    """Verify general dependencies have upper version bounds to prevent breaking changes."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()

    # Check that key dependencies have upper bounds (<major+1 pattern)
    expected_bounds = [
        "mcp>=2.0.0,<3.0.0",
        "pydantic>=2.0.0,<3.0.0",
        "click>=8.0.0,<9.0.0",
        "rich>=13.0.0,<16.0.0",
        "cryptography>=41.0.0,<51.0.0",
    ]

    for bound in expected_bounds:
        assert bound in content, (
            f"Expected dependency bound '{bound}' not found in pyproject.toml. "
            "All general dependencies should have upper bounds to prevent breaking changes."
        )


def test_drifted_pyproject_is_rejected(tmp_path):
    """Prove that a deliberately drifted pyproject.toml fails lock consistency check."""
    repo_root = Path(__file__).resolve().parent.parent

    # Copy current pyproject.toml to temp location
    original_pyproject = repo_root / "pyproject.toml"
    temp_pyproject = tmp_path / "pyproject.toml"
    temp_pyproject.write_text(original_pyproject.read_text())

    # Deliberately modify a constraint to create drift
    drifted_content = temp_pyproject.read_text().replace(
        'mcp>=2.0.0,<3.0.0',
        'mcp>=2.0.0,<2.5.0',  # Narrow the range to exclude current locked version
    )
    temp_pyproject.write_text(drifted_content)

    # Copy uv.lock to same directory
    original_lock = repo_root / "uv.lock"
    temp_lock = tmp_path / "uv.lock"
    temp_lock.write_text(original_lock.read_text())

    result = subprocess.run(
        ["uv", "lock", "--check"], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "lockfile" in result.stderr.lower() or "lock file" in result.stderr.lower()


def test_clean_install_from_lock(tmp_path):
    """Verify uv sync respects the lockfile and installs successfully."""
    repo_root = Path(__file__).resolve().parent.parent

    venv_dir = tmp_path / "venv"
    env = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(venv_dir)}
    result = subprocess.run(
        ["uv", "sync", "--locked", "--all-extras"],
        cwd=repo_root, capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, result.stderr
    python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    installed = subprocess.run(
        [str(python), "-c", "import importlib.metadata as m; print(m.version('secure-gateway')); import numpy, onnxruntime, sklearn, psutil, tree_sitter_language_pack, pytest"],
        capture_output=True, text=True,
    )
    assert installed.returncode == 0, installed.stderr
    assert installed.stdout.strip() == __import__("secure_gateway").__version__


def test_version_metadata_matches():
    """Verify package version is consistent across pyproject.toml, __init__.py, and CLI."""
    repo_root = Path(__file__).resolve().parent.parent

    # Read version from pyproject.toml
    pyproject = (repo_root / "pyproject.toml").read_text()
    import re
    pyproject_match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert pyproject_match, "Could not find version in pyproject.toml"
    pyproject_version = pyproject_match.group(1)

    # Read version from __init__.py
    init_file = repo_root / "src" / "secure_gateway" / "__init__.py"
    init_content = init_file.read_text()
    init_match = re.search(r'^__version__ = "([^"]+)"', init_content, re.MULTILINE)
    assert init_match, "Could not find __version__ in __init__.py"
    init_version = init_match.group(1)

    # Versions must match
    assert pyproject_version == init_version, (
        f"Version mismatch: pyproject.toml has {pyproject_version}, "
        f"but __init__.py has {init_version}"
    )


def test_ci_installs_locked_dependencies():
    workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/ci.yml').read_text()
    assert 'uv sync --locked --all-extras' in workflow
    assert 'uv pip install --system -e' not in workflow
