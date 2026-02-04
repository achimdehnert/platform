"""
Dashboard Views for Weltenhub
=============================

Main dashboard and entity list/detail views with tenant isolation.
"""

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.core.mixins import TenantRequiredMixin
from apps.worlds.models import World
from apps.characters.models import Character
from apps.stories.models import Story


class DashboardView(LoginRequiredMixin, TenantRequiredMixin, TemplateView):
    """
    Main dashboard showing overview of user's content.
    
    Displays counts and recent items for worlds, characters, stories.
    """

    template_name = "dashboard/index.html"
    login_url = reverse_lazy("dashboard:login")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add dashboard statistics to context."""
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant

        # Get counts
        context["world_count"] = World.objects.filter(tenant=tenant).count()
        context["character_count"] = Character.objects.filter(tenant=tenant).count()
        context["story_count"] = Story.objects.filter(tenant=tenant).count()

        # Recent items
        context["recent_worlds"] = (
            World.objects.filter(tenant=tenant)
            .order_by("-created_at")[:5]
        )
        context["recent_characters"] = (
            Character.objects.filter(tenant=tenant)
            .order_by("-created_at")[:5]
        )
        context["recent_stories"] = (
            Story.objects.filter(tenant=tenant)
            .order_by("-created_at")[:5]
        )

        return context


# =============================================================================
# World Views
# =============================================================================

class WorldListView(LoginRequiredMixin, TenantRequiredMixin, ListView):
    """List all worlds for current tenant."""

    model = World
    template_name = "dashboard/worlds/list.html"
    context_object_name = "worlds"
    paginate_by = 12

    def get_queryset(self):
        """Filter by tenant."""
        return (
            World.objects.filter(tenant=self.request.tenant)
            .select_related("genre")
            .annotate(character_count=Count("characters"))
            .order_by("-created_at")
        )


class WorldDetailView(LoginRequiredMixin, TenantRequiredMixin, DetailView):
    """Show world details."""

    model = World
    template_name = "dashboard/worlds/detail.html"
    context_object_name = "world"

    def get_queryset(self):
        """Filter by tenant."""
        return World.objects.filter(tenant=self.request.tenant)


class WorldCreateView(LoginRequiredMixin, TenantRequiredMixin, CreateView):
    """Create a new world."""

    model = World
    template_name = "dashboard/worlds/form.html"
    fields = [
        "name", "genre", "description", "setting_era",
        "geography", "inhabitants", "culture",
        "technology_level", "magic_system", "history",
        "is_public", "tags"
    ]
    success_url = reverse_lazy("dashboard:world-list")

    def form_valid(self, form):
        """Set tenant and created_by."""
        form.instance.tenant = self.request.tenant
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class WorldUpdateView(LoginRequiredMixin, TenantRequiredMixin, UpdateView):
    """Update an existing world."""

    model = World
    template_name = "dashboard/worlds/form.html"
    fields = [
        "name", "genre", "description", "setting_era",
        "geography", "inhabitants", "culture",
        "technology_level", "magic_system", "history",
        "is_public", "tags"
    ]

    def get_queryset(self):
        """Filter by tenant."""
        return World.objects.filter(tenant=self.request.tenant)

    def get_success_url(self):
        """Redirect to detail view."""
        return reverse_lazy("dashboard:world-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        """Set updated_by."""
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class WorldDeleteView(LoginRequiredMixin, TenantRequiredMixin, DeleteView):
    """Delete a world (soft delete via model)."""

    model = World
    template_name = "dashboard/worlds/confirm_delete.html"
    success_url = reverse_lazy("dashboard:world-list")

    def get_queryset(self):
        """Filter by tenant."""
        return World.objects.filter(tenant=self.request.tenant)
