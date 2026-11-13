"""Tests for local arithmetic tool dispatcher and execution interception (#319)."""

import json
from decimal import Decimal
import pytest

from secure_gateway import gateway
from secure_gateway.encrypted_session import load_session, save_session
from secure_gateway.experiment_profiles import candidate_profile
from secure_gateway.private_arithmetic import (
    LOCAL_ARITHMETIC_TOOL_NAME,
    PrivateArithmetic,
)


def test_tool_injected_only_when_toggle_is_on():
    payload = {
        "model": "fixture",
        "messages": [{"role": "user", "content": "Calculate total"}],
    }

    # When toggle is off: tools is NOT injected
    session_off = gateway.GatewaySession(mask_numbers=True)
    req_off = session_off.request(payload)
    assert "tools" not in req_off or not any(
        t.get("function", {}).get("name") == LOCAL_ARITHMETIC_TOOL_NAME for t in req_off.get("tools", [])
    )

    # When toggle is on: tools is injected
    with candidate_profile("local_arithmetic"):
        session_on = gateway.GatewaySession(mask_numbers=True)
        req_on = session_on.request(payload)
        assert any(
            (t.get("name") == LOCAL_ARITHMETIC_TOOL_NAME or t.get("function", {}).get("name") == LOCAL_ARITHMETIC_TOOL_NAME)
            for t in req_on.get("tools", [])
        )


def test_user_tool_name_collision_detected():
    colliding_payload = {
        "model": "fixture",
        "messages": [{"role": "user", "content": "test"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": LOCAL_ARITHMETIC_TOOL_NAME,
                    "description": "User collision tool",
                },
            }
        ],
    }
    with candidate_profile("local_arithmetic"):
        session = gateway.GatewaySession(mask_numbers=True)
        with pytest.raises(ValueError, match="collides"):
            session.request(colliding_payload)


def test_local_dispatcher_intercepts_tool_call_and_removes_from_host():
    with candidate_profile("local_arithmetic"):
        session = gateway.GatewaySession(mask_numbers=True)
        p1 = session.values("12.75")
        p2 = session.values("4")
        session.tool_dispatcher.tool.allowed[p1] = "USD"
        session.tool_dispatcher.tool.allowed[p2] = "count"
        session.tool_dispatcher.tool.result_units["multiply"] = "USD"

        # Model response from upstream calling the local arithmetic tool
        upstream_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc123",
                                "type": "function",
                                "function": {
                                    "name": LOCAL_ARITHMETIC_TOOL_NAME,
                                    "arguments": json.dumps({"operation": "multiply", "aliases": [p1, p2]}),
                                },
                            }
                        ],
                    }
                }
            ]
        }

        # Intercept upstream response
        processed_body = session.response(
            json.dumps(upstream_response).encode("utf-8"),
            content_type="application/json",
            dialect="chat_completions",
        )
        processed = json.loads(processed_body.decode("utf-8"))

        # The tool call was removed from what the host sees
        msg = processed["choices"][0]["message"]
        assert "tool_calls" not in msg
        # Content has the result restored for the user host
        assert msg["content"] == "51.00"

        # Dispatcher recorded the execution
        assert len(session.tool_dispatcher.executed_calls) == 1
        call_record = session.tool_dispatcher.executed_calls[0]
        assert call_record["operation"] == "multiply"
        result_alias = call_record["result"]["alias"]
        assert Decimal(session.restore(result_alias)) == Decimal("51.00")


def test_snapshot_restart_replay_strict_restore_derived_alias(tmp_path):
    session = gateway.GatewaySession(mask_numbers=True)
    session.session.session_id = "arithmetic-persist"
    a = session.values("2032-02-27")
    b = session.values("2032-03-02")
    tool = PrivateArithmetic(session, allowed={a: "date", b: "date"}, result_units={"date_difference": "days"})
    res = tool.call("date_difference", [a, b])
    derived_alias = res["alias"]

    # 1. Strict restore before restart
    assert session.restore(derived_alias, strict=True) == "4"

    # 2. Save session snapshot
    token = "snapshot-auth-token-12345"
    save_session(tmp_path / "session.enc", session.session, token)

    # 3. Reload session from encrypted snapshot (restart)
    reloaded_owner = load_session(tmp_path / "session.enc", token, "arithmetic-persist")
    reloaded_session = gateway.GatewaySession(reloaded_owner)

    # 4. Strict restore on restarted session works
    assert reloaded_session.restore(derived_alias, strict=True) == "4"
    assert reloaded_session.restore(a, strict=True) == "2032-02-27"
    assert reloaded_session.restore(b, strict=True) == "2032-03-02"


def test_unknown_foreign_session_and_mutated_aliases_rejected():
    session1 = gateway.GatewaySession(mask_numbers=True)
    session2 = gateway.GatewaySession(mask_numbers=True)
    p1 = session1.values("10")
    session2.values("dummy1")
    session2.values("dummy2")
    p2 = session2.values("20")

    tool1 = PrivateArithmetic(session1, allowed={p1: "count", p2: "count"})
    # p2 is absent from session1 reverse_store
    with pytest.raises(ValueError, match="absent from this session"):
        tool1.call("add", [p1, p2])

    # Mutated alias
    with pytest.raises(ValueError, match="Unknown or unauthorized"):
        tool1.call("add", [p1, p1 + "_mutated"])


def test_ambiguous_unit_and_date_errors():
    session = gateway.GatewaySession(mask_numbers=True)
    x = session.values("10")
    y = session.values("20")
    # Unit mismatch: USD vs EUR
    tool = PrivateArithmetic(session, allowed={x: "USD", y: "EUR"})
    with pytest.raises(ValueError, match="units do not match"):
        tool.call("add", [x, y])

    # Invalid ISO date format
    bad_date = session.values("2032/02/27")
    good_date = session.values("2032-03-02")
    date_tool = PrivateArithmetic(session, allowed={bad_date: "date", good_date: "date"}, result_units={"date_difference": "days"})
    with pytest.raises(ValueError, match="Explicit ISO date"):
        date_tool.call("date_difference", [bad_date, good_date])
