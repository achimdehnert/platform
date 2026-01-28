"""
Unit tests for the migration module.
"""

import pytest
from datetime import datetime, timezone

from creative_services.prompts import (
    PromptTemplateSpec,
    PromptVariable,
    LLMConfig,
)
from creative_services.prompts.migration import (
    BFAgentTemplateAdapter,
    convert_bfagent_template,
    convert_to_bfagent_format,
)


class MockBFAgentTemplate:
    """Mock BFAgent PromptTemplate for testing."""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.template_key = kwargs.get("template_key", "test.template.v1")
        self.name = kwargs.get("name", "Test Template")
        self.description = kwargs.get("description", "A test template")
        self.category = kwargs.get("category", "character")
        self.version = kwargs.get("version", 1)
        self.system_prompt = kwargs.get("system_prompt", "You are a helpful assistant.")
        self.user_prompt_template = kwargs.get("user_prompt_template", "Hello {{ name }}")
        self.required_variables = kwargs.get("required_variables", ["name"])
        self.optional_variables = kwargs.get("optional_variables", ["greeting"])
        self.variable_defaults = kwargs.get("variable_defaults", {"greeting": "Hello"})
        self.is_active = kwargs.get("is_active", True)
        self.max_tokens = kwargs.get("max_tokens", 1000)
        self.temperature = kwargs.get("temperature", 0.7)
        self.top_p = kwargs.get("top_p", 1.0)
        self.preferred_llm = kwargs.get("preferred_llm", None)
        self.tags = kwargs.get("tags", None)
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        self.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))


class MockLLM:
    """Mock LLM model for testing."""
    
    def __init__(self, provider="openai", llm_name="gpt-4"):
        self.provider = provider
        self.llm_name = llm_name


class TestBFAgentTemplateAdapter:
    """Tests for BFAgentTemplateAdapter."""

    def test_from_django_model_basic(self):
        """Test converting a basic BFAgent template."""
        mock_template = MockBFAgentTemplate()
        adapter = BFAgentTemplateAdapter()
        
        spec = adapter.from_django_model(mock_template)
        
        assert spec.template_key == "test.template.v1"
        assert spec.name == "Test Template"
        assert spec.system_prompt == "You are a helpful assistant."
        assert spec.user_prompt == "Hello {{ name }}"

    def test_from_django_model_variables(self):
        """Test that variables are correctly converted."""
        mock_template = MockBFAgentTemplate(
            required_variables=["name", "age"],
            optional_variables=["title"],
            variable_defaults={"title": "Mr."},
        )
        adapter = BFAgentTemplateAdapter()
        
        spec = adapter.from_django_model(mock_template)
        
        assert len(spec.variables) == 3
        
        # Check required variables
        name_var = next(v for v in spec.variables if v.name == "name")
        assert name_var.required is True
        
        age_var = next(v for v in spec.variables if v.name == "age")
        assert age_var.required is True
        
        # Check optional variable with default
        title_var = next(v for v in spec.variables if v.name == "title")
        assert title_var.required is False
        assert title_var.default == "Mr."

    def test_from_django_model_llm_config(self):
        """Test that LLM config is correctly converted."""
        mock_template = MockBFAgentTemplate(
            max_tokens=2000,
            temperature=0.9,
            top_p=0.95,
            preferred_llm=MockLLM(provider="anthropic", llm_name="claude-3"),
        )
        adapter = BFAgentTemplateAdapter()
        
        spec = adapter.from_django_model(mock_template)
        
        assert spec.llm_config is not None
        assert spec.llm_config.max_tokens == 2000
        assert spec.llm_config.temperature == 0.9
        assert spec.llm_config.provider == "anthropic"
        assert spec.llm_config.model == "claude-3"

    def test_from_django_model_domain_mapping(self):
        """Test that category is mapped to domain_code."""
        adapter = BFAgentTemplateAdapter()
        
        # Character category -> writing domain
        char_template = MockBFAgentTemplate(category="character")
        spec = adapter.from_django_model(char_template)
        assert spec.domain_code == "writing"
        
        # Chapter category -> writing domain
        chapter_template = MockBFAgentTemplate(category="chapter")
        spec = adapter.from_django_model(chapter_template)
        assert spec.domain_code == "writing"
        
        # Unknown category -> general domain
        unknown_template = MockBFAgentTemplate(category="unknown")
        spec = adapter.from_django_model(unknown_template)
        assert spec.domain_code == "general"

    def test_from_django_model_schema_version(self):
        """Test that schema_version is correctly set."""
        mock_template = MockBFAgentTemplate(id=42, category="character", version=3)
        adapter = BFAgentTemplateAdapter()
        
        spec = adapter.from_django_model(mock_template)
        
        assert spec.schema_version == 3

    def test_from_django_model_tags(self):
        """Test that tags are correctly parsed."""
        adapter = BFAgentTemplateAdapter()
        
        # String tags
        template1 = MockBFAgentTemplate(category="character", tags="fantasy, scifi")
        spec1 = adapter.from_django_model(template1)
        assert "fantasy" in spec1.tags
        assert "scifi" in spec1.tags
        
        # List tags
        template2 = MockBFAgentTemplate(category="chapter", tags=["Drama", "Romance"])
        spec2 = adapter.from_django_model(template2)
        assert "drama" in spec2.tags
        assert "romance" in spec2.tags

    def test_to_django_dict_basic(self, simple_template):
        """Test converting PromptTemplateSpec to BFAgent dict."""
        adapter = BFAgentTemplateAdapter()
        
        result = adapter.to_django_dict(simple_template)
        
        assert result["template_key"] == simple_template.template_key
        assert result["name"] == simple_template.name
        assert result["system_prompt"] == simple_template.system_prompt
        assert result["user_prompt_template"] == simple_template.user_prompt

    def test_to_django_dict_variables(self):
        """Test that variables are correctly converted back."""
        spec = PromptTemplateSpec(
            template_key="test.vars.v1",
            domain_code="test",
            name="Test",
            system_prompt="System",
            user_prompt="User",
            variables=[
                PromptVariable(name="required_var", required=True),
                PromptVariable(name="optional_var", required=False, default="default"),
            ],
        )
        adapter = BFAgentTemplateAdapter()
        
        result = adapter.to_django_dict(spec)
        
        assert "required_var" in result["required_variables"]
        assert "optional_var" in result["optional_variables"]
        assert result["variable_defaults"]["optional_var"] == "default"

    def test_to_django_dict_llm_config(self):
        """Test that LLM config is correctly converted back."""
        spec = PromptTemplateSpec(
            template_key="test.llm.v1",
            domain_code="test",
            name="Test",
            system_prompt="System",
            user_prompt="User",
            llm_config=LLMConfig(
                max_tokens=2000,
                temperature=0.8,
                top_p=0.9,
            ),
        )
        adapter = BFAgentTemplateAdapter()
        
        result = adapter.to_django_dict(spec)
        
        assert result["max_tokens"] == 2000
        assert result["temperature"] == 0.8
        assert result["top_p"] == 0.9

    def test_roundtrip_conversion(self):
        """Test that conversion is reversible."""
        mock_template = MockBFAgentTemplate(
            template_key="roundtrip.test.v1",
            name="Roundtrip Test",
            required_variables=["input"],
            optional_variables=["style"],
            variable_defaults={"style": "formal"},
        )
        adapter = BFAgentTemplateAdapter()
        
        # Convert to spec
        spec = adapter.from_django_model(mock_template)
        
        # Convert back to dict
        result = adapter.to_django_dict(spec)
        
        # Verify key fields match
        assert result["template_key"] == mock_template.template_key
        assert result["name"] == mock_template.name
        assert "input" in result["required_variables"]
        assert "style" in result["optional_variables"]


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_convert_bfagent_template(self):
        """Test convert_bfagent_template function."""
        mock_template = MockBFAgentTemplate()
        
        spec = convert_bfagent_template(mock_template)
        
        assert isinstance(spec, PromptTemplateSpec)
        assert spec.template_key == mock_template.template_key

    def test_convert_to_bfagent_format(self, simple_template):
        """Test convert_to_bfagent_format function."""
        result = convert_to_bfagent_format(simple_template)
        
        assert isinstance(result, dict)
        assert result["template_key"] == simple_template.template_key
