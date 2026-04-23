"""Tests for TenantManager dual-mode auto-filter (ADR-137)."""

import uuid

import pytest
from django.contrib.auth import get_user_model

from django_tenancy.context import clear_context, set_tenant
from django_tenancy.managers import TenantQuerySet
from django_tenancy.models import Organization
from django_tenancy.module_models import ModuleSubscription

User = get_user_model()


@pytest.fixture
def org_a():
    return Organization.objects.create(name="Org A", slug="orga")


@pytest.fixture
def org_b():
    return Organization.objects.create(name="Org B", slug="orgb")


@pytest.fixture
def user_a():
    return User.objects.create_user(
        username="user_a", email="a@test.com", password="test123"
    )


@pytest.fixture
def subs(org_a, org_b):
    """Create module subscriptions for both orgs."""
    s1 = ModuleSubscription.objects.create(
        organization=org_a,
        tenant_id=org_a.tenant_id,
        module="risk",
        status=ModuleSubscription.Status.ACTIVE,
    )
    s2 = ModuleSubscription.objects.create(
        organization=org_b,
        tenant_id=org_b.tenant_id,
        module="dsb",
        status=ModuleSubscription.Status.ACTIVE,
    )
    return s1, s2


@pytest.mark.django_db
class TestTenantManagerAutoFilter:
    """Test TenantManager context-based auto-filtering."""

    def teardown_method(self):
        clear_context()

    def test_should_auto_filter_when_context_set(self, org_a, org_b, subs):
        set_tenant(org_a.tenant_id, "orga")
        qs = ModuleSubscription.objects.all()
        assert qs.count() == 1
        assert qs.first().module == "risk"

    def test_should_return_all_when_no_context(self, org_a, org_b, subs):
        qs = ModuleSubscription.objects.all()
        assert qs.count() == 2

    def test_should_for_tenant_bypass_context(self, org_a, org_b, subs):
        set_tenant(org_a.tenant_id, "orga")
        qs = ModuleSubscription.objects.for_tenant(org_b.tenant_id)
        assert qs.count() == 1
        assert qs.first().module == "dsb"

    def test_should_unscoped_bypass_context(self, org_a, org_b, subs):
        set_tenant(org_a.tenant_id, "orga")
        qs = ModuleSubscription.objects.unscoped()
        assert qs.count() == 2

    def test_should_return_tenant_queryset(self, org_a, subs):
        qs = ModuleSubscription.objects.all()
        assert isinstance(qs, TenantQuerySet)

    def test_should_chain_filter_with_auto_filter(self, org_a, org_b, subs):
        set_tenant(org_a.tenant_id, "orga")
        qs = ModuleSubscription.objects.filter(
            status=ModuleSubscription.Status.ACTIVE
        )
        assert qs.count() == 1
        assert qs.first().tenant_id == org_a.tenant_id

    def test_should_queryset_unscoped_bypass(self, org_a, org_b, subs):
        set_tenant(org_a.tenant_id, "orga")
        qs = ModuleSubscription.objects.all()
        assert qs.count() == 1
        unscoped = qs.unscoped()
        assert unscoped.count() == 2


@pytest.mark.django_db
class TestTenantManagerForTenant:
    """Test explicit for_tenant() method."""

    def test_should_filter_by_explicit_tenant(self, org_a, org_b, subs):
        qs = ModuleSubscription.objects.for_tenant(org_a.tenant_id)
        assert qs.count() == 1
        assert qs.first().module == "risk"

    def test_should_return_empty_for_unknown_tenant(self, subs):
        qs = ModuleSubscription.objects.for_tenant(uuid.uuid4())
        assert qs.count() == 0
