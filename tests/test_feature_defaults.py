"""2.17.0 gateway-setting defaults after the joint ADOPT of #310, #316 B and #318.

#310 is on by default, #316 B and #318 are on but active only with a trusted
policy (otherwise a byte-identical no-op), #309 and #319 stay off. Explicit
settings and ``--features-off`` win.
"""

from hashlib import sha256
import json

import pytest

from secure_gateway import gateway
from secure_gateway import gateway_install
from secure_gateway.engine import strategies
from secure_gateway.gateway_features import (
    CORRECTIONS_PASSWORD_ENV,
    SETTING_DEFAULTS,
    GatewayFeatures,
    resolve_settings,
)

NAMES = "Project name: drift. Review it."
CORRECTION = "Review meadow before publication."
BUNDLE = "Customer: Brook; Site: NorthQuay; Due: 2034-04-18; State: waiting approval"
# Output of the 2.15/2.16 default path (GatewayFeatures(), all off) for NAMES.
OFF_NAMES_SHA256 = "a5700849289c71459db0f17a81422b3e4f95039147a27fa2736ca12626a217f4"
BUNDLE_POLICY = {"document_sha256": sha256(BUNDLE.encode()).hexdigest(), "scope": [0, len(BUNDLE)],
                 "required_fields": ["Customer", "Site", "Due"], "protect_fields": ["Customer", "Site", "Due"]}


@pytest.fixture
def nonce(monkeypatch):
    state = {"value": 100000}

    def draw(limit):
        state["value"] += 1
        return state["value"] % limit

    monkeypatch.setattr(strategies.secrets, "randbelow", draw)
    return state


def request(text):
    return {"model": "fixture", "input": [{"role": "user", "content": text}]}


def output(features, text):
    payload = gateway.GatewaySession(natural_language="en", features=features).request(request(text))
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def test_setting_defaults_and_report():
    assert SETTING_DEFAULTS == {"ko_conjugation_split": "off", "contextual_name_spans": "on",
                                "scoped_corrections": "policy", "attribute_bundle": "policy",
                                "local_arithmetic": "off"}
    features, report = resolve_settings({}, environ={})
    assert features.enabled_names() == ("contextual_name_spans",)
    assert report["contextual_name_spans"] == {
        "issue": 310, "default": True, "default_mode": "on", "enabled": True, "active": True,
        "source": "default", "gateway_setting": "boolean"}
    assert report["scoped_corrections"] == {
        "issue": 316, "default": True, "default_mode": "policy", "enabled": True, "active": False,
        "source": "default", "gateway_setting": "records-file", "inactive_reason": "no-policy-configured"}
    assert report["attribute_bundle"] == {
        "issue": 318, "default": True, "default_mode": "policy", "enabled": True, "active": False,
        "source": "default", "gateway_setting": "session-only", "inactive_reason": "per-session-policy-only"}
    for name in ("ko_conjugation_split", "local_arithmetic"):
        assert report[name]["default"] is False and not report[name]["enabled"] and not report[name]["active"]


def test_name_introducer_is_protected_by_default():
    features, _ = resolve_settings({}, environ={})
    session = gateway.GatewaySession(natural_language="en", features=features)
    masked = session.request(request(NAMES))["input"][0]["content"]
    assert "drift" not in masked and session.restore(masked) == NAMES
    assert sha256(output(features, NAMES)).hexdigest() != OFF_NAMES_SHA256


@pytest.mark.parametrize("kwargs", [
    {"config": {"features": {"contextual_name_spans": False}}},
    {"config": {"features": {"contextual_name_spans": "off"}}},
    {"environ": {"SECURE_GATEWAY_FEATURE_CONTEXTUAL_NAME_SPANS": "off"}},
    {"cli": {"contextual_name_spans": False}},
    {"config": {"features": {"contextual_name_spans": True, "ko_conjugation_split": True}}, "all_off": True},
])
def test_explicit_off_and_features_off_restore_old_output(kwargs):
    config = kwargs.pop("config", {})
    environ = kwargs.pop("environ", {})
    features, report = resolve_settings(config, environ=environ, **kwargs)
    assert features.enabled_names() == ()
    assert report["contextual_name_spans"]["enabled"] is False
    assert sha256(output(features, NAMES)).hexdigest() == OFF_NAMES_SHA256
    assert output(features, NAMES) == output(GatewayFeatures(), NAMES) == output(None, NAMES)


def test_cli_features_off_flag_disables_default_on_features(tmp_path):
    from click.testing import CliRunner

    from secure_gateway.cli import _resolve_features, main

    features, report = _resolve_features({}, (), True)
    assert features.enabled_names() == () and {item["source"] for item in report.values()} == {"cli-off"}
    assert not any(item["active"] for item in report.values())
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"port": 38117, "token": "t" * 40}))
    shown = json.loads(CliRunner().invoke(main, ["gateway", "features", "--config", str(config)]).output)
    assert shown["configured"]["contextual_name_spans"]["active"] is True
    off = json.loads(CliRunner().invoke(main, ["gateway", "features", "--config", str(config),
                                               "--features-off"]).output)
    assert not any(item["enabled"] for item in off["configured"].values())


@pytest.mark.parametrize("text", [CORRECTION, BUNDLE, NAMES])
def test_policy_features_without_policy_are_byte_identical_noops(text, nonce):
    # Default-on #316/#318 with no policy configured; #310 turned off to isolate them.
    features, report = resolve_settings({}, environ={}, cli={"contextual_name_spans": False})
    assert features.enabled_names() == () and features.scoped_corrections is None and features.attribute_bundle is None
    assert report["scoped_corrections"]["enabled"] and not report["scoped_corrections"]["active"]
    nonce["value"] = 100000
    candidate = output(features, text)
    nonce["value"] = 100000
    assert candidate == output(GatewayFeatures(), text)


def test_gateway_starts_and_reports_inactive_policy_features(tmp_path):
    features, report = resolve_settings({}, environ={})
    server = gateway.PrivacyGateway(("127.0.0.1", 0), "local-private-token-for-test-only",
                                    upstreams={"claude": "http://127.0.0.1:9", "codex": "http://127.0.0.1:9"},
                                    state_dir=tmp_path / "sessions", features=features, feature_report=report)
    try:
        settings = server.feature_settings()
        assert settings["enabled"] == ["contextual_name_spans"]
        assert settings["settings"]["scoped_corrections"]["inactive_reason"] == "no-policy-configured"
        session = server.get_session("codex", "conversation-a")
        assert "drift" not in session.request(request(NAMES))["input"][0]["content"]
    finally:
        server.server_close()


def test_policy_features_apply_when_configured(tmp_path):
    from secure_gateway.experiment_corrections import save_record

    path = tmp_path / "corrections.enc"
    save_record(path, "local-passphrase", {"term": "meadow", "project": "alpha", "language": "en",
                                           "source": "explicit-local-correction", "expires_at": 4102444800,
                                           "revoked": False, "policy_version": 1, "created_at": 1.0})
    config = {"features": {"scoped_corrections": {"project": "alpha", "language": "en", "records_file": str(path)}}}
    features, report = resolve_settings(config, environ={CORRECTIONS_PASSWORD_ENV: "local-passphrase"})
    assert features.enabled_names() == ("contextual_name_spans", "scoped_corrections")
    assert report["scoped_corrections"]["active"] and report["scoped_corrections"]["source"] == "config"
    masked = gateway.GatewaySession(natural_language="en", features=features).mask(CORRECTION + " " + NAMES)
    assert "meadow" not in masked and "drift" not in masked
    # A configured records file is an explicit request: failures still stop the gateway.
    with pytest.raises(ValueError, match=CORRECTIONS_PASSWORD_ENV):
        resolve_settings(config, environ={})
    # Explicit enabling without a policy is still refused rather than silently ignored.
    with pytest.raises(ValueError):
        resolve_settings({"features": {"scoped_corrections": True}}, environ={})
    with pytest.raises(ValueError):
        resolve_settings({}, environ={"SECURE_GATEWAY_FEATURE_ATTRIBUTE_BUNDLE": "on"})
    # #318 applies whenever a trusted per-session policy is supplied, alongside the #310 default.
    session = gateway.GatewaySession(natural_language="en", features=GatewayFeatures(
        contextual_name_spans=True, attribute_bundle=BUNDLE_POLICY))
    masked = session.request(request(BUNDLE))["input"][0]["content"]
    assert "Brook" not in masked and "NorthQuay" not in masked and session.restore(masked) == BUNDLE


def install(tmp_path):
    return gateway_install.install_gateway(tmp_path / "gateway/config.json", agent="claude",
                                           claude_dir=tmp_path / "claude", startup_path=tmp_path / "startup")


def test_upgrade_keeps_explicit_settings_and_new_installs_get_defaults(tmp_path):
    install(tmp_path / "new")
    fresh = gateway_install.load_config(tmp_path / "new/gateway/config.json")
    assert "features" not in fresh
    assert resolve_settings(fresh, environ={})[0].enabled_names() == ("contextual_name_spans",)

    config_path = tmp_path / "old/gateway/config.json"
    config_path.parent.mkdir(parents=True)
    explicit = {"contextual_name_spans": False, "scoped_corrections": {"enabled": False},
                "ko_conjugation_split": False}
    config_path.write_text(json.dumps({"port": 38117, "token": "t" * 40, "features": explicit}))
    install(tmp_path / "old")
    upgraded = gateway_install.load_config(config_path)
    assert upgraded["features"] == explicit
    features, report = resolve_settings(upgraded, environ={})
    assert features.enabled_names() == ()
    assert report["contextual_name_spans"]["source"] == "config" and not report["scoped_corrections"]["enabled"]
    # The #318 default still reports as policy-gated and inactive; it never blocks start.
    assert report["attribute_bundle"]["active"] is False
