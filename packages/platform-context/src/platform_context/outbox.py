"""
Outbox pattern for reliable event publishing.

Ensures events are published reliably by writing to the database
within the same transaction as the business operation.
Model-agnostic: configure PLATFORM_OUTBOX_MODEL in Django settings.
"""

import logging
from typing import Any
from uuid import UUID

_logger = logging.getLogger(__name__)


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

    Requires PLATFORM_OUTBOX_MODEL to be set in Django settings
    (e.g., "bfagent_core.OutboxMessage").

    Args:
        tenant_id: The tenant this event belongs to
        topic: Event topic (e.g., "risk.assessment.created")
        payload: Event payload data
    """
    from django.conf import settings

    model_path = getattr(settings, "PLATFORM_OUTBOX_MODEL", None)
    if not model_path:
        _logger.warning(
            "PLATFORM_OUTBOX_MODEL not configured, outbox event dropped: %s",
            topic,
        )
        return

    from django.apps import apps

    try:
        app_label, model_name = model_path.rsplit(".", 1)
        OutboxModel = apps.get_model(app_label, model_name)
    except (LookupError, ValueError) as exc:
        _logger.error("Cannot resolve PLATFORM_OUTBOX_MODEL=%s: %s", model_path, exc)
        return

    OutboxModel.objects.create(
        tenant_id=tenant_id,
        topic=topic,
        payload=payload,
    )
