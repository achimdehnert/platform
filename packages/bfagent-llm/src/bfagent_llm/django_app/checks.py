"""
Django system checks for bfagent-llm configuration (ADR-089).

Runs on startup to warn about missing API keys or misconfigured actions.
"""

import os

from django.core.checks import Error, Warning, register


@register("bfagent_llm")
def check_llm_configuration(app_configs, **kwargs):
    """Check that active providers have accessible API keys."""
    errors = []

    try:
        from bfagent_llm.django_app.models import AIActionType, LLMProvider
    except Exception:
        return errors

    # Check providers have API keys accessible
    try:
        for provider in LLMProvider.objects.filter(is_active=True):
            env_var = provider.api_key_env_var
            if not env_var:
                errors.append(
                    Warning(
                        f"LLM Provider '{provider.name}' has no api_key_env_var.",
                        hint="Set api_key_env_var in Admin → LLM Providers.",
                        id="bfagent_llm.W001",
                    )
                )
                continue

            # Check if key is available via env or /run/secrets/
            has_env = bool(os.environ.get(env_var, ""))
            has_secret = os.path.isfile(
                f"/run/secrets/{env_var.lower()}"
            )

            if not has_env and not has_secret:
                errors.append(
                    Warning(
                        f"API key for provider '{provider.name}' not found. "
                        f"Expected env {env_var} or /run/secrets/{env_var.lower()}.",
                        hint=f"Set {env_var} in .env.prod or /run/secrets/.",
                        id="bfagent_llm.W002",
                    )
                )
    except Exception:
        pass  # DB not ready yet (e.g. during migrations)

    # Check active actions have models assigned
    try:
        orphaned = AIActionType.objects.filter(
            is_active=True,
            default_model__isnull=True,
        ).values_list("code", flat=True)

        for code in orphaned:
            errors.append(
                Error(
                    f"Active AIActionType '{code}' has no default_model.",
                    hint="Assign a default_model in Admin → AI Action Types.",
                    id="bfagent_llm.E001",
                )
            )
    except Exception:
        pass  # DB not ready yet

    return errors
