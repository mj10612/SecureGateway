"""Korean word count must not multiply the cost of copying a vocabulary."""
import pytest

from secure_gateway.engine import grammar_ko
from secure_gateway.engine.grammar_ko import KoreanGrammarEngine
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import MaskMode, SurrogateStrategy
from secure_gateway.session import PrivacySession


@pytest.mark.parametrize("mode", [MaskMode.CONTENT_WORDS, MaskMode.UNCOMMON_WORDS])
@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_korean_words_never_union_the_full_vocabulary(monkeypatch, mode, strategy):
    class CountUnions(set):
        unions = 0
        def __or__(self, other):
            self.unions += 1
            return super().__or__(other)
    builtins = CountUnions(grammar_ko.KNOWN_STEMS)
    monkeypatch.setattr(grammar_ko, "KNOWN_STEMS", builtins)
    session = PrivacySession("no-copies", strategy=strategy)
    engine = MaskingEngine()
    source = "문서 " * 200
    result = engine.mask_text(source, session.session_id, session.generator,
                              session.forward_store, session.reverse_store,
                              mode=mode, language="ko",
                              common_vocabulary={f"extra{n}" for n in range(10000)})
    assert builtins.unions == 0
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source
    if mode == MaskMode.UNCOMMON_WORDS:
        assert result.masked_tokens == 0


def test_builtin_and_mutable_custom_stems_both_supply_membership():
    known = {"루미노바"}
    assert KoreanGrammarEngine.decompose_token("결과가", known)[:2] == ("결과", "가")
    assert KoreanGrammarEngine.decompose_token("루미노바가", known)[:2] == ("루미노바", "가")
    known.clear()
    assert KoreanGrammarEngine.decompose_token("루미노바가", known)[:2] == ("루미노바가", "")
    assert KoreanGrammarEngine.decompose_token("결과가", None)[:2] == ("결과", "가")


@pytest.mark.parametrize("plain_dict", [False, True])
@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_request_learns_new_stems_without_repeated_store_enumeration(plain_dict, strategy):
    class CountValues(dict):
        calls = 0
        def values(self):
            self.calls += 1
            return super().values()
    session = PrivacySession("new-stems", strategy=strategy)
    forward = CountValues() if plain_dict else session.forward_store
    reverse = {} if plain_dict else session.reverse_store
    source = "루미노바 루미노바가 and AnotherSecret"
    engine = MaskingEngine()
    result = engine.mask_text(source, session.session_id, session.generator,
                              forward, reverse)
    first, second, connective, _ = result.masked_text.split()
    assert second == first + "가" and connective == "and"
    if plain_dict:
        assert forward.calls == 1
    assert engine.unmask(result.masked_text, session.session_id, reverse,
                         strategy, strict=True).unmasked_text == source
