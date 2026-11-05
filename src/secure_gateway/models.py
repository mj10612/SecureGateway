"""Pydantic data models and schemas for SecureGateway."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal
from pydantic import BaseModel, Field, computed_field


class MaskMode(str, Enum):
    """Masking policy mode defining which token classes are obfuscated."""

    CONTENT_WORDS = "content_words"  # Preserves grammar & syntax; masks nouns, content terms, numbers, entities
    ENTITIES_ONLY = "entities_only"  # Masks only recognized entities (PII, names, emails, IPs, numbers)
    UNCOMMON_WORDS = "uncommon_words"  # Preserves reviewed common vocabulary; masks unknown content
    CODE_AWARE = "code_aware"  # Preserves language syntax/keywords; masks identifiers, literals, secrets
    AGGRESSIVE = (
        "aggressive"  # Obfuscates all tokens except essential structural function words
    )


class SurrogateStrategy(str, Enum):
    """Strategy for generating synthetic surrogate tokens."""

    BRACKET = "bracket"  # e.g., [ENTITY_1], [TERM_1], [NUM_1]
    UNICODE = "unicode"  # e.g., ⟦ENT_1⟧
    PSEUDOWORD = "pseudoword"  # Explicitly delimited pronounceable random words
    HASH = "hash"  # Random 96-bit nonce, independent of the original


class TokenType(str, Enum):
    """Linguistic and structural token classifications."""

    GRAMMAR = "grammar"  # Functional word, preposition, particle, syntax marker
    ENTITY = "entity"  # Named entity (Person, Org, Location, etc.)
    NOUN = "noun"  # Substantive noun / concept
    VERB = "verb"  # Content verb
    ADJECTIVE = "adjective"  # Descriptive adjective/adverb
    NUMBER = "number"  # Numeric literal / currency / measurement
    IDENTIFIER = "identifier"  # Code variable / function / class name
    LITERAL = "literal"  # String or character literal
    UNKNOWN = "unknown"  # General content token


class TokenMapping(BaseModel):
    """Bi-directional mapping between original token and synthetic surrogate."""

    # Mapping identity is immutable: stores cache its size and original/alias indexes.
    # Use a new session for different bindings instead of mutating stored identity.
    original: str = Field(frozen=True)
    surrogate: str = Field(frozen=True)
    token_type: TokenType = Field(default=TokenType.UNKNOWN, frozen=True)
    occurrence_count: int = 1
    is_capitalized: bool = Field(default=False, frozen=True)
    is_all_caps: bool = Field(default=False, frozen=True)
    context: Literal["text", "code"] = Field(default="text", frozen=True)
    format_version: int = Field(default=2, ge=1, le=2, frozen=True)
    identifier_base: str | None = Field(default=None, frozen=True)
    identifier_language: str | None = Field(default=None, frozen=True)
    identifier_key: str | None = Field(default=None, frozen=True)
    identifier_quoted: bool = Field(default=False, frozen=True)
    lookup_key: str | None = Field(default=None, frozen=True)
    code_literal: bool = Field(default=False, frozen=True)

    def _initialize_identifier(self, surrogate, base, language, key, quoted):
        """Allocator-only initialization, before the operation exposes this binding."""
        for name, value in (("surrogate", surrogate), ("identifier_base", base),
                            ("identifier_language", language), ("identifier_key", key),
                            ("identifier_quoted", quoted)):
            object.__setattr__(self, name, value)

    def _mark_code_literal(self):
        """The shared allocator may encounter an existing text alias in code."""
        object.__setattr__(self, "code_literal", True)


class MaskResult(BaseModel):
    """Result returned after masking text or code."""

    masked_text: str
    session_id: str
    total_tokens: int
    masked_tokens: int
    preserved_tokens: int
    privacy_entropy_score: float = Field(
        ...,
        description="Deprecated alias of masked_ratio; token occurrence ratio, not entropy or a security guarantee",
    )
    strategy: SurrogateStrategy
    mode: MaskMode
    detected_language: str = "en"
    code_language: str | None = None

    @computed_field
    def masked_ratio(self) -> float:
        """Masked / non-whitespace, non-punctuation token occurrences."""
        return self.privacy_entropy_score


class UnmaskResult(BaseModel):
    """Result returned after restoring original tokens from AI response."""

    unmasked_text: str
    session_id: str
    restored_tokens_count: int
    restored_unique_tokens: int = 0
    unmatched_surrogates: List[str] = Field(
        default_factory=list,
        description="Surrogate tokens found in text that had no matching session mapping",
    )

    @computed_field
    def unmasked_code(self) -> str:
        """Alias for code unmasking operations."""
        return self.unmasked_text

    @computed_field
    def restored_occurrences(self) -> int:
        return self.restored_tokens_count


class SessionStats(BaseModel):
    """Sanitized session metrics that never reveal proprietary raw tokens."""

    session_id: str
    created_at: float
    last_accessed: float
    total_unique_mappings: int
    mapping_bytes: int = 0
    max_mapping_bytes: int = 64 * 1024 * 1024
    max_snapshot_bytes: int = 128 * 1024 * 1024
    total_mask_calls: int
    total_unmask_calls: int
    mode: MaskMode
    strategy: SurrogateStrategy
    type_distribution: Dict[str, int] = Field(default_factory=dict)
