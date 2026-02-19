"""Tests for ModuleSubscription and ModuleMembership models."""

import pytest
from django.contrib.auth import get_user_model

from django_tenancy.models import Organization
from django_tenancy.module_models import ModuleMembership, ModuleSubscription

User = get_user_model()


@pytest.fixture
def org(db):
    return Organization.objects.create(slug="acme", name="Acme GmbH", status="active")


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", password="pw")


@pytest.fixture
def subscription(db, org):
    return ModuleSubscription.objects.create(
        organization=org,
        tenant_id=org.tenant_id,
        module="risk",
        status=ModuleSubscription.Status.ACTIVE,
    )


@pytest.fixture
def membership(db, org, user):
    return ModuleMembership.objects.create(
        tenant_id=org.tenant_id,
        user=user,
        module="risk",
        role=ModuleMembership.Role.MEMBER,
    )


class TestModuleSubscription:
    def test_create(self, subscription):
        assert subscription.module == "risk"
        assert subscription.status == "active"
        assert subscription.is_accessible is True

    def test_suspended_not_accessible(self, org, db):
        sub = ModuleSubscription.objects.create(
            organization=org,
            tenant_id=org.tenant_id,
            module="dsb",
            status=ModuleSubscription.Status.SUSPENDED,
        )
        assert sub.is_accessible is False

    def test_trial_is_accessible(self, org, db):
        sub = ModuleSubscription.objects.create(
            organization=org,
            tenant_id=org.tenant_id,
            module="ex",
            status=ModuleSubscription.Status.TRIAL,
        )
        assert sub.is_accessible is True

    def test_unique_per_tenant_module(self, subscription, org, db):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ModuleSubscription.objects.create(
                organization=org,
                tenant_id=org.tenant_id,
                module="risk",
                status="active",
            )

    def test_for_tenant_manager(self, subscription, org, db):
        other_org = Organization.objects.create(
            slug="other", name="Other GmbH", status="active",
        )
        ModuleSubscription.objects.create(
            organization=other_org,
            tenant_id=other_org.tenant_id,
            module="risk",
            status="active",
        )
        qs = ModuleSubscription.objects.for_tenant(org.tenant_id)
        assert qs.count() == 1
        assert qs.first().organization == org

    def test_str(self, subscription):
        assert "risk" in str(subscription)
        assert "active" in str(subscription)


class TestModuleMembership:
    def test_create(self, membership):
        assert membership.module == "risk"
        assert membership.role == "member"

    def test_unique_per_tenant_user_module(self, membership, org, user, db):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ModuleMembership.objects.create(
                tenant_id=org.tenant_id,
                user=user,
                module="risk",
                role="viewer",
            )

    def test_different_modules_allowed(self, membership, org, user, db):
        m2 = ModuleMembership.objects.create(
            tenant_id=org.tenant_id,
            user=user,
            module="dsb",
            role="admin",
        )
        assert m2.module == "dsb"

    def test_for_tenant_manager(self, membership, org, db):
        other_user = User.objects.create_user(username="bob", password="pw")
        other_org = Organization.objects.create(
            slug="other2", name="Other2 GmbH", status="active",
        )
        ModuleMembership.objects.create(
            tenant_id=other_org.tenant_id,
            user=other_user,
            module="risk",
            role="viewer",
        )
        qs = ModuleMembership.objects.for_tenant(org.tenant_id)
        assert qs.count() == 1

    def test_str(self, membership):
        assert "risk" in str(membership)
        assert "member" in str(membership)
