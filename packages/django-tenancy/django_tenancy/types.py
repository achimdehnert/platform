"""Shared type definitions for tenant context."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RequestContext:
    """Immutable snapshot of current request context.

    Attributes:
        tenant_id: UUID of the current tenant (from Organization.tenant_id).
        tenant_slug: Subdomain slug of the current tenant.
        user_id: UUID of the authenticated user (if any).
        request_id: Unique request identifier for tracing.
    """

    tenant_id: UUID | None
    tenant_slug: str | None
    user_id: UUID | None
    request_id: str | None
