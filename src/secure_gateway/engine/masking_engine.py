"""Local masking and exact, single-pass restoration."""

from __future__ import annotations

from contextlib import nullcontext
import re

from secure_gateway.engine.code_parser import CodeParser, detect_language, literal_parts
from secure_gateway.engine.code_identifiers import ascii_lower, equivalent_alias, identifier_key
from secure_gateway.engine.grammar_en import EnglishGrammarEngine
from secure_gateway.engine.grammar_ko import (
    KOREAN_COPULA_LIST,
    KOREAN_JOSA_LIST,
    KOREAN_PLURAL,
    KoreanGrammarEngine,
    is_hangul_string,
    normalize_particle,
)
from secure_gateway.engine.strategies import StrategyGenerator, mapping_key
from secure_gateway.engine.tokenizer import MultilingualTokenizer, TextChunk
from secure_gateway.engine import natural_languages
from secure_gateway.models import (
    MaskMode,
    MaskResult,
    SurrogateStrategy,
    TokenMapping,
    TokenType,
    UnmaskResult,
)

STRUCTURAL_WORDS = {
    "a",
    "an",
    "the",
    "of",
    "in",
    "to",
    "for",
    "with",
    "on",
    "at",
    "from",
    "by",
    "and",
    "or",
    "but",
    "if",
}
STRUCTURAL_KO = {"그리고", "그러나", "및", "또는", "하지만"}
# Code number aliases are "732846" + 12 digits (see StrategyGenerator.generate).
# Legacy dotted numbers (0.5 + .1) could glue two aliases with no separator.
NUMERIC_ALIAS_LENGTH = 18
NUMERIC_ALIAS_RUN = re.compile(r"(?<![A-Za-z0-9_])(?:732846\d{12})+(?![A-Za-z0-9_])")


class NumericLiteralConflict(ValueError):
    """A preserved number would be interpreted as an existing alias."""


class MaskingEngine:
    def __init__(self, max_input_bytes: int = 16 * 1024 * 1024,
                 max_restore_input_bytes: int = 16 * 1024 * 1024,
                 max_restore_output_bytes: int = 16 * 1024 * 1024) -> None:
        if type(max_input_bytes) is not int or max_input_bytes < 1:
            raise ValueError("max_input_bytes must be a positive integer.")
        for limit in (max_restore_input_bytes, max_restore_output_bytes):
            if type(limit) is not int or limit < 1:
                raise ValueError("Restoration limits must be positive integers.")
        self.max_restore_input_bytes = max_restore_input_bytes
        self.max_restore_output_bytes = max_restore_output_bytes
        self._restore_remaining: int | None = None
        self.max_input_bytes = max_input_bytes
        self.en_grammar = EnglishGrammarEngine()
        self.ko_grammar = KoreanGrammarEngine()
        self.code_parser = CodeParser()
        self.tokenizer = MultilingualTokenizer()

    def _check_input(self, text: str) -> None:
        if not isinstance(text, str):
            raise ValueError("Input must be text.")
        if len(text.encode("utf-8")) > self.max_input_bytes:
            raise ValueError("Input size limit reached; split the input into smaller requests.")

    @staticmethod
    def _strategy(
        generator: StrategyGenerator, requested: SurrogateStrategy | None
    ) -> SurrogateStrategy:
        if requested is not None and requested != generator.strategy:
            raise ValueError("Requested strategy must match the generator's strategy.")
        return generator.strategy

    def mask_text(
        self,
        text: str,
        session_id: str,
        generator: StrategyGenerator,
        mapping_store: dict[str, TokenMapping],
        reverse_store: dict[str, TokenMapping],
        mode: MaskMode = MaskMode.CONTENT_WORDS,
        strategy: SurrogateStrategy | None = None,
        custom_preserve: set[str] | None = None,
        language: str = "auto",
        sensitive_terms: set[str] | None = None,
        code_language: str = "auto",
        mask_numbers: bool = False,
        sql_dialect: str = "sqlite",
    ) -> MaskResult:
        strategy = self._strategy(generator, strategy)
        self._check_input(text)
        language = natural_languages.canonical_language(language)
        selected_language = natural_languages.detect_natural_language(text) if language == "auto" else language
        with generator.operation():
            if mode == MaskMode.CODE_AWARE:
                return self.mask_code(
                    text,
                    session_id,
                    generator,
                    mapping_store,
                    reverse_store,
                    strategy,
                    language=code_language,
                    mask_numbers=mask_numbers,
                    sql_dialect=sql_dialect,
                )
            terms = sensitive_terms or set()
            preserve = {word.casefold() for word in (custom_preserve or set())}
            # Source text can itself contain a reserved surrogate spelling. Treat
            # it as an opaque entity so strict restoration never confuses it
            # with an earlier allocation (or rejects a literal unknown alias).
            literal_aliases = {match[0] for match in StrategyGenerator.get_pattern(strategy).finditer(text)}
            chunks = self._chunks(text, terms | literal_aliases, selected_language)
            if hasattr(mapping_store, "originals_in"):
                known = terms | mapping_store.originals_in(text)
            else:
                known = terms | {m.original for m in mapping_store.values()}
            output: list[str] = []
            total = masked = 0
            for chunk in chunks:
                word = chunk.text
                if chunk.is_whitespace or (
                    not chunk.is_word and not chunk.is_code and chunk.kind != "ENTITY"
                ):
                    output.append(word)
                    continue
                total += 1
                stem, suffix = word, ""
                force = chunk.kind in {
                    "ENTITY",
                    "EMAIL",
                    "URL",
                    "SECRET",
                    "UUID",
                    "IP",
                    "PHONE",
                    "CODE_BLOCK",
                }
                token_type = TokenType.ENTITY if force else TokenType.NOUN
                should_mask = force
                if chunk.is_number:
                    token_type, should_mask = TokenType.NUMBER, True
                elif not force and is_hangul_string(word):
                    # Mixed Korean/English input is handled per token, even with language=en.
                    stem, suffix, token_type = self.ko_grammar.decompose_token(
                        word, known
                    )
                    should_mask = token_type != TokenType.GRAMMAR
                    # Case-free scripts have no reliable proper-name cue: mask conservatively.
                    if (
                        mode == MaskMode.ENTITIES_ONLY
                        and should_mask
                        and token_type != TokenType.NUMBER
                    ):
                        token_type = TokenType.ENTITY
                    if mode == MaskMode.AGGRESSIVE and word not in STRUCTURAL_KO:
                        stem, suffix, token_type, should_mask = (
                            word,
                            "",
                            TokenType.NOUN,
                            True,
                        )
                elif not force and selected_language not in {"en", "ko"}:
                    token_type, should_mask = natural_languages.classify_token(word, selected_language)
                    if mode == MaskMode.ENTITIES_ONLY and should_mask:
                        token_type = TokenType.ENTITY
                elif not force:
                    token_type, should_mask = self.en_grammar.classify_token(word)
                    if (
                        any(ord(c) > 127 and c.isalpha() for c in word)
                        and not word.isascii()
                    ):
                        if (
                            mode == MaskMode.ENTITIES_ONLY
                            and token_type != TokenType.GRAMMAR
                        ):
                            token_type, should_mask = TokenType.ENTITY, True
                    if mode == MaskMode.ENTITIES_ONLY and token_type not in {
                        TokenType.ENTITY,
                        TokenType.NUMBER,
                    }:
                        should_mask = False
                    if (
                        mode == MaskMode.AGGRESSIVE
                        and word.casefold() not in STRUCTURAL_WORDS
                    ):
                        should_mask = True
                    if should_mask and word.endswith(("'s", "’s")):
                        stem, suffix = word[:-2], word[-2:]
                if word.casefold() in preserve and not force:
                    should_mask = False
                if should_mask:
                    output.append(
                        self._get_or_create_surrogate(
                            stem, token_type, generator, mapping_store, reverse_store
                        )
                        + suffix
                    )
                    known.add(stem)
                    masked += 1
                else:
                    output.append(word)
            return self._result(
                "".join(output),
                session_id,
                total,
                masked,
                strategy,
                mode,
                selected_language,
            )

    def _chunks(self, text: str, terms: set[str], language: str = "en") -> list[TextChunk]:
        tokenize = self.tokenizer.tokenize if language in {"en", "ko"} else lambda value: natural_languages.tokenize(value, language)
        if not terms:
            return tokenize(text)
        if "" in terms:
            raise ValueError("Sensitive terms must be nonempty.")
        suffixes = set(KOREAN_JOSA_LIST) | set(KOREAN_COPULA_LIST)
        suffixes.update(KOREAN_PLURAL + particle for particle in KOREAN_JOSA_LIST)
        # Chinese/Japanese words need not have spaces between them. Keep Latin
        # word boundaries (ABC must not match ABCdef), but permit an explicit
        # term next to Han/kana. The original spelling remains untouched.
        boundary = r"\w"
        if language in {"zh", "ja"}:
            boundary = r"[^\W\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af]"
        pattern = re.compile(
            rf"(?<!{boundary})(?P<entity>"
            + "|".join(re.escape(s) for s in sorted(terms, key=len, reverse=True))
            + r")(?P<particle>"
            + "|".join(re.escape(s) for s in sorted(suffixes, key=len, reverse=True))
            + rf")?(?!{boundary})"
        )
        output: list[TextChunk] = []
        cursor = 0
        for match in pattern.finditer(text):
            output.extend(tokenize(text[cursor : match.start()]))
            output.append(TextChunk(match["entity"], "ENTITY"))
            if match["particle"]:
                output.append(TextChunk(match["particle"], "PARTICLE"))
            cursor = match.end()
        output.extend(tokenize(text[cursor:]))
        return output

    def mask_code(
        self,
        code: str,
        session_id: str,
        generator: StrategyGenerator,
        mapping_store: dict[str, TokenMapping],
        reverse_store: dict[str, TokenMapping],
        strategy: SurrogateStrategy | None = None,
        language: str = "auto",
        mask_numbers: bool = False,
        sql_dialect: str = "sqlite",
    ) -> MaskResult:
        if type(mask_numbers) is not bool:
            raise ValueError("mask_numbers must be a boolean.")
        strategy = self._strategy(generator, strategy)
        self._check_input(code)
        language = detect_language(code, language)
        if sql_dialect not in {"standard", "postgresql", "sqlite"}:
            raise ValueError("Unsupported SQL dialect.")
        identifier_language = "sql:" + sql_dialect if language == "sql" else language
        with generator.operation():
            tokens = self.code_parser.tokenize(code, language)
            if not mask_numbers:
                for raw, token_type, _ in tokens:
                    if token_type == TokenType.NUMBER:
                        self._preserve_number(raw, generator, mapping_store, reverse_store)
            output: list[str] = []
            total = masked = 0
            for raw, token_type, subkind in tokens:
                if subkind == "whitespace":
                    output.append(raw)
                    continue
                if subkind == "syntax":
                    output.append(raw)
                    continue
                total += 1
                if token_type == TokenType.GRAMMAR or (token_type == TokenType.NUMBER and not mask_numbers):
                    output.append(raw)
                elif subkind == "quoted_identifier":
                    prefix, suffix = raw[0], raw[-1]
                    content = raw[1:-1].replace(suffix + suffix, suffix)
                    surrogate = self._code_identifier(
                        content, identifier_language, generator, mapping_store,
                        reverse_store, quoted=True,
                    )
                    output.append(prefix + surrogate + suffix)
                    masked += 1
                elif token_type == TokenType.IDENTIFIER:
                    output.append(self._code_identifier(
                        raw, "nasm:macro" if subkind == "case_insensitive_identifier" else identifier_language,
                        generator, mapping_store, reverse_store,
                    ))
                    masked += 1
                elif subkind == "character":
                    # A whole character literal is an opaque identifier expression.
                    # Multi-character aliases inside character quotes are invalid.
                    output.append(self._get_or_create_surrogate(
                        raw, token_type, generator, mapping_store, reverse_store, code=True
                    ))
                    masked += 1
                elif token_type == TokenType.LITERAL:
                    prefix, suffix = literal_parts(raw, subkind)
                    end = len(raw) - len(suffix) if suffix else len(raw)
                    content = raw[len(prefix) : end]
                    if content:
                        surrogate = self._get_or_create_surrogate(
                            content,
                            token_type,
                            generator,
                            mapping_store,
                            reverse_store,
                            code=True,
                        )
                        output.append(prefix + surrogate + suffix)
                        masked += 1
                    else:
                        output.append(raw)
                else:
                    output.append(
                        self._get_or_create_surrogate(
                            raw,
                            token_type,
                            generator,
                            mapping_store,
                            reverse_store,
                            code=True,
                        )
                    )
                    masked += 1
            result = self._result(
                "".join(output),
                session_id,
                total,
                masked,
                strategy,
                MaskMode.CODE_AWARE,
                "code",
            )
            result.code_language = language
            return result

    def _code_identifier(self, raw, language, generator, mapping_store, reverse_store, quoted=False):
        semantic = identifier_key(raw, language, quoted=quoted)
        quoted_sql = quoted and language.startswith("sql:") and language != "sql:sqlite"
        # SQL quoted names follow the selected dialect. In the standard profile,
        # a quoted lowercase spelling can refer to an unquoted folded name.
        group = (language, semantic)
        cache = getattr(generator, "_identifier_groups", None)
        if cache is None:
            cache = {}
            generator._identifier_groups = cache
        variants = cache.setdefault(group, [])
        if not variants:
            seed = mapping_store.get(mapping_key(semantic, TokenType.IDENTIFIER, code=True))
            if (seed is not None and seed.identifier_base and seed.identifier_language != language
                    and identifier_key(seed.surrogate, language, quoted=quoted)
                    == identifier_key(seed.identifier_base, language, quoted=quoted)):
                variants.append(seed)
        existing = next((mapping for mapping in variants if mapping.original == raw
                         and (not language.startswith("sql:") or mapping.identifier_quoted == quoted)), None)
        if existing is not None:
            existing.occurrence_count += 1
            return existing.surrogate
        if variants:
            base = variants[0].identifier_base
            variant = len(variants)
            candidate = ascii_lower(base) if quoted_sql else equivalent_alias(base, language, variant)
            while not quoted_sql and (candidate in generator.used_surrogates or candidate == raw
                                      or (language.startswith("sql:") and candidate == ascii_lower(base))):
                variant += 1
                candidate = equivalent_alias(base, language, variant)
        else:
            base = candidate = None
        previous = mapping_store.get(mapping_key(raw, TokenType.IDENTIFIER, code=True))
        lookup_key = None
        if language.startswith("sql:") and quoted:
            lookup_key = f"binding:{language}:quoted:{raw}"
        elif (previous is not None and previous.identifier_language
              and previous.identifier_language != language
              and identifier_key(previous.surrogate, language, quoted=quoted)
              != identifier_key(previous.identifier_base, language, quoted=quoted)):
            lookup_key = f"binding:{language}:{semantic}:{raw}"
        elif previous is not None and previous.identifier_language == language and previous.identifier_key != semantic:
            lookup_key = f"binding:{language}:{semantic}:{raw}"
        elif previous is not None and variants and identifier_key(previous.surrogate, language) != identifier_key(base, language):
            lookup_key = f"binding:{language}:{semantic}:{raw}"
        allocated = self._get_or_create_surrogate(
            raw, TokenType.IDENTIFIER, generator, mapping_store, reverse_store,
            code=True, lookup_key=lookup_key,
        )
        mapping = reverse_store[allocated]
        if not variants and language.startswith("sql:") and language != "sql:sqlite":
            base = allocated
            candidate = ascii_lower(base) if quoted_sql else allocated
            if not quoted_sql and candidate == ascii_lower(base):
                candidate = equivalent_alias(base, language, 1)
        # Ordinary languages have no alternate semantic spellings; their raw
        # allocation remains unchanged. Distinct languages share existing raw
        # aliases where the Gateway's cross-representation contract requires it.
        if mapping.identifier_language and mapping.identifier_language != language:
            if mapping not in variants:
                variants.append(mapping)
            return allocated
        if candidate is not None and allocated != candidate:
            del reverse_store[allocated]
            mapping.surrogate = candidate
            reverse_store[candidate] = mapping
            generator.used_surrogates.add(candidate)
        mapping.identifier_base = base or allocated
        mapping.identifier_language = language
        mapping.identifier_key = semantic
        mapping.identifier_quoted = quoted
        variants.append(mapping)
        return mapping.surrogate

    def _preserve_number(self, raw, generator, mapping_store, reverse_store):
        # Identity entries disambiguate literal numbers in the reserved alias range
        # and survive encrypted snapshots using the existing mapping format.
        for match in NUMERIC_ALIAS_RUN.finditer(raw):
            for offset in range(0, len(match[0]), NUMERIC_ALIAS_LENGTH):
                number = match[0][offset:offset + NUMERIC_ALIAS_LENGTH]
                key = mapping_key(number, TokenType.NUMBER, code=True)
                reverse = reverse_store.get(number)
                forward = mapping_store.get(key)
                if ((reverse is not None and reverse.original != number)
                        or (forward is not None and forward.surrogate != number)):
                    raise NumericLiteralConflict("Numeric literal conflicts with an existing alias; use a new session.")
                if reverse is None:
                    limit = min(generator.max_mappings, getattr(self, "mapping_limit", generator.max_mappings))
                    if len(mapping_store) >= limit:
                        raise ValueError("Mapping limit reached; use a new session.")
                    mapping = TokenMapping(original=number, surrogate=number,
                                           token_type=TokenType.NUMBER, context="code")
                    mapping_store[key] = mapping
                    reverse_store[number] = mapping
                generator.used_surrogates.add(number)

    @staticmethod
    def _result(
        text: str,
        sid: str,
        total: int,
        masked: int,
        strategy: SurrogateStrategy,
        mode: MaskMode,
        language: str,
    ) -> MaskResult:
        return MaskResult(
            masked_text=text,
            session_id=sid,
            total_tokens=total,
            masked_tokens=masked,
            preserved_tokens=total - masked,
            privacy_entropy_score=round(masked / max(1, total), 4),
            strategy=strategy,
            mode=mode,
            detected_language=language,
        )

    def unmask(
        self,
        masked_text: str,
        session_id: str,
        reverse_store: dict[str, TokenMapping],
        strategy: SurrogateStrategy = SurrogateStrategy.BRACKET,
        normalize_particles: bool = False,
        strict: bool = False,
    ) -> UnmaskResult:
        if not isinstance(masked_text, str):
            raise ValueError("Restoration input must be text.")
        if len(masked_text.encode("utf-8")) > self.max_restore_input_bytes:
            raise ValueError("Restoration input size limit reached.")
        generator = getattr(reverse_store, "generator", None)
        guard = generator.operation() if generator else nullcontext()
        with guard:
            # Scan surrogate syntax in the input, then perform O(1) lookups.
            # Only v1/nonstandard allocations need an inventory-based fallback.
            legacy = getattr(reverse_store, "nonstandard_surrogates", None)
            if legacy is None:
                legacy = {value for value in reverse_store
                          if not StrategyGenerator.get_pattern(strategy).fullmatch(value)}
            sorted_values = sorted(legacy, key=len, reverse=True)
            alternatives = []
            for value in sorted_values:
                escaped = re.escape(value)
                if value[0].isalnum():
                    escaped = r"(?<![A-Za-z0-9_])" + escaped + r"(?![A-Za-z0-9_])"
                alternatives.append(escaped)
            count = 0
            unique: set[str] = set()

            # Legacy masks could glue adjacent numeric aliases (0.5.1 -> two
            # aliases with no separator). Recover only runs that are exactly a
            # sequence of numeric aliases; foreign digit runs are left untouched.
            glued_unmatched: list[str] = []

            def restore(match: re.Match[str]) -> str:
                nonlocal count
                run = match["numeric"]
                if run is None:
                    key = match["alias"]
                    mapping = reverse_store.get(key)
                    if mapping is None:
                        return match[0]
                    count += 1
                    unique.add(key)
                    suffix = match.groupdict().get("particle") or ""
                    original = mapping.original
                    if (mapping.context == "code" and mapping.token_type == TokenType.IDENTIFIER
                        and (mapping.identifier_quoted or (not mapping.identifier_base and not mapping.code_literal))):
                        before = masked_text[match.start() - 1:match.start()] if match.start() else ""
                        after = masked_text[match.end():match.end() + 1]
                        if (before, after) in {('"', '"'), ("`", "`"), ("[", "]")}:
                            original = original.replace(after, after + after)
                    return original + (
                        normalize_particle(mapping.original, suffix) if suffix else ""
                    )
                pieces = []
                piece_bytes = 0
                for offset in range(0, len(run), NUMERIC_ALIAS_LENGTH):
                    chunk = run[offset : offset + NUMERIC_ALIAS_LENGTH]
                    numeric_mapping = reverse_store.get(chunk)
                    if numeric_mapping is None:
                        glued_unmatched.append(chunk)
                        pieces.append(chunk)
                    else:
                        count += 1
                        unique.add(chunk)
                        pieces.append(numeric_mapping.original)
                    piece_bytes += len(pieces[-1].encode("utf-8"))
                    if piece_bytes > self.max_restore_output_bytes:
                        raise ValueError("Restoration output size limit reached.")
                return "".join(pieces)

            # Both forms are substituted from the original input in one pass:
            # restored originals may themselves contain allocated aliases.
            pattern = "(?P<numeric>" + NUMERIC_ALIAS_RUN.pattern + ")"
            syntax = StrategyGenerator.get_pattern(strategy).pattern.split(r"|\b", 1)[0]
            aliases = [syntax, r"(?<![A-Za-z0-9_])(?:smcp_(?:ID|NUM|LIT)|private_symbol)_\d+(?![A-Za-z0-9_])"]
            pattern += "|(?P<alias>" + "|".join(alternatives + aliases) + ")"
            if normalize_particles:
                pattern += r"(?P<particle>(?:으로|이랑|이나|은|는|을|를|과|와|이|가|로|랑|나)(?:부터|도|만|는|의)?(?=\s|[.,!?]|$))?"
            output_limit = self.max_restore_output_bytes if self._restore_remaining is None else self._restore_remaining
            parts, cursor, output_bytes = [], 0, 0
            for match in re.finditer(pattern, masked_text, re.IGNORECASE):
                for part in (masked_text[cursor:match.start()], restore(match)):
                    output_bytes += len(part.encode("utf-8"))
                    if output_bytes > output_limit:
                        raise ValueError("Restoration output size limit reached.")
                    parts.append(part)
                cursor = match.end()
            tail = masked_text[cursor:]
            if output_bytes + len(tail.encode("utf-8")) > output_limit:
                raise ValueError("Restoration output size limit reached.")
            parts.append(tail)
            output = "".join(parts)
            if self._restore_remaining is not None:
                self._restore_remaining -= output_bytes + len(tail.encode("utf-8"))
            candidates = StrategyGenerator.get_pattern(strategy).findall(masked_text)
            unmatched = sorted(
                {c for c in candidates if c not in reverse_store} | set(glued_unmatched)
            )
            if strict and unmatched:
                raise ValueError(
                    "Unrecognized or altered surrogate tokens: " + ", ".join(unmatched)
                )
            return UnmaskResult(
                unmasked_text=output,
                session_id=session_id,
                restored_tokens_count=count,
                restored_unique_tokens=len(unique),
                unmatched_surrogates=unmatched,
            )

    def _get_or_create_surrogate(
        self,
        original_token: str,
        token_type: TokenType,
        generator: StrategyGenerator,
        mapping_store: dict[str, TokenMapping],
        reverse_store: dict[str, TokenMapping],
        code: bool = False,
        lookup_key: str | None = None,
    ) -> str:
        with generator.operation():
            key = lookup_key or mapping_key(original_token, token_type, code)
            if key in mapping_store:
                if code and token_type == TokenType.NUMBER and mapping_store[key].surrogate == original_token:
                    raise NumericLiteralConflict("Numeric literal conflicts with a preserved number; use a new session.")
                mapping_store[key].occurrence_count += 1
                return mapping_store[key].surrogate
            if len(mapping_store) >= generator.max_mappings:
                raise ValueError("Mapping limit reached; clear the session or use a new one.")
            surrogate = generator.generate(token_type, original_token, code=code)
            mapping = TokenMapping(
                original=original_token,
                surrogate=surrogate,
                token_type=token_type,
                context="code" if code else "text",
                lookup_key=lookup_key,
                code_literal=code and token_type == TokenType.LITERAL,
                is_capitalized=original_token.istitle(),
                is_all_caps=original_token.isupper() and len(original_token) > 1,
            )
            mapping_store[key] = mapping
            reverse_store[surrogate] = mapping
            return surrogate
