"""
Context Enrichment Exceptions

Custom exception hierarchy for context enrichment errors.
"""


class EnrichmentError(Exception):
    """Base exception for all context enrichment errors"""
    pass


class SchemaNotFoundError(EnrichmentError):
    """Schema not found in database or is inactive"""
    
    def __init__(self, schema_name: str):
        self.schema_name = schema_name
        super().__init__(f"Schema '{schema_name}' not found or inactive")


class SourceResolutionError(EnrichmentError):
    """Error resolving a context source"""
    
    def __init__(self, source_name: str, reason: str):
        self.source_name = source_name
        self.reason = reason
        super().__init__(f"Source '{source_name}' resolution failed: {reason}")


class ValidationError(EnrichmentError):
    """Schema or parameter validation error"""
    
    def __init__(self, message: str, errors: list = None):
        self.errors = errors or []
        super().__init__(message)


class TimeoutError(SourceResolutionError):
    """Source resolution timed out"""
    
    def __init__(self, source_name: str, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        super().__init__(
            source_name,
            f"Timed out after {timeout_seconds} seconds"
        )


class ModelNotFoundError(SourceResolutionError):
    """Django model not found"""
    
    def __init__(self, source_name: str, model_name: str):
        self.model_name = model_name
        super().__init__(
            source_name,
            f"Model '{model_name}' not found"
        )


class FunctionNotFoundError(SourceResolutionError):
    """Computed function not found"""
    
    def __init__(self, source_name: str, function_name: str):
        self.function_name = function_name
        super().__init__(
            source_name,
            f"Computed function '{function_name}' not found"
        )
