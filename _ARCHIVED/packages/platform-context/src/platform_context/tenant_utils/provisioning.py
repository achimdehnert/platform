"""
Tenant provisioning helpers — ADR-056 Phase 3.

Provides provision_tenant() which creates a tenant schema in ALL service
databases by dispatching Celery tasks to each registered service.

This is a coordination helper — each service must implement the
`provision_tenant_schema` Celery task that actually creates the local schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TenantProvisioningRequest:
    """
    Data required to provision a new tenant across all services.

    Attributes:
        schema_name: PostgreSQL schema name (lowercase, underscores only)
        name: Human-readable tenant name
        company_name: Legal company name
        contact_email: Primary contact email
        plan: Subscription plan (default: "basic")
        max_users: Maximum users for this tenant (default: 5)
        data_region: Data residency region (default: "eu-de")
        domains: List of domain strings to register
    """

    schema_name: str
    name: str
    company_name: str
    contact_email: str
    plan: str = "basic"
    max_users: int = 5
    data_region: str = "eu-de"
    domains: list[str] = field(default_factory=list)


def provision_tenant(
    request: TenantProvisioningRequest,
    services: list[str] | None = None,
) -> dict[str, Any]:
    """
    Provision a new tenant in the local service DB and dispatch provisioning
    tasks to all other registered services.

    Args:
        request: TenantProvisioningRequest with tenant data
        services: List of service names to notify (default: all registered)

    Returns:
        dict with 'local' (tenant object) and 'dispatched' (list of task IDs)

    Raises:
        ValueError: If schema_name contains invalid characters
        RuntimeError: If local tenant creation fails

    Usage::

        from platform_context.tenant_utils.provisioning import (
            TenantProvisioningRequest,
            provision_tenant,
        )

        req = TenantProvisioningRequest(
            schema_name="acme_corp",
            name="ACME Corporation",
            company_name="ACME Corp GmbH",
            contact_email="admin@acme-corp.de",
            domains=["acme.bfa.example.com"],
        )
        result = provision_tenant(req)
    """
    _validate_schema_name(request.schema_name)

    tenant = _create_local_tenant(request)
    task_ids = _dispatch_to_services(request, services or [])

    return {
        "local": tenant,
        "dispatched": task_ids,
        "schema_name": request.schema_name,
    }


def _validate_schema_name(schema_name: str) -> None:
    """Validate schema name — only lowercase letters, digits, underscores."""
    safe_chars = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")
    if not schema_name or not all(c in safe_chars for c in schema_name):
        raise ValueError(
            f"Invalid schema_name '{schema_name}': "
            "only lowercase letters, digits and underscores allowed."
        )
    if schema_name.startswith("pg_") or schema_name == "public":
        raise ValueError(
            f"Reserved schema_name '{schema_name}': "
            "cannot use PostgreSQL reserved names."
        )


def _create_local_tenant(request: TenantProvisioningRequest) -> Any:
    """Create tenant in the local service database via django-tenants."""
    try:
        from tenants.models import Client, Domain
    except ImportError as exc:
        raise RuntimeError(
            "django-tenants Client/Domain models not found. "
            "Ensure 'tenants' app is in INSTALLED_APPS."
        ) from exc

    tenant = Client(
        schema_name=request.schema_name,
        name=request.name,
    )
    if hasattr(tenant, "company_name"):
        tenant.company_name = request.company_name
    if hasattr(tenant, "contact_email"):
        tenant.contact_email = request.contact_email
    if hasattr(tenant, "plan"):
        tenant.plan = request.plan
    if hasattr(tenant, "max_users"):
        tenant.max_users = request.max_users
    if hasattr(tenant, "data_region"):
        tenant.data_region = request.data_region

    tenant.save()

    for i, domain_str in enumerate(request.domains):
        Domain.objects.create(
            domain=domain_str,
            tenant=tenant,
            is_primary=(i == 0),
        )

    return tenant


def _dispatch_to_services(
    request: TenantProvisioningRequest,
    services: list[str],
) -> list[str]:
    """Dispatch provisioning tasks to other services via Celery."""
    if not services:
        return []

    from celery import current_app

    task_ids = []
    payload = {
        "schema_name": request.schema_name,
        "name": request.name,
        "company_name": request.company_name,
        "contact_email": request.contact_email,
        "plan": request.plan,
        "max_users": request.max_users,
        "data_region": request.data_region,
        "domains": request.domains,
    }

    for service in services:
        result = current_app.send_task(
            f"{service}.tasks.provision_tenant_schema",
            kwargs=payload,
        )
        task_ids.append(str(result.id))

    return task_ids
