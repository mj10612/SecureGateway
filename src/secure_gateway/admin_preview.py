"""Isolated administrative masking preview endpoint and span alignment (#342)."""

from __future__ import annotations

import concurrent.futures
import json
import logging
from threading import Semaphore
import time
from typing import Any

from secure_gateway.engine.code_parser import LANGUAGE_KEYWORDS
from secure_gateway.engine.natural_languages import SUPPORTED_LANGUAGES
from secure_gateway.gateway import GatewaySession, PrivacyGateway
from secure_gateway.logging_config import log_failure
from secure_gateway.span_derivation import derive_spans

logger = logging.getLogger(__name__)

# Limits per specification
MAX_PREVIEW_BYTES = 256 * 1024  # 256 KiB UTF-8
MAX_CONCURRENT_PREVIEWS = 2
PREVIEW_DEADLINE_SECONDS = 10.0

_PREVIEW_SEMAPHORE = Semaphore(MAX_CONCURRENT_PREVIEWS)
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_PREVIEWS)


def create_preview_session(gateway: PrivacyGateway, natural_language: str = "auto") -> GatewaySession:
    """Create a short-lived, preview-only GatewaySession from a gateway policy snapshot.

    The returned session is never registered in conversation sessions, never writes
    snapshots, and is discarded when the request completes.
    """
    snapshot = gateway.get_policy_snapshot()
    mask_rules = tuple(snapshot["forced_rules"])
    domain_policy = dict(snapshot["domain_policy"])

    session = GatewaySession(
        session=None,
        mapping_limit=gateway.mapping_limit,
        mask_numbers=gateway.mask_numbers,
        natural_language=natural_language if natural_language != "auto" else gateway.natural_language,
        sql_dialect=gateway.sql_dialect,
        max_mapping_bytes=gateway.max_mapping_bytes,
        max_snapshot_bytes=gateway.max_snapshot_bytes,
        prose_mode=gateway.prose_mode,
        common_words=gateway.common_words,
        context_model=gateway.context_model,
        # Preview with the same per-session features as live conversations (#354).
        features=getattr(gateway, "features", None),
        **gateway.restore_limits,
    )
    session.forced_rules = lambda: mask_rules
    session.engine.domain_spans = lambda text: gateway.domain_catalog.spans(text, domain_policy)
    session.domain_policy_version = snapshot["domain_policy_version"]
    return session


def _execute_preview(
    gateway: PrivacyGateway,
    text: str,
    mode: str,
    language: str,
    code_language: str | None,
) -> dict[str, Any]:
    """Execute masking and span alignment in a worker thread."""
    start_time = time.perf_counter()

    # Determine language hint
    if mode == "code":
        code_lang = code_language or language
        selected_lang = code_lang if code_lang in LANGUAGE_KEYWORDS else "auto"
        session = create_preview_session(gateway, natural_language="auto")
        masked = session.mask(text, code=True, language=selected_lang)
    else:
        selected_lang = language if language in SUPPORTED_LANGUAGES else "auto"
        session = create_preview_session(gateway, natural_language=selected_lang)
        masked = session.mask(text, code=False, language="auto")

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    uncertain, spans = derive_spans(session, text, masked)

    snapshot = gateway.get_policy_snapshot()
    unique_aliases = len({s["alias"] for s in spans}) if spans else 0
    replacement_count = len(spans)

    stats = {
        "replacement_count": replacement_count,
        "unique_alias_count": unique_aliases,
        "duration_ms": duration_ms,
        "selected_language": selected_lang,
        "mode": mode,
    }

    # Safe policy summary: never expose forced-rule text
    policy = {
        "forced_rule_count": len(snapshot["forced_rules"]),
        "domains": snapshot["domain_policy"],
        "domain_policy_version": snapshot["domain_policy_version"],
        "manifest_version": snapshot.get("manifest_version", gateway.domain_catalog.version),
    }

    return {
        "masked": masked,
        "spans": spans,
        "stats": stats,
        "policy": policy,
        "uncertain": uncertain,
    }


def handle_admin_preview(handler: Any) -> None:
    """Handle authenticated, bounded POST /admin/api/preview requests."""
    port = handler.server.server_port
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    origin = handler.headers.get("Origin")
    if handler.headers.get("Host") not in hosts or (
        origin is not None and origin not in {"http://" + host for host in hosts}
    ):
        handler.send_body(403, b'{"error":"Local origin required","code":"forbidden_origin"}')
        return

    if not handler.authorized():
        handler.send_body(401, b'{"error":"Unauthorized","code":"unauthorized"}')
        return

    handler.response_headers = {
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; "
        "style-src 'self'; connect-src 'self'; img-src 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    }

    try:
        content_length_header = handler.headers.get("Content-Length", "0")
        if not content_length_header.isdigit():
            handler.send_body(400, b'{"error":"Invalid content length","code":"invalid_request"}')
            return
        length = int(content_length_header)
    except ValueError:
        handler.send_body(400, b'{"error":"Invalid content length","code":"invalid_request"}')
        return

    # Envelope budget: 256 KiB text + up to 4 KiB JSON overhead
    if length > MAX_PREVIEW_BYTES + 4096:
        handler.send_body(413, b'{"error":"Input exceeds 256 KiB limit","code":"oversize"}')
        return

    if not _PREVIEW_SEMAPHORE.acquire(blocking=False):
        handler.send_body(429, b'{"error":"Server busy processing other previews","code":"busy"}')
        return

    try:
        raw = handler.rfile.read(length)
        handler._request_body_consumed = len(raw) == length
        if len(raw) != length:
            handler.send_body(400, b'{"error":"Incomplete body","code":"invalid_request"}')
            return

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            handler.send_body(400, b'{"error":"Malformed JSON body","code":"invalid_request"}')
            return

        if not isinstance(payload, dict) or "text" not in payload:
            handler.send_body(400, b'{"error":"Invalid payload; text required","code":"invalid_request"}')
            return

        text = payload["text"]
        if not isinstance(text, str):
            handler.send_body(400, b'{"error":"text must be a string","code":"invalid_request"}')
            return

        if len(text.encode("utf-8")) > MAX_PREVIEW_BYTES:
            handler.send_body(413, b'{"error":"Input exceeds 256 KiB limit","code":"oversize"}')
            return

        mode = payload.get("mode", "prose")
        if mode not in {"prose", "code"}:
            handler.send_body(400, b'{"error":"mode must be prose or code","code":"invalid_request"}')
            return

        language = payload.get("language", "auto")
        if not isinstance(language, str):
            handler.send_body(400, b'{"error":"language must be a string","code":"invalid_request"}')
            return

        code_language = payload.get("code_language")
        if code_language is not None and not isinstance(code_language, str):
            handler.send_body(400, b'{"error":"code_language must be a string","code":"invalid_request"}')
            return

        future = _EXECUTOR.submit(_execute_preview, handler.server, text, mode, language, code_language)
        try:
            result = future.result(timeout=PREVIEW_DEADLINE_SECONDS)
        except concurrent.futures.TimeoutError:
            handler.send_body(504, b'{"error":"Processing deadline exceeded","code":"deadline_exceeded"}')
            return
        except ValueError as exc:
            log_failure(logger, "preview_rejected", exc)
            handler.send_body(400, b'{"error":"Processing rejected for input budget or structure","code":"invalid_request"}')
            return
        except Exception as exc:
            log_failure(logger, "preview_processing_failed", exc)
            handler.send_body(500, b'{"error":"Internal error processing preview","code":"internal_error"}')
            return

        handler.send_body(200, json.dumps(result, ensure_ascii=False).encode("utf-8"))
    finally:
        _PREVIEW_SEMAPHORE.release()
