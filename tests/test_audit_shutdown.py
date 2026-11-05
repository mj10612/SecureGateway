from contextlib import closing, contextmanager
from threading import Event, Thread
import sqlite3
import json
import time
import urllib.error
import urllib.request
from unittest.mock import Mock

import pytest

from secure_gateway.gateway import PrivacyGateway
from secure_gateway.gateway_install import stop_gateway


@contextmanager
def serving(tmp_path):
    server = PrivacyGateway(("127.0.0.1", 0), "fixture-token-for-audit-tests-32-bytes", audit_path=tmp_path / "audit.sqlite")
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def rejected_post(server):
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_port}/claude/v1/messages", b"{}"
    )
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=2)
    try:
        error.value.read()
        return error.value.code
    finally:
        error.value.close()


def test_close_waits_for_audit_completion_of_unadmitted_request(tmp_path, monkeypatch):
    with serving(tmp_path) as server:
        entered, release, completed, closed = Event(), Event(), Event(), Event()
        finish = server.audit.finish

        def paused_finish(request_id, metadata):
            entered.set()
            assert release.wait(5)
            try:
                finish(request_id, metadata)
            finally:
                completed.set()

        monkeypatch.setattr(server.audit, "finish", paused_finish)
        assert rejected_post(server) == 401
        assert entered.wait(2)
        assert server.admitted_requests == 0
        assert server.active_audit_handlers == 1
        server.shutdown()

        def close():
            server.server_close()
            closed.set()

        closer = Thread(target=close, daemon=True)
        closer.start()
        try:
            assert not closed.wait(.05)
            assert server.audit._owner_file is not None
            release.set()
            assert completed.wait(2)
            assert closed.wait(2)
            assert server.active_audit_handlers == 0
            assert server.audit._owner_file is None
            rows = server.audit.query({})["rows"]
            assert len(rows) == 1 and rows[0]["status"] == 401
        finally:
            release.set()
            closer.join(timeout=2)
        assert not closer.is_alive()


def test_failed_audit_admission_releases_handler_reservation(tmp_path, monkeypatch):
    with serving(tmp_path) as server:
        monkeypatch.setattr(server.audit, "begin", Mock(side_effect=sqlite3.OperationalError("locked")))
        assert rejected_post(server) == 503
        with server.admission:
            assert server.admission.wait_for(lambda: server.active_audit_handlers == 0, timeout=2)
        assert server.admitted_requests == 0 and server.audit_write_errors == 1


def test_closing_server_rejects_audited_request_without_accessing_store(tmp_path, monkeypatch):
    with serving(tmp_path) as server:
        begin = Mock(side_effect=AssertionError("closed audit must not be accessed"))
        monkeypatch.setattr(server.audit, "begin", begin)
        with server.admission:
            server.closing = True
        assert rejected_post(server) == 503
        begin.assert_not_called()
        assert server.active_audit_handlers == server.admitted_requests == 0


@pytest.mark.parametrize("phase", ["update", "maintenance"])
def test_stop_under_real_completion_lock_respects_stop_deadline(tmp_path, monkeypatch, phase):
    with serving(tmp_path) as server:
        entered, release = Event(), Event()
        name = "finish" if phase == "update" else "_completion_maintenance"
        original = getattr(server.audit, name)

        def paused(*args, **kwargs):
            entered.set()
            assert release.wait(5)
            return original(*args, **kwargs)

        monkeypatch.setattr(server.audit, name, paused)
        assert rejected_post(server) == 401
        assert entered.wait(2)
        config = tmp_path / "config.json"
        config.write_text(json.dumps({"port": server.server_port, "token": server.token}))
        try:
            with closing(sqlite3.connect(server.audit.path, timeout=0)) as blocker:
                blocker.execute("BEGIN IMMEDIATE")
                try:
                    release.set()
                    started = time.monotonic()
                    assert stop_gateway(config) is True
                    # The five-second CLI deadline must have room for polling;
                    # only background metadata work remains after the response.
                    assert time.monotonic() - started < 4
                    assert server.active_audit_handlers == 0
                finally:
                    blocker.rollback()
            deadline = time.monotonic() + 3
            while server.audit.completion_retries.diagnostics()["pending"]:
                assert time.monotonic() < deadline
                time.sleep(.01)
            rows = server.audit.query({})["rows"]
            assert len(rows) == 1 and rows[0]["status"] == 401
            assert server.audit_write_errors == 1
        finally:
            release.set()
