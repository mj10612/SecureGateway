"""Versioned local protection terms with one shared, bounded Aho–Corasick index."""

from __future__ import annotations

from collections import deque
from array import array
from functools import lru_cache
from hashlib import sha256
import json
from io import StringIO
from pathlib import Path
import unicodedata

from secure_gateway.engine.tokenizer import TextChunk

DEFAULTS = {"defense": True, "automotive": False, "semiconductor": False}
MAX_FILE = 32 * 1024 * 1024


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
        self.edges: list[dict[str, int]] = [{}]
        self.failure = [0]
        self.outputs: list[list[tuple]] = [[]]
        self.build_count = 1
        for term, domain, case_sensitive, boundary in terms:
            key, _ = normalize(term)
            state = 0
            for char in key:
                if char not in self.edges[state]:
                    self.edges[state][char] = len(self.edges)
                    self.edges.append({})
                    self.failure.append(0)
                    self.outputs.append([])
                state = self.edges[state][char]
            self.outputs[state].append((len(key), domain, _case_form(term) if case_sensitive else term, case_sensitive, boundary))
        # Aho–Corasick failure links: on mismatch, fall back to the longest proper
        # suffix that is also a pattern prefix; propagate outputs along failures.
        queue = deque(self.edges[0].values())
        while queue:
            state = queue.popleft()
            for char, child in self.edges[state].items():
                queue.append(child)
                fallback = self.failure[state]
                while fallback and char not in self.edges[fallback]:
                    fallback = self.failure[fallback]
                self.failure[child] = self.edges[fallback].get(char, 0)
                self.outputs[child].extend(self.outputs[self.failure[child]])

    def spans(self, text, enabled, max_matches=100_000):
        """Find protected original-text spans for enabled domains.

        Normalizes ``text`` once, walks the automaton, maps normalized positions
        back to original offsets, applies boundary/case checks, and merges to
        leftmost-longest / union for overlaps. Returns a list of ``(start, end)``
        character offsets in the original text, or ``[]`` when no domains are
        enabled or no matches survive.
        """
        if not any(enabled.values()):
            return []
        if len(text.encode()) > 16 * 1024 * 1024:
            raise ValueError("Dictionary input budget exceeded")
        normalized, offsets = normalize(text)
        matches = []
        state = count = 0
        for pos, char in enumerate(normalized):
            # Automaton walk: follow failure links until a transition matches.
            while state and char not in self.edges[state]:
                state = self.failure[state]
            state = self.edges[state].get(char, 0)
            for length, domain, term, sensitive_case, boundary in self.outputs[state]:
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
                matches.append((start, end))
        # Leftmost-longest for coincident starts; crossing private spans form
        # their union so an overlapping term never leaks a surviving tail.
        output: list[tuple[int, int]] = []
        for start, end in sorted(set(matches), key=lambda item: (item[0], -item[1])):
            if not output or start >= output[-1][1]:
                output.append((start, end))
            else:
                output[-1] = (output[-1][0], max(output[-1][1], end))
        return output


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


class DomainCatalog:
    """Loaded domain dictionary manifest, documents, and match index."""

    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else Path(__file__).parent / "data/domains"
        manifest_bytes = _read(self.directory / "manifest.json")
        manifest = json.loads(manifest_bytes)
        if manifest.get("schema_version") != 1 or set(manifest.get("domains", {})) != set(DEFAULTS):
            raise ValueError("Invalid domain manifest")
        self.version = sha256(manifest_bytes).hexdigest()
        self.documents = {}
        terms = []
        for domain in DEFAULTS:
            record = manifest["domains"][domain]
            if record.get("file") != domain + ".json":
                raise ValueError("Invalid dictionary filename")
            data = _read(self.directory / record["file"])
            if sha256(data).hexdigest() != record["sha256"]:
                raise ValueError("Domain dictionary integrity check failed")
            value = json.loads(data)
            if value.get("id") != domain or value.get("schema_version") != 1 or len(value.get("entries", [])) > 30_000:
                raise ValueError("Invalid domain dictionary")
            self.documents[domain] = value
            for entry in value["entries"]:
                # Source-category labels include named equipment/projects as
                # explicitly requested; incomplete classification expressions
                # remain browse-only until lexical review is sufficient.
                if entry.get("activation_status") not in {"active-editorial-core", "active-source-label"}:
                    continue
                for form in entry["forms"]:
                    term = form.get("text")
                    if not isinstance(term, str) or not 2 <= len(term) <= 256 or form.get("boundary") not in {"word", "hangul"}:
                        raise ValueError("Invalid domain match form")
                    terms.append((term, domain, form["case_sensitive"], form["boundary"]))
        self.index = TermIndex(terms)

    def spans(self, text, enabled, max_matches=100_000):
        """Return protected spans for ``text`` under the enabled-domain policy.

        Delegates to :meth:`TermIndex.spans`. Returns ``(start, end)`` offsets
        in the original text, or ``[]`` when nothing is protected.
        """
        return self.index.spans(text, enabled, max_matches)

    def status(self, enabled):
        """Return catalog/policy status metadata for the enabled-domain map.

        Returns a JSON-serializable dict with policy/manifest versions and per-
        domain counts. Never returns ``None``.
        """
        policy_version = sha256((self.version + json.dumps(enabled, sort_keys=True)).encode()).hexdigest()
        return {"enabled": dict(enabled), "policy_version": policy_version, "dictionary_manifest": self.version,
                "domains": [{"id": domain, "version": doc["version"],
                             "concept_count": len(doc["entries"]),
                             "active_concepts": sum(e.get("activation_status") in {"active-editorial-core", "active-source-label"} for e in doc["entries"]),
                             "form_count": sum(len(e["forms"]) for e in doc["entries"])}
                            for domain, doc in self.documents.items()]}

    def page(self, domain, query="", limit=50, offset=0):
        """Return a bounded page of dictionary entries for a domain.

        Filters by ``query`` (casefold substring over forms) when provided.
        Returns a dict with domain, total, offset, entries slice, and version;
        never returns ``None``.

        Raises:
            ValueError: For unknown domains or out-of-range query/pagination.
        """
        if domain not in self.documents or len(query) > 128 or not 1 <= limit <= 100 or not 0 <= offset <= 100_000:
            raise ValueError("Invalid dictionary page")
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
