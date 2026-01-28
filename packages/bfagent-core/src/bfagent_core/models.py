"""
Core Django models for bfagent-core.

These models are designed to be used across all BFAgent hubs.
Each hub should run migrations for these models in their own database.
"""

import uuid
from django.db import models


class AuditEvent(models.Model):
    """
    Audit trail for compliance-relevant mutations.
    
    Every write operation that affects risk-relevant data should
    create an AuditEvent record.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    actor_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    category = models.CharField(max_length=80, db_index=True)
    action = models.CharField(max_length=80, db_index=True)
    entity_type = models.CharField(max_length=120, db_index=True)
    entity_id = models.UUIDField(db_index=True)
    
    payload = models.JSONField(default=dict)
    request_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = "bfagent_core_audit_event"
        indexes = [
            models.Index(fields=["tenant_id", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["tenant_id", "category", "action"]),
        ]
        ordering = ["-created_at"]
    
    def __str__(self) -> str:
        return f"{self.category}.{self.action} on {self.entity_type}:{self.entity_id}"


class OutboxMessage(models.Model):
    """
    Transactional outbox for reliable event publishing.
    
    Events are written here within the same transaction as the
    business operation, then published by a background worker.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    topic = models.CharField(max_length=120, db_index=True)
    payload = models.JSONField(default=dict)
    
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = "bfagent_core_outbox_message"
        indexes = [
            models.Index(fields=["tenant_id", "published_at", "created_at"]),
            models.Index(fields=["topic", "created_at"]),
        ]
        ordering = ["created_at"]
    
    def __str__(self) -> str:
        status = "published" if self.published_at else "pending"
        return f"{self.topic} ({status})"
    
    @property
    def is_published(self) -> bool:
        return self.published_at is not None
