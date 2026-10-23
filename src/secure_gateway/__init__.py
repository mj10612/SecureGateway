"""Local multilingual masking and trusted-client restoration with MCP utilities."""

__version__ = "1.3.0"
__author__ = "SecureGateway Contributors"
__license__ = "Apache-2.0"

from secure_gateway.models import (
    MaskMode,
    SurrogateStrategy,
    TokenType,
    TokenMapping,
    MaskResult,
    UnmaskResult,
    SessionStats,
)
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.session import SessionVault
from secure_gateway.client import LocalPrivacyClient

__all__ = [
    "MaskMode",
    "SurrogateStrategy",
    "TokenType",
    "TokenMapping",
    "MaskResult",
    "UnmaskResult",
    "SessionStats",
    "MaskingEngine",
    "SessionVault",
    "LocalPrivacyClient",
]
