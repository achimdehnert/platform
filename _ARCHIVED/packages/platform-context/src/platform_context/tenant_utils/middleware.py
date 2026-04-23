"""
TenantPropagationMiddleware — ADR-056 Kanal 1 (Service-zu-Service REST).

Liest den X-Tenant-Schema Header bei eingehenden Service-zu-Service-Calls
und setzt den PostgreSQL search_path auf das entsprechende Tenant-Schema.

Nur aktiv wenn kein Tenant bereits via Subdomain gesetzt wurde
(django-tenants TenantMainMiddleware hat Priorität).
"""

from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse

TENANT_HEADER = "X-Tenant-Schema"
_SAFE_SCHEMA_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyz0123456789_"
)


def _is_safe_schema_name(name: str) -> bool:
    """Validate schema name to prevent SQL injection."""
    return bool(name) and all(c in _SAFE_SCHEMA_CHARS for c in name)


class TenantPropagationMiddleware:
    """
    Middleware for service-to-service calls that do NOT go through subdomains
    (e.g. internal Docker network calls: http://service-b:8000/api/...).

    Reads X-Tenant-Schema header and sets the PostgreSQL search_path.
    django-tenants TenantMainMiddleware (subdomain-based) takes priority.

    Add AFTER TenantMainMiddleware in MIDDLEWARE settings:

        MIDDLEWARE = [
            "django_tenants.middleware.main.TenantMainMiddleware",
            "platform_context.tenant_utils.middleware.TenantPropagationMiddleware",
            ...
        ]
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not hasattr(request, "tenant") and TENANT_HEADER in request.headers:
            schema = request.headers[TENANT_HEADER]
            if _is_safe_schema_name(schema):
                try:
                    from django.db import connection
                    connection.set_schema(schema)
                except Exception:
                    pass
        return self.get_response(request)
