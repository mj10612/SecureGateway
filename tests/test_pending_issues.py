"""Regression proof for the outstanding GitHub issues (#91–#103)."""

from contextlib import contextmanager
import http.client
import json
from pathlib import Path
import socket
import sys
from threading import Event, Thread
import urllib.error
import urllib.request

from click.testing import CliRunner
import pytest

from secure_gateway import __version__, gateway_install
from secure_gateway.antigravity_install import configure_antigravity
from secure_gateway.antigravity_sdk import antigravity_endpoint
from secure_gateway.cli import main
from secure_gateway.engine.grammar_ko import normalize_particle
from secure_gateway.gateway import GatewayHandler, GatewaySession, PrivacyGateway
from secure_gateway.models import TokenMapping, TokenType

CLIENT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


@contextmanager
def gateway_server():
    server = PrivacyGateway(("127.0.0.1", 0), "t" * 32)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


def send_request(server, payload):
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_port}/claude/v1/messages",
        json.dumps(payload).encode(),
        {
            "X-SecureGateway-Token": "t" * 32,
            "Authorization": "Bearer sk-ant-oat-fixture",
            "Content-Type": "application/json",
        },
    )
    return CLIENT.open(request, timeout=3)


@pytest.mark.parametrize("location", ["message", "system", "tool"])
@pytest.mark.parametrize(
    "control",
    [
        "secret",
        {"type": "ephemeral", "private_note": "secret"},
        {"type": "ephemeral", "ttl": "secret"},
        {"type": "ephemeral", "ttl": {}},
    ],
)
def test_cache_controls_rejected_before_forwarding(monkeypatch, location, control):
    block = {"type": "text", "text": "hello", "cache_control": control}
    payload = {"messages": [{"role": "user", "content": "hello"}]}
    if location == "message":
        payload["messages"][0]["content"] = [block]
    elif location == "system":
        payload["system"] = [block]
    else:
        payload["tools"] = [
            {
                "name": "Read",
                "input_schema": {"type": "object"},
                "cache_control": control,
            }
        ]
    calls = []
    with gateway_server() as server:
        # urlopen for the local client does not use this provider-opener factory.
        monkeypatch.setattr(
            urllib.request, "build_opener", lambda *args: calls.append(args)
        )
        with pytest.raises(urllib.error.HTTPError) as error:
            send_request(server, payload)
        assert error.value.code == 400
        error.value.close()
    assert calls == []


@pytest.mark.parametrize("dialect", ["claude", "responses", "chat_completions"])
def test_tool_output_protocol_named_private_fields_are_masked(dialect):
    secrets = {
        "id": "patient-4471",
        "status": "/srv/private",
        "model": "internal-model",
        "role": "dr-hannah",
        "object": "billing-invoice",
        "effort": "quarterly-budget",
    }
    block = {"type": "text", "text": "ok", **secrets}
    block["extra"] = {
        "type": "tool_use",
        "id": "private-disguised-id",
        "input": {"role": "private-user"},
    }
    if dialect == "claude":
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "t1", "content": [block]}
                    ],
                }
            ]
        }
    elif dialect == "responses":
        payload = {
            "input": [
                {"type": "function_call_output", "call_id": "t1", "output": [block]}
            ]
        }
    else:
        payload = {
            "messages": [
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "content": "ok",
                    **{k: v for k, v in secrets.items() if k != "role"},
                }
            ]
        }
    session = GatewaySession()
    masked = session.request(payload, dialect=dialect)
    for key, secret in secrets.items():
        if dialect != "chat_completions" or key != "role":
            assert secret not in json.dumps(masked)
    if dialect != "chat_completions":
        assert "private-disguised-id" not in json.dumps(masked)
        assert "private-user" not in json.dumps(masked)
    field = "input" if dialect == "responses" else "messages"
    # The added privacy system message belongs to the outgoing request only.
    history = masked[field][1:] if dialect == "chat_completions" else masked[field]
    assert session.walk(history, restore=True) == payload[field]


@pytest.mark.parametrize(
    "ending",
    ["이라도", "이라서", "이지만", "이다", "이야", "이란", "이고", "이며", "이니"],
)
def test_copular_endings_are_not_subject_markers(ending):
    assert normalize_particle("사과", ending) == ending
    assert normalize_particle("사람", ending) == ending


@pytest.mark.parametrize(
    "format_value",
    [
        {"type": "text"},
        {"type": "json_object"},
        {
            "type": "json_schema",
            "json_schema": {
                "name": "privateReport",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"privateField": {"type": "string"}},
                    "required": ["privateField"],
                    "additionalProperties": False,
                },
            },
        },
    ],
)
def test_chat_reasoning_and_structured_output_controls(format_value):
    session = GatewaySession()
    masked = session.request(
        {
            "messages": [{"role": "user", "content": "hello"}],
            "reasoning_effort": "high",
            "response_format": format_value,
        },
        dialect="chat_completions",
    )
    assert masked["reasoning_effort"] == "high"
    assert session.walk(masked["response_format"], restore=True) == format_value
    assert "privateReport" not in json.dumps(masked)
    assert "privateField" not in json.dumps(masked)


@pytest.mark.parametrize(
    "options",
    [
        {"reasoning_effort": "secret"},
        {"reasoning_effort": {}},
        {"response_format": {"type": "json_object", "private": "secret"}},
        {"response_format": {"type": {}}},
        {
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "r", "schema": {}, "strict": "secret"},
            }
        },
    ],
)
def test_chat_controls_refuse_private_or_malformed_values(options):
    with pytest.raises(ValueError):
        GatewaySession().request(
            {"messages": [], **options}, dialect="chat_completions"
        )


@pytest.mark.parametrize(
    "failure,expected",
    [
        (ConnectionRefusedError("private endpoint"), 502),
        (urllib.error.URLError(TimeoutError("private endpoint")), 504),
        (http.client.IncompleteRead(b"private text", 20), 502),
    ],
)
@pytest.mark.parametrize("during_read", [False, True])
def test_transport_failure_statuses_do_not_disclose_exceptions(
    monkeypatch, failure, expected, during_read
):
    class Upstream:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self, *_):
            raise failure

    class Opener:
        def open(self, *_args, **_kwargs):
            if during_read:
                return Upstream()
            raise failure

    with gateway_server() as server:
        monkeypatch.setattr(urllib.request, "build_opener", lambda *args: Opener())
        with pytest.raises(urllib.error.HTTPError) as error:
            send_request(server, {"messages": [{"role": "user", "content": "hello"}]})
        assert error.value.code == expected
        assert b"private" not in error.value.read()
        error.value.close()


@pytest.mark.parametrize("partial_headers", [False, True])
def test_incomplete_client_request_releases_handler(monkeypatch, partial_headers):
    finished = Event()
    original_finish = GatewayHandler.finish

    def finish(handler):
        try:
            original_finish(handler)
        finally:
            finished.set()

    monkeypatch.setattr(GatewayHandler, "timeout", 0.15)
    monkeypatch.setattr(GatewayHandler, "finish", finish)
    with (
        gateway_server() as server,
        socket.create_connection(server.server_address, timeout=2) as client,
    ):
        headers = (
            b"POST /claude/v1/messages HTTP/1.0\r\nX-SecureGateway-Token: "
            + b"t" * 32
            + b"\r\nAuthorization: Bearer sk-ant-oat-fixture\r\nContent-Length: 100\r\n"
        )
        client.sendall(headers if partial_headers else headers + b"\r\na")
        assert finished.wait(2), "handler did not release an incomplete request"


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("failure_stage", ["config", "manifest", "host"])
def test_install_failure_restores_config_and_every_host(
    tmp_path, monkeypatch, existing, failure_stage
):
    config = tmp_path / "config.json"
    manifest = tmp_path / "installation.json"
    if existing:
        config.write_bytes(b'{"old_config":true}\n')
        manifest.write_bytes(b'{"files":{}}\n')
    originals = {p: p.read_bytes() if p.exists() else None for p in [config, manifest]}
    hosts = [tmp_path / "host1.json", tmp_path / "host2.json"]
    for host in hosts:
        host.write_bytes(b"personal setting")
    atomic_json, atomic_bytes = (
        gateway_install._atomic_json,
        gateway_install.atomic_bytes,
    )

    def write_json(path, data):
        if (failure_stage == "config" and path == config) or (
            failure_stage == "manifest" and path == manifest
        ):
            raise OSError("injected metadata failure")
        atomic_json(path, data)

    def write_bytes(path, data):
        if failure_stage == "host" and path == hosts[1] and data == b"installed":
            raise OSError("injected host failure")
        atomic_bytes(path, data)

    monkeypatch.setattr(gateway_install, "_atomic_json", write_json)
    monkeypatch.setattr(gateway_install, "atomic_bytes", write_bytes)
    with pytest.raises(OSError):
        gateway_install.apply_settings(
            config, {"port": 12345, "token": "t" * 32}, {p: b"installed" for p in hosts}
        )
    for path, original in originals.items():
        assert (path.read_bytes() if path.exists() else None) == original
    assert all(host.read_bytes() == b"personal setting" for host in hosts)


def test_rate_limit_headers_preserved_without_unrelated_headers():
    handler = object.__new__(GatewayHandler)
    headers = {
        "anthropic-ratelimit-requests-remaining": "20",
        "x-ratelimit-reset-requests": "1s",
        "retry-after": "1",
        "Set-Cookie": "secret",
        "x-private": "secret",
    }
    handler.capture_response_headers(headers)
    assert handler.response_headers == {
        k: v for k, v in headers.items() if "secret" != v
    }


def test_sdk_query_forwarding_and_private_query_refusal(monkeypatch):
    requests = []

    class Response:
        status = 200
        headers = http.client.HTTPMessage()
        headers["Content-Type"] = "application/json"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self, *_):
            return b"{}"

    class Opener:
        def open(self, request, **_kwargs):
            requests.append(request)
            return Response()

    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: Opener())
    with antigravity_endpoint(
        "http://127.0.0.1:12345", "t" * 32, "xai-fixture"
    ) as base_url:
        for query, status in [
            ("api-version=2024-02-01", 200),
            ("stream=true", 200),
            ("stream=private", 400),
            ("secret=patient", 400),
        ]:
            request = urllib.request.Request(
                base_url + "/chat/completions?" + query,
                b"{}",
                {"Content-Type": "application/json"},
            )
            if status == 200:
                with CLIENT.open(request, timeout=3) as response:
                    assert response.status == 200
            else:
                with pytest.raises(urllib.error.HTTPError) as error:
                    CLIENT.open(request, timeout=3)
                assert error.value.code == status
                error.value.close()
    assert len(requests) == 2
    assert (
        requests[0].full_url
        == "http://127.0.0.1:12345/xai/v1/chat/completions?api-version=2024-02-01"
    )
    assert requests[1].full_url.endswith("?stream=true")


def test_antigravity_registration_uses_interpreter_and_preserves_user_changes(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    path = tmp_path / ".gemini" / "config" / "mcp_config.json"
    path.parent.mkdir(parents=True)
    original = {
        "mcpServers": {
            "other": {"command": "other"},
            "secure-gateway": {"command": "previous"},
        },
        "personal": True,
    }
    path.write_text(json.dumps(original))
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--agent", "antigravity"]).exit_code == 0
    assert runner.invoke(main, ["init", "--agent", "agy"]).exit_code == 0
    settings = json.loads(path.read_text())
    assert settings["mcpServers"]["secure-gateway"] == {
        "command": sys.executable,
        "args": ["-m", "secure_gateway", "serve"],
    }
    assert settings["mcpServers"]["other"] == original["mcpServers"]["other"]
    assert (
        json.loads(path.with_name(path.name + ".secure-gateway.bak").read_text())
        == original
    )
    settings["mcpServers"]["new-server"] = {"command": "new"}
    path.write_text(json.dumps(settings))
    assert runner.invoke(main, ["doctor", "--agent", "antigravity"]).exit_code == 0
    assert runner.invoke(main, ["uninstall", "--agent", "agy"]).exit_code == 0
    restored = json.loads(path.read_text())
    assert restored["mcpServers"]["secure-gateway"] == {"command": "previous"}
    assert "new-server" in restored["mcpServers"]
    assert restored["personal"] is True


def test_antigravity_registration_refuses_edits_and_uninstalls_new_entry(tmp_path):
    path = tmp_path / "mcp_config.json"
    configure_antigravity(path)
    settings = json.loads(path.read_text())
    settings["mcpServers"]["secure-gateway"]["command"] = "user-edit"
    path.write_text(json.dumps(settings))
    with pytest.raises(ValueError, match="changed"):
        configure_antigravity(path, install=False)
    settings["mcpServers"]["secure-gateway"]["command"] = sys.executable
    path.write_text(json.dumps(settings))
    configure_antigravity(path, install=False)
    assert "secure-gateway" not in json.loads(path.read_text())["mcpServers"]


def test_cli_version_matches_package():
    assert __version__ in CliRunner().invoke(main, ["--version"]).output


def test_recursive_root_reference_and_remote_reference_boundary():
    session = GatewaySession()
    schema = {"type": "object", "properties": {"privateChild": {"$ref": "#"}}}
    masked = session.request(
        {"messages": [], "tools": [{"name": "recursive", "input_schema": schema}]}
    )
    transformed = masked["tools"][0]["input_schema"]
    assert next(iter(transformed["properties"].values()))["$ref"] == "#"
    assert session.walk(transformed, restore=True) == schema
    for ref in ["https://private.example/schema", "#node"]:
        with pytest.raises(ValueError, match="Remote schema references"):
            session.walk({"$ref": ref})


def test_prose_function_words_and_source_identifier_references():
    session = GatewaySession()
    masked = session.mask("A cat and I saw B.")
    assert masked.startswith("A ") and " I " in masked
    assert "code:identifier:A" not in session.session.forward_store
    assert "code:identifier:I" not in session.session.forward_store
    assert "code:identifier:B" in session.session.forward_store
    session.mask("def A(customer): return customer", code=True)
    assert session.session.forward_store["code:identifier:A"].surrogate in session.mask(
        "Review A."
    )
    fallback = GatewaySession()
    assert not fallback.mask("A = 'unfinished", code=True).startswith("A")


@pytest.mark.parametrize("existing", [False, True])
def test_antigravity_failed_write_restores_registration(
    tmp_path, monkeypatch, existing
):
    import secure_gateway.antigravity_install as install

    path = tmp_path / "mcp_config.json"
    if existing:
        path.write_bytes(b'{"mcpServers":{"other":{"command":"other"}}}\n')
    original = path.read_bytes() if path.exists() else None
    write = install._atomic_json

    def fail_settings(target, data):
        if target == path:
            raise OSError("injected settings failure")
        write(target, data)

    monkeypatch.setattr(install, "_atomic_json", fail_settings)
    with pytest.raises(OSError):
        configure_antigravity(path)
    assert (path.read_bytes() if path.exists() else None) == original
    assert not path.with_name(path.name + ".secure-gateway.json").exists()


def test_original_index_and_legacy_aliases_follow_store_mutations():
    session = GatewaySession()
    store = session.session.forward_store
    mapping = TokenMapping(
        original="PrivateCustomer", surrogate="LegacyAlias", token_type=TokenType.ENTITY
    )
    store.update({"first": mapping})
    assert store.originals_in("PrivateCustomer") == {"PrivateCustomer"}
    assert "LegacyAlias" in store.nonstandard_surrogates
    replacement = TokenMapping(
        original="NewCustomer",
        surrogate="private_symbol_1",
        token_type=TokenType.ENTITY,
    )
    store["first"] = replacement
    assert store.originals_in("PrivateCustomer") == set()
    assert "LegacyAlias" not in store.nonstandard_surrogates
    assert store.pop("first") == replacement
    assert store.originals_in("NewCustomer") == set()
    store.setdefault("second", mapping)
    store |= {"third": replacement}
    assert store.popitem() == ("third", replacement)
    assert store.originals_in("NewCustomer") == set()
    assert store.pop("missing", None) is None
    store.clear()
    assert store.originals_in("PrivateCustomer") == set()


def test_large_mapping_lookup_does_not_enumerate_stable_stores(monkeypatch):
    session = GatewaySession()
    store = session.session.forward_store
    for index in range(10_000):
        mapping = TokenMapping(
            original=f"Original{index}",
            surrogate=f"private_symbol_{index}",
            token_type=TokenType.IDENTIFIER,
            context="code",
        )
        store[f"code:identifier:Original{index}"] = mapping
        session.session.reverse_store[mapping.surrogate] = mapping
    assert store.originals_in("Review Original9999") == {
        "Original9",
        "Original99",
        "Original999",
        "Original9999",
    }

    def no_inventory_scan(*_):
        pytest.fail("stable masking/restoration enumerated the mapping inventory")

    monkeypatch.setattr(type(store), "values", no_inventory_scan)
    monkeypatch.setattr(type(store), "__iter__", no_inventory_scan)
    assert (
        session.restore("private_symbol_9999 and ordinary prose")
        == "Original9999 and ordinary prose"
    )
    assert "private_symbol_9999" in session.mask("Review Original9999")
    session.mask("NewIdentifier", code=True)
    assert store.originals_in("NewIdentifier") == {"NewIdentifier"}
