"""One-time host setup and automatic loopback startup; never changes login caches."""

from __future__ import annotations

from hashlib import sha256
from http.client import HTTPException
import json
import os
from pathlib import Path
import secrets
import re
import plistlib
import subprocess
import sys
import time
import tempfile
from threading import Thread
import urllib.error
import urllib.request

import tomlkit

from secure_mcp.encrypted_session import session_file_lock
from secure_mcp.hooks import _atomic_json, _remove_owned, _settings


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def _installed(record, data):
    return data is not None and sha256(data).hexdigest() in {
        record["installed_sha256"],
        *record.get("accepted_sha256", []),
    }


def _recover_install(path):
    """Roll an interrupted prepare/apply transaction back without losing edits."""
    journal = path.parent / "installation.pending.json"
    if not journal.exists():
        return
    try:
        value = json.loads(journal.read_bytes())
        records = value["files"]
        if not isinstance(records, dict):
            raise ValueError()
        originals = {}
        for name, record in records.items():
            target = Path(name)
            if not target.is_absolute() or not isinstance(record, dict):
                raise ValueError()
            if not isinstance(record.get("after_sha256"), str) or not re.fullmatch(
                r"[0-9a-f]{64}", record["after_sha256"]
            ):
                raise ValueError()
            if record.get("before_hex") is not None and not isinstance(
                record["before_hex"], str
            ):
                raise ValueError()
            original = (
                bytes.fromhex(record["before_hex"])
                if record["before_hex"] is not None
                else None
            )
            current = target.read_bytes() if target.is_file() else None
            if (target.exists() and not target.is_file()) or (
                current != original
                and (
                    current is None
                    or sha256(current).hexdigest() != record["after_sha256"]
                )
            ):
                raise ValueError()
            originals[target] = original
    except (ValueError, KeyError, TypeError):
        raise ValueError(
            "Interrupted installation settings changed; merge installation.pending.json before retrying."
        ) from None
    # Validate all files before restoring any. Retain journal until every restore
    # succeeds, so recovery itself can be interrupted and safely retried.
    for target, original in originals.items():
        if original is None:
            target.unlink(missing_ok=True)
        else:
            atomic_bytes(target, original)
    journal.unlink()


def default_config() -> Path:
    return Path.home() / ".secure-mcp" / "gateway" / "config.json"


def atomic_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".secure-mcp-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_config(path: Path):
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Gateway configuration must be a JSON object.")
    if not isinstance(config.get("port"), int) or not 1024 <= config["port"] <= 65535:
        raise ValueError("Invalid gateway port.")
    if not isinstance(config.get("token"), str) or len(config["token"]) < 32:
        raise ValueError("Invalid local gateway token.")
    return config


def _parse_installation_manifest(data):
    message = "Invalid installation manifest; restore/merge installation.json before retrying."
    try:
        manifest = json.loads(data)
    except (ValueError, UnicodeError):
        raise ValueError(message) from None
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        raise ValueError(message)
    if "uninstall_started" in manifest and not isinstance(
        manifest["uninstall_started"], bool
    ):
        raise ValueError(message)
    for name, record in manifest["files"].items():
        if (
            not isinstance(name, str)
            or not Path(name).is_absolute()
            or not isinstance(record, dict)
        ):
            raise ValueError(message)
        original = record.get("original_hex")
        digest = record.get("installed_sha256")
        accepted = record.get("accepted_sha256", [])
        if (
            "original_hex" not in record
            or original is not None
            and (
                not isinstance(original, str)
                or len(original) % 2
                or not re.fullmatch(r"[0-9a-fA-F]*", original)
            )
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or not isinstance(accepted, list)
            or any(
                not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{64}", item)
                for item in accepted
            )
        ):
            raise ValueError(message)
    return manifest


def load_installation_manifest(path: Path):
    """Validate every restore record before any host settings are changed."""
    return _parse_installation_manifest(path.read_bytes())


def _healthy_response(config):
    request = urllib.request.Request(
        f"http://127.0.0.1:{config['port']}/health",
        headers={"X-SecureMCP-Token": config["token"]},
    )
    try:
        with urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect()
        ).open(request, timeout=1) as response:
            value = json.load(response)
            return (
                isinstance(value, dict)
                and value.get("service") == "secure-mcp-subscription-gateway"
            )
    except urllib.error.HTTPError as exc:
        exc.close()
        return False
    except (OSError, ValueError, HTTPException):
        return False


def healthy(config):
    try:
        return _healthy_response(config)
    except urllib.error.HTTPError as exc:
        exc.close()
        return False


def ensure_gateway(path: Path):
    config = load_config(path)
    with session_file_lock(path):
        if healthy(config):
            return
        options = (
            {
                "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
            }
            if os.name == "nt"
            else {"start_new_session": True}
        )
        # Keep the child's stderr for diagnostics only; prompts and tokens are
        # never logged by the gateway. A temp file avoids pipe backpressure.
        diagnostics = tempfile.TemporaryFile()
        try:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "secure_mcp",
                    "gateway",
                    "run",
                    "--config",
                    str(path.resolve()),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=diagnostics,
                **options,
            )
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if healthy(config):
                    # Keep the child handle owned and reap it after shutdown.
                    Thread(target=process.wait, daemon=True).start()
                    return
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            diagnostics.seek(0)
            detail = diagnostics.read(2000).decode("utf-8", "replace").strip()
            message = "Local gateway could not start; no direct-provider fallback was enabled."
            if detail:
                message += " (" + detail[-1000:] + ")"
            raise ValueError(message)
        finally:
            diagnostics.close()


def stop_gateway(path: Path):
    if not path.exists():
        return False
    config = load_config(path)
    if not healthy(config):
        return False
    request = urllib.request.Request(
        f"http://127.0.0.1:{config['port']}/shutdown",
        data=b"",
        headers={"X-SecureMCP-Token": config["token"]},
    )
    try:
        with urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect()
        ).open(request, timeout=5) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        # An authenticated HTTP rejection is never a successful shutdown.
        exc.close()
        raise
    except (HTTPException, OSError):
        # The daemon can close its socket while acknowledging shutdown. Confirm
        # that it actually disappeared rather than hiding a failed stop request.
        pass
    deadline = time.monotonic() + 5
    while healthy(config):
        if time.monotonic() >= deadline:
            raise OSError("Gateway remained active after the shutdown request.")
        time.sleep(0.05)
    return True


def codex_settings_homes(codex_dir: Path | None = None) -> list[Path]:
    """Orca mirrors canonical user config into its marked account homes."""
    home = codex_dir or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    if codex_dir is not None:
        return [home]
    orca_home = os.environ.get("ORCA_CODEX_HOME")
    if (
        orca_home
        and Path(orca_home).resolve() == home.resolve()
        and (home / ".orca-managed-home").is_file()
    ):
        canonical = Path.home() / ".codex"
        if canonical.resolve() != home.resolve():
            return [canonical, home]
    return [home]


def changed_installation_files(path: Path) -> list[str] | None:
    """Check installation ownership without exposing settings or credentials."""
    manifest_path = path.parent / "installation.json"
    if not manifest_path.exists():
        return None
    manifest = load_installation_manifest(manifest_path)
    return [
        name
        for name, record in manifest["files"].items()
        if not Path(name).is_file() or not _installed(record, Path(name).read_bytes())
    ]


def install_gateway(
    path: Path,
    agent="both",
    port=38117,
    claude_dir: Path | None = None,
    codex_dir: Path | None = None,
    startup_path: Path | None = None,
):
    path = path.resolve()
    manifest_path = path.parent / "installation.json"
    if manifest_path.exists():
        load_installation_manifest(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with session_file_lock(path):
        _recover_install(path)
        return _install_gateway(path, agent, port, claude_dir, codex_dir, startup_path)


def startup_registration(arguments, startup_path=None):
    """Use user-login startup, without installing agent hooks or a system service."""
    if any("\n" in argument or "\r" in argument for argument in arguments):
        raise ValueError("Startup arguments must not contain line breaks.")
    if sys.platform == "win32":
        destination = startup_path or (
            Path(os.environ["APPDATA"])
            / "Microsoft/Windows/Start Menu/Programs/Startup/SecureMCP.vbs"
        )
        command = subprocess.list2cmdline(arguments).replace('"', '""')
        data = f'CreateObject("WScript.Shell").Run "{command}", 0, False\r\n'.encode(
            "utf-16"
        )
    elif sys.platform == "darwin":
        destination = (
            startup_path
            or Path.home() / "Library/LaunchAgents/io.securemcp.gateway.plist"
        )
        data = plistlib.dumps(
            {
                "Label": "io.securemcp.gateway",
                "RunAtLoad": True,
                "ProgramArguments": arguments,
            }
        )
    else:
        destination = (
            startup_path
            or Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
            / "autostart/secure-mcp.desktop"
        )

        def quote(value):
            return (
                '"'
                + value.replace("%", "%%")
                .replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("`", "\\`")
                .replace("$", "\\$")
                + '"'
            )

        # Desktop Entry string escaping is decoded before Exec argument quoting.
        command = " ".join(quote(value) for value in arguments).replace("\\", "\\\\")
        data = f"[Desktop Entry]\nType=Application\nName=SecureMCP\nExec={command}\nTerminal=false\n".encode()
    return destination, data


def _install_gateway(path: Path, agent, port, claude_dir, codex_dir, startup_path):
    path = path.resolve()
    manifest_path = path.parent / "installation.json"
    previous_manifest = (
        load_installation_manifest(manifest_path) if manifest_path.exists() else None
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    config = (
        load_config(path)
        if path.exists()
        else {"port": port, "token": secrets.token_urlsafe(32)}
    )
    if config.get("mode", "subscription") != "subscription":
        raise ValueError("API configuration cannot be used for subscription setup.")
    if path.exists() and config["port"] != port:
        # After `gateway uninstall` the config file is intentionally retained
        # for recovery (token/state), while installation.json is removed. With
        # no active installation the stored port can be updated instead of
        # leaving users stuck with no supported way to change it.
        if previous_manifest is None:
            config["port"] = port
        else:
            raise ValueError(
                "Existing installation uses another port; uninstall before changing it."
            )
    arguments = [
        sys.executable,
        "-m",
        "secure_mcp",
        "gateway",
        "ensure",
        "--config",
        str(path),
    ]
    startup, startup_data = startup_registration(arguments, startup_path)
    changes = {startup: startup_data}
    if agent in {"claude", "both"}:
        settings = (
            claude_dir
            or Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
        ) / "settings.json"
        value = _settings(settings)
        if not isinstance(value.get("env", {}), dict) or not isinstance(
            value.get("env", {}).get("ANTHROPIC_CUSTOM_HEADERS", ""), str
        ):
            raise ValueError(
                "Invalid Claude environment settings; no settings were overwritten."
            )
        env = value.setdefault("env", {})
        if (
            env.get("ANTHROPIC_AUTH_TOKEN")
            or env.get("ANTHROPIC_API_KEY")
            or value.get("apiKeyHelper")
        ):
            raise ValueError(
                "Remove API/gateway credential overrides before installing subscription mode."
            )
        env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{config['port']}/claude"
        existing = env.get("ANTHROPIC_CUSTOM_HEADERS", "")
        lines = [
            line
            for line in existing.splitlines()
            if not line.lower().startswith("x-securemcp-token:")
        ]
        env["ANTHROPIC_CUSTOM_HEADERS"] = "\n".join(
            lines + ["X-SecureMCP-Token: " + config["token"]]
        )
        _remove_owned(value, "claude")
        changes[settings] = (
            json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        ).encode()
    homes = codex_settings_homes(codex_dir) if agent in {"codex", "both"} else []
    for home in homes:
        settings = home / "config.toml"
        value = (
            tomlkit.parse(settings.read_text(encoding="utf-8"))
            if settings.exists()
            else tomlkit.document()
        )
        value["model_provider"] = "secure_mcp_subscription"
        value["forced_login_method"] = "chatgpt"
        providers = value.setdefault("model_providers", {})
        if not isinstance(providers, dict):
            raise ValueError(
                "Codex model_providers must be a table; no settings were overwritten."
            )
        providers["secure_mcp_subscription"] = {
            "name": "SecureMCP subscription",
            "base_url": f"http://127.0.0.1:{config['port']}/codex",
            "wire_api": "responses",
            "requires_openai_auth": True,
            "supports_websockets": False,
            "http_headers": {"X-SecureMCP-Token": config["token"]},
        }
        changes[settings] = tomlkit.dumps(value).encode()
    mirrors = (
        {homes[1] / "config.toml": homes[0] / "config.toml"} if len(homes) == 2 else {}
    )
    return apply_settings(path, config, changes, mirrors=mirrors)


def apply_settings(path: Path, config, changes, *, mirrors=None):
    """Back up and transactionally apply settings, shared by subscription/API setup."""
    manifest_path = path.parent / "installation.json"
    _recover_install(path)
    previous_config = path.read_bytes() if path.exists() else None
    previous_manifest = manifest_path.read_bytes() if manifest_path.exists() else None
    manifest = (
        _parse_installation_manifest(previous_manifest)
        if previous_manifest is not None
        else {"files": {}}
    )
    if manifest.get("uninstall_started"):
        raise ValueError(
            "Uninstall recovery is incomplete; retry uninstall before installing."
        )
    # Prepare and validate every file before any host settings are changed.
    for settings, data in changes.items():
        name = str(settings.resolve())
        record = manifest["files"].get(name)
        if record and (
            not settings.is_file() or not _installed(record, settings.read_bytes())
        ):
            raise ValueError(
                "Host settings changed after setup; uninstall/merge them before reinstalling."
            )
        if record is None:
            record = {
                "original_hex": settings.read_bytes().hex()
                if settings.exists()
                else None
            }
            manifest["files"][name] = record
        record["installed_sha256"] = sha256(data).hexdigest()
        record.pop("accepted_sha256", None)
        if mirrors and settings in mirrors:
            record["accepted_sha256"] = [sha256(changes[mirrors[settings]]).hexdigest()]
    originals = {
        settings: settings.read_bytes() if settings.exists() else None
        for settings in changes
    }
    applied = []
    journal_path = path.parent / "installation.pending.json"
    pending = {
        str(settings.resolve()): {
            "before_hex": original.hex() if original is not None else None,
            "after_sha256": sha256(changes[settings]).hexdigest(),
        }
        for settings, original in originals.items()
    }
    config_data = (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode()
    manifest_data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    for target, previous, data in [
        (path, previous_config, config_data),
        (manifest_path, previous_manifest, manifest_data),
    ]:
        pending[str(target.resolve())] = {
            "before_hex": previous.hex() if previous is not None else None,
            "after_sha256": sha256(data).hexdigest(),
        }
    _atomic_json(journal_path, {"files": pending})
    try:
        _atomic_json(path, config)
        path.chmod(0o600)
        _atomic_json(manifest_path, manifest)
        manifest_path.chmod(0o600)
        for settings, data in changes.items():
            atomic_bytes(settings, data)
            applied.append(settings)
            settings.chmod(0o600)
        journal_path.unlink()
    except OSError:
        for settings in reversed(applied):
            original = originals[settings]
            if original is None:
                settings.unlink()
            else:
                atomic_bytes(settings, original)
        if previous_manifest is None:
            manifest_path.unlink(missing_ok=True)
        else:
            atomic_bytes(manifest_path, previous_manifest)
        if previous_config is None:
            path.unlink(missing_ok=True)
        else:
            atomic_bytes(path, previous_config)
        journal_path.unlink(missing_ok=True)
        raise
    return list(changes)


def uninstall_gateway(path: Path):
    path = path.resolve()
    if not path.parent.exists():
        return False
    manifest_path = path.parent / "installation.json"
    if manifest_path.exists():
        load_installation_manifest(manifest_path)
    with session_file_lock(path):
        _recover_install(path)
        return _uninstall_gateway(path)


def _uninstall_gateway(path: Path):
    manifest_path = path.parent / "installation.json"
    if not manifest_path.exists():
        return False
    manifest = load_installation_manifest(manifest_path)
    recovering = manifest.get("uninstall_started") is True
    originals = {}
    for name, record in manifest["files"].items():
        settings = Path(name)
        original = (
            bytes.fromhex(record["original_hex"])
            if record["original_hex"] is not None
            else None
        )
        originals[settings] = original
        current = settings.read_bytes() if settings.is_file() else None
        installed = _installed(record, current)
        restored = (
            recovering
            and current == original
            and (current is not None or not settings.exists())
        )
        if not installed and not restored:
            raise ValueError(
                "Host settings changed; refusing to overwrite them. Restore/merge installation.json manually."
            )
    # Persist the recovery boundary before touching any settings. A failed or
    # interrupted uninstall may retry files already restored to exact originals,
    # while any other user edits still prevent overwriting them.
    if not recovering:
        manifest["uninstall_started"] = True
        _atomic_json(manifest_path, manifest)
    stop_gateway(path)
    for settings, original in originals.items():
        if original is None:
            settings.unlink(missing_ok=True)
        else:
            atomic_bytes(settings, original)
    manifest_path.unlink()
    return True
