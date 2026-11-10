"""docs/API.md stays aligned with the supported public Python surface."""

from __future__ import annotations

import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_api_doc_covers_public_surface() -> None:
    api = (ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    pkg = importlib.import_module("secure_gateway")
    for name in pkg.__all__:
        assert f"`{name}`" in api or name in api, f"__all__ name missing from docs/API.md: {name}"
        getattr(pkg, name)

    for token in (
        "GatewaySession",
        "LocalPrivacyClient",
        "secure-gateway",
        "gateway install",
        "gateway run",
        "mask_text",
        "mask_code",
        "create_privacy_session",
        "get_session_stats",
        "clear_privacy_session",
    ):
        assert token in api, f"Expected API.md token missing: {token}"
