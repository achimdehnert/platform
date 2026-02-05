"""
Dashboard URL Configuration
===========================

URLs for dashboard and entity CRUD views.
"""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    # Authentication
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="dashboard/login.html"),
        name="login"
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="/"),
        name="logout"
    ),

    # Main Dashboard
    path("", views.DashboardView.as_view(), name="index"),

    # Worlds
    path("worlds/", views.WorldListView.as_view(), name="world-list"),
    path("worlds/create/", views.WorldCreateView.as_view(), name="world-create"),
    path("worlds/<int:pk>/", views.WorldDetailView.as_view(), name="world-detail"),
    path("worlds/<int:pk>/edit/", views.WorldUpdateView.as_view(), name="world-edit"),
    path(
        "worlds/<int:pk>/delete/",
        views.WorldDeleteView.as_view(),
        name="world-delete"
    ),

    # Characters
    path("characters/", views.CharacterListView.as_view(), name="character-list"),
    path(
        "characters/create/",
        views.CharacterCreateView.as_view(),
        name="character-create"
    ),
    path(
        "characters/<int:pk>/",
        views.CharacterDetailView.as_view(),
        name="character-detail"
    ),
    path(
        "characters/<int:pk>/edit/",
        views.CharacterUpdateView.as_view(),
        name="character-edit"
    ),
    path(
        "characters/<int:pk>/delete/",
        views.CharacterDeleteView.as_view(),
        name="character-delete"
    ),

    # Stories
    path("stories/", views.StoryListView.as_view(), name="story-list"),
    path("stories/create/", views.StoryCreateView.as_view(), name="story-create"),
    path("stories/<int:pk>/", views.StoryDetailView.as_view(), name="story-detail"),
    path("stories/<int:pk>/edit/", views.StoryUpdateView.as_view(), name="story-edit"),
    path(
        "stories/<int:pk>/delete/",
        views.StoryDeleteView.as_view(),
        name="story-delete"
    ),

    # Scenes
    path("scenes/", views.SceneListView.as_view(), name="scene-list"),
    path("scenes/create/", views.SceneCreateView.as_view(), name="scene-create"),
    path("scenes/<int:pk>/", views.SceneDetailView.as_view(), name="scene-detail"),
    path("scenes/<int:pk>/edit/", views.SceneUpdateView.as_view(), name="scene-edit"),
    path(
        "scenes/<int:pk>/delete/",
        views.SceneDeleteView.as_view(),
        name="scene-delete"
    ),
]
