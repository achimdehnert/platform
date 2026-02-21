"""Reusable test assertions for all platform Django repos.

All assertions are repo-agnostic and cover the most common test patterns
defined in ADR-058 (Platform Test Taxonomy):

- A2: Auth / access control
- A6: Error handling (JSON body, no traceback)
- U3: HTMX fragment responses
- U9: Smoke / graceful degradation
- Celery dispatch verification

Example usage::

    from platform_context.testing.assertions import (
        assert_htmx_fragment,
        assert_login_required,
        assert_no_data_leak,
    )

    def test_should_return_fragment(auth_client):
        response = auth_client.get("/trips/", HTTP_HX_REQUEST="true")
        assert_htmx_fragment(response)

    def test_should_require_login(client):
        assert_login_required(client, "/dashboard/")

    def test_should_isolate_user_data(client):
        trip = TripFactory()
        other = UserFactory()
        assert_no_data_leak(client, f"/trips/{trip.pk}/", other)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from django.http import HttpResponse
    from django.test import Client


def assert_htmx_fragment(response: HttpResponse) -> None:
    """ADR-058 U3: Assert response is an HTMX fragment, not a full HTML page.

    Verifies that the response does not contain a full <html> document,
    which would indicate the view is not returning a partial correctly.

    Args:
        response: Django test client response.

    Raises:
        AssertionError: If response contains a full HTML page.
    """
    content = response.content.decode("utf-8", errors="replace")
    assert "<html" not in content, (
        f"Expected HTMX fragment but got full HTML page. "
        f"Status: {response.status_code}. "
        f"Check that the view returns a partial when HX-Request header is set."
    )


def assert_login_required(
    client: Client,
    url: str,
    *,
    login_url: str | None = None,
    method: str = "get",
) -> None:
    """ADR-058 A2: Assert that a URL requires authentication.

    Verifies that an unauthenticated request is redirected to the login page.
    Supports both Django built-in auth (/login/) and allauth (/accounts/login/).

    Args:
        client: Unauthenticated Django test client.
        url: URL to test.
        login_url: Expected login URL fragment. Auto-detected if None.
        method: HTTP method to use (default: "get").

    Raises:
        AssertionError: If the URL does not require authentication.
    """
    request_method = getattr(client, method.lower())
    response = request_method(url)
    assert response.status_code == 302, (
        f"Expected redirect (302) for unauthenticated request to {url!r}, "
        f"got {response.status_code}."
    )
    location = response.get("Location", "")
    if login_url:
        assert login_url in location, (
            f"Expected redirect to {login_url!r} but got {location!r}."
        )
    else:
        assert any(
            fragment in location
            for fragment in ("/login/", "/accounts/login/", "login")
        ), (
            f"Expected redirect to a login URL but got {location!r}. "
            f"Pass login_url= explicitly if your login URL differs."
        )


def assert_no_data_leak(
    client: Client,
    url: str,
    other_user: object,
    *,
    expected_status: int = 404,
    method: str = "get",
) -> None:
    """ADR-058 A2: Assert that a resource is not accessible by another user.

    Verifies cross-user data isolation: a resource owned by one user
    must not be accessible by a different authenticated user.

    Args:
        client: Django test client (will be logged in as other_user).
        url: URL of the resource to test.
        other_user: User who should NOT have access.
        expected_status: Expected HTTP status code (default: 404).
        method: HTTP method to use (default: "get").

    Raises:
        AssertionError: If the other user can access the resource.
    """
    client.force_login(other_user)
    request_method = getattr(client, method.lower())
    response = request_method(url)
    assert response.status_code == expected_status, (
        f"Data leak detected: user {other_user!r} accessed {url!r} "
        f"and got {response.status_code} instead of {expected_status}. "
        f"Ensure the view uses get_object_or_404(Model, pk=pk, user=request.user)."
    )


def assert_json_error(
    response: HttpResponse,
    expected_status: int,
    *,
    error_key: str = "detail",
) -> None:
    """ADR-058 A6: Assert that an error response returns JSON, not a traceback.

    Verifies that error responses (4xx/5xx) return a structured JSON body
    with an error key, not a raw Django traceback or HTML error page.

    Args:
        response: Django test client response.
        expected_status: Expected HTTP status code.
        error_key: Expected key in the JSON body (default: "detail").

    Raises:
        AssertionError: If status code is wrong or response is not JSON.
    """
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}."
    )
    try:
        data = response.json()
    except Exception:
        content_preview = response.content[:200].decode("utf-8", errors="replace")
        raise AssertionError(
            f"Expected JSON error body for status {expected_status}, "
            f"but response is not valid JSON. "
            f"Content preview: {content_preview!r}"
        ) from None
    assert error_key in data, (
        f"Expected JSON key {error_key!r} in error response, got keys: {list(data.keys())}. "
        f"Ensure the view returns a structured error body, not a raw traceback."
    )


def assert_htmx_trigger(
    response: HttpResponse,
    trigger_name: str,
) -> None:
    """ADR-058 U3/U4: Assert that an HTMX response includes a specific HX-Trigger.

    Verifies that the response sets the HX-Trigger header with the given
    event name, which is used to trigger client-side HTMX events.

    Args:
        response: Django test client response.
        trigger_name: Expected event name in HX-Trigger header.

    Raises:
        AssertionError: If HX-Trigger header is missing or does not contain the event.
    """
    import json as _json

    trigger_header = response.get("HX-Trigger", "")
    assert trigger_header, (
        f"Expected HX-Trigger header with {trigger_name!r} but header is absent."
    )
    try:
        triggers = _json.loads(trigger_header)
        assert trigger_name in triggers, (
            f"Expected {trigger_name!r} in HX-Trigger, got: {list(triggers.keys())}."
        )
    except _json.JSONDecodeError:
        assert trigger_name == trigger_header, (
            f"Expected HX-Trigger={trigger_name!r}, got {trigger_header!r}."
        )


def assert_graceful_degradation(
    client: Client,
    url: str,
    *,
    auth_user: object | None = None,
) -> None:
    """ADR-058 U9/A9: Assert that a URL returns 200 even when external services fail.

    Use this after mocking an external service to raise an exception,
    to verify the view handles the failure gracefully (no 500).

    Args:
        client: Django test client.
        url: URL to test.
        auth_user: User to authenticate as (optional).

    Raises:
        AssertionError: If the URL returns a 5xx status code.
    """
    if auth_user is not None:
        client.force_login(auth_user)
    response = client.get(url)
    assert response.status_code < 500, (
        f"Graceful degradation failed: {url!r} returned {response.status_code} "
        f"(5xx) when an external service is unavailable. "
        f"Ensure the view catches external service exceptions."
    )


def assert_celery_dispatched(
    mock_delay: MagicMock,
    *,
    count: int = 1,
) -> None:
    """ADR-058 A10: Assert that a Celery task was dispatched exactly N times.

    Args:
        mock_delay: Mocked ``task.delay`` method.
        count: Expected number of dispatch calls (default: 1).

    Raises:
        AssertionError: If the task was not dispatched the expected number of times.
    """
    assert mock_delay.call_count == count, (
        f"Expected Celery task to be dispatched {count} time(s), "
        f"but it was called {mock_delay.call_count} time(s). "
        f"Check that the view calls task.delay() exactly once per request."
    )
