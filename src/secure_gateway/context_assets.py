"""Explicit installation of pinned local model data; never called by requests."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import urllib.request

from secure_gateway.encrypted_session import session_file_lock
from secure_gateway.hooks import _atomic_json

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
_DOWNLOAD_RECORD = ".secure-gateway-download.json"


def _download_identity(path: Path) -> list[int]:
    """Return the device/inode identity of a download-owned path.

    Args:
        path: Expected temporary download file path.

    Returns:
        A two-integer list ``[st_dev, st_ino]`` suitable for JSON records and
        equality checks. Never returns ``None``.

    Raises:
        ValueError: If ``path`` is a symlink or not a regular file, preventing
            operations on a path whose identity is not the expected owned file.
    """
    stat = path.lstat()
    if path.is_symlink() or not path.is_file():
        raise ValueError("Download path changed; no temporary files were removed.")
    return [stat.st_dev, stat.st_ino]


def _recover_download(directory: Path) -> None:
    """Only a recorded inode may be removed after its owner's lock is released."""
    record = directory / _DOWNLOAD_RECORD
    if not record.exists() and not record.is_symlink():
        return
    try:
        if record.is_symlink() or not record.is_file() or record.stat().st_size > 4096:
            raise ValueError()
        value = json.loads(record.read_bytes())
        if (not isinstance(value, dict) or value.get("version") != 1
                or value.get("asset") not in FILES
                or not isinstance(value.get("identity"), list)
                or len(value["identity"]) != 2
                or any(type(item) is not int for item in value["identity"])):
            raise ValueError()
        pending = directory / (value["asset"] + ".download")
        if pending.exists() or pending.is_symlink():
            if _download_identity(pending) != value["identity"]:
                raise ValueError()
            pending.unlink()
        record.unlink()
    except (ValueError, TypeError, KeyError):
        raise ValueError(
            "Download ownership record is invalid or its temporary file changed; "
            "stop all model installers, inspect/move the .download file and "
            ".secure-gateway-download.json aside, then retry. No unverified files were removed."
        ) from None


def _check_unowned_downloads(directory: Path) -> None:
    for name in FILES:
        pending = directory / (name + ".download")
        if pending.exists() or pending.is_symlink():
            raise FileExistsError(
                "Unowned .download file remains; no files were removed. Stop all model "
                f"installers, inspect/move '{pending}' aside, then retry model-install or model-remove."
            )


def default_model_directory() -> Path:
    """Return the default per-user directory for the pinned context model.

    The path is under ``~/.secure-gateway/models/<MODEL_ID>``; never ``None``.
    """
    return Path.home() / ".secure-gateway" / "models" / MODEL_ID


def valid_file(path: Path, size: int, digest: str) -> bool:
    """Check that a regular file matches the expected size and SHA-256 digest.

    Returns ``True`` only for a non-symlink regular file whose bytes hash to
    ``digest``; otherwise returns ``False`` (never ``None``).
    """
    if not path.is_file() or path.is_symlink() or path.stat().st_size != size:
        return False
    hasher = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest() == digest


def verify_model(directory: Path) -> None:
    """Verify all pinned model assets in ``directory``.

    Returns ``None`` when every required asset is present and verified.

    Raises:
        ValueError: If any required asset is missing or fails verification.
    """
    for name, (_, size, digest) in FILES.items():
        if not valid_file(directory / name, size, digest):
            raise ValueError("Missing or unverified local context model; run gateway model-install.")


def install_model(directory: Path) -> None:
    """Download data only after an explicit CLI invocation, with bounded bytes."""
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    # Keep the persistent lock next to the model directory. Never unlink it:
    # different lock inodes would allow two installers to run concurrently.
    with session_file_lock(directory.with_name(directory.name + ".model-install")):
        _recover_download(directory)
        _check_unowned_downloads(directory)
        _install_model(directory)


def _install_model(directory: Path) -> None:
    for name, (remote, size, digest) in FILES.items():
        target = directory / name
        if valid_file(target, size, digest):
            continue
        if target.exists() or target.is_symlink():
            raise ValueError("An existing model file differs; choose an empty directory.")
        # Exclusive creation avoids overwriting another install or user data.
        pending = directory / (name + ".download")
        owned = False
        identity = None
        try:
            with pending.open("xb") as output:
                owned = True
                identity = _download_identity(pending)
                _atomic_json(directory / _DOWNLOAD_RECORD, {
                    "version": 1, "asset": name, "identity": identity,
                })
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
            (directory / _DOWNLOAD_RECORD).unlink()
        except BaseException:
            # A pre-existing .download belongs to someone else.
            if owned:
                if pending.exists() and _download_identity(pending) == identity:
                    pending.unlink()
                if not pending.exists():
                    (directory / _DOWNLOAD_RECORD).unlink(missing_ok=True)
            raise
    verify_model(directory)


def remove_model(directory: Path) -> None:
    """Remove only unchanged upstream assets; preserve all unrelated files."""
    directory = directory.resolve()
    if not directory.exists():
        return
    with session_file_lock(directory.with_name(directory.name + ".model-install")):
        _remove_model(directory)


def _remove_model(directory: Path) -> None:
    present = [(directory / name, size, digest) for name, (_, size, digest) in FILES.items()
               if (directory / name).exists() or (directory / name).is_symlink()]
    if any(not valid_file(path, size, digest) for path, size, digest in present):
        raise ValueError("A model file was changed; no model files were removed.")
    _recover_download(directory)
    _check_unowned_downloads(directory)
    for path, _, _ in present:
        path.unlink()


def model_metadata() -> dict:
    """Return metadata for the pinned context model assets.

    Includes model id, upstream repository/revision, total download bytes, and
    license. Never returns ``None``.
    """
    return {"id": MODEL_ID, "repository": REPOSITORY, "revision": REVISION,
            "download_bytes": sum(item[1] for item in FILES.values()),
            "license": "MIT"}


def head_parameters() -> dict:
    """Load bounded context-classifier head parameters from package data.

    Returns the parsed JSON object; never returns ``None``.

    Raises:
        ValueError: If the parameter file exceeds the 128 KiB size limit.
    """
    path = Path(__file__).with_name("data") / "context_head.json"
    if path.stat().st_size > 128 * 1024:
        raise ValueError("Context classifier parameters exceed size limit.")
    return json.loads(path.read_text(encoding="utf-8"))
