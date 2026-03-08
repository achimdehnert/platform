"""
django_tenancy/decorators.py

Tenant context decorators and context managers.
"""
from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from contextlib import contextmanager
from uuid import UUID

from .context import TenantContext, clear_context, set_tenant


@contextmanager
def tenant_context(tenant_id: UUID, slug: str | None = None):
    """Context manager: run a block under a specific tenant."""
    with TenantContext(tenant_id, slug):
        yield


def with_tenant_from_arg(arg_name: str) -> Callable:
    """Decorator: extract tenant_id from a named argument and activate context.

    Works on both sync and async functions.
    The argument must be a UUID or UUID string.

    Usage::

        @with_tenant_from_arg("tenant_id")
        def process(tenant_id: str, data: str): ...

        @with_tenant_from_arg("tenant_id")
        async def async_process(tenant_id: str, data: str): ...
    """
    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                raw = _extract_arg(func, args, kwargs, arg_name)
                if raw is not None:
                    tid = UUID(str(raw)) if not isinstance(raw, UUID) else raw
                    set_tenant(tid)
                try:
                    return await func(*args, **kwargs)
                finally:
                    clear_context()
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                raw = _extract_arg(func, args, kwargs, arg_name)
                if raw is not None:
                    tid = UUID(str(raw)) if not isinstance(raw, UUID) else raw
                    set_tenant(tid)
                try:
                    return func(*args, **kwargs)
                finally:
                    clear_context()
            return sync_wrapper
    return decorator


def _extract_arg(func, args, kwargs, arg_name: str):
    """Extract a named argument from args or kwargs."""
    if arg_name in kwargs:
        return kwargs[arg_name]
    try:
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        idx = params.index(arg_name)
        if idx < len(args):
            return args[idx]
    except (ValueError, IndexError):
        pass
    return None


def with_tenant(tenant_id: int) -> Callable:
    """Legacy: wrap a Celery task in TenantContext (int tenant_id)."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tid = kwargs.pop("tenant_id", tenant_id)
            with TenantContext(UUID(int=tid)):
                return func(*args, **kwargs)
        return wrapper
    return decorator
