"""
Base View Classes
ADR-009: Tenant-aware views with SoC
"""

from typing import Any

from django.http import HttpRequest
from django.views.generic import TemplateView


class TenantMixin:
    """Mixin for tenant-aware views."""

    request: HttpRequest

    def get_tenant_id(self) -> int:
        """Get tenant ID from session/request."""
        return getattr(self.request, "tenant_id", 1)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["tenant_id"] = self.get_tenant_id()
        return context


class BaseView(TenantMixin, TemplateView):
    """Base view with tenant awareness."""

    pass


class HTMXMixin:
    """Mixin for HTMX partial responses."""

    request: HttpRequest
    partial_template_name: str | None = None

    def get_template_names(self) -> list[str]:
        if self.is_htmx_request() and self.partial_template_name:
            return [self.partial_template_name]
        return super().get_template_names()

    def is_htmx_request(self) -> bool:
        return self.request.headers.get("HX-Request") == "true"
