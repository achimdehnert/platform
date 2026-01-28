"""
Outbox pattern for reliable event publishing.

Ensures events are published reliably by writing to the database
within the same transaction as the business operation.
"""

from uuid import UUID
from typing import Any


def emit_outbox_event(
    *,
    tenant_id: UUID,
    topic: str,
    payload: dict[str, Any],
) -> None:
    """
    Emit an outbox event for async processing.
    
    The event is written to the outbox table within the current transaction.
    A background worker polls the outbox and publishes events to the event bus.
    
    Args:
        tenant_id: The tenant this event belongs to
        topic: Event topic (e.g., "risk.assessment.created")
        payload: Event payload data
    
    Example:
        emit_outbox_event(
            tenant_id=ctx.tenant_id,
            topic="risk.assessment.approved",
            payload={"assessment_id": str(assessment.id)},
        )
    
    Note:
        - Always call within a transaction (atomic block)
        - Keep payloads small, use IDs to reference large data
        - Topic format: "{domain}.{entity}.{action}"
    """
    # Import here to avoid circular imports
    from bfagent_core.models import OutboxMessage
    
    OutboxMessage.objects.create(
        tenant_id=tenant_id,
        topic=topic,
        payload=payload,
    )
