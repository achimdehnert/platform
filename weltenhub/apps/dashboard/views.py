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
from apps.scenes.models import Scene


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
        context["character_count"] = Character.objects.filter(
            tenant=tenant
        ).count()
        context["story_count"] = Story.objects.filter(tenant=tenant).count()
        context["scene_count"] = Scene.objects.filter(tenant=tenant).count()

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


# =============================================================================
# Character Views
# =============================================================================

class CharacterListView(LoginRequiredMixin, TenantRequiredMixin, ListView):
    """List all characters for current tenant."""

    model = Character
    template_name = "dashboard/characters/list.html"
    context_object_name = "characters"
    paginate_by = 12

    def get_queryset(self):
        """Filter by tenant."""
        return (
            Character.objects.filter(tenant=self.request.tenant)
            .select_related("world", "role")
            .order_by("-is_protagonist", "name")
        )


class CharacterDetailView(LoginRequiredMixin, TenantRequiredMixin, DetailView):
    """Show character details."""

    model = Character
    template_name = "dashboard/characters/detail.html"
    context_object_name = "character"

    def get_queryset(self):
        """Filter by tenant."""
        return Character.objects.filter(tenant=self.request.tenant)


class CharacterCreateView(LoginRequiredMixin, TenantRequiredMixin, CreateView):
    """Create a new character."""

    model = Character
    template_name = "dashboard/characters/form.html"
    fields = [
        "name", "world", "role", "title", "nickname",
        "description", "personality", "backstory", "motivation",
        "goals", "flaws", "strengths", "voice",
        "age", "gender", "is_protagonist", "is_public"
    ]
    success_url = reverse_lazy("dashboard:character-list")

    def get_form(self, form_class=None):
        """Limit world choices to current tenant."""
        form = super().get_form(form_class)
        form.fields["world"].queryset = World.objects.filter(
            tenant=self.request.tenant
        )
        return form

    def form_valid(self, form):
        """Set tenant and created_by."""
        form.instance.tenant = self.request.tenant
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class CharacterUpdateView(LoginRequiredMixin, TenantRequiredMixin, UpdateView):
    """Update an existing character."""

    model = Character
    template_name = "dashboard/characters/form.html"
    fields = [
        "name", "world", "role", "title", "nickname",
        "description", "personality", "backstory", "motivation",
        "goals", "flaws", "strengths", "voice",
        "age", "gender", "is_protagonist", "is_public"
    ]

    def get_queryset(self):
        """Filter by tenant."""
        return Character.objects.filter(tenant=self.request.tenant)

    def get_form(self, form_class=None):
        """Limit world choices to current tenant."""
        form = super().get_form(form_class)
        form.fields["world"].queryset = World.objects.filter(
            tenant=self.request.tenant
        )
        return form

    def get_success_url(self):
        """Redirect to detail view."""
        return reverse_lazy("dashboard:character-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        """Set updated_by."""
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class CharacterDeleteView(LoginRequiredMixin, TenantRequiredMixin, DeleteView):
    """Delete a character."""

    model = Character
    template_name = "dashboard/characters/confirm_delete.html"
    success_url = reverse_lazy("dashboard:character-list")

    def get_queryset(self):
        """Filter by tenant."""
        return Character.objects.filter(tenant=self.request.tenant)


# =============================================================================
# Story Views
# =============================================================================

class StoryListView(LoginRequiredMixin, TenantRequiredMixin, ListView):
    """List all stories for current tenant."""

    model = Story
    template_name = "dashboard/stories/list.html"
    context_object_name = "stories"
    paginate_by = 12

    def get_queryset(self):
        """Filter by tenant."""
        return (
            Story.objects.filter(tenant=self.request.tenant)
            .select_related("world")
            .order_by("-created_at")
        )


class StoryDetailView(LoginRequiredMixin, TenantRequiredMixin, DetailView):
    """Show story details."""

    model = Story
    template_name = "dashboard/stories/detail.html"
    context_object_name = "story"

    def get_queryset(self):
        """Filter by tenant."""
        return Story.objects.filter(tenant=self.request.tenant)


class StoryCreateView(LoginRequiredMixin, TenantRequiredMixin, CreateView):
    """Create a new story."""

    model = Story
    template_name = "dashboard/stories/form.html"
    fields = [
        "title", "world", "genre", "logline", "synopsis",
        "themes", "mood", "conflict_level", "is_public"
    ]
    success_url = reverse_lazy("dashboard:story-list")

    def get_form(self, form_class=None):
        """Limit world choices to current tenant."""
        form = super().get_form(form_class)
        form.fields["world"].queryset = World.objects.filter(
            tenant=self.request.tenant
        )
        return form

    def form_valid(self, form):
        """Set tenant and created_by."""
        form.instance.tenant = self.request.tenant
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class StoryUpdateView(LoginRequiredMixin, TenantRequiredMixin, UpdateView):
    """Update an existing story."""

    model = Story
    template_name = "dashboard/stories/form.html"
    fields = [
        "title", "world", "genre", "logline", "synopsis",
        "themes", "mood", "conflict_level", "is_public"
    ]

    def get_queryset(self):
        """Filter by tenant."""
        return Story.objects.filter(tenant=self.request.tenant)

    def get_form(self, form_class=None):
        """Limit world choices to current tenant."""
        form = super().get_form(form_class)
        form.fields["world"].queryset = World.objects.filter(
            tenant=self.request.tenant
        )
        return form

    def get_success_url(self):
        """Redirect to detail view."""
        return reverse_lazy("dashboard:story-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        """Set updated_by."""
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class StoryDeleteView(LoginRequiredMixin, TenantRequiredMixin, DeleteView):
    """Delete a story."""

    model = Story
    template_name = "dashboard/stories/confirm_delete.html"
    success_url = reverse_lazy("dashboard:story-list")

    def get_queryset(self):
        """Filter by tenant."""
        return Story.objects.filter(tenant=self.request.tenant)


# =============================================================================
# Scene Views
# =============================================================================

class SceneListView(LoginRequiredMixin, TenantRequiredMixin, ListView):
    """List all scenes for current tenant."""

    model = Scene
    template_name = "dashboard/scenes/list.html"
    context_object_name = "scenes"
    paginate_by = 12

    def get_queryset(self):
        """Filter by tenant."""
        return (
            Scene.objects.filter(tenant=self.request.tenant)
            .select_related("story", "pov_character", "mood")
            .order_by("-created_at")
        )


class SceneDetailView(LoginRequiredMixin, TenantRequiredMixin, DetailView):
    """Show scene details."""

    model = Scene
    template_name = "dashboard/scenes/detail.html"
    context_object_name = "scene"

    def get_queryset(self):
        """Filter by tenant."""
        return Scene.objects.filter(tenant=self.request.tenant)


class SceneCreateView(LoginRequiredMixin, TenantRequiredMixin, CreateView):
    """Create a new scene."""

    model = Scene
    template_name = "dashboard/scenes/form.html"
    fields = [
        "title", "story", "summary", "content",
        "pov_character", "mood", "conflict_level",
        "goal", "status", "order"
    ]
    success_url = reverse_lazy("dashboard:scene-list")

    def get_form(self, form_class=None):
        """Limit choices to current tenant."""
        form = super().get_form(form_class)
        form.fields["story"].queryset = Story.objects.filter(
            tenant=self.request.tenant
        )
        from apps.characters.models import Character
        form.fields["pov_character"].queryset = Character.objects.filter(
            tenant=self.request.tenant
        )
        return form

    def form_valid(self, form):
        """Set tenant and created_by."""
        form.instance.tenant = self.request.tenant
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class SceneUpdateView(LoginRequiredMixin, TenantRequiredMixin, UpdateView):
    """Update an existing scene."""

    model = Scene
    template_name = "dashboard/scenes/form.html"
    fields = [
        "title", "story", "summary", "content",
        "pov_character", "mood", "conflict_level",
        "goal", "status", "order"
    ]

    def get_queryset(self):
        """Filter by tenant."""
        return Scene.objects.filter(tenant=self.request.tenant)

    def get_form(self, form_class=None):
        """Limit choices to current tenant."""
        form = super().get_form(form_class)
        form.fields["story"].queryset = Story.objects.filter(
            tenant=self.request.tenant
        )
        from apps.characters.models import Character
        form.fields["pov_character"].queryset = Character.objects.filter(
            tenant=self.request.tenant
        )
        return form

    def get_success_url(self):
        """Redirect to detail view."""
        return reverse_lazy(
            "dashboard:scene-detail", kwargs={"pk": self.object.pk}
        )

    def form_valid(self, form):
        """Set updated_by."""
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class SceneDeleteView(LoginRequiredMixin, TenantRequiredMixin, DeleteView):
    """Delete a scene."""

    model = Scene
    template_name = "dashboard/scenes/confirm_delete.html"
    success_url = reverse_lazy("dashboard:scene-list")

    def get_queryset(self):
        """Filter by tenant."""
        return Scene.objects.filter(tenant=self.request.tenant)
