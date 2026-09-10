"""Django-App: sammelt beim Start alle ``<app>.dienste``-Module ein (wie admin.autodiscover)."""

from __future__ import annotations

from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class IilDienstConfig(AppConfig):
    name = "iil_dienst"
    verbose_name = "iil-dienst (Vertraege)"

    def ready(self) -> None:
        autodiscover_modules("dienste")
