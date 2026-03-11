from django.urls import path

from iil_commons.health.views import liveness, readiness

urlpatterns = [
    path("livez/", liveness, name="iil_livez"),
    path("healthz/", readiness, name="iil_healthz"),
    path("readyz/", readiness, name="iil_readyz"),
    path("health/", readiness, name="iil_health_compat"),
]
