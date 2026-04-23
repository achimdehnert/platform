"""
Request context management using contextvars.

Thread-safe context propagation for:
- tenant_id / tenant_slug
- user_id
- request_id (correlation ID)
"""

import contextvars
from dataclasses import dataclass
from uuid import UUID

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
_current_tenant_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "tenant_id", default=None
)
_current_tenant_slug: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tenant_slug", default=None
)
_current_user_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "user_id", default=None
)


@dataclass(frozen=True)
class RequestContext:
    """Immutable snapshot of the current request context."""

    request_id: str | None
    tenant_id: UUID | None
    tenant_slug: str | None
    user_id: UUID | None

    @property
    def is_authenticated(self) -> bool:
        """Check if a user is set in context."""
        return self.user_id is not None

    @property
    def has_tenant(self) -> bool:
        """Check if a tenant is set in context."""
        return self.tenant_id is not None


def set_request_id(value: str | None) -> None:
    """Set the request/correlation ID for the current context."""
    _request_id.set(value)


def set_tenant(tenant_id: UUID | None, tenant_slug: str | None) -> None:
    """Set the current tenant for the context."""
    _current_tenant_id.set(tenant_id)
    _current_tenant_slug.set(tenant_slug)


def set_user_id(value: UUID | None) -> None:
    """Set the current user ID for the context."""
    _current_user_id.set(value)


def get_context() -> RequestContext:
    """Get the current request context snapshot."""
    return RequestContext(
        request_id=_request_id.get(),
        tenant_id=_current_tenant_id.get(),
        tenant_slug=_current_tenant_slug.get(),
        user_id=_current_user_id.get(),
    )


def clear_context() -> None:
    """Clear all context variables. Useful for testing."""
    _request_id.set(None)
    _current_tenant_id.set(None)
    _current_tenant_slug.set(None)
    _current_user_id.set(None)
