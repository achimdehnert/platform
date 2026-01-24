"""
Base Image Handler
==================

Abstract base handler for image generation following BF Agent Handler Framework.

Three-Phase Pattern:
1. Input Phase: Validation with Pydantic
2. Processing Phase: Core business logic
3. Output Phase: Result formatting and storage

Author: BF Agent Team
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)


class HandlerError(Exception):
    """Base exception for handler errors"""
    pass


class ValidationError(HandlerError):
    """Raised when input validation fails"""
    pass


class ProcessingError(HandlerError):
    """Raised during processing phase"""
    pass


class OutputError(HandlerError):
    """Raised during output phase"""
    pass


class BaseImageHandler(ABC):
    """
    Abstract base class for all image generation handlers.
    
    Implements the three-phase handler pattern:
    - INPUT: Validate and prepare input data
    - PROCESSING: Execute core logic
    - OUTPUT: Format and return results
    
    Includes:
    - Transaction safety
    - Rollback capabilities
    - Comprehensive logging
    - Error handling
    """
    
    # Handler metadata (override in subclasses)
    HANDLER_NAME: str = "BaseImageHandler"
    HANDLER_VERSION: str = "1.0.0"
    HANDLER_DESCRIPTION: str = "Base handler for image generation"
    
    # Schema classes (override in subclasses)
    INPUT_SCHEMA = None  # Pydantic model for input
    OUTPUT_SCHEMA = None  # Pydantic model for output
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize handler.
        
        Args:
            config: Handler configuration
        """
        self.config = config or {}
        self.execution_id = None
        self.start_time = None
        self.end_time = None
        
        # State tracking for rollback
        self._state_snapshots = []
        self._resources_created = []
        
        logger.info(
            "Handler initialized",
            handler=self.HANDLER_NAME,
            version=self.HANDLER_VERSION
        )
    
    # ==================== PUBLIC API ====================
    
    def handle(self, data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry point for handler execution.
        
        Implements three-phase pattern with transaction safety.
        
        Args:
            data: Input data dictionary
            config: Optional runtime configuration
            
        Returns:
            Dictionary containing handler output
            
        Raises:
            ValidationError: If input validation fails
            ProcessingError: If processing fails
            OutputError: If output formatting fails
        """
        self.execution_id = self._generate_execution_id()
        self.start_time = datetime.now()
        
        # Merge runtime config with handler config
        effective_config = {**self.config, **(config or {})}
        
        logger.info(
            "Handler execution started",
            handler=self.HANDLER_NAME,
            execution_id=self.execution_id
        )
        
        try:
            # PHASE 1: INPUT VALIDATION
            validated_input = self._input_phase(data)
            
            # PHASE 2: PROCESSING
            processing_result = self._processing_phase(validated_input, effective_config)
            
            # PHASE 3: OUTPUT FORMATTING
            output = self._output_phase(processing_result)
            
            self.end_time = datetime.now()
            execution_time = (self.end_time - self.start_time).total_seconds()
            
            logger.info(
                "Handler execution completed successfully",
                handler=self.HANDLER_NAME,
                execution_id=self.execution_id,
                execution_time=execution_time
            )
            
            # Add execution metadata
            output['_metadata'] = {
                'handler': self.HANDLER_NAME,
                'version': self.HANDLER_VERSION,
                'execution_id': self.execution_id,
                'execution_time_seconds': execution_time,
                'timestamp': self.end_time.isoformat()
            }
            
            return output
            
        except ValidationError as e:
            logger.error(
                "Input validation failed",
                handler=self.HANDLER_NAME,
                execution_id=self.execution_id,
                error=str(e)
            )
            self._rollback()
            raise
            
        except ProcessingError as e:
            logger.error(
                "Processing failed",
                handler=self.HANDLER_NAME,
                execution_id=self.execution_id,
                error=str(e)
            )
            self._rollback()
            raise
            
        except OutputError as e:
            logger.error(
                "Output formatting failed",
                handler=self.HANDLER_NAME,
                execution_id=self.execution_id,
                error=str(e)
            )
            self._rollback()
            raise
            
        except Exception as e:
            logger.error(
                "Unexpected error in handler",
                handler=self.HANDLER_NAME,
                execution_id=self.execution_id,
                error=str(e),
                error_type=type(e).__name__
            )
            self._rollback()
            raise HandlerError(f"Handler execution failed: {str(e)}") from e
    
    # ==================== ABSTRACT METHODS (MUST IMPLEMENT) ====================
    
    @abstractmethod
    def _validate_input(self, data: Dict[str, Any]) -> Any:
        """
        Validate input data using Pydantic schema.
        
        Args:
            data: Raw input data
            
        Returns:
            Validated Pydantic model instance
            
        Raises:
            ValidationError: If validation fails
        """
        pass
    
    @abstractmethod
    def _process(self, validated_input: Any, config: Dict[str, Any]) -> Any:
        """
        Core processing logic.
        
        Args:
            validated_input: Validated input from INPUT phase
            config: Effective configuration
            
        Returns:
            Processing result (any type)
            
        Raises:
            ProcessingError: If processing fails
        """
        pass
    
    @abstractmethod
    def _format_output(self, processing_result: Any) -> Dict[str, Any]:
        """
        Format processing result into output schema.
        
        Args:
            processing_result: Result from PROCESSING phase
            
        Returns:
            Dictionary matching OUTPUT_SCHEMA
            
        Raises:
            OutputError: If formatting fails
        """
        pass
    
    # ==================== PHASE IMPLEMENTATIONS ====================
    
    def _input_phase(self, data: Dict[str, Any]) -> Any:
        """
        INPUT PHASE: Validate and prepare input.
        
        Uses Pydantic schema for validation.
        """
        logger.debug("Starting INPUT phase", execution_id=self.execution_id)
        
        try:
            validated = self._validate_input(data)
            logger.debug("Input validation successful", execution_id=self.execution_id)
            return validated
            
        except Exception as e:
            raise ValidationError(f"Input validation failed: {str(e)}") from e
    
    def _processing_phase(self, validated_input: Any, config: Dict[str, Any]) -> Any:
        """
        PROCESSING PHASE: Execute core logic.
        
        Includes transaction tracking for rollback.
        """
        logger.debug("Starting PROCESSING phase", execution_id=self.execution_id)
        
        # Create state snapshot before processing
        self._create_snapshot()
        
        try:
            result = self._process(validated_input, config)
            logger.debug("Processing completed", execution_id=self.execution_id)
            return result
            
        except Exception as e:
            raise ProcessingError(f"Processing failed: {str(e)}") from e
    
    def _output_phase(self, processing_result: Any) -> Dict[str, Any]:
        """
        OUTPUT PHASE: Format and validate output.
        """
        logger.debug("Starting OUTPUT phase", execution_id=self.execution_id)
        
        try:
            output = self._format_output(processing_result)
            
            # Validate output if schema defined
            if self.OUTPUT_SCHEMA:
                validated_output = self.OUTPUT_SCHEMA(**output)
                output = validated_output.dict()
            
            logger.debug("Output formatting successful", execution_id=self.execution_id)
            return output
            
        except Exception as e:
            raise OutputError(f"Output formatting failed: {str(e)}") from e
    
    # ==================== TRANSACTION & ROLLBACK ====================
    
    def _create_snapshot(self):
        """Create state snapshot for rollback"""
        snapshot = {
            'timestamp': datetime.now(),
            'state': self._get_current_state()
        }
        self._state_snapshots.append(snapshot)
    
    def _get_current_state(self) -> Dict[str, Any]:
        """
        Get current handler state for rollback.
        Override in subclass if you need custom state tracking.
        """
        return {}
    
    def _rollback(self):
        """
        Rollback to previous state.
        
        Override in subclass for custom rollback logic (e.g., delete files).
        """
        logger.warning(
            "Rolling back handler execution",
            handler=self.HANDLER_NAME,
            execution_id=self.execution_id,
            snapshots_count=len(self._state_snapshots)
        )
        
        # Cleanup created resources
        for resource in self._resources_created:
            try:
                if isinstance(resource, Path) and resource.exists():
                    resource.unlink()
                    logger.debug(f"Deleted resource: {resource}")
            except Exception as e:
                logger.error(f"Failed to cleanup resource {resource}: {e}")
        
        self._resources_created.clear()
        self._state_snapshots.clear()
    
    def _register_resource(self, resource_path: Path):
        """Register a resource for cleanup on rollback"""
        self._resources_created.append(resource_path)
    
    # ==================== UTILITIES ====================
    
    def _generate_execution_id(self) -> str:
        """Generate unique execution ID"""
        import uuid
        return f"{self.HANDLER_NAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get handler metadata"""
        return {
            'name': self.HANDLER_NAME,
            'version': self.HANDLER_VERSION,
            'description': self.HANDLER_DESCRIPTION,
            'input_schema': self.INPUT_SCHEMA.__name__ if self.INPUT_SCHEMA else None,
            'output_schema': self.OUTPUT_SCHEMA.__name__ if self.OUTPUT_SCHEMA else None,
        }
    
    def __repr__(self) -> str:
        return f"{self.HANDLER_NAME}(version={self.HANDLER_VERSION})"


# Example of handler usage pattern (for documentation)
"""
class MyCustomImageHandler(BaseImageHandler):
    HANDLER_NAME = "MyCustomImageHandler"
    HANDLER_VERSION = "1.0.0"
    INPUT_SCHEMA = MyInputSchema  # Pydantic model
    OUTPUT_SCHEMA = MyOutputSchema  # Pydantic model
    
    def _validate_input(self, data):
        return self.INPUT_SCHEMA(**data)
    
    def _process(self, validated_input, config):
        # Your core logic here
        return result
    
    def _format_output(self, processing_result):
        return {'key': 'value'}
"""
