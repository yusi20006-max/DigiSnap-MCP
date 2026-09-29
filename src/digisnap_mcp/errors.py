"""Domain errors with stable error categories."""


class DigiSnapError(Exception):
    """Base exception for expected DigiSnap failures."""


class AdapterError(DigiSnapError):
    """A store adapter could not complete an operation."""


class ConfigurationError(DigiSnapError):
    """Invalid application configuration."""


class ProductNotFoundError(AdapterError):
    """A requested product does not exist at a store."""


class RateLimitError(AdapterError):
    """An upstream store rejected a request because of rate limiting."""
