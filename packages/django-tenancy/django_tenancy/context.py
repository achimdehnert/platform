"""
django_tenancy/context.py

Thread/async-safe tenant context propagation via contextvars.
Used by Celery tasks and async views (ADR-035 §2.3).
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

_current_tenant_id: ContextVar[Optional[int]] = ContextVar(
    "current_tenant_id", default=None
)


def get_current_tenant_id() -> Optional[int]:
    """Return the tenant_id for the current execution context."""
    return _current_tenant_id.get()


def set_current_tenant_id(tenant_id: Optional[int]) -> None:
    """Set the tenant_id for the current execution context."""
    _current_tenant_id.set(tenant_id)


class TenantContext:
    """Context manager for scoping a block to a specific tenant."""

    def __init__(self, tenant_id: int) -> None:
        self._tenant_id = tenant_id
        self._token = None

    def __enter__(self) -> "TenantContext":
        self._token = _current_tenant_id.set(self._tenant_id)
        return self

    def __exit__(self, *args) -> None:
        _current_tenant_id.reset(self._token)
