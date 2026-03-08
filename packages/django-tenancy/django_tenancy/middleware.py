"""
django_tenancy/middleware.py

SubdomainTenantMiddleware with TenancyMode strategy.

Fixes (ADR-109 REVIEW):
  B-3: Redirect to TENANCY_FALLBACK_URL on TenantNotFound (no 500)
  B-5: ASGI-safe language — only request.LANGUAGE_CODE, no translation.activate()
  H-3: TenancyMode enum (SUBDOMAIN / SESSION / HEADER / DISABLED)

Middleware order (critical — ADR-110 B-4):
  SessionMiddleware → LocaleMiddleware → SubdomainTenantMiddleware
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from enum import StrEnum

from django.conf import settings
from django.db import models
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

from .context import set_current_tenant_id
from .exceptions import TenantNotFound
from .models import Organization

logger = logging.getLogger(__name__)


class TenancyMode(StrEnum):
    SUBDOMAIN = "subdomain"  # Prod: <slug>.hub.domain.tld
    SESSION = "session"      # Dev: session["tenant_id"]
    HEADER = "header"        # API/CI: X-Tenant-ID header
    DISABLED = "disabled"    # billing-hub, dev-hub


class SubdomainTenantMiddleware:
    """
    Resolves the current tenant from the request and sets:
      - request.tenant  (Organization instance)
      - request.tenant_id  (int)
      - request.LANGUAGE_CODE  (ASGI-safe, ADR-110 B-5)
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response
        mode_str = getattr(settings, "TENANCY_MODE", "session")
        try:
            self.mode = TenancyMode(mode_str)
        except ValueError as exc:
            raise ValueError(
                f"Invalid TENANCY_MODE '{mode_str}'. "
                f"Valid values: {[m.value for m in TenancyMode]}"
            ) from exc
        self.fallback_url = getattr(settings, "TENANCY_FALLBACK_URL", "/onboarding/")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.process_request(request)
        if response is not None:
            return response
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        if self.mode == TenancyMode.DISABLED:
            request.tenant = None
            request.tenant_id = 0
            return None

        # ADR-022: health check paths exempt from tenant resolution
        from .healthz import HEALTH_PATHS
        if request.path in HEALTH_PATHS:
            request.tenant = None
            request.tenant_id = 0
            return None

        try:
            tenant = self._resolve(request)
        except TenantNotFound as exc:
            # Fix B-3: no 500 — redirect to onboarding
            logger.info("Tenant not found: %s — redirecting to %s", exc, self.fallback_url)
            return HttpResponseRedirect(self.fallback_url)

        request.tenant = tenant
        request.tenant_id = tenant.pk
        set_current_tenant_id(tenant.pk)

        # Fix B-5: ASGI-safe language — only set request attribute,
        # never call translation.activate() (thread-local, ASGI-unsafe)
        if tenant.language:
            request.LANGUAGE_CODE = tenant.language
            request._tenant_language = tenant.language

        return None

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        # Set language cookie so LocaleMiddleware picks it up next request
        lang = getattr(request, "_tenant_language", None)
        if lang:
            cookie_name = getattr(settings, "LANGUAGE_COOKIE_NAME", "iil_lang")
            response.set_cookie(
                cookie_name,
                lang,
                max_age=getattr(settings, "LANGUAGE_COOKIE_AGE", 60 * 60 * 24 * 365),
                secure=getattr(settings, "LANGUAGE_COOKIE_SECURE", False),
                samesite="Lax",
            )
        return response

    def _resolve(self, request: HttpRequest) -> Organization:
        if self.mode == TenancyMode.SUBDOMAIN:
            return self._resolve_subdomain(request)
        if self.mode == TenancyMode.SESSION:
            return self._resolve_session(request)
        if self.mode == TenancyMode.HEADER:
            return self._resolve_header(request)
        raise TenantNotFound("No resolver for mode: disabled")

    def _resolve_subdomain(self, request: HttpRequest) -> Organization:
        host = request.get_host().split(":")[0]  # strip port
        subdomain = host.split(".")[0]
        try:
            return Organization.objects.active().get(
                models.Q(subdomain=subdomain) | models.Q(slug=subdomain)
            )
        except Organization.DoesNotExist as exc:
            raise TenantNotFound(f"No tenant for subdomain: {subdomain}") from exc

    def _resolve_session(self, request: HttpRequest) -> Organization:
        tenant_id = request.session.get("tenant_id")
        if not tenant_id:
            raise TenantNotFound("No tenant_id in session")
        try:
            return Organization.objects.active().get(pk=tenant_id)
        except Organization.DoesNotExist as exc:
            raise TenantNotFound(f"No tenant with id: {tenant_id}") from exc

    def _resolve_header(self, request: HttpRequest) -> Organization:
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            raise TenantNotFound("X-Tenant-ID header missing")
        try:
            return Organization.objects.active().get(pk=int(tenant_id))
        except (Organization.DoesNotExist, ValueError) as exc:
            raise TenantNotFound(f"No tenant with id: {tenant_id}") from exc
