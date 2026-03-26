"""d.velop API exceptions with structured error context."""

from __future__ import annotations


class DvelopError(Exception):
    """Base exception for all d.velop API errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str = "",
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class DvelopAuthError(DvelopError):
    """HTTP 401 — API key invalid or expired."""


class DvelopForbiddenError(DvelopError):
    """HTTP 403 — Missing Origin header or insufficient permissions."""


class DvelopNotFoundError(DvelopError):
    """HTTP 404 — Repository or document not found."""


class DvelopRateLimitError(DvelopError):
    """HTTP 429 — Rate limit exceeded. Check retry_after attribute."""

    def __init__(
        self, message: str, *, retry_after: int | None = None, **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
