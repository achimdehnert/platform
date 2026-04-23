"""Django app configuration for platform-notifications."""

from django.apps import AppConfig


class PlatformNotificationsConfig(AppConfig):
    """Platform Notifications app config."""

    name = "platform_notifications"
    verbose_name = "Platform Notifications"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Register built-in channels on app startup."""
        from platform_notifications.channels.email import EmailChannel
        from platform_notifications.channels.webhook import WebhookChannel
        from platform_notifications.registry import ChannelRegistry

        registry = ChannelRegistry.get_instance()
        registry.register(EmailChannel())
        registry.register(WebhookChannel())

        try:
            from platform_notifications.channels.sms import SmsChannel
            registry.register(SmsChannel())
        except ImportError:
            pass

        from platform_notifications.channels.discord import DiscordChannel
        from platform_notifications.channels.telegram import TelegramChannel

        registry.register(DiscordChannel())
        registry.register(TelegramChannel())
