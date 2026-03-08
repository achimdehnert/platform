"""Module catalogue views."""
from __future__ import annotations

import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.views.generic import TemplateView

from .catalogue import get_catalogue
from .services import get_active_modules

logger = logging.getLogger(__name__)


def _get_org(request: HttpRequest):
    """Resolve Organization for the current request (tenant-aware, with fallback)."""
    try:
        from django_tenancy.models import Organization

        tenant_id = getattr(request, "tenant_id", None)
        if tenant_id:
            return Organization.objects.filter(tenant_id=tenant_id).first()
    except Exception:  # noqa: BLE001
        pass
    return None


class ModuleCatalogueView(LoginRequiredMixin, TemplateView):
    """Render the full module catalogue with activation status."""

    template_name = "django_module_shop/catalogue.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        catalogue = get_catalogue()
        tenant_id = getattr(self.request, "tenant_id", None)
        active_modules = get_active_modules(tenant_id)
        organization = _get_org(self.request)
        ctx["catalogue"] = catalogue
        ctx["active_modules"] = active_modules
        ctx["organization"] = organization
        ctx["categories"] = sorted({m.category for m in catalogue.values()})
        return ctx


class ModuleToggleView(LoginRequiredMixin, TemplateView):
    """HTMX endpoint: toggle module active/inactive and return updated card partial."""

    def post(self, request: HttpRequest) -> HttpResponse:
        org = _get_org(request)
        if not org:
            return HttpResponse("No tenant context", status=403)
        try:
            data = json.loads(request.body)
            module_code = str(data["module"])
            do_activate = bool(data.get("active", True))
        except (KeyError, ValueError, json.JSONDecodeError):
            return HttpResponse("Invalid request body", status=400)

        catalogue = get_catalogue()
        if module_code not in catalogue:
            return HttpResponse(f"Unknown module: {module_code}", status=400)

        if do_activate:
            activate_module(org, module_code)
        else:
            deactivate_module(org, module_code)

        tenant_id = getattr(request, "tenant_id", None)
        active_modules = get_active_modules(tenant_id) if tenant_id else set()
        html = render_to_string(
            "django_module_shop/partials/module_card.html",
            {"module": catalogue[module_code], "active_modules": active_modules, "organization": org},
            request=request,
        )
        return HttpResponse(html)
