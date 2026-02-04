"""
Weltenhub Core Mixins
=====================

Reusable mixins for views and other components.
"""

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from typing import Any


class TenantRequiredMixin:
    """
    Mixin that enforces tenant context for views.

    Use this mixin on all views that access tenant-isolated data.
    Raises PermissionDenied if no tenant is set in the current context.

    Example:
        class WorldListView(LoginRequiredMixin, TenantRequiredMixin, ListView):
            model = World
    """

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """Check tenant context before processing request."""
        from apps.core.middleware.tenant import get_current_tenant

        tenant = get_current_tenant()
        if not tenant:
            raise PermissionDenied(
                "Tenant context required. Please select a tenant."
            )

        return super().dispatch(request, *args, **kwargs)

    def get_tenant(self):
        """Get the current tenant from thread-local storage."""
        from apps.core.middleware.tenant import get_current_tenant
        return get_current_tenant()


class TenantFilterMixin:
    """
    Mixin that automatically filters querysets by current tenant.

    Use with ListView or other views that use get_queryset().
    The model must inherit from TenantAwareModel.

    Example:
        class WorldListView(TenantFilterMixin, ListView):
            model = World
    """

    def get_queryset(self):
        """Filter queryset by current tenant."""
        from apps.core.middleware.tenant import get_current_tenant

        qs = super().get_queryset()
        tenant = get_current_tenant()
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


class TenantCreateMixin:
    """
    Mixin that automatically sets tenant on form save.

    Use with CreateView for tenant-isolated models.

    Example:
        class WorldCreateView(TenantCreateMixin, CreateView):
            model = World
            fields = ["name", "description"]
    """

    def form_valid(self, form):
        """Set tenant before saving."""
        from apps.core.middleware.tenant import get_current_tenant

        tenant = get_current_tenant()
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)
