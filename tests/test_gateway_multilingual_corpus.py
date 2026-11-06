"""Synthetic everyday text and repository prose; no fluency claim is implied."""
import json
from pathlib import Path

import pytest

from secure_gateway.engine.natural_languages import SUPPORTED_LANGUAGES
from secure_gateway.gateway import GatewaySession


ROOT = Path(__file__).resolve().parents[1]
CORPUS = json.loads((ROOT / "tests/fixtures/everyday_multilingual.json").read_text(encoding="utf-8"))
ADDITIONAL = json.loads((ROOT / "tests/fixtures/everyday_additional.json").read_text(encoding="utf-8"))
INDEPENDENT = json.loads((ROOT / "tests/fixtures/independent_multilingual.json").read_text(encoding="utf-8"))
FRESH = json.loads((ROOT / "tests/fixtures/fresh_multilingual.json").read_text(encoding="utf-8"))
SENSITIVE = json.loads((ROOT / "tests/fixtures/sensitive_multilingual.json").read_text(encoding="utf-8"))
MEETING_CONCEPTS = {
    "en": ("meeting", "starts"), "ko": ("회의", "시작하는지"),
    "es": ("reunión", "empieza"), "fr": ("réunion", "commence"),
    "pt": ("reunião", "começa"), "de": ("Treffen", "beginnt"),
    "id": ("rapat", "dimulai"), "tr": ("toplantının", "başladığını"),
    "ru": ("встреча", "начинается"), "hi": ("बैठक", "शुरू"),
    "mr": ("बैठक", "सुरू"), "bn": ("সভা", "শুরু"),
    "ur": ("اجلاس", "شروع"), "te": ("సమావేశం", "మొదలవుతుందో"),
    "ar": ("الاجتماع", "يبدأ"), "zh": ("会议", "开始"),
    "ja": ("会議", "始まる"),
}
ADDITIONAL_CONCEPTS = {
    "en": ("book", "home", "find"), "ko": ("책", "집", "찾아"),
    "es": ("libro", "casa", "encontrar"), "fr": ("livre", "maison", "retrouver"),
    "pt": ("livro", "casa", "encontrar"), "de": ("Buch", "Hause", "finden"),
    "id": ("buku", "rumah", "menemukan"), "tr": ("kitabı", "bulmama"),
    "ru": ("книгу", "дома", "найти"), "hi": ("किताब", "घर", "ढूँढ़ने"),
    "mr": ("पुस्तक", "घरी", "शोधायला"), "bn": ("বইটি", "বাড়িতে", "খুঁজে"),
    "ur": ("کتاب", "گھر", "ڈھونڈنے"), "te": ("పుస్తకాన్ని", "ఇంట్లో", "కనుగొనడానికి"),
    "ar": ("الكتاب", "المنزل", "العثور"), "zh": ("书", "家", "找到"),
    "ja": ("本", "家", "探す"),
}


def prose_lines(language):
    """Read real project prose, excluding code, link lists and headings."""
    source = (ROOT / "docs/i18n" / f"README.{language}.md").read_text(encoding="utf-8")
    in_fence = False
    for line in source.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and len(line) >= 50 and not line.startswith(("#", "[")):
            yield line


CASES = [
    pytest.param(language, text, index, id=f"{language}-everyday-{index + 1}")
    for language, texts in CORPUS.items() for index, text in enumerate(texts)
] + [
    pytest.param(language, text, 0, id=f"{language}-additional")
    for language, text in ADDITIONAL.items()
] + [
    pytest.param(language, text, 0, id=f"{language}-independent")
    for language, text in INDEPENDENT.items()
] + [
    pytest.param(language, text, 0, id=f"{language}-fresh")
    for language, text in FRESH.items()
] + [
    pytest.param(language, text, index, id=f"{language}-documentation-{index + 1}")
    for language in CORPUS for index, text in enumerate(prose_lines(language))
]


def test_corpus_covers_all_supported_languages():
    assert set(CORPUS) == SUPPORTED_LANGUAGES - {"auto"}
    assert set(SENSITIVE) == set(CORPUS)
    assert set(ADDITIONAL) == set(CORPUS)
    assert set(INDEPENDENT) == set(CORPUS)
    assert set(FRESH) == set(CORPUS)
    assert all(len(texts) >= 5 for texts in CORPUS.values())
    assert all(len(item["terms"]) == 3 for item in SENSITIVE.values())


@pytest.mark.parametrize("language", CORPUS)
def test_ordinary_meeting_request_keeps_subject_and_action(language):
    forwarded = GatewaySession(natural_language=language).mask(CORPUS[language][0])
    for concept in MEETING_CONCEPTS[language]:
        assert concept in forwarded


@pytest.mark.parametrize("language", CORPUS)
def test_auto_language_keeps_common_request_concepts(language):
    forwarded = GatewaySession().mask(CORPUS[language][0])
    for concept in MEETING_CONCEPTS[language]:
        assert concept in forwarded


@pytest.mark.parametrize("language", ADDITIONAL)
def test_everyday_request_keeps_object_place_and_action(language):
    forwarded = GatewaySession(natural_language=language).mask(ADDITIONAL[language])
    for concept in ADDITIONAL_CONCEPTS[language]:
        assert concept in forwarded


@pytest.mark.parametrize("language,text,index", CASES)
def test_multilingual_passages_mask_private_values_and_restore(language, text, index):
    session = GatewaySession(natural_language=language)
    fixture = SENSITIVE[language]
    private = (fixture["person"], fixture["company"], *fixture["terms"],
               f"person{index}@example.invalid")
    original = text + "\n" + " | ".join(private)
    masked = session.request({"model": "fixture", "input": [{"role": "user", "content": original}]})
    forwarded = masked["input"][0]["content"]
    for value in private:
        assert value not in forwarded, f"Unmasked {language} fixture: {value}"
        for component in value.split():
            assert component not in forwarded, f"Unmasked {language} component: {component}"
    assert session.restore(forwarded) == original


@pytest.mark.parametrize("language", CORPUS)
def test_long_multilingual_document_keeps_aliases_stable(language):
    sample = SENSITIVE[language]
    private = (sample["person"], sample["company"], *sample["terms"], "person@example.invalid")
    paragraph = "\n".join([*CORPUS[language], *prose_lines(language), " | ".join(private)])
    session = GatewaySession(natural_language=language)
    first = session.mask(paragraph)
    document = (paragraph + "\n") * 20
    assert len(document.encode("utf-8")) >= 16000
    masked = session.mask(document)
    assert all(value not in masked for value in private)
    assert session.restore(masked) == document
    assert session.restore(first) == paragraph
    count = len(session.session.forward_store)
    assert session.mask(document) == masked
    assert len(session.session.forward_store) == count
