"""Subdomain-based tenant resolution middleware.

Resolution order:
    1. Subdomain: ``acme.example.com`` → Organization(slug="acme")
    2. Header: ``X-Tenant-ID: <uuid>`` (for API clients and tests)
    3. None: ``request.tenant_id = None`` (public pages, health endpoints)

Sets on request:
    - ``request.tenant_id``: UUID (from Organization.tenant_id)
    - ``request.tenant``: Organization instance
    - ``request.tenant_slug``: str subdomain

Propagates to:
    - ``django_tenancy.context``: contextvars for async-safe access
    - ``SET app.tenant_id``: PostgreSQL RLS session variable
"""

from __future__ import annotations

import logging
import uuid as _uuid

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from .context import clear_context, set_db_tenant, set_request_id, set_tenant, set_user
from .healthz import HEALTH_PATHS

logger = logging.getLogger(__name__)


class SubdomainTenantMiddleware(MiddlewareMixin):
    """Subdomain-based tenant resolution with header fallback."""

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        """Resolve tenant from subdomain or header."""
        # Generate request ID for tracing
        set_request_id()

        # Set user context if authenticated
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            user_id = getattr(user, "pk", None)
            if user_id:
                try:
                    set_user(_uuid.UUID(str(user_id)))
                except (ValueError, TypeError):
                    pass

        # Skip health endpoints
        if request.path in HEALTH_PATHS:
            request.tenant_id = None
            request.tenant = None
            request.tenant_slug = None
            return None

        # Try subdomain resolution
        host = request.get_host().split(":")[0]
        parts = host.split(".")

        if len(parts) > 2:
            subdomain = parts[0]
            if subdomain not in ("www", "api"):
                result = self._resolve_from_subdomain(request, subdomain)
                if result is not None:
                    return result
                return None

        # Try header fallback (API clients, tests)
        header_tenant = request.META.get("HTTP_X_TENANT_ID")
        if header_tenant:
            result = self._resolve_from_header(request, header_tenant)
            if result is not None:
                return result
            return None

        # No tenant context
        request.tenant_id = None
        request.tenant = None
        request.tenant_slug = None
        return None

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """Clear context at end of request."""
        clear_context()
        return response

    def _resolve_from_subdomain(
        self, request: HttpRequest, subdomain: str
    ) -> HttpResponse | None:
        """Resolve tenant from subdomain slug.

        Returns None on success, HttpResponse on error.
        """
        from .models import Organization

        try:
            org = Organization.objects.get(slug=subdomain)
        except Organization.DoesNotExist:
            logger.warning("Unknown tenant subdomain: %s", subdomain)
            request.tenant_id = None
            request.tenant = None
            request.tenant_slug = None
            return None

        if not org.is_active:
            logger.warning("Inactive tenant: %s (status=%s)", subdomain, org.status)
            request.tenant_id = None
            request.tenant = None
            request.tenant_slug = None
            return None

        self._set_tenant_context(request, org, subdomain)
        return None

    def _resolve_from_header(
        self, request: HttpRequest, header_value: str
    ) -> HttpResponse | None:
        """Resolve tenant from X-Tenant-ID header.

        Returns None on success, HttpResponse on error.
        """
        from .models import Organization

        try:
            tenant_uuid = _uuid.UUID(header_value)
        except (ValueError, TypeError):
            logger.warning("Invalid X-Tenant-ID header: %s", header_value)
            request.tenant_id = None
            request.tenant = None
            request.tenant_slug = None
            return None

        try:
            org = Organization.objects.get(tenant_id=tenant_uuid)
        except Organization.DoesNotExist:
            logger.warning("Unknown tenant from header: %s", tenant_uuid)
            request.tenant_id = None
            request.tenant = None
            request.tenant_slug = None
            return None

        self._set_tenant_context(request, org, org.slug)
        return None

    @staticmethod
    def _set_tenant_context(
        request: HttpRequest, org: "Organization", slug: str
    ) -> None:
        """Set tenant on request + contextvars + RLS."""
        request.tenant_id = org.tenant_id
        request.tenant = org
        request.tenant_slug = slug

        set_tenant(org.tenant_id, slug)
        set_db_tenant(org.tenant_id)
