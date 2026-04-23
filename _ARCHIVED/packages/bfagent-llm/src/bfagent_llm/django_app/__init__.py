"""
bfagent_llm.django_app — DB-driven LLM routing for Django apps (ADR-089).

Usage:
    # settings.py
    INSTALLED_APPS = [..., "bfagent_llm.django_app"]

    # In any service:
    from bfagent_llm.django_app.service import completion
    result = await completion(
        action_code="character_generation",
        messages=[{"role": "user", "content": prompt}],
        tenant_id=request.tenant_id,
    )
"""

from django.apps import AppConfig


class BfagentLlmConfig(AppConfig):
    """Django app config for bfagent-llm DB-driven routing."""

    name = "bfagent_llm.django_app"
    label = "bfagent_llm"
    verbose_name = "BFAgent LLM"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from bfagent_llm.django_app import checks  # noqa: F401


default_app_config = "bfagent_llm.django_app.BfagentLlmConfig"
