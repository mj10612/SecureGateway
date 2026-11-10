"""Exception categories for SecureGateway boundaries."""


class SecureGatewayError(Exception):
    """Base for gateway errors."""


class ConfigurationError(SecureGatewayError, ValueError):
    """Configuration validation failed."""


class ResourceError(SecureGatewayError):
    """A resource operation failed."""


class ProcessError(SecureGatewayError):
    """A process operation failed."""


class StreamError(SecureGatewayError):
    """A stream operation failed."""
