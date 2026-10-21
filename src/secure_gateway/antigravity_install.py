"""Owned stdio MCP registration; never changes Antigravity authentication."""

import json
from pathlib import Path
import sys

from secure_gateway.encrypted_session import session_file_lock
from secure_gateway.gateway_install import atomic_bytes
from secure_gateway.hooks import _atomic_json


def _settings(path):
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(value, dict) or not isinstance(value.get("mcpServers", {}), dict):
        raise ValueError("Antigravity configuration must contain an mcpServers object.")
    return value


def _record(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or type(value.get("had_entry")) is not bool
        or not isinstance(value.get("installed"), dict)
        or "original" not in value
    ):
        raise ValueError("Invalid Antigravity installation record.")
    return value


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _recover(path, record_path, pending):
    """Validate both sides before rolling back an interrupted owned transaction."""
    if not pending.exists():
        return
    try:
        journal = json.loads(pending.read_bytes())
        originals = {}
        for name, target in (("settings", path), ("record", record_path)):
            states = journal[name]
            before = (
                bytes.fromhex(states["before_hex"])
                if states["before_hex"] is not None
                else None
            )
            after = (
                bytes.fromhex(states["after_hex"])
                if states["after_hex"] is not None
                else None
            )
            current = target.read_bytes() if target.is_file() else None
            if (target.exists() and not target.is_file()) or current not in (
                before,
                after,
            ):
                raise ValueError()
            originals[target] = before
    except (ValueError, TypeError, KeyError):
        raise ValueError(
            "Antigravity settings changed during interrupted registration; merge the pending record before retrying."
        ) from None
    # Keeping the journal until both restores finish also makes recovery retryable.
    for target, before in originals.items():
        if before is None:
            target.unlink(missing_ok=True)
        else:
            atomic_bytes(target, before)
    pending.unlink()


def configure_antigravity(path: Path, install=True):
    """Back up once, preserve other servers, and restore only our owned entry."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    record_path = path.with_name(path.name + ".secure-gateway.json")
    pending = path.with_name(path.name + ".secure-gateway.pending.json")
    backup = path.with_name(path.name + ".secure-gateway.bak")
    with session_file_lock(path):
        _recover(path, record_path, pending)
        settings = _settings(path)
        servers = settings.get("mcpServers", {})
        record = _record(record_path) if record_path.exists() else None
        if record is not None and servers.get("secure-gateway") != record["installed"]:
            raise ValueError(
                "SecureGateway registration changed; merge it before reinstalling/removing."
            )
        if not install and record is None:
            return None
        original_bytes = path.read_bytes() if path.exists() else None
        previous_record = record_path.read_bytes() if record_path.exists() else None
        if install:
            installed = {
                "command": sys.executable,
                "args": ["-m", "secure_gateway", "serve"],
            }
            if record is None:
                record = {
                    "had_entry": "secure-gateway" in servers,
                    "original": servers.get("secure-gateway"),
                    "installed": installed,
                }
                if original_bytes is not None:
                    atomic_bytes(backup, original_bytes)
            else:
                record["installed"] = installed
            servers["secure-gateway"] = installed
        else:
            assert record is not None
            if record["had_entry"]:
                servers["secure-gateway"] = record["original"]
            else:
                servers.pop("secure-gateway", None)
        settings["mcpServers"] = servers
        _atomic_json(
            pending,
            {
                "settings": {
                    "before_hex": original_bytes.hex()
                    if original_bytes is not None
                    else None,
                    "after_hex": _json_bytes(settings).hex(),
                },
                "record": {
                    "before_hex": previous_record.hex()
                    if previous_record is not None
                    else None,
                    "after_hex": _json_bytes(record).hex() if install else None,
                },
            },
        )
        try:
            if install:
                _atomic_json(record_path, record)
            _atomic_json(path, settings)
            if not install:
                record_path.unlink()
            pending.unlink()
        except OSError:
            if original_bytes is None:
                path.unlink(missing_ok=True)
            else:
                atomic_bytes(path, original_bytes)
            if previous_record is None:
                record_path.unlink(missing_ok=True)
            else:
                atomic_bytes(record_path, previous_record)
            pending.unlink(missing_ok=True)
            raise
    return backup if backup.exists() else None


def antigravity_status(path: Path):
    settings = _settings(path)
    record_path = path.with_name(path.name + ".secure-gateway.json")
    record = _record(record_path) if record_path.exists() else None
    return {
        "agent": "antigravity",
        "settings": str(path),
        "ready": record is not None
        and settings.get("mcpServers", {}).get("secure-gateway") == record["installed"],
    }
