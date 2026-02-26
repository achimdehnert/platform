"""
Tests for bfagent_llm.django_app.service (ADR-089).

Covers:
- _get_api_key(): ADR-045 read_secret pattern
- _build_litellm_model_string(): provider/model format
- completion(): DB lookup + LiteLLM call + usage logging
"""

import os
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bfagent_llm.django_app.models import (
    AIActionType,
    AIUsageLog,
    LLMConfigurationError,
    LLMModel,
    LLMProvider,
)
from bfagent_llm.django_app.service import (
    _build_litellm_model_string,
    _get_api_key,
)

TENANT_ID = uuid.uuid4()


@pytest.fixture()
def groq_provider(db):
    return LLMProvider.objects.create(
        name="groq",
        display_name="Groq",
        api_key_env_var="GROQ_API_KEY",
    )


@pytest.fixture()
def groq_model(groq_provider):
    return LLMModel.objects.create(
        provider=groq_provider,
        name="qwen-qwen3-32b",
        display_name="Qwen3 32B",
        max_tokens=4096,
    )


@pytest.fixture()
def test_action(groq_model):
    return AIActionType.objects.create(
        tenant_id=TENANT_ID,
        code="test_completion",
        name="Test Completion",
        default_model=groq_model,
    )


@pytest.mark.django_db
class TestGetApiKey:
    def test_should_find_key_in_env(self, groq_provider):
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"}):
            assert _get_api_key(groq_provider) == "gsk_test"

    def test_should_raise_when_no_key(self, groq_provider):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(LLMConfigurationError, match="nicht gefunden"):
                _get_api_key(groq_provider)

    def test_should_raise_when_no_env_var_configured(self, db):
        provider = LLMProvider.objects.create(
            name="nokey",
            display_name="No Key",
            api_key_env_var="",
        )
        with pytest.raises(
            LLMConfigurationError, match="kein api_key_env_var"
        ):
            _get_api_key(provider)


@pytest.mark.django_db
class TestBuildLitellmModelString:
    def test_should_build_groq_string(self, groq_model):
        result = _build_litellm_model_string(groq_model)
        assert result == "groq/qwen-qwen3-32b"

    def test_should_build_openai_string(self, db):
        provider = LLMProvider.objects.create(
            name="openai",
            display_name="OpenAI",
            api_key_env_var="OPENAI_API_KEY",
        )
        model = LLMModel.objects.create(
            provider=provider,
            name="gpt-4o",
            display_name="GPT-4o",
        )
        assert _build_litellm_model_string(model) == "openai/gpt-4o"


@pytest.mark.django_db(transaction=True)
class TestCompletion:
    @pytest.mark.asyncio
    async def test_should_complete_and_log_usage(self, test_action):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Hello world"))
        ]
        mock_response.model = "groq/qwen-qwen3-32b"
        mock_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=5
        )
        mock_response.model_dump = MagicMock(return_value={})

        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"}),
            patch(
                "bfagent_llm.django_app.service.litellm",
                create=True,
            ) as mock_litellm,
        ):
            mock_litellm.acompletion = AsyncMock(
                return_value=mock_response
            )

            from bfagent_llm.django_app.service import completion

            result = await completion(
                action_code="test_completion",
                messages=[{"role": "user", "content": "Hi"}],
                tenant_id=TENANT_ID,
            )

            assert result.success is True
            assert result.content == "Hello world"
            assert result.tokens_in == 10
            assert result.tokens_out == 5
            assert result.provider == "groq"

            # Verify usage was logged
            assert AIUsageLog.objects.filter(
                tenant_id=TENANT_ID,
                success=True,
            ).exists()

    @pytest.mark.asyncio
    async def test_should_raise_for_unknown_action(self, db):
        with pytest.raises(LLMConfigurationError, match="nicht gefunden"):
            from bfagent_llm.django_app.service import completion

            await completion(
                action_code="nonexistent_action",
                messages=[{"role": "user", "content": "Hi"}],
                tenant_id=TENANT_ID,
            )
