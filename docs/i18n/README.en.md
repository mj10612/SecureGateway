# SecureGateway — English

[English](README.en.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Türkçe](README.tr.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [मराठी](README.mr.md) · [বাংলা](README.bn.md) · [اردو](README.ur.md) · [العربية](README.ar.md) · [తెలుగు](README.te.md) · [简体中文](README.zh.md) · [日本語](README.ja.md)

[README](../../README.md) · [Gateway](../GATEWAY.md) · [MCP / Hook](../LOCAL_INTEGRATION.md) · [Languages](../LANGUAGES.md)

SecureGateway masks supported text and source code locally before sending it to an AI provider. The local Gateway restores replies and tool arguments. Mapping tables stay in local memory or encrypted local snapshots.

## Installation

Prepare Python 3.10 or newer, uv and Git, and sign in to Claude Code or Codex first. Setup changes user-wide provider settings and registers automatic startup while preserving login files. Restart the AI client after installation. For the first test, start a new conversation instead of resuming one created before setup.

```sh
git clone https://github.com/mj10612/SecureGateway.git
cd SecureGateway
uv tool install .
```

If the command is not found, run `uv tool update-shell` and reopen the terminal.

```sh
secure-gateway gateway install --agent both
secure-gateway gateway status
```

## Use

The example below selects English explicitly. For Gateway prose, add natural_language to the existing Gateway configuration with the value en; keep its other settings and restart the Gateway. Numbers in source code are preserved by default. Run gateway diagnostics to inspect aggregate session limits.

```sh
secure-gateway mask "Example document for review" --language en --json-output
secure-gateway gateway diagnostics
```

## Scope and limits

Language support is lexical and masking is heuristic; exact restoration does not prove that anonymized code preserves every behavior. Images and unsupported remote attachments are blocked. The uncommon_words mode bundles ordinary vocabulary only for English and Korean; other languages use conservative content masking. Adding an MCP server alone does not intercept prompts. Restoration belongs in the trusted local application, outside the model context.

## Stop and remove

Stop the daemon before removing its settings. Subscription uninstall removes owned gateway settings while preserving later user edits, including settings synchronized to Orca account homes. Use `gateway uninstall --force-clean` to recover without an installation record; unknown previous values cannot be restored. The gateway requires regular host settings files rather than direct symlinks. See the main guide for upgrade and recovery procedures.

```sh
secure-gateway gateway stop
secure-gateway gateway uninstall
uv tool uninstall secure-gateway
```
