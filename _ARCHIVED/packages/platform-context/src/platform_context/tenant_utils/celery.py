"""
Celery tenant utilities — ADR-056 Kanal 3 (Cross-Service Tasks).

Provides:
  - TenantAwareTask: Base task class that restores tenant context on execution
  - send_cross_service_task: Send task to another service WITH tenant context

Within a single service, use tenant-schemas-celery which handles this automatically.
These helpers are for CROSS-SERVICE tasks only.
"""

from __future__ import annotations

from typing import Any

_TENANT_SCHEMA_KEY = "_tenant_schema"


def _get_current_schema() -> str:
    """Get current tenant schema from django-tenants connection."""
    try:
        from django.db import connection
        return getattr(connection, "schema_name", "public") or "public"
    except Exception:
        return "public"


def send_cross_service_task(
    task_name: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    **options: Any,
) -> Any:
    """
    Send a Celery task to another service WITH the current tenant context.

    The receiving service must use TenantAwareTask as its base class to
    automatically restore the tenant schema.

    Usage::

        send_cross_service_task(
            "risk_hub.tasks.sync_assessment",
            kwargs={"assessment_id": 42},
        )
    """
    from celery import current_app

    task_kwargs = dict(kwargs or {})
    task_kwargs[_TENANT_SCHEMA_KEY] = _get_current_schema()

    return current_app.send_task(
        task_name,
        args=args or [],
        kwargs=task_kwargs,
        **options,
    )


class TenantAwareTask:
    """
    Base Celery task class that restores tenant context for cross-service tasks.

    Reads _tenant_schema from kwargs (injected by send_cross_service_task)
    and sets the PostgreSQL search_path before executing the task.

    Usage in receiving service::

        # config/celery.py
        app = Celery("myservice")
        app.config_from_object("django.conf:settings", namespace="CELERY")
        app.Task = TenantAwareTask  # set as default base

        # Or per-task:
        @app.task(base=TenantAwareTask)
        def my_task(data):
            ...
    """

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        schema = kwargs.pop(_TENANT_SCHEMA_KEY, "public")
        try:
            from django_tenants.utils import schema_context
            with schema_context(schema):
                return super().__call__(*args, **kwargs)  # type: ignore[misc]
        except ImportError:
            return super().__call__(*args, **kwargs)  # type: ignore[misc]
