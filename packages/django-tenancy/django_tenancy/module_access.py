"""Module-level access control for multi-tenant Django apps.

Two complementary mechanisms:

1. ``ModuleAccessMiddleware`` — coarse URL-prefix guard. Configured via
   ``settings.MODULE_URL_MAP = {"/risk/": "risk", "/dsb/": "dsb"}``.
   Runs automatically for every request; no per-view code needed.

2. ``require_module(module, min_role)`` — fine-grained view decorator.
   Use when a module has internal role distinctions (e.g. only managers
   may delete records).

Access logic (both mechanisms):
    1. Tenant must have an active ``ModuleSubscription`` for the module.
    2. User must have a ``ModuleMembership`` for the module.
    3. If ``min_role`` is given, the membership role must be sufficient.

Role hierarchy (ascending): viewer < member < manager < admin.

Usage::

    # settings.py
    MODULE_URL_MAP = {
        "/risk/": "risk",
        "/dsb/":  "dsb",
    }

    # MIDDLEWARE (after SubdomainTenantMiddleware + AuthenticationMiddleware)
    MIDDLEWARE = [
        ...
        "django_tenancy.middleware.SubdomainTenantMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django_tenancy.module_access.ModuleAccessMiddleware",
    ]

    # views.py — fine-grained role check
    from django_tenancy.module_access import require_module

    @login_required
    @require_module("dsb", min_role="manager")
    def mandate_delete(request, pk):
        ...
"""

from __future__ import annotations

import logging
import uuid
from functools import wraps
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# Role hierarchy — higher index = more permissions.
_ROLE_ORDER = ["viewer", "member", "manager", "admin"]


def _role_sufficient(user_role: str, min_role: str) -> bool:
    """Return True if user_role meets or exceeds min_role."""
    try:
        return _ROLE_ORDER.index(user_role) >= _ROLE_ORDER.index(min_role)
    except ValueError:
        return False


def _resolve_tenant_from_membership(user) -> "uuid.UUID | None":
    """Resolve tenant_id from user's first active membership (dev fallback)."""
    try:
        from .models import Membership
        m = (
            Membership.objects
            .filter(user=user)
            .select_related("organization")
            .order_by("created_at")
            .first()
        )
        if m and m.organization.is_active:
            return m.organization.tenant_id
    except Exception:
        pass
    return None


def _check_module_access(
    tenant_id,
    user,
    module: str,
    min_role: str = "viewer",
) -> str | None:
    """Check subscription + membership. Returns error string or None on success."""
    from .module_models import ModuleMembership, ModuleSubscription

    if tenant_id is None:
        return "No tenant context"

    if not user or not getattr(user, "is_authenticated", False):
        return "Not authenticated"

    # 1. Tenant must have an active subscription for this module.
    if not ModuleSubscription.objects.filter(
        tenant_id=tenant_id,
        module=module,
        status__in=["trial", "active"],
    ).exists():
        return f"Module '{module}' is not subscribed for this tenant"

    # 2. User must have a module membership.
    try:
        membership = ModuleMembership.objects.get(
            tenant_id=tenant_id,
            user=user,
            module=module,
        )
    except ModuleMembership.DoesNotExist:
        return f"No access to module '{module}'"

    # 3. Role must be sufficient.
    if not _role_sufficient(membership.role, min_role):
        return (
            f"Role '{membership.role}' insufficient for module '{module}' "
            f"(requires '{min_role}')"
        )

    return None


class ModuleAccessMiddleware(MiddlewareMixin):
    """Coarse URL-prefix based module access guard.

    Reads ``settings.MODULE_URL_MAP`` (dict mapping URL prefix → module code).
    Skips paths not covered by the map.

    Example settings::

        MODULE_URL_MAP = {
            "/risk/":       "risk",
            "/dsb/":        "dsb",
            "/api/ex/":     "ex",
            "/ex/":         "ex",
            "/substances/": "ex",
        }

    Paths not in the map pass through unchecked (static files, health
    checks, admin, etc.).
    """

    # Paths always exempt from module checks.
    _EXEMPT_PREFIXES = (
        "/static/",
        "/livez/",
        "/healthz/",
        "/health/",
        "/favicon.ico",
        "/__debug__/",
        "/admin/",
        "/accounts/",
        "/api/schema",
        "/api/v1/",
        "/dashboard/",
        "/",
    )

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        module_url_map: dict[str, str] = getattr(settings, "MODULE_URL_MAP", {})
        if not module_url_map:
            return None

        path = request.path

        # Determine which module this path belongs to.
        matched_module: str | None = None
        for prefix, module in module_url_map.items():
            if path.startswith(prefix):
                matched_module = module
                break

        if matched_module is None:
            return None  # Not a module path — pass through.

        tenant_id = getattr(request, "tenant_id", None)
        user = getattr(request, "user", None)

        # Dev fallback: no subdomain tenant → resolve from user membership
        if tenant_id is None and user and getattr(user, "is_authenticated", False):
            tenant_id = _resolve_tenant_from_membership(user)

        error = _check_module_access(tenant_id, user, matched_module)
        if error:
            logger.warning(
                "Module access denied: path=%s module=%s tenant=%s user=%s reason=%s",
                path, matched_module, tenant_id,
                getattr(user, "username", "?"), error,
            )
            return HttpResponseForbidden(f"Access denied: {error}")

        return None


def require_module(module: str, min_role: str = "viewer") -> Callable:
    """View decorator enforcing module subscription + membership + role.

    Args:
        module: Module code (e.g. ``"risk"``, ``"dsb"``).
        min_role: Minimum role required. One of ``"viewer"``, ``"member"``,
            ``"manager"``, ``"admin"``. Defaults to ``"viewer"``.

    Returns:
        Decorator that wraps the view function.

    Usage::

        @login_required
        @require_module("dsb", min_role="manager")
        def mandate_delete(request, pk):
            ...
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            tenant_id = getattr(request, "tenant_id", None)
            user = getattr(request, "user", None)

            if tenant_id is None and user and getattr(user, "is_authenticated", False):
                tenant_id = _resolve_tenant_from_membership(user)

            error = _check_module_access(tenant_id, user, module, min_role)
            if error:
                logger.warning(
                    "require_module denied: view=%s module=%s min_role=%s "
                    "tenant=%s user=%s reason=%s",
                    view_func.__name__, module, min_role, tenant_id,
                    getattr(user, "username", "?"), error,
                )
                return HttpResponseForbidden(f"Access denied: {error}")

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator
