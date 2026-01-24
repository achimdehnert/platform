"""
Enhanced Base Output Handler
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from django.db import transaction
import structlog

from ..exceptions import OutputHandlerException, ConfigurationException
from ..decorators import with_logging, with_performance_monitoring

logger = structlog.get_logger()


class BaseOutputHandler(ABC):
    """
    Base class for all output handlers.
    
    Output handlers are responsible for:
    1. Parsing processed data into structured format
    2. Validating the parsed data
    3. Creating EnrichmentResponse objects for approval
    4. Applying approved data to database/filesystem
    
    Attributes:
        handler_type: Always "output"
        handler_name: Unique identifier
        handler_version: Version string
        description: Human-readable description
        supports_multiple_objects: Can create multiple objects
        supports_rollback: Can rollback applied changes
    """
    
    handler_type: str = "output"
    handler_name: str = None
    handler_version: str = "2.0.0"
    description: str = ""
    
    supports_multiple_objects: bool = False
    supports_nested_data: bool = False
    supports_validation: bool = True
    supports_preview: bool = True
    supports_rollback: bool = False
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize handler with configuration.
        
        Args:
            config: Handler-specific configuration
            
        Raises:
            ConfigurationException: If config invalid
        """
        if self.handler_name is None:
            raise ConfigurationException(
                "Handler must define handler_name class attribute",
                handler_name=self.__class__.__name__
            )
        
        self.config = config
        self.logger = logger.bind(
            handler=self.handler_name,
            version=self.handler_version
        )
        
        try:
            self.validate_config()
        except Exception as e:
            raise ConfigurationException(
                f"Configuration validation failed: {e}",
                handler_name=self.handler_name,
                context={"config": config},
                original_error=e
            )
    
    @abstractmethod
    def validate_config(self) -> None:
        """Validate handler configuration"""
        pass
    
    @abstractmethod
    def parse(self, processed_data: Any) -> List[Dict[str, Any]]:
        """
        Parse processed data into structured format.
        
        Args:
            processed_data: Output from processing stage
            
        Returns:
            List of dictionaries to be created/updated
            
        Raises:
            OutputHandlerException: If parsing fails
        """
        pass
    
    @abstractmethod
    def validate(self, parsed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate parsed data.
        
        Args:
            parsed_data: List of parsed objects
            
        Returns:
            Validation results dict with 'valid', 'errors', 'warnings'
        """
        pass
    
    @abstractmethod
    def create_enrichment_responses(
        self,
        parsed_data: List[Dict[str, Any]],
        project: Any,
        agent: Any
    ) -> List[Any]:
        """
        Create EnrichmentResponse objects for approval.
        
        Args:
            parsed_data: List of validated objects
            project: BookProjects instance
            agent: Agents instance
            
        Returns:
            List of EnrichmentResponse objects
        """
        pass
    
    @abstractmethod
    def apply(self, enrichment_response: Any) -> Any:
        """
        Apply approved data to database/filesystem.
        
        Args:
            enrichment_response: EnrichmentResponse to apply
            
        Returns:
            Created/updated object(s)
            
        Raises:
            OutputHandlerException: If application fails
        """
        pass
    
    def _apply_with_transaction(self, func, *args, **kwargs):
        """
        Execute function with transaction safety.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments
            
        Returns:
            Result of function
        """
        try:
            with transaction.atomic():
                sid = transaction.savepoint()
                try:
                    result = func(*args, **kwargs)
                    transaction.savepoint_commit(sid)
                    return result
                except Exception:
                    transaction.savepoint_rollback(sid)
                    raise
        except Exception as e:
            raise OutputHandlerException(
                f"Transaction failed: {e}",
                handler_name=self.handler_name,
                original_error=e
            )
    
    def _generate_summary(self, enrichment_response: Any) -> str:
        """Generate human-readable summary"""
        return f"Handler: {self.handler_name}"
    
    def rollback(self, enrichment_response: Any) -> None:
        """Rollback applied changes"""
        if not self.supports_rollback:
            raise NotImplementedError(
                f"{self.handler_name} does not support rollback"
            )
        raise NotImplementedError("Rollback not implemented")
    
    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"name={self.handler_name} "
            f"version={self.handler_version}>"
        )