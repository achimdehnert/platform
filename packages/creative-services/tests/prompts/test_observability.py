"""
Unit tests for the observability module.
"""

import pytest
import logging
from datetime import datetime, timezone
from uuid import uuid4

from creative_services.prompts.observability import (
    PromptEvent,
    EventType,
    emit_event,
    get_event_logger,
    record_execution,
    PROMPT_EXECUTIONS_TOTAL,
    PROMPT_EXECUTION_DURATION,
    is_prometheus_available,
)
from creative_services.prompts.observability.events import (
    emit_execution_started,
    emit_execution_completed,
    emit_execution_failed,
    emit_injection_detected,
)


class TestPromptEvent:
    """Tests for PromptEvent."""

    def test_create_event(self):
        """Test creating a basic event."""
        event = PromptEvent(
            event_type=EventType.EXECUTION_STARTED,
            template_key="test.template.v1",
            app_name="test_app",
        )
        
        assert event.event_type == EventType.EXECUTION_STARTED
        assert event.template_key == "test.template.v1"
        assert event.app_name == "test_app"
        assert event.timestamp is not None

    def test_event_with_execution_id(self):
        """Test event with execution ID."""
        exec_id = uuid4()
        event = PromptEvent(
            event_type=EventType.EXECUTION_COMPLETED,
            execution_id=exec_id,
            template_key="test.template.v1",
        )
        
        assert event.execution_id == exec_id

    def test_event_with_error(self):
        """Test event with error information."""
        event = PromptEvent(
            event_type=EventType.EXECUTION_FAILED,
            template_key="test.template.v1",
            error_type="LLMError",
            error_message="API timeout",
        )
        
        assert event.error_type == "LLMError"
        assert event.error_message == "API timeout"

    def test_event_with_data(self):
        """Test event with custom data."""
        event = PromptEvent(
            event_type=EventType.CACHE_HIT,
            template_key="test.template.v1",
            data={"cache_key": "abc123", "ttl_remaining": 300},
        )
        
        assert event.data["cache_key"] == "abc123"
        assert event.data["ttl_remaining"] == 300

    def test_event_with_duration(self):
        """Test event with duration."""
        event = PromptEvent(
            event_type=EventType.EXECUTION_COMPLETED,
            template_key="test.template.v1",
            duration_ms=1234.5,
        )
        
        assert event.duration_ms == 1234.5

    def test_to_log_dict(self):
        """Test converting event to log dictionary."""
        exec_id = uuid4()
        event = PromptEvent(
            event_type=EventType.EXECUTION_COMPLETED,
            execution_id=exec_id,
            template_key="test.template.v1",
            app_name="test_app",
            user_id="user123",
            duration_ms=500.0,
            data={"tokens": 100},
        )
        
        log_dict = event.to_log_dict()
        
        assert log_dict["event_type"] == "execution.completed"
        assert log_dict["execution_id"] == str(exec_id)
        assert log_dict["template_key"] == "test.template.v1"
        assert log_dict["app_name"] == "test_app"
        assert log_dict["user_id"] == "user123"
        assert log_dict["duration_ms"] == 500.0
        assert log_dict["data"]["tokens"] == 100

    def test_event_is_frozen(self):
        """Test that events are immutable."""
        event = PromptEvent(
            event_type=EventType.EXECUTION_STARTED,
            template_key="test.template.v1",
        )
        
        with pytest.raises(Exception):  # ValidationError for frozen model
            event.template_key = "modified"


class TestEventTypes:
    """Tests for EventType enum."""

    def test_lifecycle_events(self):
        """Test lifecycle event types exist."""
        assert EventType.EXECUTION_STARTED.value == "execution.started"
        assert EventType.EXECUTION_COMPLETED.value == "execution.completed"
        assert EventType.EXECUTION_FAILED.value == "execution.failed"

    def test_cache_events(self):
        """Test cache event types exist."""
        assert EventType.CACHE_HIT.value == "cache.hit"
        assert EventType.CACHE_MISS.value == "cache.miss"
        assert EventType.CACHE_SET.value == "cache.set"

    def test_security_events(self):
        """Test security event types exist."""
        assert EventType.INJECTION_DETECTED.value == "security.injection_detected"
        assert EventType.INPUT_SANITIZED.value == "security.input_sanitized"

    def test_llm_events(self):
        """Test LLM event types exist."""
        assert EventType.LLM_REQUEST_STARTED.value == "llm.request_started"
        assert EventType.LLM_REQUEST_COMPLETED.value == "llm.request_completed"
        assert EventType.LLM_REQUEST_FAILED.value == "llm.request_failed"
        assert EventType.LLM_RETRY.value == "llm.retry"


class TestEmitEvent:
    """Tests for emit_event function."""

    def test_emit_event_logs(self, caplog):
        """Test that emit_event logs the event."""
        event = PromptEvent(
            event_type=EventType.EXECUTION_STARTED,
            template_key="test.template.v1",
            app_name="test_app",
        )
        
        with caplog.at_level(logging.INFO):
            emit_event(event)
        
        assert "execution.started" in caplog.text

    def test_emit_failed_event_logs_error(self):
        """Test that failed events are emitted (log level depends on logger config)."""
        # Get the logger and add a handler to capture output
        logger = get_event_logger()
        original_level = logger.level
        logger.setLevel(logging.DEBUG)
        
        # Create a list to capture log records
        captured = []
        
        class CaptureHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.setLevel(logging.DEBUG)
            
            def emit(self, record):
                captured.append(record)
        
        handler = CaptureHandler()
        logger.addHandler(handler)
        
        try:
            event = PromptEvent(
                event_type=EventType.EXECUTION_FAILED,
                template_key="test.template.v1",
                error_type="TestError",
                error_message="Test failure",
            )
            
            emit_event(event, logger=logger)
            
            # Check that event was logged
            assert len(captured) == 1
            assert "execution.failed" in captured[0].message
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)

    def test_emit_injection_logs_warning(self, caplog):
        """Test that injection events log at warning level."""
        event = PromptEvent(
            event_type=EventType.INJECTION_DETECTED,
            template_key="test.template.v1",
            data={"pattern": "ignore_instructions"},
        )
        
        with caplog.at_level(logging.WARNING):
            emit_event(event)
        
        assert "injection_detected" in caplog.text


class TestConvenienceFunctions:
    """Tests for convenience event functions."""

    def test_emit_execution_started(self, caplog):
        """Test emit_execution_started helper."""
        exec_id = uuid4()
        
        with caplog.at_level(logging.INFO):
            event = emit_execution_started(
                execution_id=exec_id,
                template_key="test.template.v1",
                app_name="test_app",
                variables={"name": "test"},
            )
        
        assert event.event_type == EventType.EXECUTION_STARTED
        assert event.execution_id == exec_id
        assert event.data["variables_count"] == 1

    def test_emit_execution_completed(self, caplog):
        """Test emit_execution_completed helper."""
        exec_id = uuid4()
        
        with caplog.at_level(logging.INFO):
            event = emit_execution_completed(
                execution_id=exec_id,
                template_key="test.template.v1",
                duration_ms=1000.0,
                tokens_total=500,
                cost_dollars=0.01,
                from_cache=False,
            )
        
        assert event.event_type == EventType.EXECUTION_COMPLETED
        assert event.duration_ms == 1000.0
        assert event.data["tokens_total"] == 500

    def test_emit_execution_failed(self, caplog):
        """Test emit_execution_failed helper."""
        exec_id = uuid4()
        
        with caplog.at_level(logging.ERROR):
            event = emit_execution_failed(
                execution_id=exec_id,
                template_key="test.template.v1",
                error_type="LLMError",
                error_message="Timeout",
                duration_ms=5000.0,
            )
        
        assert event.event_type == EventType.EXECUTION_FAILED
        assert event.error_type == "LLMError"

    def test_emit_injection_detected(self, caplog):
        """Test emit_injection_detected helper."""
        with caplog.at_level(logging.WARNING):
            event = emit_injection_detected(
                template_key="test.template.v1",
                variable_name="user_input",
                pattern_matched="ignore_instructions",
                user_id="user123",
            )
        
        assert event.event_type == EventType.INJECTION_DETECTED
        assert event.data["variable_name"] == "user_input"


class TestMetrics:
    """Tests for Prometheus metrics."""

    def test_prometheus_availability(self):
        """Test checking Prometheus availability."""
        # Should return True or False without error
        result = is_prometheus_available()
        assert isinstance(result, bool)

    def test_record_execution_success(self):
        """Test recording successful execution metrics."""
        # Should not raise even if Prometheus not available
        record_execution(
            template_key="test.template.v1",
            app_name="test_app",
            status="success",
            duration_seconds=1.5,
            tokens_input=100,
            tokens_output=200,
            cost_dollars=0.01,
            llm_provider="openai",
        )

    def test_record_execution_failure(self):
        """Test recording failed execution metrics."""
        record_execution(
            template_key="test.template.v1",
            app_name="test_app",
            status="failed",
            duration_seconds=0.5,
            error_type="LLMError",
        )

    def test_record_execution_cached(self):
        """Test recording cached execution metrics."""
        record_execution(
            template_key="test.template.v1",
            app_name="test_app",
            status="cached",
            duration_seconds=0.01,
            from_cache=True,
        )
