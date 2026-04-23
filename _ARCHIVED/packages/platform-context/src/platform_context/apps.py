"""Django app configuration for platform_context."""

from django.apps import AppConfig


class PlatformContextConfig(AppConfig):
    """Django app config for platform-context.

    Registers ADR-167 system checks on startup to validate
    HEALTH_PROBE_PATHS, HEALTH_RESPONSE_FORMAT, and middleware order.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "platform_context"
    verbose_name = "Platform Context"

    def ready(self) -> None:
        from platform_context import health_checks  # noqa: F401
