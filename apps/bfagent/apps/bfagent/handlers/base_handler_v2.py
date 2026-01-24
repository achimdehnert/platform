"""
Base Handler Framework V2.0
============================

Three-phase processing architecture:
1. INPUT: Pydantic validation
2. PROCESSING: Business logic with transaction safety
3. OUTPUT: Structured response formatting

Author: BF Agent Framework
Date: 2025-11-02
"""

from typing import TypeVar, Generic, Dict, Any, Type, Optional
from pydantic import BaseModel, ValidationError as PydanticValidationError
from django.db import transaction
from django.utils import timezone
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Type variables for generics
InputT = TypeVar('InputT', bound=BaseModel)
OutputT = TypeVar('OutputT', bound=BaseModel)


class HandlerError(Exception):
    """Base exception for handler errors"""
    pass


class ValidationError(HandlerError):
    """Input validation failed"""
    pass


class ProcessingError(HandlerError):
    """Business logic processing failed"""
    pass


class HandlerMetrics:
    """Track handler execution metrics"""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.success: bool = False
        self.error: Optional[str] = None
        self.input_size: int = 0
        self.output_size: int = 0
    
    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'duration_seconds': round(self.duration, 3),
            'success': self.success,
            'error': self.error,
            'input_size_bytes': self.input_size,
            'output_size_bytes': self.output_size
        }


class BaseHandler(Generic[InputT, OutputT]):
    """
    Base handler with three-phase processing
    
    Usage:
        class MyHandler(BaseHandler):
            class InputSchema(BaseModel):
                field1: int
                field2: str
            
            class OutputSchema(BaseModel):
                result: str
            
            def process(self, validated_input: InputSchema) -> Dict[str, Any]:
                # Your logic here
                return {'result': 'success'}
    """
    
    # Override these in subclasses
    InputSchema: Type[BaseModel] = None
    OutputSchema: Type[BaseModel] = None
    
    # Metadata
    handler_name: str = None
    handler_version: str = '1.0.0'
    domain: str = 'general'
    category: str = 'processing'
    
    def __init__(self):
        self.metrics = HandlerMetrics()
        self.logger = logger
        
        # Validation
        if not self.InputSchema:
            raise ValueError(f"{self.__class__.__name__} must define InputSchema")
        if not self.OutputSchema:
            raise ValueError(f"{self.__class__.__name__} must define OutputSchema")
    
    def execute(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point - orchestrates three phases
        
        Args:
            raw_input: Unvalidated input dictionary
            
        Returns:
            Validated output dictionary
        """
        self.metrics.start_time = time.time()
        self.metrics.input_size = len(str(raw_input))
        
        try:
            # PHASE 1: VALIDATE INPUT
            self.logger.info(
                f"{self.__class__.__name__}: Phase 1 - Input validation started"
            )
            validated_input = self._validate_input(raw_input)
            self.logger.info(
                f"{self.__class__.__name__}: Phase 1 - Input validation completed"
            )
            
            # PHASE 2: PROCESS WITH TRANSACTION SAFETY
            self.logger.info(
                f"{self.__class__.__name__}: Phase 2 - Processing started"
            )
            with self._transaction_context():
                result = self.process(validated_input)
            self.logger.info(
                f"{self.__class__.__name__}: Phase 2 - Processing completed"
            )
            
            # PHASE 3: FORMAT OUTPUT
            self.logger.info(
                f"{self.__class__.__name__}: Phase 3 - Output formatting started"
            )
            output = self._format_output(result)
            self.logger.info(
                f"{self.__class__.__name__}: Phase 3 - Output formatting completed"
            )
            
            # Success metrics
            self.metrics.end_time = time.time()
            self.metrics.success = True
            self.metrics.output_size = len(str(output))
            
            # Add metadata
            output['_metadata'] = {
                'handler': self.__class__.__name__,
                'version': self.handler_version,
                'executed_at': timezone.now().isoformat(),
                'success': True,
                'metrics': self.metrics.to_dict()
            }
            
            self.logger.info(
                f"{self.__class__.__name__}: Execution completed successfully",
                extra={
                    'duration': self.metrics.duration,
                    'success': True
                }
            )
            
            return output
            
        except PydanticValidationError as e:
            self.metrics.end_time = time.time()
            self.metrics.error = str(e)
            self.logger.error(
                f"{self.__class__.__name__}: Input validation failed",
                extra={'error': str(e), 'errors': e.errors()}
            )
            return self._handle_validation_error(e)
            
        except ProcessingError as e:
            self.metrics.end_time = time.time()
            self.metrics.error = str(e)
            self.logger.error(
                f"{self.__class__.__name__}: Processing failed",
                extra={'error': str(e)}
            )
            return self._handle_processing_error(e, raw_input)
            
        except Exception as e:
            self.metrics.end_time = time.time()
            self.metrics.error = str(e)
            self.logger.exception(
                f"{self.__class__.__name__}: Unexpected error",
                extra={'error': str(e)}
            )
            return self._handle_unexpected_error(e, raw_input)
    
    # ==================== PHASE 1: INPUT VALIDATION ====================
    
    def _validate_input(self, raw_input: Dict[str, Any]) -> InputT:
        """
        Phase 1: Validate input with Pydantic
        """
        try:
            validated = self.InputSchema(**raw_input)
            self.logger.debug(
                f"{self.__class__.__name__}: Input validated",
                extra={'model': validated.dict()}
            )
            return validated
        except PydanticValidationError as e:
            # Re-raise Pydantic errors directly for proper error handling
            raise e
    
    # ==================== PHASE 2: PROCESSING ====================
    
    def process(self, validated_input: InputT) -> Dict[str, Any]:
        """
        Phase 2: Business logic processing
        
        Override this method in subclasses with your business logic.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement process() method"
        )
    
    @contextmanager
    def _transaction_context(self):
        """
        Wrap processing in database transaction
        
        Automatically rolls back on any exception.
        """
        if self._should_use_transaction():
            with transaction.atomic():
                yield
        else:
            yield
    
    def _should_use_transaction(self) -> bool:
        """
        Override to disable transactions if needed
        """
        return True  # Default: always use transactions
    
    # ==================== PHASE 3: OUTPUT FORMATTING ====================
    
    def _format_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 3: Format output with Pydantic
        """
        try:
            # Add standard fields
            result.setdefault('success', True)
            result.setdefault('action', self._get_action_name())
            result.setdefault('message', 'Processing completed successfully')
            
            # Validate with Pydantic
            validated = self.OutputSchema(**result)
            self.logger.debug(
                f"{self.__class__.__name__}: Output validated",
                extra={'model': validated.dict()}
            )
            return validated.dict()
            
        except PydanticValidationError as e:
            self.logger.error(
                f"{self.__class__.__name__}: Output validation failed",
                extra={'error': str(e)}
            )
            raise ProcessingError(f"Output validation failed: {e}")
    
    def _get_action_name(self) -> str:
        """Get action name from handler class name"""
        import re
        name = self.__class__.__name__
        if name.endswith('Handler'):
            name = name[:-7]
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    
    # ==================== ERROR HANDLING ====================
    
    def _handle_validation_error(self, error: PydanticValidationError) -> Dict[str, Any]:
        """Handle input validation errors"""
        return {
            'success': False,
            'action': self._get_action_name(),
            'error_type': 'validation_error',
            'message': 'Input validation failed',
            'errors': error.errors(),
            'timestamp': timezone.now().isoformat()
        }
    
    def _handle_processing_error(
        self, 
        error: ProcessingError, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle business logic processing errors"""
        return {
            'success': False,
            'action': self._get_action_name(),
            'error_type': 'processing_error',
            'message': str(error),
            'context': self._sanitize_context(context),
            'timestamp': timezone.now().isoformat()
        }
    
    def _handle_unexpected_error(
        self, 
        error: Exception, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle unexpected errors"""
        return {
            'success': False,
            'action': self._get_action_name(),
            'error_type': type(error).__name__,
            'message': 'Unexpected error occurred',
            'error_detail': str(error),
            'context': self._sanitize_context(context),
            'timestamp': timezone.now().isoformat()
        }
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize context for error responses
        
        Removes sensitive data and truncates large values.
        """
        sanitized = {}
        sensitive_keys = {'password', 'api_key', 'secret', 'token'}
        
        for key, value in context.items():
            # Skip sensitive keys
            if any(s in key.lower() for s in sensitive_keys):
                sanitized[key] = '***REDACTED***'
                continue
            
            # Truncate large strings
            if isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + '...'
            else:
                sanitized[key] = value
        
        return sanitized
