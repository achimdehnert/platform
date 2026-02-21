"""
platform-context: Shared platform foundation for all Django projects.

Provides:
- Request context management (tenant, user, request_id)
- Multi-tenancy middleware (subdomain-based)
- Postgres RLS helpers
- Audit event logging (model-agnostic)
- Outbox pattern for reliable events
- Exception hierarchy
- Django template context processors
- Shared test helpers (platform_context.testing)

Usage::

    from platform_context import get_context, set_tenant, set_user_id
    from platform_context.middleware import SubdomainTenantMiddleware
    from platform_context.audit import emit_audit_event

Test helpers (install with platform-context[testing])::

    # conftest.py
    from platform_context.testing.fixtures import user, admin_user, auth_client  # noqa: F401

    # tests
    from platform_context.testing.assertions import assert_htmx_fragment, assert_login_required
"""

from platform_context.context import (
    RequestContext,
    clear_context,
    get_context,
    set_request_id,
    set_tenant,
    set_user_id,
)
from platform_context.db import get_db_tenant, set_db_tenant
from platform_context.htmx import (
    HtmxErrorMiddleware,
    HtmxResponseMixin,
    is_htmx_request,
)

__version__ = "0.3.0"

__all__ = [
    # Context
    "RequestContext",
    "clear_context",
    "get_context",
    "set_request_id",
    "set_tenant",
    "set_user_id",
    # DB
    "get_db_tenant",
    "set_db_tenant",
    # HTMX (ADR-048)
    "HtmxErrorMiddleware",
    "HtmxResponseMixin",
    "is_htmx_request",
    # Testing helpers (platform-context[testing])
    # Import via: from platform_context.testing.assertions import ...
    # Import via: from platform_context.testing.fixtures import ...
]
