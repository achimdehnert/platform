"""
Tenant model for multi-tenancy support.

Follows Platform principles:
- Database-First: All constraints in DB
- Zero Breaking Changes: Soft-Delete instead of Hard-Delete
- Spec vs. Derived: Only persist facts
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models import QuerySet


class TenantStatus(models.TextChoices):
    """
    Tenant lifecycle status.
    
    State Machine:
        TRIAL → ACTIVE → SUSPENDED → DELETED
                  ↓          ↑
                  └──────────┘
    """
    TRIAL = "trial", "Trial"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    DELETED = "deleted", "Deleted"


class TenantQuerySet(models.QuerySet["Tenant"]):
    """Custom QuerySet for tenant-specific queries."""
    
    def active(self) -> QuerySet[Tenant]:
        """Only active tenants (active + trial)."""
        return self.filter(status__in=[TenantStatus.ACTIVE, TenantStatus.TRIAL])
    
    def by_slug(self, slug: str) -> Tenant | None:
        """Tenant by slug."""
        return self.active().filter(slug=slug).first()


class TenantManager(models.Manager["Tenant"]):
    """Custom manager with QuerySet methods."""
    
    def get_queryset(self) -> TenantQuerySet:
        return TenantQuerySet(self.model, using=self._db)
    
    def active(self) -> QuerySet[Tenant]:
        return self.get_queryset().active()
    
    def by_slug(self, slug: str) -> Tenant | None:
        return self.get_queryset().by_slug(slug)


class Tenant(models.Model):
    """
    Central tenant model for multi-tenancy.
    
    Design decisions:
    - UUID as PK: Prevents ID guessing
    - Slug for URLs: Human-readable, immutable
    - FK to Plan: Normalized, not string
    - Soft-Delete: status=DELETED
    
    Example:
        tenant = Tenant.objects.create(
            slug="acme-corp",
            name="ACME Corporation",
            plan_code="professional",
        )
    """
    
    # ══════════════════════════════════════════════════════════════════════════
    # IDENTITY
    # ══════════════════════════════════════════════════════════════════════════
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique tenant ID (UUID v4)",
    )
    
    slug = models.SlugField(
        max_length=63,
        unique=True,
        db_index=True,
        help_text="URL-friendly identifier for subdomains",
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Organization display name",
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ══════════════════════════════════════════════════════════════════════════
    
    status = models.CharField(
        max_length=20,
        choices=TenantStatus.choices,
        default=TenantStatus.TRIAL,
        db_index=True,
    )
    
    trial_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End of trial period",
    )
    
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_reason = models.TextField(blank=True, default="")
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # ══════════════════════════════════════════════════════════════════════════
    # PLAN (FK to normalized table)
    # ══════════════════════════════════════════════════════════════════════════
    
    plan = models.ForeignKey(
        "bfagent_core.Plan",
        on_delete=models.PROTECT,
        default="free",
        related_name="tenants",
        help_text="Subscription plan",
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # SETTINGS (OK for non-critical config)
    # ══════════════════════════════════════════════════════════════════════════
    
    settings = models.JSONField(
        default=dict,
        help_text="{'timezone': 'Europe/Berlin', 'locale': 'de-DE'}",
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # BILLING (Optional)
    # ══════════════════════════════════════════════════════════════════════════
    
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # METADATA
    # ══════════════════════════════════════════════════════════════════════════
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TenantManager()
    
    class Meta:
        db_table = "core_tenant"
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(status__in=["trial", "active", "suspended", "deleted"]),
                name="tenant_status_chk",
            ),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"
    
    # ══════════════════════════════════════════════════════════════════════════
    # PROPERTIES (Derived)
    # ══════════════════════════════════════════════════════════════════════════
    
    @property
    def is_active(self) -> bool:
        return self.status in (TenantStatus.ACTIVE, TenantStatus.TRIAL)
    
    @property
    def is_trial(self) -> bool:
        return self.status == TenantStatus.TRIAL
    
    @property
    def is_trial_expired(self) -> bool:
        if not self.is_trial or not self.trial_ends_at:
            return False
        return timezone.now() > self.trial_ends_at
    
    # ══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE METHODS
    # ══════════════════════════════════════════════════════════════════════════
    
    def activate(self) -> None:
        """Trial/Suspended → Active."""
        if self.status not in (TenantStatus.TRIAL, TenantStatus.SUSPENDED):
            raise ValueError(f"Cannot activate from status {self.status}")
        
        self.status = TenantStatus.ACTIVE
        self.trial_ends_at = None
        self.suspended_at = None
        self.suspended_reason = ""
        self.save(update_fields=[
            "status", "trial_ends_at", "suspended_at", 
            "suspended_reason", "updated_at"
        ])
    
    def suspend(self, reason: str = "") -> None:
        """Suspend the tenant."""
        if self.status == TenantStatus.DELETED:
            raise ValueError("Cannot suspend deleted tenant")
        
        self.status = TenantStatus.SUSPENDED
        self.suspended_at = timezone.now()
        self.suspended_reason = reason
        self.save(update_fields=[
            "status", "suspended_at", "suspended_reason", "updated_at"
        ])
    
    def soft_delete(self) -> None:
        """Soft-delete (data remains for compliance)."""
        self.status = TenantStatus.DELETED
        self.deleted_at = timezone.now()
        self.save(update_fields=["status", "deleted_at", "updated_at"])
    
    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.save(update_fields=["settings", "updated_at"])
