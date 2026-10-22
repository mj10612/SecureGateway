"""Offline, conservative natural-language adapters.

These are lexical adapters, not named-entity recognizers or morphological
analyzers. Unknown words remain content; only reviewed closed-class words are
preserved. Chinese uses jieba's bundled local dictionary; Japanese uses TinySegmenter's
local statistical model. Neither downloads resources or sends input away. Original spelling is never
normalized: normalization is used only for grammar lookup.
"""
from __future__ import annotations

import unicodedata
import warnings
from functools import lru_cache

from secure_gateway.engine.tokenizer import TOKEN_SPLIT_REGEX, TextChunk
from secure_gateway.models import TokenType

# Reviewable starter vocabularies, deliberately excluding personal pronouns
# whose capitalization or use as names would otherwise leak a content token.
_CLOSED = {
    "es": "el la los las un una unos unas de del al a en por para con sin sobre entre y o pero que si como",
    "fr": "le la les un une des du de au aux à en par pour avec sans sur sous et ou mais que si dans l' d' qu' n' s' c' j'",
    "pt": "o a os as um uma uns umas de do da dos das em no na nos nas ao aos por para com sem sobre entre e ou mas que se",
    "de": "der die das den dem des ein eine einer eines einem einen und oder aber wenn weil dass zu zum zur in im am an auf für mit von vom bei ohne über unter",
    "id": "dan atau tetapi jika karena yang di ke dari pada untuk dengan tanpa dalam antara sebagai adalah",
    "tr": "ve veya ama fakat ile için gibi kadar göre bir bu şu o da de ki mi mı mu mü",
    "ru": "и или но а если что как в во на к ко с со из от до для по без под над при между о об у",
    "hi": "और या लेकिन यदि तो कि का की के को से में पर तक लिए साथ बिना एक है हैं था थी थे",
    "mr": "आणि किंवा पण जर तर की चा ची चे ला ने मध्ये वर पासून साठी सह एक आहे आहेत होता होती होते",
    "bn": "এবং বা কিন্তু যদি তবে যে এর এ কে থেকে জন্য সঙ্গে মধ্যে উপর একটি হয় আছে ছিল",
    "ur": "اور یا لیکن اگر تو کہ کا کی کے کو سے میں پر تک لیے ساتھ بغیر ایک ہے ہیں تھا تھی تھے",
    "te": "మరియు లేదా కానీ అయితే అని యొక్క కు లో పై నుండి కోసం తో లేక ఒక ఉంది ఉన్నాయి",
    "ar": "و أو لكن إذا أن إن في من إلى عن على مع بين دون هذا هذه ذلك التي الذي ال",
    "zh": "的 了 和 与 與 或 但 在 从 從 到 对 對 为 為 以 把 被 是 有 一个 一個 这 這 那 及 并 並",
    "ja": "は が を に で と の へ や も から まで より ので そして しかし また です ます した する ある いる",
}
SUPPORTED_LANGUAGES = frozenset({"auto", "en", "ko", *_CLOSED})
CLOSED_CLASS_WORDS = {
    language: frozenset(unicodedata.normalize("NFC", word).casefold() for word in words.split())
    for language, words in _CLOSED.items()
}
@lru_cache(maxsize=2)
def _segmenter(language: str):
    # Lazy imports keep English/Korean startup independent of model loading.
    if language == "zh":
        # jieba 0.42.1 uses legacy escaped regex literals. Keep strict warning
        # runs usable on a cold bytecode cache without hiding other warnings.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*invalid escape sequence.*",
                                    category=DeprecationWarning)
            warnings.filterwarnings("ignore", message=".*invalid escape sequence.*",
                                    category=SyntaxWarning)
            warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API.*",
                                    category=Warning)
            warnings.filterwarnings("ignore", message="Deprecated call to .*pkg_resources.declare_namespace.*",
                                    category=DeprecationWarning)
            import jieba
        return jieba.Tokenizer()
    from tinysegmenter import TinySegmenter
    return TinySegmenter()


def _cjk_chunks(text: str, language: str) -> list[TextChunk]:
    segmenter = _segmenter(language)
    words = (list(segmenter.cut(text, HMM=False)) if language == "zh"
             else segmenter.tokenize(text))
    # Enforce exact input spans even if a future model changes behavior. Never
    # allow a model-generated normalization to enter the restoration mapping.
    if not words or "".join(words) != text:
        return [TextChunk(text, "WORD")]
    chunks: list[TextChunk] = []
    for word in words:
        if chunks and (unicodedata.category(word[0])[0] == "M"
                       or word[0] in "\u200c\u200d"
                       or chunks[-1].text[-1] in "\u200c\u200d"):
            chunks[-1].text += word
        else:
            chunks.append(TextChunk(word, "WORD"))
    return chunks


def canonical_language(language: str) -> str:
    """Validate a language tag and resolve supported regional/script variants.

    Variants select the same conservative adapter and never convert spelling.
    Unsupported base languages raise instead of silently using English.
    """
    if not isinstance(language, str):
        raise ValueError("language must be a supported language tag")
    tag = language.strip().replace("_", "-").lower()
    parts = tag.split("-")
    if not tag or any(not part.isascii() or not part.isalnum() for part in parts):
        raise ValueError("language must be a supported language tag")
    base = parts[0]
    if base not in SUPPORTED_LANGUAGES or (base == "auto" and len(parts) > 1):
        raise ValueError("Unsupported natural language: " + language)
    return base


def structural_words(language: str) -> frozenset[str]:
    return CLOSED_CLASS_WORDS.get(canonical_language(language), frozenset())


def grammar_key(word: str, language: str) -> str:
    """Comparison key only; never use this spelling in restoration mappings."""
    key = unicodedata.normalize("NFC", word)
    if canonical_language(language) == "tr":
        key = key.translate(str.maketrans("Iİ", "ıi"))
    return key.casefold().replace("’", "'")


def classify_token(word: str, language: str) -> tuple[TokenType, bool]:
    """Preserve known grammar, conservatively classify other words as content."""
    key = grammar_key(word, language)
    if key in structural_words(language):
        return TokenType.GRAMMAR, False
    return TokenType.NOUN, True


def detect_natural_language(text: str) -> str:
    """Infer only unambiguous scripts; shared scripts use conservative fallback.

    Hindi/Marathi, Arabic/Urdu, Chinese/Japanese Han-only text cannot be
    distinguished reliably from script alone. Explicit language wins; auto
    selects Hindi/Arabic/Chinese lexical defaults, not a confidence claim.
    Latin and Cyrillic inference never guesses from a few content words.
    """
    for char in text:
        cp = ord(char)
        if 0x3040 <= cp <= 0x30FF:
            return "ja"
    for char in text:
        cp = ord(char)
        if 0xAC00 <= cp <= 0xD7A3:
            return "ko"
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            return "zh"
        if 0x0900 <= cp <= 0x097F:
            return "hi"
        if 0x0980 <= cp <= 0x09FF:
            return "bn"
        if 0x0C00 <= cp <= 0x0C7F:
            return "te"
        if 0x0600 <= cp <= 0x06FF:
            return "ar"
        if 0x0400 <= cp <= 0x052F:
            return "ru"
    return "en"


def _is_word(char: str) -> bool:
    return unicodedata.category(char)[0] in "LMN" or char == "_" or char in "\u200c\u200d"


def _is_cjk(char: str) -> bool:
    cp = ord(char)
    return (0x3400 <= cp <= 0x9FFF or 0x3040 <= cp <= 0x30FF
            or 0x20000 <= cp <= 0x323AF)


def _cluster_end(text: str, start: int) -> int:
    # Never detach a combining sign, variation selector or joiner sequence.
    end = start + 1
    while end < len(text):
        char = text[end]
        if unicodedata.category(char)[0] == "M" or char in "\u200c\u200d":
            end += 1
        elif text[end - 1] in "\u200c\u200d":
            end += 1
        else:
            break
    return end


def tokenize(text: str, language: str) -> list[TextChunk]:
    """Lossless chunks, compatible with the engine's existing TextChunk API.

    Sensitive spans/code blocks use the existing tokenizer's precedence. Word
    scanning includes Unicode marks and joining controls, including Hindi,
    Marathi, Bengali, Telugu, Arabic and Urdu orthographic clusters.
    """
    lang = canonical_language(language)
    if lang == "auto":
        lang = detect_natural_language(text)
    chunks: list[TextChunk] = []
    position = 0
    protected = {"WHITESPACE", "CODE_BLOCK", "URL", "EMAIL", "SECRET", "UUID", "IP", "PHONE", "NUMBER"}
    while position < len(text):
        match = TOKEN_SPLIT_REGEX.match(text, position)
        if match is not None and match.lastgroup in protected:
            # A number followed by a combining sign belongs to the same word.
            if not (match.lastgroup == "NUMBER" and match.end() < len(text)
                    and unicodedata.category(text[match.end()])[0] == "M"):
                chunks.append(TextChunk(match[0], match.lastgroup or "OTHER"))
                position = match.end()
                continue
        if _is_cjk(text[position]) and lang in {"zh", "ja"}:
            end = _cluster_end(text, position)
            while end < len(text) and _is_cjk(text[end]):
                end = _cluster_end(text, end)
            chunks.extend(_cjk_chunks(text[position:end], lang))
        elif _is_word(text[position]):
            end = _cluster_end(text, position)
            while end < len(text):
                char = text[end]
                if _is_cjk(char) and lang in {"zh", "ja"}:
                    break
                if _is_word(char):
                    end = _cluster_end(text, end)
                elif char in "'’" and end + 1 < len(text) and _is_word(text[end + 1]):
                    end += 1
                    if lang == "fr" and unicodedata.normalize("NFC", text[position:end]).casefold().replace("’", "'") in CLOSED_CLASS_WORDS["fr"]:
                        break
                else:
                    break
            chunks.append(TextChunk(text[position:end], "WORD"))
        else:
            end = _cluster_end(text, position)
            chunks.append(TextChunk(text[position:end], "OTHER"))
        position = end
    return chunks
