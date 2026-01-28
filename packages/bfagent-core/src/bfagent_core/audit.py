"""
Audit event logging for compliance.

Provides structured audit trail for all risk-relevant mutations.
"""

from uuid import UUID
from typing import Any

from bfagent_core.context import get_context


def emit_audit_event(
    *,
    tenant_id: UUID,
    category: str,
    action: str,
    entity_type: str,
    entity_id: UUID,
    payload: dict[str, Any],
) -> None:
    """
    Emit an audit event for a mutation.
    
    This creates an AuditEvent record in the database. The actor_user_id
    and request_id are automatically populated from the current context.
    
    Args:
        tenant_id: The tenant this event belongs to
        category: Event category (e.g., "risk.assessment", "documents.document")
        action: Action performed (e.g., "created", "approved", "deleted")
        entity_type: Full entity type (e.g., "risk.Assessment")
        entity_id: UUID of the affected entity
        payload: Additional data to store (keep small, reference docs for large data)
    
    Example:
        emit_audit_event(
            tenant_id=ctx.tenant_id,
            category="risk.assessment",
            action="approved",
            entity_type="risk.Assessment",
            entity_id=assessment.id,
            payload={"status": "approved", "approved_by": str(user.id)},
        )
    """
    # Import here to avoid circular imports and allow standalone usage
    from bfagent_core.models import AuditEvent
    
    ctx = get_context()
    
    AuditEvent.objects.create(
        tenant_id=tenant_id,
        actor_user_id=ctx.user_id,
        category=category,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        request_id=ctx.request_id,
    )
