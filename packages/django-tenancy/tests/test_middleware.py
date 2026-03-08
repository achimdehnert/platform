"""
Tests for SubdomainTenantMiddleware.
"""

import pytest
from django.test import RequestFactory

from django_tenancy.middleware import SubdomainTenantMiddleware
from django_tenancy.models import Organization


@pytest.fixture
def get_response():
    def _get_response(request):
        from django.http import HttpResponse
        return HttpResponse("ok")
    return _get_response


@pytest.fixture
def rf():
    return RequestFactory()


class TestTenancyModeDisabled:
    def test_disabled_mode_sets_no_tenant(self, get_response, rf, settings):
        settings.TENANCY_MODE = "disabled"
        mw = SubdomainTenantMiddleware(get_response)
        request = rf.get("/")
        request.session = {}
        mw.process_request(request)
        assert request.tenant is None
        assert request.tenant_id == 0


@pytest.mark.django_db
class TestTenancyModeSession:
    def test_session_mode_resolves_tenant(self, get_response, rf, settings):
        settings.TENANCY_MODE = "session"
        org = Organization.objects.create(name="Sess", slug="sess")
        mw = SubdomainTenantMiddleware(get_response)
        request = rf.get("/")
        request.session = {"tenant_id": org.pk}
        mw.process_request(request)
        assert request.tenant_id == org.pk

    def test_session_mode_missing_tenant_redirects(self, get_response, rf, settings):
        settings.TENANCY_MODE = "session"
        settings.TENANCY_FALLBACK_URL = "/onboarding/"
        mw = SubdomainTenantMiddleware(get_response)
        request = rf.get("/")
        request.session = {}
        response = mw.process_request(request)
        assert response is not None
        assert response.status_code == 302
        assert response["Location"] == "/onboarding/"

    def test_language_code_set_from_tenant(self, get_response, rf, settings):
        settings.TENANCY_MODE = "session"
        org = Organization.objects.create(name="EN", slug="en-org", language="en")
        mw = SubdomainTenantMiddleware(get_response)
        request = rf.get("/")
        request.session = {"tenant_id": org.pk}
        mw.process_request(request)
        assert request.LANGUAGE_CODE == "en"


@pytest.mark.django_db
class TestTenancyModeHeader:
    def test_header_mode_resolves_tenant(self, get_response, rf, settings):
        settings.TENANCY_MODE = "header"
        org = Organization.objects.create(name="HDR", slug="hdr")
        mw = SubdomainTenantMiddleware(get_response)
        request = rf.get("/", HTTP_X_TENANT_ID=str(org.pk))
        request.session = {}
        mw.process_request(request)
        assert request.tenant_id == org.pk
