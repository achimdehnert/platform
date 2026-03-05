"""
aifw/apps.py — Django AppConfig for aifw.

Fix G-097-03: signals.py must be imported in ready() to register signal handlers.
Without this, cache invalidation on AIActionType save/delete does NOT work.
"""
from django.apps import AppConfig


class AifwConfig(AppConfig):
    name = "aifw"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "AI Framework"

    def ready(self) -> None:
        """
        Import signal handlers when Django starts.

        This is the standard Django pattern for signal registration.
        Signals are defined in aifw/signals.py and handle cache invalidation
        for AIActionType and TierQualityMapping changes.
        """
        import aifw.signals  # noqa: F401 — side-effect import registers signal handlers
