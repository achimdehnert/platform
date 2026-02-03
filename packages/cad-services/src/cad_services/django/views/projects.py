"""
Project Views
ADR-009: Database-driven project management
"""

from typing import Any

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cad_services.django.models.cadhub import Project
from cad_services.django.views.base import HTMXMixin, TenantMixin


class ProjectListView(HTMXMixin, TenantMixin, ListView):
    """List all projects for current tenant."""

    model = Project
    template_name = "cadhub/projects/list.html"
    partial_template_name = "cadhub/projects/partials/project_list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(tenant_id=self.get_tenant_id())

        # Search
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(name__icontains=search)

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_count"] = self.get_queryset().count()
        return context


class ProjectDetailView(HTMXMixin, TenantMixin, DetailView):
    """Project detail with models and statistics."""

    model = Project
    template_name = "cadhub/projects/detail.html"
    partial_template_name = "cadhub/projects/partials/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=self.get_tenant_id())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        project = self.object

        # Load related CAD models
        cad_models = project.cad_models.all()
        context["cad_models"] = cad_models
        context["model_count"] = cad_models.count()

        # Calculate statistics from all models
        total_rooms = 0
        total_windows = 0
        total_area = 0

        for cad_model in cad_models:
            total_rooms += cad_model.rooms.count()
            total_windows += cad_model.windows.count()
            area_sum = cad_model.rooms.aggregate(total=Sum("area_m2"))["total"]
            if area_sum:
                total_area += float(area_sum)

        context["stats"] = {
            "total_rooms": total_rooms,
            "total_windows": total_windows,
            "total_area": round(total_area, 2),
        }

        return context


class ProjectCreateView(HTMXMixin, TenantMixin, CreateView):
    """Create new project."""

    model = Project
    template_name = "cadhub/projects/create.html"
    partial_template_name = "cadhub/projects/partials/project_form.html"
    fields = ["name", "description"]

    def form_valid(self, form) -> HttpResponse:
        form.instance.tenant_id = self.get_tenant_id()
        form.instance.created_by_id = 1  # Default user ID
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse("cadhub:project-detail", kwargs={"pk": self.object.pk})


class ProjectEditView(HTMXMixin, TenantMixin, UpdateView):
    """Edit existing project."""

    model = Project
    template_name = "cadhub/projects/edit.html"
    partial_template_name = "cadhub/projects/partials/project_form.html"
    fields = ["name", "description"]

    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=self.get_tenant_id())

    def get_success_url(self) -> str:
        return reverse("cadhub:project-detail", kwargs={"pk": self.object.pk})


class ProjectDeleteView(TenantMixin, View):
    """Delete a project."""

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, tenant_id=self.get_tenant_id())
        project.delete()

        if request.headers.get("HX-Request"):
            return HttpResponse(
                status=200,
                headers={"HX-Redirect": reverse("cadhub:project-list")},
            )
        return redirect("cadhub:project-list")
