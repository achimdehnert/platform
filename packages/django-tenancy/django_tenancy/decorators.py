"""Decorators for tenant context in non-HTTP contexts (Celery, management commands).

Usage::

    from django_tenancy.decorators import with_tenant

    @shared_task
    @with_tenant_from_arg("tenant_id")
    def process_data(tenant_id: str, data: dict):
        # tenant context is set, RLS is active
        ...

    # Or explicit:
    @shared_task
    def process_data(tenant_id: str, data: dict):
        with tenant_context(UUID(tenant_id)):
            ...
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
from functools import wraps
from uuid import UUID

from .context import clear_context, set_db_tenant, set_tenant


@contextlib.contextmanager
def tenant_context(tenant_id: UUID, slug: str | None = None):
    """Context manager that sets tenant for the duration of a block.

    Sets both contextvars and PostgreSQL RLS session variable.
    Clears context on exit.

    Args:
        tenant_id: The tenant UUID.
        slug: Optional subdomain slug.

    Usage::

        with tenant_context(some_uuid):
            MyModel.objects.for_tenant(some_uuid).all()
    """
    set_tenant(tenant_id, slug)
    set_db_tenant(tenant_id)
    try:
        yield
    finally:
        set_db_tenant(None)
        clear_context()


def _resolve_arg(func, arg_name: str, args: tuple, kwargs: dict):
    """Extract a named argument from args/kwargs."""
    raw_value = kwargs.get(arg_name)
    if raw_value is None:
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        if arg_name in params:
            idx = params.index(arg_name)
            if idx < len(args):
                raw_value = args[idx]
    return raw_value


def with_tenant_from_arg(arg_name: str = "tenant_id"):
    """Decorator that extracts tenant_id from a function argument.

    Works with both sync and async functions.
    The argument value must be a string UUID or UUID instance.

    Args:
        arg_name: Name of the kwarg containing the tenant UUID.

    Usage::

        @shared_task
        @with_tenant_from_arg("tenant_id")
        def my_task(tenant_id: str, payload: dict):
            # RLS + contextvars active
            ...

        @with_tenant_from_arg("tenant_id")
        async def my_async_task(tenant_id: str):
            # Also works with async functions
            ...
    """

    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                raw_value = _resolve_arg(func, arg_name, args, kwargs)
                if raw_value is not None:
                    tid = UUID(str(raw_value)) if not isinstance(raw_value, UUID) else raw_value
                    with tenant_context(tid):
                        return await func(*args, **kwargs)
                return await func(*args, **kwargs)

            return async_wrapper

        @wraps(func)
        def wrapper(*args, **kwargs):
            raw_value = _resolve_arg(func, arg_name, args, kwargs)
            if raw_value is not None:
                tid = UUID(str(raw_value)) if not isinstance(raw_value, UUID) else raw_value
                with tenant_context(tid):
                    return func(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator
