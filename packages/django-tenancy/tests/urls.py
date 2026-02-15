"""Minimal URL conf for testing health endpoints."""

from django.urls import path

from django_tenancy.healthz import liveness, readiness

urlpatterns = [
    path("livez/", liveness, name="health-liveness"),
    path("healthz/", readiness, name="health-readiness"),
    path("health/", readiness, name="health-compat"),
]
