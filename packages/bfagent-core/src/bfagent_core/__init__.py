"""
bfagent-core: Shared core components for BFAgent Hub ecosystem.

Provides:
- Request context management (tenant, user, request_id)
- Audit event logging
- Outbox pattern for reliable events
- Postgres RLS helpers
- Django middleware for multi-tenancy
"""

from bfagent_core.context import (
    RequestContext,
    get_context,
    set_request_id,
    set_tenant,
    set_user_id,
)
from bfagent_core.audit import emit_audit_event
from bfagent_core.outbox import emit_outbox_event
from bfagent_core.db import set_db_tenant

__version__ = "0.1.0"

__all__ = [
    # Context
    "RequestContext",
    "get_context",
    "set_request_id",
    "set_tenant",
    "set_user_id",
    # Audit
    "emit_audit_event",
    # Outbox
    "emit_outbox_event",
    # DB
    "set_db_tenant",
]
