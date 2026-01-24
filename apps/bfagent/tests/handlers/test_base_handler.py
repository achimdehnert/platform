"""
Unit Tests for BaseHandler V2.0
================================

Tests three-phase processing, validation, transaction safety, and error handling.

Author: BF Agent Framework
Date: 2025-11-02
"""

import pytest
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
from django.test import TestCase
from django.db import transaction

from apps.bfagent.handlers.base_handler_v2 import (
    BaseHandler,
    HandlerError,
    ValidationError,
    ProcessingError,
    HandlerMetrics
)


# ==================== TEST FIXTURES ====================

class TestInputSchema(BaseModel):
    """Test input schema"""
    user_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=100)
    optional_field: Optional[str] = None


class TestOutputSchema(BaseModel):
    """Test output schema"""
    success: bool = True
    action: str
    result: str
    message: str


class SuccessfulHandler(BaseHandler):
    """Handler that succeeds"""
    
    InputSchema = TestInputSchema
    OutputSchema = TestOutputSchema
    
    def process(self, validated_input: TestInputSchema) -> Dict[str, Any]:
        return {
            'result': f"Processed message: {validated_input.message}",
            'user_id': validated_input.user_id
        }


class FailingHandler(BaseHandler):
    """Handler that fails during processing"""
    
    InputSchema = TestInputSchema
    OutputSchema = TestOutputSchema
    
    def process(self, validated_input: TestInputSchema) -> Dict[str, Any]:
        raise ProcessingError("Simulated processing failure")


class InvalidOutputHandler(BaseHandler):
    """Handler that returns invalid output"""
    
    InputSchema = TestInputSchema
    OutputSchema = TestOutputSchema
    
    def process(self, validated_input: TestInputSchema) -> Dict[str, Any]:
        return {
            'result': 123  # Wrong type! Should be str, not int
        }


# ==================== TESTS ====================

class TestHandlerMetrics(TestCase):
    """Test HandlerMetrics class"""
    
    def test_metrics_initialization(self):
        """Test metrics are initialized correctly"""
        metrics = HandlerMetrics()
        
        assert metrics.start_time is None
        assert metrics.end_time is None
        assert metrics.success is False
        assert metrics.error is None
        assert metrics.input_size == 0
        assert metrics.output_size == 0
    
    def test_metrics_duration_calculation(self):
        """Test duration calculation"""
        metrics = HandlerMetrics()
        metrics.start_time = 100.0
        metrics.end_time = 105.5
        
        assert metrics.duration == 5.5
    
    def test_metrics_to_dict(self):
        """Test metrics serialization"""
        metrics = HandlerMetrics()
        metrics.start_time = 100.0
        metrics.end_time = 105.5
        metrics.success = True
        metrics.input_size = 1000
        metrics.output_size = 2000
        
        result = metrics.to_dict()
        
        assert result['duration_seconds'] == 5.5
        assert result['success'] is True
        assert result['error'] is None
        assert result['input_size_bytes'] == 1000
        assert result['output_size_bytes'] == 2000


class TestBaseHandlerInitialization(TestCase):
    """Test BaseHandler initialization"""
    
    def test_handler_requires_input_schema(self):
        """Test handler requires InputSchema"""
        
        class NoInputSchemaHandler(BaseHandler):
            OutputSchema = TestOutputSchema
        
        with pytest.raises(ValueError, match="must define InputSchema"):
            NoInputSchemaHandler()
    
    def test_handler_requires_output_schema(self):
        """Test handler requires OutputSchema"""
        
        class NoOutputSchemaHandler(BaseHandler):
            InputSchema = TestInputSchema
        
        with pytest.raises(ValueError, match="must define OutputSchema"):
            NoOutputSchemaHandler()
    
    def test_handler_initialization_success(self):
        """Test successful handler initialization"""
        handler = SuccessfulHandler()
        
        assert handler.InputSchema == TestInputSchema
        assert handler.OutputSchema == TestOutputSchema
        assert handler.metrics is not None
        assert handler.logger is not None


class TestThreePhaseProcessing(TestCase):
    """Test three-phase processing (Input → Process → Output)"""
    
    def test_successful_execution(self):
        """Test successful three-phase execution"""
        handler = SuccessfulHandler()
        
        input_data = {
            'user_id': 1,
            'message': 'Hello, world!'
        }
        
        result = handler.execute(input_data)
        
        # Check success
        assert result['success'] is True
        assert result['action'] == 'successful'
        assert 'result' in result
        assert 'Processed message: Hello, world!' in result['result']
        
        # Check metadata
        assert '_metadata' in result
        assert result['_metadata']['handler'] == 'SuccessfulHandler'
        assert result['_metadata']['success'] is True
        
        # Check metrics
        metrics = result['_metadata']['metrics']
        assert metrics['success'] is True
        assert metrics['duration_seconds'] >= 0  # May be 0 for very fast execution
        assert metrics['input_size_bytes'] > 0
        assert metrics['output_size_bytes'] > 0
    
    def test_input_validation_phase(self):
        """Test Phase 1: Input validation"""
        handler = SuccessfulHandler()
        
        # Invalid user_id (must be > 0)
        invalid_input = {
            'user_id': -1,
            'message': 'Test'
        }
        
        result = handler.execute(invalid_input)
        
        assert result['success'] is False
        assert result['error_type'] == 'validation_error'
        assert 'errors' in result
        assert len(result['errors']) > 0
    
    def test_processing_phase_error(self):
        """Test Phase 2: Processing error handling"""
        handler = FailingHandler()
        
        input_data = {
            'user_id': 1,
            'message': 'Test'
        }
        
        result = handler.execute(input_data)
        
        assert result['success'] is False
        assert result['error_type'] == 'processing_error'
        assert 'Simulated processing failure' in result['message']
    
    def test_output_validation_phase(self):
        """Test Phase 3: Output validation"""
        handler = InvalidOutputHandler()
        
        input_data = {
            'user_id': 1,
            'message': 'Test'
        }
        
        result = handler.execute(input_data)
        
        assert result['success'] is False
        assert result['error_type'] == 'processing_error'
        assert 'Output validation failed' in result['message']


class TestInputValidation(TestCase):
    """Test input validation with Pydantic"""
    
    def test_valid_input(self):
        """Test valid input passes validation"""
        handler = SuccessfulHandler()
        
        input_data = {
            'user_id': 1,
            'message': 'Valid message',
            'optional_field': 'Optional value'
        }
        
        result = handler.execute(input_data)
        assert result['success'] is True
    
    def test_missing_required_field(self):
        """Test missing required field fails"""
        handler = SuccessfulHandler()
        
        input_data = {
            'user_id': 1
            # Missing 'message'
        }
        
        result = handler.execute(input_data)
        
        assert result['success'] is False
        assert result['error_type'] == 'validation_error'
        assert any('message' in str(err) for err in result['errors'])
    
    def test_invalid_field_type(self):
        """Test invalid field type fails"""
        handler = SuccessfulHandler()
        
        input_data = {
            'user_id': 'not_an_integer',
            'message': 'Test'
        }
        
        result = handler.execute(input_data)
        
        assert result['success'] is False
        assert result['error_type'] == 'validation_error'
    
    def test_field_constraints(self):
        """Test field constraints are enforced"""
        handler = SuccessfulHandler()
        
        # Message too long
        input_data = {
            'user_id': 1,
            'message': 'x' * 101  # Max is 100
        }
        
        result = handler.execute(input_data)
        
        assert result['success'] is False
        assert result['error_type'] == 'validation_error'
    
    def test_optional_fields(self):
        """Test optional fields work correctly"""
        handler = SuccessfulHandler()
        
        # Without optional field
        input_data = {
            'user_id': 1,
            'message': 'Test'
        }
        
        result = handler.execute(input_data)
        assert result['success'] is True
        
        # With optional field
        input_data['optional_field'] = 'Optional'
        result = handler.execute(input_data)
        assert result['success'] is True


class TestTransactionSafety(TestCase):
    """Test transaction safety and rollback"""
    
    def test_transaction_context_enabled_by_default(self):
        """Test transactions are enabled by default"""
        handler = SuccessfulHandler()
        assert handler._should_use_transaction() is True
    
    def test_transaction_can_be_disabled(self):
        """Test transactions can be disabled"""
        
        class NoTransactionHandler(SuccessfulHandler):
            def _should_use_transaction(self) -> bool:
                return False
        
        handler = NoTransactionHandler()
        assert handler._should_use_transaction() is False


class TestErrorHandling(TestCase):
    """Test error handling and context sanitization"""
    
    def test_validation_error_response(self):
        """Test validation error response format"""
        handler = SuccessfulHandler()
        
        result = handler.execute({'user_id': -1, 'message': 'Test'})
        
        assert result['success'] is False
        assert result['error_type'] == 'validation_error'
        assert 'message' in result
        assert 'errors' in result
        assert 'timestamp' in result
    
    def test_processing_error_response(self):
        """Test processing error response format"""
        handler = FailingHandler()
        
        result = handler.execute({'user_id': 1, 'message': 'Test'})
        
        assert result['success'] is False
        assert result['error_type'] == 'processing_error'
        assert 'message' in result
        assert 'context' in result
        assert 'timestamp' in result
    
    def test_context_sanitization_removes_sensitive_data(self):
        """Test sensitive data is removed from error context"""
        handler = SuccessfulHandler()
        
        context = {
            'user_id': 1,
            'password': 'secret123',
            'api_key': 'sk-1234567890',
            'normal_field': 'visible'
        }
        
        sanitized = handler._sanitize_context(context)
        
        assert sanitized['password'] == '***REDACTED***'
        assert sanitized['api_key'] == '***REDACTED***'
        assert sanitized['normal_field'] == 'visible'
    
    def test_context_sanitization_truncates_large_strings(self):
        """Test large strings are truncated"""
        handler = SuccessfulHandler()
        
        context = {
            'large_field': 'x' * 500
        }
        
        sanitized = handler._sanitize_context(context)
        
        assert len(sanitized['large_field']) == 203  # 200 + '...'
        assert sanitized['large_field'].endswith('...')


class TestActionNameGeneration(TestCase):
    """Test action name generation from class name"""
    
    def test_action_name_from_handler_class(self):
        """Test action name is generated from class name"""
        handler = SuccessfulHandler()
        action = handler._get_action_name()
        
        assert action == 'successful'
    
    def test_action_name_converts_camel_case(self):
        """Test camelCase is converted to snake_case"""
        
        class MyComplexHandler(BaseHandler):
            InputSchema = TestInputSchema
            OutputSchema = TestOutputSchema
            
            def process(self, validated_input):
                return {'result': 'test'}
        
        handler = MyComplexHandler()
        action = handler._get_action_name()
        
        assert action == 'my_complex'


class TestMetadataTracking(TestCase):
    """Test metadata tracking in responses"""
    
    def test_metadata_included_in_response(self):
        """Test metadata is included in successful response"""
        handler = SuccessfulHandler()
        
        result = handler.execute({'user_id': 1, 'message': 'Test'})
        
        assert '_metadata' in result
        assert 'handler' in result['_metadata']
        assert 'version' in result['_metadata']
        assert 'executed_at' in result['_metadata']
        assert 'metrics' in result['_metadata']
    
    def test_metadata_contains_correct_handler_name(self):
        """Test metadata contains correct handler name"""
        handler = SuccessfulHandler()
        
        result = handler.execute({'user_id': 1, 'message': 'Test'})
        
        assert result['_metadata']['handler'] == 'SuccessfulHandler'
    
    def test_metadata_contains_execution_metrics(self):
        """Test metadata contains execution metrics"""
        handler = SuccessfulHandler()
        
        result = handler.execute({'user_id': 1, 'message': 'Test'})
        
        metrics = result['_metadata']['metrics']
        assert 'duration_seconds' in metrics
        assert 'success' in metrics
        assert 'input_size_bytes' in metrics
        assert 'output_size_bytes' in metrics


# ==================== INTEGRATION TESTS ====================

class TestEndToEndIntegration(TestCase):
    """End-to-end integration tests"""
    
    def test_complete_successful_flow(self):
        """Test complete successful execution flow"""
        handler = SuccessfulHandler()
        
        input_data = {
            'user_id': 123,
            'message': 'Integration test message',
            'optional_field': 'Extra data'
        }
        
        result = handler.execute(input_data)
        
        # Verify all phases completed
        assert result['success'] is True
        assert result['action'] == 'successful'
        assert 'Integration test message' in result['result']
        
        # Verify metadata
        assert result['_metadata']['handler'] == 'SuccessfulHandler'
        assert result['_metadata']['metrics']['success'] is True
        assert result['_metadata']['metrics']['duration_seconds'] >= 0  # May be 0 for very fast execution
    
    def test_complete_failure_flow(self):
        """Test complete failure handling flow"""
        handler = FailingHandler()
        
        input_data = {
            'user_id': 123,
            'message': 'Will fail'
        }
        
        result = handler.execute(input_data)
        
        # Verify error handling
        assert result['success'] is False
        assert result['error_type'] == 'processing_error'
        assert 'Simulated processing failure' in result['message']
        assert 'context' in result
        assert 'timestamp' in result


# ==================== PERFORMANCE TESTS ====================

class TestPerformance(TestCase):
    """Performance and metrics tests"""
    
    def test_metrics_track_execution_time(self):
        """Test metrics accurately track execution time"""
        handler = SuccessfulHandler()
        
        result = handler.execute({'user_id': 1, 'message': 'Test'})
        
        duration = result['_metadata']['metrics']['duration_seconds']
        assert duration >= 0  # May be 0 for very fast execution
        assert duration < 1.0  # Should be very fast
    
    def test_metrics_track_input_output_sizes(self):
        """Test metrics track input/output sizes"""
        handler = SuccessfulHandler()
        
        input_data = {
            'user_id': 1,
            'message': 'Test message with some length'
        }
        
        result = handler.execute(input_data)
        
        metrics = result['_metadata']['metrics']
        assert metrics['input_size_bytes'] > 0
        assert metrics['output_size_bytes'] > 0
        assert metrics['output_size_bytes'] > metrics['input_size_bytes']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
