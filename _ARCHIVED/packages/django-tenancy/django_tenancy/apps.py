"""Django app configuration for django-tenancy."""

from django.apps import AppConfig


class DjangoTenancyConfig(AppConfig):
    """App config for shared tenancy models."""

    name = "django_tenancy"
    verbose_name = "Tenancy"
    default_auto_field = "django.db.models.BigAutoField"
