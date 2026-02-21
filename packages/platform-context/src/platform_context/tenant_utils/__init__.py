"""
platform_context.tenant_utils — Multi-Tenancy Utilities (ADR-056)

Provides tenant-context propagation across all 3 communication channels:
  - REST/JSON APIs (TenantAwareHttpClient, TenantPropagationMiddleware)
  - Celery Tasks (TenantAwareTask, send_cross_service_task)
  - Test Fixtures (tenant_a, tenant_b, tenant_a_client)
  - Provisioning (provision_tenant)

Requires django-tenants to be installed in the consuming service.

Usage::

    from platform_context.tenant_utils.http_client import TenantAwareHttpClient
    from platform_context.tenant_utils.middleware import TenantPropagationMiddleware
    from platform_context.tenant_utils.celery import TenantAwareTask, send_cross_service_task
    from platform_context.tenant_utils.provisioning import provision_tenant

    # In conftest.py:
    from platform_context.tenant_utils.testing import tenant_a, tenant_b, tenant_a_client  # noqa: F401
"""

TENANT_HEADER: str = "X-Tenant-Schema"

__all__ = ["TENANT_HEADER"]
