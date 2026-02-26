"""Notification audit log model (ADR-088).

Multi-Tenancy: Row-Level Isolation via tenant_id.
Begründung: Siehe ADR-088 §ADR-072 Abweichung.
"""

import uuid

from django.db import models


class NotificationLog(models.Model):
    """Audit log for all notifications."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    channel = models.CharField(max_length=50)
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField()
    source_app = models.CharField(max_length=50)
    source_event = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    retry_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notification_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_notif_tenant_status",
            ),
            models.Index(
                fields=["channel", "status"],
                name="idx_notif_channel_status",
            ),
            models.Index(
                fields=["source_app", "source_event"],
                name="idx_notif_source",
            ),
            models.Index(
                fields=["created_at"],
                name="idx_notif_created",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.channel}:{self.recipient} "
            f"({self.get_status_display()})"
        )
