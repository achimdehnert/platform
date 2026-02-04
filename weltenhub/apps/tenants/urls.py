"""
Weltenhub Tenants API URLs
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TenantViewSet, TenantUserViewSet

app_name = "tenants"

router = DefaultRouter()
router.register("tenants", TenantViewSet, basename="tenant")
router.register("memberships", TenantUserViewSet, basename="tenant-user")

urlpatterns = [
    path("", include(router.urls)),
]
