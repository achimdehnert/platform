"""Tests for Organization and Membership models."""

import pytest
from django.contrib.auth import get_user_model

from django_tenancy.models import Membership, Organization

User = get_user_model()


@pytest.mark.django_db
class TestOrganization:
    """Tests for Organization model."""

    def test_should_create_organization_with_defaults(self):
        org = Organization.objects.create(name="Acme Corp", slug="acme")
        assert org.name == "Acme Corp"
        assert org.slug == "acme"
        assert org.status == Organization.Status.TRIAL
        assert org.plan_code == "free"
        assert org.tenant_id is not None
        assert org.id != org.tenant_id

    def test_should_have_unique_tenant_id(self):
        org1 = Organization.objects.create(name="Org 1", slug="org1")
        org2 = Organization.objects.create(name="Org 2", slug="org2")
        assert org1.tenant_id != org2.tenant_id

    def test_should_have_unique_slug(self):
        Organization.objects.create(name="Org 1", slug="same-slug")
        with pytest.raises(Exception):
            Organization.objects.create(name="Org 2", slug="same-slug")

    def test_should_report_active_for_trial(self):
        org = Organization(status=Organization.Status.TRIAL)
        assert org.is_active is True

    def test_should_report_active_for_active(self):
        org = Organization(status=Organization.Status.ACTIVE)
        assert org.is_active is True

    def test_should_report_inactive_for_suspended(self):
        org = Organization(status=Organization.Status.SUSPENDED)
        assert org.is_active is False

    def test_should_report_inactive_for_deleted(self):
        org = Organization(status=Organization.Status.DELETED)
        assert org.is_active is False

    def test_should_str_return_name(self):
        org = Organization(name="Test Org")
        assert str(org) == "Test Org"


@pytest.mark.django_db
class TestMembership:
    """Tests for Membership model."""

    def test_should_create_membership(self):
        org = Organization.objects.create(name="Acme", slug="acme")
        user = User.objects.create_user(username="alice", password="test")
        membership = Membership.objects.create(
            tenant_id=org.tenant_id,
            organization=org,
            user=user,
            role=Membership.Role.ADMIN,
        )
        assert membership.role == "admin"
        assert membership.tenant_id == org.tenant_id

    def test_should_enforce_unique_per_tenant_user(self):
        org = Organization.objects.create(name="Acme", slug="acme")
        user = User.objects.create_user(username="bob", password="test")
        Membership.objects.create(
            tenant_id=org.tenant_id,
            organization=org,
            user=user,
        )
        with pytest.raises(Exception):
            Membership.objects.create(
                tenant_id=org.tenant_id,
                organization=org,
                user=user,
            )

    def test_should_default_to_member_role(self):
        org = Organization.objects.create(name="Acme", slug="acme")
        user = User.objects.create_user(username="carol", password="test")
        m = Membership.objects.create(
            tenant_id=org.tenant_id,
            organization=org,
            user=user,
        )
        assert m.role == Membership.Role.MEMBER
