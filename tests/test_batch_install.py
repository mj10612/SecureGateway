"""Installation ownership, interruption recovery and control requests."""

import json
import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import urllib.error

import pytest

from secure_gateway import gateway_install as g


def install(tmp_path, **kwargs):
    return g.install_gateway(
        tmp_path / "gateway/config.json",
        agent="claude",
        claude_dir=tmp_path / "claude",
        startup_path=tmp_path / "startup",
        **kwargs,
    )


def test_reinstall_refuses_deleted_owned_file(tmp_path):
    install(tmp_path)
    settings = tmp_path / "claude/settings.json"
    settings.unlink()
    with pytest.raises(ValueError, match="settings changed"):
        install(tmp_path)
    assert not settings.exists()


@pytest.mark.parametrize(
    "value",
    [
        {"env": None},
        {"env": []},
        {"hooks": None},
        {"env": {"ANTHROPIC_CUSTOM_HEADERS": 42}},
    ],
)
def test_invalid_claude_structure_is_clean_error(tmp_path, value):
    settings = tmp_path / "claude/settings.json"
    settings.parent.mkdir()
    raw = json.dumps(value).encode()
    settings.write_bytes(raw)
    with pytest.raises(ValueError):
        install(tmp_path)
    assert settings.read_bytes() == raw
    assert not (tmp_path / "startup").exists()


@pytest.mark.parametrize("operation", ["install", "uninstall"])
def test_interrupted_install_recovers_exact_originals(tmp_path, monkeypatch, operation):
    settings = tmp_path / "claude/settings.json"
    settings.parent.mkdir()
    original = b'{"personal": true}\n'
    settings.write_bytes(original)
    write = g.atomic_bytes

    def interrupt(path, data):
        if path == settings:
            raise KeyboardInterrupt()
        return write(path, data)

    with monkeypatch.context() as patch:
        patch.setattr(g, "atomic_bytes", interrupt)
        with pytest.raises(KeyboardInterrupt):
            install(tmp_path)
    monkeypatch.setattr(g, "stop_gateway", lambda _: False)
    if operation == "install":
        install(tmp_path)
    g.uninstall_gateway(tmp_path / "gateway/config.json")
    assert settings.read_bytes() == original
    assert not (tmp_path / "startup").exists()


def test_interrupted_install_preserves_later_user_edit(tmp_path, monkeypatch):
    settings = tmp_path / "claude/settings.json"
    write = g.atomic_bytes

    def interrupt(path, data):
        if path == settings:
            raise KeyboardInterrupt()
        return write(path, data)

    with monkeypatch.context() as patch:
        patch.setattr(g, "atomic_bytes", interrupt)
        with pytest.raises(KeyboardInterrupt):
            install(tmp_path)
    settings.parent.mkdir(exist_ok=True)
    settings.write_text('{"personal": "new"}')
    with pytest.raises(ValueError):
        install(tmp_path)
    assert settings.read_text() == '{"personal": "new"}'


def test_orca_mirror_accepts_canonical_bytes_preserves_each_backup(
    tmp_path, monkeypatch
):
    canonical, managed = tmp_path / ".codex", tmp_path / "account"
    canonical.mkdir()
    managed.mkdir()
    (managed / ".orca-managed-home").touch()
    originals = [b'model="canonical"\n', b'model="account"\n']
    for home, raw in zip([canonical, managed], originals):
        (home / "config.toml").write_bytes(raw)
    monkeypatch.setattr(g.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("CODEX_HOME", str(managed))
    monkeypatch.setenv("ORCA_CODEX_HOME", str(managed))
    monkeypatch.setattr(g, "stop_gateway", lambda _: False)
    config = tmp_path / "gateway/config.json"
    g.install_gateway(config, agent="codex", startup_path=tmp_path / "startup")
    assert (managed / "config.toml").read_bytes() != (
        canonical / "config.toml"
    ).read_bytes()
    shutil.copyfile(canonical / "config.toml", managed / "config.toml")
    assert g.changed_installation_files(config) == []
    g.install_gateway(config, agent="codex", startup_path=tmp_path / "startup")
    g.uninstall_gateway(config)
    for home, raw in zip([canonical, managed], originals):
        assert (home / "config.toml").read_bytes() == raw


def test_stop_waits_after_successful_ack(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"port": 38117, "token": "t" * 32}))
    states = iter([True, True, False])
    monkeypatch.setattr(g, "healthy", lambda _: next(states))

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self):
            return b"{}"

    class Opener:
        def open(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(g.urllib.request, "build_opener", lambda *_: Opener())
    sleeps = []
    monkeypatch.setattr(g.time, "sleep", sleeps.append)
    assert g.stop_gateway(config)
    assert sleeps


@pytest.mark.parametrize("operation", ["health", "shutdown"])
def test_control_requests_never_follow_token_redirect(tmp_path, monkeypatch, operation):
    received = []

    class Receiver(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            received.append(self.headers.get("X-SecureGateway-Token"))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"service":"secure-gateway-subscription-gateway"}')

    receiver = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)

    class Redirect(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            self.send_response(302)
            self.send_header(
                "Location", f"http://127.0.0.1:{receiver.server_port}/capture"
            )
            self.end_headers()

        do_POST = do_GET

    source = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    workers = [Thread(target=server.serve_forever) for server in (receiver, source)]
    for worker in workers:
        worker.start()
    config = {"port": source.server_port, "token": "t" * 32}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    try:
        if operation == "health":
            assert not g.healthy(config)
        else:
            monkeypatch.setattr(g, "healthy", lambda _: True)
            with pytest.raises(urllib.error.HTTPError):
                g.stop_gateway(path)
        assert received == []
    finally:
        for server in (receiver, source):
            server.shutdown()
            server.server_close()
        for worker in workers:
            worker.join()


def test_reinstall_interruption_restores_previous_install(tmp_path, monkeypatch):
    install(tmp_path)
    paths = [
        tmp_path / "claude/settings.json",
        tmp_path / "startup",
        tmp_path / "gateway/config.json",
        tmp_path / "gateway/installation.json",
    ]
    before = [path.read_bytes() for path in paths]
    write = g.atomic_bytes

    def interrupt(path, data):
        if path == paths[0]:
            raise KeyboardInterrupt()
        return write(path, data)

    with monkeypatch.context() as patch:
        patch.setattr(g, "atomic_bytes", interrupt)
        with pytest.raises(KeyboardInterrupt):
            install(tmp_path)
    install(tmp_path)
    assert [path.read_bytes() for path in paths] == before
