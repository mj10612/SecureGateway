"""Local Claude Code and Codex hooks: partial tool-text protection."""

from __future__ import annotations

from contextlib import contextmanager
import base64
import errno
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import re
import shlex
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Iterator

from secure_gateway.encrypted_session import (
    _LOCK_MAGIC, SessionExpiredError, load_session, save_session, session_file_lock,
)
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.engine.strategies import StrategyGenerator
from secure_gateway.models import MaskMode, SurrogateStrategy
from secure_gateway.session import PrivacySession


EVENTS = ("PreToolUse", "PostToolUse", "MessageDisplay", "SessionEnd")
AGENT_EVENTS = {
    "claude": EVENTS,
    "codex": ("PreToolUse", "PostToolUse", "SessionEnd"),
}
MARKER = "-m secure_gateway hook --state-dir"
_ENCODED_COMMAND = "powershell.exe -NoProfile -NonInteractive -EncodedCommand "
_SNAPSHOT_NAME = re.compile(r"[a-f0-9]{64}\.enc")
_SNAPSHOT_STATUSES = ("valid", "expired", "corrupt", "active", "legacy_lock", "retired", "unknown")
# Preserve protocol discriminators, IDs, binary data and JSON scalar types.
TEXT_FIELDS = frozenset(
    {
        "stdout",
        "stderr",
        "text",
        "content",
        "output",
        "filePath",
        "file_path",
        "filename",
        "filenames",
        "matches",
        "line",
        "lines",
        "message",
    }
)
OPAQUE_FIELDS = frozenset(
    {
        "type",
        "mimeType",
        "mime_type",
        "data",
        "signature",
        "id",
        "tool_use_id",
        "encoding",
    }
)
LOCAL_TOOLS = frozenset(
    {"Bash", "PowerShell", "Read", "Grep", "Glob", "Edit", "Write", "MultiEdit"}
)


def default_state_dir() -> Path:
    return Path.home() / ".secure-gateway" / "hooks"


def agent_state_dir(directory: Path, agent: str) -> Path:
    """Keep existing Claude snapshots in place; isolate new Codex sessions."""
    return directory / "codex" if agent == "codex" else directory


def _atomic_json(path: Path, value: Any) -> None:
    fd, temporary = tempfile.mkstemp(prefix=".secure-gateway-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _settings(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(value, dict) or not isinstance(value.get("hooks", {}), dict):
        raise ValueError("Invalid agent settings; no settings were overwritten.")
    for entries in value.get("hooks", {}).values():
        if not isinstance(entries, list):
            raise ValueError("Invalid hook registry; no settings were overwritten.")
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("hooks"), list):
                raise ValueError("Invalid hook entry; no settings were overwritten.")
            if not all(isinstance(h, dict) for h in entry["hooks"]):
                raise ValueError("Invalid hook command; no settings were overwritten.")
    return value


def _powershell_invocation(args: list[str]) -> str:
    return "& " + " ".join("'" + arg.replace("'", "''") + "'" for arg in args) + "; exit $LASTEXITCODE"


def _hook_command(args: list[str]) -> str:
    if os.name != "nt":
        return shlex.join(args)
    # cmd expands percent variables even inside double quotes. Encode literal
    # arguments instead of exposing path metacharacters to its parser.
    if any(any(c in arg for c in "&%|<>^!") for arg in args):
        script = _powershell_invocation(args)
        return _ENCODED_COMMAND + base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return subprocess.list2cmdline(args)


def _command_parts(command: str) -> list[str]:
    if command.startswith(_ENCODED_COMMAND):
        encoded = command[len(_ENCODED_COMMAND):]
        try:
            script = base64.b64decode(encoded, validate=True).decode("utf-16le")
        except (ValueError, UnicodeError):
            raise ValueError("Invalid hook command") from None
        args = [part.replace("''", "'") for part in re.findall(r"'((?:[^']|'')*)'", script)]
        if script != _powershell_invocation(args):
            raise ValueError("Invalid hook command")
        return args
    return [part.strip('"') for part in shlex.split(command, posix=os.name != "nt")]


def _owned(hook: dict[str, Any], agent: str | None = None) -> bool:
    command = hook.get("command")
    if (
        hook.get("type") != "command"
        or not isinstance(command, str)
    ):
        return False
    try:
        parts = _command_parts(command)
    except ValueError:
        return False
    if parts[1:5] != ["-m", "secure_gateway", "hook", "--state-dir"]:
        return False
    owner = "claude" if len(parts) == 6 else None
    if len(parts) == 8 and parts[6] == "--agent" and parts[7] in AGENT_EVENTS:
        owner = parts[7]
    return owner is not None and (agent is None or owner == agent)


def _remove_owned(config: dict[str, Any], agent: str) -> None:
    registry = config.get("hooks", {})
    for event in list(registry):
        remaining = []
        for entry in registry[event]:
            kept = [h for h in entry["hooks"] if not _owned(h, agent)]
            if kept:
                remaining.append({**entry, "hooks": kept})
        if remaining:
            registry[event] = remaining
        else:
            del registry[event]


def configure(
    settings: Path, state_dir: Path, install: bool, agent: str = "claude"
) -> Path | None:
    """Merge only our hooks; back up exact previous bytes and preserve other settings."""
    if agent not in AGENT_EVENTS:
        raise ValueError("Unsupported agent.")
    settings.parent.mkdir(parents=True, exist_ok=True)
    with session_file_lock(settings):
        config = _settings(settings)
        _remove_owned(config, agent)
        if install:
            state_dir = state_dir.resolve()
            state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            key = state_dir / "key"
            with session_file_lock(key):
                if key.exists():
                    try:
                        password = key.read_text(encoding="ascii")
                    except UnicodeError:
                        raise ValueError("Invalid local encryption key; restore it before reinstalling.") from None
                    if not password and any(state_dir.glob("*.enc")):
                        raise ValueError("Missing local encryption key for existing snapshots; restore it before reinstalling.")
                else:
                    password = ""
                    if any(state_dir.glob("*.enc")):
                        raise ValueError("Missing local encryption key for existing snapshots; restore it before reinstalling.")
                if not password:
                    password = secrets.token_urlsafe(32)
                    fd, temporary = tempfile.mkstemp(prefix=".key-", dir=state_dir)
                    try:
                        with os.fdopen(fd, "w", encoding="ascii") as stream:
                            stream.write(password)
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(temporary, key)
                    finally:
                        if os.path.exists(temporary):
                            os.unlink(temporary)
            args = [
                sys.executable,
                "-m",
                "secure_gateway",
                "hook",
                "--state-dir",
                str(state_dir),
            ]
            if agent != "claude":
                args.extend(["--agent", agent])
            command = _hook_command(args)
            registry = config.setdefault("hooks", {})
            for event in AGENT_EVENTS[agent]:
                registry.setdefault(event, []).append(
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": command,
                                "timeout": 3
                                if agent == "codex" and event == "SessionEnd"
                                else 10,
                            }
                        ]
                    }
                )
        backup = None
        if settings.exists():
            backup = settings.with_name(
                settings.name + f".secure-gateway-{time.time_ns()}.bak"
            )
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(settings.read_bytes())
        _atomic_json(settings, config)
        return backup


def installation_status(
    settings: Path, state_dir: Path, agent: str = "claude"
) -> dict[str, Any]:
    if agent not in AGENT_EVENTS:
        raise ValueError("Unsupported agent.")
    config = _settings(settings)
    registry = config.get("hooks", {})
    installed = [
        event
        for event in AGENT_EVENTS[agent]
        if any(
            _working_registration(h, state_dir, agent)
            for entry in registry.get(event, [])
            for h in entry["hooks"]
        )
    ]
    try:
        key_valid = bool((state_dir / "key").read_text(encoding="ascii"))
    except (OSError, UnicodeError):
        key_valid = False
    return {
        "installed_events": installed,
        "key_present": (state_dir / "key").is_file(),
        "ready": len(installed) == len(AGENT_EVENTS[agent])
        and key_valid,
        "scope": "tool text only; prompts, attachments and telemetry are not covered",
        "agent": agent,
        "display_restoration": agent == "claude",
        "host_trust": "Review installed hooks using /hooks"
        if agent == "codex"
        else "Check host trust settings",
    }


def _working_registration(hook: dict[str, Any], state_dir: Path, agent: str) -> bool:
    if not _owned(hook, agent):
        return False
    parts = _command_parts(hook["command"])
    return (
        Path(parts[0].strip('"')).is_file()
        and Path(parts[5].strip('"')).resolve() == state_dir.resolve()
    )


class _SnapshotBusy(ValueError):
    pass


class _LegacySnapshotLock(ValueError):
    pass


@contextmanager
def _existing_snapshot_lock(path: Path):
    """Inspect under an existing native lock; never create a lock for a dry run."""
    lock = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock, os.O_RDWR)
    except FileNotFoundError:
        yield
        return
    try:
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise _SnapshotBusy from None
            raise
        if os.read(fd, len(_LOCK_MAGIC) + 1) != _LOCK_MAGIC:
            raise _LegacySnapshotLock
        yield
    finally:
        os.close(fd)


class HookStore:
    """Encrypted snapshots shared by short-lived hook processes; no HTTP service."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.engine = MaskingEngine()

    def path(self, sid: str) -> Path:
        if not isinstance(sid, str) or not sid.strip() or len(sid) > 1024:
            raise ValueError("A valid host session ID is required.")
        return self.directory / (sha256(sid.encode("utf-8")).hexdigest() + ".enc")

    @staticmethod
    def _retired(path: Path) -> Path:
        return path.with_name(path.name + ".retired")

    @staticmethod
    def _reference(path: Path) -> str:
        return sha256(path.name.encode("utf-8")).hexdigest()[:16]

    def _snapshot_paths(self) -> list[Path]:
        if not self.directory.is_dir():
            return []
        paths = set()
        for entry in self.directory.iterdir():
            name = entry.name
            if name.endswith(".retired"):
                name = name[:-8]
            elif name.endswith(".lock"):
                name = name[:-5]
            if name.endswith(".enc"):
                paths.add(self.directory / name)
        return sorted(paths)

    def _snapshot_status(self, path: Path, password: str | None) -> dict[str, Any]:
        result: dict[str, Any] = {"ref": self._reference(path), "status": "unknown"}
        if not _SNAPSHOT_NAME.fullmatch(path.name) or path.is_symlink():
            return result
        if self._retired(path).exists():
            result["status"] = "retired"
            return result
        session = None
        try:
            with _existing_snapshot_lock(path):
                if not path.is_file() or password is None:
                    return result
                session = load_session(path, password, None)
                result.update(status="valid", mapping_count=len(session.forward_store),
                              mask_calls=session.total_mask_calls,
                              unmask_calls=session.total_unmask_calls)
        except _SnapshotBusy:
            result["status"] = "active"
        except _LegacySnapshotLock:
            result["status"] = "legacy_lock"
        except SessionExpiredError:
            result["status"] = "expired"
        except ValueError:
            result["status"] = "corrupt"
        except OSError:
            result["status"] = "unknown"
        finally:
            if session is not None:
                session.clear()
        return result

    def _diagnostic_password(self) -> str | None:
        try:
            return (self.directory / "key").read_text(encoding="ascii") or None
        except (OSError, UnicodeError):
            return None

    def snapshot_diagnostics(self) -> dict[str, Any]:
        """Local metadata only; never return identities, mappings or file paths."""
        password = self._diagnostic_password()
        snapshots = [self._snapshot_status(path, password) for path in self._snapshot_paths()]
        counts = {status: 0 for status in _SNAPSHOT_STATUSES}
        for item in snapshots:
            counts[item["status"]] += 1
        return {"total": len(snapshots), "counts": counts, "snapshots": snapshots}

    def gc(self, dry_run: bool = True) -> dict[str, Any]:
        """Retire only authenticated expired snapshots, revalidating under a lock."""
        report = self.snapshot_diagnostics()
        candidates = {item["ref"] for item in report["snapshots"]
                      if item["status"] == "expired" or item["status"] == "retired"}
        candidates &= {self._reference(path) for path in self._snapshot_paths() if path.is_file()}
        report.update(dry_run=dry_run, candidates=len(candidates), removed=0)
        if dry_run:
            return report
        password = self._diagnostic_password()
        if password is None:
            return report
        for path in self._snapshot_paths():
            if self._reference(path) not in candidates or path.is_symlink():
                continue
            session = None
            try:
                with session_file_lock(path):
                    if not path.is_file():
                        continue
                    try:
                        session = load_session(path, password, None)
                    except SessionExpiredError:
                        retired = self._retired(path)
                        if not retired.exists():
                            fd = os.open(retired, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                            with os.fdopen(fd, "wb") as stream:
                                stream.write(b"SecureGateway-retired-hook-session-v1\n")
                                stream.flush()
                                os.fsync(stream.fileno())
                        path.unlink()
                        report["removed"] += 1
            except (ValueError, OSError):
                # Busy, changed, corrupt and missing entries require no deletion.
                continue
            finally:
                if session is not None:
                    session.clear()
        return report

    @contextmanager
    def session(
        self, sid: str, create: bool = False
    ) -> Iterator[PrivacySession | None]:
        path = self.path(sid)
        if self._retired(path).exists():
            raise ValueError("Hook session has been retired; start a new conversation.")
        password = (self.directory / "key").read_text(encoding="ascii")
        if not password:
            raise ValueError("Missing local encryption key.")
        with session_file_lock(path):
            if self._retired(path).exists():
                raise ValueError("Hook session has been retired; start a new conversation.")
            session = load_session(path, password, sid) if path.exists() else None
            if session is None and create:
                session = PrivacySession(
                    sid, MaskMode.ENTITIES_ONLY, SurrogateStrategy.UNICODE
                )
            try:
                yield session
                if session is not None:
                    save_session(path, session, password)
            finally:
                if session is not None:
                    session.clear()

    def mask(self, text: str, session: PrivacySession) -> str:
        # Tool output can echo values the model already saw. Never nest placeholders.
        pieces = []
        end = 0
        for match in StrategyGenerator.get_pattern(session.strategy).finditer(text):
            pieces.append(self._mask_piece(text[end : match.start()], session))
            pieces.append(match.group())
            end = match.end()
        pieces.append(self._mask_piece(text[end:], session))
        session.total_mask_calls += 1
        session.touch()
        return "".join(pieces)

    def _mask_piece(self, text: str, session: PrivacySession) -> str:
        return self.engine.mask_text(
            text,
            session.session_id,
            session.generator,
            session.forward_store,
            session.reverse_store,
            mode=MaskMode.ENTITIES_ONLY,
        ).masked_text

    def restore(self, text: str, session: PrivacySession | None) -> str:
        result = self.engine.unmask(
            text,
            session.session_id if session else "missing",
            session.reverse_store if session else {},
            SurrogateStrategy.UNICODE,
            strict=True,
        )
        if session:
            session.total_unmask_calls += 1
            session.touch()
        return result.unmasked_text

    def clear(self, sid: str) -> None:
        path = self.path(sid)
        with session_file_lock(path):
            path.unlink(missing_ok=True)


def _walk(
    value: Any,
    transform: Callable[[str], str],
    all_strings: bool = False,
    preserve_protocol: bool = False,
) -> Any:
    if isinstance(value, str):
        return transform(value) if all_strings else value
    if isinstance(value, list):
        return [
            _walk(item, transform, all_strings, preserve_protocol) for item in value
        ]
    if isinstance(value, dict):
        return {
            key: item
            if preserve_protocol
            and (
                key in OPAQUE_FIELDS
                or (key == "stdout" and value.get("isImage") is True)
            )
            else _walk(
                item, transform, all_strings or key in TEXT_FIELDS, preserve_protocol
            )
            for key, item in value.items()
        }
    return value


def handle_hook(
    payload: dict[str, Any], state_dir: Path, agent: str = "claude"
) -> dict[str, Any]:
    event = payload.get("hook_event_name")
    if agent not in AGENT_EVENTS or event not in AGENT_EVENTS[agent]:
        raise ValueError("Unsupported hook event.")
    sid = payload.get("session_id")
    if not isinstance(sid, str):
        raise ValueError("A host session ID is required.")
    store = HookStore(state_dir)
    store.path(sid)
    if event == "SessionEnd":
        store.clear(sid)
        return {}
    if event == "PostToolUse":
        if "tool_response" not in payload:
            raise ValueError("Missing tool response.")
        with store.session(sid, create=True) as session:
            assert session is not None
            replacement = _walk(
                payload["tool_response"],
                lambda text: store.mask(text, session),
                isinstance(payload["tool_response"], (str, list)),
                preserve_protocol=True,
            )
        if agent == "codex":
            # Codex does not support Claude's updatedToolOutput. Feedback replacement
            # also reaches code-mode tool calls without rejecting the nested promise.
            text = (
                replacement
                if isinstance(replacement, str)
                else json.dumps(replacement, ensure_ascii=False)
            )
            return {
                "continue": False,
                "stopReason": text or "SecureGateway: empty tool output.",
            }
        return {
            "hookSpecificOutput": {
                "hookEventName": event,
                "updatedToolOutput": replacement,
            }
        }
    with store.session(sid) as session:
        if event == "PreToolUse":
            if not isinstance(payload.get("tool_input"), dict):
                raise ValueError("Missing tool input object.")
            local_tools = {"Bash", "apply_patch"} if agent == "codex" else LOCAL_TOOLS
            if payload.get("tool_name") not in local_tools:
                # Never restore originals into remote MCP/network tools.
                if StrategyGenerator.get_pattern(SurrogateStrategy.UNICODE).search(
                    json.dumps(payload["tool_input"], ensure_ascii=False)
                ):
                    raise ValueError("Restoration is restricted to local tools.")
                return {}
            restored = _walk(
                payload["tool_input"], lambda text: store.restore(text, session), True
            )
            if restored == payload["tool_input"]:
                return {}
            if agent == "codex":
                if not isinstance(restored.get("command"), str):
                    raise ValueError("Codex local tool requires a command string.")
                # Codex requires allow alongside updatedInput. This is PreToolUse,
                # not a PermissionRequest approval; sandbox/approval policy is retained.
                return {
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "permissionDecision": "allow",
                        "updatedInput": restored,
                    }
                }
            # Never grant permission: the host must run its normal approval checks.
            return {
                "hookSpecificOutput": {"hookEventName": event, "updatedInput": restored}
            }
        delta = payload.get("delta")
        if not isinstance(delta, str):
            raise ValueError("Missing display delta.")
        return {
            "hookSpecificOutput": {
                "hookEventName": event,
                "displayContent": store.restore(delta, session),
            }
        }
