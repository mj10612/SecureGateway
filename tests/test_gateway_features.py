"""Per-session opt-in features (#354): combinations, isolation, settings and restart."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from threading import Barrier, Thread
import urllib.error
import urllib.request

from click.testing import CliRunner
import pytest

from secure_gateway import gateway
from secure_gateway.engine import strategies
from secure_gateway.experiment_profiles import candidate_profile
from secure_gateway.gateway_features import (
    CORRECTIONS_PASSWORD_ENV,
    DEFAULT_FEATURES,
    FEATURES,
    GatewayFeatures,
    resolve_settings,
)
from secure_gateway.private_arithmetic import LOCAL_ARITHMETIC_TOOL_NAME

FUTURE = 4102444800
KO = "선반 높이를 모르면 먼저 물어보세요."
NAMES = "Project name: drift. Review it."
FOLLOW = "Check drift before release."
CORRECTION = "Review meadow before publication."
BUNDLE = "Customer: Brook; Site: NorthQuay; Due: 2034-04-18; State: waiting approval"


def record(term):
    return {"term": term, "project": "alpha", "language": "en", "source": "explicit-local-correction",
            "expires_at": FUTURE, "revoked": False}


CORRECTIONS = {"trusted_project": "alpha", "workspace": "alpha", "language": "en", "policyrecords": [record("meadow")]}
BUNDLE_POLICY = {"document_sha256": sha256(BUNDLE.encode()).hexdigest(), "scope": [0, len(BUNDLE)],
                 "required_fields": ["Customer", "Site", "Due"], "protect_fields": ["Customer", "Site", "Due"]}
SINGLE = {
    309: (GatewayFeatures(ko_conjugation_split=True), None),
    310: (GatewayFeatures(contextual_name_spans=True), None),
    316: (GatewayFeatures(scoped_corrections=CORRECTIONS), CORRECTIONS),
    318: (GatewayFeatures(attribute_bundle=BUNDLE_POLICY), BUNDLE_POLICY),
    319: (GatewayFeatures(local_arithmetic=True), None),
}
ALL_ON = GatewayFeatures(ko_conjugation_split=True, contextual_name_spans=True, scoped_corrections=CORRECTIONS,
                         attribute_bundle=BUNDLE_POLICY, local_arithmetic=True)


@pytest.fixture
def nonce(monkeypatch):
    state = {"value": 100000}

    def draw(limit):
        state["value"] += 1
        return state["value"] % limit

    monkeypatch.setattr(strategies.secrets, "randbelow", draw)
    return state


def request(text, key="input"):
    return {"model": "fixture", key: [{"role": "user", "content": text}]}


def transcript(session, texts):
    output = []
    for text in texts:
        result = session.request(request(text))
        output.append(json.dumps(result, sort_keys=True, ensure_ascii=False))
        masked = result["input"][0]["content"]
        assert session.restore(masked) == text
    return output


def test_default_features_are_off_and_validated():
    assert DEFAULT_FEATURES.enabled_names() == () and not DEFAULT_FEATURES.any_enabled
    assert gateway.GatewaySession().features is DEFAULT_FEATURES
    assert set(ALL_ON.enabled_names()) == set(FEATURES)
    with pytest.raises(ValueError):
        GatewayFeatures(ko_conjugation_split="yes")
    with pytest.raises(ValueError):
        GatewayFeatures(scoped_corrections=True)
    with pytest.raises(ValueError):
        GatewayFeatures(local_arithmetic={"unknown": 1})
    with pytest.raises(ValueError):
        gateway.GatewaySession(features={"ko_conjugation_split": True})


@pytest.mark.parametrize("issue", sorted(SINGLE))
def test_each_flag_alone_matches_its_compatibility_profile(issue, nonce):
    features, policy = SINGLE[issue]
    texts = [KO, NAMES, FOLLOW, CORRECTION, BUNDLE]
    nonce["value"] = 100000
    with candidate_profile(issue, policy):
        expected = transcript(gateway.GatewaySession(natural_language="auto"), texts)
    nonce["value"] = 100000
    assert transcript(gateway.GatewaySession(natural_language="auto", features=features), texts) == expected
    nonce["value"] = 100000
    assert transcript(gateway.GatewaySession(natural_language="auto"), texts) != expected or issue in {309}


def test_all_features_on_together_protect_and_restore():
    session = gateway.GatewaySession(natural_language="auto", features=ALL_ON)
    korean = session.request(request(KO))["input"][0]["content"]
    assert "모르면" in korean and "물어보세요" in korean
    named = session.request(request(NAMES))["input"][0]["content"]
    later = session.request(request(FOLLOW))["input"][0]["content"]
    assert "drift" not in named and "drift" not in later
    corrected = session.request(request(CORRECTION))["input"][0]["content"]
    assert "meadow" not in corrected
    bundle = session.request(request(BUNDLE))["input"][0]["content"]
    assert all(value not in bundle for value in ("Brook", "NorthQuay", "2034-04-18"))
    claude = session.request(request("Calculate total", key="messages"))
    assert any(tool.get("name") == LOCAL_ARITHMETIC_TOOL_NAME for tool in claude["tools"])
    for text, masked in ((KO, korean), (NAMES, named), (FOLLOW, later), (CORRECTION, corrected), (BUNDLE, bundle)):
        assert session.restore(masked) == text


def test_features_need_no_global_state_and_profiles_still_refuse_nesting():
    before = gateway.GatewaySession, gateway.SharedEngine, gateway.ordinary_words
    first = gateway.GatewaySession(features=SINGLE[310][0])
    second = gateway.GatewaySession(features=SINGLE[309][0])
    assert (gateway.GatewaySession, gateway.SharedEngine, gateway.ordinary_words) == before
    assert first.engine.features is not second.engine.features
    assert not gateway.GatewaySession().engine.ko_conjugation_split
    with candidate_profile(310):
        with pytest.raises(ValueError):
            with candidate_profile(309):
                pass


def test_concurrent_sessions_with_different_features_stay_isolated():
    named = gateway.GatewaySession(natural_language="en", features=GatewayFeatures(contextual_name_spans=True))
    corrected = gateway.GatewaySession(natural_language="en", features=GatewayFeatures(scoped_corrections=CORRECTIONS))
    plain = gateway.GatewaySession(natural_language="en")
    barrier = Barrier(3)
    text = "Project name: drift. Review meadow and drift."

    def run(session):
        barrier.wait()
        results = []
        for _ in range(20):
            with session.lock:
                results.append(session.request(request(text))["input"][0]["content"])
        return results

    with ThreadPoolExecutor(3) as pool:
        outputs = list(pool.map(run, (named, corrected, plain)))
    assert all("drift" not in item and "meadow" in item for item in outputs[0])
    assert all("meadow" not in item and "drift" in item.split("Project name: ")[1] for item in outputs[1])
    assert all("drift" in item and "meadow" in item for item in outputs[2])
    assert not plain.session.forward_store.originals_in(text)
    assert "meadow" not in named.session.forward_store.originals_in(text)
    assert "drift" not in corrected.session.forward_store.originals_in(text)
    assert all(len(set(result)) == 1 for result in outputs)


def test_disabled_path_is_byte_identical_to_default():
    payload = request("Review EmberQzx. If approval is unknown, ask first; do not publish.")
    off = gateway.GatewaySession(natural_language="en", features=GatewayFeatures()).request(payload)
    encoded = json.dumps(off, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    assert sha256(encoded).hexdigest() == "a904367ef76f8571e15b5876ad46f5c5d195ac93fca329451aec4ca2a7859043"
    features, report = resolve_settings({"features": {"contextual_name_spans": True}}, environ={}, all_off=True)
    assert features.enabled_names() == () and report["contextual_name_spans"]["source"] == "cli-off"


def test_settings_precedence_and_sources():
    config = {"features": {"ko_conjugation_split": True, "contextual_name_spans": "on"}}
    features, report = resolve_settings(config, environ={"SECURE_GATEWAY_FEATURE_CONTEXTUAL_NAME_SPANS": "off",
                                                         "SECURE_GATEWAY_FEATURE_LOCAL_ARITHMETIC": "1"},
                                        cli={"ko_conjugation_split": False})
    assert features.enabled_names() == ("local_arithmetic",)
    assert {name: (item["enabled"], item["source"]) for name, item in report.items()} == {
        "ko_conjugation_split": (False, "cli"), "contextual_name_spans": (False, "env"),
        "scoped_corrections": (True, "default"), "attribute_bundle": (True, "default"),
        "local_arithmetic": (True, "env")}
    # 2.17.0 defaults: #310 on, #316/#318 policy-gated (inactive without a policy), others off.
    assert {name: item["default"] for name, item in report.items()} == {
        "ko_conjugation_split": False, "contextual_name_spans": True, "scoped_corrections": True,
        "attribute_bundle": True, "local_arithmetic": False}
    assert not report["scoped_corrections"]["active"] and not report["attribute_bundle"]["active"]
    defaults = resolve_settings({}, environ={})[1]
    assert all(item["source"] == "default" for item in defaults.values())
    assert {name for name, item in defaults.items() if item["active"]} == {"contextual_name_spans"}
    for bad in ({"features": {"unknown": True}}, {"features": {"ko_conjugation_split": "maybe"}}, {"features": []},
                {"features": {"attribute_bundle": True}}):
        with pytest.raises(ValueError):
            resolve_settings(bad, environ={})
    with pytest.raises(ValueError):
        resolve_settings({}, environ={"SECURE_GATEWAY_FEATURE_KO_CONJUGATION_SPLIT": "sometimes"})


def test_scoped_corrections_load_encrypted_records(tmp_path):
    from secure_gateway.experiment_corrections import save_record

    path = tmp_path / "corrections.enc"
    save_record(path, "local-passphrase", {**record("meadow"), "policy_version": 1, "created_at": 1.0})
    config = {"features": {"scoped_corrections": {"project": "alpha", "language": "en", "records_file": str(path)}}}
    with pytest.raises(ValueError, match=CORRECTIONS_PASSWORD_ENV):
        resolve_settings(config, environ={})
    with pytest.raises(ValueError, match="could not be loaded"):
        resolve_settings(config, environ={CORRECTIONS_PASSWORD_ENV: "wrong"})
    features, report = resolve_settings(config, environ={CORRECTIONS_PASSWORD_ENV: "local-passphrase"})
    assert features.correction_terms == ("meadow",)
    assert "meadow" not in json.dumps(report)
    masked = gateway.GatewaySession(natural_language="en", features=features).mask(CORRECTION)
    assert "meadow" not in masked
    disabled = {"features": {"scoped_corrections": {"enabled": False, "project": "alpha"}}}
    assert resolve_settings(disabled, environ={})[0].enabled_names() == ("contextual_name_spans",)


def make_gateway(tmp_path, features=None, report=None):
    return gateway.PrivacyGateway(("127.0.0.1", 0), "local-private-token-for-test-only",
                                  upstreams={"claude": "http://127.0.0.1:9", "codex": "http://127.0.0.1:9"},
                                  state_dir=tmp_path / "sessions", features=features, feature_report=report)


def test_restart_restores_aliases_and_applies_current_features(tmp_path):
    features, report = resolve_settings({"features": {"contextual_name_spans": True}}, environ={})
    first = make_gateway(tmp_path, features, report)
    try:
        session = first.get_session("codex", "conversation-a")
        masked = session.request(request(NAMES))["input"][0]["content"]
        other = first.get_session("claude", "conversation-b")
        assert session.features is features and other.features is features
        assert "drift" in other.mask("Watch physical drift.")
        first.save("codex", session)
    finally:
        first.server_close()
    second = make_gateway(tmp_path, features, report)
    try:
        restored = second.get_session("codex", "conversation-a")
        assert restored.features.contextual_name_spans
        assert restored.restore(masked) == NAMES
        assert "drift" not in restored.request(request(FOLLOW))["input"][0]["content"]
        second.save("codex", restored)
    finally:
        second.server_close()
    # Rollback: restarting without the feature keeps old aliases restorable.
    third = make_gateway(tmp_path)
    try:
        rolled_back = third.get_session("codex", "conversation-a")
        assert not rolled_back.features.any_enabled and rolled_back.restore(masked) == NAMES
        assert "drift" in third.get_session("codex", "conversation-new").mask("Watch physical drift.")
    finally:
        third.server_close()


def test_diagnostics_report_sources_without_policy_contents(tmp_path):
    features, report = resolve_settings({"features": {"local_arithmetic": True}}, environ={},
                                        cli={"ko_conjugation_split": True})
    server = make_gateway(tmp_path, features, report)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        headers = {"X-SecureGateway-Token": server.token}
        with urllib.request.urlopen(urllib.request.Request(url + "/admin/api/features", headers=headers), timeout=5) as response:
            settings = json.loads(response.read())
        assert settings["enabled"] == ["ko_conjugation_split", "contextual_name_spans", "local_arithmetic"]
        assert settings["settings"]["ko_conjugation_split"]["source"] == "cli"
        assert settings["settings"]["local_arithmetic"]["source"] == "config"
        assert settings["settings"]["contextual_name_spans"] == {
            "issue": 310, "default": True, "default_mode": "on", "enabled": True, "active": True,
            "source": "default", "gateway_setting": "boolean"}
        with pytest.raises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(url + "/admin/api/features", timeout=5)
        assert denied.value.code == 401
        denied.value.close()
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"port": server.server_port, "token": server.token}))
        from secure_gateway.cli import main
        result = CliRunner().invoke(main, ["gateway", "diagnostics", "--config", str(config)])
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["features"]["enabled"] == [
            "ko_conjugation_split", "contextual_name_spans", "local_arithmetic"]
    finally:
        server.shutdown()
        thread.join(2)
        server.server_close()
    plain = make_gateway(tmp_path / "x")
    try:
        assert plain.feature_settings()["enabled"] == []
        assert all(item["source"] == "default" for item in plain.session_diagnostics()["features"]["settings"].values())
    finally:
        plain.server_close()


def test_cli_features_command_reports_configured_state(tmp_path, monkeypatch):
    from secure_gateway.cli import main

    monkeypatch.delenv("SECURE_GATEWAY_FEATURE_KO_CONJUGATION_SPLIT", raising=False)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"port": 38117, "token": "t" * 40, "features": {"ko_conjugation_split": True}}))
    runner = CliRunner()
    result = runner.invoke(main, ["gateway", "features", "--config", str(config)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["configured"]["ko_conjugation_split"]["source"] == "config"
    off = runner.invoke(main, ["gateway", "features", "--config", str(config), "--features-off"])
    assert json.loads(off.output)["configured"]["ko_conjugation_split"] == {
        "issue": 309, "default": False, "default_mode": "off", "enabled": False, "active": False,
        "source": "cli-off", "gateway_setting": "boolean"}
    flag = runner.invoke(main, ["gateway", "features", "--config", str(config), "--feature", "ko_conjugation_split=off"])
    assert json.loads(flag.output)["configured"]["ko_conjugation_split"]["source"] == "cli"
    bad = runner.invoke(main, ["gateway", "features", "--config", str(config), "--feature", "nope=on"])
    assert bad.exit_code != 0
