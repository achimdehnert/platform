"""
Tenant model for multi-tenancy support.

Folgt den Platform-Prinzipien:
- Database-First: Alle Constraints in DB
- Zero Breaking Changes: Soft-Delete statt Hard-Delete
- Spec vs. Derived: Nur Fakten persistieren
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
    Tenant-Lifecycle-Status.
    
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
    """Custom QuerySet für Tenant-spezifische Queries."""
    
    def active(self) -> QuerySet[Tenant]:
        """Nur aktive Tenants (active + trial)."""
        return self.filter(status__in=[TenantStatus.ACTIVE, TenantStatus.TRIAL])
    
    def by_slug(self, slug: str) -> Tenant | None:
        """Tenant by Slug."""
        return self.active().filter(slug=slug).first()


class TenantManager(models.Manager["Tenant"]):
    """Custom Manager mit QuerySet-Methoden."""
    
    def get_queryset(self) -> TenantQuerySet:
        return TenantQuerySet(self.model, using=self._db)
    
    def active(self) -> QuerySet[Tenant]:
        return self.get_queryset().active()
    
    def by_slug(self, slug: str) -> Tenant | None:
        return self.get_queryset().by_slug(slug)


class Tenant(models.Model):
    """
    Zentrales Tenant-Model für Multi-Tenancy.
    
    Design-Entscheidungen:
    - UUID als PK: Verhindert ID-Guessing
    - Slug für URLs: Menschenlesbar, immutable
    - JSON-Felder: quotas, features, settings
    - Soft-Delete: status=DELETED
    
    Beispiel:
        tenant = Tenant.objects.create(
            slug="acme-corp",
            name="ACME Corporation",
            plan_code="professional",
        )
    """
    
    # ══════════════════════════════════════════════════════════════════════════
    # IDENTITÄT
    # ══════════════════════════════════════════════════════════════════════════
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Eindeutige Tenant-ID (UUID v4)",
    )
    
    slug = models.SlugField(
        max_length=63,
        unique=True,
        db_index=True,
        help_text="URL-freundlicher Identifier für Subdomains",
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Anzeigename der Organisation",
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
        help_text="Ende der Trial-Periode",
    )
    
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_reason = models.TextField(blank=True, default="")
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # ══════════════════════════════════════════════════════════════════════════
    # PLAN & QUOTAS
    # ══════════════════════════════════════════════════════════════════════════
    
    plan_code = models.CharField(
        max_length=50,
        default="free",
        db_index=True,
        help_text="Plan: free, professional, enterprise",
    )
    
    quotas = models.JSONField(
        default=dict,
        help_text="{'api_calls_monthly': 10000, 'storage_mb': 1000}",
    )
    
    features = models.JSONField(
        default=dict,
        help_text="{'ai_generation': true, 'export_pdf': false}",
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
    # SETTINGS
    # ══════════════════════════════════════════════════════════════════════════
    
    settings = models.JSONField(
        default=dict,
        help_text="{'timezone': 'Europe/Berlin', 'locale': 'de-DE'}",
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # METADATA
    # ══════════════════════════════════════════════════════════════════════════
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TenantManager()
    
    class Meta:
        db_table = "bfagent_core_tenant"
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
        ordering = ["name"]
    
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
        """Suspendiert den Tenant."""
        if self.status == TenantStatus.DELETED:
            raise ValueError("Cannot suspend deleted tenant")
        
        self.status = TenantStatus.SUSPENDED
        self.suspended_at = timezone.now()
        self.suspended_reason = reason
        self.save(update_fields=[
            "status", "suspended_at", "suspended_reason", "updated_at"
        ])
    
    def soft_delete(self) -> None:
        """Soft-Delete (Daten bleiben für Compliance)."""
        self.status = TenantStatus.DELETED
        self.deleted_at = timezone.now()
        self.save(update_fields=["status", "deleted_at", "updated_at"])
    
    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    
    def get_quota(self, key: str, default: int = 0) -> int:
        return self.quotas.get(key, default)
    
    def has_feature(self, feature: str) -> bool:
        return self.features.get(feature, False)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)
