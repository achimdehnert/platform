"""
Tenant test fixtures — ADR-056 §9.2.

pytest fixtures for multi-tenant tests. Requires django-tenants.

Usage in conftest.py::

    from platform_context.tenant_utils.testing import (  # noqa: F401
        tenant_a,
        tenant_b,
        tenant_a_client,
        tenant_b_client,
    )

Usage in tests::

    @pytest.mark.django_db(transaction=True)
    def test_should_isolate_tenant_data(tenant_a, tenant_b):
        from django_tenants.utils import schema_context
        from apps.core.models import MyModel

        with schema_context(tenant_a.schema_name):
            MyModel.objects.create(title="Secret A")

        with schema_context(tenant_b.schema_name):
            assert MyModel.objects.count() == 0
"""

from __future__ import annotations

import pytest


@pytest.fixture
def tenant_a(db: None) -> Any:
    """
    Creates Tenant A for multi-tenant tests.
    Requires django-tenants Client and Domain models.
    """
    from django_tenants.test.cases import TenantTestCase  # noqa: F401
    from tenants.models import Client, Domain

    tenant = Client(
        schema_name="test_tenant_a",
        name="Test Tenant A",
    )
    tenant.save(verbosity=0)
    Domain.objects.create(
        domain="tenant-a.test.localhost",
        tenant=tenant,
        is_primary=True,
    )
    return tenant


@pytest.fixture
def tenant_b(db: None) -> Any:
    """
    Creates Tenant B for isolation tests.
    Use together with tenant_a to verify cross-tenant data isolation.
    """
    from tenants.models import Client, Domain

    tenant = Client(
        schema_name="test_tenant_b",
        name="Test Tenant B",
    )
    tenant.save(verbosity=0)
    Domain.objects.create(
        domain="tenant-b.test.localhost",
        tenant=tenant,
        is_primary=True,
    )
    return tenant


@pytest.fixture
def tenant_a_client(tenant_a: Any) -> Any:
    """Django TenantClient in the context of Tenant A."""
    from django_tenants.test.client import TenantClient
    return TenantClient(tenant_a)


@pytest.fixture
def tenant_b_client(tenant_b: Any) -> Any:
    """Django TenantClient in the context of Tenant B."""
    from django_tenants.test.client import TenantClient
    return TenantClient(tenant_b)


from typing import Any
