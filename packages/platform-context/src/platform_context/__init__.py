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

Usage:
    from platform_context import get_context, set_tenant, set_user_id
    from platform_context.middleware import SubdomainTenantMiddleware
    from platform_context.audit import emit_audit_event
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

__version__ = "0.1.0"

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
]
