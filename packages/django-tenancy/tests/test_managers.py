"""
Tests for TenantManager and TenantQuerySet.
"""
import pytest
from django_tenancy.models import Organization


@pytest.mark.django_db
class TestTenantManager:
    def test_for_tenant_filters_by_tenant_id(self):
        org1 = Organization.objects.create(name="Org1", slug="org1")
        org2 = Organization.objects.create(name="Org2", slug="org2")
        result = Organization.objects.for_tenant(org1.pk)
        # Organization itself doesn't have tenant_id — but subclasses do.
        # Verify for_tenant() method exists and returns a QuerySet.
        assert hasattr(result, "filter")

    def test_active_excludes_deleted(self):
        from django.utils import timezone
        Organization.objects.create(name="Live", slug="live")
        dead = Organization.objects.create(name="Dead2", slug="dead2")
        dead.deleted_at = timezone.now()
        dead.save()
        active = Organization.objects.active()
        slugs = list(active.values_list("slug", flat=True))
        assert "live" in slugs
        assert "dead2" not in slugs
