"""
Management command: Validate LLM configuration.

Checks:
- Active providers have accessible API keys
- Active actions have default_model assigned
- Referenced models are active

Usage:
    python manage.py check_llm_config
"""

import os
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Validate LLM configuration for correctness."

    def handle(self, *args, **options) -> None:
        from bfagent_llm.django_app.models import (
            AIActionType,
            LLMModel,
            LLMProvider,
        )

        errors = 0
        warnings = 0

        # 1. Check providers
        self.stdout.write("\n=== LLM Providers ===")
        for provider in LLMProvider.objects.filter(is_active=True):
            env_var = provider.api_key_env_var
            has_env = bool(os.environ.get(env_var, ""))
            has_secret = os.path.isfile(
                f"/run/secrets/{env_var.lower()}"
            )

            if has_env or has_secret:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {provider.name}: OK (key found)"
                    )
                )
            elif env_var:
                self.stdout.write(
                    self.style.WARNING(
                        f"  {provider.name}: WARN — {env_var} not found"
                    )
                )
                warnings += 1
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"  {provider.name}: ERROR — no api_key_env_var set"
                    )
                )
                errors += 1

        # 2. Check models
        self.stdout.write("\n=== LLM Models ===")
        active_models = LLMModel.objects.filter(is_active=True).count()
        inactive_models = LLMModel.objects.filter(is_active=False).count()
        self.stdout.write(
            f"  Active: {active_models}, Inactive: {inactive_models}"
        )

        # 3. Check action types
        self.stdout.write("\n=== AI Action Types ===")
        for action in AIActionType.objects.filter(is_active=True).select_related(
            "default_model", "fallback_model"
        ):
            issues = []

            if not action.default_model_id:
                issues.append("NO default_model")
                errors += 1
            elif not action.default_model.is_active:
                issues.append("default_model is INACTIVE")
                errors += 1

            if (
                action.fallback_model_id
                and not action.fallback_model.is_active
            ):
                issues.append("fallback_model is INACTIVE")
                warnings += 1

            if issues:
                self.stdout.write(
                    self.style.ERROR(
                        f"  {action.code} (tenant={action.tenant_id}): "
                        f"{', '.join(issues)}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {action.code} (tenant={action.tenant_id}): OK"
                    )
                )

        # Summary
        self.stdout.write(f"\n=== Summary ===")
        self.stdout.write(f"  Errors: {errors}")
        self.stdout.write(f"  Warnings: {warnings}")

        if errors > 0:
            self.stdout.write(
                self.style.ERROR("FAILED — fix errors before deployment.")
            )
            sys.exit(1)
        else:
            self.stdout.write(
                self.style.SUCCESS("All checks passed.")
            )
