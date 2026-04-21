"""
Django middleware for multi-tenancy, health probes, and request context.

Provides:
- HealthBypassMiddleware: Short-circuits health probe paths (ADR-167 v1.1)
- RequestContextMiddleware: Sets request_id and user_id
- SubdomainTenantMiddleware: Resolves tenant from subdomain (health-aware)

Note: TenantPermissionMiddleware remains in bfagent-core as it
depends on bfagent-specific models (CoreUser, TenantMembership).

v0.7.0 BREAKING CHANGES:
- Default HEALTH_PROBE_PATHS reduced to {"/livez/", "/healthz/"}.
  /readyz/ is no longer bypassed — use platform_context.health.urls for DB-checking readiness.
- Response is text/plain "ok\n" by default (was JSON). Use Accept: application/json for JSON.
- Non-GET/HEAD requests to health paths return 405 (was 200).
- Middleware is now async-capable (ASGI-native dual-mode).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Final

from asgiref.sync import iscoroutinefunction
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed
from django.utils.decorators import sync_and_async_middleware
from django.utils.deprecation import MiddlewareMixin

from platform_context.context import set_request_id, set_tenant, set_user_id
from platform_context.db import set_db_tenant
from platform_context.metrics import HEALTH_PROBE_COUNTER

logger = logging.getLogger("platform_context.health")

# ADR-167 v1.1: /readyz/ and /health/ intentionally removed from defaults.
# /readyz/ must be served by a DB-checking view (platform_context.health.urls).
DEFAULT_HEALTH_PATHS: Final[frozenset[str]] = frozenset({"/livez/", "/healthz/"})
ALLOWED_METHODS: Final[frozenset[str]] = frozenset({"GET", "HEAD"})

# Pre-built response bodies (avoid per-request allocation).
_BODY_TEXT: Final[bytes] = b"ok\n"
_BODY_JSON: Final[bytes] = b'{"status":"ok"}'

_COMMON_HEADERS: Final[dict[str, str]] = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "X-Content-Type-Options": "nosniff",
}


def _is_health_path(request: HttpRequest) -> bool:
    """Return True if the request targets a health probe endpoint."""
    paths = getattr(settings, "HEALTH_PROBE_PATHS", DEFAULT_HEALTH_PATHS)
    return request.path in paths


def _get_response_format() -> str:
    """Resolve default response format; one of {"text", "json"}."""
    fmt = getattr(settings, "HEALTH_RESPONSE_FORMAT", "text")
    return "json" if fmt == "json" else "text"


def _build_health_response(request: HttpRequest) -> HttpResponse:
    """Construct the bypass response honoring Accept header.

    The Accept header takes precedence over settings.HEALTH_RESPONSE_FORMAT.
    This keeps back-compat for monitors that parse JSON while letting LBs
    request lightweight text.
    """
    accept = request.META.get("HTTP_ACCEPT", "")
    default_format = _get_response_format()

    if "application/json" in accept or (default_format == "json" and "text/plain" not in accept):
        body = _BODY_JSON
        content_type = "application/json"
    else:
        body = _BODY_TEXT
        content_type = "text/plain; charset=utf-8"

    response = HttpResponse(body, content_type=content_type, status=200)
    for header, value in _COMMON_HEADERS.items():
        response[header] = value
    return response


def _log_and_count(request: HttpRequest, mode: str) -> None:
    """Emit debug log + Prometheus counter for observability."""
    HEALTH_PROBE_COUNTER.labels(path=request.path, mode=mode).inc()
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "health.bypass path=%s method=%s mode=%s remote=%s",
            request.path,
            request.method,
            mode,
            request.META.get("REMOTE_ADDR", "-"),
        )


@sync_and_async_middleware
def HealthBypassMiddleware(  # noqa: N802 — Django convention: middleware can be function
    get_response: Callable[[HttpRequest], HttpResponse] | Callable[[HttpRequest], Awaitable[HttpResponse]],
) -> Callable[[HttpRequest], HttpResponse] | Callable[[HttpRequest], Awaitable[HttpResponse]]:
    """Tier 1 middleware — short-circuits health probe paths (ADR-167 v1.1).

    Place this FIRST in MIDDLEWARE so that health probes bypass all
    downstream middleware (tenant resolution, auth, CSRF, etc.).

    Returns text/plain "ok\\n" for /livez/ and /healthz/ without touching
    the database. Only GET and HEAD are accepted; others return 405.

    Configure paths via ``settings.HEALTH_PROBE_PATHS`` (frozenset of str).
    Defaults to ``{"/livez/", "/healthz/"}``.

    Back-compat: set ``HEALTH_RESPONSE_FORMAT = "json"`` for JSON response,
    or send ``Accept: application/json`` header.

    Usage::

        MIDDLEWARE = [
            "platform_context.middleware.HealthBypassMiddleware",  # FIRST — ADR-167
            "django.middleware.security.SecurityMiddleware",
            ...
        ]
    """

    if iscoroutinefunction(get_response):

        async def async_middleware(request: HttpRequest) -> HttpResponse:
            if _is_health_path(request):
                _log_and_count(request, mode="async")
                if request.method not in ALLOWED_METHODS:
                    return HttpResponseNotAllowed(permitted_methods=sorted(ALLOWED_METHODS))
                return _build_health_response(request)
            return await get_response(request)  # type: ignore[misc]

        return async_middleware

    def sync_middleware(request: HttpRequest) -> HttpResponse:
        if _is_health_path(request):
            _log_and_count(request, mode="sync")
            if request.method not in ALLOWED_METHODS:
                return HttpResponseNotAllowed(permitted_methods=sorted(ALLOWED_METHODS))
            return _build_health_response(request)
        return get_response(request)  # type: ignore[return-value]

    return sync_middleware


def _parse_subdomain(host: str, base_domain: str) -> str | None:
    """
    Extract subdomain from host.

    Examples:
        - "demo.risk-hub.de" with base "risk-hub.de" -> "demo"
        - "risk-hub.de" with base "risk-hub.de" -> None
        - "demo.localhost" with base "localhost" -> "demo"
    """
    host = host.split(":")[0].lower()
    base = base_domain.lower()

    if host == base:
        return None

    if host.endswith("." + base):
        return host[: -(len(base) + 1)]

    return None


class RequestContextMiddleware(MiddlewareMixin):
    """
    Middleware to set up request context (request_id, user_id).

    Should be placed early in the middleware stack.
    """

    def process_request(self, request: HttpRequest) -> None:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        set_request_id(request_id)

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            set_user_id(user.id if hasattr(user, "id") else None)
        else:
            set_user_id(None)


class SubdomainTenantMiddleware(MiddlewareMixin):
    """
    Middleware for subdomain-based tenant resolution.

    Resolves tenant from subdomain (e.g., demo.risk-hub.de -> tenant "demo")
    and sets both the request context and Postgres session variable for RLS.

    Settings:
        TENANT_BASE_DOMAIN: Base domain (e.g., "risk-hub.de", "localhost")
        TENANT_ALLOW_LOCALHOST: Allow requests without tenant for admin (dev only)
        TENANT_MODEL: Dotted path to tenant model (default: "tenancy.Organization")
        TENANT_SLUG_FIELD: Field name for slug lookup (default: "slug")
        TENANT_ID_FIELD: Field name for tenant_id (default: "tenant_id")
    """

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        # ADR-021: Skip tenant resolution for health probes
        if _is_health_path(request):
            set_tenant(None, None)
            set_db_tenant(None)
            return None

        base_domain = getattr(settings, "TENANT_BASE_DOMAIN", "localhost")
        allow_localhost = getattr(settings, "TENANT_ALLOW_LOCALHOST", False)

        subdomain = _parse_subdomain(request.get_host(), base_domain)

        if not subdomain:
            if allow_localhost and request.path.startswith("/admin/"):
                set_tenant(None, None)
                set_db_tenant(None)
                return None
            return HttpResponseForbidden("Missing tenant subdomain")

        tenant = self._get_tenant(subdomain)
        if not tenant:
            return HttpResponseForbidden(f"Unknown tenant: {subdomain}")

        tenant_id_field = getattr(settings, "TENANT_ID_FIELD", "tenant_id")
        tenant_id = getattr(tenant, tenant_id_field, None)

        set_tenant(tenant_id, subdomain)
        set_db_tenant(tenant_id)

        request.tenant = tenant
        request.tenant_id = tenant_id
        request.tenant_slug = subdomain

        return None

    def _get_tenant(self, slug: str):
        """Look up tenant by slug."""
        model_path = getattr(settings, "TENANT_MODEL", "tenancy.Organization")
        slug_field = getattr(settings, "TENANT_SLUG_FIELD", "slug")

        try:
            from django.apps import apps
            app_label, model_name = model_path.rsplit(".", 1)
            model = apps.get_model(app_label, model_name)
            return model.objects.filter(**{slug_field: slug}).first()
        except Exception:
            return None
