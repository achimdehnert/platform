"""Tests for SecureTemplateEngine."""

import pytest
from bfagent_llm.engine import (
    SecureTemplateEngine,
    TemplateSecurityError,
    ContextValidationError,
    ValidationResult,
)


class TestSecureTemplateEngine:
    """Tests for SecureTemplateEngine."""
    
    @pytest.fixture
    def engine(self):
        return SecureTemplateEngine()
    
    def test_render_simple_template(self, engine):
        """Should render simple template."""
        result = engine.render_string("Hello {{ name }}!", {"name": "World"})
        assert result == "Hello World!"
    
    def test_render_with_filters(self, engine):
        """Should support custom filters."""
        result = engine.render_string(
            "{{ text | truncate_words(3) }}",
            {"text": "one two three four five"},
        )
        assert result == "one two three..."
    
    def test_render_json_filter(self, engine):
        """Should support json_pretty filter."""
        result = engine.render_string(
            "{{ data | json_pretty }}",
            {"data": {"key": "value"}},
        )
        assert '"key": "value"' in result
    
    def test_block_eval(self, engine):
        """Should block eval() calls."""
        with pytest.raises(TemplateSecurityError) as exc:
            engine.render_string("{{ eval('1+1') }}", {})
        assert "Eval not allowed" in str(exc.value.violations)
    
    def test_block_exec(self, engine):
        """Should block exec() calls."""
        with pytest.raises(TemplateSecurityError) as exc:
            engine.render_string("{{ exec('print(1)') }}", {})
        assert "Exec not allowed" in str(exc.value.violations)
    
    def test_block_dunder(self, engine):
        """Should block __dunder__ access."""
        with pytest.raises(TemplateSecurityError) as exc:
            engine.render_string("{{ obj.__class__ }}", {"obj": {}})
        assert "Dunder attributes not allowed" in str(exc.value.violations)
    
    def test_block_import(self, engine):
        """Should block import statements."""
        with pytest.raises(TemplateSecurityError) as exc:
            engine.render_string("{% import os %}", {})
        assert "Import statements not allowed" in str(exc.value.violations)
    
    def test_sanitize_context_removes_dangerous_keys(self, engine):
        """Should remove dangerous keys from context."""
        context = {
            "safe_key": "value",
            "__builtins__": {},
            "eval": lambda x: x,
            "_private": "hidden",
        }
        result = engine.render_string("{{ safe_key }}", context)
        assert result == "value"
    
    def test_validate_template_valid(self, engine):
        """Should validate correct template."""
        result = engine.validate_template("Hello {{ name }}!")
        assert result.valid
        assert len(result.errors) == 0
    
    def test_validate_template_invalid(self, engine):
        """Should detect security violations."""
        result = engine.validate_template("{{ eval('x') }}")
        assert not result.valid
        assert len(result.errors) > 0
    
    def test_render_full_prompt(self, engine):
        """Should render full prompt with system and user."""
        result = engine.render(
            system_prompt="You are a {{ role }}.",
            user_prompt="Help me with {{ task }}.",
            context={"role": "assistant", "task": "coding"},
        )
        assert result.system_prompt == "You are a assistant."
        assert "Help me with coding." in result.user_prompt
    
    def test_render_with_default_values(self, engine):
        """Should use default values for missing context."""
        result = engine.render(
            system_prompt="You are {{ role }}.",
            user_prompt="Hello!",
            context={},
            default_values={"role": "helpful"},
        )
        assert result.system_prompt == "You are helpful."
    
    def test_context_validation_with_schema(self, engine):
        """Should validate context against schema."""
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
            },
        }
        
        # Valid context
        result = engine.render_string(
            "Hello {{ name }}!",
            {"name": "World"},
            schema=schema,
        )
        assert result == "Hello World!"
        
        # Invalid context (missing required)
        with pytest.raises(ContextValidationError):
            engine.render_string("Hello!", {}, schema=schema)


class TestValidationResult:
    """Tests for ValidationResult."""
    
    def test_bool_valid(self):
        """Valid result should be truthy."""
        result = ValidationResult(valid=True)
        assert bool(result) is True
    
    def test_bool_invalid(self):
        """Invalid result should be falsy."""
        result = ValidationResult(valid=False, errors=["error"])
        assert bool(result) is False
