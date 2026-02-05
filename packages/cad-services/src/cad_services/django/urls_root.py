"""
CAD-Hub Root URL Configuration
"""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("cad_services.django.urls")),
]
