from django.urls import path

from .views import ModuleCatalogueView, ModuleToggleView

app_name = "module_shop"

urlpatterns = [
    path("", ModuleCatalogueView.as_view(), name="catalogue"),
    path("toggle/", ModuleToggleView.as_view(), name="toggle"),
]
