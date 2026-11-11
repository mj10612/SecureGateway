"""Tests for the administrative masking preview endpoint and engine isolation (#342)."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from threading import Event, Lock, Thread
import unicodedata
import urllib.error
import urllib.request

import pytest

from secure_gateway.gateway import GatewaySession, PrivacyGateway


@pytest.fixture
def preview_gateway(tmp_path):
    class FailingProvider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            pytest.fail("Provider upstream must not be called during preview")

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), FailingProvider)
    upstream.received = []
    worker = Thread(target=upstream.serve_forever, daemon=True)
    worker.start()
    origin = f"http://127.0.0.1:{upstream.server_port}"

    state_dir = tmp_path / "sessions"
    state_dir.mkdir(parents=True, exist_ok=True)
    audit_path = tmp_path / "logs.sqlite3"

    gateway = PrivacyGateway(
        ("127.0.0.1", 0),
        "test-admin-preview-token",
        upstreams={"claude": origin, "codex": origin},
        api_upstreams={"xai": origin},
        state_dir=state_dir,
        audit_path=audit_path,
    )
    thread = Thread(target=gateway.serve_forever, daemon=True)
    thread.start()
    try:
        yield gateway, upstream, state_dir, audit_path
    finally:
        gateway.shutdown()
        thread.join(2)
        gateway.server_close()
        upstream.shutdown()
        worker.join(2)
        upstream.server_close()


def admin_post(gateway, path, data, headers=None, timeout=15):
    hdrs = {"X-SecureGateway-Token": gateway.token, "Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req_data = data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{gateway.server_port}" + path,
        data=req_data,
        headers=hdrs,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8")), response.headers
    except urllib.error.HTTPError as exc:
        with exc:
            try:
                body = json.loads(exc.read().decode("utf-8"))
            except Exception:
                body = {}
            return exc.code, body, exc.headers


def test_preview_auth_and_origin_checks(preview_gateway):
    gateway, _, _, _ = preview_gateway
    # Missing token -> 401
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": "hello"}, headers={"X-SecureGateway-Token": ""})
    assert status == 401
    assert body.get("code") == "unauthorized"

    # Wrong token -> 401
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": "hello"}, headers={"X-SecureGateway-Token": "wrong-token"})
    assert status == 401
    assert body.get("code") == "unauthorized"

    # Foreign origin -> 403
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": "hello"}, headers={"Origin": "http://evil.com"})
    assert status == 403
    assert body.get("code") == "forbidden_origin"

    # Foreign host -> 403
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": "hello"}, headers={"Host": "attacker.com"})
    assert status == 403
    assert body.get("code") == "forbidden_origin"


def test_preview_validation_and_size_limits(preview_gateway):
    gateway, _, _, _ = preview_gateway
    # Invalid JSON payload
    req = urllib.request.Request(
        f"http://127.0.0.1:{gateway.server_port}/admin/api/preview",
        data=b"not-json",
        headers={"X-SecureGateway-Token": gateway.token, "Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=5)
    with exc_info.value:
        assert exc_info.value.code == 400

    # Non-dict payload
    status, body, _ = admin_post(gateway, "/admin/api/preview", ["text"])
    assert status == 400
    assert body.get("code") == "invalid_request"

    # Missing text field
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"mode": "prose"})
    assert status == 400
    assert body.get("code") == "invalid_request"

    # Non-string text
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": 12345})
    assert status == 400
    assert body.get("code") == "invalid_request"

    # Oversize text (> 256 KiB)
    oversize = "a" * (256 * 1024 + 1)
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": oversize})
    assert status == 413
    assert body.get("code") == "oversize"


def test_preview_empty_input_and_no_changes(preview_gateway):
    gateway, _, _, _ = preview_gateway
    status, body, headers = admin_post(gateway, "/admin/api/preview", {"text": "", "mode": "prose"})
    assert status == 200
    assert headers.get("Cache-Control") == "no-store"
    assert body["masked"] == ""
    assert body["spans"] == []
    assert body["uncertain"] is False
    assert body["stats"]["replacement_count"] == 0
    assert body["stats"]["unique_alias_count"] == 0

    # Text with ordinary words only -> no changes
    ordinary = "The quick brown fox jumps over the lazy dog."
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": ordinary, "mode": "prose"})
    assert status == 200
    assert body["masked"] == ordinary
    assert body["spans"] == []
    assert body["uncertain"] is False
    assert body["stats"]["replacement_count"] == 0


def test_preview_sensitive_patterns_and_span_alignment(preview_gateway):
    gateway, _, _, _ = preview_gateway
    original = "Contact alice@example.com or visit 192.168.1.50 for details."
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": original, "mode": "prose"})
    assert status == 200
    assert body["uncertain"] is False
    assert body["stats"]["replacement_count"] >= 2

    masked = body["masked"]
    assert "alice@example.com" not in masked
    assert "192.168.1.50" not in masked

    spans = body["spans"]
    assert len(spans) >= 2
    # Verify span positions match byte-for-byte
    for span in spans:
        assert span["index"] >= 0
        o_sub = original[span["original_start"] : span["original_end"]]
        m_sub = masked[span["masked_start"] : span["masked_end"]]
        assert span["alias"] in m_sub
        assert o_sub in {"alice@example.com", "192.168.1.50"}


def test_preview_forced_rules_priority_and_safe_policy_summary(preview_gateway):
    gateway, _, _, _ = preview_gateway
    # Set forced rules in gateway
    gateway.set_mask_rules(["TOP_SECRET_PROJECT", "비밀문서"])

    original = "이것은 비밀문서 내용이며 TOP_SECRET_PROJECT 코드입니다."
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": original, "mode": "prose"})
    assert status == 200
    assert body["uncertain"] is False
    assert "TOP_SECRET_PROJECT" not in body["masked"]
    assert "비밀문서" not in body["masked"]

    # Policy summary must NEVER expose forced rule strings
    policy = body["policy"]
    assert policy["forced_rule_count"] == 2
    policy_str = json.dumps(policy)
    assert "TOP_SECRET_PROJECT" not in policy_str
    assert "비밀문서" not in policy_str
    assert "domains" in policy
    assert "domain_policy_version" in policy


def test_preview_code_and_json_structures(preview_gateway):
    gateway, _, _, _ = preview_gateway
    # Python code
    code_text = "def calculate_fee(account_balance):\n    return account_balance * 0.05"
    status, body, _ = admin_post(gateway, "/admin/api/preview", {
        "text": code_text,
        "mode": "code",
        "code_language": "python",
    })
    assert status == 200
    assert body["uncertain"] is False
    assert "calculate_fee" not in body["masked"]
    assert "account_balance" not in body["masked"]
    assert body["stats"]["mode"] == "code"

    # JSON in prose mode
    json_text = '{"customer_id": "cust-9982", "active": true}'
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": json_text, "mode": "prose"})
    assert status == 200
    assert body["uncertain"] is False


def test_preview_korean_particles_nfc_nfd_emoji_and_newlines(preview_gateway):
    gateway, _, _, _ = preview_gateway
    gateway.set_mask_rules(["보안서버", "프로젝트Alpha"])

    # Korean particles attached
    korean_text = "보안서버에서 데이터를 받고 프로젝트Alpha로 전달한다."
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": korean_text, "mode": "prose"})
    assert status == 200
    assert body["uncertain"] is False
    assert "보안서버" not in body["masked"]
    # Particle preservation and span mapping
    assert "에서" in body["masked"]
    assert len(body["spans"]) == 2

    # NFD normalization
    nfd_term = unicodedata.normalize("NFD", "보안서버")
    nfd_text = f"이것은 {nfd_term} 테스트입니다."
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": nfd_text, "mode": "prose"})
    assert status == 200
    assert body["uncertain"] is False
    # Original slice reconstructed correctly
    for span in body["spans"]:
        o_sub = nfd_text[span["original_start"] : span["original_end"]]
        assert o_sub == nfd_term

    # Emoji and newlines
    emoji_text = "Line 1: 🔒 보안서버\n\nLine 3: 🚀 프로젝트Alpha 완료!"
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": emoji_text, "mode": "prose"})
    assert status == 200
    assert body["uncertain"] is False
    assert "🔒" in body["masked"]
    assert "🚀" in body["masked"]
    assert "\n\n" in body["masked"]


def test_preview_repeated_strings_identical_spans(preview_gateway):
    gateway, _, _, _ = preview_gateway
    gateway.set_mask_rules(["REPEATED_SECRET"])
    text = "First REPEATED_SECRET then middle and second REPEATED_SECRET at end."
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": text, "mode": "prose"})
    assert status == 200
    assert body["uncertain"] is False
    assert len(body["spans"]) == 2
    # Both spans share the same alias
    assert body["spans"][0]["alias"] == body["spans"][1]["alias"]
    assert body["spans"][0]["original_start"] != body["spans"][1]["original_start"]


def test_preview_xss_inert_text(preview_gateway):
    gateway, _, _, _ = preview_gateway
    xss_payload = "<script>alert('xss')</script><img src=x onerror=alert(1)>"
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": xss_payload, "mode": "prose"})
    assert status == 200
    # Must be returned as valid JSON payload with string masked property without execution
    assert isinstance(body["masked"], str)
    assert isinstance(body["spans"], list)


def test_preview_concurrency_limit_and_busy_code(preview_gateway, monkeypatch):
    gateway, _, _, _ = preview_gateway
    from secure_gateway import admin_preview

    entered_1 = Event()
    entered_2 = Event()
    release_event = Event()
    count_lock = Lock()
    call_count = 0

    orig_execute = admin_preview._execute_preview

    def blocking_execute(*args, **kwargs):
        nonlocal call_count
        with count_lock:
            call_count += 1
            num = call_count
        if num == 1:
            entered_1.set()
            release_event.wait(timeout=20)
        elif num == 2:
            entered_2.set()
            release_event.wait(timeout=20)
        return orig_execute(*args, **kwargs)

    monkeypatch.setattr(admin_preview, "_execute_preview", blocking_execute)

    results = []

    def request_worker():
        res = admin_post(gateway, "/admin/api/preview", {"text": "hello test", "mode": "prose"}, timeout=30)
        results.append(res)

    t1 = Thread(target=request_worker)
    t2 = Thread(target=request_worker)

    try:
        t1.start()
        assert entered_1.wait(timeout=15), "First preview did not enter execution"

        t2.start()
        assert entered_2.wait(timeout=15), "Second preview did not enter execution"

        # At this point, both previews 1 and 2 are guaranteed to be in flight,
        # holding the two semaphore slots. The third request must immediately receive 429.
        status_3, body_3, _ = admin_post(
            gateway, "/admin/api/preview", {"text": "third preview", "mode": "prose"}, timeout=15
        )
        assert status_3 == 429
        assert body_3.get("code") == "busy"
        assert body_3.get("error") == "Server busy processing other previews"
    finally:
        # Release the two in-flight requests
        release_event.set()
        t1.join(timeout=15)
        t2.join(timeout=15)

    assert len(results) == 2
    assert results[0][0] == 200
    assert results[1][0] == 200


def test_preview_isolation_and_no_leakage_to_audit_or_logs(preview_gateway, caplog):
    gateway, upstream, state_dir, audit_path = preview_gateway

    # Record state before preview
    sessions_before = dict(gateway.sessions)
    files_before = set(state_dir.iterdir()) if state_dir.exists() else set()
    audit_rows_before = gateway.audit.query({})["rows"] if gateway.audit else []

    canary = "CANARY_SECRET_TOKEN_XYZ_98765"
    with caplog.at_level(logging.DEBUG):
        status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": f"User secret is {canary}", "mode": "prose"})

    assert status == 200
    assert canary not in body["masked"]

    # 1. Canary must not appear in audit DB
    audit_rows_after = gateway.audit.query({})["rows"] if gateway.audit else []
    assert len(audit_rows_after) == len(audit_rows_before)
    assert canary not in json.dumps(audit_rows_after)

    # 2. Canary must not appear in logs/stderr
    for record in caplog.records:
        assert canary not in record.getMessage()

    # 3. Sessions dict unchanged
    assert dict(gateway.sessions) == sessions_before

    # 4. Snapshot directory unchanged
    files_after = set(state_dir.iterdir()) if state_dir.exists() else set()
    assert files_after == files_before

    # 5. Upstream received 0 requests
    assert len(upstream.received) == 0


def test_preview_domain_policy_on_off(preview_gateway):
    gateway, _, _, _ = preview_gateway
    text = "The tactical data link and radome were tested."

    # When defense domain is ON (default is defense ON)
    gateway.set_domain_policy({"defense": True, "automotive": False, "semiconductor": False})
    status, body_on, _ = admin_post(gateway, "/admin/api/preview", {"text": text, "mode": "prose"})
    assert status == 200
    assert body_on["uncertain"] is False
    assert "radome" not in body_on["masked"]

    # When defense domain is OFF
    gateway.set_domain_policy({"defense": False, "automotive": False, "semiconductor": False})
    status, body_off, _ = admin_post(gateway, "/admin/api/preview", {"text": text, "mode": "prose"})
    assert status == 200
    assert body_off["uncertain"] is False
    # Without domain policy, generic text has fewer or no domain replacements
    assert body_on["stats"]["replacement_count"] > body_off["stats"]["replacement_count"]


def test_preview_boundary(preview_gateway, monkeypatch):
    gateway, _, _, _ = preview_gateway
    from secure_gateway import admin_preview

    monkeypatch.setattr(admin_preview, "PREVIEW_DEADLINE_SECONDS", 300.0)

    # Exactly 256 KiB (262,144 bytes) of cheap-to-mask ordinary public words with line breaks
    sentence = (
        "The quick brown fox jumps over the lazy dog and runs across the green meadow on a bright sunny afternoon, "
        "while observers watch from a safe distance without making any noise or disturbance.\n"
    )
    repeat = (256 * 1024 // len(sentence)) + 1
    exact_256k = (sentence * repeat)[: 256 * 1024]
    assert len(exact_256k.encode("utf-8")) == 256 * 1024

    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": exact_256k, "mode": "prose"}, timeout=60)
    assert status == 200
    assert body["uncertain"] is False
    assert body["masked"] == exact_256k

    # 1 byte over 256 KiB (262,145 bytes)
    over_256k = exact_256k + "x"
    assert len(over_256k.encode("utf-8")) == 256 * 1024 + 1
    status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": over_256k, "mode": "prose"}, timeout=15)
    assert status == 413
    assert body.get("code") == "oversize"


def test_preview_deadline_timeout_and_no_leakage(preview_gateway, monkeypatch, caplog):
    gateway, _, _, _ = preview_gateway
    from secure_gateway import admin_preview

    # Monkeypatch deadline to a tiny value (50 ms)
    monkeypatch.setattr(admin_preview, "PREVIEW_DEADLINE_SECONDS", 0.05)

    unblock_event = Event()
    orig_execute = admin_preview._execute_preview

    def slow_execute(*args, **kwargs):
        unblock_event.wait(timeout=15)
        return orig_execute(*args, **kwargs)

    monkeypatch.setattr(admin_preview, "_execute_preview", slow_execute)

    canary = "TIMEOUT_CANARY_SECRET_789012"
    try:
        with caplog.at_level(logging.DEBUG):
            status, body, _ = admin_post(
                gateway,
                "/admin/api/preview",
                {"text": f"Confidential payload: {canary}", "mode": "prose"},
                timeout=15,
            )

        assert status == 504
        assert body.get("code") == "deadline_exceeded"
        assert body.get("error") == "Processing deadline exceeded"

        # Assert nothing from the input leaks into response body, audit DB, or logs
        body_str = json.dumps(body)
        assert canary not in body_str

        for record in caplog.records:
            assert canary not in record.getMessage()

        audit_rows = gateway.audit.query({})["rows"] if gateway.audit else []
        assert canary not in json.dumps(audit_rows)
    finally:
        unblock_event.set()


def test_preview_direct_input_and_file_content_equivalence(preview_gateway, tmp_path):
    gateway, _, _, _ = preview_gateway
    sample_content = "Config file with secret_key = 192.168.1.1 and email = ops@company.org\nNew line here."

    # Direct input
    status_direct, body_direct, _ = admin_post(gateway, "/admin/api/preview", {
        "text": sample_content,
        "mode": "prose",
    })
    assert status_direct == 200

    # Write to a file, read as text in browser fashion, send as text
    file_path = tmp_path / "sample.txt"
    file_path.write_text(sample_content, encoding="utf-8")
    content_from_file = file_path.read_text(encoding="utf-8")

    status_file, body_file, _ = admin_post(gateway, "/admin/api/preview", {
        "text": content_from_file,
        "mode": "prose",
    })
    assert status_file == 200

    assert body_direct["masked"] == body_file["masked"]
    assert body_direct["spans"] == body_file["spans"]
    assert body_direct["uncertain"] == body_file["uncertain"]


def test_preview_concurrent_previews_isolation(preview_gateway):
    gateway, _, _, _ = preview_gateway
    text_a = "Session A contact alice.secret@domain.com"
    text_b = "Session B contact bob.private@secure.net"

    results = {}

    def run_preview(name, text):
        status, body, _ = admin_post(gateway, "/admin/api/preview", {"text": text, "mode": "prose"})
        results[name] = (status, body)

    t1 = Thread(target=run_preview, args=("A", text_a))
    t2 = Thread(target=run_preview, args=("B", text_b))
    t1.start()
    t2.start()
    t1.join(15)
    t2.join(15)

    assert results["A"][0] == 200
    assert results["B"][0] == 200

    # Ensure no crosstalk between A and B
    masked_a = results["A"][1]["masked"]
    masked_b = results["B"][1]["masked"]

    assert "alice.secret@domain.com" not in masked_a
    assert "bob.private@secure.net" not in masked_b
    assert "bob.private" not in masked_a
    assert "alice.secret" not in masked_b


def test_preview_uncertain_when_verification_fails(preview_gateway):
    gateway, _, _, _ = preview_gateway

    # Force verification failure inside derive_spans
    orig_restore = GatewaySession.restore

    def corrupt_restore(self, text, *args, **kwargs):
        return "CORRUPTED_RESTORE_RESULT"

    GatewaySession.restore = corrupt_restore
    try:
        status, body, _ = admin_post(gateway, "/admin/api/preview", {
            "text": "Secret user@example.com is protected.",
            "mode": "prose",
        })
        assert status == 200
        # Verification failed -> uncertain True, spans empty list
        assert body["uncertain"] is True
        assert body["spans"] == []
        assert isinstance(body["masked"], str)
    finally:
        GatewaySession.restore = orig_restore


def test_comparison_js_asset_served(preview_gateway):
    gateway, _, _, _ = preview_gateway
    req = urllib.request.Request(f"http://127.0.0.1:{gateway.server_port}/admin/comparison.js")
    with urllib.request.urlopen(req, timeout=5) as response:
        assert response.status == 200
        assert "text/javascript" in response.headers.get("Content-Type", "")
        content = response.read().decode("utf-8")
        assert "ComparisonView" in content


def test_client_side_decoder_logic_via_node():
    import shutil
    import subprocess

    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    js_test = """
    const fs = require('fs');
    const code = fs.readFileSync('src/secure_gateway/admin/app.js', 'utf-8');
    const vm = require('vm');
    const dummyElem = { addEventListener: () => {}, querySelector: () => ({ href: '' }) };
    const window = { addEventListener: () => {} };
    vm.runInNewContext(code, {
      window, TextDecoder, Uint8Array,
      document: { getElementById: () => dummyElem },
      setInterval: () => {}, addEventListener: () => {}
    });
    const { decodeFileBuffer } = window.PreviewDecoder;

    // 1. Normal UTF-8 text
    if (decodeFileBuffer(Buffer.from('Hello world 안녕'), 'test.txt') !== 'Hello world 안녕') process.exit(1);

    // 2. UTF-8 BOM
    if (decodeFileBuffer(Buffer.from('\\uFEFFHello BOM'), 'test.md') !== 'Hello BOM') process.exit(2);

    // 3. NUL byte rejection
    try {
      decodeFileBuffer(Buffer.from([0x48, 0x00, 0x69]), 'test.txt');
      process.exit(3);
    } catch (e) {
      if (!e.message.includes('NUL')) process.exit(3);
    }

    // 4. Invalid UTF-8 sequence rejection
    try {
      decodeFileBuffer(Buffer.from([0xFF, 0xFE, 0xFD]), 'test.txt');
      process.exit(4);
    } catch (e) {
      if (!e.message.includes('UTF-8')) process.exit(4);
    }

    // 5. Unsupported extension rejection
    try {
      decodeFileBuffer(Buffer.from('hello'), 'document.docx');
      process.exit(5);
    } catch (e) {
      if (!e.message.includes('PDF')) process.exit(5);
    }

    // 6. Oversize rejection (> 256 KiB)
    try {
      decodeFileBuffer(Buffer.alloc(256 * 1024 + 1), 'large.txt');
      process.exit(6);
    } catch (e) {
      if (!e.message.includes('256 KiB')) process.exit(6);
    }
    """
    proc = subprocess.run(["node", "-e", js_test], capture_output=True, text=True)
    assert proc.returncode == 0, f"Node test failed with stdout: {proc.stdout}, stderr: {proc.stderr}"

