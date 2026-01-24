"""
Unit tests for GenAgent Action Executor.
Tests ACID transaction safety, rollback, and execution logging.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.utils import timezone

from apps.genagent.core.executor import (
    ActionExecutor,
    ExecutionError,
    ValidationError
)
from apps.genagent.core.handler_registry import HandlerRegistry, HandlerNotFoundError
from apps.genagent.models import Action, Phase, ExecutionLog


# Mock Handler Classes
class SuccessfulHandler:
    """Handler that always succeeds."""
    
    def process(self, context):
        return {
            "success": True,
            "message": "Execution successful",
            "data": context.get("test_data", "default")
        }


class FailingHandler:
    """Handler that always fails."""
    
    def process(self, context):
        raise RuntimeError("Intentional failure for testing")


class InvalidResultHandler:
    """Handler that returns invalid result."""
    
    def process(self, context):
        return {"success": False, "error": "Handler indicated failure"}


@pytest.mark.django_db
class TestActionExecutor(TestCase):
    """Test suite for ActionExecutor."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear handler registry
        HandlerRegistry.clear()
        
        # Create test phase
        self.phase = Phase.objects.create(
            name="Test Phase",
            description="Phase for testing",
            order=1
        )
        
        # Create test action
        self.action = Action.objects.create(
            phase=self.phase,
            name="Test Action",
            handler_class="test_handler",
            config={"test_config": "value"},
            order=1
        )
        
        # Register successful handler
        HandlerRegistry.register(
            name="test_handler",
            handler_class=SuccessfulHandler,
            version="1.0.0",
            domains=["test"]
        )
    
    def tearDown(self):
        """Clean up after tests."""
        HandlerRegistry.clear()
    
    def test_successful_execution(self):
        """Test successful action execution."""
        context = {"test_data": "test_value"}
        
        result = ActionExecutor.execute_action(
            action_id=self.action.id,
            context=context
        )
        
        # Check result structure
        assert result["success"] is True
        assert "result" in result
        assert "duration" in result
        assert "execution_log_id" in result
        assert "timestamp" in result
        
        # Check execution log was created
        log = ExecutionLog.objects.get(id=result["execution_log_id"])
        assert log.action == self.action
        assert log.status == "success"
        assert log.duration_seconds >= 0  # Can be 0 for very fast operations
        assert not log.error_message  # Empty string or None
        assert "test_data" in log.input_data["context"]
    
    def test_handler_not_found(self):
        """Test execution with non-existent handler."""
        # Create action with non-existent handler
        action = Action.objects.create(
            phase=self.phase,
            name="Invalid Action",
            handler_class="nonexistent_handler",
            config={},
            order=2
        )
        
        with pytest.raises(ExecutionError, match="Handler not found"):
            ActionExecutor.execute_action(
                action_id=action.id,
                context={}
            )
        
        # Check failure was logged
        log = ExecutionLog.objects.filter(
            action=action,
            status="failed"
        ).first()
        assert log is not None
        assert "Handler not found" in log.error_message
    
    def test_handler_execution_failure(self):
        """Test execution when handler raises exception."""
        # Register failing handler
        HandlerRegistry.register(
            name="failing_handler",
            handler_class=FailingHandler,
            version="1.0.0",
            domains=["test"]
        )
        
        action = Action.objects.create(
            phase=self.phase,
            name="Failing Action",
            handler_class="failing_handler",
            config={},
            order=3
        )
        
        with pytest.raises(ExecutionError, match="Execution failed"):
            ActionExecutor.execute_action(
                action_id=action.id,
                context={}
            )
        
        # Check failure was logged
        log = ExecutionLog.objects.filter(
            action=action,
            status="failed"
        ).first()
        assert log is not None
        assert "Intentional failure" in log.error_message
    
    def test_result_validation_failure(self):
        """Test execution with invalid handler result."""
        # Register handler with invalid result
        HandlerRegistry.register(
            name="invalid_result_handler",
            handler_class=InvalidResultHandler,
            version="1.0.0",
            domains=["test"]
        )
        
        action = Action.objects.create(
            phase=self.phase,
            name="Invalid Result Action",
            handler_class="invalid_result_handler",
            config={},
            order=4
        )
        
        with pytest.raises(ValidationError, match="Handler indicated failure"):
            ActionExecutor.execute_action(
                action_id=action.id,
                context={},
                validate_result=True
            )
    
    def test_transaction_rollback_on_failure(self):
        """Test that database changes are rolled back on failure."""
        initial_log_count = ExecutionLog.objects.count()
        
        # Register failing handler
        HandlerRegistry.register(
            name="failing_handler",
            handler_class=FailingHandler,
            version="1.0.0",
            domains=["test"]
        )
        
        action = Action.objects.create(
            phase=self.phase,
            name="Rollback Test Action",
            handler_class="failing_handler",
            config={},
            order=5
        )
        
        try:
            ActionExecutor.execute_action(
                action_id=action.id,
                context={}
            )
        except ExecutionError:
            pass  # Expected
        
        # Log count should increase by 1 (failure log is created outside transaction)
        assert ExecutionLog.objects.count() == initial_log_count + 1
        
        # But the log should show failure
        failure_log = ExecutionLog.objects.latest('created_at')
        assert failure_log.status == "failed"
    
    def test_snapshot_creation(self):
        """Test that execution snapshot is created correctly."""
        context = {
            "user_input": "test input",
            "config_value": 123
        }
        
        result = ActionExecutor.execute_action(
            action_id=self.action.id,
            context=context
        )
        
        log = ExecutionLog.objects.get(id=result["execution_log_id"])
        snapshot = log.input_data
        
        assert "context" in snapshot
        assert "action_config" in snapshot
        assert "action_handler" in snapshot
        assert "timestamp" in snapshot
        
        assert snapshot["context"]["user_input"] == "test input"
        assert snapshot["action_config"]["test_config"] == "value"
        assert snapshot["action_handler"] == "test_handler"
    
    def test_execution_history(self):
        """Test getting execution history for an action."""
        # Execute action multiple times
        for i in range(3):
            ActionExecutor.execute_action(
                action_id=self.action.id,
                context={"iteration": i}
            )
        
        history = ActionExecutor.get_execution_history(
            action_id=self.action.id,
            limit=10
        )
        
        assert len(history) == 3
        assert all("status" in entry for entry in history)
        assert all("duration" in entry for entry in history)
        assert all(entry["status"] == "success" for entry in history)
    
    def test_execution_stats(self):
        """Test getting execution statistics."""
        # Execute successfully 3 times
        for i in range(3):
            ActionExecutor.execute_action(
                action_id=self.action.id,
                context={}
            )
        
        # Execute with failure once
        HandlerRegistry.register(
            name="failing_handler",
            handler_class=FailingHandler,
            version="1.0.0",
            domains=["test"]
        )
        
        failing_action = Action.objects.create(
            phase=self.phase,
            name="Stats Test Failing",
            handler_class="failing_handler",
            config={},
            order=6
        )
        
        try:
            ActionExecutor.execute_action(
                action_id=failing_action.id,
                context={}
            )
        except ExecutionError:
            pass
        
        # Get stats for successful action
        stats = ActionExecutor.get_execution_stats(self.action.id)
        
        assert stats["total_executions"] == 3
        assert stats["successful"] == 3
        assert stats["failed"] == 0
        assert stats["success_rate"] == 100.0
        assert stats["avg_duration"] >= 0  # Can be 0 for very fast operations
        
        # Get stats for failing action
        fail_stats = ActionExecutor.get_execution_stats(failing_action.id)
        
        assert fail_stats["total_executions"] == 1
        assert fail_stats["successful"] == 0
        assert fail_stats["failed"] == 1
        assert fail_stats["success_rate"] == 0.0
    
    def test_context_merging(self):
        """Test that action config is merged with context."""
        context = {"context_key": "context_value"}
        
        # Create action with config
        action = Action.objects.create(
            phase=self.phase,
            name="Config Merge Test",
            handler_class="test_handler",
            config={"config_key": "config_value"},
            order=7
        )
        
        result = ActionExecutor.execute_action(
            action_id=action.id,
            context=context
        )
        
        # Both context and config should be in snapshot
        log = ExecutionLog.objects.get(id=result["execution_log_id"])
        assert "context_key" in log.input_data["context"]
        assert "config_key" in log.input_data["action_config"]
    
    def test_validation_can_be_disabled(self):
        """Test that result validation can be disabled."""
        # Register handler with invalid result
        HandlerRegistry.register(
            name="invalid_result_handler",
            handler_class=InvalidResultHandler,
            version="1.0.0",
            domains=["test"]
        )
        
        action = Action.objects.create(
            phase=self.phase,
            name="No Validation Test",
            handler_class="invalid_result_handler",
            config={},
            order=8
        )
        
        # Should not raise with validation disabled
        result = ActionExecutor.execute_action(
            action_id=action.id,
            context={},
            validate_result=False
        )
        
        assert result["success"] is True
        assert "execution_log_id" in result


@pytest.mark.django_db
class TestExecutorEdgeCases(TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        HandlerRegistry.clear()
        
        self.phase = Phase.objects.create(
            name="Edge Case Phase",
            order=1
        )
    
    def tearDown(self):
        """Clean up."""
        HandlerRegistry.clear()
    
    def test_empty_context(self):
        """Test execution with empty context."""
        HandlerRegistry.register(
            name="test_handler",
            handler_class=SuccessfulHandler,
            version="1.0.0",
            domains=["test"]
        )
        
        action = Action.objects.create(
            phase=self.phase,
            name="Empty Context Test",
            handler_class="test_handler",
            config={},
            order=1
        )
        
        result = ActionExecutor.execute_action(
            action_id=action.id,
            context={}
        )
        
        assert result["success"] is True
    
    def test_large_context(self):
        """Test execution with large context."""
        HandlerRegistry.register(
            name="test_handler",
            handler_class=SuccessfulHandler,
            version="1.0.0",
            domains=["test"]
        )
        
        action = Action.objects.create(
            phase=self.phase,
            name="Large Context Test",
            handler_class="test_handler",
            config={},
            order=2
        )
        
        # Create large context
        large_context = {
            f"key_{i}": f"value_{i}" * 100
            for i in range(100)
        }
        
        result = ActionExecutor.execute_action(
            action_id=action.id,
            context=large_context
        )
        
        assert result["success"] is True
        
        # Check snapshot was created
        log = ExecutionLog.objects.get(id=result["execution_log_id"])
        assert len(log.input_data["context"]) == 100
