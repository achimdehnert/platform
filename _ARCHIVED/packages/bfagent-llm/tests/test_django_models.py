"""
Tests for bfagent_llm.django_app.models (ADR-089).

Covers:
- LLMProvider: name validation, uniqueness
- LLMModel: unique_together, litellm_model_string()
- AIActionType: tenant_id, code validation, get_model(), clean()
- AIUsageLog: tenant_id, cost auto-calculation
- LLMConfigurationError: raised when no model configured
"""

import uuid
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from bfagent_llm.django_app.models import (
    AIActionType,
    AIUsageLog,
    LLMConfigurationError,
    LLMModel,
    LLMProvider,
)

TENANT_ID = uuid.uuid4()


@pytest.fixture()
def openai_provider(db):
    return LLMProvider.objects.create(
        name="openai",
        display_name="OpenAI",
        api_key_env_var="OPENAI_API_KEY",
    )


@pytest.fixture()
def groq_provider(db):
    return LLMProvider.objects.create(
        name="groq",
        display_name="Groq (LPU)",
        api_key_env_var="GROQ_API_KEY",
    )


@pytest.fixture()
def gpt4o(openai_provider):
    return LLMModel.objects.create(
        provider=openai_provider,
        name="gpt-4o",
        display_name="GPT-4o",
        max_tokens=4096,
        input_cost_per_million=Decimal("2.5000"),
        output_cost_per_million=Decimal("10.0000"),
    )


@pytest.fixture()
def qwen_groq(groq_provider):
    return LLMModel.objects.create(
        provider=groq_provider,
        name="qwen-qwen3-32b",
        display_name="Qwen3 32B (Groq)",
        max_tokens=4096,
        input_cost_per_million=Decimal("0.0000"),
        output_cost_per_million=Decimal("0.0000"),
    )


@pytest.mark.django_db
class TestLLMProvider:
    def test_should_create_provider(self, openai_provider):
        assert openai_provider.pk is not None
        assert str(openai_provider) == "OpenAI"

    def test_should_reject_invalid_name(self, db):
        provider = LLMProvider(
            name="OpenAI",  # PascalCase not allowed
            display_name="Test",
        )
        with pytest.raises(ValidationError):
            provider.full_clean()

    def test_should_enforce_unique_name(self, openai_provider):
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            LLMProvider.objects.create(
                name="openai",
                display_name="Duplicate",
            )


@pytest.mark.django_db
class TestLLMModel:
    def test_should_create_model(self, gpt4o):
        assert gpt4o.pk is not None
        assert str(gpt4o) == "openai:gpt-4o"

    def test_should_build_litellm_string(self, gpt4o):
        assert gpt4o.litellm_model_string() == "openai/gpt-4o"

    def test_should_enforce_unique_together(self, openai_provider, gpt4o):
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            LLMModel.objects.create(
                provider=openai_provider,
                name="gpt-4o",
                display_name="Duplicate",
            )


@pytest.mark.django_db
class TestAIActionType:
    def test_should_create_action_with_tenant_id(self, gpt4o):
        action = AIActionType.objects.create(
            tenant_id=TENANT_ID,
            code="test_action",
            name="Test Action",
            default_model=gpt4o,
        )
        assert action.tenant_id == TENANT_ID
        assert str(action) == "test_action (Test Action)"

    def test_should_reject_invalid_code(self, db, gpt4o):
        action = AIActionType(
            tenant_id=TENANT_ID,
            code="AB",  # Too short + uppercase
            name="Bad",
            default_model=gpt4o,
        )
        with pytest.raises(ValidationError):
            action.full_clean()

    def test_should_reject_active_without_default_model(self, db):
        action = AIActionType(
            tenant_id=TENANT_ID,
            code="no_model_action",
            name="No Model",
            is_active=True,
            default_model=None,
        )
        with pytest.raises(ValidationError) as exc_info:
            action.clean()
        assert "default_model" in exc_info.value.message_dict

    def test_should_get_default_model(self, gpt4o):
        action = AIActionType.objects.create(
            tenant_id=TENANT_ID,
            code="get_model_test",
            name="Get Model Test",
            default_model=gpt4o,
        )
        assert action.get_model() == gpt4o

    def test_should_get_fallback_when_default_inactive(
        self, gpt4o, qwen_groq
    ):
        gpt4o.is_active = False
        gpt4o.save()

        action = AIActionType.objects.create(
            tenant_id=TENANT_ID,
            code="fallback_test",
            name="Fallback Test",
            default_model=gpt4o,
            fallback_model=qwen_groq,
        )
        assert action.get_model() == qwen_groq

    def test_should_raise_error_when_no_model(self, db):
        action = AIActionType(
            tenant_id=TENANT_ID,
            code="no_models",
            name="No Models",
            is_active=False,
        )
        action.save()
        with pytest.raises(LLMConfigurationError):
            action.get_model()

    def test_should_enforce_unique_tenant_code(self, gpt4o):
        from django.db import IntegrityError

        AIActionType.objects.create(
            tenant_id=TENANT_ID,
            code="unique_test",
            name="First",
            default_model=gpt4o,
        )
        with pytest.raises(IntegrityError):
            AIActionType.objects.create(
                tenant_id=TENANT_ID,
                code="unique_test",
                name="Duplicate",
                default_model=gpt4o,
            )


@pytest.mark.django_db
class TestAIUsageLog:
    def test_should_auto_calculate_cost(self, gpt4o):
        action = AIActionType.objects.create(
            tenant_id=TENANT_ID,
            code="cost_test",
            name="Cost Test",
            default_model=gpt4o,
        )
        log = AIUsageLog(
            tenant_id=TENANT_ID,
            action_type=action,
            model_used=gpt4o,
            input_tokens=1_000_000,
            output_tokens=500_000,
        )
        log.save()

        assert log.total_tokens == 1_500_000
        # input: 1M * 2.5/1M = 2.5, output: 0.5M * 10/1M = 5.0
        assert float(log.estimated_cost) == pytest.approx(7.5, rel=0.01)

    def test_should_calculate_zero_cost_for_groq(self, qwen_groq):
        action = AIActionType.objects.create(
            tenant_id=TENANT_ID,
            code="groq_cost_test",
            name="Groq Cost Test",
            default_model=qwen_groq,
        )
        log = AIUsageLog(
            tenant_id=TENANT_ID,
            action_type=action,
            model_used=qwen_groq,
            input_tokens=100_000,
            output_tokens=50_000,
        )
        log.save()

        assert log.total_tokens == 150_000
        assert float(log.estimated_cost) == 0.0
