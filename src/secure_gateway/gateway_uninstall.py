"""Selective subscription settings recovery; never touches login caches."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re

import tomlkit


PROVIDER = "secure_gateway_subscription"


def recovery_settings():
    """Discover canonical, active and synchronized Orca settings, read-only."""
    home = Path.home()
    codex = {home / ".codex/config.toml"}
    roots = {home / "orca", home / ".config/orca",
             home / "Library/Application Support/orca"}
    if os.environ.get("APPDATA"):
        roots.add(Path(os.environ["APPDATA"]) / "orca")
    for key in ("CODEX_HOME", "ORCA_CODEX_HOME"):
        if os.environ.get(key):
            active = Path(os.environ[key])
            codex.add(active / "config.toml")
            if active.name == "home" and active.parent.parent.name == "codex-accounts":
                roots.add(active.parent.parent.parent)
    for root in roots:
        codex.update(root.glob("codex-accounts/*/home/config.toml"))
    claude = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(home / ".claude")))
    return codex | {claude / "settings.json"}


def _gateway_url(value, agent, config):
    if not isinstance(value, str):
        return False
    if config is not None:
        return value == f"http://127.0.0.1:{config['port']}/{agent}"
    return bool(re.fullmatch(r"http://127\.0\.0\.1:[0-9]{1,5}/" + agent, value))


def _token_line(line, config):
    name, separator, value = line.partition(":")
    return (bool(separator) and name.strip().lower() == "x-securegateway-token"
            and (value.strip() == config["token"] if config is not None else len(value.strip()) >= 32))


def _restore_key(current, original, key, installed):
    if current.get(key) == installed:
        if key in original:
            current[key] = original[key]
        else:
            current.pop(key, None)


def merge_subscription_settings(path, current, original, config):
    """Return cleaned bytes, or None when the file is not a supported setting.

    A missing original means recovery without a backup: remove recognizable
    gateway keys, never guess the previous provider, URL or login method.
    """
    if path.name == "config.toml":
        value = tomlkit.parse(current.decode("utf-8-sig"))
        before = tomlkit.parse(original.decode("utf-8-sig")) if original else {}
        providers = value.get("model_providers", {})
        provider = providers.get(PROVIDER, {}) if isinstance(providers, dict) else {}
        headers = provider.get("http_headers", {}) if isinstance(provider, dict) else {}
        token = headers.get("X-SecureGateway-Token") if isinstance(headers, dict) else None
        owned = (isinstance(provider, dict)
                 and _gateway_url(provider.get("base_url"), "codex", config)
                 and isinstance(token, str)
                 and (token == config["token"] if config is not None else len(token) >= 32))
        if not owned:
            return current
        _restore_key(value, before, "model_provider", PROVIDER)
        _restore_key(value, before, "forced_login_method", "chatgpt")
        old_providers = before.get("model_providers", {})
        if PROVIDER in old_providers:
            providers[PROVIDER] = old_providers[PROVIDER]
        else:
            del providers[PROVIDER]
        if not providers and "model_providers" not in before:
            value.pop("model_providers", None)
        return tomlkit.dumps(value).encode()
    if path.name == "settings.json":
        value = json.loads(current)
        before = json.loads(original) if original else {}
        if not isinstance(value, dict) or not isinstance(before, dict):
            raise ValueError("Invalid Claude settings; no settings were overwritten.")
        env = value.get("env", {})
        old_env = before.get("env", {})
        if not isinstance(env, dict) or not isinstance(old_env, dict):
            raise ValueError("Invalid Claude environment; no settings were overwritten.")
        headers = env.get("ANTHROPIC_CUSTOM_HEADERS", "")
        if not isinstance(headers, str):
            raise ValueError("Invalid Claude headers; no settings were overwritten.")
        lines = headers.splitlines()
        matching = any(_token_line(line, config) for line in lines)
        url_owned = _gateway_url(env.get("ANTHROPIC_BASE_URL"), "claude", config)
        # Without a config, require both the loopback route and a gateway token
        # before adopting ownership of an otherwise unknown Claude environment.
        if config is None and not (matching and url_owned):
            return current
        changed = False
        if url_owned:
            if "ANTHROPIC_BASE_URL" in old_env:
                env["ANTHROPIC_BASE_URL"] = old_env["ANTHROPIC_BASE_URL"]
            else:
                env.pop("ANTHROPIC_BASE_URL", None)
            changed = True
        if matching:
            remaining = [line for line in lines if not _token_line(line, config)]
            if remaining or "ANTHROPIC_CUSTOM_HEADERS" in old_env:
                env["ANTHROPIC_CUSTOM_HEADERS"] = "\n".join(remaining)
            else:
                env.pop("ANTHROPIC_CUSTOM_HEADERS", None)
            changed = True
        if not changed:
            return current
        if not env and "env" not in before:
            value.pop("env", None)
        return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    return None
