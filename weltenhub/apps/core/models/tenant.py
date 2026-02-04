"""
Weltenhub Tenant-Aware Model
============================

Provides tenant isolation for all data models.
All tenant-specific data inherits from TenantAwareModel.
"""

from django.db import models

from .base import AuditableSoftDeleteModel


class TenantAwareManager(models.Manager):
    """
    Manager that automatically filters by current tenant.

    Requires TenantMiddleware to set the current tenant.
    """

    def get_queryset(self):
        """Filter queryset by current tenant from thread-local storage."""
        from apps.core.middleware.tenant import get_current_tenant

        qs = super().get_queryset().filter(deleted_at__isnull=True)
        tenant = get_current_tenant()
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs

    def for_tenant(self, tenant):
        """Explicitly filter by a specific tenant."""
        return super().get_queryset().filter(
            deleted_at__isnull=True,
            tenant=tenant
        )


class TenantAwareModel(AuditableSoftDeleteModel):
    """
    Abstract base model for tenant-isolated data.

    All models that should be isolated per tenant should inherit from this.
    The tenant is automatically set on save if not provided.

    Attributes:
        tenant: Foreign key to the Tenant model
    """

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        help_text="Tenant this record belongs to"
    )

    objects = TenantAwareManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Override save to automatically set tenant if not provided.

        Uses current tenant from thread-local storage.
        """
        if not self.tenant_id:
            from apps.core.middleware.tenant import get_current_tenant
            tenant = get_current_tenant()
            if tenant:
                self.tenant = tenant
        super().save(*args, **kwargs)
