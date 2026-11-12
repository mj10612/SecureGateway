"""Optional context assistance cannot weaken explicit privacy boundaries."""
from contextlib import nullcontext
from hashlib import sha256
import io
import json
import os
import re
from pathlib import Path
from threading import RLock

from click.testing import CliRunner
import pytest

from secure_gateway import context_assets
from secure_gateway.cli import main
from secure_gateway.context_model import ContextModel, load_context_model
from secure_gateway.gateway import GatewaySession, PrivacyGateway
from secure_gateway.encrypted_session import load_session, save_session
from secure_gateway.engine.natural_languages import tokenize


class PublicModel:
    """An overconfident helper must still lose to the gateway's hard rules."""
    def __init__(self):
        self.calls = 0

    def public_spans(self, text, spans, language):
        self.calls += 1
        return frozenset(spans)

    def request_budget(self):
        return nullcontext()


def test_public_words_do_not_depend_on_context_model_occurrence_votes():
    class FirstOnly(PublicModel):
        def public_spans(self, text, spans, language):
            return frozenset(span for span in spans if span[0] == 0)
    session = GatewaySession(natural_language="en", context_model=FirstOnly())
    text = "Paint works with Paint."
    masked = session.mask(text)
    assert masked == text
    assert session.restore(masked) == text


@pytest.mark.parametrize("language,text,private", [
    ("en", "Zorvexa works here.", "Zorvexa"),
    ("pt", "Cemente as amostras no forno.", "Cemente"),
    ("ko", "동결건조하시오. 그 뒤에 바이알을 밀봉한다.", "동결건조"),
])
def test_model_confidence_cannot_disclose_registered_private_vocabulary(language, text, private):
    session = GatewaySession(natural_language=language, context_model=PublicModel())
    session.forced_rules = lambda: (private,)
    masked = session.mask(text)
    assert private not in masked
    assert session.restore(masked) == text


@pytest.mark.parametrize("text", ["Use `value` Paint the room.", "Read SKILL.md Paint the room."])
def test_split_prose_does_not_create_model_sentence_boundary(text):
    baseline = GatewaySession(natural_language="en").mask(text)
    assisted = GatewaySession(natural_language="en", context_model=PublicModel()).mask(text)
    assert assisted == baseline


def test_force_prior_mappings_domain_patterns_and_numbers_dominate_model():
    model = PublicModel()
    session = GatewaySession(natural_language="en", context_model=model)
    session.mask("Zorvexa", code=True)
    session.forced_rules = lambda: ("window",)
    text = "Explain Zorvexa and insulin to John near the window: alice@example.com 37591"
    masked = session.mask(text)
    assert all(word not in masked for word in ("Zorvexa", "window", "alice@example.com"))
    # #374: an unlabelled ordinary number is public by default.
    assert "insulin" in masked and "John" in masked and "37591" in masked
    assert session.restore(masked) == text


def test_reviewed_domain_root_remains_private_in_verbal_inflections():
    session = GatewaySession(natural_language="ko", context_model=PublicModel())
    text = "표면을 전기도금하십시오. 결과를 기록해 주세요."
    masked = session.mask(text)
    assert "전기도금" not in masked
    assert session.restore(masked) == text


def test_strict_data_code_tool_values_and_aggressive_skip_model():
    model = PublicModel()
    session = GatewaySession(natural_language="en", context_model=model)
    source = "customer_value = 'ordinary meeting'"
    assert session.restore(session.mask(source, code=True)) == source
    assert session.restore(session.walk_data("ordinary meeting")) == "ordinary meeting"
    assert "ordinary meeting" not in session.values("ordinary meeting")
    assert model.calls == 0
    aggressive = GatewaySession(natural_language="en", prose_mode="aggressive", context_model=model)
    assert "Zorvexa" not in aggressive.mask("Explain Zorvexa")
    assert model.calls == 0


@pytest.mark.parametrize("name", ["summarizeData", "private_method", "ZORVEXA", "account37591", "customer.Paint"])
def test_identifier_shapes_never_become_public_through_model(name):
    session = GatewaySession(natural_language="en", context_model=PublicModel())
    text = "Please inspect " + name + " before continuing."
    masked = session.mask(text)
    assert name not in masked
    if "." in name:
        assert name.rsplit(".", 1)[1] not in masked
    assert session.restore(masked) == text


@pytest.mark.parametrize("language,private,text", [
    ("ja", "変更", "値を変更してください。"),
    ("zh", "调整", "请先调整现有选项。"),
    ("ja", "顧客一覧", "この顧客一覧を確認してください。"),
])
def test_prior_cjk_source_words_stay_private_inside_prose(language, private, text):
    session = GatewaySession(natural_language=language, context_model=PublicModel())
    session.mask(private, code=True)
    masked = session.mask(text)
    assert private not in masked
    assert session.restore(masked) == text


def test_cjk_opaque_data_and_restored_code_origins_remain_private(tmp_path):
    session = GatewaySession(natural_language="ja", context_model=PublicModel())
    session.walk_data("変更")
    session.mask("顧客一覧", code=True)
    path = tmp_path / "session.enc"
    save_session(path, session.session, "test-password")
    restored = GatewaySession(load_session(path, "test-password"), natural_language="ja", context_model=PublicModel())
    text = "この顧客一覧を変更してください。"
    masked = restored.mask(text)
    assert "変更" not in masked and "顧客一覧" not in masked
    assert restored.restore(masked) == text


@pytest.mark.parametrize("language,data,private,text", [
    ("ja", "変更予約", "変更", "値を変更してください。"),
    ("zh", "变更预约", "变更", "请先变更现有选项。"),
])
def test_adjacent_strict_data_aliases_keep_private_origin(language, data, private, text):
    session = GatewaySession(natural_language=language, context_model=PublicModel())
    session.walk_data(data)
    assert all(mapping.source_reference for mapping in session.session.forward_store.values())
    assert private not in session.mask(text)


@pytest.mark.parametrize("language,private,text", [
    ("ja", "変更", "値を変更してください。"),
    ("zh", "调整", "请调整这个值。"),
])
def test_alternate_sql_binding_protects_same_spelling_in_cjk_prose(language, private, text):
    session = GatewaySession(natural_language=language, sql_dialect="standard", context_model=PublicModel())
    session.mask(f'SELECT "{private}";', code=True, language="sql")
    session.mask(private)
    masked = session.mask(text)
    assert private not in masked
    assert session.restore(masked) == text


def bare_model():
    model = ContextModel.__new__(ContextModel)
    model.lock = RLock()
    model.calls = model.errors = model.skipped = 0
    return model


def test_request_budget_caches_seed_decisions_and_limits_total_work():
    model = bare_model()
    calls = []
    def classify(text, spans):
        calls.extend(spans)
        return frozenset(spans)
    model._public_spans = classify
    spans = [(i, i + 2) for i in range(32)]
    with model.request_budget():
        first = model.public_spans("x" * 80, spans, "en")
        assert model.public_spans("x" * 80, spans[:20], "en") == first.intersection(spans[:20])
        model.public_spans("y" * 80, spans, "en")
        assert not model.public_spans("z" * 80, spans, "en")
    assert len(calls) == 64
    with model.request_budget():
        assert model.public_spans("z" * 80, spans, "en")
    assert len(calls) == 96


def test_inference_failure_falls_back_without_network(monkeypatch):
    model = bare_model()
    def broken(*_):
        raise RuntimeError("private input must not be logged")
    model._public_spans = broken
    monkeypatch.setattr(context_assets.urllib.request, "urlopen", lambda *_a, **_k: pytest.fail("Inference must remain offline"))
    assert not model.public_spans("private input", [(0, 7)], "en")
    assert model.diagnostics() == {"status": "ready", "model": "context-e5-small-v1", "calls": 0, "errors": 1, "skipped": 0}


def test_missing_model_reports_unavailable_and_retains_default_masking(tmp_path):
    model, status = load_context_model(str(tmp_path))
    assert model is None and status == "unavailable"
    with PrivacyGateway(("127.0.0.1", 0), "x" * 32, context_model_path=str(tmp_path)) as gateway:
        assert gateway.session_diagnostics()["context_model"]["status"] == "unavailable"
        session = gateway.get_session("codex")
        assert session.mask("Zorvexa") == GatewaySession().mask("Zorvexa")
        session.forced_rules = lambda: ("Zorvexa",)
        assert "Zorvexa" not in session.mask("Zorvexa")


@pytest.mark.parametrize("path", ["relative/model", "", 42, False])
def test_model_path_is_local_and_explicit(path):
    with pytest.raises(ValueError, match="absolute local"):
        load_context_model(path)


@pytest.fixture
def tiny_assets(monkeypatch):
    data = b"verified model data"
    monkeypatch.setattr(context_assets, "FILES", {"model.onnx": ("model.onnx", len(data), sha256(data).hexdigest())})
    monkeypatch.setattr(context_assets.urllib.request, "urlopen", lambda *_a, **_k: io.BytesIO(data))
    return data


def test_install_reuses_verified_data_and_remove_preserves_other_files(tmp_path, tiny_assets, monkeypatch):
    context_assets.install_model(tmp_path)
    monkeypatch.setattr(context_assets.urllib.request, "urlopen", lambda *_a, **_k: pytest.fail("Redownloaded verified model"))
    context_assets.install_model(tmp_path)
    unrelated = tmp_path / "notes.txt"
    unrelated.write_text("user data")
    context_assets.remove_model(tmp_path)
    assert unrelated.read_text() == "user data"
    assert not (tmp_path / "model.onnx").exists()


def test_download_collision_and_modified_remove_never_clobber(tmp_path, tiny_assets, monkeypatch):
    target = tmp_path / "model.onnx"
    def race(*_a, **_k):
        target.write_bytes(b"user data")
        return io.BytesIO(tiny_assets)
    monkeypatch.setattr(context_assets.urllib.request, "urlopen", race)
    with pytest.raises(FileExistsError):
        context_assets.install_model(tmp_path)
    assert target.read_bytes() == b"user data"
    with pytest.raises(ValueError, match="no model files"):
        context_assets.remove_model(tmp_path)
    assert target.read_bytes() == b"user data"
    assert not (tmp_path / "model.onnx.download").exists()


def test_download_size_checksum_and_preexisting_partial_are_guarded(tmp_path, tiny_assets, monkeypatch):
    monkeypatch.setattr(context_assets.urllib.request, "urlopen", lambda *_a, **_k: io.BytesIO(tiny_assets + b"overflow"))
    with pytest.raises(ValueError, match="size"):
        context_assets.install_model(tmp_path)
    assert not list(tmp_path.iterdir())
    monkeypatch.setattr(context_assets.urllib.request, "urlopen", lambda *_a, **_k: io.BytesIO(b"wrong bytes"))
    with pytest.raises(ValueError, match="checksum"):
        context_assets.install_model(tmp_path)
    partial = tmp_path / "model.onnx.download"
    partial.write_bytes(b"another installer")
    with pytest.raises(FileExistsError):
        context_assets.install_model(tmp_path)
    assert partial.read_bytes() == b"another installer"


def test_model_cli_install_and_remove_are_explicit(tmp_path, tiny_assets):
    runner = CliRunner()
    result = runner.invoke(main, ["gateway", "model-install", "--directory", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "context_model_path" in result.output
    assert runner.invoke(main, ["gateway", "model-remove", "--directory", str(tmp_path)]).exit_code == 0


@pytest.mark.parametrize("apostrophe", ["'", "’"])
def test_private_whole_possessive_suffix_overrides_public_grammar(apostrophe):
    session = GatewaySession(natural_language="en", context_model=PublicModel())
    suffix = apostrophe + "s"
    session.mask("Drelvona", code=True)
    session.mask(json.dumps(suffix, ensure_ascii=False), code=True, language="python")
    text = f"Ask Drelvona{suffix} coordinator."
    payload = {"model": "fixture", "input": [{"role": "user", "content": text}]}
    masked = session.request(payload)["input"][0]["content"]
    assert suffix not in masked
    assert "Drelvona" not in masked
    assert session.restore(masked) == text
    assert session.request(payload)["input"][0]["content"] == masked
    assert not any(mapping.original == "s" for mapping in session.session.forward_store.values())


@pytest.mark.parametrize("apostrophe", ["'", "’"])
def test_english_possessive_retains_grammar_without_creating_s_mapping(apostrophe):
    session = GatewaySession(natural_language="en", context_model=PublicModel())
    text = f"Ask Drelvona{apostrophe}s coordinator to confirm the missing cartons."
    payload = {"model": "fixture", "input": [{"role": "user", "content": text}]}
    masked = session.request(payload)["input"][0]["content"]
    assert f"{apostrophe}s" in masked
    assert "Drelvona" not in masked
    assert session.restore(masked) == text
    assert session.request(payload)["input"][0]["content"] == masked
    assert not any(mapping.original == "s" for mapping in session.session.forward_store.values())


@pytest.mark.parametrize("apostrophe", ["'", "’"])
def test_french_elision_keeps_grammar_when_private_term_splits_fragment(apostrophe):
    session = GatewaySession(natural_language="fr")
    text = f"Nous avons intégré le module d{apostrophe}Zorvexa d{apostrophe}papier."
    payload = {"model": "fixture", "input": [{"role": "user", "content": text}]}
    masked = session.request(payload)["input"][0]["content"]
    assert f"d{apostrophe}" in masked
    assert "Zorvexa" not in masked
    assert session.restore(masked) == text
    assert session.request(payload)["input"][0]["content"] == masked
    assert not any(mapping.original == "d" for mapping in session.session.forward_store.values())


@pytest.mark.skipif(not os.getenv("SECURE_GATEWAY_CONTEXT_MODEL_DIR"), reason="Optional pinned local model integration")
def test_real_model_keeps_requests_stable_private_and_locally_restorable():
    model = ContextModel(Path(os.environ["SECURE_GATEWAY_CONTEXT_MODEL_DIR"]))
    for language, text in [
        ("en", "Explain how to fold the paper for Zorvexa. Keep this as a proposal; do not send it."),
        ("de", "Erstelle für Zorvexa zuerst eine Liste und beschreibe danach die Vorbereitung."),
        ("ko", "Zorvexa의 조건이 불분명하면 추측하지 말고 필요한 정보를 알려 주세요."),
    ]:
        session = GatewaySession(natural_language=language, context_model=model)
        request = {"model": "fixture", "input": [{"role": "user", "content": text}]}
        masked = session.request(request)["input"][0]["content"]
        assert "Zorvexa" not in masked
        assert session.restore(masked) == text
        assert session.request(request)["input"][0]["content"] == masked


@pytest.mark.skipif(not os.getenv("SECURE_GATEWAY_CONTEXT_MODEL_DIR"), reason="Optional independent local-model corpus")
def test_real_model_independent_corpora_do_not_add_private_exposure(tmp_path):
    model = ContextModel(Path(os.environ["SECURE_GATEWAY_CONTEXT_MODEL_DIR"]))
    fixtures = Path(__file__).parent / "fixtures"
    examples = []
    for name in ("context_classification.json", "context_challenge.json", "context_morphology.json", "context_final_holdout.json", "context_confirmation.json"):
        rows = json.loads((fixtures / name).read_text(encoding="utf-8"))["examples"]
        examples.extend(row for row in rows if row["split"] == "test")
    def visible(text, candidate):
        return candidate in re.sub(r"private_symbol_\d+|732846\d{12}", " ", text)
    results = []
    for row in examples:
        payload = {"model": "fixture", "input": [{"role": "user", "content": row["text"]}]}
        baseline = GatewaySession(natural_language=row["language"])
        assisted = GatewaySession(natural_language=row["language"], context_model=model)
        before = baseline.request(payload)["input"][0]["content"]
        after = assisted.request(payload)["input"][0]["content"]
        assert assisted.restore(after) == row["text"], row["id"]
        assert assisted.request(payload)["input"][0]["content"] == after, row["id"]
        if row["label"] == "private":
            for component in [row["candidate"], *(c.text for c in tokenize(row["candidate"], row["language"]) if c.is_word and len(c.text) >= 2)]:
                assert not visible(after, component) or visible(before, component), (row["id"], component)
        results.append({"id": row["id"], "language": row["language"], "label": row["label"],
                        "baseline_visible": visible(before, row["candidate"]), "model_visible": visible(after, row["candidate"])})
    assert sum(r["label"] == "public" and r["model_visible"] for r in results) > sum(
        r["label"] == "public" and r["baseline_visible"] for r in results)
    (tmp_path / "context-corpus-results.json").write_text(json.dumps(results), encoding="utf-8")
