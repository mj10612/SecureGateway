"""Crash, concurrent-owner and unowned-partial recovery for pinned model data."""

from hashlib import sha256
import io
import json
import subprocess
import sys
import time

import pytest

from secure_gateway import context_assets as assets


@pytest.fixture
def tiny_assets(monkeypatch):
    contents = {"first.bin": b"verified first", "second.bin": b"verified second"}
    monkeypatch.setattr(assets, "FILES", {
        name: (name, len(data), sha256(data).hexdigest()) for name, data in contents.items()
    })

    def download(request, **_kwargs):
        name = request.full_url.split("/")[-1].split("?")[0]
        return io.BytesIO(contents[name])

    monkeypatch.setattr(assets.urllib.request, "urlopen", download)
    return contents


@pytest.mark.parametrize("recovery", ["install", "remove"])
def test_killed_download_releases_lock_and_recovers(tmp_path, tiny_assets, recovery):
    directory = tmp_path / "model"
    ready = tmp_path / "ready"
    script = """
from hashlib import sha256
import io
from pathlib import Path
import sys, time
from secure_gateway import context_assets as assets
directory, ready = map(Path, sys.argv[1:])
contents = {'first.bin': b'verified first', 'second.bin': b'verified second'}
assets.FILES = {name: (name, len(data), sha256(data).hexdigest()) for name, data in contents.items()}
def download(request, **kwargs):
    name = request.full_url.split('/')[-1].split('?')[0]
    if name == 'second.bin':
        ready.write_text('downloading')
        while True:
            time.sleep(0.1)
    return io.BytesIO(contents[name])
assets.urllib.request.urlopen = download
assets.install_model(directory)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(directory), str(ready)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 10
        while not ready.exists():
            if process.poll() is not None or time.monotonic() > deadline:
                stdout, stderr = process.communicate(timeout=2)
                pytest.fail(f"Downloader failed to reach barrier: {stdout!r} {stderr!r}")
            time.sleep(0.02)
        assert (directory / "first.bin").read_bytes() == tiny_assets["first.bin"]
        assert (directory / "second.bin.download").exists()
        for operation in (assets.install_model, assets.remove_model):
            with pytest.raises(ValueError, match="in use"):
                operation(directory)
        process.kill()
        process.communicate(timeout=5)
        if recovery == "install":
            assets.install_model(directory)
        else:
            assets.remove_model(directory)
            assert not any((directory / name).exists() for name in tiny_assets)
            assets.install_model(directory)
        assets.verify_model(directory)
        assert not list(directory.glob("*.download"))
        assert not (directory / assets._DOWNLOAD_RECORD).exists()
        assets.remove_model(directory)
        assert not list(directory.iterdir())
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)


def test_unowned_partial_remove_explains_recovery_without_success(tmp_path, tiny_assets):
    assets.install_model(tmp_path)
    pending = tmp_path / "second.bin.download"
    pending.write_bytes(b"user-created partial")
    with pytest.raises(FileExistsError, match="inspect/move.*model-install or model-remove"):
        assets.remove_model(tmp_path)
    assert pending.read_bytes() == b"user-created partial"
    assert (tmp_path / "first.bin").read_bytes() == tiny_assets["first.bin"]


def test_replaced_pending_inode_is_not_deleted(tmp_path, tiny_assets):
    pending = tmp_path / "first.bin.download"
    pending.write_bytes(b"original temporary bytes")
    identity = assets._download_identity(pending)
    replacement = tmp_path / "replacement"
    replacement.write_bytes(b"user replacement")
    replacement.replace(pending)
    (tmp_path / assets._DOWNLOAD_RECORD).write_text(json.dumps({
        "version": 1, "asset": "first.bin", "identity": identity,
    }))
    for operation in (assets.install_model, assets.remove_model):
        with pytest.raises(ValueError, match="ownership record"):
            operation(tmp_path)
    assert pending.read_bytes() == b"user replacement"


def test_network_failure_cleans_only_current_pending(tmp_path, tiny_assets, monkeypatch):
    def fail(*_args, **_kwargs):
        raise OSError("network interrupted")

    monkeypatch.setattr(assets.urllib.request, "urlopen", fail)
    with pytest.raises(OSError, match="network interrupted"):
        assets.install_model(tmp_path)
    assert not list(tmp_path.iterdir())


def test_changed_final_prevents_partial_cleanup(tmp_path, tiny_assets):
    pending = tmp_path / "first.bin.download"
    pending.write_bytes(b"recorded pending")
    (tmp_path / assets._DOWNLOAD_RECORD).write_text(json.dumps({
        "version": 1, "asset": "first.bin", "identity": assets._download_identity(pending),
    }))
    (tmp_path / "second.bin").write_bytes(b"user modified final")
    with pytest.raises(ValueError, match="no model files"):
        assets.remove_model(tmp_path)
    assert pending.read_bytes() == b"recorded pending"
