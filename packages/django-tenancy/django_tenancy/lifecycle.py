"""Tenant lifecycle enforcement middleware (ADR-137).

Runs AFTER SubdomainTenantMiddleware. Blocks requests for
suspended or trial-expired tenants with an info page.

Middleware order::

    MIDDLEWARE = [
        ...
        "django_tenancy.middleware.SubdomainTenantMiddleware",
        "django_tenancy.lifecycle.TenantLifecycleMiddleware",
        ...
    ]
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

EXEMPT_PATHS = frozenset([
    "/livez/",
    "/healthz/",
    "/static/",
    "/accounts/",
    "/api/internal/",
    "/billing/",
    "/admin/",
])


class TenantLifecycleMiddleware(MiddlewareMixin):
    """Block requests for suspended or trial-expired tenants.

    Returns HTTP 403 with an info template for:
    - Suspended tenants → ``tenancy/suspended.html``
    - Trial-expired tenants → ``tenancy/trial_expired.html``

    Paths in EXEMPT_PATHS are always allowed (health, auth, billing, admin).
    """

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        if any(request.path.startswith(p) for p in EXEMPT_PATHS):
            return None

        org = getattr(request, "tenant", None)
        if org is None:
            return None

        if org.status == "suspended":
            logger.info(
                "Blocked request for suspended tenant %s (path=%s)",
                org.slug,
                request.path,
            )
            return render(request, "tenancy/suspended.html", status=403)

        if org.status == "trial" and org.trial_ends_at:
            if org.trial_ends_at < timezone.now():
                logger.info(
                    "Blocked request for trial-expired tenant %s (expired=%s)",
                    org.slug,
                    org.trial_ends_at,
                )
                upgrade_url = getattr(
                    settings, "BILLING_UPGRADE_URL", "/billing/"
                )
                return render(
                    request,
                    "tenancy/trial_expired.html",
                    {"org": org, "upgrade_url": upgrade_url},
                    status=403,
                )

        return None
