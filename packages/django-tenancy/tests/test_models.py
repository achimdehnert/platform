"""
Tests for Organization model and TenantModel.
"""
import pytest
from django.db import models

from django_tenancy.models import Organization, TenantModel


@pytest.mark.django_db
class TestOrganization:
    def test_create_organization(self):
        org = Organization.objects.create(name="ACME", slug="acme")
        assert org.pk is not None
        assert org.public_id is not None
        assert org.effective_subdomain == "acme"
        assert org.language == "de"

    def test_subdomain_override(self):
        org = Organization.objects.create(
            name="Test", slug="test", subdomain="custom"
        )
        assert org.effective_subdomain == "custom"

    def test_for_tenant_manager(self):
        org = Organization.objects.create(name="T1", slug="t1")
        found = Organization.objects.active().get(slug="t1")
        assert found.pk == org.pk

    def test_soft_delete_excluded_from_active(self):
        from django.utils import timezone
        org = Organization.objects.create(name="Dead", slug="dead")
        org.deleted_at = timezone.now()
        org.save()
        assert Organization.objects.active().filter(slug="dead").count() == 0


class TestTenantModelAbstract:
    def test_tenant_model_is_abstract(self):
        assert TenantModel._meta.abstract is True

    def test_tenant_id_is_bigintegerfield(self):
        field = TenantModel._meta.get_field("tenant_id")
        assert isinstance(field, models.BigIntegerField)

    def test_tenant_id_is_not_foreignkey(self):
        field = TenantModel._meta.get_field("tenant_id")
        assert not isinstance(field, models.ForeignKey)
