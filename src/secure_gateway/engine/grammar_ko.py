"""Korean grammar, agglutinative particle (조사) separation, and token classification engine."""

from __future__ import annotations

import re
from typing import AbstractSet, Set, Tuple
from secure_gateway.models import TokenType


# Korean closed-class connective and grammatical functional words (접속사, 기능부사, 지시대명사 등)
KOREAN_FUNCTION_WORDS: Set[str] = {
    # 접속사 / 연결어
    "그리고",
    "그러나",
    "그런데",
    "하지만",
    "따라서",
    "그러므로",
    "또한",
    "및",
    "또는",
    "혹은",
    "게다가",
    "더구나",
    "결국",
    "즉",
    "그러면",
    "그럼",
    "그래서",
    "비록",
    "반면에",
    "한편",
    "오히려",
    "요컨대",
    # 지시대명사 / 관형사
    "이",
    "그",
    "저",
    "이것",
    "그것",
    "저것",
    "여기",
    "거기",
    "저기",
    "이곳",
    "그곳",
    "저곳",
    "이때",
    "그때",
    "저때",
    "이런",
    "그런",
    "저런",
    "모든",
    "어떤",
    "각",
    "각각",
    "매",
    "몇",
    "여러",
    "온갖",
    "무슨",
    # 기능 부사 (정도/빈도/양태)
    "매우",
    "아주",
    "너무",
    "더",
    "덜",
    "가장",
    "제일",
    "이미",
    "벌써",
    "아직",
    "항상",
    "늘",
    "자주",
    "가끔",
    "때때로",
    "전혀",
    "결코",
    "오직",
    "단지",
    "다만",
    "함께",
    "같이",
    "서로",
    "스스로",
    "직접",
    "특히",
    "주로",
    "참",
    "정말",
    "진짜",
    "반드시",
    "꼭",
    "아마",
    "혹시",
    "어쩌면",
    "과연",
    # 보조용언 / 기본 어미 표현
    "있다",
    "없다",
    "계시다",
    "않다",
    "못하다",
    "되다",
    "하다",
    "있으며",
    "없으며",
    "있고",
    "없고",
    "있지만",
    "없지만",
}

# Sorted by length in descending order for greedy longest-match stripping
KOREAN_JOSA_LIST: list[str] = sorted(
    set(
        [
            # 복합 조사 / 장문 조사
            "으로부터",
            "로부터",
            "한테서부터",
            "에서부터",
            "에게서는",
            "에게서",
            "에게도",
            "에게만",
            "한테서",
            "한테는",
            "한테도",
            "한테만",
            "에서는",
            "에서도",
            "에서만",
            "으로서",
            "로서",
            "으로써",
            "로써",
            "으로는",
            "로는",
            "으로도",
            "로도",
            "으로만",
            "로만",
            "와는",
            "과는",
            "와도",
            "과도",
            "와의",
            "과의",
            "에는",
            "에도",
            "에만",
            "까지는",
            "까지도",
            "부터는",
            "부터도",
            "이라도",
            "라도",
            "이나마",
            "나마",
            "이야말로",
            "야말로",
            "조차도",
            "마저도",
            "뿐만아니라",
            "에게",
            "한테",
            "에서",
            "으로",
            "보다",
            "처럼",
            "만큼",
            "까지",
            "부터",
            "이라",
            "라도",
            "나마",
            "조차",
            "마저",
            "대로",
            "따라",
            "에게",
            "한테",
            "께서",
            "이며",
            "이나",
            "이란",
            "이야",
            "치고",
            "마는",
            "하구",
            # 단일 조사
            "은",
            "는",
            "이",
            "가",
            "을",
            "를",
            "에",
            "의",
            "로",
            "도",
            "만",
            "와",
            "과",
            "야",
            "여",
            "랑",
            "서",
            "께",
            "엔",
            "론",
            "선",
        ]
    ),
    key=lambda s: (-len(s), s),
)

# Copula / Predicate endings attached to nouns (서술격조사 / 서술어미)
KOREAN_COPULA_LIST: list[str] = sorted(
    set(
        [
            "이었습니다",
            "였습니다",
            "이었습니다",
            "이었습니다만",
            "였습니다만",
            "입니다",
            "였습니다",
            "입니다만",
            "이었다",
            "였다",
            "이고",
            "이며",
            "이면",
            "이라서",
            "이지만",
            "이라",
            "이다",
        ]
    ),
    key=lambda s: (-len(s), s),
)

# Evidence for ambiguous short suffixes. Unknown stems remain whole for privacy.
KNOWN_STEMS = set(
    "회의 국가 인도 대만 개인 통일 로그인 확인 승인 원인 결과 사과 내일 김민서 박하은 홍길동 데이터 고객 환자 서버 병원 대학 회사 삼성전자 카카오 네이버 클라우드 카카오페이 플랫폼 솔루션 계약 보안 인프라 파트너십 금액 이름 계정 기록 결제 프로젝트".split()
)

# Plural suffixes
KOREAN_PLURAL = "들"

# Bounded conjugation/condition/negation/request/sequence/adnominal endings (candidate ko_conjugation_split)
KOREAN_CONJUGATION_ENDINGS: list[str] = sorted(
    {
        # Conditional
        "면", "으면",
        # Sequence (with and without internal space)
        "기 전에", "기전에", "기 전", "기전", "기",
        "ㄴ 뒤에", "ㄴ뒤에", "ㄴ 뒤", "ㄴ뒤",
        "은 뒤에", "은뒤에", "은 뒤", "은뒤",
        "ㄴ 후에", "ㄴ후에", "은 후에", "은후에",
        # Negation / Prohibition (with and without internal space)
        "지 말고", "지말고", "지 마", "지마", "지 마세요", "지마세요",
        "지 마십시오", "지마십시오", "지 않고", "지않고", "지 않으면", "지않으면", "지 않다", "지않다", "지",
        # Request (with and without internal space)
        "세요", "으세요", "해줘", "해 줘", "해줘요", "해 줘요", "해주세요", "해 주세요", "해주십시오", "해 주십시오",
        "어줘", "어 줘", "아줘", "아 줘", "어주세요", "어 주세요", "아주세요", "아 주세요",
        "어주십시오", "어 주십시오", "아주십시오", "아 주십시오",
        # Adnominal
        "된", "한", "는", "은", "ㄴ",
        # Compound verb endings
        "하기 전에", "하기전에", "하지 말고", "하지말고", "하지 마", "하지마", "하지 마세요", "하지마세요",
        "하지 마십시오", "하지마십시오", "하지 않고", "하지않고", "하지 않으면", "하지않으면",
        "하기", "하지", "하고", "하면", "해도", "해서", "해야", "하며",
    },
    key=lambda s: (-len(s), s),
)


def is_hangul_char(ch: str) -> bool:
    """Return True if character is a Korean Hangul syllable."""
    return 0xAC00 <= ord(ch) <= 0xD7A3


def is_hangul_string(s: str) -> bool:
    """Return True if string contains Korean Hangul characters."""
    return any(is_hangul_char(c) for c in s)


def has_batchim(ch: str) -> bool:
    """Return True if the Korean Hangul syllable has a final consonant (받침)."""
    if not is_hangul_char(ch):
        return False
    return (ord(ch) - 0xAC00) % 28 != 0


class KoreanGrammarEngine:
    """Decomposes Korean agglutinative word forms into content stem and grammatical particle/suffix."""

    @staticmethod
    def is_function_word(word: str) -> bool:
        """Check if entire token is a closed-class grammatical functional word."""
        clean = word.strip(".,!?;:\"'()[]{}~`")
        return clean in KOREAN_FUNCTION_WORDS

    @classmethod
    def decompose_token(
        cls, token: str, known_stems: AbstractSet[str] | None = None,
        allow_conjugation: bool = False,
    ) -> Tuple[str, str, TokenType]:
        """Decompose an agglutinative Korean token into (stem, grammatical_suffix, token_type).

        Example:
            '삼성전자가' -> ('삼성전자', '가', TokenType.ENTITY)
            '고객들에게' -> ('고객', '들에게', TokenType.NOUN)
            '결과입니다' -> ('결과', '입니다', TokenType.NOUN)
            '그리고'     -> ('그리고', '', TokenType.GRAMMAR)
        """
        clean = token.strip()
        if not clean:
            return token, "", TokenType.GRAMMAR

        # If it's a known standalone function word
        if cls.is_function_word(clean):
            return clean, "", TokenType.GRAMMAR

        # Keep membership live without copying every supplied stem per word.
        known_word = clean in KNOWN_STEMS or (
            known_stems is not None and clean in known_stems
        )

        # Numbers with Korean units (e.g. 100만, 500원, 30개)
        num_match = re.match(
            r"^(\d+(?:,\d{3})*(?:\.\d+)?)(억원|만원|억|만|조|원|개|명|달러|건|회|년|월|일|시|분|초|%)?(.*)$",
            clean,
        )
        if num_match:
            val, unit, rest = num_match.groups()
            if rest and rest not in set(KOREAN_JOSA_LIST) | set(KOREAN_COPULA_LIST):
                # An arbitrary tail is private content, not a grammatical suffix.
                return clean, "", TokenType.NUMBER
            return val + (unit or ""), rest or "", TokenType.NUMBER

        # Check for plural suffix + josa (e.g., 고객들에게 -> stem: 고객, suffix: 들에게)
        best_stem = clean
        best_suffix = ""

        # Check copula endings first (e.g. 병원입니다 -> 병원 + 입니다)
        for copula in KOREAN_COPULA_LIST if not known_word else []:
            if clean.endswith(copula) and len(clean) > len(copula):
                stem_candidate = clean[: -len(copula)]
                # Ensure stem is substantive
                if len(stem_candidate) >= 1:
                    best_stem = stem_candidate
                    best_suffix = copula
                    break

        # If not copula, check plural + josa
        if not best_suffix:
            # Check plural prefix in josa (e.g. 들에게)
            for josa in KOREAN_JOSA_LIST:
                plural_josa = KOREAN_PLURAL + josa
                if clean.endswith(plural_josa) and len(clean) > len(plural_josa):
                    best_stem = clean[: -len(plural_josa)]
                    best_suffix = plural_josa
                    break

        # If not plural+josa, check standard josa
        if not best_suffix:
            for josa in KOREAN_JOSA_LIST:
                if clean.endswith(josa) and len(clean) > len(josa):
                    candidate = clean[: -len(josa)]
                    # Heuristic: Avoid stripping if stem is empty or single jamo
                    if not known_word and cls._supported_stem(
                        candidate, josa, known_stems
                    ):
                        best_stem = candidate
                        best_suffix = josa
                        break

        # Just plural suffix (고객들 -> 고객 + 들)
        if (
            not best_suffix
            and clean.endswith(KOREAN_PLURAL)
            and len(clean) > len(KOREAN_PLURAL)
        ):
            best_stem = clean[: -len(KOREAN_PLURAL)]
            best_suffix = KOREAN_PLURAL

        # Conjugation / condition / negation / request / adnominal split (candidate ko_conjugation_split)
        if allow_conjugation and not best_suffix and not known_word:
            decomp = cls.decompose_conjugation(clean, known_stems)
            if decomp is not None:
                best_stem, best_suffix, token_type = decomp
                return best_stem, best_suffix, token_type

        # Determine token type
        # Check if stem looks like entity (company/org/person/capitalized)
        if re.search(
            r"(전자|통신|증권|생명|건설|병원|대학|학회|재단|협회|포털|네이버|카카오|삼성|엘지|현대|SK|KT|LG)",
            best_stem,
            re.IGNORECASE,
        ):
            token_type = TokenType.ENTITY
        elif any(c.isupper() for c in best_stem):
            token_type = TokenType.ENTITY
        else:
            token_type = TokenType.NOUN

        return best_stem, best_suffix, token_type

    @classmethod
    def decompose_conjugation(
        cls, clean: str, known_stems: AbstractSet[str] | None = None
    ) -> Tuple[str, str, TokenType] | None:
        """Decompose a Korean token by bounded rule-based verbal/conjugational ending."""
        if len(clean) < 2:
            return None
        for ending in KOREAN_CONJUGATION_ENDINGS:
            if ending == "ㄴ":
                if clean.endswith("ㄴ") and len(clean) > 1:
                    stem = clean[:-1]
                    if not is_hangul_char(stem[-1]) and stem[-1].isalnum():
                        return stem, "ㄴ", TokenType.ENTITY
                continue
            if clean.endswith(ending) and len(clean) > len(ending):
                stem = clean[:-len(ending)]
                if not stem:
                    continue
                # Foreign/alphanumeric stem
                if not is_hangul_char(stem[-1]):
                    if stem[-1].isalnum():
                        return stem, ending, TokenType.ENTITY
                    continue

                # Batchim condition validation
                has_b = has_batchim(stem[-1])
                coda = (ord(stem[-1]) - 0xAC00) % 28
                # 으-alternating endings require batchim (except ㄹ)
                if ending.startswith(("으", "은")):
                    if not has_b or coda == 8:
                        continue
                # 면, 세요 require vowel or ㄹ batchim
                elif ending in {"면", "세요"}:
                    if has_b and coda != 8:
                        continue
                token_type = TokenType.ENTITY if any(c.isupper() for c in stem) else TokenType.NOUN
                return stem, ending, token_type

        # Check adnominal ㄴ coda contraction on vowel stem
        if is_hangul_char(clean[-1]):
            code = ord(clean[-1]) - 0xAC00
            coda = code % 28
            if coda == 4:  # ㄴ 받침
                lead = code // 588
                vowel = (code % 588) // 28
                vowel_syllable = chr(0xAC00 + (lead * 21 + vowel) * 28)
                stem_cand = clean[:-1] + vowel_syllable
                if len(stem_cand) >= 1:
                    token_type = TokenType.ENTITY if any(c.isupper() for c in stem_cand) else TokenType.NOUN
                    return stem_cand, "ㄴ", token_type
        return None

    @staticmethod
    def _supported_stem(stem: str, suffix: str, known: AbstractSet[str] | None) -> bool:
        if not stem:
            return False
        # Foreign names/acronyms have unknown pronunciation; retain their written particle.
        if not is_hangul_char(stem[-1]):
            return stem[-1].isalnum()
        if (stem not in KNOWN_STEMS and (known is None or stem not in known)
                and len(suffix) <= 2):
            return False
        pairs = {
            "은": True,
            "는": False,
            "이": True,
            "가": False,
            "을": True,
            "를": False,
            "과": True,
            "와": False,
        }
        first = suffix[0]
        return first not in pairs or has_batchim(stem[-1]) == pairs[first]


def normalize_particle(original: str, particle: str) -> str:
    """Choose a Korean allomorph; never guess pronunciation of Latin stems."""
    if not original or not is_hangul_char(original[-1]):
        return particle
    batchim = has_batchim(original[-1])
    # Copular endings are not subject-marker 이/가 allomorphs. Retain the
    # written form rather than guessing contraction of an arbitrary ending.
    if particle.startswith(("이라", "이지만", "이다", "이야", "이란", "이며", "이고", "이니")):
        return particle
    for consonant, vowel in [
        ("으로", "로"),
        ("이랑", "랑"),
        ("이나", "나"),
        ("은", "는"),
        ("을", "를"),
        ("과", "와"),
        ("이", "가"),
    ]:
        for variant in (consonant, vowel):
            if particle.startswith(variant):
                if consonant == "이" and particle[len(variant):] not in {
                    "", "도", "만", "는", "부터", "의",
                }:
                    continue
                use_consonant = batchim
                if consonant == "으로" and (ord(original[-1]) - 0xAC00) % 28 == 8:
                    use_consonant = False
                return (consonant if use_consonant else vowel) + particle[
                    len(variant) :
                ]
    return particle
