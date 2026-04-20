"""Tests for platform_context.middleware module."""

import json

from django.http import HttpRequest, JsonResponse
from django.test import RequestFactory

from platform_context.middleware import (
    DEFAULT_HEALTH_PATHS,
    HealthBypassMiddleware,
    _is_health_path,
    _parse_subdomain,
)


class TestParseSubdomain:
    """Tests for subdomain extraction."""

    def test_should_extract_subdomain(self):
        assert _parse_subdomain("demo.risk-hub.de", "risk-hub.de") == "demo"

    def test_should_return_none_for_base_domain(self):
        assert _parse_subdomain("risk-hub.de", "risk-hub.de") is None

    def test_should_handle_localhost(self):
        assert _parse_subdomain("demo.localhost", "localhost") == "demo"

    def test_should_strip_port(self):
        assert _parse_subdomain("demo.localhost:8000", "localhost") == "demo"

    def test_should_be_case_insensitive(self):
        assert _parse_subdomain("Demo.Risk-Hub.DE", "risk-hub.de") == "demo"

    def test_should_return_none_for_unrelated_domain(self):
        assert _parse_subdomain("other.com", "risk-hub.de") is None


class TestIsHealthPath:
    """Tests for _is_health_path helper."""

    def test_should_match_livez(self):
        request = RequestFactory().get("/livez/")
        assert _is_health_path(request) is True

    def test_should_match_healthz(self):
        request = RequestFactory().get("/healthz/")
        assert _is_health_path(request) is True

    def test_should_match_readyz(self):
        request = RequestFactory().get("/readyz/")
        assert _is_health_path(request) is True

    def test_should_match_health(self):
        request = RequestFactory().get("/health/")
        assert _is_health_path(request) is True

    def test_should_not_match_regular_path(self):
        request = RequestFactory().get("/api/v1/users/")
        assert _is_health_path(request) is False

    def test_should_not_match_partial(self):
        request = RequestFactory().get("/livez")
        assert _is_health_path(request) is False

    def test_should_use_custom_paths(self, settings):
        settings.HEALTH_PROBE_PATHS = frozenset({"/custom-health/"})
        request = RequestFactory().get("/custom-health/")
        assert _is_health_path(request) is True

    def test_should_not_match_default_when_overridden(self, settings):
        settings.HEALTH_PROBE_PATHS = frozenset({"/custom-health/"})
        request = RequestFactory().get("/livez/")
        assert _is_health_path(request) is False

    def test_should_contain_four_default_paths(self):
        assert len(DEFAULT_HEALTH_PATHS) == 4
        assert "/livez/" in DEFAULT_HEALTH_PATHS
        assert "/healthz/" in DEFAULT_HEALTH_PATHS
        assert "/readyz/" in DEFAULT_HEALTH_PATHS
        assert "/health/" in DEFAULT_HEALTH_PATHS


class TestHealthBypassMiddleware:
    """Tests for HealthBypassMiddleware (ADR-021 Tier 1)."""

    def _make_middleware(self):
        """Create middleware with a downstream handler that should NOT be called."""
        def downstream(request):
            return JsonResponse({"error": "should not reach downstream"}, status=500)
        return HealthBypassMiddleware(downstream)

    def test_should_return_200_for_livez(self):
        mw = self._make_middleware()
        request = RequestFactory().get("/livez/")
        response = mw(request)
        assert response.status_code == 200
        assert json.loads(response.content) == {"status": "ok"}

    def test_should_return_200_for_healthz(self):
        mw = self._make_middleware()
        request = RequestFactory().get("/healthz/")
        response = mw(request)
        assert response.status_code == 200

    def test_should_return_200_for_readyz(self):
        mw = self._make_middleware()
        request = RequestFactory().get("/readyz/")
        response = mw(request)
        assert response.status_code == 200

    def test_should_pass_through_regular_paths(self):
        def downstream(request):
            return JsonResponse({"page": "home"})
        mw = HealthBypassMiddleware(downstream)
        request = RequestFactory().get("/api/v1/users/")
        response = mw(request)
        assert json.loads(response.content) == {"page": "home"}

    def test_should_work_with_any_host_header(self):
        mw = self._make_middleware()
        request = RequestFactory().get("/livez/", HTTP_HOST="localhost")
        response = mw(request)
        assert response.status_code == 200

    def test_should_work_with_any_method(self):
        mw = self._make_middleware()
        request = RequestFactory().head("/livez/")
        response = mw(request)
        assert response.status_code == 200

    def test_should_respect_custom_paths(self, settings):
        settings.HEALTH_PROBE_PATHS = frozenset({"/ping/"})
        mw = self._make_middleware()
        # /ping/ should be intercepted
        request = RequestFactory().get("/ping/")
        response = mw(request)
        assert response.status_code == 200
        # /livez/ should pass through (and get 500 from downstream)
        request = RequestFactory().get("/livez/")
        response = mw(request)
        assert response.status_code == 500
