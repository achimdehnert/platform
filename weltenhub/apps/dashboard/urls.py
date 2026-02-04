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
]
