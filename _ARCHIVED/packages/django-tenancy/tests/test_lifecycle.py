"""Tests for TenantLifecycleMiddleware (ADR-137)."""

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.test import RequestFactory
from django.utils import timezone

from django_tenancy.lifecycle import TenantLifecycleMiddleware


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def middleware():
    get_resp = lambda r: MagicMock(status_code=200)  # noqa: E731
    return TenantLifecycleMiddleware(get_response=get_resp)


class TestLifecycleExemptPaths:
    """Test that exempt paths are not blocked."""

    @pytest.mark.parametrize("path", [
        "/livez/",
        "/healthz/",
        "/static/foo.css",
        "/accounts/login/",
        "/api/internal/activate/",
        "/billing/checkout/",
        "/admin/",
    ])
    def test_should_allow_exempt_paths(self, rf, middleware, path):
        request = rf.get(path)
        request.tenant = MagicMock(status="suspended")
        result = middleware.process_request(request)
        assert result is None


class TestLifecycleNoTenant:
    """Test behavior when no tenant is set."""

    def test_should_allow_when_no_tenant(self, rf, middleware):
        request = rf.get("/dashboard/")
        request.tenant = None
        result = middleware.process_request(request)
        assert result is None


class TestLifecycleSuspended:
    """Test blocking of suspended tenants."""

    def test_should_block_suspended_tenant(self, rf, middleware):
        request = rf.get("/dashboard/")
        request.tenant = MagicMock(status="suspended", slug="acme")
        result = middleware.process_request(request)
        assert result is not None
        assert result.status_code == 403

    def test_should_allow_active_tenant(self, rf, middleware):
        request = rf.get("/dashboard/")
        request.tenant = MagicMock(status="active")
        result = middleware.process_request(request)
        assert result is None


class TestLifecycleTrialExpired:
    """Test blocking of trial-expired tenants."""

    def test_should_block_expired_trial(self, rf, middleware):
        request = rf.get("/dashboard/")
        request.tenant = MagicMock(
            status="trial",
            trial_ends_at=timezone.now() - timedelta(days=1),
            slug="acme",
        )
        result = middleware.process_request(request)
        assert result is not None
        assert result.status_code == 403

    def test_should_allow_valid_trial(self, rf, middleware):
        request = rf.get("/dashboard/")
        request.tenant = MagicMock(
            status="trial",
            trial_ends_at=timezone.now() + timedelta(days=7),
        )
        result = middleware.process_request(request)
        assert result is None

    def test_should_allow_trial_without_end_date(self, rf, middleware):
        request = rf.get("/dashboard/")
        request.tenant = MagicMock(
            status="trial",
            trial_ends_at=None,
        )
        result = middleware.process_request(request)
        assert result is None
