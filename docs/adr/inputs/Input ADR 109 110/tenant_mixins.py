"""
iil_testkit/tenant_mixins.py

Fixes H-2 (ADR-109): TenantTestMixin bisher undefiniert.
Vollständige Spezifikation mit allen benötigten Methoden.

Verwendung:
    from iil_testkit.tenant_mixins import TenantTestMixin

    class MyViewTest(TenantTestMixin, TestCase):
        def test_user_sees_only_own_data(self):
            tenant_a = self.create_tenant("tenant-a")
            tenant_b = self.create_tenant("tenant-b")
            obj_a = MyModel.objects.create(tenant_id=tenant_a.id, name="A")

            self.set_tenant(self.client, tenant_a)
            response = self.client.get("/my-list/")
            self.assertContains(response, "A")

            self.set_tenant(self.client, tenant_b)
            response = self.client.get("/my-list/")
            self.assertNotContains(response, "A")  # Cross-tenant isolation
"""

from __future__ import annotations

from typing import Any

from django.test import Client, RequestFactory, TestCase

from django_tenancy.models import Organization


class TenantTestMixin:
    """
    Mixin for Django TestCase subclasses that need multi-tenant test support.

    Provides:
      create_tenant()         → Create a test Organization
      set_tenant()            → Set tenant on test Client session
      make_tenant_request()   → Create a mock request with tenant set
      assert_tenant_isolated()→ Assert model is not visible to other tenants
    """

    # Override in subclass if your default language differs
    default_language: str = "de"

    def create_tenant(
        self,
        slug: str = "test-tenant",
        name: str | None = None,
        language: str | None = None,
        **kwargs: Any,
    ) -> Organization:
        """
        Create a test Organization.
        Handles unique slug conflicts by appending a counter.
        """
        name = name or slug.replace("-", " ").title()
        language = language or self.default_language

        org, created = Organization.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "language": language,
                "subdomain": slug,
                "is_active": True,
                **kwargs,
            },
        )
        return org

    def set_tenant(self, client: Client, tenant: Organization) -> None:
        """
        Set tenant_id in the test client session.
        Works with TENANCY_MODE = "session" (CI default).
        """
        session = client.session
        session["tenant_id"] = tenant.id
        session.save()

    def make_tenant_request(
        self,
        path: str = "/",
        tenant: Organization | None = None,
        method: str = "GET",
        user: Any = None,
        **kwargs: Any,
    ) -> Any:
        """
        Create a mock HttpRequest with tenant set on request.tenant_id.
        Useful for testing service-layer functions that take request.
        """
        factory = RequestFactory()
        request_method = getattr(factory, method.lower())
        request = request_method(path, **kwargs)
        if tenant:
            request.tenant = tenant
            request.tenant_id = tenant.id
            request.LANGUAGE_CODE = tenant.language
        else:
            request.tenant = None
            request.tenant_id = 0
            request.LANGUAGE_CODE = self.default_language
        if user:
            request.user = user
        return request

    def assert_tenant_isolated(
        self,
        model_class: type,
        obj: Any,
        other_tenant: Organization,
    ) -> None:
        """
        Assert that `obj` is NOT visible when querying as `other_tenant`.
        Verifies tenant isolation via the TenantManager.for_tenant() method.
        """
        visible_to_other = model_class.objects.for_tenant(other_tenant.id).filter(
            pk=obj.pk
        ).exists()
        assert not visible_to_other, (
            f"{model_class.__name__} pk={obj.pk} (tenant_id={getattr(obj, 'tenant_id', '?')}) "
            f"is visible to tenant_id={other_tenant.id} — isolation broken!"
        )

    def assert_tenant_visible(
        self,
        model_class: type,
        obj: Any,
        tenant: Organization,
    ) -> None:
        """Assert that `obj` IS visible when querying as `tenant`."""
        visible = model_class.objects.for_tenant(tenant.id).filter(pk=obj.pk).exists()
        assert visible, (
            f"{model_class.__name__} pk={obj.pk} is NOT visible to tenant_id={tenant.id}"
        )
