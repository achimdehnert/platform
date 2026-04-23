"""Tests for platform_context.testing module.

Verifies that all shared assertions and fixtures work correctly
without requiring a full Django app setup.
"""

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from platform_context.testing.assertions import (
    assert_celery_dispatched,
    assert_htmx_fragment,
    assert_htmx_trigger,
    assert_json_error,
)


class TestAssertHtmxFragment:
    """Tests for assert_htmx_fragment."""

    def test_should_pass_for_fragment_response(self):
        response = HttpResponse("<div>fragment</div>")
        assert_htmx_fragment(response)  # no exception

    def test_should_fail_for_full_html_page(self):
        response = HttpResponse("<html><body>full page</body></html>")
        with pytest.raises(AssertionError, match="full HTML page"):
            assert_htmx_fragment(response)

    def test_should_fail_for_html_with_attributes(self):
        response = HttpResponse('<html lang="de"><body>page</body></html>')
        with pytest.raises(AssertionError):
            assert_htmx_fragment(response)

    def test_should_pass_for_empty_response(self):
        response = HttpResponse("")
        assert_htmx_fragment(response)  # no exception


class TestAssertJsonError:
    """Tests for assert_json_error."""

    def test_should_pass_for_correct_json_error(self):
        response = HttpResponse(
            '{"detail": "Not found."}',
            status=404,
            content_type="application/json",
        )
        assert_json_error(response, 404)  # no exception

    def test_should_fail_for_wrong_status(self):
        response = HttpResponse(
            '{"detail": "Not found."}',
            status=404,
            content_type="application/json",
        )
        with pytest.raises(AssertionError, match="Expected status 200"):
            assert_json_error(response, 200)

    def test_should_fail_for_non_json_body(self):
        response = HttpResponse("<h1>Server Error</h1>", status=500)
        with pytest.raises(AssertionError, match="not valid JSON"):
            assert_json_error(response, 500)

    def test_should_fail_for_missing_error_key(self):
        response = HttpResponse(
            '{"error": "something"}',
            status=400,
            content_type="application/json",
        )
        with pytest.raises(AssertionError, match="detail"):
            assert_json_error(response, 400)

    def test_should_pass_with_custom_error_key(self):
        response = HttpResponse(
            '{"message": "Bad request"}',
            status=400,
            content_type="application/json",
        )
        assert_json_error(response, 400, error_key="message")  # no exception


class TestAssertHtmxTrigger:
    """Tests for assert_htmx_trigger."""

    def test_should_pass_for_matching_trigger(self):
        response = HttpResponse(status=204)
        response["HX-Trigger"] = '{"tripUpdated": null}'
        assert_htmx_trigger(response, "tripUpdated")  # no exception

    def test_should_fail_for_missing_trigger_header(self):
        response = HttpResponse(status=204)
        with pytest.raises(AssertionError, match="absent"):
            assert_htmx_trigger(response, "tripUpdated")

    def test_should_fail_for_wrong_trigger_name(self):
        response = HttpResponse(status=204)
        response["HX-Trigger"] = '{"otherEvent": null}'
        with pytest.raises(AssertionError, match="tripUpdated"):
            assert_htmx_trigger(response, "tripUpdated")

    def test_should_pass_for_plain_string_trigger(self):
        response = HttpResponse(status=204)
        response["HX-Trigger"] = "tripUpdated"
        assert_htmx_trigger(response, "tripUpdated")  # no exception


class TestAssertCeleryDispatched:
    """Tests for assert_celery_dispatched."""

    def test_should_pass_when_called_once(self):
        from unittest.mock import MagicMock
        mock = MagicMock()
        mock()
        assert_celery_dispatched(mock, count=1)  # no exception

    def test_should_fail_when_not_called(self):
        from unittest.mock import MagicMock
        mock = MagicMock()
        with pytest.raises(AssertionError, match="0 time"):
            assert_celery_dispatched(mock, count=1)

    def test_should_pass_for_multiple_dispatches(self):
        from unittest.mock import MagicMock
        mock = MagicMock()
        mock()
        mock()
        assert_celery_dispatched(mock, count=2)  # no exception

    def test_should_fail_for_wrong_count(self):
        from unittest.mock import MagicMock
        mock = MagicMock()
        mock()
        with pytest.raises(AssertionError, match="2 time"):
            assert_celery_dispatched(mock, count=2)


class TestFixturesImport:
    """Verify that fixtures module imports cleanly."""

    def test_should_import_fixtures_module(self):
        from platform_context.testing import fixtures
        assert hasattr(fixtures, "user")
        assert hasattr(fixtures, "admin_user")
        assert hasattr(fixtures, "auth_client")
        assert hasattr(fixtures, "admin_client")
        assert hasattr(fixtures, "htmx_client")

    def test_should_import_assertions_module(self):
        from platform_context.testing import assertions
        assert hasattr(assertions, "assert_htmx_fragment")
        assert hasattr(assertions, "assert_login_required")
        assert hasattr(assertions, "assert_no_data_leak")
        assert hasattr(assertions, "assert_json_error")
        assert hasattr(assertions, "assert_htmx_trigger")
        assert hasattr(assertions, "assert_graceful_degradation")
        assert hasattr(assertions, "assert_celery_dispatched")
