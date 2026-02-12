"""
Audit event logging for compliance.

Provides structured audit trail for all risk-relevant mutations.
Model-agnostic: configure PLATFORM_AUDIT_MODEL in Django settings.
"""

import logging
from typing import Any
from uuid import UUID

from platform_context.context import get_context

_logger = logging.getLogger(__name__)


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

    The actor_user_id and request_id are automatically populated
    from the current request context.

    Requires PLATFORM_AUDIT_MODEL to be set in Django settings
    (e.g., "bfagent_core.AuditEvent").

    Args:
        tenant_id: The tenant this event belongs to
        category: Event category (e.g., "risk.assessment")
        action: Action performed (e.g., "created", "approved")
        entity_type: Full entity type (e.g., "risk.Assessment")
        entity_id: UUID of the affected entity
        payload: Additional data to store
    """
    from django.conf import settings

    model_path = getattr(settings, "PLATFORM_AUDIT_MODEL", None)
    if not model_path:
        _logger.warning(
            "PLATFORM_AUDIT_MODEL not configured, audit event dropped: "
            "%s.%s on %s",
            category,
            action,
            entity_type,
        )
        return

    from django.apps import apps

    try:
        app_label, model_name = model_path.rsplit(".", 1)
        AuditModel = apps.get_model(app_label, model_name)
    except (LookupError, ValueError) as exc:
        _logger.error("Cannot resolve PLATFORM_AUDIT_MODEL=%s: %s", model_path, exc)
        return

    ctx = get_context()

    AuditModel.objects.create(
        tenant_id=tenant_id,
        actor_user_id=ctx.user_id,
        category=category,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        request_id=ctx.request_id,
    )
