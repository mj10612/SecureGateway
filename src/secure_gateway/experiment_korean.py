"""Opt-in experimental Korean action/condition spans; no baseline registration.

This finite lexical morphology candidate proposes public *prose* spans. It is
not a privacy classifier or general Korean analyzer. A caller must subtract all
forced rules, domain matches, existing private mappings, code/tool data and
other protected spans before using a proposal. A familiar action can still be
an organization's secret name; this function cannot infer that private policy.

Only reviewed roots admit reviewed conjugation classes. Unknown stems are never
made public merely because they share an ending. Returned offsets refer to the
original Unicode string; normalization is used only for whole-token lookup.
"""

from __future__ import annotations

import re
import unicodedata

from secure_gateway.engine.tokenizer import MultilingualTokenizer
from secure_gateway.gateway_source import looks_like_source, markdown_code_spans


MAX_INPUT_BYTES = 1024 * 1024
MAX_SPANS = 100_000

# Independently reviewed common task roots. Industrial process verbs and an
# arbitrary noun followed by 하다 are deliberately not part of this class.
_HADA_ROOTS = (
    "확인", "검토", "검증", "검사", "배치", "삭제", "배포", "실행", "보존",
    "제외", "요약", "정리", "질문", "비교", "선택", "변경", "제안", "완료",
    "승인", "준비", "복사", "수정", "설명", "기록", "출력", "포함", "정",
)
_DOEDA_ROOTS = ("손상", "완료", "변경", "확인", "승인", "준비", "삭제")
_BASE_ENDINGS = r"(?:다|고|면|지만|도록|기|기를|기만|는|는지|자|자는|세요|시고|시면|시길|겠으면|겠다면)"
_PAST_ENDINGS = r"(?:다|고|으면|다면|더라도|는지|지만|던|을|을때|을때만)"
_NEGATION = r"지(?:말고|말아|말아줘|말아주세요|말아야|마|마세요|마십시오|않고|않으면|않는)?"
_TEMPORAL = r"(?:뒤에|뒤에는|후에|후에는|다음에|다음에는)"
_BEFORE = r"기(?:전에|전에는)"


def _alternatives(words: tuple[str, ...]) -> str:
    return "(?:" + "|".join(re.escape(word) for word in sorted(words, key=len, reverse=True)) + ")"


_HADA = (
    _alternatives(_HADA_ROOTS) + "?"  # standalone 하다 also carries an action
    + r"(?:하(?:" + _BASE_ENDINGS + "|" + _NEGATION + "|" + _BEFORE + r")"
    + r"|해(?:줘|주세요|주십시오|도|서|야|야만|보고|보세요)?"
    + r"|했" + _PAST_ENDINGS
    + r"|하셨" + _PAST_ENDINGS
    + r"|한(?:" + _TEMPORAL + r")?"
    + r"|할(?:때|때만)?)"
)
_DOEDA = (
    _alternatives(_DOEDA_ROOTS)
    + r"(?:되(?:" + _BASE_ENDINGS + "|" + _NEGATION + "|" + _BEFORE + r")"
    + r"|되었" + _PAST_ENDINGS + r"|됐" + _PAST_ENDINGS
    + r"|되어(?:도|서|야)?|돼(?:도|서|야)?|된(?:" + _TEMPORAL + r")?|될(?:때|때만)?)"
)
_ASK = (
    r"(?:물어보(?:" + _BASE_ENDINGS + "|" + _NEGATION + "|" + _BEFORE + r")"
    + r"|물어봐(?:줘|주세요|도|서)?|물어봤" + _PAST_ENDINGS
    + r"|물어보셨" + _PAST_ENDINGS + r"|물어본(?:" + _TEMPORAL + r")?|물어볼(?:때|때만)?)"
)
_ATTACH = (
    r"(?:붙이(?:" + _BASE_ENDINGS + "|" + _NEGATION + "|" + _BEFORE + r")"
    + r"|붙여(?:줘|주세요|도|서)?|붙였" + _PAST_ENDINGS
    + r"|붙이셨" + _PAST_ENDINGS + r"|붙인(?:" + _TEMPORAL + r")?|붙일(?:때|때만)?)"
)
_TELL = (
    r"(?:알려주(?:" + _BASE_ENDINGS + "|" + _NEGATION + "|" + _BEFORE + r")"
    + r"|알려줘|알려주세요|알려주셨" + _PAST_ENDINGS + r"|알려줬" + _PAST_ENDINGS + r")"
)
_UNKNOWN = (
    r"(?:모르(?:" + _BASE_ENDINGS + "|" + _BEFORE + r")"
    + r"|몰라(?:도|서)?|몰랐" + _PAST_ENDINGS
    + r"|없(?:으면|다면|더라도|지만|고|는|을|을때|을때만|는지|이))"
)
_COPULA = r"(?:정상|비정상)(?:인|이면|이라면|인지|일때|일때만)"
_RELATIONS = r"(?:전에|전에는|뒤에|뒤에는|후에|후에는|말고|마세요|마|주세요)"
_REVIEWED = re.compile(r"(?:" + "|".join((_HADA, _DOEDA, _ASK, _ATTACH, _TELL, _UNKNOWN, _COPULA, _RELATIONS)) + r")\Z")
_OPAQUE = frozenset({"EMAIL", "URL", "SECRET", "UUID", "IP", "PHONE", "CODE_BLOCK"})


def preserve_spans(text: str) -> list[tuple[int, int]]:
    """Return bounded, ordered whole-token proposals in original coordinates.

    This candidate is intentionally not installed in the production gateway.
    No rule identifies confidential names, and no unknown-root suffix is
    disclosed. Complete source inputs and Markdown code spans are excluded.
    """
    if not isinstance(text, str):
        raise ValueError("Korean candidate input must be text")
    if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("Korean candidate input budget exceeded")
    # Source-prefix recognition must not hand a near-budget repeated-token
    # document to Python's AST compiler (which can exhaust parser memory).
    if looks_like_source(text[:4096]):
        return []
    try:
        code_spans = markdown_code_spans(text)
    except ValueError:
        # Incomplete markup does not create new public text boundaries.
        return []
    words = []
    offset = 0
    code_index = 0
    for chunk in MultilingualTokenizer.tokenize(text):
        end = offset + len(chunk.text)
        while code_index < len(code_spans) and code_spans[code_index][1] <= offset:
            code_index += 1
        in_code = code_index < len(code_spans) and code_spans[code_index][0] < end
        if chunk.is_word and chunk.kind not in _OPAQUE and not in_code:
            word = unicodedata.normalize("NFC", chunk.text)
            if re.fullmatch(r"[가-힣]+", word):
                words.append((offset, end, word))
        offset = end
    selected: set[tuple[int, int]] = set()
    for index, (start, end, word) in enumerate(words):
        if _REVIEWED.fullmatch(word):
            selected.add((start, end))
        # 알 and 수 are ambiguous outside this explicit inability phrase.
        if word == "알" and index + 2 < len(words):
            middle, last = words[index + 1], words[index + 2]
            if (middle[2] == "수" and last[2] in {"없으면", "없다면", "없는", "없을", "없을때", "없을때만"}
                    and text[end:middle[0]].isspace() and text[middle[1]:last[0]].isspace()):
                selected.update({(start, end), middle[:2], last[:2]})
        if len(selected) > MAX_SPANS:
            raise ValueError("Korean candidate output budget exceeded")
    return sorted(selected)
