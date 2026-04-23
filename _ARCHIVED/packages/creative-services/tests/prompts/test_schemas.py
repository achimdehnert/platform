"""Tests for prompt template schemas."""

import pytest
from datetime import datetime, timezone
from uuid import UUID

from pydantic import ValidationError

from creative_services.prompts.schemas import (
    PromptVariable,
    VariableType,
    LLMConfig,
    RetryConfig,
    PromptTemplateSpec,
    PromptExecution,
    ExecutionStatus,
)


class TestPromptVariable:
    """Tests for PromptVariable schema."""

    def test_minimal_variable(self):
        var = PromptVariable(name="test_var")
        assert var.name == "test_var"
        assert var.var_type == VariableType.STRING
        assert var.required is True
        assert var.default is None

    def test_full_variable(self):
        var = PromptVariable(
            name="genre",
            var_type=VariableType.STRING,
            required=False,
            default="fantasy",
            description="The genre of the story",
            max_length=50,
            allowed_values=["fantasy", "scifi", "mystery"],
            sanitize=True,
            check_injection=True,
        )
        assert var.name == "genre"
        assert var.default == "fantasy"
        assert var.allowed_values == ["fantasy", "scifi", "mystery"]

    def test_name_validation_snake_case(self):
        # Valid names
        PromptVariable(name="valid_name")
        PromptVariable(name="name123")
        PromptVariable(name="a")

        # Invalid names
        with pytest.raises(ValidationError):
            PromptVariable(name="InvalidName")  # CamelCase
        with pytest.raises(ValidationError):
            PromptVariable(name="123name")  # Starts with number
        with pytest.raises(ValidationError):
            PromptVariable(name="name-with-dash")  # Contains dash

    def test_default_only_for_optional(self):
        # Valid: optional with default
        PromptVariable(name="opt", required=False, default="value")

        # Invalid: required with default
        with pytest.raises(ValidationError):
            PromptVariable(name="req", required=True, default="value")

    def test_allowed_values_not_empty(self):
        with pytest.raises(ValidationError):
            PromptVariable(name="test", allowed_values=[])

    def test_validate_value_type_check(self):
        var = PromptVariable(name="count", var_type=VariableType.INTEGER)

        valid, error = var.validate_value(42)
        assert valid is True
        assert error is None

        valid, error = var.validate_value("not an int")
        assert valid is False
        assert "Expected integer" in error

    def test_validate_value_length_check(self):
        var = PromptVariable(name="short", var_type=VariableType.STRING, max_length=10)

        valid, _ = var.validate_value("short")
        assert valid is True

        valid, error = var.validate_value("this is too long")
        assert valid is False
        assert "max length" in error

    def test_validate_value_allowed_values(self):
        var = PromptVariable(
            name="color",
            required=False,
            default="red",
            allowed_values=["red", "green", "blue"],
        )

        valid, _ = var.validate_value("red")
        assert valid is True

        valid, error = var.validate_value("yellow")
        assert valid is False
        assert "not in allowed values" in error

    def test_frozen(self):
        var = PromptVariable(name="test")
        with pytest.raises(ValidationError):
            var.name = "changed"


class TestRetryConfig:
    """Tests for RetryConfig schema."""

    def test_defaults(self):
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay_seconds == 1.0
        assert config.exponential_base == 2.0
        assert 429 in config.retry_on_status_codes

    def test_custom_config(self):
        config = RetryConfig(
            max_attempts=5,
            initial_delay_seconds=0.5,
            max_delay_seconds=60.0,
        )
        assert config.max_attempts == 5
        assert config.initial_delay_seconds == 0.5

    def test_validation_bounds(self):
        with pytest.raises(ValidationError):
            RetryConfig(max_attempts=0)  # Must be >= 1

        with pytest.raises(ValidationError):
            RetryConfig(max_attempts=100)  # Must be <= 10


class TestLLMConfig:
    """Tests for LLMConfig schema."""

    def test_defaults(self):
        config = LLMConfig()
        assert config.tier == "standard"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.retry is not None

    def test_tier_validation(self):
        LLMConfig(tier="fast")
        LLMConfig(tier="standard")
        LLMConfig(tier="quality")
        LLMConfig(tier="premium")

        with pytest.raises(ValidationError):
            LLMConfig(tier="invalid")

    def test_temperature_bounds(self):
        LLMConfig(temperature=0.0)
        LLMConfig(temperature=2.0)

        with pytest.raises(ValidationError):
            LLMConfig(temperature=-0.1)
        with pytest.raises(ValidationError):
            LLMConfig(temperature=2.1)

    def test_get_effective_model(self):
        tier_mapping = {
            "fast": ("openai", "gpt-4o-mini"),
            "standard": ("openai", "gpt-4o"),
            "quality": ("anthropic", "claude-3-sonnet"),
            "premium": ("anthropic", "claude-3-opus"),
        }

        # Tier-based selection
        config = LLMConfig(tier="premium")
        provider, model = config.get_effective_model(tier_mapping)
        assert provider == "anthropic"
        assert model == "claude-3-opus"

        # Direct override
        config = LLMConfig(provider="groq", model="llama-3")
        provider, model = config.get_effective_model(tier_mapping)
        assert provider == "groq"
        assert model == "llama-3"


class TestPromptTemplateSpec:
    """Tests for PromptTemplateSpec schema."""

    def test_minimal_template(self):
        template = PromptTemplateSpec(
            template_key="test.simple.v1",
            domain_code="test",
            name="Simple Test Template",
            system_prompt="You are a helpful assistant.",
            user_prompt="Hello {{ name }}",
        )
        assert template.template_key == "test.simple.v1"
        assert template.is_active is True
        assert template.schema_version == 1

    def test_full_template(self):
        template = PromptTemplateSpec(
            template_key="writing.character.backstory.v1",
            domain_code="writing",
            name="Character Backstory Generator",
            description="Generates detailed character backstories",
            category="character",
            tags=["character", "backstory", "creative"],
            system_prompt="You are a creative writing assistant.",
            user_prompt="Create a backstory for {{ character_name }}",
            variables=[
                PromptVariable(name="character_name", required=True),
                PromptVariable(name="genre", required=False, default="fantasy"),
            ],
            llm_config=LLMConfig(tier="quality", temperature=0.8),
            max_cost_per_execution=0.10,
            track_executions="all",
            author="test@example.com",
        )
        assert len(template.variables) == 2
        assert template.llm_config.tier == "quality"

    def test_template_key_validation(self):
        # Valid keys
        PromptTemplateSpec(
            template_key="a.b.c",
            domain_code="test",
            name="Test",
            system_prompt="sys",
            user_prompt="user",
        )

        # Invalid: uppercase
        with pytest.raises(ValidationError):
            PromptTemplateSpec(
                template_key="Test.Template",
                domain_code="test",
                name="Test",
                system_prompt="sys",
                user_prompt="user",
            )

        # Invalid: starts with number
        with pytest.raises(ValidationError):
            PromptTemplateSpec(
                template_key="1test.template",
                domain_code="test",
                name="Test",
                system_prompt="sys",
                user_prompt="user",
            )

    def test_unique_variable_names(self):
        with pytest.raises(ValidationError) as exc_info:
            PromptTemplateSpec(
                template_key="test.dup.v1",
                domain_code="test",
                name="Test",
                system_prompt="sys",
                user_prompt="user",
                variables=[
                    PromptVariable(name="same_name"),
                    PromptVariable(name="same_name"),
                ],
            )
        assert "Duplicate" in str(exc_info.value)

    def test_tags_normalized(self):
        template = PromptTemplateSpec(
            template_key="test.tags.v1",
            domain_code="test",
            name="Test",
            system_prompt="sys",
            user_prompt="user",
            tags=["TAG1", "  tag2  ", "TAG1"],  # Duplicates and whitespace
        )
        assert "tag1" in template.tags
        assert "tag2" in template.tags
        assert len(template.tags) == 2  # Duplicates removed

    def test_helper_methods(self):
        template = PromptTemplateSpec(
            template_key="test.helpers.v1",
            domain_code="test",
            name="Test",
            system_prompt="sys",
            user_prompt="user",
            variables=[
                PromptVariable(name="required_var", required=True),
                PromptVariable(name="optional_var", required=False, default="default"),
            ],
        )

        assert template.get_required_variables() == ["required_var"]
        assert template.get_optional_variables() == ["optional_var"]
        assert template.get_variable_defaults() == {"optional_var": "default"}
        assert template.has_variable("required_var") is True
        assert template.has_variable("nonexistent") is False
        assert template.get_variable("required_var") is not None
        assert template.get_variable("nonexistent") is None

    def test_frozen_immutability(self):
        template = PromptTemplateSpec(
            template_key="test.frozen.v1",
            domain_code="test",
            name="Test",
            system_prompt="sys",
            user_prompt="user",
        )

        with pytest.raises(ValidationError):
            template.is_active = False

        # Use model_copy for modifications
        new_template = template.model_copy(update={"is_active": False})
        assert new_template.is_active is False
        assert template.is_active is True  # Original unchanged


class TestPromptExecution:
    """Tests for PromptExecution schema."""

    def test_minimal_execution(self):
        execution = PromptExecution(template_key="test.template.v1")
        assert execution.template_key == "test.template.v1"
        assert execution.status == ExecutionStatus.PENDING
        assert isinstance(execution.execution_id, UUID)
        assert execution.started_at is not None

    def test_computed_properties(self):
        execution = PromptExecution(
            template_key="test.v1",
            tokens_input=100,
            tokens_output=50,
            status=ExecutionStatus.SUCCESS,
        )
        assert execution.tokens_total == 150
        assert execution.is_success is True
        assert execution.is_complete is True

    def test_mark_success(self):
        execution = PromptExecution(template_key="test.v1")
        completed = execution.mark_success(
            response_text="Generated response",
            tokens_input=100,
            tokens_output=50,
            cost_dollars=0.01,
            duration_seconds=1.5,
        )

        assert completed.status == ExecutionStatus.SUCCESS
        assert completed.response_text == "Generated response"
        assert completed.tokens_input == 100
        assert completed.completed_at is not None
        assert execution.status == ExecutionStatus.PENDING  # Original unchanged

    def test_mark_success_cached(self):
        execution = PromptExecution(template_key="test.v1")
        completed = execution.mark_success(
            response_text="Cached response",
            tokens_input=0,
            tokens_output=0,
            cost_dollars=0.0,
            duration_seconds=0.01,
            from_cache=True,
        )

        assert completed.status == ExecutionStatus.CACHED
        assert completed.from_cache is True

    def test_mark_failed(self):
        execution = PromptExecution(template_key="test.v1")
        failed = execution.mark_failed(
            error_type="LLMError",
            error_message="Rate limit exceeded",
            duration_seconds=5.0,
            retry_count=3,
        )

        assert failed.status == ExecutionStatus.FAILED
        assert failed.error_type == "LLMError"
        assert failed.retry_count == 3
        assert failed.is_success is False

    def test_to_log_dict(self):
        execution = PromptExecution(
            template_key="test.v1",
            app_name="test_app",
            llm_provider="openai",
            llm_model="gpt-4",
            status=ExecutionStatus.SUCCESS,
        )
        log_dict = execution.to_log_dict()

        assert log_dict["template_key"] == "test.v1"
        assert log_dict["app_name"] == "test_app"
        assert log_dict["status"] == "success"
        assert "execution_id" in log_dict

    def test_frozen_immutability(self):
        execution = PromptExecution(template_key="test.v1")
        with pytest.raises(ValidationError):
            execution.status = ExecutionStatus.SUCCESS
