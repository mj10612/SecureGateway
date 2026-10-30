"""Exercise selected prose policy through real public entry points."""
import json
import pytest
from click.testing import CliRunner
from secure_gateway.cli import main
from secure_gateway.client import LocalPrivacyClient
from secure_gateway.encrypted_session import save_session, load_session
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.gateway import GatewaySession, PrivacyGateway
from secure_gateway.models import MaskMode, SurrogateStrategy
from secure_gateway.session import PrivacySession

@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_uncommon_snapshot_and_overrides(strategy, tmp_path):
    e = MaskingEngine()
    s = PrivacySession("words", strategy=strategy, mode=MaskMode.UNCOMMON_WORDS)
    source = "the meeting uses zorblyx and nexvanta at test@example.com"
    r = e.mask_text(source, s.session_id, s.generator, s.forward_store, s.reverse_store,
                    mode=MaskMode.UNCOMMON_WORDS, common_vocabulary={"NEXVANTA"}, sensitive_terms={"meeting"}, custom_preserve={"meeting", "test@example.com"})
    assert "meeting" not in r.masked_text and "zorblyx" not in r.masked_text
    assert "nexvanta" in r.masked_text and "test@example.com" not in r.masked_text
    path = tmp_path / "words.enc"
    save_session(path, s, "test-password")
    s = load_session(path, "test-password")
    assert s.mode == MaskMode.UNCOMMON_WORDS
    assert e.unmask(r.masked_text, s.session_id, s.reverse_store, strategy, strict=True).unmasked_text == source


def test_cli_mcp_sdk_same_policy():
    source = "the meeting uses zorblyx and nexvanta"
    result = CliRunner().invoke(main, ["mask", source, "--session-id", "words-cli", "--mode", "uncommon_words", "--common-word", "nexvanta", "--json-output"])
    assert result.exit_code == 0, result.output
    masked = json.loads(result.output)["masked_text"]
    assert "meeting" in masked and "nexvanta" in masked and "zorblyx" not in masked
    from secure_gateway.server import mask_text, unmask_text
    import uuid
    sid = "words-mcp-" + uuid.uuid4().hex
    data = json.loads(mask_text(source, sid, mode="uncommon_words", common_vocabulary=["nexvanta"]))
    assert data["masked_text"] == masked
    assert json.loads(unmask_text(masked, sid))["unmasked_text"] == source
    seen = []
    with LocalPrivacyClient() as client:
        restored = client.request(source, lambda payload: seen.append(payload) or payload,
                     mode=MaskMode.UNCOMMON_WORDS, common_vocabulary={"nexvanta"})
        assert restored.unmasked_text == source and seen == [masked]


def test_gateway_policy_and_code_default_preservation():
    with PrivacyGateway(("127.0.0.1", 0), "t" * 32, prose_mode="uncommon_words", common_words=["nexvanta"]) as gateway:
        session = gateway.get_session("codex")
        masked = session._mask_prose("the meeting uses zorblyx and nexvanta")
        assert "meeting" in masked and "nexvanta" in masked and "zorblyx" not in masked
        code = session._mask_source("privateValue = 7", "python")
        assert "7" in code and "privateValue" not in code


@pytest.mark.parametrize("options", [{"prose_mode":"code_aware"}, {"common_words":"nexvanta"}, {"common_words":[1]}, {"common_words":[""]}])
def test_gateway_invalid_policy_rejected(options):
    with pytest.raises(ValueError):
        GatewaySession(**options)


def test_unsupported_language_falls_back_to_content_and_limits():
    e = MaskingEngine()
    s = PrivacySession("fallback", mapping_limit=1)
    r = e.mask_text("para zorblyx", s.session_id, s.generator, s.forward_store, s.reverse_store,
                    mode=MaskMode.UNCOMMON_WORDS, language="es")
    assert r.masked_text.startswith("para ") and "zorblyx" not in r.masked_text
    with pytest.raises(ValueError, match="Mapping limit"):
        e.mask_text("anotherunknown", s.session_id, s.generator, s.forward_store, s.reverse_store, mode=MaskMode.UNCOMMON_WORDS)


@pytest.mark.parametrize("value", ["meeting", {""}, {1}])
def test_invalid_vocabulary_is_rejected_without_mapping(value):
    e = MaskingEngine()
    s = PrivacySession("invalid")
    with pytest.raises(ValueError, match="Common vocabulary"):
        e.mask_text("private", s.session_id, s.generator, s.forward_store, s.reverse_store, common_vocabulary=value)
    assert not s.forward_store

