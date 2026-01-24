"""
Test Framework Completeness
"""

import pytest
from pathlib import Path


def test_all_schemas_exist():
    """Test that all required schemas are defined"""
    from apps.bfagent.services.handlers import schemas
    
    required_schemas = [
        "ProjectFieldsConfig",
        "ChapterDataConfig",
        "CharacterDataConfig",
        "WorldDataConfig",
        "UserInputConfig",
        "TemplateRendererConfig",
        "LLMProcessorConfig",
        "FrameworkGeneratorConfig",
        "SimpleTextFieldConfig",
        "ChapterCreatorConfig",
        "MarkdownFileConfig",
    ]
    
    for schema_name in required_schemas:
        assert hasattr(schemas, schema_name), f"Missing schema: {schema_name}"
        print(f"✅ {schema_name}")


def test_all_decorators_exist():
    """Test that all decorators are implemented"""
    from apps.bfagent.services.handlers import decorators
    
    required_decorators = [
        "with_logging",
        "with_performance_monitoring",
        "retry_on_failure",
        "with_caching",
        "validate_context",
        "measure_tokens",
    ]
    
    for decorator_name in required_decorators:
        assert hasattr(decorators, decorator_name), f"Missing decorator: {decorator_name}"
        print(f"✅ {decorator_name}")


def test_registries_exist():
    """Test that registries are implemented"""
    from apps.bfagent.services.handlers import registries
    
    required_classes = [
        "InputHandlerRegistry",
        "ProcessingHandlerRegistry",
        "OutputHandlerRegistry",
        "input_registry",
        "processing_registry",
        "output_registry",
    ]
    
    for class_name in required_classes:
        assert hasattr(registries, class_name), f"Missing: {class_name}"
        print(f"✅ {class_name}")


def test_all_input_handlers_exist():
    """Test that all input handlers exist"""
    from apps.bfagent.services.handlers import input as input_handlers
    
    required_handlers = [
        "ProjectFieldsInputHandler",
        "ChapterDataHandler",
        "CharacterDataHandler",
        "WorldDataHandler",
        "UserInputHandler",
    ]
    
    for handler_name in required_handlers:
        assert hasattr(input_handlers, handler_name), f"Missing handler: {handler_name}"
        print(f"✅ {handler_name}")


def test_all_processing_handlers_exist():
    """Test that all processing handlers exist"""
    from apps.bfagent.services.handlers import processing
    
    required_handlers = [
        "TemplateRendererHandler",
        "LLMProcessingHandler",
        "FrameworkGeneratorHandler",
    ]
    
    for handler_name in required_handlers:
        assert hasattr(processing, handler_name), f"Missing handler: {handler_name}"
        print(f"✅ {handler_name}")


def test_all_output_handlers_exist():
    """Test that all output handlers exist"""
    from apps.bfagent.services.handlers import output
    
    required_handlers = [
        "SimpleTextFieldHandler",
        "ChapterCreatorHandler",
        "MarkdownFileOutputHandler",
    ]
    
    for handler_name in required_handlers:
        assert hasattr(output, handler_name), f"Missing handler: {handler_name}"
        print(f"✅ {handler_name}")


def test_handlers_can_be_instantiated():
    """Test that handlers can be created with valid config"""
    from apps.bfagent.services.handlers.input import ChapterDataHandler
    from apps.bfagent.services.handlers.processing import TemplateRendererHandler
    from apps.bfagent.services.handlers.output import SimpleTextFieldHandler
    
    # Input handler
    input_handler = ChapterDataHandler({"include_outline": True, "limit": 5})
    assert input_handler.handler_name == "chapter_data"
    print("✅ ChapterDataHandler instantiated")
    
    # Processing handler
    processing_handler = TemplateRendererHandler({
        "template": "Test {{ value }}",
        "strict": False
    })
    assert processing_handler.handler_name == "template_renderer"
    print("✅ TemplateRendererHandler instantiated")
    
    # Output handler
    output_handler = SimpleTextFieldHandler({
        "target_model": "BookProjects",
        "target_field": "description",
        "target_instance": "current"
    })
    assert output_handler.handler_name == "simple_text_field"
    print("✅ SimpleTextFieldHandler instantiated")


def test_pydantic_validation_works():
    """Test that Pydantic validation catches errors"""
    from apps.bfagent.services.handlers.input import ChapterDataHandler
    
    # Valid config
    try:
        handler = ChapterDataHandler({"limit": 50})
        print("✅ Valid config accepted")
    except ValueError:
        pytest.fail("Valid config rejected")
    
    # Invalid config - limit too high
    try:
        handler = ChapterDataHandler({"limit": 200})
        pytest.fail("Invalid config accepted")
    except ValueError as e:
        print(f"✅ Invalid config rejected: {e}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🔍 Framework Completeness Test")
    print("="*80 + "\n")
    
    test_all_schemas_exist()
    print()
    test_all_decorators_exist()
    print()
    test_registries_exist()
    print()
    test_all_input_handlers_exist()
    print()
    test_all_processing_handlers_exist()
    print()
    test_all_output_handlers_exist()
    print()
    test_handlers_can_be_instantiated()
    print()
    test_pydantic_validation_works()
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED - Framework is COMPLETE!")
    print("="*80 + "\n")