"""
Tests for management commands (ADR-089).

Covers:
- init_llm_config: idempotent seed data (update_or_create)
- check_llm_config: validation of configuration
"""

import uuid

import pytest
from django.core.management import call_command

from bfagent_llm.django_app.models import (
    AIActionType,
    LLMModel,
    LLMProvider,
)


@pytest.mark.django_db
class TestInitLlmConfig:
    def test_should_create_seed_providers(self):
        call_command("init_llm_config")

        assert LLMProvider.objects.filter(name="openai").exists()
        assert LLMProvider.objects.filter(name="anthropic").exists()
        assert LLMProvider.objects.filter(name="groq").exists()
        assert LLMProvider.objects.filter(name="google").exists()

    def test_should_create_seed_models(self):
        call_command("init_llm_config")

        assert LLMModel.objects.filter(name="gpt-4o").exists()
        assert LLMModel.objects.filter(name="gpt-4o-mini").exists()
        assert LLMModel.objects.filter(
            name="qwen-qwen3-32b"
        ).exists()

    def test_should_be_idempotent(self):
        call_command("init_llm_config")
        count_1 = LLMProvider.objects.count()

        call_command("init_llm_config")
        count_2 = LLMProvider.objects.count()

        assert count_1 == count_2

    def test_should_create_actions_with_tenant_id(self):
        tenant_id = str(uuid.uuid4())
        call_command("init_llm_config", tenant_id=tenant_id)

        assert AIActionType.objects.filter(
            tenant_id=tenant_id,
            code="default_completion",
        ).exists()


@pytest.mark.django_db
class TestCheckLlmConfig:
    def test_should_pass_with_valid_config(self):
        call_command("init_llm_config")
        # Should not raise SystemExit
        call_command("check_llm_config")

    def test_should_warn_about_missing_keys(self, capsys):
        call_command("init_llm_config")
        call_command("check_llm_config")

        captured = capsys.readouterr()
        # API keys won't be found in test env
        assert "WARN" in captured.out or "not found" in captured.out
