"""Explicit installation of pinned local model data; never called by requests."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import urllib.request

REPOSITORY = "intfloat/multilingual-e5-small"
REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
MODEL_ID = "context-e5-small-v1"
PREFIX = "query: "
# Original upstream bytes, not arbitrary user-supplied executable models.
FILES = {
    "model.onnx": ("onnx/model_qint8_avx512_vnni.onnx", 118346824, "dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88"),
    "tokenizer.json": ("tokenizer.json", 17082730, "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39"),
    "tokenizer_config.json": ("tokenizer_config.json", 443, "a1d6bc8734a6f635dc158508bef000f8e2e5a759c7d92f984b2c86e5ff53425b"),
    "config.json": ("config.json", 655, "69137736cab8b8903a07fe8afaafdda25aac55415a12a55d1bffa9f581abf959"),
}


def default_model_directory() -> Path:
    return Path.home() / ".secure-gateway" / "models" / MODEL_ID


def valid_file(path: Path, size: int, digest: str) -> bool:
    if not path.is_file() or path.is_symlink() or path.stat().st_size != size:
        return False
    hasher = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest() == digest


def verify_model(directory: Path) -> None:
    for name, (_, size, digest) in FILES.items():
        if not valid_file(directory / name, size, digest):
            raise ValueError("Missing or unverified local context model; run gateway model-install.")


def install_model(directory: Path) -> None:
    """Download data only after an explicit CLI invocation, with bounded bytes."""
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    for name, (remote, size, digest) in FILES.items():
        target = directory / name
        if valid_file(target, size, digest):
            continue
        if target.exists() or target.is_symlink():
            raise ValueError("An existing model file differs; choose an empty directory.")
        # Exclusive creation avoids overwriting another install or user data.
        pending = directory / (name + ".download")
        owned = False
        try:
            with pending.open("xb") as output:
                owned = True
                request = urllib.request.Request(
                    f"https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{remote}?download=true",
                    headers={"User-Agent": "SecureGateway-model-install"},
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    total = 0
                    while block := response.read(1024 * 1024):
                        total += len(block)
                        if total > size:
                            raise ValueError("Context model download exceeds its pinned size.")
                        output.write(block)
            if not valid_file(pending, size, digest):
                raise ValueError("Context model checksum verification failed.")
            os.link(pending, target)
            pending.unlink()
        except BaseException:
            # A pre-existing .download belongs to someone else.
            if owned:
                pending.unlink(missing_ok=True)
            raise
    verify_model(directory)


def remove_model(directory: Path) -> None:
    """Remove only unchanged upstream assets; preserve all unrelated files."""
    directory = directory.resolve()
    present = [(directory / name, size, digest) for name, (_, size, digest) in FILES.items()
               if (directory / name).exists()]
    if any(not valid_file(path, size, digest) for path, size, digest in present):
        raise ValueError("A model file was changed; no model files were removed.")
    for path, _, _ in present:
        path.unlink()


def model_metadata() -> dict:
    return {"id": MODEL_ID, "repository": REPOSITORY, "revision": REVISION,
            "download_bytes": sum(item[1] for item in FILES.values()),
            "license": "MIT"}


def head_parameters() -> dict:
    path = Path(__file__).with_name("data") / "context_head.json"
    if path.stat().st_size > 128 * 1024:
        raise ValueError("Context classifier parameters exceed size limit.")
    return json.loads(path.read_text(encoding="utf-8"))
