"""Windows text conversion must not invalidate packaged dictionary hashes."""

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize("pin_lf", [False, True])
def test_autocrlf_checkout_preserves_pinned_dictionary_bytes(tmp_path, pin_lf):
    git = shutil.which("git")
    if not git:
        pytest.skip("Git is required for the checkout byte-integrity regression")
    root = Path(__file__).resolve().parents[1]
    source = tmp_path / "source"
    source.mkdir()
    dictionary_path = Path("src/secure_gateway/data/domains")
    shutil.copytree(root / dictionary_path, source / dictionary_path)
    if pin_lf:
        shutil.copyfile(root / ".gitattributes", source / ".gitattributes")

    def run(*args):
        subprocess.run([git, "-C", str(source), *args], check=True,
                       capture_output=True, timeout=30)

    run("init", "--quiet")
    run("config", "core.autocrlf", "true")
    attributes = tmp_path / "empty-attributes"
    attributes.touch()
    run("config", "core.attributesFile", str(attributes))
    run("config", "core.hooksPath", str(tmp_path / "no-hooks"))
    run("config", "commit.gpgsign", "false")
    run("config", "user.name", "Synthetic checkout fixture")
    run("config", "user.email", "fixture@example.invalid")
    run("add", ".")
    run("commit", "--quiet", "-m", "fixture")
    checkout = tmp_path / "checkout"
    subprocess.run([git, "-c", "core.autocrlf=true", "-c", f"core.attributesFile={attributes}",
                    "clone", "--quiet", "--no-local",
                    str(source), str(checkout)], check=True, capture_output=True, timeout=30)
    manifest_path = checkout / dictionary_path / "manifest.json"
    assert (b"\r\n" not in manifest_path.read_bytes()) is pin_lf
    manifest = json.loads(manifest_path.read_bytes())
    valid = []
    for record in manifest["domains"].values():
        data = (checkout / dictionary_path / record["file"]).read_bytes()
        valid.append(sha256(data).hexdigest() == record["sha256"])
        if pin_lf:
            assert b"\r\n" not in data
    assert all(valid) is pin_lf


def test_frozen_evaluation_bytes_survive_git_conversion(tmp_path):
    git = shutil.which("git")
    if not git:
        pytest.skip("Git required")
    source = tmp_path / "source"
    source.mkdir()
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / ".gitattributes", source / ".gitattributes")
    relative = Path("docs/evaluations/accuracy-20261109/frozen/queries.json")
    path = source / relative
    path.parent.mkdir(parents=True)
    captured = b'{\r\n  "synthetic": true\r\n}\r\n'
    path.write_bytes(captured)
    common = [git, "-c", "core.autocrlf=true", "-c", "core.hooksPath=", "-c", "commit.gpgsign=false"]
    for args in (["init", "--quiet", str(source)], ["-C", str(source), "add", "."],
                 ["-C", str(source), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                  "commit", "--quiet", "-m", "fixture"]):
        subprocess.run(common + args, check=True, capture_output=True, timeout=30)
    checkout = tmp_path / "checkout"
    subprocess.run(common + ["clone", "--quiet", "--no-local", str(source), str(checkout)],
                   check=True, capture_output=True, timeout=30)
    assert (checkout / relative).read_bytes() == captured
