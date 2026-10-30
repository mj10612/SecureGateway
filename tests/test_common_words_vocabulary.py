"""Independent small acceptance corpus for the offline starter vocabulary."""

import pytest

from secure_gateway.engine.common_words import (
    COMMON_WORDS,
    COMMON_WORDS_VERSION,
    is_common,
    vocabulary_key,
)


# Hand-labelled holdout examples; no tests derive labels from the dictionary.
GENERAL_EN = ("meeting", "work", "question", "school", "water", "time", "file", "uses")
UNCOMMON_EN = ("zorblyx", "nexvanta", "privatename", "meetng", "xyqv", "team_omega", "apiX42")
GENERAL_KO = ("회의", "질문", "학교", "시간", "문서", "결과", "사용", "업무")
UNCOMMON_KO = ("초롱비밀사업", "김민서", "넥스반타", "조르블릭스", "기밀부호", "햇살암호단")


def test_vocabulary_scope_and_reviewed_version():
    assert COMMON_WORDS_VERSION == "1"
    assert set(COMMON_WORDS) == {"en", "ko"}
    assert len(COMMON_WORDS["en"]) >= 150
    assert len(COMMON_WORDS["ko"]) >= 80


@pytest.mark.parametrize("language,general,uncommon", [
    ("en", GENERAL_EN, UNCOMMON_EN), ("ko", GENERAL_KO, UNCOMMON_KO),
])
def test_independent_general_and_uncommon_vocabulary(language, general, uncommon):
    assert all(is_common(word, language) for word in general)
    assert all(not is_common(word, language) for word in uncommon)


def test_extra_vocabulary_normalization_and_unsupported_language():
    extra = {vocabulary_key(word) for word in ("Cafe\u0301", "조직단어")}
    assert is_common("CAFÉ", "en", extra)
    assert is_common("조직단어", "fr", extra)
    assert not is_common("meeting", "fr")
    assert not is_common("cafeteria", "en", extra)
    assert extra == {"café", "조직단어"}


def test_korean_lookup_normalizes_decomposed_hangul():
    import unicodedata

    assert is_common(unicodedata.normalize("NFD", "회의"), "ko")


@pytest.mark.parametrize("strategy_name", ["bracket", "unicode", "pseudoword", "hash"])
def test_uncommon_policy_holdout_and_exact_restoration(strategy_name):
    from secure_gateway.engine.masking_engine import MaskingEngine
    from secure_gateway.models import MaskMode, SurrogateStrategy
    from secure_gateway.session import PrivacySession

    engine = MaskingEngine()
    strategy = SurrogateStrategy(strategy_name)
    for language, general, uncommon in (("en", GENERAL_EN, UNCOMMON_EN),
                                        ("ko", GENERAL_KO, UNCOMMON_KO)):
        for word in (*general, *uncommon):
            session = PrivacySession("holdout", strategy=strategy)
            result = engine.mask_text(word, session.session_id, session.generator,
                                      session.forward_store, session.reverse_store,
                                      mode=MaskMode.UNCOMMON_WORDS, language=language)
            assert (result.masked_tokens == 0) == (word in general), (language, word)
            restored = engine.unmask(result.masked_text, session.session_id,
                                     session.reverse_store, strategy, strict=True)
            assert restored.unmasked_text == word


def test_holdout_compares_policies_without_claiming_dictionary_completeness():
    from secure_gateway.engine.masking_engine import MaskingEngine
    from secure_gateway.models import MaskMode
    from secure_gateway.session import PrivacySession

    scores = {}
    engine = MaskingEngine()
    for mode in (MaskMode.CONTENT_WORDS, MaskMode.ENTITIES_ONLY, MaskMode.UNCOMMON_WORDS):
        found = false_positives = misses = 0
        for language, general, uncommon in (("en", GENERAL_EN, UNCOMMON_EN),
                                            ("ko", GENERAL_KO, UNCOMMON_KO)):
            for word in (*general, *uncommon):
                session = PrivacySession("comparison")
                result = engine.mask_text(word, session.session_id, session.generator,
                                          session.forward_store, session.reverse_store,
                                          mode=mode, language=language)
                detected = result.masked_tokens > 0
                if word in uncommon:
                    found += detected
                    misses += not detected
                else:
                    false_positives += detected
        scores[mode] = (found, false_positives, misses)
    # This intentionally small, hand-labelled fixture proves the policy gap,
    # not statistical accuracy on real-world text or privacy classification.
    assert scores[MaskMode.UNCOMMON_WORDS] == (13, 0, 0)
    assert scores[MaskMode.CONTENT_WORDS][1] > 0
    assert scores[MaskMode.ENTITIES_ONLY][2] > 0


@pytest.mark.parametrize("word", ["CommonName", "Meeting", "MEETING"])
def test_proper_name_cues_override_common_vocabulary(word):
    from secure_gateway.engine.masking_engine import MaskingEngine
    from secure_gateway.models import MaskMode
    from secure_gateway.session import PrivacySession

    session = PrivacySession("proper-name")
    result = MaskingEngine().mask_text(
        word, session.session_id, session.generator, session.forward_store,
        session.reverse_store, mode=MaskMode.UNCOMMON_WORDS, language="en",
        common_vocabulary={word},
    )
    assert result.masked_tokens == 1
