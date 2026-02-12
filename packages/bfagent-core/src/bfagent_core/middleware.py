"""
Django middleware for multi-tenancy and request context.

The framework-agnostic middleware (RequestContextMiddleware,
SubdomainTenantMiddleware) has been moved to platform-context.
This module re-exports them and keeps TenantPermissionMiddleware
which depends on bfagent-core models.
"""

import warnings

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

# Re-export from platform-context
from platform_context.middleware import (  # noqa: F401
    RequestContextMiddleware,
    SubdomainTenantMiddleware,
    _parse_subdomain,
)

warnings.warn(
    "bfagent_core.middleware.RequestContextMiddleware and "
    "SubdomainTenantMiddleware are deprecated, "
    "use platform_context.middleware instead",
    DeprecationWarning,
    stacklevel=2,
)


class TenantPermissionMiddleware(MiddlewareMixin):
    """
    Middleware for resolving CoreUser and attaching permissions.

    Should be placed AFTER SubdomainTenantMiddleware and AuthenticationMiddleware.

    Attaches:
        request.core_user: CoreUser instance (if available)
        request.membership: TenantMembership instance (if in tenant context)
        request.permissions: FrozenSet of permission codes
    """

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        request.core_user = None
        request.membership = None
        request.permissions = frozenset()

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None

        try:
            from bfagent_core.models import CoreUser, TenantMembership

            core_user = CoreUser.objects.filter(legacy_user_id=user.id).first()
            if not core_user:
                core_user = CoreUser.objects.create(
                    legacy_user_id=user.id,
                    provider="local",
                    email=user.email,
                    display_name=user.get_full_name() or user.username,
                )

            request.core_user = core_user

            tenant_id = getattr(request, "tenant_id", None)
            if tenant_id and core_user:
                membership = TenantMembership.objects.get_membership(
                    tenant_id,
                    core_user.id,
                )
                if membership:
                    request.membership = membership

                    from bfagent_core.permissions import get_permission_checker
                    checker = get_permission_checker()
                    request.permissions = checker.get_permissions(
                        core_user.id,
                        tenant_id,
                    )

        except Exception:
            pass

        return None
