"""Tests for ModuleAccessMiddleware and require_module decorator."""

import pytest
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from django_tenancy.models import Organization
from django_tenancy.module_access import ModuleAccessMiddleware, require_module
from django_tenancy.module_models import ModuleMembership, ModuleSubscription

User = get_user_model()


@pytest.fixture
def org(db):
    return Organization.objects.create(slug="testco", name="TestCo", status="active")


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="pw")


@pytest.fixture
def active_subscription(db, org):
    return ModuleSubscription.objects.create(
        organization=org,
        tenant_id=org.tenant_id,
        module="risk",
        status="active",
    )


@pytest.fixture
def member_membership(db, org, user):
    return ModuleMembership.objects.create(
        tenant_id=org.tenant_id,
        user=user,
        module="risk",
        role="member",
    )


def _make_request(path, tenant_id=None, user=None):
    factory = RequestFactory()
    request = factory.get(path)
    request.tenant_id = tenant_id
    if user is not None:
        request.user = user
    else:
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    return request


class TestRequireModuleDecorator:
    def test_allows_access_with_subscription_and_membership(
        self, db, org, user, active_subscription, member_membership,
    ):
        @require_module("risk")
        def my_view(request):
            return HttpResponse("ok")

        request = _make_request("/risk/", tenant_id=org.tenant_id, user=user)
        response = my_view(request)
        assert response.status_code == 200

    def test_denies_no_subscription(self, db, org, user, member_membership):
        @require_module("risk")
        def my_view(request):
            return HttpResponse("ok")

        request = _make_request("/risk/", tenant_id=org.tenant_id, user=user)
        response = my_view(request)
        assert response.status_code == 403

    def test_denies_no_membership(self, db, org, user, active_subscription):
        @require_module("risk")
        def my_view(request):
            return HttpResponse("ok")

        request = _make_request("/risk/", tenant_id=org.tenant_id, user=user)
        response = my_view(request)
        assert response.status_code == 403

    def test_denies_no_tenant(self, db, user, active_subscription, member_membership):
        @require_module("risk")
        def my_view(request):
            return HttpResponse("ok")

        request = _make_request("/risk/", tenant_id=None, user=user)
        response = my_view(request)
        assert response.status_code == 403

    def test_denies_insufficient_role(
        self, db, org, user, active_subscription, member_membership,
    ):
        @require_module("risk", min_role="admin")
        def my_view(request):
            return HttpResponse("ok")

        request = _make_request("/risk/", tenant_id=org.tenant_id, user=user)
        response = my_view(request)
        assert response.status_code == 403

    def test_allows_exact_role(
        self, db, org, user, active_subscription, member_membership,
    ):
        @require_module("risk", min_role="member")
        def my_view(request):
            return HttpResponse("ok")

        request = _make_request("/risk/", tenant_id=org.tenant_id, user=user)
        response = my_view(request)
        assert response.status_code == 200

    def test_allows_higher_role(self, db, org, user, active_subscription):
        ModuleMembership.objects.create(
            tenant_id=org.tenant_id,
            user=user,
            module="risk",
            role="admin",
        )

        @require_module("risk", min_role="viewer")
        def my_view(request):
            return HttpResponse("ok")

        request = _make_request("/risk/", tenant_id=org.tenant_id, user=user)
        response = my_view(request)
        assert response.status_code == 200

    def test_suspended_subscription_denied(self, db, org, user, member_membership):
        ModuleSubscription.objects.create(
            organization=org,
            tenant_id=org.tenant_id,
            module="risk",
            status="suspended",
        )

        @require_module("risk")
        def my_view(request):
            return HttpResponse("ok")

        request = _make_request("/risk/", tenant_id=org.tenant_id, user=user)
        response = my_view(request)
        assert response.status_code == 403


class TestModuleAccessMiddleware:
    def _get_middleware(self):
        return ModuleAccessMiddleware(get_response=lambda r: HttpResponse("ok"))

    def test_allows_access_with_subscription_and_membership(
        self, db, settings, org, user, active_subscription, member_membership,
    ):
        settings.MODULE_URL_MAP = {"/risk/": "risk", "/dsb/": "dsb"}
        mw = self._get_middleware()
        request = _make_request("/risk/assessments/", tenant_id=org.tenant_id, user=user)
        response = mw.process_request(request)
        assert response is None  # Middleware passes through

    def test_denies_no_subscription(self, db, settings, org, user, member_membership):
        settings.MODULE_URL_MAP = {"/risk/": "risk", "/dsb/": "dsb"}
        mw = self._get_middleware()
        request = _make_request("/risk/assessments/", tenant_id=org.tenant_id, user=user)
        response = mw.process_request(request)
        assert response is not None
        assert response.status_code == 403

    def test_passes_through_unmatched_path(self, db, settings, org, user):
        settings.MODULE_URL_MAP = {"/risk/": "risk", "/dsb/": "dsb"}
        mw = self._get_middleware()
        request = _make_request("/dashboard/", tenant_id=org.tenant_id, user=user)
        response = mw.process_request(request)
        assert response is None

    def test_passes_through_no_map(self, db, settings, org, user):
        settings.MODULE_URL_MAP = {}
        mw = self._get_middleware()
        request = _make_request("/risk/", tenant_id=org.tenant_id, user=user)
        response = mw.process_request(request)
        assert response is None

    def test_dsb_path_checked_separately(
        self, db, settings, org, user, active_subscription, member_membership,
    ):
        settings.MODULE_URL_MAP = {"/risk/": "risk", "/dsb/": "dsb"}
        # risk subscription/membership exists but NOT dsb
        mw = self._get_middleware()
        request = _make_request("/dsb/dashboard/", tenant_id=org.tenant_id, user=user)
        response = mw.process_request(request)
        assert response is not None
        assert response.status_code == 403
