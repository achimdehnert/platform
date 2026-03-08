"""Module activation/deactivation services."""
from __future__ import annotations

import logging

from .catalogue import get_catalogue

logger = logging.getLogger(__name__)


def get_active_modules(tenant_id: str | None) -> set[str]:
    """Return set of active module codes for a tenant.

    Falls back to all modules if django_tenancy is not installed.
    """
    if not tenant_id:
        return set()
    try:
        from django_tenancy.module_models import ModuleSubscription

        return set(
            ModuleSubscription.objects.filter(
                tenant_id=tenant_id,
                status=ModuleSubscription.Status.ACTIVE,
            ).values_list("module", flat=True)
        )
    except Exception:  # noqa: BLE001
        return set(get_catalogue().keys())


def activate_module(organization, module_code: str, plan_code: str = "business"):
    """Activate or reactivate a module subscription for a tenant."""
    try:
        from django_tenancy.module_models import ModuleSubscription

        sub, created = ModuleSubscription.objects.get_or_create(
            tenant_id=organization.tenant_id,
            module=module_code,
            defaults={
                "organization": organization,
                "status": ModuleSubscription.Status.ACTIVE,
                "plan_code": plan_code,
            },
        )
        if not created and sub.status != ModuleSubscription.Status.ACTIVE:
            sub.status = ModuleSubscription.Status.ACTIVE
            sub.plan_code = plan_code
            sub.save(update_fields=["status", "plan_code", "updated_at"])
            logger.info("[module-shop] re-activated module=%s tenant=%s", module_code, organization.tenant_id)
        elif created:
            logger.info("[module-shop] activated module=%s tenant=%s", module_code, organization.tenant_id)
        return sub
    except Exception:  # noqa: BLE001
        logger.warning("[module-shop] activate_module skipped (no django_tenancy): module=%s", module_code)
        return None


def deactivate_module(organization, module_code: str):
    """Deactivate a module subscription for a tenant."""
    try:
        from django_tenancy.module_models import ModuleSubscription

        updated = ModuleSubscription.objects.filter(
            tenant_id=organization.tenant_id,
            module=module_code,
        ).update(status=ModuleSubscription.Status.INACTIVE)
        if updated:
            logger.info("[module-shop] deactivated module=%s tenant=%s", module_code, organization.tenant_id)
    except Exception:  # noqa: BLE001
        logger.warning("[module-shop] deactivate_module skipped (no django_tenancy): module=%s", module_code)
