"""
Management command: Initialize LLM configuration with seed data.

Idempotent — uses update_or_create() for all operations.
Safe to run multiple times.

Usage:
    python manage.py init_llm_config
    python manage.py init_llm_config --tenant-id=<uuid>
"""

from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

SEED_PROVIDERS = [
    {
        "name": "openai",
        "display_name": "OpenAI",
        "api_key_env_var": "OPENAI_API_KEY",
    },
    {
        "name": "anthropic",
        "display_name": "Anthropic",
        "api_key_env_var": "ANTHROPIC_API_KEY",
    },
    {
        "name": "groq",
        "display_name": "Groq (LPU)",
        "api_key_env_var": "GROQ_API_KEY",
    },
    {
        "name": "google",
        "display_name": "Google AI",
        "api_key_env_var": "GOOGLE_API_KEY",
    },
]

SEED_MODELS = [
    # OpenAI
    {
        "provider": "openai",
        "name": "gpt-4o",
        "display_name": "GPT-4o",
        "max_tokens": 4096,
        "context_window": 128_000,
        "supports_vision": True,
        "input_cost_per_million": "2.5000",
        "output_cost_per_million": "10.0000",
    },
    {
        "provider": "openai",
        "name": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "max_tokens": 4096,
        "context_window": 128_000,
        "supports_vision": True,
        "input_cost_per_million": "0.1500",
        "output_cost_per_million": "0.6000",
        "is_default": True,
    },
    # Anthropic
    {
        "provider": "anthropic",
        "name": "claude-sonnet-4-20250514",
        "display_name": "Claude Sonnet 4",
        "max_tokens": 8192,
        "context_window": 200_000,
        "supports_vision": True,
        "input_cost_per_million": "3.0000",
        "output_cost_per_million": "15.0000",
    },
    # Groq (free developer tier)
    {
        "provider": "groq",
        "name": "qwen-qwen3-32b",
        "display_name": "Qwen3 32B (Groq)",
        "max_tokens": 4096,
        "context_window": 131_072,
        "input_cost_per_million": "0.0000",
        "output_cost_per_million": "0.0000",
    },
    {
        "provider": "groq",
        "name": "meta-llama/llama-3.3-70b-versatile",
        "display_name": "Llama 3.3 70B (Groq)",
        "max_tokens": 4096,
        "context_window": 131_072,
        "input_cost_per_million": "0.0000",
        "output_cost_per_million": "0.0000",
    },
    {
        "provider": "groq",
        "name": "meta-llama/llama-3.1-8b-instant",
        "display_name": "Llama 3.1 8B Instant (Groq)",
        "max_tokens": 2048,
        "context_window": 131_072,
        "input_cost_per_million": "0.0000",
        "output_cost_per_million": "0.0000",
    },
    {
        "provider": "groq",
        "name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "display_name": "Llama 4 Scout 17B (Groq)",
        "max_tokens": 4096,
        "context_window": 512_000,
        "input_cost_per_million": "0.0000",
        "output_cost_per_million": "0.0000",
    },
    {
        "provider": "groq",
        "name": "openai/gpt-oss-120b",
        "display_name": "GPT-OSS 120B (Groq)",
        "max_tokens": 4096,
        "context_window": 131_072,
        "input_cost_per_million": "0.0000",
        "output_cost_per_million": "0.0000",
    },
]


class Command(BaseCommand):
    help = "Initialize LLM configuration with seed data (idempotent)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--tenant-id",
            type=str,
            default=None,
            help="Tenant UUID to create default AIActionTypes for.",
        )

    def handle(self, *args, **options) -> None:
        from bfagent_llm.django_app.models import (
            AIActionType,
            LLMModel,
            LLMProvider,
        )

        # 1. Seed providers
        provider_cache: dict[str, LLMProvider] = {}
        for data in SEED_PROVIDERS:
            obj, created = LLMProvider.objects.update_or_create(
                name=data["name"],
                defaults={
                    "display_name": data["display_name"],
                    "api_key_env_var": data["api_key_env_var"],
                },
            )
            provider_cache[data["name"]] = obj
            status = "CREATED" if created else "EXISTS"
            self.stdout.write(f"  Provider {data['name']}: {status}")

        # 2. Seed models
        for data in SEED_MODELS:
            provider = provider_cache[data["provider"]]
            defaults = {
                "display_name": data["display_name"],
                "max_tokens": data.get("max_tokens", 4096),
                "context_window": data.get("context_window", 128_000),
                "supports_vision": data.get("supports_vision", False),
                "supports_tools": data.get("supports_tools", True),
                "input_cost_per_million": data.get(
                    "input_cost_per_million", "0.0000"
                ),
                "output_cost_per_million": data.get(
                    "output_cost_per_million", "0.0000"
                ),
                "is_default": data.get("is_default", False),
            }
            obj, created = LLMModel.objects.update_or_create(
                provider=provider,
                name=data["name"],
                defaults=defaults,
            )
            status = "CREATED" if created else "UPDATED"
            self.stdout.write(
                f"  Model {provider.name}:{data['name']}: {status}"
            )

        # 3. Seed default action types (if tenant_id provided)
        tenant_id = options.get("tenant_id")
        if tenant_id:
            try:
                tenant_uuid = UUID(tenant_id)
            except ValueError:
                raise CommandError(
                    f"Invalid tenant-id: {tenant_id}"
                )

            default_model = LLMModel.objects.filter(
                is_default=True, is_active=True
            ).first()

            groq_model = LLMModel.objects.filter(
                provider__name="groq",
                name="qwen-qwen3-32b",
                is_active=True,
            ).first()

            DEFAULT_ACTIONS = [
                {
                    "code": "default_completion",
                    "name": "Default Completion",
                    "description": "General-purpose LLM completion.",
                },
            ]

            for action_data in DEFAULT_ACTIONS:
                obj, created = AIActionType.objects.update_or_create(
                    tenant_id=tenant_uuid,
                    code=action_data["code"],
                    defaults={
                        "name": action_data["name"],
                        "description": action_data["description"],
                        "default_model": default_model,
                        "fallback_model": groq_model,
                    },
                )
                status = "CREATED" if created else "UPDATED"
                self.stdout.write(
                    f"  Action {action_data['code']}: {status}"
                )

        self.stdout.write(
            self.style.SUCCESS("LLM configuration initialized.")
        )
