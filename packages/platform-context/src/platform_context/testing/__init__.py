"""platform_context.testing — Shared test helpers for all platform Django repos.

Provides repo-agnostic assertions, pytest fixtures, and conftest helpers
that can be imported by any repo using platform-context[testing].

Usage in any repo's conftest.py::

    from platform_context.testing.fixtures import user, admin_user, auth_client  # noqa: F401

Usage in tests::

    from platform_context.testing.assertions import (
        assert_htmx_fragment,
        assert_login_required,
        assert_no_data_leak,
        assert_json_error,
        assert_api_auth_required,
    )
"""

from platform_context.testing.assertions import (
    assert_api_auth_required,
    assert_celery_dispatched,
    assert_graceful_degradation,
    assert_htmx_fragment,
    assert_htmx_trigger,
    assert_json_error,
    assert_login_required,
    assert_no_data_leak,
)

__all__ = [
    "assert_api_auth_required",
    "assert_celery_dispatched",
    "assert_graceful_degradation",
    "assert_htmx_fragment",
    "assert_htmx_trigger",
    "assert_json_error",
    "assert_login_required",
    "assert_no_data_leak",
]
