"""
Weltenhub Tenant Middleware
===========================

Provides tenant context for all requests.
Sets current tenant in thread-local storage for automatic filtering.
"""

import threading
from typing import Optional

from django.http import HttpRequest, HttpResponse

# Thread-local storage for current tenant
_thread_locals = threading.local()


def get_current_tenant():
    """
    Get the current tenant from thread-local storage.

    Returns:
        Tenant instance or None if not set.
    """
    return getattr(_thread_locals, "tenant", None)


def set_current_tenant(tenant) -> None:
    """
    Set the current tenant in thread-local storage.

    Args:
        tenant: Tenant instance or None to clear.
    """
    _thread_locals.tenant = tenant


def clear_current_tenant() -> None:
    """Clear the current tenant from thread-local storage."""
    if hasattr(_thread_locals, "tenant"):
        del _thread_locals.tenant


class TenantMiddleware:
    """
    Middleware to set current tenant based on request.

    Determines tenant from:
    1. X-Tenant-ID header (for API requests)
    2. Session (for authenticated users)
    3. User's default tenant (fallback)

    Usage in settings.py:
        MIDDLEWARE = [
            ...
            'apps.core.middleware.tenant.TenantMiddleware',
            ...
        ]
    """

    def __init__(self, get_response):
        """Initialize middleware."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request and set tenant context."""
        tenant = self._get_tenant_for_request(request)
        set_current_tenant(tenant)

        try:
            response = self.get_response(request)
        finally:
            clear_current_tenant()

        return response

    def _get_tenant_for_request(self, request: HttpRequest) -> Optional[object]:
        """
        Determine tenant for the current request.

        Priority:
        1. X-Tenant-ID header
        2. Session tenant_id
        3. User's default tenant

        Returns:
            Tenant instance or None.
        """
        from apps.tenants.models import Tenant, TenantUser

        # Skip for unauthenticated users
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return None

        # 1. Check X-Tenant-ID header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            try:
                tenant = Tenant.objects.get(id=tenant_id, is_active=True)
                if self._user_has_access(request.user, tenant):
                    return tenant
            except (Tenant.DoesNotExist, ValueError):
                pass

        # 2. Check session
        session_tenant_id = request.session.get("tenant_id")
        if session_tenant_id:
            try:
                tenant = Tenant.objects.get(
                    id=session_tenant_id,
                    is_active=True
                )
                if self._user_has_access(request.user, tenant):
                    return tenant
            except (Tenant.DoesNotExist, ValueError):
                pass

        # 3. Fall back to user's first active tenant
        membership = TenantUser.objects.filter(
            user=request.user,
            is_active=True,
            tenant__is_active=True
        ).select_related("tenant").first()

        if membership:
            return membership.tenant

        return None

    def _user_has_access(self, user, tenant) -> bool:
        """Check if user has access to tenant."""
        from apps.tenants.models import TenantUser

        return TenantUser.objects.filter(
            user=user,
            tenant=tenant,
            is_active=True
        ).exists()
