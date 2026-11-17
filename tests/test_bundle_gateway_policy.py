"""Trusted document policies reach the gateway before forced numeric splitting (#318)."""

from copy import deepcopy
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import urllib.request

import pytest
from click.testing import CliRunner

from secure_gateway.gateway import GatewaySession, PrivacyGateway
from secure_gateway.gateway_features import GatewayFeatures, resolve_settings


DOCUMENT = "Customer: meadow; Site: grove; Due: 2034-04-18; State: waiting approval"
POLICY = {"document_sha256": sha256(DOCUMENT.encode()).hexdigest(), "scope": [0, len(DOCUMENT)],
          "required_fields": ["Customer", "Site", "Due"], "protect_fields": ["Customer", "Site", "Due"]}


def config(policy=None):
    return {"features": {"contextual_name_spans": False,
                         "attribute_bundle": {"policy": deepcopy(POLICY if policy is None else policy)}}}


def payload(text=DOCUMENT, dialect="codex", role="user"):
    return {"model": "fixture", "messages" if dialect == "claude" else "input":
            [{"role": role, "content": text}]}


def test_trusted_bundle_settings_are_active_and_diagnostics_reveal_no_policy():
    features, report = resolve_settings(config(), environ={})
    assert features.attribute_bundle == POLICY
    assert report["attribute_bundle"]["active"]
    assert report["attribute_bundle"]["source"] == "config"
    assert not any(secret in json.dumps(report["attribute_bundle"]) for secret in (POLICY["document_sha256"], "Customer", "scope"))


@pytest.mark.parametrize("dialect", ["codex", "claude"])
def test_gateway_policy_protects_original_document_even_with_forced_dates(tmp_path, dialect):
    features, report = resolve_settings(config(), environ={})
    server = PrivacyGateway(("127.0.0.1", 0), "test-token-for-local-bundle-policy-only",
                            state_dir=tmp_path, features=features, feature_report=report)
    try:
        session = server.get_session(dialect, "approved-document")
        session.forced_rules = lambda: ("2034-04-18",)
        result = session.request(payload(dialect=dialect))
        masked = result["messages" if dialect == "claude" else "input"][0]["content"]
        assert all(value not in masked for value in ("meadow", "grove", "2034-04-18"))
        assert session.restore(masked) == DOCUMENT
        server.save(dialect, session)
    finally:
        server.server_close()
    restarted = PrivacyGateway(("127.0.0.1", 0), "test-token-for-local-bundle-policy-only",
                               state_dir=tmp_path, features=features, feature_report=report)
    try:
        assert restarted.get_session(dialect, "approved-document").restore(masked) == DOCUMENT
        other = restarted.get_session(dialect, "other-document")
        assert "meadow" in other.request(payload("Review meadow and grove.", dialect=dialect))["messages" if dialect == "claude" else "input"][0]["content"]
    finally:
        restarted.server_close()


def test_direct_mask_validates_whole_document_before_numeric_forcing():
    session = GatewaySession(natural_language="en", features=GatewayFeatures(attribute_bundle=POLICY))
    session.forced_rules = lambda: ("2034-04-18",)
    masked = session.mask(DOCUMENT)
    assert "meadow" not in masked and "grove" not in masked
    assert session.restore(masked) == DOCUMENT
    with pytest.raises(ValueError, match="identity mismatch"):
        session.mask(DOCUMENT + " changed")


@pytest.mark.parametrize("role", ["user", "assistant", "system"])
def test_unmatched_or_non_user_documents_cannot_activate_policy(role):
    features, _ = resolve_settings(config(), environ={})
    session = GatewaySession(natural_language="en", features=features)
    text = DOCUMENT + " changed" if role == "user" else DOCUMENT
    result = session.request(payload(text, role=role))["input"][0]["content"]
    assert "meadow" in result and "grove" in result
    assert session.restore(result) == text


@pytest.mark.parametrize("bad", [
    {"document_sha256": "not-a-hash"}, {"scope": [True, 10]}, {"scope": [10, 2]},
    {"required_fields": []}, {"protect_fields": ["Site", "site"]}, {"unknown": True},
])
def test_malformed_policy_is_rejected_before_gateway_start(bad):
    with pytest.raises(ValueError):
        resolve_settings(config({**POLICY, **bad}), environ={})


def test_policy_can_be_disabled_without_changing_saved_configuration():
    settings = config()
    for overrides in ({"all_off": True}, {"cli": {"attribute_bundle": False}},
                      {"environ": {"SECURE_GATEWAY_FEATURE_ATTRIBUTE_BUNDLE": "off"}}):
        features, report = resolve_settings(settings, **overrides)
        assert features.attribute_bundle is None and not report["attribute_bundle"]["active"]
    assert settings == config()


def test_cli_reports_trusted_document_policy_without_contents(tmp_path, monkeypatch):
    from secure_gateway.cli import main

    monkeypatch.delenv("SECURE_GATEWAY_FEATURE_ATTRIBUTE_BUNDLE", raising=False)
    path = tmp_path / "gateway.json"
    path.write_text(json.dumps({"port": 38117, "token": "t" * 40, **config()}), encoding="utf-8")
    result = CliRunner().invoke(main, ["gateway", "features", "--config", str(path)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["configured"]["attribute_bundle"]["active"]
    assert POLICY["document_sha256"] not in result.output


@pytest.mark.parametrize("dialect", ["codex", "claude"])
def test_http_provider_receives_protection_and_client_receives_exact_restoration(tmp_path, dialect):
    captured = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            document = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            captured.append(document)
            masked = document["messages" if dialect == "claude" else "input"][0]["content"]
            data = json.dumps({"content": [{"type": "text", "text": masked}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    provider_thread = Thread(target=provider.serve_forever, daemon=True)
    provider_thread.start()
    upstream = f"http://127.0.0.1:{provider.server_port}"
    features, report = resolve_settings(config(), environ={})
    server = PrivacyGateway(("127.0.0.1", 0), "local-token", {"claude": upstream, "codex": upstream},
                            state_dir=tmp_path, features=features, feature_report=report)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        path = "/claude/v1/messages" if dialect == "claude" else "/codex/responses"
        headers = {"X-SecureGateway-Token": "local-token", "Content-Type": "application/json",
                   "Authorization": "Bearer sk-ant-oat01-offline" if dialect == "claude" else "Bearer eyJoffline.subscription"}
        req = urllib.request.Request(f"http://127.0.0.1:{server.server_port}{path}",
                                     json.dumps(payload(dialect=dialect)).encode(), headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            assert json.load(response)["content"][0]["text"] == DOCUMENT
        assert len(captured) == 1
        assert all(value not in json.dumps(captured[0]) for value in ("meadow", "grove", "2034-04-18"))
        assert POLICY["document_sha256"] not in json.dumps(captured[0])
    finally:
        server.shutdown()
        thread.join(2)
        server.server_close()
        provider.shutdown()
        provider_thread.join(2)
        provider.server_close()
