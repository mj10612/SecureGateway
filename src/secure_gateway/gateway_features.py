"""Per-session masking features (issue #354).

``GatewayFeatures()`` (the library default) enables nothing. Gateway settings
(``resolve_settings``) enable the jointly adopted features by default from
2.17.0: #310 on, #316 B and #318 on but active only with a trusted policy; see
``SETTING_DEFAULTS``.

The candidate features were first evaluated as process-global experiment
profiles (``experiment_profiles.candidate_profile``). This module carries the
same behaviour as an immutable value attached to one ``GatewaySession`` and its
engine, so any combination can be enabled in one process and two sessions,
providers or concurrent requests never share feature state. The experiment
profiles remain a thin compatibility wrapper over these flags.

Trusted local policy (correction records, document hashes, unit policies) is an
input from the local host or configuration, never from model or request text.
Diagnostics expose feature names, sources and booleans only, never policy terms.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
from typing import Any
import unicodedata

from secure_gateway.domain_dictionaries import protect_chunks
from secure_gateway.experiment_bundle import bundle_spans
from secure_gateway.experiment_korean import preserve_spans as korean_spans
from secure_gateway.experiment_name_context import trusted_name_spans, user_texts
from secure_gateway.gateway_source import looks_like_source
from secure_gateway.models import MaskMode, TokenType

# name -> (issue, gateway-wide configuration support)
FEATURES: dict[str, tuple[int, str]] = {
    "ko_conjugation_split": (309, "boolean"),
    "contextual_name_spans": (310, "boolean"),
    "scoped_corrections": (316, "records-file"),
    "attribute_bundle": (318, "session-only"),
    "local_arithmetic": (319, "boolean"),
}
# Gateway-settings defaults (2.17.0, after the joint ADOPT of #310/#316 B/#318):
# "on" = enabled unless explicitly turned off; "policy" = enabled, but active only
# when a trusted local policy is configured (without one it is a no-op and never
# blocks gateway start); "off" = opt-in. Library constructors
# (GatewaySession/PrivacyGateway without ``features``) keep DEFAULT_FEATURES (all off).
SETTING_DEFAULTS: dict[str, str] = {
    "ko_conjugation_split": "off",
    "contextual_name_spans": "on",
    "scoped_corrections": "policy",
    "attribute_bundle": "policy",
    "local_arithmetic": "off",
}
CORRECTIONS_PASSWORD_ENV = "SECURE_GATEWAY_CORRECTIONS_PASSWORD"
_POLICY_FIELDS = {
    "scoped_corrections": {"trusted_project", "workspace", "language", "policyrecords", "public_records"},
    "attribute_bundle": {"document_sha256", "scope", "required_fields", "protect_fields"},
    "local_arithmetic": {"allowed", "result_units", "max_calls"},
}
_TRUE = {"1", "true", "on", "yes", "enabled"}
_FALSE = {"0", "false", "off", "no", "disabled"}


def _overlaps(span, blocked):
    return any(start < span[1] and end > span[0] for start, end in blocked)


def _term_spans(text, terms):
    """Small session/rule inventory only; no source normalization is returned."""
    spans = []
    normalized = unicodedata.normalize("NFC", text)
    for term in terms:
        if not term:
            continue
        # Exact offsets for the ordinary case. Ambiguous NFC/NFD offsets block
        # the whole candidate preservation rather than invent an alignment.
        if term not in text and unicodedata.normalize("NFC", term) in normalized:
            return [(0, len(text))]
        start = text.find(term)
        while start >= 0:
            spans.append((start, start + len(term)))
            start = text.find(term, start + len(term))
    return spans


def correction_terms(policy):
    """Return active scoped terms; trusted local scope is never model text."""
    from secure_gateway.experiment_corrections import validate_record

    if set(policy) - {"trusted_project", "workspace", "language", "policyrecords"}:
        raise ValueError("Unsupported correction policy fields")
    trusted, workspace = policy.get("trusted_project"), policy.get("workspace")
    language, records = policy.get("language"), policy.get("policyrecords", [])
    if (not isinstance(trusted, str) or not trusted or not isinstance(workspace, str)
            or language not in {"en", "ko"} or not isinstance(records, list) or len(records) > 256):
        raise ValueError("Invalid scoped correction policy")
    result = []
    now = datetime.now(timezone.utc).timestamp()
    for record in records:
        if isinstance(record, dict) and set(record) == {"term", "project", "language", "source", "policy_version", "created_at", "expires_at", "revoked"}:
            validate_record(record)
            record = {key: record[key] for key in ("term", "project", "language", "source", "expires_at", "revoked")}
        if (not isinstance(record, dict) or set(record) != {"term", "project", "language", "source", "expires_at", "revoked"}
                or not isinstance(record["term"], str) or not 1 <= len(record["term"]) <= 256
                or not isinstance(record["project"], str) or record["language"] not in {"en", "ko"}
                or record["source"] != "explicit-local-correction" or type(record["revoked"]) is not bool
                or type(record["expires_at"]) not in {int, float}):
            raise ValueError("Invalid local correction record")
        if (trusted == workspace == record["project"] and language == record["language"]
                and not record["revoked"] and record["expires_at"] > now):
            result.append(record["term"])
    return tuple(result)


def _policy(name, value):
    if value is None or value is False:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("Feature policy must be a local object: " + name)
    if set(value) - _POLICY_FIELDS[name]:
        raise ValueError("Unsupported feature policy fields: " + name)
    return deepcopy(dict(value))


@dataclass(frozen=True, eq=False)
class GatewayFeatures:
    """Immutable per-session feature selection; the default enables nothing.

    Boolean features take ``True``/``False``. Policy features are enabled by a
    trusted local policy object and disabled by ``None``.
    """

    ko_conjugation_split: bool = False
    contextual_name_spans: bool = False
    scoped_corrections: Mapping[str, Any] | None = None
    attribute_bundle: Mapping[str, Any] | None = None
    local_arithmetic: Mapping[str, Any] | bool | None = None
    correction_terms: tuple[str, ...] = field(init=False, default=())
    public_terms: tuple[str, ...] = field(init=False, default=())

    def __post_init__(self):
        for name in ("ko_conjugation_split", "contextual_name_spans"):
            if type(getattr(self, name)) is not bool:
                raise ValueError("Feature flag must be a boolean: " + name)
        local = {} if self.local_arithmetic is True else self.local_arithmetic
        object.__setattr__(self, "local_arithmetic", _policy("local_arithmetic", local))
        object.__setattr__(self, "attribute_bundle", _policy("attribute_bundle", self.attribute_bundle))
        scoped = _policy("scoped_corrections", self.scoped_corrections)
        object.__setattr__(self, "scoped_corrections", scoped)
        if scoped is not None:
            base = {key: value for key, value in scoped.items() if key != "public_records"}
            object.__setattr__(self, "correction_terms", correction_terms(base))
            if "public_records" in scoped:
                public = dict(base)
                public["policyrecords"] = scoped["public_records"]
                object.__setattr__(self, "public_terms", correction_terms(public))

    @property
    def any_enabled(self) -> bool:
        """Return whether any feature is selected."""
        return bool(self.enabled_names())

    def enabled_names(self) -> tuple[str, ...]:
        """Return enabled feature names in registry order; never policy contents."""
        return tuple(name for name in FEATURES
                     if getattr(self, name) is True or isinstance(getattr(self, name), Mapping))


DEFAULT_FEATURES = GatewayFeatures()


# Engine hooks ---------------------------------------------------------------

def feature_chunk_spans(engine, text):
    """Return additional protected spans for one engine chunking pass."""
    features = engine.features
    if features.scoped_corrections is not None and features.correction_terms:
        return _term_spans(text, features.correction_terms)
    return []


def apply_chunk_features(engine, text, chunks):
    """Union feature protection with chunks already protected by domain policy."""
    return protect_chunks(text, chunks, feature_chunk_spans(engine, text))


def apply_mask_text_features(engine, args, kwargs, private_context):
    """Adjust one ``mask_text`` call in place for the engine's own features."""
    from secure_gateway import gateway

    features = engine.features
    owner = engine.owner
    text = args[0] if args else kwargs["text"]
    public_terms = features.public_terms
    if (features.scoped_corrections is not None and public_terms and not private_context and owner is not None
            and (not getattr(owner, "_feature_request", False)
                 or getattr(owner, "_public_user_only", False))
            and getattr(owner, "_evaluation_prose", False)
            and kwargs.get("mode") != MaskMode.AGGRESSIVE):
        # The evaluation arm only considers whole, alphabetic name-fallback
        # tokens. Opaque token kinds, identifiers, domain terms, existing
        # mappings, forced rules and additional protect rules always win.
        protected = tuple(owner.forced_rules()) + tuple(features.correction_terms)
        protected += tuple(owner.session.forward_store.originals_in(text))
        language = kwargs.get("language", "en")
        blocked = _term_spans(text, protected + tuple(gateway.domain_terms(text, language)))
        if engine.domain_spans is not None:
            blocked.extend(engine.domain_spans(text))
        safe = set()
        offset = 0
        for chunk in engine.tokenizer.tokenize(text):
            start, offset = offset, offset + len(chunk.text)
            word = chunk.text
            if (word in public_terms and chunk.kind == "WORD" and word.isalpha()
                    and not gateway._identifier_shaped(word)
                    and not gateway._identifier_context(text, start, offset)
                    and gateway._name_fallback(text, start, word, language)
                    and not _overlaps((start, offset), blocked)):
                safe.add((start, offset))
        if safe:
            terms = set(kwargs.get("sensitive_terms") or ())
            terms.difference_update(text[start:end] for start, end in safe)
            kwargs["sensitive_terms"] = terms
            kwargs["preserve_spans"] = frozenset(kwargs.get("preserve_spans", ())) | safe
    if features.ko_conjugation_split and not private_context and kwargs.get("mode") != MaskMode.AGGRESSIVE:
        candidates = korean_spans(text)
        blocked = _term_spans(text, kwargs.get("sensitive_terms") or ())
        if owner is not None:
            blocked.extend(_term_spans(text, owner.forced_rules()))
            blocked.extend(_term_spans(text, owner.session.forward_store.originals_in(text)))
        if engine.domain_spans is not None:
            blocked.extend(engine.domain_spans(text))
        safe = {span for span in candidates if not _overlaps(span, blocked)}
        kwargs["preserve_spans"] = frozenset(kwargs.get("preserve_spans", ())) | safe


# Session hooks --------------------------------------------------------------

def _register(session, text, start, end):
    session.engine._get_or_create_surrogate(
        text[start:end], TokenType.LITERAL, session.session.generator,
        session.session.forward_store, session.session.reverse_store)


def register_introductions(session, text):
    """Register direct, unquoted user-prose name introductions in this session."""
    if looks_like_source(text[:4096]):
        return
    try:
        spans = trusted_name_spans(text)
    except ValueError:
        return
    for start, end in spans:
        _register(session, text, start, end)


def before_mask_unforced(session, text, code):
    """Register feature-owned protection before ordinary unforced masking."""
    features = session.features
    if features.contextual_name_spans and not code and not session._feature_request:
        register_introductions(session, text)
    if features.attribute_bundle is not None and not code:
        policy = features.attribute_bundle
        matches_document = sha256(text.encode()).hexdigest() == policy.get("document_sha256")
        spans = [] if session._feature_request and not matches_document else bundle_spans(text, dict(policy))
        for start, end in spans:
            _register(session, text, start, end)


def mask_prose(session, text, preserve_task_words, skill_verbs, model_context_complete):
    """Apply prose-level features, delegating each piece to the core prose masker."""
    features = session.features
    core = session._mask_prose_core
    if features.contextual_name_spans and preserve_task_words:
        known = session.session.forward_store.originals_in(text)
        for name in sorted(known, key=len, reverse=True):
            if not name or not all("가" <= char <= "힣" for char in name):
                continue
            for suffix in ("입니다", "이에요", "예요"):
                position = text.find(name + suffix)
                suffix_start = position + len(name)
                if position < 0 or session.session.forward_store.originals_in(suffix):
                    continue
                protected = tuple(session.forced_rules()) + tuple(term for term in known if term != name)
                if _overlaps((suffix_start, suffix_start + len(suffix)), _term_spans(text, protected)):
                    continue
                if session.engine.domain_spans is not None and _overlaps(
                        (suffix_start, suffix_start + len(suffix)), session.engine.domain_spans(text)):
                    continue
                left = core(text[:suffix_start], preserve_task_words, skill_verbs, model_context_complete)
                right = core(text[suffix_start + len(suffix):], preserve_task_words, skill_verbs, model_context_complete)
                return left + suffix + right
    if features.scoped_corrections is not None and features.public_terms:
        session._evaluation_prose = True
        try:
            return core(text, preserve_task_words, skill_verbs, model_context_complete)
        finally:
            session._evaluation_prose = False
    return core(text, preserve_task_words, skill_verbs, model_context_complete)


def begin_request(session, payload):
    """Prepare per-request feature state before the request is masked."""
    features = session.features
    if features.scoped_corrections is not None:
        contents = payload.get("messages", payload.get("input"))
        session._public_user_only = (
            set(payload).issubset({"model", "input", "messages"})
            and isinstance(contents, list) and bool(contents)
            and all(isinstance(item, dict) and item.get("role") == "user"
                    and set(item).issubset({"role", "content"}) and isinstance(item.get("content"), str)
                    for item in contents))
    if features.contextual_name_spans:
        for text in user_texts(payload):
            register_introductions(session, text)


def tool_dispatcher(session):
    """Return the local arithmetic dispatcher selected by this session, if any."""
    policy = session.features.local_arithmetic
    if policy is None:
        return None
    from secure_gateway.private_arithmetic import LocalArithmeticDispatcher

    return LocalArithmeticDispatcher(
        session,
        allowed=policy.get("allowed"),
        result_units=policy.get("result_units"),
        max_calls=policy.get("max_calls", 16),
    )


# Gateway-wide settings ------------------------------------------------------

def _parse_bool(value, name):
    if type(value) is bool:
        return value
    if isinstance(value, str) and value.strip().casefold() in _TRUE | _FALSE:
        return value.strip().casefold() in _TRUE
    raise ValueError("Invalid feature setting: " + name)


def _config_value(name, raw):
    """Normalize one configuration-file value to (enabled, options)."""
    if name == "scoped_corrections" and isinstance(raw, dict):
        if set(raw) - {"enabled", "project", "language", "records_file"}:
            raise ValueError("Unsupported scoped_corrections settings")
        return _parse_bool(raw.get("enabled", True), name), dict(raw)
    return _parse_bool(raw, name), {}


def _load_corrections(options, environ):
    from secure_gateway.experiment_corrections import load_records

    project, language, records_file = options.get("project"), options.get("language"), options.get("records_file")
    if (not isinstance(project, str) or not project or language not in {"en", "ko"}
            or not isinstance(records_file, str) or not records_file):
        raise ValueError("scoped_corrections requires project, language and records_file settings.")
    password = environ.get(CORRECTIONS_PASSWORD_ENV)
    if not password:
        raise ValueError("scoped_corrections requires " + CORRECTIONS_PASSWORD_ENV + ".")
    path = Path(records_file).expanduser()
    if path.is_symlink() or not path.is_file():
        raise ValueError("scoped_corrections records file is missing or unsafe.")
    try:
        records = load_records(path, password)
    except (ValueError, OSError):
        raise ValueError("scoped_corrections records could not be loaded.") from None
    return {"trusted_project": project, "workspace": project, "language": language, "policyrecords": records}


def resolve_settings(config: Mapping[str, Any] | None = None, *, environ: Mapping[str, str] | None = None,
                     cli: Mapping[str, bool] | None = None, all_off: bool = False):
    """Resolve gateway-wide features with precedence CLI > environment > config > default.

    Returns ``(GatewayFeatures, report)``. The report lists, per feature, its
    default (``SETTING_DEFAULTS``), requested and active state and source; it
    never contains policy contents. ``all_off`` (``--features-off``) disables
    every feature regardless of source. A policy feature that is on only by
    default and has no configured policy is inactive (a no-op); an explicit
    request without a usable policy still stops the gateway.
    """
    environ = os.environ if environ is None else environ
    section = (config or {}).get("features", {})
    if not isinstance(section, dict) or set(section) - set(FEATURES):
        raise ValueError("Unknown or invalid gateway feature settings.")
    cli = dict(cli or {})
    if set(cli) - set(FEATURES) or any(type(value) is not bool for value in cli.values()):
        raise ValueError("Unknown gateway feature option.")
    report: dict[str, dict[str, Any]] = {}
    kwargs: dict[str, Any] = {}
    for name, (issue, support) in FEATURES.items():
        mode = SETTING_DEFAULTS[name]
        enabled, source, options = mode != "off", "default", {}
        if name in section:
            enabled, options = _config_value(name, section[name])
            source = "config"
        env_name = "SECURE_GATEWAY_FEATURE_" + name.upper()
        if environ.get(env_name) not in (None, ""):
            enabled, source = _parse_bool(environ[env_name], env_name), "env"
        if name in cli:
            enabled, source = cli[name], "cli"
        if all_off:
            enabled, source = False, "cli-off"
        active, reason = enabled, None
        if enabled:
            if support == "session-only":
                if source != "default":
                    raise ValueError(name + " requires a per-document trusted policy; enable it per session, not gateway-wide.")
                # Default-on, policy-gated: gateway settings have no per-document policy source.
                active, reason = False, "per-session-policy-only"
            elif name == "scoped_corrections":
                if source == "default" and not options:
                    active, reason = False, "no-policy-configured"
                else:
                    kwargs[name] = _load_corrections(options, environ)
            elif name == "local_arithmetic":
                kwargs[name] = {}
            else:
                kwargs[name] = True
        report[name] = {"issue": issue, "default": mode != "off", "default_mode": mode, "enabled": enabled,
                        "active": active, "source": source, "gateway_setting": support}
        if reason:
            report[name]["inactive_reason"] = reason
    return GatewayFeatures(**kwargs), report


def report_for(features: GatewayFeatures):
    """Report features passed directly to a gateway constructor (library use).

    Gateway-settings defaults do not apply to direct construction: the library
    default is ``DEFAULT_FEATURES`` (all off), reported as ``default: False``.
    """
    enabled = set(features.enabled_names())
    return {name: {"issue": issue, "default": False, "default_mode": "off", "enabled": name in enabled,
                   "active": name in enabled, "source": "constructor" if name in enabled else "default",
                   "gateway_setting": support}
            for name, (issue, support) in FEATURES.items()}
