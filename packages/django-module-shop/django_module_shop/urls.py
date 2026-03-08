from django.urls import path

from .views import ModuleCatalogueView, ModuleToggleView

urlpatterns = [
    path("", ModuleCatalogueView.as_view(), name="module-catalogue"),
    path("toggle/", ModuleToggleView.as_view(), name="module-toggle"),
]
