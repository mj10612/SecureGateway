"""MCP utilities. Confidential pipelines must mask before a provider request."""

from __future__ import annotations

import atexit
from functools import wraps
import json
import uuid

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from secure_gateway import __version__
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.engine.natural_languages import canonical_language, SUPPORTED_LANGUAGES
from secure_gateway.engine.code_parser import LANGUAGE_KEYWORDS
from secure_gateway.models import MaskMode, SurrogateStrategy
from secure_gateway.session import SessionVault

app = MCPServer(
    name="SecureGateway",
    version=__version__,
    instructions=(
        "Local masking utilities. Model-invoked tool arguments are already visible to the provider. "
        "Use the trusted client-side LocalPrivacyClient before sending confidential input. "
        "Restoration is available only in the local Python API/CLI, never as an MCP tool."
    ),
)
engine = MaskingEngine()
vault = SessionVault()
atexit.register(vault.close)


def _tool_errors(fn):
    @wraps(fn)
    def guarded(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as exc:
            raise ToolError(str(exc)) from None

    return guarded


@app.tool()
@_tool_errors
def mask_text(
    text: str,
    session_id: str = "",
    mode: str = "content_words",
    strategy: str = "bracket",
    language: str = "auto",
    sensitive_terms: list[str] | None = None,
    custom_preserve: list[str] | None = None,
    code_language: str = "auto",
    mask_numbers: bool = False,
    sql_dialect: str = "sqlite",
    common_vocabulary: list[str] | None = None,
) -> str:
    """Mask text. Tool arguments are provider-visible; pre-mask confidential data locally.

    mode: content_words, entities_only, code_aware, aggressive, uncommon_words.
    strategy: bracket, unicode, pseudoword, hash. language: auto or a supported natural-language tag.
    sensitive_terms forces explicit words/phrases; custom_preserve opts terms out of masking.
    common_vocabulary extends the local ordinary-word list in uncommon_words mode.
    code_language selects a code lexer when mode=code_aware.
    mask_numbers=True masks code numbers; the default preserves them.
    """
    mask_mode, strat = MaskMode(mode), SurrogateStrategy(strategy)
    language = canonical_language(language)
    session = vault.get_or_create(session_id, mask_mode, strat)
    with session.operation():
        result = engine.mask_text(
            text,
            session.session_id,
            session.generator,
            session.forward_store,
            session.reverse_store,
            mode=mask_mode,
            strategy=strat,
            language=language,
            sensitive_terms=set(sensitive_terms or []),
            custom_preserve=set(custom_preserve or []),
            common_vocabulary=set(common_vocabulary or []),
            code_language=code_language,
            mask_numbers=mask_numbers,
            sql_dialect=sql_dialect,
        )
        session.mode = mask_mode
        session.total_mask_calls += 1
        return result.model_dump_json(indent=2)


@_tool_errors
def unmask_text(
    masked_text: str,
    session_id: str = "",
    strategy: str | None = None,
    normalize_particles: bool = False,
    strict: bool = False,
) -> str:
    """Trusted local API only. Deliberately NOT registered as a model-invoked tool."""
    session = vault.get_session(session_id)
    if session is None:
        return json.dumps(
            {
                "error": f"Session '{session_id}' not found or expired.",
                "unmasked_text": masked_text,
                "restored_tokens_count": 0,
            }
        )
    with session.operation():
        strat = (
            SurrogateStrategy(strategy) if strategy is not None else session.strategy
        )
        if strat != session.strategy:
            raise ValueError("Unmask strategy must match the session's strategy.")
        result = engine.unmask(
            masked_text,
            session.session_id,
            session.reverse_store,
            strat,
            normalize_particles,
            strict,
        )
        session.total_unmask_calls += 1
        return result.model_dump_json(indent=2)


@app.tool()
@_tool_errors
def mask_code(
    code: str, session_id: str = "", strategy: str = "bracket", language: str = "auto",
    mask_numbers: bool = False, sql_dialect: str = "sqlite"
) -> str:
    """Mask identifiers/literals. Set language explicitly when auto detection is ambiguous.

    Numbers are preserved by default; mask_numbers=True opts into numeric masking.
    Supported language profiles are listed in privacy://policies and docs/LANGUAGES.md.
    SQL dialect: standard (lowercase folding), postgresql, sqlite.
    Generated code is a review representation; it is not executable anonymization.
    """
    strat = SurrogateStrategy(strategy)
    session = vault.get_or_create(session_id, MaskMode.CODE_AWARE, strat)
    with session.operation():
        result = engine.mask_code(
            code,
            session.session_id,
            session.generator,
            session.forward_store,
            session.reverse_store,
            strat,
            language,
            mask_numbers=mask_numbers,
            sql_dialect=sql_dialect,
        )
        session.mode = MaskMode.CODE_AWARE
        session.total_mask_calls += 1
        return result.model_dump_json(indent=2)


def unmask_code(
    masked_code: str,
    session_id: str = "",
    strategy: str | None = None,
    strict: bool = False,
) -> str:
    """Trusted local restoration; no raw originals are returned through MCP."""
    return unmask_text(masked_code, session_id, strategy, strict=strict)


@app.tool()
@_tool_errors
def create_privacy_session(
    session_id: str = "",
    mode: str = "content_words",
    strategy: str = "bracket",
    ttl_seconds: int = 3600,
) -> str:
    """Create a new session. Duplicate IDs are errors; TTL is 1..86400 seconds."""
    session = vault.create(
        session_id.strip() or f"sess_{uuid.uuid4().hex}",
        MaskMode(mode),
        SurrogateStrategy(strategy),
        ttl_seconds,
    )
    return json.dumps(
        {
            "status": "created",
            "session_id": session.session_id,
            "mode": session.mode.value,
            "strategy": session.strategy.value,
            "ttl_seconds": session.ttl_seconds,
        }
    )


@app.tool()
@_tool_errors
def get_session_stats(session_id: str = "") -> str:
    """Sanitized metrics. mode means the most recent masking policy."""
    session = vault.get_session(session_id)
    if session is None:
        return json.dumps({"error": f"Session '{session_id}' not found."})
    return session.get_stats().model_dump_json(indent=2)


@app.tool()
def clear_privacy_session(session_id: str = "") -> str:
    """Wait for active operations, invalidate the session and release mapping references."""
    cleared = vault.clear_session(session_id)
    return json.dumps(
        {
            "session_id": session_id,
            "purged": cleared,
            "status": "mapping references cleared" if cleared else "session not found",
        }
    )


@app.prompt()
def privacy_preserving_assistant(task_description: str = "") -> str:
    """Instructions for a payload already masked by the trusted local client."""
    return (
        "SecureGateway: process the already-masked payload. Preserve every surrogate exactly, "
        "including brackets and delimiters. Do not guess hidden values. Restoration happens "
        "outside the model context in the trusted local client. Task: "
        + task_description
    )


@app.prompt()
def secure_code_assistant(goal: str = "refactor") -> str:
    return (
        "Review the masked source representation. Keep smcp_ID_n identifiers, "
        "literal placeholders and numeric nonce constants unchanged. Numeric constants are opaque; "
        "do not infer execution results. Goal: " + goal
    )


@app.resource("privacy://policies")
def get_privacy_policies() -> str:
    return json.dumps(
        {
            "modes": [m.value for m in MaskMode],
            "strategies": [s.value for s in SurrogateStrategy],
            "languages": sorted(SUPPORTED_LANGUAGES),
            "code_languages": sorted(LANGUAGE_KEYWORDS),
            "confidentiality": "Only pre-provider client-side masking protects against the provider.",
            "detection": "Heuristic; use sensitive_terms or aggressive for unrecognized data.",
            "metrics": "masked_ratio is an occurrence ratio, not entropy or proof of privacy.",
        }
    )


@app.resource("privacy://status")
def get_privacy_status() -> str:
    return json.dumps(
        {
            "server": "SecureGateway",
            "version": __version__,
            "active_sessions": vault.active_count,
            "protocol": "Model Context Protocol (MCP)",
        }
    )
