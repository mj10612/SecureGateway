"""Privacy-safe, opt-in process logging."""

import logging
import os
import sys
from pathlib import Path
from typing import TextIO


def get_logger(name: str) -> logging.Logger:
    """Return a logger within the SecureGateway namespace."""
    return logging.getLogger(name if name.startswith("secure_gateway.") else "secure_gateway." + name)


def configure_logging(level: str | None = None, *, stream: TextIO | None = None, file: Path | None = None) -> None:
    """Configure one owned handler; importing the library never calls this."""
    package = logging.getLogger("secure_gateway")
    numeric = getattr(logging, (level or os.getenv("SECURE_GATEWAY_LOG_LEVEL") or "WARNING").upper(), logging.WARNING)
    if not isinstance(numeric, int):
        numeric = logging.WARNING
    for handler in package.handlers[:]:
        if getattr(handler, "_secure_gateway_owned", False):
            package.removeHandler(handler)
            handler.close()
    handler = logging.FileHandler(file, encoding="utf-8") if file is not None else logging.StreamHandler(stream or sys.stderr)
    setattr(handler, "_secure_gateway_owned", True)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    package.addHandler(handler)
    package.setLevel(numeric)


def log_failure(logger: logging.Logger, event: str, exc: BaseException) -> None:
    """Log only an event and exception type, never the exception value."""
    try:
        logger.warning("%s exception_type=%s", event, type(exc).__name__)
    except Exception:
        return  # Logging cannot interrupt recovery or log its own failure.
