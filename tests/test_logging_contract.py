import io
import logging


def test_logging_failure_omits_exception_text_and_deduplicates_handlers():
    from secure_gateway.logging_config import configure_logging, get_logger, log_failure

    stream = io.StringIO()
    configure_logging("INFO", stream=stream)
    configure_logging("INFO", stream=stream)
    log_failure(get_logger("test"), "cleanup_failed", ValueError("private-token"))
    assert stream.getvalue().count("cleanup_failed") == 1
    assert "ValueError" in stream.getvalue()
    assert "private-token" not in stream.getvalue()


def test_gateway_request_error_preserves_value_error_contract():
    from secure_gateway.exceptions import SecureGatewayError
    from secure_gateway.gateway_errors import GatewayRequestError

    error = GatewayRequestError("invalid_request")
    assert isinstance(error, (ValueError, SecureGatewayError))
    assert isinstance(error, ValueError)
    assert isinstance(error, SecureGatewayError)


def test_sdk_request_log_uses_only_safe_metadata(caplog):
    import urllib.error
    import urllib.request
    from secure_gateway.antigravity_sdk import antigravity_endpoint

    with caplog.at_level(logging.INFO, logger="secure_gateway.antigravity_sdk"):
        with antigravity_endpoint("http://127.0.0.1:12345", "a" * 32, "xai-secret") as url:
            try:
                urllib.request.urlopen(url + "/private-query?token=secret", timeout=3)
            except urllib.error.HTTPError as exc:
                exc.close()
    output = caplog.text
    assert "sdk_request" in output
    assert "method=GET" in output
    assert "status_class=4" in output
    assert "private-query" not in output
    assert "secret" not in output


def test_failed_log_delivery_does_not_raise():
    from secure_gateway.logging_config import log_failure

    class BrokenLogger:
        def warning(self, *args):
            raise OSError("private path")

    log_failure(BrokenLogger(), "cleanup_failed", ValueError("secret"))


def test_source_does_not_log_exception_objects_or_tracebacks():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "secure_gateway"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            assert node.func.attr != "exception", path
            assert not any(k.arg == "exc_info" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords), path
            if (node.func.attr in {"debug", "info", "warning", "error", "critical", "log"}
                    and isinstance(node.func.value, ast.Name)
                    and "logger" in node.func.value.id.lower()):
                for arg in node.args:
                    if isinstance(arg, (ast.Name, ast.JoinedStr, ast.BinOp)):
                        assert not any(isinstance(n, ast.Name) and n.id in {"exc", "exception", "err"}
                                       for n in ast.walk(arg)), path
        for handler in (n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler) and n.name):
            for call in (n for n in ast.walk(handler) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in {"debug", "info", "warning", "error", "critical", "log"} and isinstance(n.func.value, ast.Name) and "logger" in n.func.value.id.lower()):
                for arg in call.args:
                    assert not any(isinstance(n, ast.Name) and n.id == handler.name for n in ast.walk(arg)), path


def test_library_import_does_not_configure_process_handlers():
    import subprocess
    import sys

    code = (
        "import logging; before=list(logging.getLogger().handlers); "
        "import secure_gateway; p=logging.getLogger('secure_gateway'); "
        "assert logging.getLogger().handlers == before; "
        "assert all(isinstance(h, logging.NullHandler) for h in p.handlers)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_cli_translates_hierarchy_error_without_exception_text():
    import click
    from click.testing import CliRunner
    from secure_gateway.cli import LiteralArgumentGroup
    from secure_gateway.exceptions import ProcessError

    @click.group(cls=LiteralArgumentGroup)
    def entry():
        pass

    @entry.command()
    def fail():
        raise ProcessError("private-token")

    result = CliRunner().invoke(entry, ["fail"])
    assert result.exit_code == 1
    assert "SecureGateway operation failed" in result.output
    assert "private-token" not in result.output


def test_legacy_exception_classes_join_hierarchy_and_keep_existing_bases():
    import sqlite3
    from secure_gateway.encrypted_session import SessionExpiredError
    from secure_gateway.engine.masking_engine import NumericLiteralConflict
    from secure_gateway.evaluation_diagnostics import ObservedWorkerFailure
    from secure_gateway.exceptions import SecureGatewayError
    from secure_gateway.gateway_audit import AuditMaintenanceError
    from secure_gateway.gateway_morphology import _Rejected
    from secure_gateway.hooks import _LegacySnapshotLock, _SnapshotBusy

    for cls in (SessionExpiredError, NumericLiteralConflict, ObservedWorkerFailure,
                AuditMaintenanceError, _Rejected, _LegacySnapshotLock, _SnapshotBusy):
        assert issubclass(cls, SecureGatewayError)
    for cls in (SessionExpiredError, NumericLiteralConflict, ObservedWorkerFailure,
                _LegacySnapshotLock, _SnapshotBusy):
        assert issubclass(cls, ValueError)
    assert issubclass(AuditMaintenanceError, sqlite3.OperationalError)
