"""Django app configuration for chat_logging."""

from django.apps import AppConfig


class ChatLoggingConfig(AppConfig):
    """Django AppConfig for the chat-logging package."""

    name = "chat_logging"
    verbose_name = "Chat Logging & QM"
    default_auto_field = "django.db.models.BigAutoField"
