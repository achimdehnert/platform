"""Tests for platform_context.middleware module (v0.7.0 — ADR-167 v1.1).

Covers:
    - Default paths (only /livez/ and /healthz/ — NOT /readyz/, /health/)
    - Sync and async dispatch
    - HTTP method enforcement (GET/HEAD allowed, others 405)
    - Content negotiation (text/plain default, JSON on Accept header)
    - Response headers (Cache-Control, X-Content-Type-Options)
    - Pass-through for non-health paths
    - Configuration overrides (HEALTH_PROBE_PATHS, HEALTH_RESPONSE_FORMAT)
    - Edge cases: case sensitivity, query strings, path traversal
    - Subdomain parsing (unchanged from v0.6.0)
"""

import json
from unittest.mock import MagicMock

import pytest
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.test import RequestFactory, override_settings

from platform_context.middleware import (
    ALLOWED_METHODS,
    DEFAULT_HEALTH_PATHS,
    HealthBypassMiddleware,
    _is_health_path,
    _parse_subdomain,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def sync_downstream():
    """Downstream handler that should NOT be called for health paths."""
    def _inner(request):
        return HttpResponse(f"downstream: {request.path}", status=200)
    return _inner


@pytest.fixture
def async_downstream():
    """Async downstream handler."""
    async def _inner(request):
        return HttpResponse(f"downstream async: {request.path}", status=200)
    return _inner


# --------------------------------------------------------------------------- #
# Default paths (v0.7.0: only /livez/ and /healthz/)
# --------------------------------------------------------------------------- #


class TestDefaultPaths:
    def test_should_contain_only_livez_and_healthz(self):
        assert DEFAULT_HEALTH_PATHS == frozenset({"/livez/", "/healthz/"})

    def test_should_NOT_contain_readyz(self):
        """ADR-167 v1.1: /readyz/ must reach downstream (DB-checking view)."""
        assert "/readyz/" not in DEFAULT_HEALTH_PATHS

    def test_should_NOT_contain_health(self):
        assert "/health/" not in DEFAULT_HEALTH_PATHS

    def test_readyz_passes_through_to_downstream(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/readyz/"))
        assert response.status_code == 200
        assert b"downstream" in response.content

    def test_health_passes_through_to_downstream(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/health/"))
        assert b"downstream" in response.content


# --------------------------------------------------------------------------- #
# Sync dispatch — GET / HEAD
# --------------------------------------------------------------------------- #


class TestSyncDispatch:
    @pytest.mark.parametrize("path", ["/livez/", "/healthz/"])
    def test_get_returns_200_text_plain(self, rf, sync_downstream, path):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get(path))
        assert response.status_code == 200
        assert response["Content-Type"] == "text/plain; charset=utf-8"
        assert response.content == b"ok\n"

    @pytest.mark.parametrize("path", ["/livez/", "/healthz/"])
    def test_head_returns_200(self, rf, sync_downstream, path):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.head(path))
        assert response.status_code == 200

    @pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    def test_non_get_head_methods_return_405(self, rf, sync_downstream, method):
        mw = HealthBypassMiddleware(sync_downstream)
        request = rf.generic(method, "/livez/")
        response = mw(request)
        assert response.status_code == 405
        assert set(response["Allow"].split(", ")) == ALLOWED_METHODS


# --------------------------------------------------------------------------- #
# Response headers
# --------------------------------------------------------------------------- #


class TestResponseHeaders:
    def test_cache_control_no_store(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/livez/"))
        assert "no-store" in response["Cache-Control"]
        assert "no-cache" in response["Cache-Control"]

    def test_x_content_type_options_nosniff(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/livez/"))
        assert response["X-Content-Type-Options"] == "nosniff"


# --------------------------------------------------------------------------- #
# Content negotiation
# --------------------------------------------------------------------------- #


class TestContentNegotiation:
    def test_accept_json_returns_json(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        request = rf.get("/livez/", HTTP_ACCEPT="application/json")
        response = mw(request)
        assert response["Content-Type"] == "application/json"
        assert json.loads(response.content) == {"status": "ok"}

    def test_accept_text_returns_text(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        request = rf.get("/livez/", HTTP_ACCEPT="text/plain")
        response = mw(request)
        assert response["Content-Type"] == "text/plain; charset=utf-8"
        assert response.content == b"ok\n"

    @override_settings(HEALTH_RESPONSE_FORMAT="json")
    def test_settings_override_json_default(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/livez/"))
        assert response["Content-Type"] == "application/json"

    @override_settings(HEALTH_RESPONSE_FORMAT="text")
    def test_settings_override_text_default(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/livez/"))
        assert response["Content-Type"] == "text/plain; charset=utf-8"


# --------------------------------------------------------------------------- #
# Async dispatch
# --------------------------------------------------------------------------- #


class TestAsyncDispatch:
    @pytest.mark.asyncio
    async def test_async_get_livez(self, rf, async_downstream):
        mw = HealthBypassMiddleware(async_downstream)
        response = await mw(rf.get("/livez/"))
        assert response.status_code == 200
        assert response.content == b"ok\n"

    @pytest.mark.asyncio
    async def test_async_downstream_called_for_non_health(self, rf, async_downstream):
        mw = HealthBypassMiddleware(async_downstream)
        response = await mw(rf.get("/api/users/"))
        assert response.status_code == 200
        assert b"downstream async" in response.content

    @pytest.mark.asyncio
    async def test_async_post_returns_405(self, rf, async_downstream):
        mw = HealthBypassMiddleware(async_downstream)
        response = await mw(rf.post("/livez/"))
        assert response.status_code == 405


# --------------------------------------------------------------------------- #
# Pass-through for non-health paths
# --------------------------------------------------------------------------- #


class TestPassThrough:
    def test_root_passes_through(self, rf):
        downstream = MagicMock(return_value=HttpResponse("root"))
        mw = HealthBypassMiddleware(downstream)
        mw(rf.get("/"))
        downstream.assert_called_once()

    def test_api_passes_through(self, rf):
        downstream = MagicMock(return_value=HttpResponse("api"))
        mw = HealthBypassMiddleware(downstream)
        mw(rf.get("/api/v1/items/"))
        downstream.assert_called_once()

    def test_livezz_typo_passes_through(self, rf):
        downstream = MagicMock(return_value=HttpResponse("not health"))
        mw = HealthBypassMiddleware(downstream)
        mw(rf.get("/livezz/"))
        downstream.assert_called_once()

    def test_livez_without_trailing_slash_passes_through(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/livez"))
        assert b"downstream" in response.content


# --------------------------------------------------------------------------- #
# Configuration overrides
# --------------------------------------------------------------------------- #


class TestConfigurationOverrides:
    @override_settings(HEALTH_PROBE_PATHS=frozenset({"/custom/ping/"}))
    def test_custom_paths(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/custom/ping/"))
        assert response.content == b"ok\n"

    @override_settings(HEALTH_PROBE_PATHS=frozenset({"/custom/ping/"}))
    def test_custom_paths_livez_no_longer_bypassed(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/livez/"))
        assert b"downstream" in response.content

    @override_settings(HEALTH_PROBE_PATHS=frozenset())
    def test_empty_paths_disables_bypass(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/livez/"))
        assert b"downstream" in response.content


# --------------------------------------------------------------------------- #
# Edge cases
# --------------------------------------------------------------------------- #


class TestEdgeCases:
    def test_case_sensitive(self, rf, sync_downstream):
        """/LIVEZ/ is NOT bypassed — Django paths are case-sensitive."""
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/LIVEZ/"))
        assert b"downstream" in response.content

    def test_query_string_ignored(self, rf):
        """Query string is not part of request.path; bypass still triggers."""
        downstream = MagicMock()
        mw = HealthBypassMiddleware(downstream)
        response = mw(rf.get("/livez/?source=elb"))
        downstream.assert_not_called()
        assert response.status_code == 200

    def test_path_traversal_does_not_bypass(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        request = rf.get("/livez/../etc/")
        response = mw(request)
        assert b"downstream" in response.content

    def test_works_with_any_host_header(self, rf, sync_downstream):
        mw = HealthBypassMiddleware(sync_downstream)
        response = mw(rf.get("/livez/", HTTP_HOST="totally-random.example.com"))
        assert response.status_code == 200
        assert response.content == b"ok\n"


# --------------------------------------------------------------------------- #
# Subdomain parsing (unchanged from v0.6.0)
# --------------------------------------------------------------------------- #


class TestParseSubdomain:
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


# --------------------------------------------------------------------------- #
# _is_health_path helper
# --------------------------------------------------------------------------- #


class TestIsHealthPath:
    def test_should_match_livez(self):
        request = RequestFactory().get("/livez/")
        assert _is_health_path(request) is True

    def test_should_match_healthz(self):
        request = RequestFactory().get("/healthz/")
        assert _is_health_path(request) is True

    def test_should_not_match_readyz(self):
        """v0.7.0: /readyz/ removed from defaults."""
        request = RequestFactory().get("/readyz/")
        assert _is_health_path(request) is False

    def test_should_not_match_health(self):
        """v0.7.0: /health/ removed from defaults."""
        request = RequestFactory().get("/health/")
        assert _is_health_path(request) is False

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
