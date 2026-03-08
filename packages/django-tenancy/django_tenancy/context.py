"""
django_tenancy/context.py

Thread/async-safe tenant context propagation via contextvars.
Used by Celery tasks and async views (ADR-035 §2.3).

Public API:
    get_context()           -> RequestContext (frozen snapshot)
    set_tenant(id, slug)    -> None
    set_user(id)            -> None
    set_request_id(id?)     -> str
    clear_context()         -> None
    tenant_context(id, slug?) -> context manager

Legacy aliases (for backwards compat):
    get_current_tenant_id() -> Optional[int]
    set_current_tenant_id() -> None
"""
from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Optional
from uuid import UUID

from .types import RequestContext

_tenant_id: ContextVar[Optional[UUID]] = ContextVar("tenant_id", default=None)
_tenant_slug: ContextVar[Optional[str]] = ContextVar(
    "tenant_slug", default=None
)
_user_id: ContextVar[Optional[UUID]] = ContextVar("user_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_context() -> RequestContext:
    """Return immutable snapshot of current request context."""
    return RequestContext(
        tenant_id=_tenant_id.get(),
        tenant_slug=_tenant_slug.get(),
        user_id=_user_id.get(),
        request_id=_request_id.get(),
    )


def set_tenant(tenant_id: UUID, slug: Optional[str] = None) -> None:
    """Set the current tenant context."""
    _tenant_id.set(tenant_id)
    _tenant_slug.set(slug)


def set_user(user_id: UUID) -> None:
    """Set the current user context."""
    _user_id.set(user_id)


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set (or generate) a request ID. Returns the ID used."""
    rid = request_id or str(uuid.uuid4())
    _request_id.set(rid)
    return rid


def clear_context() -> None:
    """Reset all context vars to None."""
    _tenant_id.set(None)
    _tenant_slug.set(None)
    _user_id.set(None)
    _request_id.set(None)


# ---------------------------------------------------------------------------
# Legacy aliases
# ---------------------------------------------------------------------------

def get_current_tenant_id() -> Optional[int]:
    """Legacy: return tenant_id as int (or None)."""
    tid = _tenant_id.get()
    return int(tid) if tid is not None else None


def set_current_tenant_id(tenant_id: Optional[int]) -> None:
    """Legacy: set tenant_id from int."""
    _tenant_id.set(UUID(int=tenant_id) if tenant_id is not None else None)


class TenantContext:
    """Context manager for scoping a block to a specific tenant."""

    def __init__(self, tenant_id: UUID, slug: Optional[str] = None) -> None:
        self._tenant_id = tenant_id
        self._slug = slug
        self._prev: Optional[RequestContext] = None

    def __enter__(self) -> "TenantContext":
        self._prev = get_context()
        set_tenant(self._tenant_id, self._slug)
        return self

    def __exit__(self, *args) -> None:
        clear_context()
        if self._prev is not None:
            if self._prev.tenant_id is not None:
                set_tenant(self._prev.tenant_id, self._prev.tenant_slug)
            if self._prev.user_id is not None:
                set_user(self._prev.user_id)
            if self._prev.request_id is not None:
                set_request_id(self._prev.request_id)
