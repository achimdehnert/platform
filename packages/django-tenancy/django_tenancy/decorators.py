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

import contextlib
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


def with_tenant_from_arg(arg_name: str = "tenant_id"):
    """Decorator that extracts tenant_id from a function argument.

    The argument value must be a string UUID or UUID instance.

    Args:
        arg_name: Name of the kwarg containing the tenant UUID.

    Usage::

        @shared_task
        @with_tenant_from_arg("tenant_id")
        def my_task(tenant_id: str, payload: dict):
            # RLS + contextvars active
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            raw_value = kwargs.get(arg_name)
            if raw_value is None:
                # Try positional args via introspection
                import inspect

                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if arg_name in params:
                    idx = params.index(arg_name)
                    if idx < len(args):
                        raw_value = args[idx]

            if raw_value is not None:
                tid = UUID(str(raw_value)) if not isinstance(raw_value, UUID) else raw_value
                with tenant_context(tid):
                    return func(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator
