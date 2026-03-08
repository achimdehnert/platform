from django.urls import path

from django_tenancy.healthz import liveness, readiness

urlpatterns = [
    path("livez/", liveness, name="liveness"),
    path("healthz/", readiness, name="healthz"),
    path("health/", readiness, name="health"),
]
