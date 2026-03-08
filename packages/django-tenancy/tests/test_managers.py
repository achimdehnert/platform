"""
Tests for TenantManager and TenantQuerySet.
"""
import pytest

from django_tenancy.models import Organization


@pytest.mark.django_db
class TestTenantManager:
    def test_for_tenant_method_exists(self):
        # Organization itself doesn't have tenant_id — but subclasses do.
        # Verify for_tenant() and active() methods exist on the manager.
        assert hasattr(Organization.objects, "for_tenant")
        assert hasattr(Organization.objects, "active")
        assert callable(Organization.objects.for_tenant)
        assert callable(Organization.objects.active)

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
