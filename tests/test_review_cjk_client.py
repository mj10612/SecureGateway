"""Explicit CJK terms and local client's code-profile forwarding."""
import pytest

from secure_gateway.client import LocalPrivacyClient
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import MaskMode, SurrogateStrategy, TokenType
from secure_gateway.session import PrivacySession


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("mode", [MaskMode.CONTENT_WORDS, MaskMode.ENTITIES_ONLY, MaskMode.AGGRESSIVE])
@pytest.mark.parametrize("language,source,terms,expected", [
    ("zh", "\u7532\u548c\u4e59", {"\u548c"}, "\u548c"),
    ("ja", "\u6771\u4eac\u306e\u4f1a\u793e", {"\u306e"}, "\u306e"),
    ("zh", "\u7532\u5317\u4eac\u516c\u53f8\u4e59", {"\u5317\u4eac", "\u5317\u4eac\u516c\u53f8"}, "\u5317\u4eac\u516c\u53f8"),
    ("ja", "\u7532API\u4e59", {"API"}, "API"),
    ("zh", "\U00020000\u548c\U00020001", {"\u548c"}, "\u548c"),
])
def test_explicit_cjk_terms_are_atomic_and_restore(strategy, mode, language, source, terms, expected):
    engine = MaskingEngine()
    session = PrivacySession("cjk-terms", strategy=strategy)
    result = engine.mask_text(source, session.session_id, session.generator,
                              session.forward_store, session.reverse_store,
                              language=language, sensitive_terms=terms,
                              custom_preserve=terms, mode=mode)
    forced = [m for m in session.forward_store.values()
              if m.original == expected and m.token_type == TokenType.ENTITY]
    assert len(forced) == 1
    assert expected not in result.masked_text
    assert engine.unmask(result.masked_text, session.session_id,
                         session.reverse_store, strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize("language", ["zh", "ja"])
def test_cjk_boundaries_do_not_match_inside_latin_words(language):
    engine = MaskingEngine()
    session = PrivacySession("latin-boundary")
    engine.mask_text("ABCdef xABC \u7532ABC\u4e59", session.session_id,
                     session.generator, session.forward_store, session.reverse_store,
                     language=language, sensitive_terms={"ABC"})
    forced = [m for m in session.forward_store.values() if m.token_type == TokenType.ENTITY]
    assert [m.original for m in forced] == ["ABC"]


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("language,source", [
    ("vbnet", "Dim secret As String"),
    ("lua", "local secret = 7"),
])
def test_client_passes_explicit_code_language(strategy, language, source):
    sent = []
    def provider(masked):
        sent.append(masked)
        return masked
    with LocalPrivacyClient() as client:
        result = client.request(source, provider, mode=MaskMode.CODE_AWARE,
                                strategy=strategy, code_language=language)
    assert result.unmasked_text == source
    assert "secret" not in sent[0]
    assert ("Dim" if language == "vbnet" else "local") in sent[0]


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("dialect,equivalent", [("sqlite", True), ("postgresql", False), ("standard", False)])
def test_client_forwards_sql_dialect(strategy, dialect, equivalent):
    source = 'SELECT privateName, "PrivateName" FROM privateTable'
    sent = []
    def provider(masked):
        sent.append(masked)
        return masked
    with LocalPrivacyClient() as client:
        result = client.request(source, provider, mode=MaskMode.CODE_AWARE,
                                strategy=strategy, code_language="sql", sql_dialect=dialect)
    assert result.unmasked_text == source
    fields = sent[0].split(" FROM ")[0].removeprefix("SELECT ").split(", ")
    # sqlite identifiers ignore ASCII case even when quoted. Other dialects
    # keep the quoted mixed-case name distinct from the unquoted folded one.
    assert (fields[0].lower() == fields[1].strip('"').lower()) is equivalent


@pytest.mark.parametrize("options", [{"code_language": "invalid"}, {"code_language": "sql", "sql_dialect": "invalid"}])
def test_invalid_client_code_profile_never_calls_provider(options):
    def provider(_):
        pytest.fail("invalid options must fail before the provider")
    with LocalPrivacyClient() as client:
        with pytest.raises(ValueError):
            client.request("private = 7", provider, mode=MaskMode.CODE_AWARE, **options)
        assert client.vault.active_count == 0
