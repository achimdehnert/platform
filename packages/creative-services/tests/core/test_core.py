"""Tests for BaseContext, HandlerResult, and LLMConfig."""

import os
from unittest.mock import patch

from creative_services.core.base_handler import HandlerResult
from creative_services.core.context import (
    BaseContext,
    CharacterContext,
    LocationContext,
    StoryContext,
)
from creative_services.core.llm_client import LLMConfig, LLMProvider


class TestBaseContext:
    """Tests for BaseContext Pydantic v2 model."""

    def test_should_create_with_defaults(self) -> None:
        ctx = BaseContext()
        assert ctx.genre is None
        assert ctx.tone is None
        assert ctx.language == "en"
        assert ctx.style_notes is None

    def test_should_allow_extra_fields(self) -> None:
        ctx = BaseContext(genre="fantasy", custom_field="hello")
        assert ctx.genre == "fantasy"
        assert ctx.custom_field == "hello"  # type: ignore[attr-defined]

    def test_should_inherit_extra_in_subclasses(self) -> None:
        ctx = CharacterContext(
            role="villain",
            custom="extra_value",
        )
        assert ctx.role == "villain"
        assert ctx.custom == "extra_value"  # type: ignore[attr-defined]

    def test_should_create_location_context(self) -> None:
        ctx = LocationContext(location_name="Berlin")
        assert ctx.location_name == "Berlin"
        assert ctx.include_food is True

    def test_should_create_story_context(self) -> None:
        ctx = StoryContext(
            title="My Story",
            target_word_count=2000,
        )
        assert ctx.title == "My Story"
        assert ctx.target_word_count == 2000


class TestHandlerResult:
    """Tests for HandlerResult."""

    def test_should_create_ok_result(self) -> None:
        from pydantic import BaseModel

        class DummyData(BaseModel):
            value: str = "test"

        result = HandlerResult.ok(
            data=DummyData(),
            llm_used="openai:gpt-4o",
            usage={"total_tokens": 100},
        )
        assert result.success is True
        assert result.data.value == "test"
        assert result.llm_used == "openai:gpt-4o"
        assert result.usage == {"total_tokens": 100}

    def test_should_create_fail_result(self) -> None:
        result = HandlerResult.fail(error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_should_not_share_usage_between_instances(self) -> None:
        r1 = HandlerResult(success=True)
        r2 = HandlerResult(success=True)
        r1.usage["key"] = "value"
        assert "key" not in r2.usage


class TestLLMConfig:
    """Tests for LLMConfig model_validator."""

    def test_should_use_explicit_api_key(self) -> None:
        config = LLMConfig(api_key="sk-explicit")
        assert config.api_key == "sk-explicit"

    def test_should_load_openai_key_from_env(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-openai"}):
            config = LLMConfig(provider=LLMProvider.OPENAI)
        assert config.api_key == "sk-env-openai"

    def test_should_load_anthropic_key_from_env(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-env-ant"}):
            config = LLMConfig(provider=LLMProvider.ANTHROPIC)
        assert config.api_key == "sk-env-ant"

    def test_should_not_load_key_for_ollama(self) -> None:
        config = LLMConfig(provider=LLMProvider.OLLAMA)
        assert config.api_key is None

    def test_should_have_sensible_defaults(self) -> None:
        config = LLMConfig()
        assert config.provider == LLMProvider.OPENAI
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
