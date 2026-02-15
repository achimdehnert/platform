"""Contextvars-based tenant context propagation.

Async-safe. Works with Django 5.x async views and Celery tasks.

Usage::

    from django_tenancy.context import get_context, set_tenant, set_db_tenant

    # In middleware (automatic):
    set_tenant(org.tenant_id, subdomain)
    set_db_tenant(org.tenant_id)

    # In application code:
    ctx = get_context()
    queryset.filter(tenant_id=ctx.tenant_id)

    # In Celery tasks (use @with_tenant decorator or manual):
    set_tenant(tenant_id, None)
    set_db_tenant(tenant_id)
"""

from __future__ import annotations

import contextvars
import logging
import uuid as _uuid
from uuid import UUID

from .types import RequestContext

logger = logging.getLogger(__name__)

_tenant_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "tenant_id", default=None
)
_tenant_slug: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tenant_slug", default=None
)
_user_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "user_id", default=None
)
_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def get_context() -> RequestContext:
    """Get current request context (immutable snapshot)."""
    return RequestContext(
        tenant_id=_tenant_id.get(),
        tenant_slug=_tenant_slug.get(),
        user_id=_user_id.get(),
        request_id=_request_id.get(),
    )


def set_tenant(tenant_id: UUID | None, slug: str | None) -> None:
    """Set current tenant context."""
    _tenant_id.set(tenant_id)
    _tenant_slug.set(slug)


def set_user(user_id: UUID | None) -> None:
    """Set current user context."""
    _user_id.set(user_id)


def set_request_id(request_id: str | None = None) -> str:
    """Set request ID. Generates a new UUID if not provided."""
    if request_id is None:
        request_id = str(_uuid.uuid4())
    _request_id.set(request_id)
    return request_id


def set_db_tenant(tenant_id: UUID | None) -> None:
    """Set PostgreSQL session variable for RLS policies.

    Uses session-scoped ``SET`` (not ``SET LOCAL``) so the variable
    persists for the entire connection lifetime within this request.

    Silently skips on non-PostgreSQL backends (e.g. SQLite in tests).

    Args:
        tenant_id: Tenant UUID to set, or None to reset.
    """
    from django.db import connection

    if connection.vendor != "postgresql":
        return

    if tenant_id is not None:
        with connection.cursor() as cursor:
            cursor.execute("SET app.tenant_id = %s", [str(tenant_id)])
    else:
        with connection.cursor() as cursor:
            cursor.execute("RESET app.tenant_id")


def clear_context() -> None:
    """Clear all context variables. Call at end of request."""
    _tenant_id.set(None)
    _tenant_slug.set(None)
    _user_id.set(None)
    _request_id.set(None)
