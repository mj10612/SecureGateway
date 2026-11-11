"""Tests for content audit phase 2 span derivation and verification API (#343)."""

from contextlib import contextmanager
import json
from threading import Thread
import urllib.error
import urllib.request

from secure_gateway.gateway import PrivacyGateway


@contextmanager
def gateway_at(root):
    with PrivacyGateway(("127.0.0.1", 0), "local-token", state_dir=root / "sessions",
                        audit_path=root / "logs.sqlite3") as gateway:
        worker = Thread(target=gateway.serve_forever, daemon=True)
        worker.start()
        try:
            yield gateway
        finally:
            gateway.shutdown()
            worker.join(5)


def api(gateway, endpoint, body=None, *, method=None, token="local-token", origin=None, host=None):
    headers = {"X-SecureGateway-Token": token}
    if origin:
        headers["Origin"] = origin
    if host:
        headers["Host"] = host
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(f"http://127.0.0.1:{gateway.server_port}/admin/api/content-audit/{endpoint}",
                                     data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read()), response.headers
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read()), exc.headers


def test_verified_spans_prose_request(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        admin = gateway.content_admin
        store = admin.store

        req_id = "req-prose-1"
        admin._test_bindings = {
            req_id: {
                "⟦cust_alias⟧": "PrivateCustomer",
                "⟦acct_alias⟧": "ACCT12345",
            }
        }

        store.append(req_id, "opened", {"input": ["Hello PrivateCustomer with ACCT12345"]})
        store.append(req_id, "sent", {"phase": "prepared", "fields": ["Hello ⟦cust_alias⟧ with ⟦acct_alias⟧"]})
        store.append(req_id, "sent", {"phase": "sent", "fields": ["Hello ⟦cust_alias⟧ with ⟦acct_alias⟧"]})
        store.append(req_id, "response", {"phase": "received", "fields": ["Welcome back ⟦cust_alias⟧!"]})
        store.append(req_id, "response", {"phase": "displayed", "fields": ["Welcome back PrivateCustomer!"]})
        store.append(req_id, "finished", {"partial": False, "failed": False, "uncertain": False,
                                          "omitted_bytes": 0, "omitted_events": 0})

        status, body, _ = api(gateway, "get", {"request_id": req_id})
        assert status == 200
        assert body["verified_state"] == "완료"
        assert body["uncertain"] is False

        input_sent = body["stages"]["input_sent"]
        assert input_sent["uncertain"] is False
        assert input_sent["notice"] is None
        assert len(input_sent["spans"]) == 2
        assert input_sent["spans"][0]["alias"] == "⟦cust_alias⟧"
        assert input_sent["spans"][1]["alias"] == "⟦acct_alias⟧"

        resp = body["stages"]["response"]
        assert resp["uncertain"] is False
        assert len(resp["spans"]) == 1
        assert resp["spans"][0]["alias"] == "⟦cust_alias⟧"
        assert resp["unrestored_aliases"] == []

        # Check explicit spans endpoint
        s_status, s_body, _ = api(gateway, "spans", {"request_id": req_id})
        assert s_status == 200
        assert s_body["uncertain"] is False
        assert len(s_body["spans"]) == 2


def test_verified_spans_tool_round_trip(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        admin = gateway.content_admin
        store = admin.store

        req_id = "req-tool-1"
        admin._test_bindings = {
            req_id: {
                "⟦loc_alias⟧": "Seoul",
            }
        }

        store.append(req_id, "opened", {"input": ["Check weather in Seoul"]})
        store.append(req_id, "sent", {"phase": "sent", "fields": ["Check weather in ⟦loc_alias⟧"]})
        store.append(req_id, "tool_args", {"phase": "masked", "fields": ['{"city": "⟦loc_alias⟧"}']})
        store.append(req_id, "tool_args", {"phase": "restored", "fields": ['{"city": "Seoul"}']})
        store.append(req_id, "tool_result", {"phase": "original", "fields": ["Sunny in Seoul"]})
        store.append(req_id, "tool_result", {"phase": "remasked", "fields": ["Sunny in ⟦loc_alias⟧"]})
        store.append(req_id, "finished", {"partial": False, "failed": False, "uncertain": False,
                                          "omitted_bytes": 0, "omitted_events": 0})

        status, body, _ = api(gateway, "get", {"request_id": req_id})
        assert status == 200
        assert body["uncertain"] is False

        assert "tool_args" in body["stages"]
        t_args = body["stages"]["tool_args"]
        assert t_args["uncertain"] is False
        assert len(t_args["spans"]) == 1
        assert t_args["spans"][0]["alias"] == "⟦loc_alias⟧"

        assert "tool_result" in body["stages"]
        t_res = body["stages"]["tool_result"]
        assert t_res["uncertain"] is False
        assert len(t_res["spans"]) == 1
        assert t_res["spans"][0]["alias"] == "⟦loc_alias⟧"


def test_uncertain_for_partial_record(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        admin = gateway.content_admin
        store = admin.store

        req_id = "req-partial-1"
        admin._test_bindings = {req_id: {"⟦cust_alias⟧": "PrivateCustomer"}}

        store.append(req_id, "opened", {"input": ["Hello PrivateCustomer"]})
        store.append(req_id, "sent", {"phase": "sent", "fields": ["Hello ⟦cust_alias⟧"]})
        store.append(req_id, "finished", {"partial": True, "failed": False, "uncertain": False,
                                          "omitted_bytes": 100, "omitted_events": 2})

        status, body, _ = api(gateway, "get", {"request_id": req_id})
        assert status == 200
        assert body["verified_state"] == "부분"
        assert body["uncertain"] is True
        assert body["stages"]["input_sent"]["uncertain"] is True
        assert body["stages"]["input_sent"]["spans"] == []
        assert "대응 관계를 확인할 수 없음" in body["stages"]["input_sent"]["notice"]


def test_uncertain_for_missing_kind(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        admin = gateway.content_admin
        store = admin.store

        req_id = "req-missing-kind-1"
        admin._test_bindings = {req_id: {"⟦cust_alias⟧": "PrivateCustomer"}}

        # Only sent was captured, opened/input missing
        store.append(req_id, "sent", {"phase": "sent", "fields": ["Hello ⟦cust_alias⟧"]})
        store.append(req_id, "finished", {"partial": False, "failed": False, "uncertain": False,
                                          "omitted_bytes": 0, "omitted_events": 0})

        status, body, _ = api(gateway, "get", {"request_id": req_id})
        assert status == 200
        assert body["uncertain"] is True
        assert body["stages"]["input_sent"]["uncertain"] is True
        assert body["stages"]["input_sent"]["spans"] == []
        assert "대응 관계를 확인할 수 없음" in body["stages"]["input_sent"]["notice"]


def test_uncertain_for_redacted_content(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        admin = gateway.content_admin
        store = admin.store

        req_id = "req-redacted-1"
        admin._test_bindings = {req_id: {"⟦cust_alias⟧": "PrivateCustomer"}}

        store.append(req_id, "opened", {"input": ["Hello PrivateCustomer key [credential removed]"]})
        store.append(req_id, "sent", {"phase": "sent", "fields": ["Hello ⟦cust_alias⟧ key [credential removed]"]})
        store.append(req_id, "finished", {"partial": False, "failed": False, "uncertain": False,
                                          "omitted_bytes": 0, "omitted_events": 0})

        status, body, _ = api(gateway, "get", {"request_id": req_id})
        assert status == 200
        assert body["uncertain"] is True
        assert body["stages"]["input_sent"]["uncertain"] is True
        assert body["stages"]["input_sent"]["spans"] == []
        assert "비밀 패턴" in body["stages"]["input_sent"]["notice"]


def test_uncertain_for_no_mapping(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        admin = gateway.content_admin
        store = admin.store

        req_id = "req-no-map-1"
        admin._test_bindings = {req_id: {}}  # No mappings

        store.append(req_id, "opened", {"input": ["Hello PrivateCustomer"]})
        store.append(req_id, "sent", {"phase": "sent", "fields": ["Hello ModifiedCustomer"]})
        store.append(req_id, "finished", {"partial": False, "failed": False, "uncertain": False,
                                          "omitted_bytes": 0, "omitted_events": 0})

        status, body, _ = api(gateway, "get", {"request_id": req_id})
        assert status == 200
        assert body["uncertain"] is True
        assert body["stages"]["input_sent"]["uncertain"] is True
        assert body["stages"]["input_sent"]["spans"] == []


def test_unrestored_alias_detection(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        admin = gateway.content_admin
        store = admin.store

        req_id = "req-unrestored-1"
        admin._test_bindings = {req_id: {"⟦cust_alias⟧": "PrivateCustomer"}}

        store.append(req_id, "opened", {"input": ["Hello PrivateCustomer"]})
        store.append(req_id, "sent", {"phase": "sent", "fields": ["Hello ⟦cust_alias⟧"]})
        # Model echoed alias but gateway or model altered it so displayed still has raw alias or smcp_ID_1
        store.append(req_id, "response", {"phase": "received", "fields": ["Hello ⟦cust_alias⟧ smcp_ID_99"]})
        store.append(req_id, "response", {"phase": "displayed", "fields": ["Hello PrivateCustomer smcp_ID_99"]})
        store.append(req_id, "finished", {"partial": False, "failed": False, "uncertain": False,
                                          "omitted_bytes": 0, "omitted_events": 0})

        status, body, _ = api(gateway, "get", {"request_id": req_id})
        assert status == 200
        resp = body["stages"]["response"]
        assert len(resp["unrestored_aliases"]) >= 1
        assert resp["unrestored_aliases"][0]["alias"] == "smcp_ID_99"
        assert resp["unrestored_aliases"][0]["unrestored"] is True


def test_locked_store_unknown_request_and_auth_origin_failures(tmp_path):
    with gateway_at(tmp_path) as gateway:
        # Auth failure
        assert api(gateway, "get", {"request_id": "any"}, token="wrong")[0] == 401

        # Origin failure
        assert api(gateway, "get", {"request_id": "any"}, origin="http://evil.example.com")[0] == 403

        # Host failure
        assert api(gateway, "get", {"request_id": "any"}, host="evil.example.com")[0] == 403

        # Locked store
        assert api(gateway, "get", {"request_id": "nonexistent"})[0] == 423

        # Unlock
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200

        # Unknown request ID
        assert api(gateway, "get", {"request_id": "nonexistent-id"})[0] == 404


def test_canary_decrypted_content_never_in_logs_errors_or_metadata(tmp_path, caplog, capsys):
    canary = "CANARY_PRIVATE_SECRET_XYZ_987654"
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        admin = gateway.content_admin
        store = admin.store

        req_id = "req-canary-1"
        admin._test_bindings = {req_id: {"⟦canary_alias⟧": canary}}

        store.append(req_id, "opened", {"input": [f"Sensitive {canary}"]})
        store.append(req_id, "sent", {"phase": "sent", "fields": ["Sensitive ⟦canary_alias⟧"]})
        store.append(req_id, "finished", {"partial": False, "failed": False, "uncertain": False,
                                          "omitted_bytes": 0, "omitted_events": 0})

        status, body, _ = api(gateway, "get", {"request_id": req_id})
        assert status == 200
        assert canary in json.dumps(body)

        # 1. Canary must NOT appear in metadata database logs.sqlite3
        if gateway.audit is not None:
            with gateway.audit.connect() as db:
                rows = db.execute("SELECT * FROM requests").fetchall()
                assert canary not in json.dumps(rows)

        # 2. Canary must NOT appear in application logger output
        assert canary not in caplog.text

        # 3. Canary must NOT appear in standard error / standard output
        captured = capsys.readouterr()
        assert canary not in captured.err
        assert canary not in captured.out


def test_real_split_sse_response_verified_spans(tmp_path):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            text = payload["messages"][0]["content"]
            midpoint = len(text) // 2
            events = [
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text[:midpoint]}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text[midpoint:]}},
                {"type": "message_stop"},
            ]
            body = "".join("data: " + json.dumps(ev) + "\n\n" for ev in events).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with ThreadingHTTPServer(("127.0.0.1", 0), Provider) as upstream:
        th = Thread(target=upstream.serve_forever, daemon=True)
        th.start()
        origin = f"http://127.0.0.1:{upstream.server_port}"
        with PrivacyGateway(("127.0.0.1", 0), "local-token", upstreams={"claude": origin},
                            audit_path=tmp_path / "logs.sqlite3", state_dir=tmp_path / "sessions") as gateway:
            gw_thread = Thread(target=gateway.serve_forever, daemon=True)
            gw_thread.start()
            try:
                assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
                settings = api(gateway, "settings")[1]
                settings["enabled"] = True
                settings["providers"]["claude"] = True
                settings["kinds"]["input"] = True
                settings["kinds"]["sent"] = True
                settings["kinds"]["response"] = True
                assert api(gateway, "settings", {"settings": settings, "confirm_sensitive_content": True}, method="PUT")[0] == 200

                headers = {"X-SecureGateway-Token": "local-token", "Authorization": "Bearer sk-ant-oat-test"}
                payload = {"model": "fixture", "stream": True, "messages": [{"role": "user", "content": "PrivateCustomer greetings"}]}
                req = urllib.request.Request(f"http://127.0.0.1:{gateway.server_port}/claude/v1/messages",
                                             data=json.dumps(payload).encode(), headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_data = resp.read()
                    assert b"PrivateCustomer" in resp_data

                gateway.content_admin.writer.drain()

                reqs = api(gateway, "list")[1]["requests"]
                req_id = reqs[0]["request_id"]

                status, body, _ = api(gateway, "get", {"request_id": req_id})
                assert status == 200
                assert body["verified_state"] == "완료"
                assert body["uncertain"] is False

                input_sent = body["stages"]["input_sent"]
                assert input_sent["uncertain"] is False
                assert len(input_sent["spans"]) >= 1

                resp_stage = body["stages"]["response"]
                assert resp_stage["uncertain"] is False
                assert len(resp_stage["spans"]) >= 1
            finally:
                gateway.shutdown()
                gw_thread.join(5)
                upstream.shutdown()
                th.join(5)


def test_cross_conversation_snapshots_do_not_contaminate_spans(tmp_path):
    from secure_gateway.encrypted_session import save_session
    from secure_gateway.models import MaskMode, SurrogateStrategy, TokenMapping, TokenType
    from secure_gateway.session import PrivacySession

    # Write two session snapshots to disk that use the EXACT SAME alias for different originals
    sess_dir = tmp_path / "sessions"
    sess_dir.mkdir(parents=True, exist_ok=True)

    sess_a = PrivacySession("conv-a", MaskMode.ENTITIES_ONLY, SurrogateStrategy.UNICODE)
    mapping_a = TokenMapping(surrogate="⟦shared_alias⟧", original="AliceSecret", token_type=TokenType.ENTITY)
    sess_a.reverse_store["⟦shared_alias⟧"] = mapping_a
    sess_a.forward_store["AliceSecret"] = mapping_a
    save_session(sess_dir / "conv-a.enc", sess_a, "local-token")

    sess_b = PrivacySession("conv-b", MaskMode.ENTITIES_ONLY, SurrogateStrategy.UNICODE)
    mapping_b = TokenMapping(surrogate="⟦shared_alias⟧", original="BobSecret", token_type=TokenType.ENTITY)
    sess_b.reverse_store["⟦shared_alias⟧"] = mapping_b
    sess_b.forward_store["BobSecret"] = mapping_b
    save_session(sess_dir / "conv-b.enc", sess_b, "local-token")

    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        store = gateway.content_admin.store

        # Request A records Alice's conversation
        req_a = "req-conv-a"
        store.append(req_a, "opened", {"input": ["Hello AliceSecret from team A"]})
        store.append(req_a, "sent", {"phase": "sent", "fields": ["Hello ⟦shared_alias⟧ from team A"]})
        store.append(req_a, "finished", {"partial": False, "failed": False, "uncertain": False,
                                         "omitted_bytes": 0, "omitted_events": 0})

        # Request B records Bob's conversation
        req_b = "req-conv-b"
        store.append(req_b, "opened", {"input": ["Greetings BobSecret from team B"]})
        store.append(req_b, "sent", {"phase": "sent", "fields": ["Greetings ⟦shared_alias⟧ from team B"]})
        store.append(req_b, "finished", {"partial": False, "failed": False, "uncertain": False,
                                         "omitted_bytes": 0, "omitted_events": 0})

        # Audit view for Request A must derive AliceSecret only
        st_a, body_a, _ = api(gateway, "get", {"request_id": req_a})
        assert st_a == 200
        assert body_a["uncertain"] is False
        spans_a = body_a["stages"]["input_sent"]["spans"]
        assert len(spans_a) == 1
        assert spans_a[0]["alias"] == "⟦shared_alias⟧"
        orig_text_a = body_a["stages"]["input_sent"]["original"][spans_a[0]["original_start"]:spans_a[0]["original_end"]]
        assert orig_text_a == "AliceSecret"
        assert "BobSecret" not in json.dumps(body_a)

        # Audit view for Request B must derive BobSecret only
        st_b, body_b, _ = api(gateway, "get", {"request_id": req_b})
        assert st_b == 200
        assert body_b["uncertain"] is False
        spans_b = body_b["stages"]["input_sent"]["spans"]
        assert len(spans_b) == 1
        assert spans_b[0]["alias"] == "⟦shared_alias⟧"
        orig_text_b = body_b["stages"]["input_sent"]["original"][spans_b[0]["original_start"]:spans_b[0]["original_end"]]
        assert orig_text_b == "BobSecret"
        assert "AliceSecret" not in json.dumps(body_b)


def test_ambiguous_alignment_returns_uncertain(tmp_path):
    with gateway_at(tmp_path) as gateway:
        assert api(gateway, "unlock", {"passphrase": "synthetic-passphrase", "initialize": True})[0] == 200
        store = gateway.content_admin.store

        # 1. Multiple splits with repeating anchor segments
        req_id = "req-ambiguous-anchors"
        store.append(req_id, "opened", {"input": ["foo ABC bar DEF bar GHI baz"]})
        store.append(req_id, "sent", {"phase": "sent", "fields": ["foo ⟦X⟧ bar ⟦Y⟧ baz"]})
        store.append(req_id, "finished", {"partial": False, "failed": False, "uncertain": False,
                                          "omitted_bytes": 0, "omitted_events": 0})

        status, body, _ = api(gateway, "get", {"request_id": req_id})
        assert status == 200
        assert body["uncertain"] is True
        assert body["stages"]["input_sent"]["uncertain"] is True
        assert body["stages"]["input_sent"]["spans"] == []

        # 2. Adjacent aliases with ambiguous split
        req_id2 = "req-ambiguous-adjacent"
        store.append(req_id2, "opened", {"input": ["HelloWorld"]})
        store.append(req_id2, "sent", {"phase": "sent", "fields": ["⟦X⟧⟦Y⟧"]})
        store.append(req_id2, "finished", {"partial": False, "failed": False, "uncertain": False,
                                           "omitted_bytes": 0, "omitted_events": 0})

        status2, body2, _ = api(gateway, "get", {"request_id": req_id2})
        assert status2 == 200
        assert body2["uncertain"] is True
        assert body2["stages"]["input_sent"]["uncertain"] is True
        assert body2["stages"]["input_sent"]["spans"] == []
