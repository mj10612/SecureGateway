"""Bounded prose morphology: generic positives, private collisions, budgets."""

import unicodedata

import pytest

from secure_gateway import gateway_morphology
from secure_gateway.gateway_morphology import MAX_TOKEN_LENGTH, is_ordinary_form

PUBLIC = frozenset({
    # ko: dictionary-form predicates and nouns supplied by the caller
    "먹다", "가다", "오다", "보다", "주다", "하다", "살다", "쓰다", "마시다", "돕다", "덥다", "되다",
    "잡다", "있다", "보내다", "공부", "사용", "책", "학교", "친구", "바다", "노을",
    # de
    "haus", "tür", "arbeit", "platz", "sonne", "schein", "bahnhof", "uhr", "kind", "garten",
    # ar
    "بيت", "كتاب", "مدرسة",
    # mr / te
    "घर", "शाळा", "బడి", "పుస్తకం",
})
PRIVATE = frozenset({"민서", "müller", "노을", "رامي", "सोनाली", "రవి", "kai"})


def ordinary(word, language, public=PUBLIC, private=PRIVATE):
    return is_ordinary_form(word, language, public.__contains__, private.__contains__)


@pytest.mark.parametrize("word", [
    "먹었어요", "먹습니다", "먹는", "먹고", "먹으면", "먹은", "먹을까요", "먹겠습니다",
    "갔다", "가세요", "가셨습니다", "가는", "갑니다", "와요", "봐요", "줘요", "해요", "했어요",
    "삽니다", "사는", "써요", "마셔요", "도와주세요", "더워요", "돼요", "잡아요", "보냈어요",
    "공부하세요", "공부했습니다", "사용됩니다", "먹고싶어요", "먹어보세요", "가고있어요",
    "책을", "학교에서", "친구들에게", "바다는", "친구와", "책입니다", "친구예요",
])
def test_korean_regular_forms_end_in_known_roots(word):
    assert ordinary(word, "ko")


@pytest.mark.parametrize("word", [
    "민서는", "민서하고", "노을이", "노을", "쿠르릉했어요", "블라뷔하세요", "자몽쿠는", "먹",
])
def test_korean_private_or_unknown_roots_stay_private(word):
    assert not ordinary(word, "ko")


def test_decomposed_hangul_is_normalized_for_lookup_only():
    original = unicodedata.normalize("NFD", "먹었어요")
    assert original != "먹었어요" and ordinary(original, "ko")
    assert not ordinary(unicodedata.normalize("NFD", "민서는"), "ko")


@pytest.mark.parametrize("word", [
    "Haus", "Hauses", "Haustür", "Arbeitsplatz", "Sonnenschein", "Bahnhofsuhr",
    "Kindgarten", "Haustüren",
])
def test_german_bounded_compounds_with_known_components(word):
    assert ordinary(word, "de")


@pytest.mark.parametrize("word", [
    "Müllerstraße", "Müllerhaus", "Zorbelplatz", "Hausblarg", "Kai", "Kaiplatz", "Haus-Tür",
])
def test_german_private_or_unknown_components_reject(word):
    assert not ordinary(word, "de")


@pytest.mark.parametrize("word,expected", [
    ("والبيت", True), ("بالكتاب", True), ("للمدرسة", True), ("فكتاب", True), ("بيت", True),
    ("ورامي", False), ("لرامي", False), ("والزنبق", False), ("رامي", False),
])
def test_arabic_bounded_proclitics(word, expected):
    assert ordinary(word, "ar") is expected


@pytest.mark.parametrize("word,language,expected", [
    ("घरावर", "mr", True), ("शाळाची", "mr", True), ("सोनालीची", "mr", False),
    ("बिलासपूरची", "mr", False), ("బడిలో", "te", True), ("రవికి", "te", False),
    ("చెన్నపట్నంలో", "te", False),
])
def test_indic_reviewed_suffixes_need_caller_roots(word, language, expected):
    assert ordinary(word, language) is expected


@pytest.mark.parametrize("word", [
    "user_name", "abc123", "owner@example.invalid", "https://example.invalid", "HTTP", "iPhone",
    "getHausPlatz", "Haus.Tür", "", "x" * (MAX_TOKEN_LENGTH + 1),
])
def test_code_shaped_or_oversized_tokens_reject(word):
    public = PUBLIC | {word.casefold()}
    assert not ordinary(word, "de", public=public)


def test_no_speculative_stemming_in_unsupported_languages():
    assert ordinary("book", "en", public=PUBLIC | {"book"})
    assert not ordinary("books", "en", public=PUBLIC | {"book"})


def test_public_full_form_that_is_private_is_rejected():
    assert not ordinary("kai", "de", public=PUBLIC | {"kai"})


def test_german_segmentation_work_is_bounded():
    calls = []

    def public(root):
        calls.append(root)
        return root in {"abc", "abca", "bcab"}

    word = "abc" * 26  # 78 chars; many prefix matches, no valid head
    assert not is_ordinary_form(word, "de", public, lambda _: False)
    assert len(set(calls)) <= gateway_morphology.MAX_DE_LOOKUPS + 1


def test_korean_candidate_generation_is_bounded():
    calls = []

    def public(root):
        calls.append(root)
        return False

    word = "가" * MAX_TOKEN_LENGTH
    assert not is_ordinary_form(word, "ko", public, lambda _: False)
    assert len(calls) <= 4 * gateway_morphology.MAX_CANDIDATES


def test_callbacks_receive_normalized_keys_and_text_is_not_rewritten():
    seen = []

    def public(root):
        seen.append(root)
        return root in PUBLIC

    word = unicodedata.normalize("NFD", "Haustür")
    assert is_ordinary_form(word, "de", public, lambda _: False)
    assert all(unicodedata.is_normalized("NFC", r) and r == r.casefold() for r in seen)
    assert word == unicodedata.normalize("NFD", "Haustür")
