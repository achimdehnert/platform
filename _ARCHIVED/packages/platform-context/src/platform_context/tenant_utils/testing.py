"""
Tenant test fixtures — ADR-074 (Multi-Tenancy Testing Strategy).

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

from typing import Any, Generator

import pytest


@pytest.fixture
def tenant_a(db: None) -> Generator[Any, None, None]:
    """
    Creates Tenant A for multi-tenant tests.
    Drops the schema on teardown to prevent test pollution.
    """
    from django.db import connection
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
    yield tenant
    with connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS test_tenant_a CASCADE")


@pytest.fixture
def tenant_b(db: None) -> Generator[Any, None, None]:
    """
    Creates Tenant B for isolation tests.
    Use together with tenant_a to verify cross-tenant data isolation.
    Drops the schema on teardown to prevent test pollution.
    """
    from django.db import connection
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
    yield tenant
    with connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS test_tenant_b CASCADE")


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
