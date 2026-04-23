"""Tests for platform_context.health_checks (ADR-167 system checks)."""

import pytest
from django.test import override_settings

from platform_context.health_checks import (
    HEALTH_BYPASS_DOTTED_PATH,
    check_health_probe_paths,
    check_middleware_order,
    check_response_format,
)


class TestCheckHealthProbePaths:
    def test_no_setting_returns_empty(self):
        """Default (no HEALTH_PROBE_PATHS) is fine."""
        errors = check_health_probe_paths(None)
        assert errors == []

    @override_settings(HEALTH_PROBE_PATHS=frozenset({"/livez/", "/healthz/"}))
    def test_valid_frozenset_returns_empty(self):
        errors = check_health_probe_paths(None)
        assert errors == []

    @override_settings(HEALTH_PROBE_PATHS="not a set")
    def test_string_returns_error(self):
        errors = check_health_probe_paths(None)
        assert len(errors) == 1
        assert "E167.paths_type" in errors[0].id

    @override_settings(HEALTH_PROBE_PATHS=["/livez/", 42])
    def test_non_string_element_returns_error(self):
        errors = check_health_probe_paths(None)
        assert any("E167.paths_type" in e.id for e in errors)

    @override_settings(HEALTH_PROBE_PATHS=["livez/"])
    def test_missing_leading_slash_returns_error(self):
        errors = check_health_probe_paths(None)
        assert any("E167.paths_format" in e.id for e in errors)

    @override_settings(HEALTH_PROBE_PATHS=["/livez"])
    def test_missing_trailing_slash_returns_warning(self):
        errors = check_health_probe_paths(None)
        assert any("W167.paths_format" in e.id for e in errors)


class TestCheckMiddlewareOrder:
    @override_settings(MIDDLEWARE=[
        HEALTH_BYPASS_DOTTED_PATH,
        "django.middleware.security.SecurityMiddleware",
    ])
    def test_correct_order_returns_empty(self):
        errors = check_middleware_order(None)
        assert errors == []

    @override_settings(MIDDLEWARE=[
        "django.middleware.security.SecurityMiddleware",
        HEALTH_BYPASS_DOTTED_PATH,
    ])
    def test_wrong_position_returns_error(self):
        errors = check_middleware_order(None)
        assert len(errors) == 1
        assert "E167.middleware_order" in errors[0].id

    @override_settings(MIDDLEWARE=[
        "django.middleware.security.SecurityMiddleware",
    ])
    def test_missing_middleware_returns_warning(self):
        errors = check_middleware_order(None)
        assert len(errors) == 1
        assert "W167.middleware_order" in errors[0].id

    @override_settings(MIDDLEWARE=[])
    def test_empty_middleware_returns_warning(self):
        errors = check_middleware_order(None)
        assert len(errors) == 1
        assert "W167.middleware_order" in errors[0].id


class TestCheckResponseFormat:
    def test_no_setting_returns_empty(self):
        errors = check_response_format(None)
        assert errors == []

    @override_settings(HEALTH_RESPONSE_FORMAT="text")
    def test_text_is_valid(self):
        errors = check_response_format(None)
        assert errors == []

    @override_settings(HEALTH_RESPONSE_FORMAT="json")
    def test_json_is_valid(self):
        errors = check_response_format(None)
        assert errors == []

    @override_settings(HEALTH_RESPONSE_FORMAT="xml")
    def test_invalid_format_returns_error(self):
        errors = check_response_format(None)
        assert len(errors) == 1
        assert "E167.response_format" in errors[0].id
