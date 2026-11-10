"""Loopback subscription proxy. CLI-owned OAuth is forwarded, never loaded from disk.

Only inference endpoints are proxied. Unknown/binary payloads fail closed. SSE
text is incremental; incomplete aliases and tool JSON retain bounded buffers.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager, nullcontext
from contextvars import ContextVar
from queue import Empty, Full, Queue
from collections import OrderedDict, deque
from copy import deepcopy
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
import math
import http.client
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import time
import unicodedata
from threading import Condition, Event, Lock, RLock, Thread
from typing import Any, Callable, Iterator
from secure_gateway.logging_config import get_logger, log_failure
from secure_gateway import __version__
from secure_gateway.context_model import ContextModel, load_context_model, MAX_CONTEXT_CHARS
import urllib.error
import urllib.request
import urllib.parse

from secure_gateway.engine.masking_engine import MaskingEngine, NumericLiteralConflict
from secure_gateway.engine.strategies import mapping_key
from secure_gateway.engine.natural_languages import canonical_language, detect_natural_language
from secure_gateway.engine.code_parser import LANGUAGE_KEYWORDS, ALIASES
from secure_gateway.encrypted_session import (
    SessionExpiredError,
    SnapshotEncryption,
    decrypt_snapshot_bytes,
    load_session,
    save_session,
)
from secure_gateway.hooks import _atomic_json
from secure_gateway.gateway_validation import MODEL_ID_PATTERN, validate_request
from secure_gateway.gateway_validation import validate_cache_control
from secure_gateway.engine.grammar_en import CLOSED_CLASS_WORDS
from secure_gateway.gateway_source import looks_like_source, markdown_code_spans
from secure_gateway.gateway_catalog import fetch_catalog
from secure_gateway.gateway_audit import AuditMaintenanceError, AuditStore, anonymous_ref
from secure_gateway.gateway_admin import handle_admin, save_mask_rules
from secure_gateway.gateway_vocabulary import select_gateway_language, domain_terms, DISCOURSE_WORDS, ENGLISH_NAMES, discourse_capital_positions
from secure_gateway.gateway_name_vocabulary import NAME_WORDS
from secure_gateway.gateway_public_vocabulary import ordinary_words, lexicon
from secure_gateway.gateway_morphology import is_ordinary_form
from secure_gateway.gateway_task_operators import operator_words, operator_capital_positions
from secure_gateway.mapping_budget import DEFAULT_MAPPING_BYTES, DEFAULT_SNAPSHOT_BYTES, check_mapping_budget, positive_budget, snapshot_budget, record_mapping
from secure_gateway.models import MaskMode, SurrogateStrategy, TokenMapping, TokenType
from secure_gateway.session import PrivacySession
from secure_gateway.gateway_stream import relay_stream
from secure_gateway.gateway_errors import GatewayRequestError, public_request_error
from secure_gateway.domain_dictionaries import (
    catalog as domain_catalog,
    DomainCatalog,
    DEFAULTS as DOMAIN_DEFAULTS,
    protect_chunks,
)

# Maximum request/stream payload size in bytes (16 MiB). Bounds memory use and
# rejects oversized JSON/SSE payloads before deeper processing; not user-configurable.
MAX_REQUEST_BYTES = 16 * 1024 * 1024
LIMIT = MAX_REQUEST_BYTES
# Maximum retained conversation snapshots before eviction; bounds in-memory state
# (each session holds mappings/reasoning provenance). Not user-configurable.
MAX_CONVERSATION_SESSIONS = 256
_LOGGER = get_logger(__name__)
_DIAGNOSTIC_LOGGER = logging.getLogger(__name__ + ".diagnostic")
_DIAGNOSTIC_LIMIT = 2**31 - 1  # SQLite integer upper bound for diagnostic counters.
_DIAGNOSTIC_CATEGORIES = (
    "snapshot_scan_io", "snapshot_cleanup_io", "snapshot_preserved",
    "snapshot_load_failed", "snapshot_recovered", "snapshot_recovery_io",
    "upstream_error_body", "upstream_error_format", "upstream_error_close",
    "upstream_error_stream_close",
    "log_delivery_failed", "catalog_preload_failed",
)


class _DiagnosticStreamHandler(logging.StreamHandler):
    def handleError(self, record):
        callback = getattr(record, "diagnostic_failure", None)
        if callback is not None:
            callback()


class _DiagnosticFileHandler(logging.FileHandler):
    def handleError(self, record):
        callback = getattr(record, "diagnostic_failure", None)
        if callback is not None:
            callback()

    def emit(self, record):
        try:
            super().emit(record)
        except Exception:
            self.handleError(record)


class _DiagnosticQueueHandler(logging.Handler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        try:
            self.queue.put_nowait(record)
        except Full:
            callback = getattr(record, "diagnostic_failure", None)
            if callback is not None:
                callback()


@contextmanager
def diagnostic_logging(*, stream=None, filename=None):
    """Install an isolated diagnostic destination while a server process runs."""
    destination = (_DiagnosticFileHandler(filename, delay=True) if filename is not None
                   else _DiagnosticStreamHandler(stream))
    queue: Queue[logging.LogRecord] = Queue(maxsize=1024)
    handler = _DiagnosticQueueHandler(queue)
    stopping = Event()

    def deliver():
        try:
            while not stopping.is_set() or not queue.empty():
                try:
                    record = queue.get(timeout=.1)
                except Empty:
                    continue
                destination.handle(record)
        finally:
            try:
                destination.close()
            except Exception:
                pass

    thread = Thread(target=deliver, name="gateway-diagnostics", daemon=True)
    previous = _DIAGNOSTIC_LOGGER.propagate
    _DIAGNOSTIC_LOGGER.propagate = False
    _DIAGNOSTIC_LOGGER.addHandler(handler)
    thread.start()
    try:
        yield
    finally:
        _DIAGNOSTIC_LOGGER.removeHandler(handler)
        _DIAGNOSTIC_LOGGER.propagate = previous
        handler.close()
        stopping.set()
        thread.join(timeout=.2)


def _warn_diagnostic(category, on_failure=None):
    """Optional logging must not change the error response or expose its cause."""
    try:
        logger = _DIAGNOSTIC_LOGGER if _DIAGNOSTIC_LOGGER.handlers else _LOGGER
        logger.warning("Gateway operational event: %s; inspect authenticated diagnostics.", category,
                       extra={"diagnostic_failure": on_failure})
    except Exception:
        return False
    return True


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON number: {value}")


def _validate_finite_json_numbers(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("JSON numbers must be finite.")
    if isinstance(value, dict):
        for item in value.values():
            _validate_finite_json_numbers(item)
    elif isinstance(value, list):
        for item in value:
            _validate_finite_json_numbers(item)
    return value


def strict_json_loads(data: str | bytes) -> Any:
    """Load interoperable JSON, rejecting constants and float overflow."""
    return _validate_finite_json_numbers(
        json.loads(data, parse_constant=_reject_json_constant)
    )


def strict_json_dumps(value: Any, **kwargs: Any) -> str:
    """Serialize JSON without emitting JavaScript-only numeric constants."""
    return json.dumps(value, allow_nan=False, **kwargs)


JSON_SCHEMA_DIALECTS = {
    "https://json-schema.org/draft/2020-12/schema",
    "https://json-schema.org/draft/2019-09/schema",
    "https://json-schema.org/schema",
    "https://json-schema.org/schema#",
    "http://json-schema.org/schema#",
    "http://json-schema.org/draft-07/schema#",
    "http://json-schema.org/draft-06/schema#",
    "http://json-schema.org/draft-04/schema#",
    "http://json-schema.org/draft-03/schema#",
    "https://spec.openapis.org/oas/3.1/dialect/base",
}
EXEC_GRAMMAR = r"""
start: pragma_source | plain_source
pragma_source: PRAGMA_LINE NEWLINE SOURCE
plain_source: SOURCE

PRAGMA_LINE: /[ \t]*\/\/ @exec:[^\r\n]*/
NEWLINE: /\r?\n/
SOURCE: /[\s\S]+/
"""
# Pinned OpenAI public apply_patch grammar, with/without environment selection.
PATCH_GRAMMAR_HASHES = {
    "50b06e74592ca36baf0a0804a36d76aef1847b251c7b5b5bfd9bc81ec7794023",
    "1f1bb6528b7ab190a5542bc710053077515f5f800cd58e77f141820566ca4f20",
}
TASK_WORDS = {
    "review",
    "inspect",
    "analyze",
    "explain",
    "fix",
    "implement",
    "read",
    "search",
    "find",
    "summarize",
    "compare",
    "refactor",
    "test",
    "check",
    "show",
    "repeat",
    "reply",
    "exactly",
    "identifier",
    "function",
    "code",
    "file",
    "directory",
    "bug",
    "security",
    "syntax",
    "error",
    "issue",
    "result",
    "please",
    "검토",
    "검토해줘",
    "봐줘",
    "설명",
    "설명해줘",
    "고쳐줘",
    "함수",
    "코드",
    "파일",
    "보안",
    "오류",
    "수정",
    "분석",
    "분석해줘",
    "읽어줘",
    "보여줘",
    "반환",
    "값",
    "그대로",
    # Common task language is public vocabulary, not a general allowlist for
    # identifiers. Exact forms avoid preserving arbitrary private compounds.
    "삭제", "삭제해", "삭제해줘", "삭제해주세요", "삭제해 주세요", "삭제하세요",
    "제거", "제거해", "제거해줘", "제거해주세요", "지워줘", "지워주세요",
    "찾아", "찾아서", "찾아줘", "찾아주세요", "찾을", "찾기", "검색해줘", "검색해주세요",
    "수정해", "수정해줘", "수정해주세요", "수정하세요", "변경해줘", "변경해주세요",
    "만들어", "만들어줘", "만들어주세요", "작성해줘", "작성해주세요",
    "확인해", "확인해줘", "확인해주세요", "알려줘", "알려주세요",
    "설치해줘", "설치해주세요", "실행해줘", "실행해주세요",
    "줄", "수", "있어", "있나요", "있을까", "가능해", "가능할까",
    "리파지토리", "리파지토리를", "리포지토리", "리포지토리를",
    "저장소", "저장소를", "파일을", "폴더를", "프로그램을",
    "github", "github에서",
    "delete", "remove", "create", "install", "uninstall", "run", "update",
    "repository", "repositories", "repo", "folder", "files",
}
SKILL_TASK_WORDS = {"skill", "instructions", "using", "follow"}
TASK_WORDS_BY_LANGUAGE = {
    "es": "revisa revisar busca buscar elimina explica",
    "fr": "vérifie vérifier cherche chercher supprime explique",
    "pt": "verifique verificar procure pesquise exclua explique",
    "de": "prüfe prüfen suche suchen lösche erkläre",
    "id": "periksa cari hapus jelaskan",
    "tr": "kontrol et ara sil açıkla",
    "ru": "проверь проверить найди удали объясни",
    "hi": "जाँचें जांचें खोजें हटाएं समझाएं",
    "mr": "तपासा शोधा काढा समजावून सांगा",
    "bn": "পরীক্ষা করুন খুঁজুন মুছুন ব্যাখ্যা",
    "ur": "جانچ کریں تلاش حذف وضاحت",
    "te": "తనిఖీ చేయండి వెతకండి తొలగించండి వివరించండి",
    "ar": "تحقق ابحث احذف اشرح",
    "zh": "检查 檢查 查找 搜索 删除 刪除 解释 解釋",
    "ja": "確認 検索 探す 削除 説明",
}
PRIVACY_INSTRUCTION = (
    "This context was masked locally. Names beginning private_symbol_ and numeric aliases "
    "are opaque references. Their presence alone does not make the surrounding request "
    "unreadable. Treat each supplied alias as a "
    "stable symbolic label: repeated labels refer to the same thing. Understand and "
    "carry out the visible request using its actions, relationships, order, negation, "
    "conditions and requested output format. You can summarize, compare or plan around "
    "opaque references without knowing their originals. Do not refuse or ask for originals "
    "merely because references are masked. Keep supplied aliases exactly unchanged in "
    "answers and tool arguments; the local host restores them. Never invent aliases, "
    "guess originals or assume a hidden label's type or meaning. Numeric aliases are "
    "labels, not the original magnitudes: do not calculate using their displayed digits. Use public names for "
    "new identifiers. If a particular answer truly requires a hidden fact, identify only "
    "that limitation and still complete the parts supported by visible context. "
    "Normal tool permissions and approval requirements still apply.\n"
)
PUBLIC_CLAUDE_IDENTITY = "You are Claude Code, Anthropic's official CLI for Claude."
PUBLIC_CLAUDE_IDENTITIES = (
    PUBLIC_CLAUDE_IDENTITY,
    "You are a Claude agent, built on Anthropic's Claude Agent SDK.",
)
CLAUDE_ATTRIBUTION_PREFIX = "x-anthropic-billing-header:"
# This positional protocol block is consumed by Anthropic before model inference.
# Pin its observed fields rather than passing arbitrary system text through.
CLAUDE_ATTRIBUTION = re.compile(
    r"x-anthropic-billing-header: cc_version=[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}"
    r"(?:\.[0-9a-f]{3})?; cc_entrypoint=(?:cli|sdk-cli);"
    r"(?: cch=[0-9a-f]{6,64};)?[ \t]*"
)
TOOL_DESCRIPTIONS = {
    "Read": "Read a local file using file_path.",
    "Bash": "Run a local shell command using command.",
    "PowerShell": "Run a local PowerShell command.",
    "exec_command": "Run a local shell command using cmd; return output and session_id.",
    "write_stdin": "Send chars to a running session_id, or poll for output.",
    "Write": "Write content into a local file using file_path.",
    "Edit": "Replace old_string with new_string in file_path.",
    "Grep": "Search local file contents for pattern.",
    "Glob": "Find local files matching pattern.",
    "apply_patch": "Apply a patch to local files using the supplied patch grammar.",
}
UPSTREAMS = {
    "claude": "https://api.anthropic.com",
    "codex": "https://chatgpt.com/backend-api/codex",
}
# Explicit API-key modes. These are never enabled implicitly and never fall
# back to a subscription token; see docs/COMPATIBILITY.md and GATEWAY.md.
API_UPSTREAMS = {
    "xai": "https://api.x.ai",
}
API_AUTH_PREFIXES = {
    "xai": "Bearer xai-",
}
PROTOCOL = {
    "type",
    "role",
    "id",
    "call_id",
    "tool_use_id",
    "tool_call_id",
    "phase",
    "model",
    "status",
    "stop_reason",
    "object",
    "effort",
    "verbosity",
    "syntax",
}
# JSON Schema keywords whose direct child names are aliased by walk().
# A local `$ref` pointer keeps array indexes and all other keywords intact so
# the masked reference still resolves inside the masked schema.
SCHEMA_NAME_KEYWORDS = {
    "properties",
    "$defs",
    "definitions",
    "dependentSchemas",
    "dependentRequired",
    "dependencies",
}
# JSON data positions where protocol/schema exceptions must not apply:
# enum/const/default/examples hold arbitrary data, not envelope metadata.
DATA_KEYWORDS = {"enum", "const", "default", "examples"}
SCHEMA_TYPES = {"object", "string", "number", "integer", "array", "boolean", "null"}
TOOL_NAMES = {
    "Bash",
    "PowerShell",
    "Read",
    "Edit",
    "Write",
    "Grep",
    "Glob",
    "MultiEdit",
    "TodoWrite",
    "Task",
    "Agent",
    "ToolSearch",
    "WebFetch",
    "WebSearch",
    "exec_command",
    "write_stdin",
    "apply_patch",
    "update_plan",
    "request_user_input",
    "functions",
    "exec",
    "parallel",
    "list_mcp_resources",
    "list_mcp_resource_templates",
    "read_mcp_resource",
    "view_image",
    "spawn_agent",
    "send_input",
    "wait",
    "close_agent",
}
TOP_FIELDS = {
    "model",
    "messages",
    "system",
    "input",
    "instructions",
    "tools",
    "tool_choice",
    "parallel_tool_calls",
    "reasoning",
    "stream",
    "store",
    "max_output_tokens",
    "max_tokens",
    "include",
    "metadata",
    "text",
    "prompt_cache_key",
    "safety_identifier",
    "service_tier",
    "temperature",
    "top_p",
    "top_k",
    "truncation",
    "background",
    "stop_sequences",
    "thinking",
    "output_config",
    "context_management",
    "client_metadata",
    "safeguards",
}
BLOCKED_TYPES = {
    "image",
    "document",
    "input_image",
    "input_file",
    "input_audio",
    "computer",
    "computer_20250124",
    "computer_20251124",
}
ARGUMENT_KEYS = {
    "cmd",
    "command",
    "path",
    "file_path",
    "filePath",
    "content",
    "text",
    "old_string",
    "new_string",
    "pattern",
    "query",
    "yield_time_ms",
    "max_output_tokens",
    "session_id",
    "chars",
    "workdir",
    "timeout",
    "description",
    "shell",
    "login",
    "tty",
    "justification",
    "sandbox_permissions",
    "prefix_rule",
    "input",
    "patch",
}


def validate_api_options(payload, dialect):
    """Only public, typed API controls may bypass text masking."""
    controls = {
        "model",
        "stream",
        "store",
        "parallel_tool_calls",
        "max_output_tokens",
        "max_tokens",
        "max_completion_tokens",
        "temperature",
        "top_p",
        "background",
        "truncation",
        "reasoning",
        "include",
        "service_tier",
        "stream_options",
        "metadata",
        "client_metadata",
        "reasoning_effort",
        "prompt_cache_key",
        "safety_identifier",
    }
    content = {
        "input",
        "instructions",
        "messages",
        "tools",
        "tool_choice",
        "text",
        "stop",
        "response_format",
    }
    if set(payload) - controls - content:
        raise ValueError("Unsupported API controls.")
    for key in {
        "stream",
        "store",
        "parallel_tool_calls",
        "background",
    } & payload.keys():
        if not isinstance(payload[key], bool):
            raise ValueError("API boolean controls must be booleans.")
    for key in {
        "max_output_tokens",
        "max_tokens",
        "max_completion_tokens",
    } & payload.keys():
        if type(payload[key]) is not int or payload[key] < 1:
            raise ValueError("API token limits must be positive integers.")
    for key in {"temperature", "top_p"} & payload.keys():
        if type(payload[key]) not in {int, float} or not 0 <= payload[key] <= (
            2 if key == "temperature" else 1
        ):
            raise ValueError("Invalid API sampling control.")
    for key, allowed in {
        "truncation": {"disabled"},
        "service_tier": {"auto", "default", "flex", "priority"},
    }.items():
        if key in payload and (
            not isinstance(payload[key], str) or payload[key] not in allowed
        ):
            raise ValueError("Unsupported API control enum.")
    if "model" in payload and (
        not isinstance(payload["model"], str)
        or not MODEL_ID_PATTERN.fullmatch(payload["model"])
    ):
        raise ValueError("Invalid model ID.")
    if "reasoning" in payload:
        reasoning = payload["reasoning"]
        enums = {
            "effort": {"none", "minimal", "low", "medium", "high", "xhigh"},
            "summary": {"auto", "concise", "detailed"},
        }
        if dialect == "responses":
            enums["context"] = {"auto", "current_turn", "all_turns"}
        if (
            not isinstance(reasoning, dict)
            or set(reasoning) - enums.keys()
            or any(
                not isinstance(value, str) or value not in enums[key]
                for key, value in reasoning.items()
            )
        ):
            raise ValueError("Unsupported reasoning controls.")
    if "include" in payload and (
        not isinstance(payload["include"], list)
        or any(item != "reasoning.encrypted_content" for item in payload["include"])
    ):
        raise ValueError("Unsupported API include fields.")
    if "stop" in payload and not (
        isinstance(payload["stop"], str)
        or isinstance(payload["stop"], list)
        and 1 <= len(payload["stop"]) <= 4
        and all(isinstance(item, str) for item in payload["stop"])
    ):
        raise ValueError("Stop sequences must be text or a list of text.")
    if dialect == "chat_completions" and set(payload) & {
        "input",
        "instructions",
        "text",
        "max_output_tokens",
        "include",
    }:
        raise ValueError("Responses controls are unsupported in Chat Completions.")
    if dialect == "responses" and set(payload) & {
        "messages",
        "stop",
        "max_completion_tokens",
        "max_tokens",
        "stream_options",
        "reasoning_effort",
        "response_format",
    }:
        raise ValueError("Chat controls are unsupported in Responses.")


_private_prose: ContextVar[bool] = ContextVar("private_gateway_prose", default=False)
# Issue #323: while masking a prose fragment, a single-word generic domain span
# that is an ordinary public word is not re-masked (see GatewaySession._mask_prose).
_public_domain_span: ContextVar[Callable[[str], bool] | None] = ContextVar("public_domain_span", default=None)
_STATIC_NAMES = {language: frozenset(unicodedata.normalize("NFC", word).casefold() for word in words)
                 for language, words in NAME_WORDS.items()}
_EN_NAME_SUFFIXES = ("'s", "’s", "es", "s", "ing", "ed")
_AR_PREFIXES = ("وال", "بال", "لل", "ال", "و", "ف", "ب", "ل", "ك")
# Apostrophes are not boundaries: French/Italian elision (d'Zorvexa) precedes names.
_SENTENCE_BOUNDARY = set(".!?。！？:;\n\"“”‘([{*•-")


def _static_name_hit(term: str, language: str) -> bool:
    """A match of the static NAME_WORDS/ENGLISH_NAMES lists, including their affixed forms."""
    names = _STATIC_NAMES.get(language, frozenset())
    if language == "en":
        names = names | ENGLISH_NAMES
    key = unicodedata.normalize("NFC", term).casefold()
    if key in names:
        return True
    if language == "en" and any(key.endswith(suffix) and key[:-len(suffix)] in names for suffix in _EN_NAME_SUFFIXES):
        return True
    return language == "ar" and any(key.startswith(prefix) and key[len(prefix):] in names for prefix in _AR_PREFIXES)


def _public_root(root: str, language: str, vocabulary) -> bool:
    """Ordinary frequency word or typed predicate; name evidence never vetoes it."""
    if root in vocabulary.words or root in vocabulary.predicates:
        return True
    if language == "ko" and root.endswith("다"):
        if root[:-1] in vocabulary.words:
            return True
        return (root.endswith(("하다", "되다")) and root[-2:] in vocabulary.predicates
                and root[:-2] in vocabulary.words)
    return False


def _public_surface(term: str, language: str, vocabulary) -> bool:
    key = unicodedata.normalize("NFC", term).casefold()
    if key in vocabulary.words or key in vocabulary.predicates:
        return True
    return is_ordinary_form(term, language, lambda root: _public_root(root, language, vocabulary), lambda _: False)


def _identifier_shaped(word: str) -> bool:
    """Definite identifier shape: snake_case, letters mixed with digits, inner capitals, acronyms.

    ``private_method``, ``account37591``, camelCase/PascalCase with an inner capital
    (``KeplerQzx``) and all-capital words of at least two letters that are not public
    vocabulary are treated as identifiers.
    """
    if "_" in word.strip("_") or (any(char.isdigit() for char in word) and any(char.isalpha() for char in word)):
        return True
    cased = [char for char in word if char.isalpha() and char.upper() != char.lower()]
    if len(cased) < 2:
        return False
    if all(char.isupper() for char in cased):
        return True
    return any(char.isupper() for char in word[1:])


def _identifier_context(text: str, start: int, end: int) -> bool:
    """A word that is part of a path, dotted name, handle, key=value pair or header/flag key.

    Public spellings in such positions (``src/radar/config.yaml``, ``@john``,
    ``mode=fast``, ``x-billing-header:``, ``--dry-run``) are source/tool identifiers,
    not prose, and remain masked. Ordinary hyphenated prose (``well-known``) is kept.
    """
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    if before == "=" or after == "=":
        return True
    # Maximal hyphen-joined run around the word (letters, marks, digits and '-').
    left, right = start, end
    while left > 0 and (text[left - 1] == "-" or text[left - 1].isalnum()
                        or unicodedata.category(text[left - 1]).startswith("M")):
        left -= 1
    while right < len(text) and (text[right] == "-" or text[right].isalnum()
                                 or unicodedata.category(text[right]).startswith("M")):
        right += 1
    run = text[left:right]
    if "-" in run.strip("-") and right < len(text) and text[right] in ":=":
        return True
    if text[max(0, left - 2):left] == "--" or run.startswith("--"):
        return True
    if end - start < 2:  # single letters (e.g. "e.g.") are not identifiers by themselves
        return False
    if (before and before in "/\\_@") or (after and after in "/\\_"):
        return True
    if after == "." and end + 1 < len(text) and text[end + 1].isalnum():
        return True
    return before == "." and start >= 2 and text[start - 2].isalnum() and not text[start - 2].isspace()


def _name_fallback(text: str, start: int, word: str, language: str) -> bool:
    """Narrow name fallback (issue #323 policy, documented in docs/research/issue323-public-policy.md).

    Only a non-public, Title-case word in a cased script that is not at a sentence/line/list
    start is treated as a probable proper name. German is excluded because ordinary nouns
    are capitalised; case-free scripts never trigger it. Common names that are public
    vocabulary never reach this rule.
    """
    if language == "de" or len(word) < 2 or not word[0].isupper():
        return False
    rest = [char for char in word[1:] if char.isalpha() and char.upper() != char.lower()]
    if not rest or not all(char.islower() for char in rest):
        return False
    prefix = text[:start].rstrip(" \t")
    return bool(prefix) and prefix[-1] not in _SENTENCE_BOUNDARY


class SharedEngine(MaskingEngine):
    """One alias for an original in prompts, code, paths and tool results."""
    domain_spans: Callable | None = None
    _domain_depth = 0

    def _chunks(self, text, terms, language="en", literal_aliases=None):
        if self._domain_depth or self.domain_spans is None:
            return super()._chunks(text, terms, language, literal_aliases)
        self._domain_depth += 1
        try:
            chunks = super()._chunks(text, terms, language, literal_aliases)
            spans = self.domain_spans(text)
            public = _public_domain_span.get()
            if public is not None and spans:
                # A generic dictionary entry must not re-mask an ordinary public
                # prose word; explicit/private rules are applied separately.
                spans = [(start, end) for start, end in spans if not public(text[start:end])]
            return protect_chunks(text, chunks, spans)
        finally:
            self._domain_depth -= 1

    def __init__(self, mapping_limit=100_000, **restore_limits):
        super().__init__(**restore_limits)
        self.mapping_limit = mapping_limit

    def mask_text(self, *args, private_context=False, **kwargs):
        """Handle mask text."""
        token = _private_prose.set(private_context)
        try:
            return super().mask_text(*args, **kwargs)
        finally:
            _private_prose.reset(token)

    def _get_or_create_surrogate(
        self,
        original_token,
        token_type,
        generator,
        mapping_store,
        reverse_store,
        code=False,
        lookup_key=None,
    ):
        with generator.operation():
            source_reference = code or token_type == TokenType.LITERAL or _private_prose.get()
            kind = (
                TokenType.NUMBER
                if token_type == TokenType.NUMBER
                else TokenType.IDENTIFIER
            )
            key = lookup_key or mapping_key(original_token, kind, code=True)
            if key in mapping_store:
                if kind == TokenType.NUMBER and mapping_store[key].surrogate == original_token:
                    raise NumericLiteralConflict("Numeric literal conflicts with a preserved number; use a new session.")
                if source_reference:
                    if mapping_store[key].source_reference is not True:
                        self.cache_epoch = getattr(self, "cache_epoch", 0) + 1
                    mapping_store[key]._mark_source_reference()
                mapping_store[key].occurrence_count += 1
                if code and token_type == TokenType.LITERAL:
                    if not mapping_store[key].code_literal:
                        self.cache_epoch = getattr(self, "cache_epoch", 0) + 1
                    mapping_store[key]._mark_code_literal()
                return mapping_store[key].surrogate
            if len(mapping_store) >= min(self.mapping_limit, generator.max_mappings):
                raise ValueError(
                    "Mapping limit reached; reset the gateway and start a new conversation."
                )
            check_mapping_budget(mapping_store, generator, key, original_token)
            while True:
                surrogate = generator.generate(kind, original_token, code=True)
                if kind == TokenType.NUMBER:
                    break
                surrogate = surrogate.replace("smcp_ID_", "private_symbol_", 1)
                if (
                    surrogate != original_token
                    and surrogate not in generator.used_surrogates
                ):
                    generator.used_surrogates.add(surrogate)
                    break
            mapping = TokenMapping(
                original=original_token,
                surrogate=surrogate,
                token_type=kind,
                context="code",
                lookup_key=lookup_key,
                code_literal=code and token_type == TokenType.LITERAL,
                source_reference=source_reference,
            )
            mapping_store[key] = mapping
            reverse_store[surrogate] = mapping
            record_mapping(generator, mapping_store, reverse_store, key, mapping)
            return surrogate


def _prose_policy(prose_mode, common_words):
    mode = MaskMode(prose_mode)
    if mode == MaskMode.CODE_AWARE:
        raise ValueError("prose_mode must be a text masking mode.")
    if common_words is None:
        common_words = []
    if (not isinstance(common_words, (list, tuple, set, frozenset))
            or len(common_words) > 10000
            or any(not isinstance(word, str) or not word.strip() or len(word) > 256
                   for word in common_words)):
        raise ValueError("common_words must contain at most 10000 nonempty words of at most 256 characters.")
    return mode, frozenset(common_words)


class GatewaySession:
    """Per-conversation masking/restoration state shared by gateway request handling."""
    def __init__(self, session=None, mapping_limit=100_000, mask_numbers=False, natural_language="auto", sql_dialect="sqlite", prose_mode="content_words", common_words=None, max_mapping_bytes=DEFAULT_MAPPING_BYTES,
                 max_snapshot_bytes=DEFAULT_SNAPSHOT_BYTES, context_model: ContextModel | None = None, **restore_limits):
        if type(mask_numbers) is not bool:
            raise ValueError("mask_numbers must be a boolean.")
        self.mask_numbers = mask_numbers
        self.context_model = context_model
        self.prose_mode, self.common_words = _prose_policy(prose_mode, common_words)
        self.natural_language = canonical_language(natural_language)
        if not isinstance(sql_dialect, str) or sql_dialect not in {"standard", "postgresql", "sqlite"}:
            raise ValueError("Unsupported SQL dialect.")
        self.sql_dialect = sql_dialect
        self.session = session or PrivacySession(
            "gateway", strategy=SurrogateStrategy.UNICODE, ttl_seconds=86400,
            mapping_limit=mapping_limit, max_mapping_bytes=max_mapping_bytes,
            max_snapshot_bytes=max_snapshot_bytes,
        )
        effective_mapping = min(self.session.generator.max_mapping_bytes,
                                positive_budget(max_mapping_bytes, "max_mapping_bytes"))
        effective_snapshot = min(self.session.max_snapshot_bytes, snapshot_budget(max_snapshot_bytes))
        if self.session.forward_store.mapping_bytes > effective_mapping:
            raise ValueError("Restored session exceeds mapping byte limit; reset the gateway.")
        self.session.generator.max_mapping_bytes = effective_mapping
        self.session.max_snapshot_bytes = effective_snapshot
        self.engine = SharedEngine(mapping_limit, **restore_limits)
        self.lock = RLock()
        self.opaque: set[str] = set()
        self.active_requests = 0
        self.encryption: SnapshotEncryption | None = None
        self.forced_rules = lambda: ()
        self._mask_cache: OrderedDict[tuple, str] = OrderedDict()
        self._mask_cache_bytes = 0
        self.storage_key: str | None = None
        self.domain_policy_version = ""

    def _opaque_key(self, block):
        stable = {
            key: value for key, value in block.items() if key not in {"id", "status"}
        }
        # Native Codex omits an empty content list when replaying reasoning.
        # Retain nonempty content and ciphertext in the provenance digest.
        if stable.get("type") == "reasoning" and stable.get("content") in (None, []):
            stable.pop("content", None)
        return sha256(
            json.dumps(stable, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

    def _mask_prose(self, text: str, preserve_task_words: bool = True, skill_verbs: frozenset[str] = frozenset(),
                    model_context_complete: bool = True) -> str:
        s = self.session
        # Existing source aliases take precedence over prose grammar (e.g. A).
        terms = s.forward_store.originals_in(text)
        terms.update(word for word in re.findall(r"\b[A-Z]\b", text)
                     if not preserve_task_words or word.lower() not in CLOSED_CLASS_WORDS)
        terms.update(re.findall(r"\b([A-Z])(?=\s+(?:함수|변수|식별자|클래스))", text))
        terms.update(re.findall(r"\b(?:function|variable|identifier|class)\s+([A-Z])\b", text))
        selected = (select_gateway_language(text, detect_natural_language(text))
                    if self.natural_language == "auto" else self.natural_language)
        general = ordinary_words(selected) if self.prose_mode != MaskMode.AGGRESSIVE else frozenset()
        vocabulary = lexicon(selected) if self.prose_mode != MaskMode.AGGRESSIVE else None
        static_hits = domain_terms(text, selected)
        if vocabulary is None:
            terms.update(static_hits)
        else:
            # Issue #323 public-word policy: the static NAME_WORDS/ENGLISH_NAMES
            # lists are widely used names, not private registrations, and a
            # static DOMAIN_WORDS entry must not re-mask an ordinary public word.
            # Only a non-public domain-list term keeps the old default masking.
            terms.update(term for term in static_hits
                         if not _static_name_hit(term, selected)
                         and not _public_surface(term, selected, vocabulary))
        # Pass only vocabulary occurring in this fragment to the engine. Copying
        # tens of thousands of dictionary entries for every short field/sentence
        # is both unnecessary and an avoidable request amplification vector.
        from secure_gateway.engine.natural_languages import tokenize
        relevant: set[str] = set()
        chunks = tokenize(text, selected)
        if selected == "en":
            # Nonword-leading private suffixes are not found at the ordinary
            # left word boundary inside a possessive. Look up those exact
            # originals through the existing index before preserving grammar.
            terms.update(suffix for suffix in ("'s", "’s")
                         if suffix in text and suffix in s.forward_store.originals_in(suffix))
        cjk_known = (s.forward_store.originals_in(text, cjk=True)
                     if self.context_model is not None or selected in {"zh", "ja"} else set())
        if selected in {"zh", "ja"}:
            # Code and opaque-value references remain private even between CJK
            # characters. Ordinary prose grammar must not become a new source
            # reference merely because statistical tokenization split it once.
            terms.update(mapping.original for mapping in s.forward_store.values()
                         if mapping.original in cjk_known and mapping.source_reference is not False)
        # Numeric separators can split one source value into adjacent prose
        # aliases (including 0b1010_0101). Protect the complete spelling.
        terms.update(match.group() for match in re.finditer(
            r"(?<!\w)(?:0[bBoOxX][\da-fA-F_]+|\d[\d_]*(?:\.[\d_]+)?(?:[eE][+-]?[\d_]+)?)(?!\w)", text
        ) if "_" in match.group())
        numeric_chunks = {chunk.text for chunk in chunks if chunk.is_number}
        # Replay complete prose numbers through their existing numeric alias.
        # Non-prose source spellings (1_234, 0x1F, 1e-3) must remain protected
        # whole: splitting them can create adjacent aliases that cannot restore.
        for term in terms & numeric_chunks:
            numeric = s.forward_store.get(mapping_key(term, TokenType.NUMBER, code=True))
            if numeric is not None and numeric.surrogate != term:
                terms.discard(term)
        private_roots = {unicodedata.normalize('NFC', term).casefold() for term in terms}
        private_cache: dict[str, bool] = {}

        def private_root(root):
            if root not in private_cache:
                candidates = {root}
                if selected == 'ko' and root.endswith('\ub2e4'):
                    candidates.add(root[:-1])
                    if root.endswith(('\ud558\ub2e4', '\ub418\ub2e4')):
                        candidates.add(root[:-2])
                found = bool(candidates & private_roots)
                for candidate in candidates:
                    for spelling in {candidate, candidate.capitalize(), candidate.upper()}:
                        found |= any(unicodedata.normalize('NFC', value).casefold() == candidate
                                     for value in s.forward_store.originals_in(spelling))
                if len(private_cache) < 4096:
                    private_cache[root] = found
                return found
            return private_cache[root]

        def public_root(root):
            # Name evidence is not a veto: public words and typed predicates win.
            return vocabulary is not None and _public_root(root, selected, vocabulary)

        offset = 0
        for chunk in chunks:
            start = offset
            offset += len(chunk.text)
            key = unicodedata.normalize("NFC", chunk.text).casefold()
            if (vocabulary is not None and chunk.is_word and (s.forward_store or private_roots)
                    and is_ordinary_form(chunk.text, selected, private_root, lambda _: False)):
                # Inflections of an actual private registration/mapping stay private.
                terms.add(chunk.text)
                continue
            if vocabulary is not None and chunk.is_word and _identifier_context(text, start, offset):
                terms.add(chunk.text)
                continue
            if key in general:
                relevant.add(key)
                relevant.add(chunk.text.casefold())
            elif (vocabulary is not None and chunk.is_word
                  and is_ordinary_form(chunk.text, selected, public_root, private_root)):
                relevant.add(key)
                relevant.add(chunk.text.casefold())
            elif vocabulary is not None and chunk.is_word and chunk.kind in {"WORD", "HANGUL_WORD"}:
                # Absence from the vocabulary is not evidence of privacy. Only the
                # narrow, documented identifier/name fallback masks such a word.
                if _identifier_shaped(chunk.text) or _name_fallback(text, start, chunk.text, selected):
                    # Keep English possessive grammar outside the alias (Maribel's -> alias's).
                    possessive = chunk.text[-2:] in {"'s", "’s"} and len(chunk.text) > 2
                    terms.add(chunk.text[:-2] if possessive else chunk.text)
                else:
                    relevant.add(key)
                    relevant.add(chunk.text.casefold())
            if selected == "ko" and chunk.is_word:
                stem, _, _ = self.engine.ko_grammar.decompose_token(chunk.text, general)
                if stem in general:
                    relevant.add(stem)
        task_words = (TASK_WORDS if selected in {"en", "ko"} else set(TASK_WORDS_BY_LANGUAGE.get(selected, "").split())) | relevant
        if self.prose_mode != MaskMode.AGGRESSIVE:
            task_words = task_words | DISCOURSE_WORDS.get(selected, frozenset()) | operator_words(selected)
        if selected in {"en", "ko"} and self.prose_mode != MaskMode.AGGRESSIVE:
            task_words = task_words | SKILL_TASK_WORDS
        # Single-word generic domain spans that are ordinary public words stay
        # public; any actual private registration or mapping still wins.
        span_token = _public_domain_span.set(
            (lambda span: not any(char.isspace() for char in span)
             and unicodedata.normalize('NFC', span).casefold() not in private_roots
             and _public_surface(span, selected, vocabulary)) if vocabulary is not None else None)
        try:
            public_spans: frozenset[tuple[int, int]] = frozenset()
            if (self.context_model is not None and model_context_complete and preserve_task_words and self.prose_mode != MaskMode.AGGRESSIVE
                    and len(text) <= MAX_CONTEXT_CHARS):
                candidates = []
                protected_model_terms = cjk_known | terms
                offset = 0
                for chunk in self.engine._chunks(text, terms, selected):
                    start = offset
                    offset += len(chunk.text)
                    word = chunk.text
                    prefix = text[:start].rstrip()
                    # Confidence is not permission to disclose a new word. The
                    # model only resolves sentence-initial capitalization within
                    # the gateway's existing public vocabulary. Unknown industry
                    # predicates and names keep the conservative masking policy.
                    public_word = unicodedata.normalize("NFC", word).casefold() in task_words
                    sentence_initial = not prefix or bool(re.search(r"[.!?。！？]\s+$", text[:start]))
                    if (chunk.is_word and chunk.kind in {"WORD", "HANGUL_WORD"} and 2 <= len(word) <= 64
                            and public_word and sentence_initial and word[0].isupper()
                            and not any(char.isdigit() for char in word)
                            and "_" not in word and not word.isupper()
                            and not any(char.isupper() for char in word[1:])
                            and not any(term in word for term in protected_model_terms)):
                        candidates.append((start, offset))
                if candidates:
                    public_spans = self.context_model.public_spans(text, candidates, selected).intersection(candidates)
            masked = self.engine.mask_text(
                text,
                s.session_id,
                s.generator,
                s.forward_store,
                s.reverse_store,
                mode=self.prose_mode,
                common_vocabulary=self.common_words,
                sensitive_terms=terms,
                # Code fragments keep the "no identifier preservation" rule.
                custom_preserve=task_words if preserve_task_words else None,
                preserve_capitalized=False,
                # Public words win over capitalization heuristics in every language;
                # actual private terms are forced ENTITY chunks and stay masked.
                preserve_capitalized_words=((set(relevant) | ({"treffen", "buch", "hause"} if selected == "de" else set()))
                                            if vocabulary is not None else set()) | skill_verbs,
                preserve_capitalized_positions=(discourse_capital_positions(text, selected) | operator_capital_positions(text, selected))
                if preserve_task_words and self.prose_mode != MaskMode.AGGRESSIVE else frozenset(),
                preserve_spans=public_spans,
                private_context=not preserve_task_words,
                language=selected,
            ).masked_text
        finally:
            _public_domain_span.reset(span_token)
        return masked

    def _mask_source(self, text: str, language: str = "auto") -> str:
        """Lex a source fragment, falling back to text masking for prose.

        Code lexing rejects unterminated literals, which is correct for the
        strict library API. Backtick/fence fragments inside a normal prompt can
        be prose (an apostrophe like ``don't``), so retry that fragment with
        text masking instead of failing the entire request. The fallback still
        masks content words and never forwards the fragment unmasked.
        """
        s = self.session
        try:
            return self.engine.mask_code(
                text,
                s.session_id,
                s.generator,
                s.forward_store,
                s.reverse_store,
                language=language,
                mask_numbers=self.mask_numbers,
                sql_dialect=self.sql_dialect,
            ).masked_text
        except NumericLiteralConflict:
            raise
        except ValueError:
            # Invalid source may contain a sensitive literal that happens to
            # be a grammar/common word. Keep the whole fragment opaque.
            self.engine._check_input(text)
            return self.engine._get_or_create_surrogate(text, TokenType.LITERAL,
                s.generator, s.forward_store, s.reverse_store, code=True)

    def _mask_cache_key(self, text: str, code: bool, language: str) -> tuple:
        # A new private value can change an earlier public interpretation, but
        # unrelated allocations must not invalidate the complete conversation.
        # Include embedded originals too: protected possessive suffixes and
        # fragments can affect masking without a whole-input word boundary.
        dependencies = sha256()
        for original in sorted(self.session.forward_store.originals_in(text, embedded=True)):
            encoded = original.encode("utf-8")
            dependencies.update(len(encoded).to_bytes(8, "big"))
            dependencies.update(encoded)
        return (text, code, language, self.natural_language, self.prose_mode,
                self.mask_numbers, self.sql_dialect, self.common_words, id(self.context_model),
                tuple(self.forced_rules()), self.domain_policy_version,
                getattr(self.engine, "cache_epoch", 0), dependencies.digest())

    @staticmethod
    def _mask_cache_entry_bytes(key: tuple, result: str) -> int:
        return len(key[0].encode("utf-8")) + len(result.encode("utf-8")) + 256

    def mask(self, text: str, code: bool = False, language: str = "auto") -> str:
        """Return the result of mask.

        Never returns ``None``.
        """
        key = self._mask_cache_key(text, code, language)
        cached = self._mask_cache.get(key)
        if cached is not None:
            self._mask_cache.move_to_end(key)
            return cached
        result = self._force_mask(self._mask_unforced(text, code, language))
        key = self._mask_cache_key(text, code, language)
        size = self._mask_cache_entry_bytes(key, result)
        if size <= 1024 * 1024:
            if key not in self._mask_cache:
                while self._mask_cache and (self._mask_cache_bytes + size > 4 * 1024 * 1024
                                           or len(self._mask_cache) >= 4096):
                    old_key, old_result = self._mask_cache.popitem(last=False)
                    self._mask_cache_bytes -= self._mask_cache_entry_bytes(old_key, old_result)
                self._mask_cache[key] = result
                self._mask_cache_bytes += size
        return result

    def _force_mask(self, text: str, extra_rules: tuple[str, ...] = ()) -> str:
        rules: tuple[str, ...] = self.forced_rules() + extra_rules
        # Never rewrite an existing alias: changing its spelling destroys the
        # only reference that permits restoration.
        forms: set[str] = {unicodedata.normalize(form, word) for word in rules for form in ("NFC", "NFD")}
        pattern = re.compile("|".join(re.escape(word) for word in sorted(forms, key=len, reverse=True))) if forms else None
        s = self.session
        def encode(word):
            alias = self.engine._get_or_create_surrogate(
                word, TokenType.ENTITY, s.generator, s.forward_store, s.reverse_store, code=True
            )
            # Delimit partial-word aliases so they can be restored even next to
            # ASCII letters. The delimiters are consumed during restoration.
            return "⟦" + alias + "⟧"
        def substitute(match):
            return encode(match.group())
        with s.generator.operation():
            parts = []
            output_bytes = 0
            def append(piece):
                nonlocal output_bytes
                output_bytes += len(piece.encode("utf-8"))
                if output_bytes > self.engine.max_input_bytes:
                    raise ValueError("Masked text size limit reached.")
                parts.append(piece)
            def ordinary(start, end):
                cursor = start
                if pattern:
                    for match in pattern.finditer(text, start, end):
                        append(text[cursor:match.start()])
                        append(substitute(match))
                        cursor = match.end()
                append(text[cursor:end])
            cursor = 0
            for match in re.finditer(r"private_symbol_\d+|[⟦⟧]", text):
                ordinary(cursor, match.start())
                value = match.group()
                append(encode(value) if value in {"⟦", "⟧"} else value)
                cursor = match.end()
            ordinary(cursor, len(text))
            return "".join(parts)

    def _mask_unforced(self, text: str, code: bool = False, language: str = "auto") -> str:
        if code:
            return self._mask_source(text, language)
        if looks_like_source(text):
            return self._mask_source(text, language)
        code_spans = markdown_code_spans(text)
        known_terms = self.session.forward_store.originals_in(text)
        if "`" in text and any("`" in term for term in known_terms):
            raise ValueError("Protected text overlaps Markdown code boundaries; use plain text or a new conversation.")
        if "`" not in text and any(any(char.isspace() for char in term) or "SKILL.md" in term
                                  for term in known_terms):
            # Do not split a previously protected source literal into separate
            # public words at sentence/skill/code boundaries.
            return self._mask_prose(text)
        # Fenced/inline source is lexed, rather than replaced as an opaque block.
        protected = {"EMAIL", "URL", "SECRET", "UUID", "IP", "PHONE", "CODE_BLOCK"}
        protected_skill = any("SKILL.md" in chunk.text and chunk.kind in protected
                              for chunk in self.engine.tokenizer.tokenize(text))
        for match in re.finditer(re.escape("SKILL.md"), text):
            neighbors = text[max(0, match.start() - 1):match.start()] + text[match.end():match.end() + 1]
            if any(unicodedata.category(char).startswith("M") or char in "\u200c\u200d" for char in neighbors):
                protected_skill = True
        skill_pattern = (r"(?<![\w\u0300-\u036f./\\:=?&%@+-])SKILL\.md(?![\w\u0300-\u036f/\\:=?&%@+-]|\.[\w])|"
                         if not protected_skill and self.prose_mode != MaskMode.AGGRESSIVE else "")
        prose_pattern = "(" + skill_pattern + "|".join(re.escape(identity) for identity in PUBLIC_CLAUDE_IDENTITIES) + ")"
        parts: list[str] = []
        protected_parts = set()
        def add_prose(fragment):
            if any(any(char.isspace() for char in term) or "SKILL.md" in term
                   for term in self.session.forward_store.originals_in(fragment)):
                protected_parts.add(len(parts))
                parts.append(fragment)
            else:
                parts.extend(re.split(prose_pattern, fragment))
        cursor = 0
        for start, end in code_spans:
            add_prose(text[cursor:start])
            parts.append(text[start:end])
            cursor = end
        add_prose(text[cursor:])
        output = []
        # A fragment following code or a public skill name can start mid-sentence.
        # Abstain instead of mistaking that local boundary for an instruction.
        complete = len(parts) == 1
        skill_context = self.prose_mode != MaskMode.AGGRESSIVE and ("SKILL.md" in parts or "`SKILL.md`" in parts)
        for index, part in enumerate(parts):
            if index in protected_parts:
                output.append(self._mask_prose(part, model_context_complete=complete))
                continue
            if part == "SKILL.md" and self.session.forward_store.originals_in(part):
                output.append(self._mask_source(part))
                continue
            if part in PUBLIC_CLAUDE_IDENTITIES or (part == "SKILL.md" and self.prose_mode != MaskMode.AGGRESSIVE):
                output.append(part)
                continue
            delimiter = re.match(r"`+", part)
            if delimiter and len(delimiter.group()) >= 3 and "\n" in part:
                fence = delimiter.group()
                header, body = part.split("\n", 1)
                if header[len(fence):].strip().lower() not in set(LANGUAGE_KEYWORDS) | set(ALIASES) | {""}:
                    header = fence
                output.append(
                    header
                    + "\n"
                    + self._mask_source(body[:-len(fence)], header[len(fence):].strip() or "auto")
                    + fence
                )
            elif part == "`SKILL.md`" and self.prose_mode != MaskMode.AGGRESSIVE and not self.session.forward_store.originals_in("SKILL.md"):
                output.append(part)
            elif delimiter:
                fence = delimiter.group()
                output.append(fence + self._mask_source(part[len(fence):-len(fence)]) + fence)
            else:
                if any(any(char.isspace() for char in term)
                       for term in self.session.forward_store.originals_in(part)):
                    output.append(self._mask_prose(part, model_context_complete=complete))
                    continue
                verbs = set()
                if skill_context and index + 1 < len(parts) and parts[index + 1] in {"SKILL.md", "`SKILL.md`"} and re.fullmatch(r"\s*Read\s+", part):
                    verbs.add("read")
                for sentence in (re.split(r"(?<=[.!?])(?=\s)", part) if skill_context else [part]):
                    allowed = set(verbs)
                    if skill_context and re.match(r"\s*Follow (?:its|the) instructions\b", sentence):
                        prefix = re.match(r"\s*Follow\b", sentence)
                        assert prefix is not None
                        output.append(self._mask_prose(prefix.group(), skill_verbs=frozenset({"follow"}), model_context_complete=False))
                        sentence = sentence[prefix.end():]
                    output.append(self._mask_prose(sentence, skill_verbs=frozenset(allowed), model_context_complete=complete))
        return "".join(output)

    def restore(self, text):
        """Handle restore."""
        s = self.session
        return self.engine.unmask(
            text, s.session_id, s.reverse_store, s.strategy, strict=True
        ).unmasked_text

    def values(self, value, restore=False, code=False):
        """Handle values."""
        operation = self.restore if restore else lambda text: self.mask(text, code=code)
        if isinstance(value, str):
            if not restore and not code and value:
                self.engine._check_input(value)
                s = self.session
                return self.engine._get_or_create_surrogate(value, TokenType.LITERAL,
                    s.generator, s.forward_store, s.reverse_store)
            return operation(value)
        if isinstance(value, list):
            return [self.values(item, restore, code) for item in value]
        if isinstance(value, dict):
            return {
                self.schema_name(key, restore): self.values(
                    item, restore, code and key in {"cmd", "command", "content", "text", "old_string", "new_string", "chars", "input", "patch"}
                )
                for key, item in value.items()
            }
        if restore and type(value) in {int, float}:
            # Source aliases are integers, even when the source literal was a
            # decimal. Never recover an alias after floating-point rounding.
            candidate = str(abs(value))
            if type(value) is float and 732846000000000000 <= abs(value) < 732847000000000000:
                raise ValueError("Numeric alias lost integer precision.")
            mapping = self.session.reverse_store.get(candidate)
            if mapping is not None and mapping.token_type == TokenType.NUMBER:
                if not re.fullmatch(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?", mapping.original):
                    raise ValueError("Source literal cannot be restored as a JSON number.")
                original = json.loads(mapping.original)
                if type(original) is float and not math.isfinite(original):
                    raise ValueError("Source literal is not a finite JSON number.")
                return -original if value < 0 else original
            # Detect invented numeric aliases with the same strict policy used
            # for strings, while leaving ordinary JSON scalars unchanged.
            self.restore(str(value))
        return value

    def walk(self, value, restore=False, code=False, schema_root=None,
             property_names=False, schema_refs=(), schema_context=False):
        """Handle walk."""
        if schema_root is None:
            schema_root = value
        if isinstance(value, str):
            return self.restore(value) if restore else self.mask(value, code)
        if isinstance(value, list):
            return [self.walk(item, restore, code, schema_root,
                              property_names, schema_refs, schema_context) for item in value]
        if not isinstance(value, dict):
            return value
        reference_key = "$ref" if "$ref" in value else "$dynamicRef"
        if property_names and reference_key in value:
            reference = value[reference_key]
            if not isinstance(reference, str):
                raise ValueError("Schema references must be text.")
            if reference in schema_refs or len(schema_refs) >= 64:
                raise ValueError("Recursive propertyNames references are unsupported.")
            target = self.schema_reference(reference, schema_root, restore, resolve=True)
            # A definition can serve both property names and ordinary values.
            # Specialize a copy here, rather than changing the shared definition.
            specialized = self.walk(target, restore, code, schema_root, True,
                                    schema_refs + (reference,), schema_context)
            siblings = {key: item for key, item in value.items() if key != reference_key}
            if not siblings:
                return specialized
            return {"allOf": [specialized, self.walk(
                siblings, restore, code, schema_root, True, schema_refs, schema_context)]}
        kind = value.get("type", "")
        if not isinstance(kind, str):
            kind = ""
        # Signed/encrypted reasoning is decoded before the attachment check:
        # redacted_thinking carries opaque `data` ciphertext by design.
        if kind in {"thinking", "redacted_thinking", "reasoning"}:
            key = self._opaque_key(value)
            if not restore and key not in self.opaque:
                raise ValueError(
                    "Unrecognized signed/encrypted reasoning; start a new conversation."
                )
            reasoning_result = deepcopy(value)
            if kind == "reasoning" and "summary" in value:
                summary = value["summary"]
                if not isinstance(summary, list) or any(
                    not isinstance(part, dict)
                    or part.get("type") != "summary_text"
                    or not isinstance(part.get("text"), str)
                    for part in summary
                ):
                    raise ValueError("Unsupported public reasoning summary.")
                reasoning_result["summary"] = [
                    {**part, "text": self.restore(part["text"]) if restore else self.mask(part["text"])}
                    for part in summary
                ]
            if restore:
                self.opaque.add(key)
                self.opaque.add(self._opaque_key(reasoning_result))
            return reasoning_result
        if (
            kind in BLOCKED_TYPES
            or any(k in value for k in ("image_url", "file_data", "file_id"))
            # `data` alone also occurs in ordinary tool results (for example a
            # JSON field named "data"); only attachment metadata blocks it.
            or (
                "data" in value
                and any(k in value for k in ("mimeType", "mime_type", "media_type"))
            )
        ):
            raise ValueError(
                "Binary/remote attachments are unsupported by the privacy gateway."
            )
        if any(key in value for key in {"signature", "encrypted_content"}):
            raise ValueError(
                "Opaque fields outside recognized reasoning are unsupported."
            )
        result: dict[str, Any] = {}
        title_terms: tuple[str, ...] = ()
        description_terms: tuple[str, ...] = ()
        if schema_context and not restore and isinstance(value.get("title"), str):
            title = value["title"]
            description = value.get("description", "")
            if not isinstance(description, str):
                description = ""
            title_terms, description_terms = self._schema_prose_terms(title, description)
            # Allocate from the original text before either field is transformed.
            # Thus mappings made by one field cannot change its sibling on replay.
            self._force_mask(title, title_terms)
            self._force_mask(description, description_terms)
        for key, item in value.items():
            if key == "$schema" and isinstance(item, str):
                # Public JSON Schema dialect URIs stay usable. Anything else is
                # private data and is masked/restored like ordinary text instead
                # of rejecting the whole request.
                if item in JSON_SCHEMA_DIALECTS:
                    result[key] = item
                elif restore:
                    result[key] = self.restore(item)
                else:
                    result[key] = self.mask(item)
            elif schema_context and key in {"title", "description"} and isinstance(item, str):
                terms = title_terms if key == "title" else description_terms
                result[key] = self.restore(item) if restore else self._force_mask(self.mask(item), terms)
            elif key in {"name", "tool_name"}:
                if not isinstance(item, str):
                    raise ValueError("Tool names must be strings.")
                result[key] = (
                    self.restore(item)
                    if restore
                    else item
                    if item in TOOL_NAMES
                    else self.mask(item, code=True)
                )
            elif (
                key == "format"
                and kind == "custom"
            ):
                if item == {"type": "text"}:
                    result[key] = {"type": "text"}
                    continue
                if not isinstance(item, dict):
                    raise ValueError("Unrecognized custom tool grammar format.")
                definition = item.get("definition", "")
                if (
                    set(item) != {"type", "syntax", "definition"}
                    or item.get("type") != "grammar"
                    or item.get("syntax") != "lark"
                    or not isinstance(definition, str)
                ):
                    raise ValueError("Unrecognized custom tool grammar format.")
                normalized = definition.replace("\r\n", "\n").strip()
                allowed = (
                    value.get("name") == "exec"
                    and normalized == EXEC_GRAMMAR.strip()
                    or value.get("name") == "apply_patch"
                    and sha256(normalized.encode()).hexdigest() in PATCH_GRAMMAR_HASHES
                )
                if not allowed:
                    raise ValueError(
                        "Unrecognized custom tool grammar; request was not forwarded."
                    )
                result[key] = deepcopy(
                    item
                )  # Only pinned public CLI grammars may pass unchanged.
            elif (
                key == "format"
                and isinstance(item, str)
                and item
                in {
                    "uri",
                    "uri-reference",
                    "date",
                    "time",
                    "date-time",
                    "duration",
                    "uuid",
                    "email",
                    "hostname",
                    "ipv4",
                    "ipv6",
                    "regex",
                }
            ):
                result[key] = item
            elif key == "cache_control":
                validate_cache_control(item)
                result[key] = deepcopy(item)
            elif key in PROTOCOL:
                result[key] = self.protocol_value(value, key, item, restore)
            elif key == "arguments" and isinstance(item, str):
                if not item.strip():
                    result[key] = ""
                    continue
                result[key] = strict_json_dumps(
                    self.values(strict_json_loads(item), restore, code=True),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            elif key == "output_config" and value.get("role") == "system":
                from secure_gateway.gateway_validation import _public_options
                _public_options(item, {"effort": {"low", "medium", "high", "max"}}, "inline output")
                result[key] = deepcopy(item)
            elif key == "tools" and kind == "additional_tools":
                result[key] = self.walk(item, restore)
            elif key == "input" and kind == "custom_tool_call":
                result[key] = self.walk(item, restore, code=True)
            elif key == "input" and kind == "tool_use":
                result[key] = self.values(item, restore, code=True)
            elif key == "output" and kind in {
                "function_call_output",
                "custom_tool_call_output",
            }:
                result[key] = self.tool_output(item, restore)
            elif key == "content" and kind == "tool_result":
                result[key] = self.tool_output(item, restore)
            elif key == "content" and value.get("role") == "tool":
                result[key] = self.tool_output(item, restore)
            elif (key == "patternProperties" and item) or (
                key == "pattern" and isinstance(item, str) and kind in SCHEMA_TYPES
            ):
                raise ValueError(
                    "JSON Schema pattern constraints cannot safely preserve private names."
                )
            elif key in {"parameters", "input_schema", "schema"} and isinstance(
                item, (dict, bool)
            ):
                self.validate_schema(item)
                result[key] = self.walk(item, restore, schema_root=item, schema_context=key in {"parameters", "input_schema"})
            elif key in SCHEMA_NAME_KEYWORDS:
                if not isinstance(item, dict):
                    raise ValueError("Schema name maps must be objects.")
                result[key] = {
                    self.schema_name(k, restore): (
                        [self.schema_name(name, restore) for name in v]
                        if key in {"dependentRequired", "dependencies"}
                        and isinstance(v, list)
                        else self.walk(v, restore, schema_root=schema_root, schema_context=schema_context)
                    )
                    for k, v in item.items()
                }
            elif key == "required":
                result[key] = [
                    self.schema_name(k, restore) for k in item
                ]
            elif key in {"$ref", "$dynamicRef"} and isinstance(item, str):
                result[key] = self.schema_reference(item, schema_root, restore)
            elif key == "propertyNames" and isinstance(item, dict):
                result[key] = self.walk(item, restore, schema_root=schema_root,
                                        property_names=True, schema_refs=schema_refs, schema_context=schema_context)
            elif property_names and key in {"enum", "const"}:
                def name_value(candidate):
                    return (self.schema_name(candidate, restore)
                            if isinstance(candidate, str) else self.walk_data(candidate, restore))
                result[key] = ([name_value(candidate) for candidate in item]
                               if key == "enum" else name_value(item))
            elif key in DATA_KEYWORDS:
                # enum/const/default/examples hold arbitrary JSON data. Protocol
                # and schema exceptions must not apply inside them, or private
                # values under keys like id/type/model/cache_control leak.
                result[key] = self.walk_data(item, restore, prose=False)
            else:
                if (kind in {"text", "input_text", "output_text", "refusal"}
                    or "role" in value) and key not in {"content", "tool_calls"}:
                    if key in {"text", "refusal"} and isinstance(item, str):
                        result[key] = self.restore(item) if restore else self.mask(item, code=code)
                    else:
                        result[key] = self.walk_data(item, restore)
                else:
                    result[key] = self.walk(item, restore, code, schema_root,
                                            property_names, schema_refs, schema_context)
        return result

    def _schema_prose_terms(self, title, description):
        from secure_gateway.engine.natural_languages import tokenize

        language = select_gateway_language(title, detect_natural_language(title))
        vocabulary = lexicon(language)
        roots = tuple(chunk.text for chunk in tokenize(title, language)
                      if chunk.is_word and not _public_surface(chunk.text, language, vocabulary))

        def shares_private_root(word):
            for root in roots:
                shorter, longer = (word, root) if len(word) <= len(root) else (root, word)
                for i in range(len(shorter) - 1):
                    if shorter[i:i + 2] not in longer:
                        continue
                    for j in range(len(shorter), i + 1, -1):
                        fragment = shorter[i:j]
                        if fragment in longer and not _public_surface(fragment, language, vocabulary):
                            return True
            return False

        related = tuple(chunk.text for chunk in tokenize(description, language)
                        if chunk.is_word and not _public_surface(chunk.text, language, vocabulary)
                        and shares_private_root(chunk.text))
        return roots, related

    def schema_reference(self, reference, root, restore=False, resolve=False):
        """Handle schema reference."""
        if reference == "#":
            return root if resolve else reference
        if not reference.startswith("#") or re.search(r"%(?![0-9A-Fa-f]{2})", reference):
            raise ValueError("Remote schema references or malformed pointers are unsupported.")
        pointer = urllib.parse.unquote(reference[1:], errors="strict")
        if not pointer.startswith("/"):
            raise ValueError("Remote schema references and named anchors are unsupported.")
        node = root
        name_map = False
        transformed = []
        for segment in pointer[1:].split("/"):
            if re.search(r"~(?![01])", segment):
                raise ValueError("Malformed schema pointer.")
            original = segment.replace("~1", "/").replace("~0", "~")
            decoded = self.schema_name(original, restore) if name_map and not resolve else original
            transformed.append(decoded.replace("~", "~0").replace("/", "~1"))
            next_name_map = not name_map and isinstance(node, dict) and original in SCHEMA_NAME_KEYWORDS
            try:
                node = node[int(original)] if isinstance(node, list) else node[original]
            except (KeyError, IndexError, TypeError, ValueError):
                raise ValueError("Schema reference does not resolve.") from None
            name_map = next_name_map
        return node if resolve else "#" + urllib.parse.quote("/" + "/".join(transformed), safe="/~$")

    def tool_output(self, value, restore=False):
        """Content blocks have public envelopes; their extra payloads are data."""
        if isinstance(value, str):
            return self.restore(value) if restore else self.mask(value, code=True)
        if not isinstance(value, list):
            return self.walk_data(value, restore)
        result = []
        for block in value:
            if isinstance(block, dict) and block.get("type") in {
                "text", "input_text", "output_text", "refusal",
            }:
                public_fields = {"type", "text", "refusal", "cache_control"}
                transformed = self.walk(
                    {key: item for key, item in block.items() if key in public_fields},
                    restore, code=True,
                )
                for key, item in block.items():
                    if key not in public_fields:
                        name = self.restore(key) if restore else self.mask(key, code=True)
                        transformed[name] = self.walk_data(item, restore)
                result.append(transformed)
            else:
                result.append(self.walk(block, restore, code=True))
        return result

    def protocol_value(self, envelope, key, item, restore):
        """Public tags apply only to their envelopes, never arbitrary data."""
        kind = envelope.get("type")
        if not isinstance(kind, str):
            kind = ""
        kinds = {
            "text", "input_text", "output_text", "refusal", "message",
            "tool_use", "tool_result", "function_call", "function_call_output",
            "custom_tool_call", "custom_tool_call_output", "tool_namespace", "additional_tools", "namespace",
            "tool_reference", "function", "custom", "json_schema", "json_object",
        } | SCHEMA_TYPES
        if key == "type" and isinstance(item, list) and all(
            isinstance(tag, str) and tag in SCHEMA_TYPES for tag in item
        ):
            return deepcopy(item)
        keep = key == "type" and isinstance(item, str) and item in kinds
        if key == "role":
            keep = ("content" in envelope or kind == "additional_tools") and isinstance(item, str) and item in {
                "system", "developer", "user", "assistant", "tool",
            }
        elif key == "id":
            keep = kind in {"tool_use", "function_call", "custom_tool_call", "custom_tool_call_output", "function_call_output", "message", "additional_tools"} or (kind == "function" and isinstance(envelope.get("function"), dict))
        elif key == "status" and kind in {"function_call", "custom_tool_call", "message"}:
            if not isinstance(item, str) or item not in {"in_progress", "completed", "incomplete"}:
                raise ValueError("Unsupported input item status.")
            keep = True
        elif key == "call_id":
            keep = kind in {"function_call", "function_call_output", "custom_tool_call", "custom_tool_call_output"}
        elif key == "tool_use_id":
            keep = kind == "tool_result"
        elif key == "tool_call_id":
            keep = envelope.get("role") == "tool" and "content" in envelope
        elif key == "phase":
            keep = envelope.get("role") == "assistant" and "content" in envelope
            if keep and (not isinstance(item, str) or item not in {"commentary", "final_answer"}):
                raise ValueError("Unsupported assistant phase.")
        elif key in {"effort", "verbosity", "syntax"}:
            allowed = {
                "effort": {"none", "minimal", "low", "medium", "high", "xhigh", "max"},
                "verbosity": {"low", "medium", "high"},
                "syntax": {"lark", "regex"},
            }
            keep = isinstance(item, str) and item in allowed[key]
        if keep:
            if not isinstance(item, str):
                raise ValueError("Protocol identifiers must be text.")
            return item
        return self.walk_data(item, restore)

    def schema_name(self, name, restore=False):
        """Handle schema name."""
        if not isinstance(name, str):
            raise ValueError("Schema property names must be text.")
        return (
            self.restore(name)
            if restore
            else name
            if name in ARGUMENT_KEYS
            else self.mask(name)
        )

    def validate_schema(self, schema):
        """Handle validate schema."""
        if isinstance(schema, bool):
            return
        if not isinstance(schema, dict):
            raise ValueError("Schema must be an object or boolean.")
        if schema.get("patternProperties") or "pattern" in schema:
            raise ValueError("JSON Schema pattern constraints are unsupported.")
        if set(schema) & {"minLength", "maxLength", "format"}:
            raise ValueError("JSON Schema string length/format constraints cannot preserve aliases.")
        for key, item in schema.items():
            if key in SCHEMA_NAME_KEYWORDS and key != "dependentRequired":
                if not isinstance(item, dict):
                    raise ValueError("Schema name maps must be objects.")
                for child in item.values():
                    if key == "dependencies" and isinstance(child, list):
                        continue
                    self.validate_schema(child)
            elif key in {
                "items",
                "additionalItems",
                "unevaluatedItems",
                "contentSchema",
                "additionalProperties",
                "unevaluatedProperties",
                "contains",
                "not",
                "if",
                "then",
                "else",
                "propertyNames",
            }:
                for child in item if isinstance(item, list) else [item]:
                    self.validate_schema(child)
            elif key in {"allOf", "anyOf", "oneOf", "prefixItems"}:
                if not isinstance(item, list):
                    raise ValueError("Schema alternatives must be arrays.")
                for child in item:
                    self.validate_schema(child)

    def walk_data(self, value, restore=False, *, prose=False):
        """Mask/restore arbitrary JSON data (enum/const/default/examples).

        Protocol and schema exceptions do not apply here: keys such as id,
        type, model or cache_control inside user data are still private.
        """
        if isinstance(value, str):
            if restore:
                return self.restore(value)
            return self.mask(value) if prose else self._force_mask(self._mask_prose(value, preserve_task_words=False))
        if isinstance(value, list):
            return [self.walk_data(item, restore, prose=prose) for item in value]
        if not isinstance(value, dict):
            return value
        return {
            self.schema_name(key, restore): self.walk_data(item, restore, prose=prose)
            for key, item in value.items()
        }

    def safeguards(self, value, position="envelope"):
        """Support the observed classifier envelope; reject unknown controls."""
        if isinstance(value, list):
            if position != "envelope" or any(not isinstance(item, dict) for item in value):
                raise ValueError("Unsupported safety policy envelope.")
            return [self.safeguards(item, position) for item in value]
        if not isinstance(value, dict):
            raise ValueError("Unsupported safety policy envelope.")
        fields = {
            "envelope": {"type", "classifier_context"},
            "context": {"permission_mode", "platform", "live_cwd", "rules"},
            "rules": {"allow", "deny", "ask"},
            "rule": {"rule", "source"},
        }
        enums = {
            "type": {"dangerous_tool_use"},
            "permission_mode": {"auto", "default", "acceptEdits", "plan", "dontAsk", "bypassPermissions"},
            "platform": {"windows", "linux", "darwin"},
            "source": {"toolsNarrowing", "userSettings", "projectSettings", "localSettings", "commandLine"},
        }
        if set(value) - fields[position]:
            raise ValueError("Unsupported safety policy fields.")
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key in enums:
                if not isinstance(item, str) or item not in enums[key]:
                    raise ValueError("Unsupported safety protocol tag.")
                result[key] = item
            elif key == "classifier_context":
                result[key] = self.safeguards(item, "context")
            elif key == "rules":
                result[key] = self.safeguards(item, "rules")
            elif position == "rules":
                if not isinstance(item, list):
                    raise ValueError("Safety rules must be arrays.")
                result[key] = [self.safeguards(rule, "rule") for rule in item]
            elif key in {"rule", "live_cwd"}:
                if not isinstance(item, str):
                    raise ValueError("Safety operands must be text.")
                result[key] = item if key == "rule" and item in TOOL_NAMES else self.mask(item)
            else:
                raise ValueError("Unsupported safety policy field.")
        return result

    def tool_choice(self, value, dialect):
        """Handle tool choice."""
        if isinstance(value, str):
            if value not in {"auto", "none", "required", "any"}:
                raise ValueError("Unsupported tool choice.")
            return value
        if not isinstance(value, dict):
            raise ValueError("Tool choice must be text or an object.")
        kind = value.get("type")
        if dialect == "claude":
            allowed = {"type", "disable_parallel_tool_use"} | ({"name"} if kind == "tool" else set())
            if not isinstance(kind, str) or kind not in {"auto", "none", "any", "tool"} or set(value) - allowed:
                raise ValueError("Unsupported Claude tool choice.")
            if "disable_parallel_tool_use" in value and not isinstance(value["disable_parallel_tool_use"], bool):
                raise ValueError("Invalid parallel tool choice control.")
            result = deepcopy(value)
            if kind == "tool":
                if not isinstance(value.get("name"), str):
                    raise ValueError("Tool choice requires a tool name.")
                result["name"] = self.walk({"name": value["name"]})["name"]
            return result
        if kind != "function":
            raise ValueError("Unsupported function tool choice.")
        if dialect == "chat_completions":
            if set(value) != {"type", "function"} or not isinstance(value["function"], dict) or set(value["function"]) != {"name"}:
                raise ValueError("Invalid function tool choice.")
            name = value["function"].get("name")
        else:
            if set(value) != {"type", "name"}:
                raise ValueError("Invalid function tool choice.")
            name = value.get("name")
        if not isinstance(name, str):
            raise ValueError("Tool choice requires a tool name.")
        return self.walk(value)

    def context_management(self, value):
        """Handle context management."""
        if not isinstance(value, dict) or set(value) != {"edits"} or not isinstance(value["edits"], list):
            raise ValueError("Unsupported context management.")
        result = []
        for edit in value["edits"]:
            if not isinstance(edit, dict):
                raise ValueError("Context edits must be objects.")
            kind = edit.get("type")
            if kind == "clear_tool_uses_20250919":
                fields = {"type", "trigger", "keep", "clear_at_least", "exclude_tools", "clear_tool_inputs"}
                thresholds = {"trigger": "input_tokens", "keep": "tool_uses", "clear_at_least": "input_tokens"}
            elif kind == "clear_thinking_20251015":
                fields = {"type", "keep"}
                thresholds = {"keep": "thinking_turns"}
            else:
                raise ValueError("Unsupported context edit type.")
            if set(edit) - fields:
                raise ValueError("Unsupported context edit controls.")
            transformed = deepcopy(edit)
            for key, tag in thresholds.items():
                if key not in edit:
                    continue
                item = edit[key]
                if kind == "clear_thinking_20251015" and key == "keep" and item == "all":
                    continue
                if (not isinstance(item, dict) or set(item) != {"type", "value"}
                    or item.get("type") != tag or type(item.get("value")) is not int
                    or item["value"] < (1 if tag == "thinking_turns" else 0)):
                    raise ValueError("Invalid context edit threshold.")
            if "clear_tool_inputs" in edit and not isinstance(edit["clear_tool_inputs"], bool):
                raise ValueError("Invalid clear tool inputs control.")
            if "exclude_tools" in edit:
                names = edit["exclude_tools"]
                if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
                    raise ValueError("Tool exclusions must be tool names.")
                transformed["exclude_tools"] = [self.walk({"name": name})["name"] for name in names]
            result.append(transformed)
        return {"edits": result}

    def request(self, payload: dict[str, Any], *, dialect=None) -> dict[str, Any]:
        """Return the result of request.

        Never returns ``None``.
        """
        with self.context_model.request_budget() if self.context_model is not None else nullcontext():
            return self._request(payload, dialect=dialect)

    def _request(self, payload: dict[str, Any], *, dialect=None) -> dict[str, Any]:
        request_dialect = dialect or ("claude" if "messages" in payload else "codex")
        validate_request(payload, request_dialect)
        fields = (
            TOP_FIELDS | {"max_completion_tokens", "stop", "stream_options", "reasoning_effort", "response_format"}
            if dialect == "chat_completions"
            else TOP_FIELDS
        )
        if set(payload) - fields:
            raise ValueError("Unsupported request fields; request was not forwarded.")
        if payload.get("background") or payload.get("truncation") == "auto":
            raise ValueError("Background/server-side truncation is unsupported.")
        if dialect in {"responses", "chat_completions"}:
            validate_api_options(payload, dialect)
            if "input" in payload and "messages" in payload:
                raise ValueError("Mixed API dialects are unsupported.")
            if dialect == "chat_completions" and "system" in payload:
                raise ValueError(
                    "Chat Completions uses system messages, not a system field."
                )
            options = payload.get("stream_options")
            if options is not None and (
                not isinstance(options, dict)
                or set(options) - {"include_usage"}
                or not isinstance(options.get("include_usage"), bool)
            ):
                raise ValueError("Unsupported stream options.")
            for tool in payload.get("tools", []):
                if not isinstance(tool, dict) or tool.get("type") != "function":
                    raise ValueError(
                        "API mode supports local function tools only; remote tools are blocked."
                    )
            if dialect == "responses" and "input" not in payload:
                raise ValueError("Responses requires an input payload.")
            if dialect == "chat_completions" and "messages" not in payload:
                raise ValueError("Chat Completions requires messages.")

        # Seed code aliases before prompt references in this request.
        def seed(value):
            if isinstance(value, str):
                self.mask(value)
            elif isinstance(value, list):
                for item in value:
                    seed(item)
            elif isinstance(value, dict):
                if value.get("type") in {
                    "tool_result",
                    "function_call_output",
                    "tool_use",
                    "function_call",
                    "custom_tool_call",
                    "custom_tool_call_output",
                }:
                    self.walk(value)
                else:
                    for item in value.values():
                        seed(item)

        seed(payload.get("messages", payload.get("input", [])))
        result = {}
        for key, value in payload.items():
            if key == "system" and "messages" in payload:
                result[key] = self.claude_system(value)
                continue
            if key == "safeguards":
                result[key] = self.safeguards(value)
                continue
            if key == "context_management":
                if request_dialect != "claude":
                    raise ValueError("Context editing requires the Claude dialect.")
                result[key] = self.context_management(value)
                continue
            if key in {"client_metadata", "metadata"}:
                continue  # Optional diagnostics are not required for inference.
            if key == "tool_choice":
                result[key] = self.tool_choice(value, request_dialect)
                continue
            if key in {"stop", "stop_sequences"}:
                result[key] = self.walk_data(value)
                continue
            if key in {
                "messages",
                "input",
                "instructions",
                "system",
                "tools",
                "text",
                "stop_sequences",
                "stop",
                "tool_choice",
                "output_config",
                "response_format",
                "context_management",
                "safeguards",
            }:
                result[key] = self.walk(value)
            elif key in {"prompt_cache_key", "safety_identifier"}:
                result[key] = sha256(str(value).encode()).hexdigest()
            else:
                result[key] = deepcopy(value)
        if "input" in result:
            result["store"] = False
            result["instructions"] = PRIVACY_INSTRUCTION + result.get(
                "instructions", ""
            )
        elif "messages" in result and dialect == "chat_completions":
            if "system" in result:
                raise ValueError(
                    "Chat Completions uses system messages, not a system field."
                )
            result["messages"].insert(
                0, {"role": "system", "content": PRIVACY_INSTRUCTION}
            )
        elif "messages" in result:
            system = result.get("system", [])
            if isinstance(system, str):
                system = [{"type": "text", "text": system}]
            result["system"] = [*system, {"type": "text", "text": PRIVACY_INSTRUCTION}]
        for tool in result.get("tools", []):
            if tool.get("name") in TOOL_DESCRIPTIONS:
                tool["description"] = TOOL_DESCRIPTIONS[tool["name"]]
        rules = self.forced_rules()
        if rules:
            def check(value):
                if isinstance(value, str):
                    normalized = unicodedata.normalize("NFC", value)
                    return any(unicodedata.normalize("NFC", rule) in normalized for rule in rules)
                if isinstance(value, list):
                    return any(check(item) for item in value)
                if isinstance(value, dict):
                    return any(check(key) or check(item) for key, item in value.items())
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    return any(rule in str(value) for rule in rules)
                return False
            if check(result):
                raise ValueError("A forced masking rule matches a protocol field; request blocked.")
        return result

    def claude_system(self, value):
        """Handle claude system."""
        if isinstance(value, str):
            if value.startswith(CLAUDE_ATTRIBUTION_PREFIX):
                raise ValueError(
                    "Claude attribution must be a separate first system block."
                )
            return self.walk(value)
        if not isinstance(value, list):
            raise ValueError("Unsupported Claude system payload.")
        result: list[dict[str, Any]] = []
        for index, block in enumerate(value):
            text = block.get("text", "") if isinstance(block, dict) else ""
            if isinstance(text, str) and text.startswith(CLAUDE_ATTRIBUTION_PREFIX):
                if (
                    index != 0
                    or block.get("type") != "text"
                    or set(block) - {"type", "text", "cache_control"}
                    or not CLAUDE_ATTRIBUTION.fullmatch(text)
                ):
                    raise ValueError(
                        "Unrecognized Claude attribution; request was not forwarded."
                    )
                result.append({"type": "text", "text": text})
                if "cache_control" in block:
                    control = block["cache_control"]
                    if (
                        not isinstance(control, dict)
                        or control.get("type") != "ephemeral"
                        or set(control) - {"type", "ttl"}
                        or control.get("ttl", "5m") not in {"5m", "1h"}
                    ):
                        raise ValueError("Unrecognized attribution cache control.")
                    result[-1]["cache_control"] = deepcopy(control)
            else:
                result.append(self.walk(block))
        return result

    def response(self, body: bytes, content_type: str, *, dialect=None) -> bytes:
        """Return the result of response.

        Never returns ``None``.
        """
        if len(body) > self.engine.max_restore_input_bytes:
            raise ValueError("Restoration input size limit reached.")
        self.engine._restore_remaining = self.engine.max_restore_output_bytes
        try:
            result = self._response(body, content_type, dialect=dialect)
            if len(result) > self.engine.max_restore_output_bytes:
                raise ValueError("Restoration output size limit reached.")
            return result
        finally:
            self.engine._restore_remaining = None

    def _response(self, body: bytes, content_type: str, *, dialect=None) -> bytes:
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != "text/event-stream":
            payload = strict_json_loads(body)
            if not isinstance(payload, dict):
                raise ValueError("Upstream response must be a JSON object.")
            return strict_json_dumps(
                self.walk(payload, restore=True), ensure_ascii=False
            ).encode()
        events: list[tuple[list[str], dict[str, Any] | None]] = []
        stream = body.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        frames = stream.split("\n\n")
        if frames and frames[-1]:
            # SSE dispatches an event only after a blank line.  An HTTP body may
            # end cleanly while its final SSE frame is still incomplete.
            frames.pop()
        for frame in frames:
            # SSE line endings do not include Unicode separators inside JSON strings.
            lines = frame.replace("\r\n", "\n").split("\n")
            data = "\n".join(
                line[5:].lstrip() for line in lines if line.startswith("data:")
            )
            if not data or data == "[DONE]":
                events.append((lines, None))
            else:
                event = strict_json_loads(data)
                if not isinstance(event, dict):
                    raise ValueError("SSE events must be JSON objects.")
                events.append((lines, event))
        # Fold each text/JSON stream before restoration (tokens can span any delta).
        groups: dict[tuple, list[tuple[int, dict, str]]] = {}
        thinking: dict[int, dict] = {}
        key: tuple
        for index, (_, event) in enumerate(events):
            if not isinstance(event, dict):
                continue
            if dialect == "chat_completions":
                choices = event.get("choices", [])
                if not isinstance(choices, list):
                    raise ValueError("Invalid Chat Completions choices.")
                for choice in choices:
                    if not isinstance(choice, dict) or not isinstance(choice.get("index"), int):
                        raise ValueError("Invalid Chat Completions choice.")
                    chat_delta = choice.get("delta", {})
                    if not isinstance(chat_delta, dict):
                        raise ValueError("Invalid Chat Completions delta.")
                    calls = chat_delta.get("tool_calls", [])
                    if not isinstance(calls, list):
                        raise ValueError("Invalid Chat Completions tool calls.")
                    for field in ("content", "reasoning_content", "refusal"):
                        if isinstance(chat_delta.get(field), str):
                            groups.setdefault(
                                ("chat", choice["index"], field), []
                            ).append((index, chat_delta, field))
                    for call in calls:
                        if not isinstance(call, dict) or not isinstance(call.get("index"), int):
                            raise ValueError("Invalid Chat Completions tool call.")
                        function = call.get("function", {})
                        if not isinstance(function, dict):
                            raise ValueError("Invalid Chat Completions function.")
                        for field in ("name", "arguments"):
                            if isinstance(function.get(field), str):
                                groups.setdefault(
                                    (
                                        "chat_tool",
                                        choice["index"],
                                        call["index"],
                                        field,
                                    ),
                                    [],
                                ).append((index, function, field))
                continue
            kind = event.get("type", "")
            delta = event.get("delta")
            if kind == "content_block_start" and not isinstance(event.get("content_block"), dict):
                raise ValueError("Invalid Claude content block.")
            if kind == "content_block_delta" and not isinstance(delta, dict):
                raise ValueError("Invalid Claude content delta.")
            if (
                kind == "content_block_start"
                and event.get("content_block", {}).get("type") == "thinking"
            ):
                thinking[event["index"]] = deepcopy(event["content_block"])
            if (
                kind == "content_block_delta"
                and event.get("index") in thinking
                and isinstance(delta, dict)
            ):
                block = thinking[event["index"]]
                for field in ("thinking", "signature"):
                    if field in delta:
                        if not isinstance(delta[field], str):
                            raise ValueError("Invalid Claude thinking delta.")
                        block[field] = block.get(field, "") + delta[field]
            if kind == "content_block_delta" and isinstance(delta, dict):
                field = (
                    "partial_json"
                    if delta.get("type") == "input_json_delta"
                    else "text"
                )
                if field not in delta:
                    continue  # signed thinking is kept exactly as received
                if not isinstance(delta[field], str):
                    raise ValueError("Invalid Claude text/JSON delta.")
                target = delta
                key = (kind, event.get("index"), field)
            elif kind in {
                "response.output_text.delta",
                "response.refusal.delta",
                "response.reasoning_summary_text.delta",
                "response.function_call_arguments.delta",
                "response.custom_tool_call_input.delta",
            }:
                if not isinstance(delta, str):
                    raise ValueError("Invalid Responses delta.")
                target, field = event, "delta"
                key = (
                    kind,
                    event.get("item_id"),
                    event.get("output_index"),
                    event.get("content_index"),
                    event.get("summary_index"),
                )
            else:
                continue
            groups.setdefault(key, []).append((index, target, field))
        for block in thinking.values():
            self.opaque.add(self._opaque_key(block))
        for group in groups.values():
            combined = "".join(target[field] for _, target, field in group)
            field = group[0][2]
            if (
                field == "partial_json"
                or dialect == "chat_completions"
                and field == "arguments"
                or group[0][1].get("type") == "response.function_call_arguments.delta"
            ):
                restored = (
                    combined
                    if not combined.strip()
                    else strict_json_dumps(
                        self.values(strict_json_loads(combined), restore=True),
                        ensure_ascii=False,
                    )
                )
            else:
                restored = self.restore(combined)
            for offset, (_, target, field) in enumerate(group):
                target[field] = restored if offset == 0 else ""
        output = []
        for lines, event in events:
            if event is None:
                if lines:
                    output.append("\n".join(lines) + "\n\n")
                continue
            # Deltas have already been restored; do not recursively restore twice.
            if dialect == "chat_completions":
                pass  # Chat delta text/names/arguments were restored above.
            elif event.get("type") not in {
                "content_block_delta",
                "response.output_text.delta",
                "response.refusal.delta",
                "response.reasoning_summary_text.delta",
                "response.function_call_arguments.delta",
                "response.custom_tool_call_input.delta",
            }:
                event = self.walk(event, restore=True)
            headers = [line for line in lines if not line.startswith("data:")]
            output.append(
                "\n".join(headers + ["data: " + strict_json_dumps(event, ensure_ascii=False)])
                + "\n\n"
            )
        return "".join(output).encode()


class PrivacyGateway(ThreadingHTTPServer):
    """Threaded loopback HTTP server that masks outbound requests and restores responses."""
    daemon_threads = True

    def __init__(
        self,
        address,
        token: str,
        upstreams=None,
        state_dir: Path | None = None,
        api_upstreams=None,
        mapping_limit=100_000,
        max_mapping_bytes=DEFAULT_MAPPING_BYTES,
        max_snapshot_bytes=DEFAULT_SNAPSHOT_BYTES,
        audit_path: Path | None = None,
        max_active_requests=32,
        max_provider_requests=8,
        mask_numbers=False,
        max_restore_input_bytes=16 * 1024 * 1024,
        max_restore_output_bytes=16 * 1024 * 1024,
        audit_max_records=100_000,
        audit_max_age_days=None,
        natural_language="auto",
        sql_dialect="sqlite",
        prose_mode="content_words",
        common_words=None,
        context_model_path=None,
    ):
        self.restore_limits = {"max_restore_input_bytes": max_restore_input_bytes,
                               "max_restore_output_bytes": max_restore_output_bytes}
        MaskingEngine(**self.restore_limits)
        if type(mask_numbers) is not bool:
            raise ValueError("mask_numbers must be a boolean.")
        self.mask_numbers = mask_numbers
        if address[0] != "127.0.0.1":
            raise ValueError("Gateway must bind to IPv4 loopback.")
        if (
            not isinstance(mapping_limit, int)
            or isinstance(mapping_limit, bool)
            or mapping_limit < 1
        ):
            raise ValueError("Mapping limit must be a positive integer.")
        self.mapping_limit = mapping_limit
        self.max_mapping_bytes = positive_budget(max_mapping_bytes, "max_mapping_bytes")
        self.max_snapshot_bytes = snapshot_budget(max_snapshot_bytes)
        for limit in (max_active_requests, max_provider_requests):
            if type(limit) is not int or limit < 1:
                raise ValueError("Request admission limits must be positive integers.")
        self.max_active_requests = max_active_requests
        self.max_provider_requests = max_provider_requests
        self.admission = Condition(RLock())
        self.admitted_requests = 0
        self.active_audit_handlers = 0
        self.provider_admitted: dict[str, int] = {}
        self.closing = False
        self._allow_forced_exit = False
        self.recent_timings: deque = deque(maxlen=32)
        self.token = token
        self.upstreams = dict(UPSTREAMS if upstreams is None else upstreams)
        # Explicit API-key modes are opt-in at construction. They are never
        # enabled by subscription installation and never share credentials.
        self.api_upstreams = dict(api_upstreams or {})
        for agent, origin in self.api_upstreams.items():
            if agent not in API_AUTH_PREFIXES:
                raise ValueError(f"Unsupported API mode: {agent}")
            loopback = isinstance(origin, str) and re.fullmatch(
                r"http://127\.0\.0\.1:[0-9]{1,5}", origin
            )
            if origin != API_UPSTREAMS[agent] and not loopback:
                raise ValueError("API upstream must be a fixed HTTPS origin.")
            self.upstreams[agent] = origin
        self.sessions: dict[str, GatewaySession] = {}
        self.prose_mode, self.common_words = _prose_policy(prose_mode, common_words)
        self.context_model, self.context_model_status = load_context_model(context_model_path)
        self.natural_language = canonical_language(natural_language)
        if not isinstance(sql_dialect, str) or sql_dialect not in {"standard", "postgresql", "sqlite"}:
            raise ValueError("Unsupported SQL dialect.")
        self.sql_dialect = sql_dialect
        self.sessions_lock = RLock()
        # The capacity bound is global: all providers must serialize registry
        # mutations. This lock is released before masking or provider I/O.
        self.provider_locks = {agent: self.sessions_lock for agent in self.upstreams}
        self.state_dir = state_dir
        self._snapshot_scan: Iterator[Path] = iter(())
        self._next_snapshot_cleanup = 0.0
        if state_dir:
            state_dir.mkdir(parents=True, exist_ok=True)
            state_dir.chmod(0o700)
            self._snapshot_scan = iter(state_dir.glob("*-symbols-v2.enc"))
        self.rules_path = state_dir / "mask-rules.enc" if state_dir else None
        self._preload_event = Event()
        self._preload_lock = Lock()
        self._domain_catalog: DomainCatalog | None = None
        self._catalog_preload_failed = False
        self.domain_policy = dict(DOMAIN_DEFAULTS)
        self.domain_policy_origin = "defaults"
        self.domain_policy_path = state_dir / "domain-policy.enc" if state_dir else None
        if self.domain_policy_path and self.domain_policy_path.exists():
            with self.domain_policy_path.open("rb") as policy_stream:
                encrypted_policy = policy_stream.read(16385)
            if len(encrypted_policy) > 16384:
                raise ValueError("Domain policy size exceeded")
            self.domain_policy = self.validate_domain_policy(json.loads(decrypt_snapshot_bytes(encrypted_policy, token)))
            self.domain_policy_origin = "saved"
        self.mask_rules = ()
        if self.rules_path and self.rules_path.exists():
            with self.rules_path.open("rb") as stream:
                encrypted_rules = stream.read(1024 * 1024 + 1)
            if len(encrypted_rules) > 1024 * 1024:
                raise ValueError("Rule file too large")
            self.mask_rules = self.validate_mask_rules(json.loads(decrypt_snapshot_bytes(encrypted_rules, token)))
        self.audit = AuditStore(audit_path, audit_max_records, audit_max_age_days) if audit_path is not None else None
        self.audit_write_errors = 0
        self.audit_error_counts = {"admission": 0, "completion": 0, "maintenance": 0}
        self._diagnostic_lock = RLock()
        self._diagnostic_counts = dict.fromkeys(_DIAGNOSTIC_CATEGORIES, 0)
        try:
            if self.audit is not None:
                self.audit.recover_incomplete(apply=True)
                self.audit.retention(apply=True)
            super().__init__(address, GatewayHandler)
            self.cleanup_expired_snapshots()
            self._start_catalog_preload()
        except BaseException:
            if self.audit is not None:
                self.audit.close()
            raise

    def _start_catalog_preload(self):
        thread = Thread(target=self._preload_catalog_worker, daemon=True)
        thread.start()

    def _preload_catalog_worker(self):
        try:
            cat = domain_catalog()
            with self._preload_lock:
                self._domain_catalog = cat
        except Exception:
            self.record_diagnostic("catalog_preload_failed")
            self._catalog_preload_failed = True
        finally:
            self._preload_event.set()

    @property
    def domain_catalog(self):
        """Return the preloaded or synchronously loaded DomainCatalog instance."""
        self._preload_event.wait()
        with self._preload_lock:
            if self._domain_catalog is None:
                try:
                    self._domain_catalog = domain_catalog()
                except Exception:
                    raise
            return self._domain_catalog

    @domain_catalog.setter
    def domain_catalog(self, value):
        """Set the DomainCatalog instance and mark preload as ready."""
        with self._preload_lock:
            self._domain_catalog = value
            self._preload_event.set()

    def record_audit_error(self, phase):
        """Handle record audit error."""
        with self.admission:
            self.audit_write_errors += 1  # Retain the legacy aggregate contract.
            self.audit_error_counts[phase] += 1

    @staticmethod
    def validate_mask_rules(value):
        """Handle validate mask rules."""
        if not isinstance(value, list) or len(value) > 256:
            raise ValueError("Invalid rules")
        rules = []
        for rule in value:
            if not isinstance(rule, str) or len(rule) > 256 or not rule.strip():
                raise ValueError("Invalid rule")
            literal = rule.strip().strip("*")
            if not literal or "*" in literal or "\n" in literal or "\r" in literal or "⟦" in literal or "⟧" in literal:
                raise ValueError("Invalid rule")
            rules.append(literal)
        return tuple(dict.fromkeys(rules))

    def set_mask_rules(self, rules):
        """Handle set mask rules."""
        rules = self.validate_mask_rules(rules)
        if self.rules_path is None:
            raise ValueError("Rule storage is unavailable")
        with self.admission:
            if self.admitted_requests:
                raise ValueError("Requests are active")
            from secure_gateway.gateway_install import atomic_bytes
            payload = json.dumps(list(rules), ensure_ascii=False).encode("utf-8")
            atomic_bytes(self.rules_path, SnapshotEncryption(self.token).encrypt(payload))
            self.mask_rules = rules
        return rules

    @staticmethod
    def validate_domain_policy(value):
        """Handle validate domain policy."""
        if not isinstance(value, dict) or set(value) != set(DOMAIN_DEFAULTS) or any(type(item) is not bool for item in value.values()):
            raise ValueError("Invalid domain policy")
        return dict(value)

    def domain_status(self):
        """Handle domain status."""
        return {**self.domain_catalog.status(self.domain_policy),
                "source": self.domain_policy_origin, "persistent": self.domain_policy_path is not None}

    def set_domain_policy(self, value):
        """Handle set domain policy."""
        policy = self.validate_domain_policy(value)
        with self.admission:
            if self.admitted_requests:
                raise ValueError("Requests are active")
            if self.domain_policy_path:
                from secure_gateway.gateway_install import atomic_bytes
                atomic_bytes(self.domain_policy_path, SnapshotEncryption(self.token).encrypt(json.dumps(policy).encode()))
            self.domain_policy = policy
            self.domain_policy_origin = "saved" if self.domain_policy_path else "memory"
            for session in list(self.sessions.values()):
                with session.lock:
                    session._mask_cache.clear()
                    session._mask_cache_bytes = 0
                    session.domain_policy_version = self.domain_catalog.version + json.dumps(policy, sort_keys=True)
        return self.domain_status()

    def audit_error_diagnostics(self):
        """Handle audit error diagnostics."""
        with self.admission:
            return dict(self.audit_error_counts)

    def record_diagnostic(self, category):
        """Bounded instance counters and one content-free warning per category."""
        with self._diagnostic_lock:
            if category not in self._diagnostic_counts:
                raise ValueError("Unknown diagnostic category.")
            previous = self._diagnostic_counts[category]
            self._diagnostic_counts[category] = min(previous + 1, _DIAGNOSTIC_LIMIT)
        if previous == 0 and category not in {"snapshot_preserved", "log_delivery_failed"}:
            if not _warn_diagnostic(category, lambda: self.record_diagnostic("log_delivery_failed")):
                # Count directly: logging this failure could recurse forever.
                with self._diagnostic_lock:
                    current = self._diagnostic_counts["log_delivery_failed"]
                    self._diagnostic_counts["log_delivery_failed"] = min(current + 1, _DIAGNOSTIC_LIMIT)

    def operational_diagnostics(self):
        """Handle operational diagnostics."""
        with self._diagnostic_lock:
            return dict(self._diagnostic_counts)

    def format_upstream_error(self, exc):
        """Keep a formatter failure inside the sanitized HTTP error boundary."""
        try:
            return sanitized_upstream_error(
                exc, on_failure=lambda: self.record_diagnostic("upstream_error_body"),
                on_close_failure=lambda: self.record_diagnostic("upstream_error_stream_close"),
            )
        except Exception:
            # A formatter bug must not disconnect clients or reflect its inputs.
            self.record_diagnostic("upstream_error_format")
            try:
                exc.close()
            except Exception:
                self.record_diagnostic("upstream_error_close")
            code = getattr(exc, "code", None)
            status = code if type(code) is int and code in UPSTREAM_ERROR_STATUSES else 502
            message = (b'Prompt is too long; reduce context or compact the conversation.'
                       if status == 413 else b'Upstream rejected the request.')
            return status, b'{"error": {"message": "' + message + b'"}}'

    def try_admit(self, agent):
        """Reserve an inference slot without waiting or reading the body."""
        with self.admission:
            if (self.closing or self.admitted_requests >= self.max_active_requests
                or self.provider_admitted.get(agent, 0) >= self.max_provider_requests):
                return False
            self.admitted_requests += 1
            self.provider_admitted[agent] = self.provider_admitted.get(agent, 0) + 1
            return True

    def release_admission(self, agent):
        """Handle release admission."""
        with self.admission:
            self.admitted_requests -= 1
            self.provider_admitted[agent] -= 1
            self.admission.notify_all()

    def drain_and_shutdown(self, grace=30):
        """Drain requests; only a dedicated CLI daemon may exit on timeout."""
        with self.admission:
            self.closing = True
            drained = self.admission.wait_for(
                lambda: self.admitted_requests == 0 and self.active_audit_handlers == 0,
                timeout=grace if self._allow_forced_exit else None,
            )
        if not drained:
            # Never close SQLite or encrypted sessions concurrently with active
            # handlers. Atomic snapshots and SQLite recovery own crash cleanup.
            try:
                self.socket.close()
            finally:
                try:
                    os.write(2, b"gateway_shutdown forced=true\n")
                finally:
                    os._exit(75)
        self.shutdown()

    def session_diagnostics(self):
        """Return aggregate limits and lifetimes, never mappings or credentials."""
        with self.admission:
            active = self.admitted_requests
            admitted = dict(self.provider_admitted)
            recent_timings = list(self.recent_timings)
        providers = {}
        for agent in sorted(self.upstreams):
            with self.provider_locks[agent]:
                owned_sessions = [value for key, value in self.sessions.items()
                                  if key == agent or key.startswith(agent + "-")]
                session = self.sessions.get(agent)
                if session is None and owned_sessions:
                    session = owned_sessions[0]
                item: dict[str, Any] = {"active_requests": admitted.get(agent, 0),
                        "mapping_limit": self.mapping_limit, "mapping_count": 0,
                        "max_mapping_bytes": self.max_mapping_bytes, "mapping_bytes": 0,
                        "max_snapshot_bytes": self.max_snapshot_bytes,
                        "ttl_seconds": None, "expires_at": None, "expired": False}
                if session is not None:
                    with session.lock:
                        item.update(mapping_limit=min(session.engine.mapping_limit,
                                                      session.session.generator.max_mappings),
                                    mapping_count=len(session.session.forward_store),
                                    max_mapping_bytes=session.session.generator.max_mapping_bytes,
                                    mapping_bytes=session.session.forward_store.mapping_bytes,
                                    max_snapshot_bytes=session.session.max_snapshot_bytes,
                                    ttl_seconds=session.session.ttl_seconds,
                                    expires_at=session.session.last_accessed + session.session.ttl_seconds,
                                    expired=session.session.is_expired())
                mapping_count, mapping_bytes = 0, 0
                for owned in owned_sessions:
                    with owned.lock:
                        mapping_count += len(owned.session.forward_store)
                        mapping_bytes += owned.session.forward_store.mapping_bytes
                item.update(conversation_count=len(owned_sessions), mapping_count=mapping_count,
                            mapping_bytes=mapping_bytes)
                providers[agent] = item
        return {"active_requests": active, "max_active_requests": self.max_active_requests,
                "recent_timings": recent_timings,
                "context_model": self.context_model.diagnostics() if self.context_model else {"status": self.context_model_status},
                "max_provider_requests": self.max_provider_requests, "providers": providers,
                "audit_write_errors": self.audit_write_errors,
                "audit_error_counts": self.audit_error_diagnostics(),
                "diagnostic_counts": self.operational_diagnostics(),
                "domain_catalog": self.domain_status(),
                "audit_completion_retries": self.audit.completion_retries.diagnostics() if self.audit else None}

    def _recover_snapshot(self, key: str, *, opaque_only: bool = False) -> None:
        """Quarantine proven-corrupt local snapshot state for this conversation.

        Bounded to one quarantined copy per file. Never follows symlinks and
        never raises errors containing snapshot contents, tokens, or exception
        details.
        """
        if not self.state_dir:
            return
        base = self.state_dir / f"{key}-symbols-v2.enc"
        paths = [base.with_suffix(".opaque.json")]
        if not opaque_only:
            paths.insert(0, base)
        for path in paths:
            try:
                if path.is_symlink():
                    path.unlink(missing_ok=True)
                    continue
                if not path.exists():
                    continue
                target = path.with_name(path.name + ".quarantined")
                if target.exists() or target.is_symlink():
                    raise OSError("Snapshot quarantine already exists.")
                path.chmod(0o600)
                path.replace(target)
            except OSError:
                self.record_diagnostic("snapshot_recovery_io")
                raise OSError("Snapshot recovery failed.") from None
        self.record_diagnostic("snapshot_recovered")

    def _remove_snapshot(self, key):
        if self.state_dir:
            path = self.state_dir / f"{key}-symbols-v2.enc"
            path.unlink(missing_ok=True)
            path.with_suffix(".opaque.json").unlink(missing_ok=True)

    def cleanup_expired_snapshots(self):
        """Bounded maintenance: authenticate old snapshots before deleting them.

        The mtime is only a cheap prefilter, never evidence of expiry. Scan a
        rotating batch so large state directories do not stall every request.
        Damaged or foreign snapshots are preserved for explicit recovery.
        """
        if not self.state_dir:
            return
        with self.sessions_lock:
            now = time.time()
            self._next_snapshot_cleanup = time.monotonic() + 60
            decrypted = 0
            for _ in range(32):
                try:
                    path = next(self._snapshot_scan)
                except StopIteration:
                    self._snapshot_scan = iter(self.state_dir.glob("*-symbols-v2.enc"))
                    break
                except OSError:
                    self.record_diagnostic("snapshot_scan_io")
                    break
                key = path.name.removesuffix("-symbols-v2.enc")
                if key in self.sessions or not any(key == agent or re.fullmatch(re.escape(agent) + r"-[a-f0-9]{64}", key) for agent in self.upstreams):
                    continue
                try:
                    if path.is_symlink() or path.stat().st_mtime > now - 86400:
                        continue
                    decrypted += 1
                    try:
                        loaded = load_session(path, self.token, "gateway")
                    except SessionExpiredError:
                        self._remove_snapshot(key)
                    else:
                        loaded.clear()
                except FileNotFoundError:
                    continue  # Another operation already removed the candidate.
                except OSError:
                    self.record_diagnostic("snapshot_cleanup_io")
                except ValueError:
                    # Foreign/corrupt maintenance candidates are intentionally
                    # preserved; repeated scans are not warning-worthy failures.
                    self.record_diagnostic("snapshot_preserved")
                if decrypted >= 2:
                    break

    def _drop_session(self, key, session):
        session.session.clear()
        session._mask_cache.clear()
        session._mask_cache_bytes = 0
        session.opaque.clear()
        session.encryption = None
        del self.sessions[key]

    def get_session(self, agent, conversation=None, *, pin=False):
        """Return get session.

        Returns the conversation session for the agent, creating or loading it as needed; never returns ``None``.
        """
        key = agent
        if conversation:
            if not isinstance(conversation, str) or len(conversation.encode()) > 2048:
                raise ValueError("Invalid conversation identity.")
            key += "-" + sha256((self.token + "\0" + agent + "\0" + conversation).encode()).hexdigest()
        with self.provider_locks[agent]:
            if time.monotonic() >= self._next_snapshot_cleanup:
                self.cleanup_expired_snapshots()
            current = self.sessions.get(key)
            if current is not None:
                # Serialize with an in-flight request before dropping state.
                with current.lock:
                    if not current.session.generator.closed and (
                        current.active_requests or not current.session.is_expired()
                    ):
                        if pin:
                            current.active_requests += 1
                        current.session.touch()
                        return current
                    # An always-on daemon must apply the same idle TTL as a
                    # restarted one: drop expired aliases and reasoning
                    # provenance instead of silently reusing (and reviving)
                    # them via save().
                    self._remove_snapshot(key)
                    self._drop_session(key, current)
            if len(self.sessions) >= MAX_CONVERSATION_SESSIONS:
                for old_key, old_session in list(self.sessions.items()):
                    with old_session.lock:
                        if not old_session.active_requests and old_session.session.is_expired():
                            self._remove_snapshot(old_key)
                            self._drop_session(old_key, old_session)
                if len(self.sessions) >= MAX_CONVERSATION_SESSIONS:
                    candidates = [(value.session.last_accessed, old_key, value) for old_key, value in self.sessions.items() if not value.active_requests]
                    if not self.state_dir or not candidates:
                        raise GatewayRequestError("conversation_capacity")
                    _, old_key, old_session = min(candidates, key=lambda value: value[0])
                    with old_session.lock:
                        # Persist without touching its idle TTL. On failure the
                        # live session remains intact and the request fails.
                        self._persist_session(old_key, old_session)
                        self._drop_session(old_key, old_session)
            path = (
                self.state_dir / f"{key}-symbols-v2.enc" if self.state_dir else None
            )
            saved = None
            if path and path.is_symlink():
                self.record_diagnostic("snapshot_load_failed")
                raise OSError("Snapshot path is unsafe.")
            if path and path.exists():
                try:
                    saved = load_session(path, self.token, "gateway")
                except SessionExpiredError:
                    self._remove_snapshot(key)
                    saved = None
                except ValueError as exc:
                    # Authentication failure can also mean a wrong password.
                    # Quarantine the bytes intact before starting a new session.
                    if str(exc) not in {"Invalid encrypted session file.",
                                        "Incorrect session password or damaged session file."}:
                        self.record_diagnostic("snapshot_load_failed")
                        raise ValueError("Snapshot could not be loaded.") from None
                    self._recover_snapshot(key)
                    saved = None
                except OSError:
                    self.record_diagnostic("snapshot_load_failed")
                    raise
            session = GatewaySession(saved, self.mapping_limit, mask_numbers=self.mask_numbers,
                                     natural_language=self.natural_language, sql_dialect=self.sql_dialect,
                                     max_mapping_bytes=self.max_mapping_bytes,
                                     max_snapshot_bytes=self.max_snapshot_bytes,
                                     prose_mode=self.prose_mode, common_words=self.common_words,
                                     context_model=self.context_model,
                                     **self.restore_limits)
            session.forced_rules = lambda: self.mask_rules
            session.engine.domain_spans = lambda text: self.domain_catalog.spans(text, self.domain_policy)
            session.domain_policy_version = self.domain_catalog.version + json.dumps(self.domain_policy, sort_keys=True)
            session.storage_key = key
            # Reasoning provenance is only meaningful while the matching alias
            # table is alive. Expired/missing snapshots start fresh, so stale
            # digests must not be loaded into the new table.
            opaque_path = path.with_suffix(".opaque.json") if path else None
            if saved is not None and opaque_path and opaque_path.is_symlink():
                self.record_diagnostic("snapshot_load_failed")
                raise OSError("Snapshot path is unsafe.")
            if saved is not None and opaque_path and opaque_path.exists():
                try:
                    raw_opaque = opaque_path.read_text(encoding="utf-8")
                    digests = json.loads(raw_opaque)
                    if not isinstance(digests, list) or any(
                        not isinstance(x, str) or not re.fullmatch(r"[a-f0-9]{64}", x)
                        for x in digests
                    ):
                        raise ValueError
                except OSError:
                    # Transient read/permission errors must not be treated as
                    # proven corruption; fail safely without quarantining.
                    self.record_diagnostic("snapshot_load_failed")
                    raise
                except (json.JSONDecodeError, ValueError):
                    # Invalid provenance metadata: quarantine only opaque state so
                    # encrypted mappings can still load, but old opaque blocks
                    # cannot be replayed without fresh provenance.
                    self._recover_snapshot(key, opaque_only=True)
                    digests = None
                if digests is not None:
                    session.opaque = set(digests)
            self.sessions[key] = session
            if pin:
                session.active_requests += 1
            return session

    def save(self, agent, session):
        """Handle save."""
        if session.session.is_expired() and not session.active_requests:
            # Do not revive an expired session via touch(). Drop its aliases
            # and provenance; the next get_session() replaces the registry
            # entry after its own expiry check, so no registry lock is taken
            # here (avoids lock inversion with the request path).
            session.session.clear()
            session.opaque.clear()
            return
        session.session.touch()
        self._persist_session(agent, session)

    def _persist_session(self, agent, session):
        """Write idle state as-is; eviction must not extend its lifetime."""
        if self.state_dir:
            path = self.state_dir / f"{session.storage_key or agent}-symbols-v2.enc"
            if session.encryption is None:
                session.encryption = SnapshotEncryption(self.token)
            save_session(
                path, session.session, self.token, encryption=session.encryption
            )
            _atomic_json(path.with_suffix(".opaque.json"), sorted(session.opaque))
            path.with_suffix(".opaque.json").chmod(0o600)

    def reset(self, agent="all"):
        """Handle reset."""
        agents = sorted(self.upstreams) if agent == "all" else [agent]
        if any(name not in self.upstreams for name in agents):
            raise ValueError("Unknown provider.")
        with ExitStack() as stack:
            for name in agents:
                stack.enter_context(self.provider_locks[name])
            keys = set(agents) | {key for key in self.sessions
                                      if any(key.startswith(name + "-") for name in agents)}
            if self.state_dir:
                for name in agents:
                    keys.update(file.name.removesuffix("-symbols-v2.enc") for file in
                                self.state_dir.glob(name + "-*-symbols-v2.enc"))
            current = [(name, self.sessions.get(name)) for name in sorted(keys)]
            for _, session in current:
                if session is not None:
                    stack.enter_context(session.lock)
                    if session.active_requests:
                        raise ValueError(
                            "Provider has active requests; retry after they finish."
                        )
            for name, session in current:
                if self.state_dir:
                    path = self.state_dir / f"{name}-symbols-v2.enc"
                    path.unlink(missing_ok=True)
                    path.with_suffix(".opaque.json").unlink(missing_ok=True)
                if session is not None:
                    session.session.clear()
                    session._mask_cache.clear()
                    session.opaque.clear()
                    session.encryption = None
                    del self.sessions[name]

    def server_close(self):
        """Handle server close."""
        with self.admission:
            self.closing = True
        super().server_close()
        with self.admission:
            self.admission.wait_for(lambda: self.admitted_requests == 0 and self.active_audit_handlers == 0)
        for session in self.sessions.values():
            with session.lock:
                session.session.clear()
                session._mask_cache.clear()
                session.opaque.clear()
                session.encryption = None
        self.sessions.clear()
        if self.audit is not None:
            self.audit.close()


class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the privacy gateway and local admin endpoints."""
    server: PrivacyGateway
    audit_metadata: dict[str, Any] | None = None
    stream_metrics: dict[str, Any]
    protocol_version = "HTTP/1.0"
    timeout = 60

    def finish(self):
        """Handle finish."""
        # An early rejection can leave POST bytes in flight. Closing immediately
        # then resets the connection on Windows, sometimes discarding the 401.
        # Publish EOF after the response, then allow a bounded body drain. Never
        # wait here after a normal request has already consumed its body.
        try:
            if (
                getattr(self, "command", None) == "POST"
                and not getattr(self, "_request_body_consumed", False)
            ):
                headers = getattr(self, "headers", {})
                try:
                    length = int(headers.get("Content-Length", "0"))
                except (ValueError, TypeError):
                    length = 0
                if 0 < length <= LIMIT and not headers.get("Transfer-Encoding"):
                    self.wfile.flush()
                    self.connection.shutdown(socket.SHUT_WR)
                    deadline = time.monotonic() + 0.1
                    while length:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            break
                        self.connection.settimeout(remaining)
                        block = self.rfile.read1(min(length, 65536))
                        if not block:
                            break
                        length -= len(block)
        except (OSError, ValueError) as exc:
            log_failure(_LOGGER, "peer_cleanup_failed", exc)  # Best effort.
        finally:
            super().finish()

    def log_message(self, *_):
        """Handle log message."""
        pass  # Never log headers, prompts, replies or tokens.

    def send_body(self, status, body, content_type="application/json"):
        """Handle send body."""
        if self.audit_metadata is not None:
            self.audit_metadata["status"] = status
            self.audit_metadata["output_bytes"] = len(body)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in getattr(self, "response_headers", {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def capture_response_headers(self, headers):
        """Handle capture response headers."""
        self.response_headers = {
            key: value
            for key, value in headers.items()
            if key.lower() in {"retry-after", "x-should-retry"}
            or key.lower().startswith(("anthropic-ratelimit-", "x-ratelimit-"))
        }

    def authorized(self):
        """Handle authorized."""
        return secrets.compare_digest(
            self.headers.get("X-SecureGateway-Token", "").encode(), self.server.token.encode()
        )

    def do_GET(self):
        """Handle do GET."""
        if handle_admin(self):
            return
        if self.path == "/xai/v1/models":
            if not self.authorized():
                self.send_body(401, b'{"error":"Unauthorized"}')
                return
            if "xai" not in self.server.api_upstreams:
                self.send_body(400, b'{"error":"Explicit API mode required"}')
                return
            auth = self.headers.get("Authorization", "")
            if not auth.startswith(API_AUTH_PREFIXES["xai"]) or self.headers.get("x-api-key"):
                self.send_body(401, b'{"error":"xAI API key required"}')
                return
            try:
                body = fetch_catalog(self.server.api_upstreams["xai"], auth)
                self.send_body(200, body)
            except urllib.error.HTTPError as exc:
                self.capture_response_headers(exc.headers)
                status, body = self.server.format_upstream_error(exc)
                self.send_body(status, body)
            except (ValueError, OSError, http.client.HTTPException):
                self.send_body(502, b'{"error":"Model catalog unavailable"}')
            return
        if self.path == "/health" and self.authorized():
            self.send_body(200, strict_json_dumps({"service": "secure-gateway-subscription-gateway", "version": __version__}).encode())
        elif (
            self.authorized()
            and re.fullmatch(r"/codex/models(?:\?client_version=[\d.]+)?", self.path)
            and "codex" in self.server.upstreams
        ):
            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Bearer eyJ") or self.headers.get("x-api-key"):
                self.send_body(401, b'{"error":"Subscription OAuth required"}')
                return
            try:
                request = urllib.request.Request(
                    self.server.upstreams["codex"] + self.path[len("/codex") :],
                    headers={
                        "Authorization": auth,
                        "chatgpt-account-id": self.headers.get(
                            "chatgpt-account-id", ""
                        ),
                    },
                )
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({}), NoRedirect()
                )
                with opener.open(request, timeout=30) as upstream:
                    body = upstream.read(LIMIT + 1)
                    if len(body) <= LIMIT and getattr(upstream, "length", None) not in (None, 0):
                        raise http.client.IncompleteRead(body)
                    if len(body) > LIMIT:
                        raise ValueError("Catalog size exceeded")
                    self.send_body(200, body)
            except urllib.error.HTTPError as exc:
                exc.close()
                self.send_body(
                    exc.code if exc.code in {401, 403, 429} else 502,
                    b'{"error":"Subscription catalog unavailable"}',
                )
            except (OSError, ValueError, http.client.HTTPException):
                self.send_body(502, b'{"error":"Subscription catalog unavailable"}')
        else:
            self.send_body(
                400 if self.authorized() else 401,
                b'{"error":"Unauthorized or unsupported endpoint"}',
            )

    def do_POST(self):
        """Handle do POST."""
        self._request_body_consumed = False
        # Only fixed inference routes enter the ledger; never store caller paths,
        # query strings, error bodies, arbitrary headers or request/response text.
        request_path = self.path.partition("?")[0]
        provider = (
            "claude" if request_path in {"/claude/v1/messages", "/claude/v1/messages/count_tokens"}
            else "codex" if request_path == "/codex/responses"
            else "xai" if request_path in {"/xai/v1/responses", "/xai/v1/chat/completions"}
            else None
        )
        self.audit_metadata = None
        if provider is None or self.server.audit is None:
            self._do_POST()
            return
        # Audit work outlives inference admission and also covers rejected
        # requests. Keep its owner alive until completion or retry enqueue ends.
        with self.server.admission:
            reserved = not self.server.closing
            if reserved:
                self.server.active_audit_handlers += 1
        if not reserved:
            self.send_body(503, b'{"error":"Gateway shutting down; no request forwarded"}')
            return
        try:
            self._audited_POST(provider, request_path)
        finally:
            with self.server.admission:
                self.server.active_audit_handlers -= 1
                self.server.admission.notify_all()

    def _audited_POST(self, provider, request_path):
        audit = self.server.audit
        assert audit is not None
        agent = {"claude": "Claude Code", "codex": "Codex", "xai": "xAI client"}[provider]
        subscription = {"claude": "claude_subscription", "codex": "chatgpt_subscription",
                        "xai": "api_key"}[provider]
        origin = urllib.parse.urlsplit(self.server.upstreams.get(provider, ""))
        destination = origin.scheme + "://" + origin.netloc.split("@")[-1] + origin.path
        try:
            request_id = audit.begin(
                agent, provider, subscription, request_path, destination,
            )
        except sqlite3.Error:
            self.server.record_audit_error("admission")
            self.send_body(503, b'{"error":"Audit storage unavailable; no request forwarded"}')
            return
        self.audit_metadata = {
            "agent": agent, "account_ref": None, "credential_ref": None,
            "model": None, "status": None, "outcome": "blocked",
            "upstream_attempted": 0, "input_bytes": 0, "masked_bytes": 0,
            "output_bytes": 0, "new_aliases": 0,
        }
        started = time.perf_counter()
        try:
            self._do_POST()
        finally:
            meta = self.audit_metadata
            meta["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
            if meta["status"] is None:
                meta["outcome"] = "incomplete"
            elif meta["status"] == 200:
                meta["outcome"] = "completed"
            try:
                audit.finish(request_id, meta)
            except AuditMaintenanceError:
                self.server.record_audit_error("maintenance")
            except sqlite3.Error:
                self.server.record_audit_error("completion")

    def _do_POST(self):
        if self.path == "/admin/api/mask-rules":
            save_mask_rules(self)
            return
        if self.path == "/admin/api/domain-policy":
            from secure_gateway.gateway_admin import save_domain_policy
            save_domain_policy(self)
            return
        if not self.authorized():
            self.send_body(401, b'{"error":"Unauthorized"}')
            return
        if self.path == "/shutdown":
            from threading import Thread

            with self.server.admission:
                self.server.closing = True
            raw_grace = self.headers.get("X-SecureGateway-Shutdown-Grace-Ms", "30000")
            grace_ms = int(raw_grace) if len(raw_grace) <= 5 and raw_grace.isascii() and raw_grace.isdigit() else 30000
            grace = grace_ms / 1000 if 100 <= grace_ms <= 30000 else 30
            try:
                self.send_body(200, b'{"stopping":true}')
            finally:
                Thread(target=self.server.drain_and_shutdown, args=(grace,), daemon=True).start()
            return
        if self.path == "/reset":
            try:
                if self.headers.get("Transfer-Encoding") or self.headers.get(
                    "Content-Encoding"
                ):
                    raise ValueError("Unsupported encoding.")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024:
                    raise ValueError("Invalid reset request.")
                raw = self.rfile.read(length)
                self._request_body_consumed = True
                if len(raw) != length:
                    raise ValueError("Incomplete reset request body.")
                payload = json.loads(raw)
                if not isinstance(payload, dict) or set(payload) - {"agent"}:
                    raise ValueError("Invalid reset request.")
                agent = payload.get("agent", "all")
                if not isinstance(agent, str):
                    raise ValueError("Invalid provider.")
                self.server.reset(agent)
                self.send_body(200, b'{"reset":true}')
            except (ValueError, OSError):
                self.send_body(
                    409,
                    b'{"error":"Reset refused; stop active requests and retry with a valid provider"}',
                )
            return
        routes = {
            "/claude/v1/messages": ("claude", "/v1/messages"),
            "/claude/v1/messages/count_tokens": ("claude", "/v1/messages/count_tokens"),
            "/codex/responses": ("codex", "/responses"),
            "/xai/v1/responses": ("xai", "/v1/responses"),
            "/xai/v1/chat/completions": ("xai", "/v1/chat/completions"),
        }
        request_path, _, query = self.path.partition("?")
        if not supported_query(query):
            self.send_body(400, b'{"error":"Unsupported query parameters; no request forwarded"}')
            return
        route = routes.get(request_path)
        if not route:
            self.send_body(
                400, b'{"error":"Unsupported endpoint; no request forwarded"}'
            )
            return
        agent, path = route
        if agent in API_AUTH_PREFIXES and agent not in self.server.api_upstreams:
            self.send_body(
                400,
                b'{"error":"API mode is not enabled for this gateway instance"}',
            )
            return
        if agent not in self.server.upstreams:
            self.send_body(
                400, b'{"error":"Provider is not enabled for this gateway instance"}'
            )
            return
        auth = self.headers.get("Authorization", "")
        if agent in API_AUTH_PREFIXES:
            # Explicit API mode: the caller's own API key is forwarded to the
            # fixed origin. Subscription tokens are not accepted and no
            # automatic fallback to or from subscription auth exists.
            valid_auth = auth.startswith(API_AUTH_PREFIXES[agent])
        else:
            # Subscription-only boundary: never silently switch to paid API keys.
            valid_auth = (
                auth.startswith("Bearer sk-ant-oat")
                if agent == "claude"
                else auth.startswith("Bearer eyJ")
            )
        if not valid_auth or self.headers.get("x-api-key"):
            self.send_body(
                401,
                b'{"error":"xAI API key required; subscription credentials refused"}'
                if agent in API_AUTH_PREFIXES
                else b'{"error":"Existing subscription OAuth login required; API keys refused"}',
            )
            return
        if not self.server.try_admit(agent):
            self.response_headers = {"Retry-After": "1"}
            self.send_body(503 if self.server.closing else 429,
                           b'{"error":"Gateway inference capacity unavailable; retry later"}')
            return
        meta = self.audit_metadata
        timings: dict[str, Any] = {"provider": agent}
        request_started = time.perf_counter()
        stage_started = request_started
        session = None
        if meta is not None:
            meta["credential_ref"] = anonymous_ref(self.server.token, "credential", auth)
            if agent == "codex":
                meta["account_ref"] = anonymous_ref(
                    self.server.token, "account", self.headers.get("chatgpt-account-id", ""),
                )
            source = self.headers.get("X-SecureGateway-Agent")
            if agent == "xai" and source in {"Grok Build", "Antigravity SDK"}:
                meta["agent"] = source
        try:
            if self.headers.get("Transfer-Encoding") or self.headers.get(
                "Content-Encoding"
            ):
                raise ValueError("Encoded/chunked requests unsupported.")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= LIMIT:
                raise ValueError("Request size limit exceeded.")
            raw = self.rfile.read(length)
            self._request_body_consumed = True
            if len(raw) != length:
                raise ValueError("Incomplete request body.")
            if meta is not None:
                meta["input_bytes"] = len(raw)
            payload = strict_json_loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("Request must be a JSON object.")
            if meta is not None and isinstance(payload.get("model"), str):
                model = payload["model"]
                if MODEL_ID_PATTERN.fullmatch(model):
                    meta["model"] = model
            # Refresh stays CLI-owned; changing bearer tokens must not change aliases.
            conversation = self.headers.get("session_id") or self.headers.get("X-SecureGateway-Session")
            if conversation:
                conversation = self.headers.get("chatgpt-account-id", "") + "\0" + conversation
            session = self.server.get_session(agent, conversation, pin=True)
            stage_started = time.perf_counter()
            with session.lock:
                timings["mask_lock_wait_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
                stage_started = time.perf_counter()
                dialect = (
                    "chat_completions"
                    if path.endswith("/chat/completions")
                    else "responses"
                    if agent in API_AUTH_PREFIXES
                    else None
                )
                before = len(session.session.forward_store)
                masked = session.request(payload, dialect=dialect)
                timings["mask_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
                if meta is not None:
                    meta["new_aliases"] = max(0, len(session.session.forward_store) - before)
                session.session.touch()
            headers = {
                "Content-Type": "application/json",
                "Authorization": auth,
                "Accept": "text/event-stream"
                if masked.get("stream")
                else "application/json",
            }
            for key in (
                ()
                if agent in API_AUTH_PREFIXES
                else (
                    "anthropic-version",
                    "anthropic-beta",
                    "chatgpt-account-id",
                    "OpenAI-Beta",
                    "User-Agent",
                    "originator",
                    "session_id",
                    "x-codex-beta-features",
                )
            ):
                if self.headers.get(key):
                    headers[key] = self.headers[key]
            masked_data = strict_json_dumps(masked, ensure_ascii=False).encode()
            if meta is not None:
                meta["masked_bytes"] = len(masked_data)
            request = urllib.request.Request(
                self.server.upstreams[agent] + path + ("?" + query if query else ""),
                data=masked_data,
                headers=headers,
            )
            # Disable redirects and environment proxies: credentials stay at the fixed origin.
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}), NoRedirect()
            )
            try:
                if meta is not None:
                    meta["upstream_attempted"] = 1
                    meta["outcome"] = "transport_error"
                stage_started = time.perf_counter()
                upstream_response = opener.open(request, timeout=600)
                timings["upstream_headers_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
            except urllib.error.HTTPError:
                raise
            except (OSError, http.client.HTTPException) as exc:
                reason = getattr(exc, "reason", exc)
                status = 504 if isinstance(reason, (TimeoutError, socket.timeout)) else 502
                self.send_body(status, b'{"error":"Upstream transport unavailable"}')
                return
            with upstream_response as upstream:
                self.capture_response_headers(upstream.headers)
                content_type = upstream.headers.get("Content-Type", "application/json")
                if masked.get("stream") and content_type.split(";", 1)[0].strip().lower() == "text/event-stream":
                    try:
                        persisted_state = None
                        def persist_completion():
                            nonlocal persisted_state
                            with session.lock:
                                state = (len(session.session.forward_store),
                                         getattr(session.engine, "cache_epoch", 0), frozenset(session.opaque))
                                if state != persisted_state:
                                    save_started = time.perf_counter()
                                    self.server.save(agent, session)
                                    timings["save_ms"] = timings.get("save_ms", 0) + round((time.perf_counter() - save_started) * 1000, 2)
                                    persisted_state = state
                        relay_stream(self, upstream, session, dialect, limit=LIMIT, before_complete=persist_completion)
                        timings["first_event_ms"] = self.stream_metrics["first_event_ms"]
                        timings["upstream_body_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
                        persist_completion()
                    except (ValueError, TypeError, KeyError, OSError, http.client.HTTPException):
                        if meta is not None:
                            meta["status"] = 502
                            meta["outcome"] = "stream_error"
                        # Headers have already been sent. Close rather than
                        # forge a successful completion or send a second HTTP response.
                        self.close_connection = True
                    return
                try:
                    body = upstream.read(LIMIT + 1)
                    timings["upstream_body_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
                    if len(body) <= LIMIT and getattr(upstream, "length", None) not in (None, 0):
                        raise http.client.IncompleteRead(body)
                except (OSError, http.client.HTTPException) as exc:
                    reason = getattr(exc, "reason", exc)
                    status = 504 if isinstance(reason, TimeoutError) else 502
                    self.send_body(status, b'{"error":"Upstream transport unavailable"}')
                    return
                if len(body) > LIMIT:
                    self.send_body(502, b'{"error":"Upstream response size limit exceeded"}')
                    return
                content_type = upstream.headers.get(
                    "Content-Type", "application/json"
                )
                if masked.get("stream") and body.startswith(
                    (b"event:", b"data:", b":")
                ):
                    content_type = "text/event-stream"
                with session.lock:
                    stage_started = time.perf_counter()
                    if meta is not None:
                        meta["outcome"] = "restore_error"
                    try:
                        restored = session.response(body, content_type, dialect=dialect)
                        timings["restore_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
                    except (ValueError, TypeError, AttributeError, KeyError, RecursionError):
                        self.send_body(502, b'{"error":"Upstream response could not be safely restored"}')
                        return
                    stage_started = time.perf_counter()
                    self.server.save(agent, session)
                    timings["save_ms"] = round((time.perf_counter() - stage_started) * 1000, 2)
            self.send_body(200, restored, content_type)
        except urllib.error.HTTPError as exc:
            if meta is not None:
                meta["outcome"] = "upstream_rejected"
            self.capture_response_headers(exc.headers)
            status, body = self.server.format_upstream_error(exc)
            self.send_body(status, body)
        except OSError:
            if meta is not None:
                meta["outcome"] = "local_io_error"
            self.send_body(500, b'{"error":"Privacy gateway local I/O failed; request could not be completed"}')
        except (
            ValueError,
            TypeError,
            KeyError,
            RecursionError,
            http.client.HTTPException,
        ) as exc:
            self.send_body(
                400,
                strict_json_dumps(public_request_error(exc)).encode(),
            )
        finally:
            if session is not None:
                with session.lock:
                    session.active_requests -= 1
            timings["total_ms"] = round((time.perf_counter() - request_started) * 1000, 2)
            with self.server.admission:
                self.server.recent_timings.append(timings)
            self.server.release_admission(agent)


def supported_query(query):
    """Handle supported query."""
    if not query:
        return True
    if len(query) > 256:
        return False
    try:
        pairs = urllib.parse.parse_qsl(query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return False
    if len({key for key, _ in pairs}) != len(pairs):
        return False
    return all(
        (key in {"beta", "stream"} and value in {"true", "false"})
        or (key == "client_version" and re.fullmatch(r"[0-9]{1,4}(?:\.[0-9]{1,4}){0,3}", value))
        or (key == "api-version" and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value))
        for key, value in pairs
    )


PUBLIC_ERROR_TYPES = {
    "invalid_request_error",
    "authentication_error",
    "permission_error",
    "not_found_error",
    "rate_limit_error",
    "api_error",
    "overloaded_error",
}
PUBLIC_ERROR_CODES = {
    "context_length_exceeded",
    "rate_limit_exceeded",
    "model_not_found",
    "invalid_api_key",
    "insufficient_quota",
    "server_error",
    "invalid_request",
    "request_too_large",
    "overloaded_error",
}
UPSTREAM_ERROR_STATUSES = {
    400,
    401,
    403,
    404,
    408,
    413,
    422,
    429,
    500,
    502,
    503,
    504,
    529,
}


def sanitized_upstream_error(exc, *, on_failure: Callable[[], None] | None = None,
                             on_close_failure: Callable[[], None] | None = None):
    """Return a sanitized public error for an upstream HTTP failure; never exposes the upstream body."""
    status = exc.code if exc.code in UPSTREAM_ERROR_STATUSES else 502
    error = {"message": "Upstream rejected the request."}
    try:
        body = exc.read(LIMIT + 1)
        if len(body) <= LIMIT:
            payload = json.loads(body)
            upstream = payload.get("error", {}) if isinstance(payload, dict) else {}
            if isinstance(upstream, dict):
                # Anthropic supplies this condition as a 400 message, without
                # a machine-readable code. Classify only the fixed prefix;
                # never echo token counts, filenames or other upstream text.
                message = upstream.get("message")
                if (
                    status == 400
                    and upstream.get("type") == "invalid_request_error"
                    and isinstance(message, str)
                    and re.match(r"\Aprompt is too long(?:\s*:|\s*;|\s*$)", message, re.IGNORECASE)
                ):
                    error["code"] = "context_length_exceeded"
                for field, allowed in (
                    ("type", PUBLIC_ERROR_TYPES),
                    ("code", PUBLIC_ERROR_CODES),
                ):
                    value = upstream.get(field)
                    if isinstance(value, str) and value in allowed:
                        error[field] = value
        elif on_failure is not None:
            on_failure()
        else:
            _warn_diagnostic("upstream_error_body")
    except (ValueError, OSError, http.client.HTTPException):
        if on_failure is not None:
            on_failure()
        else:
            _warn_diagnostic("upstream_error_body")
    finally:
        try:
            exc.close()
        except Exception:
            if on_close_failure is not None:
                on_close_failure()
            else:
                _warn_diagnostic("upstream_error_stream_close")
    if status == 413 or error.get("code") == "context_length_exceeded":
        error["message"] = (
            "Prompt is too long; reduce context or compact the conversation."
        )
    return status, json.dumps({"error": error}).encode()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Redirect handler that prevents automatic upstream redirects."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Handle redirect request."""
        return None
