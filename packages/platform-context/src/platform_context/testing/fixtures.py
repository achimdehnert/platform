"""Shared pytest fixtures for all platform Django repos.

Import these in your repo's conftest.py to get standard fixtures
for users, admin users, and authenticated clients::

    # conftest.py
    from platform_context.testing.fixtures import (  # noqa: F401
        admin_user,
        auth_client,
        user,
    )

All fixtures use ``django_user_model`` so they work with any custom
User model (AUTH_USER_MODEL), including allauth-based setups.

Note: These fixtures require pytest-django to be installed.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def user(db, django_user_model):
    """Standard authenticated user fixture.

    Creates a regular (non-staff, non-superuser) user.
    Works with any AUTH_USER_MODEL including allauth custom users.

    Returns:
        User instance.
    """
    kwargs = {
        "password": "testpass123",
    }
    email = "testuser@example.com"
    username = "testuser"

    if hasattr(django_user_model, "USERNAME_FIELD"):
        field = django_user_model.USERNAME_FIELD
        if field == "email":
            kwargs["email"] = email
            kwargs["username"] = username
        else:
            kwargs["username"] = username
            if "email" in [f.name for f in django_user_model._meta.get_fields()]:
                kwargs["email"] = email
    else:
        kwargs["username"] = username

    return django_user_model.objects.create_user(**kwargs)


@pytest.fixture
def admin_user(db, django_user_model):
    """Admin (superuser) fixture.

    Creates a superuser with staff and superuser flags set.

    Returns:
        Superuser instance.
    """
    kwargs = {
        "password": "adminpass123",
    }
    email = "admin@example.com"
    username = "admin"

    if hasattr(django_user_model, "USERNAME_FIELD"):
        field = django_user_model.USERNAME_FIELD
        if field == "email":
            kwargs["email"] = email
            kwargs["username"] = username
        else:
            kwargs["username"] = username
            if "email" in [f.name for f in django_user_model._meta.get_fields()]:
                kwargs["email"] = email
    else:
        kwargs["username"] = username

    return django_user_model.objects.create_superuser(**kwargs)


@pytest.fixture
def auth_client(client, user):
    """Authenticated Django test client fixture.

    Returns a test client that is already logged in as the standard
    ``user`` fixture. Use this for tests that require authentication.

    Returns:
        Authenticated Django test client.
    """
    client.force_login(user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Authenticated Django test client logged in as admin/superuser.

    Returns:
        Authenticated Django test client with superuser.
    """
    client.force_login(admin_user)
    return client


@pytest.fixture
def htmx_client(auth_client):
    """Authenticated client that sends HX-Request header on every request.

    Use this for testing HTMX fragment endpoints (ADR-058 U3).
    Automatically sets HTTP_HX_REQUEST=true on all requests.

    Returns:
        Authenticated Django test client with HTMX headers.
    """

    class HtmxClient:
        """Wrapper that injects HX-Request header into every request."""

        def __init__(self, inner_client):
            self._client = inner_client

        def _inject(self, kwargs):
            kwargs.setdefault("HTTP_HX_REQUEST", "true")
            return kwargs

        def get(self, path, **kwargs):
            return self._client.get(path, **self._inject(kwargs))

        def post(self, path, data=None, **kwargs):
            return self._client.post(path, data, **self._inject(kwargs))

        def put(self, path, data=None, **kwargs):
            return self._client.put(path, data, **self._inject(kwargs))

        def patch(self, path, data=None, **kwargs):
            return self._client.patch(path, data, **self._inject(kwargs))

        def delete(self, path, **kwargs):
            return self._client.delete(path, **self._inject(kwargs))

        def force_login(self, user):
            return self._client.force_login(user)

    return HtmxClient(auth_client)
