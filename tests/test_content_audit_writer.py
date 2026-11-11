import threading

import pytest

from secure_gateway.content_audit import ContentAuditStore
from secure_gateway.content_audit_writer import ContentAuditWriter


def test_block_preflight_is_durable_and_fails_when_locked(tmp_path):
    store = ContentAuditStore(tmp_path / "content.sqlite3")
    store.initialize("passphrase")
    writer = ContentAuditWriter(store)
    assert writer.begin("one", "block", {"text": "synthetic"})
    assert store.read("one") == [("opened", {"input": {"text": "synthetic"}, "redactions": 0})]
    store.lock()
    assert not writer.begin("two", "block", {"text": "not forwarded"})
    assert writer.status("two")["state"] == "기록 실패 (잠김)"
    writer.close()
    store.close()


def test_continue_writer_redacts_and_marks_success(tmp_path):
    store = ContentAuditStore(tmp_path / "content.sqlite3")
    store.initialize("passphrase")
    writer = ContentAuditWriter(store)
    assert writer.begin("one", "continue", {"authorization": "credential", "password": "secret",
                                             "text": "sk-abcdefghijklMNOP123456789"})
    assert writer.capture("one", "sent", {"text": "safe"})
    assert writer.finish("one")
    writer.drain()
    records = store.read("one")
    assert records[0][1] == {"input": {"text": "[credential removed]"}, "redactions": 3}
    assert records[1] == ("sent", {"content": {"text": "safe"}, "redactions": 0})
    assert writer.status("one")["state"] == "완료"
    writer.close()
    store.close()


def test_saturation_never_waits_for_slow_writer():
    class SlowStore:
        def __init__(self):
            self.started = threading.Event()
            self.release = threading.Event()

        def append(self, request_id, kind, payload):
            self.started.set()
            assert self.release.wait(5)

    store = SlowStore()
    writer = ContentAuditWriter(store, queue_size=1)
    assert writer.begin("one", "continue", None)
    assert store.started.wait(5)
    assert writer.capture("one", "sent", "first")
    assert not writer.capture("one", "response", "dropped")
    assert writer.status("one")["state"] == "기록 실패"
    store.release.set()
    writer.close()


def test_size_event_limits_and_writer_failure(tmp_path):
    store = ContentAuditStore(tmp_path / "content.sqlite3")
    store.initialize("passphrase")
    writer = ContentAuditWriter(store, kind_limit=24, stream_limit=1)
    assert writer.begin("one", "block", None)
    assert not writer.capture("one", "input", "x" * 100)
    assert writer.capture("one", "response", "one", stream=True)
    assert not writer.capture("one", "response", "two", stream=True)
    assert writer.finish("one")
    writer.drain()
    assert writer.status("one")["state"] == "부분"
    assert writer.status("one")["omitted_bytes"] > 0
    assert writer.status("one")["omitted_events"] == 1
    store.lock()
    assert writer.begin("two", "continue", None)
    writer.drain()
    assert writer.status("two")["state"] == "기록 실패 (잠김)"
    writer.close()
    store.close()


def test_later_completion_marker_reports_earlier_write_failure():
    class FailingStore:
        def __init__(self):
            self.events = []

        def append(self, request_id, kind, payload):
            if kind == "sent":
                raise OSError("synthetic failure")
            self.events.append((kind, payload))

    store = FailingStore()
    writer = ContentAuditWriter(store)
    assert writer.begin("one", "block", None)
    assert writer.capture("one", "sent", "data")
    assert writer.finish("one")
    writer.drain()
    assert writer.status("one")["state"] == "기록 실패"
    assert store.events[-1][1]["failed"] is True
    writer.close()


def test_uncertain_and_interrupted_outcomes(tmp_path):
    store = ContentAuditStore(tmp_path / "content.sqlite3")
    store.initialize("passphrase")
    writer = ContentAuditWriter(store)
    assert writer.begin("one", "block", None)
    assert writer.finish("one", uncertain=True)
    assert writer.begin("two", "block", None)
    assert writer.finish("two", interrupted=True)
    writer.drain()
    assert writer.status("one")["state"] == "전송 여부 불확실"
    assert store.read("one")[-1][1]["uncertain"] is True
    assert writer.status("two")["state"] == "부분"
    assert store.read("two")[-1][1]["partial"] is True
    writer.close()
    store.close()


def test_locked_continue_gap_survives_restart(tmp_path):
    path = tmp_path / "audit.sqlite3"
    store = ContentAuditStore(path)
    store.initialize("passphrase")
    store.lock()
    writer = ContentAuditWriter(store)
    assert writer.begin("one", "continue", {"text": "not persisted"})
    writer.drain()
    writer.close()
    store.close()
    reopened = ContentAuditStore(path)
    assert reopened.request_status("one")["state"] == "기록 실패 (잠김)"
    reopened.close()


def test_omission_is_persisted_before_request_finishes(tmp_path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3")
    store.initialize("passphrase")
    writer = ContentAuditWriter(store, kind_limit=24)
    assert writer.begin("one", "block", None)
    assert not writer.capture("one", "response", "x" * 100)
    writer.drain()
    assert store.request_status("one")["omitted_bytes"] > 0
    writer.close()
    store.close()


def test_retention_does_not_delete_active_requests(tmp_path):
    store = ContentAuditStore(tmp_path / "audit.sqlite3", max_requests=1)
    store.initialize("passphrase")
    writer = ContentAuditWriter(store)
    assert writer.begin("first", "block", "synthetic")
    with pytest.raises(ValueError):
        store.delete_selected(["first"])
    assert not writer.begin("second", "block", "synthetic")
    assert store.read("first")[0][0] == "opened"
    assert writer.finish("first")
    writer.drain()
    assert writer.begin("third", "block", "synthetic")
    assert store.read("first") == []
    assert store.read("third")[0][0] == "opened"
    writer.close()
    store.close()


def test_completed_in_memory_statuses_are_bounded():
    class MemoryStore:
        def append(self, request_id, kind, payload):
            pass

        def mark_status(self, request_id, state, omitted_bytes, omitted_events):
            pass

    writer = ContentAuditWriter(MemoryStore(), queue_size=2048)
    for number in range(1010):
        request_id = str(number)
        assert writer.begin(request_id, "block", None)
        assert writer.finish(request_id)
    writer.drain()
    assert len(writer._requests) <= 1000
    assert writer.status("1009")["state"] == "완료"
    writer.close()
