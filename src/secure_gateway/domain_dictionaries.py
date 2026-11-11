"""Versioned local protection terms with one shared, bounded Aho–Corasick index."""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from array import array
from collections import deque
from functools import lru_cache
from hashlib import sha256
from io import StringIO
from pathlib import Path
from typing import Any

from secure_gateway.engine.tokenizer import TextChunk
from secure_gateway import gateway_vocabulary, gateway_public_vocabulary

DEFAULTS = {"defense": True, "automotive": False, "semiconductor": False}
MAX_FILE = 32 * 1024 * 1024

_DESIGNATOR_RE = re.compile(r"^[A-Za-z0-9]+(?:[/\-_.:][A-Za-z0-9]+)*$")
_KOREAN_PARTICLES = ("의", "는", "은", "를", "을", "에", "로", "와", "과", "도")
_STRIP_CHARS = "()[]{}<>\"'`~,;:?!"
_CLAUSE_DELIMITERS = frozenset(".!?。！？;\n\r")


class DomainSpans(list):
    """Spans produced by the domain catalog, with common-word policy already applied."""
    pass


class _IdentityOffsets:
    def __getitem__(self, index):
        return index, index + 1


class _PackedOffsets:
    def __init__(self):
        self.starts = array("I")
        self.ends = array("I")

    def append(self, value):
        self.starts.append(value[0])
        self.ends.append(value[1])

    def __getitem__(self, index):
        return self.starts[index], self.ends[index]

    def __setitem__(self, index, value):
        self.starts[index], self.ends[index] = value


def _clean_designator_candidate(token: str) -> str:
    t = token.strip(_STRIP_CHARS)
    for p in _KOREAN_PARTICLES:
        if t.endswith(p) and len(t) > len(p):
            t = t[:-len(p)].strip(_STRIP_CHARS)
            break
    return t


def _is_alphanumeric_designator(token: str) -> bool:
    t = _clean_designator_candidate(token)
    if not t or not _DESIGNATOR_RE.match(t):
        return False
    has_alpha = any(c.isalpha() for c in t)
    has_digit = any(c.isdigit() for c in t)
    return has_alpha and has_digit


@lru_cache(maxsize=17)
def _common_words(language: str) -> frozenset[str]:
    words: set[str] = set()
    try:
        words.update(gateway_vocabulary.ordinary_words(language))
    except (ValueError, KeyError):
        # intentional: language may not have packaged vocabulary; fallback to empty common words
        pass
    try:
        words.update(gateway_public_vocabulary.ordinary_words(language))
    except (ValueError, KeyError):
        # intentional: language may not have public vocabulary; fallback to empty common words
        pass
    return frozenset(words)


_HYPHENS = str.maketrans("-‐‑–—", "     ")


def _normalize_term_key(text: str) -> str:
    """Fast normalization of dictionary term keys without offset mapping."""
    if text.isascii():
        return " ".join(text.casefold().replace("-", " ").split())
    return " ".join(unicodedata.normalize("NFC", text).casefold().translate(_HYPHENS).split())


def _is_single_word_term(text: str) -> bool:
    if " " in text or "-" in text:
        return False
    return not any(c.isspace() or c in "‐‑–—" for c in text if ord(c) > 127)


def classify_domain_entries(entries: list[dict]) -> dict[str, str]:
    """Classify each concept as 'ambiguous-common' or 'distinctive'.

    Editorial core terms are curated domain concepts and remain distinctive.
    Public source-category labels whose single-word forms appear in ordinary/public
    vocabulary are classified as 'ambiguous-common'.
    """
    en_common = _common_words("en")
    ko_common = _common_words("ko")
    common_map = {"en": en_common, "ko": ko_common}
    classified = {}
    for entry in entries:
        cid = entry.get("id")
        if not cid:
            continue
        if entry.get("activation_status") == "active-editorial-core":
            classified[cid] = "distinctive"
            continue
        is_ambiguous = False
        for form in entry.get("forms", []):
            text = form.get("text", "")
            lang = form.get("language", "en")
            case_sensitive = form.get("case_sensitive", False)
            if _is_single_word_term(text):
                norm_text = text if case_sensitive else _normalize_term_key(text)
                c_set = common_map.get(lang)
                if c_set is None:
                    c_set = _common_words(lang)
                    common_map[lang] = c_set
                if norm_text in c_set:
                    is_ambiguous = True
                    break
        classified[cid] = "ambiguous-common" if is_ambiguous else "distinctive"
    return classified


def _case_form(text):
    """Normalize text for case-sensitive domain-form comparison.

    Applies NFC normalization, maps ASCII and Unicode dash characters to spaces,
    and collapses whitespace runs. Returns the normalized string; never ``None``.
    """
    text = unicodedata.normalize("NFC", text)
    return " ".join("".join(" " if char in "-‐‑–—" else char for char in text).split())


def normalize(text):
    """Normalize lookup only; keep a map to original grapheme-cluster offsets."""
    if text.isascii() and not any(part in text for part in ("\r", "\n", "\t", "\v", "\f", "  ", " -", "- ", "--")):
        # Common ASCII prose needs no per-character tuple allocation.
        return text.casefold().replace("-", " "), _IdentityOffsets()
    result = StringIO()
    offsets = _PackedOffsets()
    previous = None
    start = 0
    while start < len(text):
        end = start + 1
        # Include combining marks and decomposed Hangul syllables in one unit.
        if "\u1100" <= text[start] <= "\u1112" and end < len(text) and "\u1161" <= text[end] <= "\u1175":
            end += 1
            if end < len(text) and "\u11a8" <= text[end] <= "\u11c2":
                end += 1
        while end < len(text) and unicodedata.combining(text[end]):
            end += 1
        value = unicodedata.normalize("NFC", text[start:end]).casefold()
        for char in value:
            char = " " if char.isspace() or char in "-‐‑–—" else char
            if char == " " and previous == " ":
                offsets[-1] = (offsets[-1][0], end)
            else:
                result.write(char)
                offsets.append((start, end))
            previous = char
        start = end
    return result.getvalue(), offsets


class TermIndex:
    """Aho–Corasick index for bounded domain-term matching."""

    def __init__(self, terms):
        """Build a shared Aho–Corasick automaton over normalized domain terms.

        Terms are normalized with :func:`normalize`; each accepting state stores
        match metadata (normalized length, domain, case form, sensitivity, boundary).
        Failure links and output propagation are computed in a breadth-first pass.
        """
        self.edges: list[Any] = [{}]
        self.failure = array("I", [0])
        self.dict_link = array("I", [0])
        self.term_at_state: dict[int, list[tuple]] = {}
        self.build_count = len(terms)

        for item in terms:
            if len(item) == 5:
                term, domain, case_sensitive, boundary, is_ambiguous = item
            else:
                term, domain, case_sensitive, boundary = item[:4]
                is_ambiguous = False
            key = _normalize_term_key(term)
            is_multiword = (" " in key)
            state = 0
            for char in key:
                edge = self.edges[state]
                if edge is None:
                    new_state = len(self.edges)
                    self.edges[state] = (char, new_state)
                    self.edges.append(None)
                    self.failure.append(0)
                    self.dict_link.append(0)
                    state = new_state
                elif isinstance(edge, tuple):
                    if edge[0] == char:
                        state = edge[1]
                    else:
                        new_state = len(self.edges)
                        self.edges[state] = {edge[0]: edge[1], char: new_state}
                        self.edges.append(None)
                        self.failure.append(0)
                        self.dict_link.append(0)
                        state = new_state
                elif isinstance(edge, dict):
                    if char in edge:
                        state = edge[char]
                    else:
                        new_state = len(self.edges)
                        edge[char] = new_state
                        self.edges.append(None)
                        self.failure.append(0)
                        self.dict_link.append(0)
                        state = new_state
            if state not in self.term_at_state:
                self.term_at_state[state] = []
            self.term_at_state[state].append(
                (len(key), domain, _case_form(term) if case_sensitive else term, case_sensitive, boundary, is_ambiguous, is_multiword)
            )

        # Aho–Corasick failure links: on mismatch, fall back to the longest proper
        # suffix that is also a pattern prefix; propagate dictionary links along failures.
        root = self.edges[0]
        assert isinstance(root, dict)  # invariant: root edges[0] is always initialized to dict
        queue = deque(root.values())
        while queue:
            state = queue.popleft()
            edge = self.edges[state]
            if edge is None:
                continue
            items = [edge] if isinstance(edge, tuple) else list(edge.items())
            for char, child in items:
                queue.append(child)
                fallback = self.failure[state]
                while fallback:
                    f_edge = self.edges[fallback]
                    if f_edge is not None:
                        if isinstance(f_edge, tuple):
                            if f_edge[0] == char:
                                fallback = f_edge[1]
                                break
                        elif isinstance(f_edge, dict) and char in f_edge:
                            fallback = f_edge[char]
                            break
                    fallback = self.failure[fallback]
                else:
                    fallback = root.get(char, 0)
                self.failure[child] = fallback
                if fallback in self.term_at_state:
                    self.dict_link[child] = fallback
                else:
                    self.dict_link[child] = self.dict_link[fallback]

    def spans(self, text, enabled, max_matches=100_000):
        """Find protected original-text spans for enabled domains.

        Normalizes ``text`` once, walks the automaton, maps normalized positions
        back to original offsets, applies boundary/case checks, and merges to
        leftmost-longest / union for overlaps. Returns a list of ``(start, end)``
        character offsets in the original text, or ``[]`` when no domains are
        enabled or no matches survive.
        """
        if not any(enabled.values()):
            return DomainSpans()
        if len(text.encode()) > 16 * 1024 * 1024:
            raise ValueError("Dictionary input budget exceeded")
        normalized, offsets = normalize(text)
        raw_matches = []
        state = count = 0
        root = self.edges[0]
        assert isinstance(root, dict)  # invariant: root edges[0] is always initialized to dict
        for pos, char in enumerate(normalized):
            # Automaton walk: follow failure links until a transition matches.
            while state:
                edge = self.edges[state]
                if edge is not None:
                    if isinstance(edge, tuple):
                        if edge[0] == char:
                            state = edge[1]
                            break
                    elif isinstance(edge, dict) and char in edge:
                        state = edge[char]
                        break
                state = self.failure[state]
            else:
                state = root.get(char, 0)
            curr = state
            while curr:
                outputs = self.term_at_state.get(curr)
                if outputs:
                    for length, domain, term, sensitive_case, boundary, is_ambiguous, is_multiword in outputs:
                        count += 1
                        if count > max_matches:
                            raise ValueError("Dictionary matching budget exceeded")
                        if not enabled.get(domain):
                            continue
                        # Map normalized match end -> original [start, end) span.
                        start, end = offsets[pos - length + 1][0], offsets[pos][1]
                        # Boundary guard: reject alnum/underscore adjacency, with limited
                        # hangul-suffix and reviewed English-plural exceptions.
                        left, right = text[start - 1:start] if start else "", text[end:end + 1]
                        if left and (left.isalnum() or left == "_"):
                            continue
                        if right and (right.isalnum() or right == "_"):
                            if boundary != "hangul" or not ("가" <= right <= "힣" or "\u1100" <= right <= "\u11ff"):
                                # Reviewed English plurals only; never arbitrary suffixes.
                                following = text[end + 1:end + 2]
                                if sensitive_case or text[end:end + 1] != "s" or following.isalnum() or following == "_":
                                    continue
                        if sensitive_case and _case_form(text[start:end]) != term:
                            continue
                        raw_matches.append((start, end, domain, is_ambiguous, is_multiword))
                curr = self.dict_link[curr]

        if not raw_matches:
            return DomainSpans()

        accepted_spans = []
        accepted_distinctive_by_domain: dict[str, list[tuple[int, int]]] = {}
        accepted_multiword_spans = []
        ambiguous_matches = []

        for start, end, domain, is_ambiguous, is_multiword in raw_matches:
            if not is_ambiguous or is_multiword:
                accepted_spans.append((start, end))
                if not is_ambiguous:
                    accepted_distinctive_by_domain.setdefault(domain, []).append((start, end))
                if is_multiword:
                    accepted_multiword_spans.append((start, end))
            else:
                ambiguous_matches.append((start, end, domain))

        for start, end, domain in ambiguous_matches:
            # Anchor 1: Membership in a multi-word dictionary term that matches as a whole
            if any(m_start <= start and end <= m_end for m_start, m_end in accepted_multiword_spans):
                accepted_spans.append((start, end))
                continue

            # Find sentence/clause boundaries
            c_start = 0
            for i in range(start - 1, -1, -1):
                if text[i] in _CLAUSE_DELIMITERS:
                    c_start = i + 1
                    break
            c_end = len(text)
            for i in range(end, len(text)):
                if text[i] in _CLAUSE_DELIMITERS:
                    c_end = i
                    break

            # Anchor 2: Another distinctive term of the same domain in the same sentence/clause
            distinctive_in_domain = accepted_distinctive_by_domain.get(domain, [])
            if any(c_start <= d_start and d_end <= c_end for d_start, d_end in distinctive_in_domain):
                accepted_spans.append((start, end))
                continue

            # Anchor 3: Adjacent model/part-number/designation token
            anchored = False
            before_text = text[c_start:start]
            tokens_before = before_text.split()
            if tokens_before:
                prev_token = tokens_before[-1]
                if _is_alphanumeric_designator(prev_token):
                    anchored = True

            if not anchored:
                after_text = text[end:c_end]
                tokens_after = after_text.split()
                if tokens_after:
                    next_token = tokens_after[0]
                    if _is_alphanumeric_designator(next_token):
                        anchored = True

            if anchored:
                accepted_spans.append((start, end))

        output: list[tuple[int, int]] = []
        for start, end in sorted(set(accepted_spans), key=lambda item: (item[0], -item[1])):
            if not output or start >= output[-1][1]:
                output.append((start, end))
            else:
                output[-1] = (output[-1][0], max(output[-1][1], end))
        return DomainSpans(output)


def _read(path):
    """Read a domain dictionary file with bounded, symlink-safe checks.

    Args:
        path: Dictionary file path inside the trusted catalog directory.

    Returns:
        Raw file bytes. Never returns ``None``.

    Raises:
        ValueError: If ``path`` is missing, not a regular file, a symlink, or
            exceeds :data:`MAX_FILE` by stat size or actual read length.
    """
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ValueError("Missing or oversized domain dictionary")
    data = path.read_bytes()
    if len(data) > MAX_FILE:
        raise ValueError("Domain dictionary budget exceeded")
    return data


class _LazyDocuments(dict):
    def __init__(self, catalog):
        super().__init__()
        self._catalog = catalog

    def _load_full(self, domain: str) -> dict:
        if domain not in DEFAULTS:
            raise KeyError(domain)
        self._catalog._load_domain(domain)
        record = self._catalog.manifest["domains"][domain]
        data = _read(self._catalog.directory / record["file"])
        if sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Domain dictionary integrity check failed")
        value = json.loads(data)
        dict.__setitem__(self, domain, value)
        return value

    def __getitem__(self, key):
        if not dict.__contains__(self, key):
            return self._load_full(key)
        return super().__getitem__(key)

    def __contains__(self, key):
        return key in DEFAULTS or dict.__contains__(self, key)

    def get(self, key, default=None):
        if key in DEFAULTS:
            return self[key]
        return super().get(key, default)

    def items(self):
        for k in DEFAULTS:
            if not dict.__contains__(self, k):
                self._load_full(k)
        return super().items()

    def values(self):
        for k in DEFAULTS:
            if not dict.__contains__(self, k):
                self._load_full(k)
        return super().values()

    def keys(self):
        return DEFAULTS.keys()


class DomainCatalog:
    """Loaded domain dictionary manifest, documents, and match index."""

    def __init__(self, directory=None):
        t0 = time.perf_counter()
        self.directory = Path(directory) if directory else Path(__file__).parent / "data/domains"
        manifest_bytes = _read(self.directory / "manifest.json")
        manifest = json.loads(manifest_bytes)
        if manifest.get("schema_version") != 1 or set(manifest.get("domains", {})) != set(DEFAULTS):
            raise ValueError("Invalid domain manifest")
        self.version = sha256(manifest_bytes).hexdigest()
        self.manifest = manifest

        self.classified_concepts: dict[str, str] = {}
        self._term_to_concept: dict[tuple[str, str], str] = {}
        self.documents = _LazyDocuments(self)
        self._domain_terms: dict[str, list[tuple]] = {}
        self._index_cache: dict[tuple, TermIndex] = {}

        # Build initial index for default enabled domains
        for domain, is_on in DEFAULTS.items():
            if is_on:
                self._load_domain(domain)
        self.index = self._get_or_build_index(DEFAULTS)

        self.load_duration_seconds = time.perf_counter() - t0
        self.approximate_memory_bytes = self._estimate_memory()

    def _estimate_memory(self) -> int:
        mem = 0
        for idx in self._index_cache.values():
            mem += sys.getsizeof(idx.edges)
            mem += idx.failure.buffer_info()[1] * idx.failure.itemsize
            mem += idx.dict_link.buffer_info()[1] * idx.dict_link.itemsize
            mem += sys.getsizeof(idx.term_at_state)
            for e in idx.edges:
                if e is not None:
                    mem += sys.getsizeof(e)
        for terms in self._domain_terms.values():
            mem += sys.getsizeof(terms)
        return max(mem, 1024 * 1024)

    def _load_domain(self, domain: str) -> None:
        if domain in self._domain_terms:
            return
        record = self.manifest["domains"][domain]
        if record.get("file") != domain + ".json":
            raise ValueError("Invalid dictionary filename")
        data = _read(self.directory / record["file"])
        if sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Domain dictionary integrity check failed")
        value = json.loads(data)
        if value.get("id") != domain or value.get("schema_version") != 1 or len(value.get("entries", [])) > 30_000:
            raise ValueError("Invalid domain dictionary")

        entries = value["entries"]
        concept_classes = classify_domain_entries(entries)
        self.classified_concepts.update(concept_classes)

        terms = []
        for entry in entries:
            cid = entry["id"]
            cls = concept_classes.get(cid, "distinctive")
            is_concept_ambiguous = (cls == "ambiguous-common")
            if entry.get("activation_status") not in {"active-editorial-core", "active-source-label"}:
                continue
            for form in entry["forms"]:
                term = form.get("text")
                if not isinstance(term, str) or not 2 <= len(term) <= 256 or form.get("boundary") not in {"word", "hangul"}:
                    raise ValueError("Invalid domain match form")
                is_single = _is_single_word_term(term)
                is_ambig = is_concept_ambiguous and is_single
                terms.append((term, domain, form["case_sensitive"], form["boundary"], is_ambig))
                self._term_to_concept[(term, domain)] = cid
        self._domain_terms[domain] = terms
        del value
        del data

    def _get_or_build_index(self, enabled: dict[str, bool]) -> TermIndex:
        enabled_tuple = tuple(sorted((k, bool(v)) for k, v in enabled.items()))
        if enabled_tuple in self._index_cache:
            return self._index_cache[enabled_tuple]

        all_terms = []
        for domain, is_on in enabled.items():
            if is_on:
                if domain not in self._domain_terms:
                    self._load_domain(domain)
                all_terms.extend(self._domain_terms[domain])

        index = TermIndex(all_terms)
        self._index_cache[enabled_tuple] = index
        return index

    def spans(self, text, enabled, max_matches=100_000):
        """Return protected spans for ``text`` under the enabled-domain policy.

        Delegates to :meth:`TermIndex.spans`. Returns ``(start, end)`` offsets
        in the original text, or ``[]`` when nothing is protected.
        """
        if not any(enabled.values()):
            return DomainSpans()
        index = self._get_or_build_index(enabled)
        return index.spans(text, enabled, max_matches)

    def concept_for_term(self, term: str, domain: str) -> str | None:
        """Return concept ID for a given term and domain, or None."""
        if domain not in self._domain_terms:
            self._load_domain(domain)
        return self._term_to_concept.get((term, domain))

    def term_classification(self, term: str, domain: str) -> str:
        """Return classification ('distinctive' or 'ambiguous-common') for a term."""
        cid = self.concept_for_term(term, domain)
        if cid:
            return self.classified_concepts.get(cid, "distinctive")
        return "distinctive"

    def status(self, enabled):
        """Return catalog/policy status metadata for the enabled-domain map.

        Returns a JSON-serializable dict with policy/manifest versions and per-
        domain counts. Never returns ``None``.
        """
        policy_version = sha256((self.version + json.dumps(enabled, sort_keys=True)).encode()).hexdigest()
        domains_status = []
        for domain in DEFAULTS:
            rec = self.manifest["domains"][domain]
            domains_status.append({
                "id": domain,
                "version": rec["version"],
                "concept_count": rec["concept_count"],
                "active_concepts": rec["active_concepts"],
                "form_count": rec["form_count"]
            })
        enabled_terms = sum(len(self._domain_terms[d]) for d, on in enabled.items() if on and d in self._domain_terms)
        return {
            "enabled": dict(enabled),
            "policy_version": policy_version,
            "dictionary_manifest": self.version,
            "load_duration_seconds": self.load_duration_seconds,
            "enabled_term_count": enabled_terms,
            "approximate_memory_bytes": self.approximate_memory_bytes,
            "domains": domains_status
        }

    def page(self, domain, query="", limit=50, offset=0):
        """Return a bounded page of dictionary entries for a domain.

        Filters by ``query`` (casefold substring over forms) when provided.
        Returns a dict with domain, total, offset, entries slice, and version;
        never returns ``None``.

        Raises:
            ValueError: For unknown domains or out-of-range query/pagination.
        """
        if domain not in DEFAULTS or len(query) > 128 or not 1 <= limit <= 100 or not 0 <= offset <= 100_000:
            raise ValueError("Invalid dictionary page")
        if domain not in self.documents:
            self._load_domain(domain)
        entries = [entry for entry in self.documents[domain]["entries"] if not query or
                   any(query.casefold() in form["text"].casefold() for form in entry["forms"])]
        return {"domain": domain, "total": len(entries), "offset": offset,
                "entries": entries[offset:offset + limit], "version": self.documents[domain]["version"]}


@lru_cache(maxsize=1)
def catalog() -> DomainCatalog:
    """Return the process-wide cached :class:`DomainCatalog` instance.

    The catalog is loaded once per process from packaged domain data. Never
    returns ``None``.
    """
    return DomainCatalog()


def protect_chunks(text, chunks, spans):
    """Expand matches to opaque lexical spans, preserving original coordinates."""
    if not spans:
        return chunks
    opaque, offset = [], 0
    for chunk in chunks:
        end = offset + len(chunk.text)
        if chunk.kind in {"URL", "EMAIL", "CODE_BLOCK", "SECRET", "UUID", "IP", "PHONE", "ENTITY"}:
            opaque.append((offset, end))
        offset = end
    expanded: list[tuple[int, int]] = []
    index = 0
    for start, end in spans:
        while index < len(opaque) and opaque[index][1] <= start:
            index += 1
        other = index
        while other < len(opaque) and opaque[other][0] < end:
            start, end = min(start, opaque[other][0]), max(end, opaque[other][1])
            other += 1
        if expanded and start < expanded[-1][1]:
            expanded[-1] = (expanded[-1][0], max(end, expanded[-1][1]))
        else:
            expanded.append((start, end))
    output: list[TextChunk] = []
    offset, index, chunk_start = 0, 0, 0

    def advance(boundary, emit):
        nonlocal offset, index, chunk_start
        while index < len(chunks) and offset < boundary:
            chunk_end = chunk_start + len(chunks[index].text)
            end = min(boundary, chunk_end)
            if emit:
                output.append(TextChunk(text[offset:end], chunks[index].kind))
            offset = end
            if offset == chunk_end:
                chunk_start = chunk_end
                index += 1
    for start, end in expanded:
        advance(start, True)
        output.append(TextChunk(text[start:end], "ENTITY"))
        advance(end, False)
    advance(len(text), True)
    return output
