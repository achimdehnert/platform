"""Notification service (ADR-088).

Synchronous API — dispatches Celery tasks for async delivery.
Celery-First pattern: no async_to_sync needed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class Notification(BaseModel):
    """Notification payload."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str = Field(description="Tenant UUID")
    channel: str = Field(
        description="Channel name (email, sms, webhook, ...)"
    )
    recipient: str = Field(description="Recipient address")
    subject: str = Field(default="", description="Notification subject")
    body: str = Field(description="Notification body")
    source_app: str = Field(
        description="Sending app (bfagent, risk-hub, ...)"
    )
    source_event: str = Field(
        description="Event type (rsvp_confirmation, ...)"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class NotificationService:
    """Platform-wide notification service.

    Synchronous API — dispatches Celery tasks for async delivery.
    """

    @classmethod
    def send(cls, notification: Notification) -> str:
        """Send notification. Returns log_id.

        Sync — safe for Django views.
        """
        from platform_notifications.models import NotificationLog
        from platform_notifications.registry import ChannelRegistry
        from platform_notifications.tasks import (
            dispatch_notification_task,
        )

        registry = ChannelRegistry.get_instance()
        channel = registry.get(notification.channel)

        if not channel.validate_recipient(notification.recipient):
            raise ValueError(
                f"Invalid recipient for channel "
                f"{notification.channel}: "
                f"{notification.recipient}"
            )

        log = NotificationLog.objects.create(
            tenant_id=notification.tenant_id,
            channel=notification.channel,
            recipient=notification.recipient,
            subject=notification.subject,
            body=notification.body,
            source_app=notification.source_app,
            source_event=notification.source_event,
            metadata=notification.metadata,
            status="pending",
        )

        dispatch_notification_task.delay(str(log.id))
        logger.info(
            "Notification queued: log_id=%s channel=%s app=%s",
            log.id,
            notification.channel,
            notification.source_app,
        )
        return str(log.id)

    @classmethod
    def send_sync(cls, notification: Notification) -> str:
        """Send notification synchronously (no Celery).

        Useful for management commands or testing.
        """
        from platform_notifications.models import NotificationLog
        from platform_notifications.registry import ChannelRegistry

        from django.utils import timezone

        registry = ChannelRegistry.get_instance()
        channel = registry.get(notification.channel)

        if not channel.validate_recipient(notification.recipient):
            raise ValueError(
                f"Invalid recipient for channel "
                f"{notification.channel}"
            )

        log = NotificationLog.objects.create(
            tenant_id=notification.tenant_id,
            channel=notification.channel,
            recipient=notification.recipient,
            subject=notification.subject,
            body=notification.body,
            source_app=notification.source_app,
            source_event=notification.source_event,
            metadata=notification.metadata,
            status="pending",
        )

        try:
            success = channel.deliver(
                recipient=notification.recipient,
                subject=notification.subject,
                body=notification.body,
            )
            if success:
                log.status = "sent"
                log.sent_at = timezone.now()
                log.save(
                    update_fields=[
                        "status", "sent_at", "updated_at"
                    ]
                )
        except Exception:
            log.status = "failed"
            log.error_message = (
                "Delivery failed. See application logs."
            )
            log.save(
                update_fields=[
                    "status", "error_message", "updated_at"
                ]
            )
            logger.exception(
                "Sync notification failed: log_id=%s",
                log.id,
            )

        return str(log.id)

    @classmethod
    def health_check(
        cls,
    ) -> dict[str, dict[str, bool | str]]:
        """Health check all registered channels."""
        from platform_notifications.registry import ChannelRegistry

        return ChannelRegistry.get_instance().health_check_all()
