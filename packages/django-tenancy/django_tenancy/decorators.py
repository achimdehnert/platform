"""
django_tenancy/decorators.py

@with_tenant decorator for Celery tasks.
Propagates tenant context into async task execution.
"""
from __future__ import annotations

import functools
from typing import Callable

from .context import TenantContext


def with_tenant(tenant_id: int) -> Callable:
    """
    Decorator factory. Wraps a function/Celery task in TenantContext.

    Usage:
        @app.task
        @with_tenant(tenant_id=42)
        def my_task():
            # Organization.objects.for_tenant(42) works here
            ...

        # Or dynamically:
        my_task.apply_async(kwargs={"tenant_id": current_tenant_id})
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tid = kwargs.pop("tenant_id", tenant_id)
            with TenantContext(tid):
                return func(*args, **kwargs)
        return wrapper
    return decorator
