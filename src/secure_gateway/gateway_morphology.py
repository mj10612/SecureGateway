"""Bounded prose morphology for proposing complete public tokens.

``is_ordinary_form`` answers one narrow question: is this whole prose token an
exact public form, or a standard inflection/derivation whose every lexical root
the caller explicitly knows to be public?  Vocabulary is never stored here; the
caller supplies it through two callbacks that receive NFC + casefolded strings.
The grammar below is independently authored (regular endings, particles,
clitics and linking elements), not a lexicon.

Safety rules: a private full token, or any private candidate root, rejects the
token; unknown roots stay private; code-shaped tokens are rejected; token length,
candidate count, derivation depth and German segmentation lookups are bounded.
Gateway private/code protections run before this helper.
"""

from __future__ import annotations

from typing import Callable
import unicodedata

MAX_TOKEN_LENGTH = 80
MAX_CANDIDATES = 48
MAX_KO_DEPTH = 3
MAX_DE_PARTS = 4
MIN_DE_PART = 3
MAX_DE_LOOKUPS = 160

RootPredicate = Callable[[str], bool]


class _Rejected(Exception):
    """A private candidate root or an exhausted work budget."""


class _Lookup:
    def __init__(self, public: RootPredicate, private: RootPredicate):
        self._public, self._private = public, private
        self._seen: dict[str, bool] = {}

    def check_private(self, root: str) -> None:
        if self._private(root):
            raise _Rejected(root)

    def public(self, root: str, budget: int | None = None) -> bool:
        if root not in self._seen:
            if budget is not None and len(self._seen) >= budget:
                raise _Rejected("lookup budget")
            self.check_private(root)
            self._seen[root] = bool(self._public(root))
        return self._seen[root]


def _code_shaped(word: str) -> bool:
    """Digits, _, -, URLs, emails and other symbols are not letters or marks."""
    for char in word:
        if char in "‌‍":  # ZWNJ/ZWJ occur inside Indic prose words
            continue
        if unicodedata.category(char)[0] not in "LM":
            return True
    cased = [char for char in word if char.isupper() or char.islower()]
    if len(cased) >= 2 and all(char.isupper() for char in cased):
        return True  # all-cap acronym
    return any(char.isupper() for char in word[1:])  # inner CamelCase


# --- Korean: Hangul syllable/coda arithmetic --------------------------------
_HANGUL_FIRST, _HANGUL_LAST = 0xAC00, 0xD7A3
_CODA = {"ㄴ": 4, "ㄹ": 8, "ㅁ": 16, "ㅂ": 17, "ㅆ": 20}
_IEUNG, _A, _AE, _EO, _YEO, _O, _WA, _WAE, _OE, _U, _WEO, _EU, _I = 11, 0, 1, 4, 6, 8, 9, 10, 11, 13, 14, 18, 20


def _syllable(char: str) -> tuple[int, int, int] | None:
    code = ord(char) - _HANGUL_FIRST
    if not 0 <= code <= _HANGUL_LAST - _HANGUL_FIRST:
        return None
    return code // 588, code % 588 // 28, code % 28


def _join(lead: int, vowel: int, coda: int = 0) -> str:
    return chr(_HANGUL_FIRST + (lead * 21 + vowel) * 28 + coda)


def _ending(text: str) -> tuple[int, str]:
    return (_CODA[text[0]], text[1:]) if text[0] in _CODA else (0, text)


# Endings attached directly to any stem; True marks ㄹ-stem ㄹ deletion (사는/살다).
_KO_DIRECT = tuple((_ending(text), drop) for text, drop in (
    ("다", False), ("고", False), ("지", False), ("지만", False), ("게", False), ("기", False),
    ("는", True), ("는데", True), ("는지", True), ("도록", False), ("자", False), ("네", True),
    ("네요", True), ("지요", False), ("죠", False), ("거나", False), ("다가", False), ("겠", False),
    ("던", False), ("고요", False), ("기로", False), ("기에", False), ("군요", False), ("는군요", True)))
# 으-alternating endings: (after vowel/ㄹ stem, after consonant stem, ㄹ deletion).
_KO_ALTERNATING = tuple((_ending(vowel), _ending(consonant), drop) for vowel, consonant, drop in (
    ("ㄴ", "은", True), ("ㄹ", "을", True), ("ㅁ", "음", False), ("ㅂ니다", "습니다", True),
    ("ㅂ니까", "습니까", True), ("ㅂ시다", "읍시다", True), ("ㄴ다", "는다", True), ("ㄴ데", "은데", True),
    ("ㄴ지", "은지", True), ("ㄹ까", "을까", True), ("ㄹ까요", "을까요", True), ("ㄹ게요", "을게요", True),
    ("ㄹ래요", "을래요", True), ("면", "으면", False), ("면서", "으면서", False), ("니까", "으니까", True),
    ("며", "으며", False), ("려고", "으려고", False), ("러", "으러", False), ("세요", "으세요", True),
    ("십시오", "으십시오", True), ("시", "으시", True)))
_KO_AFTER_A = ("요", "서", "도", "야", "")  # 아/어-form + ending (먹어요, 가서, 해도)
# Noun particles/copula: (after consonant noun, after vowel noun); "" = n/a.
_KO_PARTICLES = (("은", "는"), ("이", "가"), ("을", "를"), ("과", "와"), ("으로", "로"), ("이나", "나"),
                 ("이랑", "랑"), ("이라도", "라도"), ("이에요", "예요"), ("이었다", "였다"))
_KO_ANY_PARTICLES = ("에", "에서", "에게", "께", "께서", "도", "만", "의", "부터", "까지", "보다", "처럼",
                     "마다", "한테", "하고", "에는", "에서는", "에도", "에게는", "까지는", "만큼", "밖에",
                     "조차", "입니다", "이다", "이고", "인데", "이지만")
_KO_AUX_AFTER_A = ("주", "드리", "보", "버리", "놓", "두")
_KO_AUX_AFTER_GO = ("있", "싶", "계시")


def _coda(text: str) -> int:
    parts = _syllable(text[-1])
    return -1 if parts is None else parts[2]


def _strip(form: str, ending: tuple[int, str]) -> str | None:
    coda, rest = ending
    if len(form) <= len(rest) or not form.endswith(rest):
        return None
    stem = form[:len(form) - len(rest)]
    if coda:
        parts = _syllable(stem[-1])
        if parts is None or parts[2] != coda:
            return None
        stem = stem[:-1] + _join(parts[0], parts[1])
    return stem


def _with_rieul(stem: str) -> str:
    lead, vowel, _ = _syllable(stem[-1]) or (0, 0, 0)
    return stem[:-1] + _join(lead, vowel, _CODA["ㄹ"])


def _a_stems(form: str) -> set[str]:
    """Undo the 아/어 linking vowel, including regular vowel contractions."""
    if not form or (last := _syllable(form[-1])) is None or last[2]:
        return set()
    lead, vowel, _ = last
    head, stems = form[:-1], set()
    prev = _syllable(head[-1]) if head else None
    if lead == _IEUNG and vowel in (_A, _EO) and prev and prev[2]:
        if (vowel == _A) == (prev[1] in (_A, _O, 2)):  # vowel harmony: 잡아, 먹어
            stems.add(head)
    if form[-1] == "여" and head.endswith("하"):
        stems.add(head)
    if vowel in (_A, _EO, _AE, 5, _YEO):
        stems.add(form)  # 가, 서, 보내, 세, 켜
    if vowel in (_A, _EO) and lead != _IEUNG:
        stems.add(head + _join(lead, _EU))  # 으 deletion: 써/쓰
    if form[-1] == "해":
        stems.add(head + "하")
    for surface, base in ((_YEO, _I), (_WA, _O), (_WEO, _U), (_WAE, _OE)):
        if vowel == surface:
            stems.add(head + _join(lead, base))  # 마셔/마시, 봐/보, 줘/주, 돼/되
    if form[-1] in "와워" and prev and not prev[2]:
        stems.add(head[:-1] + _join(prev[0], prev[1], _CODA["ㅂ"]))  # ㅂ irregular: 더워/덥
    return {stem for stem in stems if stem}


def _ko_step(form: str) -> set[str]:
    stems: set[str] = set()
    for ending, drop in _KO_DIRECT:
        if (stem := _strip(form, ending)) is not None:
            stems.add(stem)
            if drop and _coda(stem) == 0:
                stems.add(_with_rieul(stem))
    for vowel_ending, consonant_ending, drop in _KO_ALTERNATING:
        if (stem := _strip(form, vowel_ending)) is not None and _coda(stem) in (0, _CODA["ㄹ"]):
            stems.add(stem)
            if drop and _coda(stem) == 0:
                stems.add(_with_rieul(stem))
        if (stem := _strip(form, consonant_ending)) is not None and _coda(stem) > 0:
            stems.add(stem)
    for suffix in _KO_AFTER_A:
        if form.endswith(suffix) and len(form) > len(suffix):
            stems |= _a_stems(form[:len(form) - len(suffix)])
    if _coda(form) == _CODA["ㅆ"]:  # past 았/었/였 (and 셨 = 시 + 었)
        stems |= _a_stems(form[:-1] + _join(*(_syllable(form[-1]) or (0, 0, 0))[:2]))
    return {stem for stem in stems if all(_syllable(char) for char in stem)}


def _ko_stems(form: str) -> set[str]:
    found: set[str] = set()
    frontier = {form}
    for _ in range(MAX_KO_DEPTH):
        frontier = {stem for item in frontier for stem in _ko_step(item)} - found
        found |= frontier
        if len(found) > MAX_CANDIDATES:
            raise _Rejected("candidate budget")
    return found


def _ko_candidates(word: str) -> list[tuple[str, ...]]:
    candidates: list[tuple[str, ...]] = []
    for stem in _ko_stems(word):
        candidates.append((stem + "다",))
        for light in ("하", "되"):  # compound 공부하다 only with a known noun
            if len(stem) > 1 and stem.endswith(light):
                candidates.append((stem[:-1],))
        for aux in _KO_AUX_AFTER_A + _KO_AUX_AFTER_GO + ("않",):
            prefix = stem[:-len(aux)] if stem.endswith(aux) and len(stem) > len(aux) else ""
            if aux in _KO_AUX_AFTER_A:
                lexical = _a_stems(prefix)
            else:
                linker = "지" if aux == "않" else "고"
                lexical = {prefix[:-1]} if len(prefix) > 1 and prefix.endswith(linker) else set()
            candidates.extend((item + "다",) for item in lexical if item)
    for consonant, vowel in _KO_PARTICLES:
        for particle, wants_coda in ((consonant, True), (vowel, False)):
            noun = _strip(word, (0, particle))
            if noun and (_coda(noun) > 0) == wants_coda:
                candidates.append((noun,))
    for particle in _KO_ANY_PARTICLES:
        if noun := _strip(word, (0, particle)):
            candidates.append((noun,))
            if len(noun) > 1 and noun.endswith("들"):
                candidates.append((noun[:-1],))
    return candidates


# --- Arabic proclitics and Marathi/Telugu reviewed case/plural suffixes -----
_AR_PROCLITICS = ("وال", "بال", "لل", "ال", "و", "ف", "ب", "ل", "ك")
_INDIC_SUFFIXES = {
    "mr": ("ांमध्ये", "ांवर", "ांच्या", "ांची", "ांचा", "ांचे", "ामध्ये", "ावर", "ाच्या", "ाची", "ाचा",
           "ाचे", "मध्ये", "वर", "च्या", "ची", "चा", "चे", "ावी", "ावा", "ावे"),
    "te": ("లలో", "లను", "లతో", "లకి", "లకు", "లోని", "లో", "లు", "తో", "ను", "ని", "కు", "కి", "గా"),
}

# --- German compounds --------------------------------------------------------
_DE_LINKS = ("", "s", "es", "n", "en")
_DE_INFLECTIONS = ("e", "en", "n", "s", "es", "er", "ern", "em")


def _de_head(rest: str, lookup: _Lookup) -> bool:
    if lookup.public(rest, MAX_DE_LOOKUPS):
        return True
    return any(lookup.public(rest[:-len(end)], MAX_DE_LOOKUPS) for end in _DE_INFLECTIONS
               if rest.endswith(end) and len(rest) - len(end) >= MIN_DE_PART)


def _de_compound(word: str, lookup: _Lookup) -> bool:
    failed: set[tuple[int, int]] = set()

    def segment(start: int, parts_left: int) -> bool:
        if (start, parts_left) in failed:
            return False
        if parts_left < MAX_DE_PARTS and _de_head(word[start:], lookup):
            return True
        if parts_left > 1:
            for end in range(start + MIN_DE_PART, len(word) - MIN_DE_PART + 1):
                if not lookup.public(word[start:end], MAX_DE_LOOKUPS):
                    continue
                for link in _DE_LINKS:
                    nxt = end + len(link)
                    if word.startswith(link, end) and nxt <= len(word) - MIN_DE_PART and segment(nxt, parts_left - 1):
                        return True
        failed.add((start, parts_left))
        return False

    return segment(0, MAX_DE_PARTS)


def _candidates(word: str, language: str) -> list[tuple[str, ...]]:
    if language == "ko":
        return _ko_candidates(word)
    if language == "ar":
        return [(word[len(p):],) for p in _AR_PROCLITICS if word.startswith(p) and len(word) - len(p) >= 2]
    if language in _INDIC_SUFFIXES:
        return [(word[:-len(s)],) for s in _INDIC_SUFFIXES[language]
                if word.endswith(s) and len(word) - len(s) >= 2]
    if language == "de":
        return [(word[:-len(end)],) for end in _DE_INFLECTIONS
                if word.endswith(end) and len(word) - len(end) >= MIN_DE_PART]
    return []


def is_ordinary_form(word: str, language: str, is_public_root: RootPredicate,
                     is_private_root: RootPredicate) -> bool:
    """Return True only for a complete public prose token; never rewrites text."""
    if not isinstance(word, str) or not word or len(word) > MAX_TOKEN_LENGTH:
        return False
    surface = unicodedata.normalize("NFC", word)
    if len(surface) > MAX_TOKEN_LENGTH or _code_shaped(surface):
        return False
    key = surface.casefold()
    lang = language.split("-")[0].split("_")[0].casefold()
    lookup = _Lookup(is_public_root, is_private_root)
    try:
        lookup.check_private(key)
        if lookup.public(key):
            return True
        candidates = _candidates(key, lang)[:MAX_CANDIDATES + 1]
        if len(candidates) > MAX_CANDIDATES:
            return False
        roots = {root for candidate in candidates for root in candidate}
        for root in roots:  # every candidate root is screened before any accept
            lookup.check_private(root)
        if any(all(lookup.public(root) for root in candidate) for candidate in candidates):
            return True
        return lang == "de" and len(key) >= 2 * MIN_DE_PART and _de_compound(key, lookup)
    except _Rejected:
        return False
