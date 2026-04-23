"""Celery tasks for notification delivery (ADR-088).

Celery-First pattern: Views dispatch tasks, tasks deliver via channels.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from celery import shared_task

if TYPE_CHECKING:
    from platform_notifications.models import NotificationLog

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    autoretry_for=(ConnectionError, TimeoutError),
)
def dispatch_notification_task(
    self,  # type: ignore[override]
    log_id: str,
) -> None:
    """Deliver notification via channel.

    Celery-First pattern (ADR-088):
    - On success: mark log as sent
    - On transient error: Celery autoretry
    - On permanent error: mark log as failed
    """
    from django.utils import timezone

    from platform_notifications.models import NotificationLog
    from platform_notifications.registry import ChannelRegistry

    log = NotificationLog.objects.get(id=log_id)
    registry = ChannelRegistry.get_instance()

    try:
        channel = registry.get(log.channel)
        success = channel.deliver(
            recipient=log.recipient,
            subject=log.subject,
            body=log.body,
        )
        if success:
            log.status = "sent"
            log.sent_at = timezone.now()
            log.retry_count = self.request.retries
            log.save(
                update_fields=[
                    "status",
                    "sent_at",
                    "retry_count",
                    "updated_at",
                ]
            )
            logger.info(
                "Notification sent: log_id=%s channel=%s",
                log_id,
                log.channel,
            )
    except (ConnectionError, TimeoutError):
        log.retry_count = self.request.retries
        log.save(update_fields=["retry_count", "updated_at"])
        raise
    except Exception:
        _log_failure(log, self.request.retries)
        logger.exception(
            "Notification delivery failed: "
            "log_id=%s channel=%s",
            log_id,
            log.channel,
        )


def _log_failure(
    log: NotificationLog, retry_count: int
) -> None:
    """Mark notification as failed with sanitized error info."""
    log.status = "failed"
    log.retry_count = retry_count
    log.error_message = (
        "Delivery failed after retries. "
        "See application logs for details."
    )
    log.save(
        update_fields=[
            "status",
            "retry_count",
            "error_message",
            "updated_at",
        ]
    )
