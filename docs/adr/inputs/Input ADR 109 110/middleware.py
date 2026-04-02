"""
django_tenancy/middleware.py

Fixes:
  B-3 (ADR-109): SubdomainTenantMiddleware ohne Fallback für unbekannte Subdomain
  B-5 (ADR-110): translation.activate() ASGI-Thread-unsafe → translation.override() als Context Manager
  H-3 (ADR-109): TenancyMode Strategy (subdomain / session / header / disabled)
  C-1 (ADR-109): _tenant_workspace_qs() aus Views entfernt — Manager-Ebene
  B-4 (ADR-110): LocaleMiddleware-Reihenfolge dokumentiert (muss nach SessionMiddleware)

MIDDLEWARE ordering (required):
    "django.contrib.sessions.middleware.SessionMiddleware",    ← 1
    "django.middleware.locale.LocaleMiddleware",               ← 2 (after Session)
    "django_tenancy.middleware.SubdomainTenantMiddleware",     ← 3 (after Locale)
    "django.middleware.common.CommonMiddleware",               ← 4
"""

from __future__ import annotations

import logging
from enum import Enum

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils import translation

from django_tenancy.models import Organization

logger = logging.getLogger(__name__)


class TenancyMode(str, Enum):
    """
    Strategy for tenant identification.

    SUBDOMAIN : Production — tenant identified by subdomain (hub.tenant.domain.tld)
    SESSION   : Development — tenant_id stored in request.session
    HEADER    : API/CI — tenant_id in X-Tenant-ID request header
    DISABLED  : billing-hub, dev-hub — no tenant isolation
    """

    SUBDOMAIN = "subdomain"
    SESSION = "session"
    HEADER = "header"
    DISABLED = "disabled"


class TenantNotFound(Exception):
    """Raised when tenant lookup fails for a given identifier."""
    pass


def _get_tenancy_mode() -> TenancyMode:
    mode = getattr(settings, "TENANCY_MODE", TenancyMode.SUBDOMAIN)
    return TenancyMode(mode)


def _resolve_tenant_subdomain(request: HttpRequest) -> Organization:
    """Extract subdomain and look up Organization."""
    host = request.get_host().split(":")[0]  # strip port
    parts = host.split(".")
    if len(parts) < 3:
        raise TenantNotFound(f"No subdomain in host: {host!r}")
    subdomain = parts[0]
    try:
        return Organization.objects.get(subdomain=subdomain, is_active=True)
    except Organization.DoesNotExist:
        raise TenantNotFound(f"No active organization for subdomain: {subdomain!r}")


def _resolve_tenant_session(request: HttpRequest) -> Organization:
    """Read tenant_id from session."""
    tenant_id = request.session.get("tenant_id")
    if not tenant_id:
        raise TenantNotFound("No tenant_id in session")
    try:
        return Organization.objects.get(id=tenant_id, is_active=True)
    except Organization.DoesNotExist:
        raise TenantNotFound(f"No active organization for session tenant_id={tenant_id}")


def _resolve_tenant_header(request: HttpRequest) -> Organization:
    """Read tenant_id from X-Tenant-ID header."""
    tenant_id_str = request.headers.get("X-Tenant-ID", "")
    if not tenant_id_str:
        raise TenantNotFound("No X-Tenant-ID header")
    try:
        tenant_id = int(tenant_id_str)
    except ValueError:
        raise TenantNotFound(f"Invalid X-Tenant-ID: {tenant_id_str!r}")
    try:
        return Organization.objects.get(id=tenant_id, is_active=True)
    except Organization.DoesNotExist:
        raise TenantNotFound(f"No active organization for header tenant_id={tenant_id}")


_RESOLVERS = {
    TenancyMode.SUBDOMAIN: _resolve_tenant_subdomain,
    TenancyMode.SESSION: _resolve_tenant_session,
    TenancyMode.HEADER: _resolve_tenant_header,
}

# URLs exempt from tenant resolution (onboarding, login, health checks)
_EXEMPT_URL_PREFIXES: tuple[str, ...] = (
    "/onboarding/",
    "/accounts/",
    "/admin/",
    "/health/",
    "/i18n/",
    "/static/",
    "/media/",
)


class SubdomainTenantMiddleware:
    """
    Resolves tenant from request and sets:
      request.tenant    → Organization instance
      request.tenant_id → int (BigIntegerField value)

    Fix B-3: Unknown subdomain → redirect to /onboarding/, no 500.
    Fix B-5: Tenant language set via request attribute only — LocaleMiddleware
             reads request.LANGUAGE_CODE, no translation.activate() thread-local.

    ASGI-Safety: Does NOT call translation.activate() — that is thread-local state
    and unsafe in async/ASGI contexts. Instead, sets request.LANGUAGE_CODE and
    relies on Django's LocaleMiddleware to handle activation per-request.
    """

    def __init__(self, get_response) -> None:
        self.get_response = get_response
        self.mode = _get_tenancy_mode()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self.mode == TenancyMode.DISABLED:
            request.tenant = None
            request.tenant_id = 0
            return self.get_response(request)

        # Exempt URLs skip tenant resolution
        for prefix in _EXEMPT_URL_PREFIXES:
            if request.path.startswith(prefix):
                request.tenant = None
                request.tenant_id = 0
                return self.get_response(request)

        # Resolve tenant
        resolver = _RESOLVERS[self.mode]
        try:
            tenant = resolver(request)
        except TenantNotFound as e:
            logger.info("Tenant not found: %s — redirecting to onboarding", e)
            return HttpResponseRedirect(
                getattr(settings, "TENANCY_FALLBACK_URL", "/onboarding/")
            )

        request.tenant = tenant
        request.tenant_id = tenant.id  # int, not FK

        # Fix B-5: Set language preference on request ONLY — DO NOT call translation.activate()
        # LocaleMiddleware (which runs before this middleware) will have already set
        # the language from Accept-Language / cookie. We override here so the NEXT
        # request picks up the tenant language via cookie.
        #
        # For immediate per-request activation (if needed in views), use:
        #   with translation.override(request.tenant.language):
        #       return my_view(request)
        if tenant.language and tenant.language != request.LANGUAGE_CODE:
            request.LANGUAGE_CODE = tenant.language
            # Set cookie so LocaleMiddleware picks it up on next request
            # (this is the ASGI-safe approach)
            request._tenant_language = tenant.language

        return self.get_response(request)

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Set language cookie from tenant preference (ASGI-safe)."""
        tenant_language = getattr(request, "_tenant_language", None)
        if tenant_language:
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                tenant_language,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=False,  # JS needs to read language for date formatting
                samesite="Lax",
            )
        return response
