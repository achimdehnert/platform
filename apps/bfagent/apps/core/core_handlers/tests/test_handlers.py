"""
Tests for Consolidated Core Handlers
====================================

Run with: pytest apps/core/handlers/tests/test_handlers.py -v
"""

from typing import Any, Dict

import pytest

# ==================== Test Base Classes ====================


class TestBaseHandler:
    """Tests for BaseHandler class."""

    def test_handler_init_with_config(self):
        """Test handler initialization with config."""
        from apps.core.handlers import ProcessingHandler

        class TestHandler(ProcessingHandler):
            handler_name = "test.handler"

            def process(self, data, context):
                return {"processed": True}

        handler = TestHandler(config={"key": "value"})
        assert handler.config == {"key": "value"}
        assert handler.handler_name == "test.handler"

    def test_handler_auto_name(self):
        """Test handler auto-generates name from class."""
        from apps.core.handlers import ProcessingHandler

        class MyCustomHandler(ProcessingHandler):
            def process(self, data, context):
                return {}

        handler = MyCustomHandler()
        assert handler.handler_name == "MyCustomHandler"

    def test_handler_get_info(self):
        """Test handler info retrieval."""
        from apps.core.handlers import ProcessingHandler

        class InfoHandler(ProcessingHandler):
            handler_name = "info.handler"
            handler_version = "2.0.0"
            description = "Test description"
            domain = "testing"

            def process(self, data, context):
                return {}

        handler = InfoHandler()
        info = handler.get_info()

        assert info["name"] == "info.handler"
        assert info["version"] == "2.0.0"
        assert info["description"] == "Test description"
        assert info["domain"] == "testing"


class TestInputHandler:
    """Tests for InputHandler class."""

    def test_input_handler_collect(self):
        """Test input handler collect method."""
        from apps.core.handlers import InputHandler

        class FileInputHandler(InputHandler):
            handler_name = "file.input"

            def collect(self, context):
                return {"data": context.get("file_content", "default")}

        handler = FileInputHandler()
        result = handler.execute({"file_content": "test data"})

        assert result["success"] is True
        assert result["data"]["data"] == "test data"


class TestProcessingHandler:
    """Tests for ProcessingHandler class."""

    def test_processing_handler_execute(self):
        """Test processing handler execution."""
        from apps.core.handlers import ProcessingHandler

        class TransformHandler(ProcessingHandler):
            handler_name = "transform.handler"

            def process(self, data, context):
                return {"transformed": data.get("input", "").upper()}

        handler = TransformHandler()
        result = handler.execute({"data": {"input": "hello"}})

        assert result["success"] is True
        assert result["transformed"] == "HELLO"

    def test_processing_handler_with_validation(self):
        """Test processing handler with Pydantic validation (if available)."""
        from apps.core.handlers import ProcessingHandler

        try:
            from pydantic import BaseModel

            class InputSchema(BaseModel):
                name: str
                value: int

            class OutputSchema(BaseModel):
                success: bool
                result: str

            class ValidatedHandler(ProcessingHandler):
                handler_name = "validated.handler"
                InputSchema = InputSchema
                OutputSchema = OutputSchema

                def process(self, data, context):
                    return {"success": True, "result": f"{data['name']}: {data['value']}"}

            handler = ValidatedHandler()
            result = handler.execute({"data": {"name": "test", "value": 42}})

            assert result["success"] is True
            assert result["result"] == "test: 42"

        except ImportError:
            pytest.skip("Pydantic not installed")


class TestOutputHandler:
    """Tests for OutputHandler class."""

    def test_output_handler_parse_and_apply(self):
        """Test output handler parse and apply workflow."""
        from apps.core.handlers import OutputHandler

        created_items = []

        class MockOutputHandler(OutputHandler):
            handler_name = "mock.output"
            supports_multiple_objects = True

            def parse(self, processed_data):
                return [{"item": i} for i in processed_data.get("items", [])]

            def apply(self, data):
                created_items.append(data)
                return data

        handler = MockOutputHandler()
        result = handler.execute({"data": {"items": ["a", "b", "c"]}})

        assert result["success"] is True
        assert result["created_count"] == 3
        assert len(created_items) == 3


# ==================== Test Registry ====================


class TestHandlerRegistry:
    """Tests for HandlerRegistry."""

    def setup_method(self):
        """Clear registry before each test."""
        from apps.core.handlers import HandlerRegistry

        HandlerRegistry.clear()

    def test_register_and_get(self):
        """Test registering and retrieving a handler."""
        from apps.core.handlers import HandlerRegistry, ProcessingHandler

        class TestHandler(ProcessingHandler):
            handler_name = "registry.test"

            def process(self, data, context):
                return {"test": True}

        HandlerRegistry.register(
            name="test.handler", handler_class=TestHandler, version="1.0.0", domain="testing"
        )

        assert HandlerRegistry.exists("test.handler")

        handler = HandlerRegistry.get("test.handler")
        assert handler is not None
        assert handler.handler_name == "registry.test"

    def test_list_by_domain(self):
        """Test listing handlers by domain."""
        from apps.core.handlers import HandlerRegistry, ProcessingHandler

        class Handler1(ProcessingHandler):
            def process(self, data, context):
                return {}

        class Handler2(ProcessingHandler):
            def process(self, data, context):
                return {}

        HandlerRegistry.register("h1", Handler1, domain="domain_a")
        HandlerRegistry.register("h2", Handler2, domain="domain_a")
        HandlerRegistry.register("h3", Handler1, domain="domain_b")

        domain_a_handlers = HandlerRegistry.list_by_domain("domain_a")

        assert len(domain_a_handlers) == 2
        assert "h1" in domain_a_handlers
        assert "h2" in domain_a_handlers
        assert "h3" not in domain_a_handlers

    def test_decorator_registration(self):
        """Test decorator-based registration."""
        from apps.core.handlers import (
            HandlerRegistry,
            ProcessingHandler,
            get_handler,
            register_handler,
        )

        @register_handler("decorated.handler", "2.0.0", domain="test")
        class DecoratedHandler(ProcessingHandler):
            def process(self, data, context):
                return {"decorated": True}

        assert HandlerRegistry.exists("decorated.handler")

        handler = get_handler("decorated.handler")
        result = handler.execute({})

        assert result["success"] is True
        assert result["decorated"] is True

    def test_get_stats(self):
        """Test registry statistics."""
        from apps.core.handlers import HandlerRegistry, InputHandler, ProcessingHandler

        class PHandler(ProcessingHandler):
            def process(self, data, context):
                return {}

        class IHandler(InputHandler):
            def collect(self, context):
                return {}

        HandlerRegistry.register("p1", PHandler, handler_type="processing")
        HandlerRegistry.register("p2", PHandler, handler_type="processing")
        HandlerRegistry.register("i1", IHandler, handler_type="input")

        stats = HandlerRegistry.get_stats()

        assert stats["total"] == 3
        assert stats["by_type"]["processing"] == 2
        assert stats["by_type"]["input"] == 1


# ==================== Test Decorators ====================


class TestDecorators:
    """Tests for handler decorators."""

    def test_with_logging(self):
        """Test logging decorator."""
        from apps.core.handlers import ProcessingHandler
        from apps.core.handlers.decorators import with_logging

        class LoggedHandler(ProcessingHandler):
            handler_name = "logged.handler"

            @with_logging
            def process(self, data, context):
                return {"logged": True}

        handler = LoggedHandler()
        result = handler.process({}, {})

        assert result["logged"] is True

    def test_with_performance_monitoring(self):
        """Test performance monitoring decorator."""
        import time

        from apps.core.handlers import ProcessingHandler
        from apps.core.handlers.decorators import with_performance_monitoring

        class TimedHandler(ProcessingHandler):
            handler_name = "timed.handler"

            @with_performance_monitoring
            def process(self, data, context):
                time.sleep(0.01)  # Small delay
                return {"timed": True}

        handler = TimedHandler()
        result = handler.process({}, {})

        assert result["timed"] is True
        assert "_execution_time_ms" in result
        assert result["_execution_time_ms"] >= 10  # At least 10ms

    def test_validate_context(self):
        """Test context validation decorator."""
        from apps.core.handlers import ProcessingHandler, ValidationError
        from apps.core.handlers.decorators import validate_context

        class ValidatedHandler(ProcessingHandler):
            handler_name = "validated.handler"

            @validate_context(["required_key"])
            def process(self, context, data=None):
                return {"valid": True}

        handler = ValidatedHandler()

        # Should raise ValidationError without required key
        with pytest.raises(ValidationError):
            handler.process({})

        # Should succeed with required key
        result = handler.process({"required_key": "value"})
        assert result["valid"] is True

    def test_retry_on_failure(self):
        """Test retry decorator."""
        from apps.core.handlers import ProcessingHandler
        from apps.core.handlers.decorators import retry_on_failure
        from apps.core.handlers.exceptions import RetryableError

        call_count = 0

        class RetryHandler(ProcessingHandler):
            handler_name = "retry.handler"

            @retry_on_failure(max_retries=2, delay=0.01)
            def process(self, data, context):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise RetryableError("Temporary failure")
                return {"success": True}

        handler = RetryHandler()
        result = handler.process({}, {})

        assert result["success"] is True
        assert call_count == 3  # Initial + 2 retries


# ==================== Test Exceptions ====================


class TestExceptions:
    """Tests for handler exceptions."""

    def test_validation_error(self):
        """Test ValidationError."""
        from apps.core.handlers.exceptions import ValidationError

        error = ValidationError(
            "Missing field", handler_name="test.handler", context={"field": "name"}
        )

        assert "Missing field" in str(error)
        assert error.handler_name == "test.handler"

        error_dict = error.to_dict()
        assert error_dict["error"] == "ValidationError"
        assert error_dict["handler_name"] == "test.handler"

    def test_processing_error_with_original(self):
        """Test ProcessingError with original exception."""
        from apps.core.handlers.exceptions import ProcessingError

        original = ValueError("Original error")
        error = ProcessingError(
            "Processing failed", handler_name="test.handler", original_error=original
        )

        assert error.original_error is original
        error_dict = error.to_dict()
        assert "Original error" in error_dict["original_error"]

    def test_retryable_error(self):
        """Test RetryableError with retry info."""
        from apps.core.handlers.exceptions import RetryableError

        error = RetryableError("Temporary failure", retry_after=10, max_retries=5)

        assert error.retry_after == 10
        assert error.max_retries == 5

        error_dict = error.to_dict()
        assert error_dict["retry_after"] == 10
        assert error_dict["max_retries"] == 5


# ==================== Test Backward Compatibility ====================


class TestBackwardCompatibility:
    """Tests for backward compatibility aliases."""

    def test_base_handler_aliases(self):
        """Test that old import names still work."""
        from apps.core.handlers import (
            BaseInputHandler,
            BaseOutputHandler,
            BaseProcessingHandler,
            InputHandler,
            OutputHandler,
            ProcessingHandler,
        )

        # Aliases should be the same classes
        assert BaseInputHandler is InputHandler
        assert BaseProcessingHandler is ProcessingHandler
        assert BaseOutputHandler is OutputHandler

    def test_genagent_compatibility(self):
        """Test GenAgent compatibility alias."""
        from apps.core.handlers import BaseHandler, GenAgentBaseHandler

        assert GenAgentBaseHandler is BaseHandler


# ==================== Integration Test ====================


class TestIntegration:
    """Integration tests for complete handler workflows."""

    def setup_method(self):
        """Clear registry before each test."""
        from apps.core.handlers import HandlerRegistry

        HandlerRegistry.clear()

    def test_complete_pipeline(self):
        """Test a complete input → processing → output pipeline."""
        from apps.core.handlers import (
            InputHandler,
            OutputHandler,
            ProcessingHandler,
            get_handler,
            register_handler,
        )

        results = []

        @register_handler("pipeline.input", domain="test")
        class PipelineInput(InputHandler):
            def collect(self, context):
                return {"raw_data": context.get("input", [])}

        @register_handler("pipeline.process", domain="test")
        class PipelineProcess(ProcessingHandler):
            def process(self, data, context):
                raw = data.get("raw_data", [])
                return {"processed": [x.upper() for x in raw]}

        @register_handler("pipeline.output", domain="test")
        class PipelineOutput(OutputHandler):
            def parse(self, processed_data):
                return [{"value": v} for v in processed_data.get("processed", [])]

            def apply(self, data):
                results.append(data["value"])
                return data

        # Execute pipeline
        input_handler = get_handler("pipeline.input")
        process_handler = get_handler("pipeline.process")
        output_handler = get_handler("pipeline.output")

        # Step 1: Input
        input_result = input_handler.execute({"input": ["a", "b", "c"]})
        assert input_result["success"]

        # Step 2: Processing
        process_result = process_handler.execute({"data": input_result["data"]})
        assert process_result["success"]

        # Step 3: Output
        output_result = output_handler.execute({"data": process_result})
        assert output_result["success"]
        assert output_result["created_count"] == 3

        # Verify results
        assert results == ["A", "B", "C"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
