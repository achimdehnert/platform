"""
Weltenhub Base Models
=====================

Abstract base models providing common functionality:
- TimestampedModel: created_at, updated_at
- AuditableSoftDeleteModel: + deleted_at, created_by, updated_by

All models in Weltenhub should inherit from these base classes.
"""

import uuid
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    """
    Abstract base model with automatic timestamps.
    
    Attributes:
        created_at: Timestamp when record was created (auto)
        updated_at: Timestamp when record was last updated (auto)
    """
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when record was last updated"
    )
    
    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SoftDeleteManager(models.Manager):
    """
    Manager that filters out soft-deleted records by default.
    
    Use .all_with_deleted() to include deleted records.
    Use .deleted_only() to get only deleted records.
    """
    
    def get_queryset(self) -> models.QuerySet:
        """Return only non-deleted records."""
        return super().get_queryset().filter(deleted_at__isnull=True)
    
    def all_with_deleted(self) -> models.QuerySet:
        """Return all records including deleted ones."""
        return super().get_queryset()
    
    def deleted_only(self) -> models.QuerySet:
        """Return only soft-deleted records."""
        return super().get_queryset().filter(deleted_at__isnull=False)


class AuditableSoftDeleteModel(TimestampedModel):
    """
    Abstract base model with soft delete and audit fields.
    
    Provides:
    - Soft delete functionality (deleted_at timestamp)
    - Audit trail (created_by, updated_by)
    - UUID primary key for external references
    
    Attributes:
        id: UUID primary key
        deleted_at: Timestamp when soft-deleted (null if active)
        created_by: User who created the record
        updated_by: User who last updated the record
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier (UUID)"
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when soft-deleted (null if active)"
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
        help_text="User who created this record"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
        help_text="User who last updated this record"
    )
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()
    
    class Meta:
        abstract = True
        ordering = ["-created_at"]
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None
    
    def soft_delete(self, user: Optional[settings.AUTH_USER_MODEL] = None) -> None:
        """
        Soft delete this record.
        
        Sets deleted_at to current timestamp.
        Does not actually remove from database.
        
        Args:
            user: User performing the deletion (for audit)
        """
        self.deleted_at = timezone.now()
        if user:
            self.updated_by = user
        self.save(update_fields=["deleted_at", "updated_by", "updated_at"])
    
    def restore(self, user: Optional[settings.AUTH_USER_MODEL] = None) -> None:
        """
        Restore a soft-deleted record.
        
        Clears deleted_at timestamp.
        
        Args:
            user: User performing the restoration (for audit)
        """
        self.deleted_at = None
        if user:
            self.updated_by = user
        self.save(update_fields=["deleted_at", "updated_by", "updated_at"])
    
    def hard_delete(self) -> None:
        """
        Permanently delete this record from database.
        
        WARNING: This cannot be undone!
        """
        super().delete()
    
    def delete(self, *args, **kwargs) -> None:
        """
        Override delete to perform soft delete by default.
        
        Use hard_delete() for permanent deletion.
        """
        self.soft_delete()
