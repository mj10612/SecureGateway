"""Restricted local alias arithmetic never returns source numeric values."""
from decimal import Decimal

import pytest

from secure_gateway.gateway import GatewaySession


def test_local_decimal_result_is_a_new_restorable_alias():
    from secure_gateway.private_arithmetic import PrivateArithmetic
    session = GatewaySession()
    left = session.values("12.50")
    right = session.values("4")
    tool = PrivateArithmetic(session, allowed={left: "USD", right: "count"}, result_units={"multiply": "USD"})
    result = tool.call("multiply", [left, right])
    assert set(result) == {"alias"}
    assert Decimal(session.restore(result["alias"])) == Decimal("50.00")
    assert result["alias"] not in {left, right}
    assert "50" not in str(result)


def test_policy_invalid_aliases_units_budget_and_operations():
    from secure_gateway.private_arithmetic import PrivateArithmetic
    session = GatewaySession()
    left, right = session.values("2"), session.values("3")
    tool = PrivateArithmetic(session, allowed={left: "USD", right: "EUR"}, max_calls=1)
    for operation, args in [("eval", [left, right]), ("add", [left, right]), ("multiply", [left + "x", right])]:
        with pytest.raises(ValueError):
            tool.call(operation, args)
    tool = PrivateArithmetic(session, allowed={left: "count", right: "count"}, max_calls=1)
    assert session.restore(tool.call("add", [left, right])["alias"]) == "5"
    with pytest.raises(ValueError, match="budget"):
        tool.call("add", [left, right])


def test_date_difference_requires_explicit_unit_and_iso_dates():
    from secure_gateway.private_arithmetic import PrivateArithmetic
    session = GatewaySession()
    a, b = session.values("2026-01-01"), session.values("2026-01-11")
    tool = PrivateArithmetic(session, allowed={a: "date", b: "date"}, result_units={"date_difference": "days"})
    assert session.restore(tool.call("date_difference", [a, b])["alias"]) == "10"


def test_derived_binding_does_not_reuse_or_retype_existing_operand():
    from secure_gateway.private_arithmetic import PrivateArithmetic
    session = GatewaySession()
    left, zero = session.values("2"), session.values("0")
    tool = PrivateArithmetic(session, allowed={left: "USD", zero: "USD"})
    result = tool.call("add", [left, zero])["alias"]
    assert result != left and session.restore(result) == "2"
    assert tool.allowed[left] == "USD"


def test_expired_session_rejects_local_computation():
    from secure_gateway.private_arithmetic import PrivateArithmetic
    session = GatewaySession()
    left = session.values("2")
    tool = PrivateArithmetic(session, allowed={left: "count"})
    session.session.last_accessed = 0
    with pytest.raises(ValueError, match="expired"):
        tool.call("add", [left, left])


def test_parallel_calls_keep_distinct_result_bindings():
    from concurrent.futures import ThreadPoolExecutor
    from secure_gateway.private_arithmetic import PrivateArithmetic
    session = GatewaySession()
    left, right = session.values("2"), session.values("3")
    tool = PrivateArithmetic(session, allowed={left: "count", right: "count"}, max_calls=2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(tool.call, "add", pair) for pair in ([left, right], [left, left])]
        aliases = [job.result()["alias"] for job in jobs]
    assert len(set(aliases)) == 2
    assert [session.restore(alias) for alias in aliases] == ["5", "4"]
    with pytest.raises(ValueError, match="budget"):
        tool.call("add", [left, left])


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1000000000001", "0.1234567890123456789", "2032-02-27T00:00:00Z"])
def test_unsupported_values_fail_without_result_binding(value):
    from secure_gateway.private_arithmetic import PrivateArithmetic
    session = GatewaySession()
    left, right = session.values(value), session.values("2")
    tool = PrivateArithmetic(session, allowed={left: "count", right: "count"})
    before = len(session.session.forward_store)
    with pytest.raises(ValueError):
        tool.call("add", [left, right])
    assert len(session.session.forward_store) == before


def test_cli_fixture_persists_alias_only_result_and_encrypted_restart(tmp_path, monkeypatch, capsys):
    import json
    from secure_gateway.encrypted_session import load_session, save_session
    from secure_gateway.private_arithmetic import main
    session = GatewaySession()
    session.session.session_id = "arithmetic-fixture"
    left, right = session.values("12.75"), session.values("4")
    save_session(tmp_path / "session.enc", session.session, "synthetic-owner")
    config = {"token": "synthetic-owner", "allowed": {left: "USD", right: "count"},
              "result_units": {"multiply": "USD"}, "max_calls": 2, "calls": 0}
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps(config), encoding="utf8")
    monkeypatch.setattr("sys.argv", ["arithmetic", "--fixture", str(fixture), "multiply", left, right])
    assert main() == 0
    output = capsys.readouterr().out
    result = json.loads(output)
    assert set(result) == {"alias"} and "12.75" not in output and "51.00" not in output
    restored = GatewaySession(load_session(tmp_path / "session.enc", "synthetic-owner", "arithmetic-fixture"))
    assert restored.restore(result["alias"]) == "51.00"
    assert restored.restore(left) == "12.75" and restored.restore(right) == "4"
    saved = json.loads(fixture.read_text(encoding="utf8"))
    assert saved["calls"] == 1 and saved["transcript"][0]["result"] == result
    assert b"12.75" not in (tmp_path / "session.enc").read_bytes()
