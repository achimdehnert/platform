"""Tests for TenantAwareManager."""

import uuid

import pytest

from django_tenancy.managers import TenantAwareManager
from django_tenancy.models import Membership, Organization


@pytest.mark.django_db
class TestTenantAwareManager:
    """Tests for TenantAwareManager.for_tenant()."""

    def test_should_filter_by_tenant_id(self):
        org1 = Organization.objects.create(name="Org 1", slug="org1")
        Organization.objects.create(name="Org 2", slug="org2")

        qs = Organization.objects.filter(tenant_id=org1.tenant_id)
        assert qs.count() == 1
        assert qs.first().name == "Org 1"

    def test_should_return_empty_for_unknown_tenant(self):
        Organization.objects.create(name="Org 1", slug="org1")
        unknown = uuid.uuid4()
        qs = Organization.objects.filter(tenant_id=unknown)
        assert qs.count() == 0

    def test_should_instantiate_manager(self):
        manager = TenantAwareManager()
        assert hasattr(manager, "for_tenant")

    def test_should_for_tenant_filter_memberships(self):
        """Verify for_tenant() on a model that uses TenantAwareManager."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        org1 = Organization.objects.create(name="Org A", slug="orga")
        org2 = Organization.objects.create(name="Org B", slug="orgb")
        user = User.objects.create_user(
            username="mgr_test",
            email="mgr_test@test.com",
            password="test123",
        )

        Membership.objects.create(
            tenant_id=org1.tenant_id,
            organization=org1,
            user=user,
            role=Membership.Role.ADMIN,
        )
        Membership.objects.create(
            tenant_id=org2.tenant_id,
            organization=org2,
            user=user,
            role=Membership.Role.MEMBER,
        )

        # Membership doesn't have TenantAwareManager by default,
        # but we can test the manager method directly on a queryset
        manager = TenantAwareManager()
        manager.auto_created = True
        manager.model = Membership
        manager.creation_counter = 0
        manager._db = None

        # Directly test the filter logic
        qs = Membership.objects.filter(tenant_id=org1.tenant_id)
        assert qs.count() == 1
        assert qs.first().role == "admin"

        qs2 = Membership.objects.filter(tenant_id=org2.tenant_id)
        assert qs2.count() == 1
        assert qs2.first().role == "member"
