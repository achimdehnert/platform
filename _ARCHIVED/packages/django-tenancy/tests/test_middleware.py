"""Tests for SubdomainTenantMiddleware."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from django_tenancy.context import clear_context
from django_tenancy.middleware import SubdomainTenantMiddleware
from django_tenancy.models import Membership, Organization

User = get_user_model()


@pytest.mark.django_db
class TestSubdomainTenantMiddleware:
    """Tests for subdomain-based tenant resolution."""

    def setup_method(self):
        clear_context()
        self.factory = RequestFactory()
        self.middleware = SubdomainTenantMiddleware(get_response=lambda r: r)

    def teardown_method(self):
        clear_context()

    def test_should_skip_health_paths(self):
        request = self.factory.get("/livez/")
        result = self.middleware.process_request(request)
        assert result is None
        assert request.tenant_id is None

    def test_should_skip_healthz_path(self):
        request = self.factory.get("/healthz/")
        result = self.middleware.process_request(request)
        assert result is None
        assert request.tenant_id is None

    def test_should_resolve_from_subdomain(self):
        org = Organization.objects.create(
            name="Acme",
            slug="acme",
            status="active",
        )
        request = self.factory.get(
            "/",
            HTTP_HOST="acme.example.com",
        )
        result = self.middleware.process_request(request)
        assert result is None
        assert request.tenant_id == org.tenant_id
        assert request.tenant.name == "Acme"
        assert request.tenant_slug == "acme"

    def test_should_resolve_from_header(self):
        org = Organization.objects.create(
            name="Beta",
            slug="beta",
            status="trial",
        )
        request = self.factory.get(
            "/",
            HTTP_HOST="example.com",
            HTTP_X_TENANT_ID=str(org.tenant_id),
        )
        result = self.middleware.process_request(request)
        assert result is None
        assert request.tenant_id == org.tenant_id

    def test_should_handle_unknown_subdomain(self):
        request = self.factory.get(
            "/",
            HTTP_HOST="unknown.example.com",
        )
        result = self.middleware.process_request(request)
        assert result is None
        assert request.tenant_id is None

    def test_should_handle_invalid_header_uuid(self):
        request = self.factory.get(
            "/",
            HTTP_HOST="example.com",
            HTTP_X_TENANT_ID="not-a-uuid",
        )
        result = self.middleware.process_request(request)
        assert result is None
        assert request.tenant_id is None

    def test_should_skip_www_subdomain(self):
        request = self.factory.get(
            "/",
            HTTP_HOST="www.example.com",
        )
        result = self.middleware.process_request(request)
        assert result is None
        assert request.tenant_id is None

    def test_should_reject_inactive_tenant(self):
        Organization.objects.create(
            name="Dead",
            slug="dead",
            status="deleted",
        )
        request = self.factory.get(
            "/",
            HTTP_HOST="dead.example.com",
        )
        result = self.middleware.process_request(request)
        assert result is None
        assert request.tenant_id is None

    def test_should_clear_context_on_response(self):
        from django.http import HttpResponse

        from django_tenancy.context import get_context

        org = Organization.objects.create(
            name="Ctx",
            slug="ctx",
            status="active",
        )
        # Simulate a request that sets tenant context
        request = self.factory.get(
            "/",
            HTTP_HOST="ctx.example.com",
        )
        self.middleware.process_request(request)
        assert request.tenant_id == org.tenant_id

        # Verify context is set
        ctx = get_context()
        assert ctx.tenant_id == org.tenant_id

        # process_response should clear it
        response = HttpResponse("ok")
        self.middleware.process_response(request, response)
        ctx = get_context()
        assert ctx.tenant_id is None
        assert ctx.tenant_slug is None

    # ── Membership enforcement (IDOR fix) ──────────────────────────────

    def test_should_honour_subdomain_for_member(self):
        org = Organization.objects.create(name="Acme", slug="acme", status="active")
        user = User.objects.create_user(username="member", password="p")
        Membership.objects.create(tenant_id=org.tenant_id, organization=org, user=user)
        request = self.factory.get("/", HTTP_HOST="acme.example.com")
        request.user = user
        self.middleware.process_request(request)
        assert request.tenant_id == org.tenant_id

    def test_should_reject_subdomain_for_authenticated_non_member(self):
        Organization.objects.create(name="Acme", slug="acme", status="active")
        outsider = User.objects.create_user(username="outsider", password="p")
        request = self.factory.get("/", HTTP_HOST="acme.example.com")
        request.user = outsider
        self.middleware.process_request(request)
        assert request.tenant_id is None

    def test_should_reject_header_for_authenticated_non_member(self):
        org = Organization.objects.create(name="Beta", slug="beta", status="active")
        outsider = User.objects.create_user(username="outsider2", password="p")
        request = self.factory.get(
            "/", HTTP_HOST="example.com", HTTP_X_TENANT_ID=str(org.tenant_id)
        )
        request.user = outsider
        self.middleware.process_request(request)
        assert request.tenant_id is None

    def test_should_honour_header_for_member(self):
        org = Organization.objects.create(name="Beta", slug="beta", status="active")
        user = User.objects.create_user(username="member2", password="p")
        Membership.objects.create(tenant_id=org.tenant_id, organization=org, user=user)
        request = self.factory.get(
            "/", HTTP_HOST="example.com", HTTP_X_TENANT_ID=str(org.tenant_id)
        )
        request.user = user
        self.middleware.process_request(request)
        assert request.tenant_id == org.tenant_id

    def test_should_allow_anonymous_subdomain_resolution(self):
        # Backward-compat: anonymous public access still resolves the tenant.
        org = Organization.objects.create(name="Acme", slug="acme", status="active")
        request = self.factory.get("/", HTTP_HOST="acme.example.com")
        request.user = AnonymousUser()
        self.middleware.process_request(request)
        assert request.tenant_id == org.tenant_id
