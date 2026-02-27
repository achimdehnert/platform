from django.urls import path

from iil_commons.health.views import liveness, readiness

urlpatterns = [
    path("livez/", liveness, name="iil_livez"),
    path("readyz/", readiness, name="iil_readyz"),
]
