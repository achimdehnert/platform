"""
Custom exceptions for handler pipeline system

Provides structured error handling with severity levels,
context tracking, and integration with logging systems.
"""

from typing import Dict, Any, Optional
from enum import Enum


class HandlerErrorSeverity(Enum):
    """Error severity levels"""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HandlerException(Exception):
    """Base exception for all handler errors"""
    
    severity = HandlerErrorSeverity.ERROR
    
    def __init__(
        self,
        message: str,
        handler_name: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.handler_name = handler_name
        self.context = context or {}
        self.original_error = original_error
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        msg = f"[{self.handler_name}] {self.message}"
        
        if self.context:
            context_items = [f"{k}={v}" for k, v in self.context.items()]
            msg += f" | Context: {', '.join(context_items)}"
        
        if self.original_error:
            error_type = type(self.original_error).__name__
            msg += f" | Caused by: {error_type}: {self.original_error}"
        
        return msg
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "severity": self.severity.value,
            "message": self.message,
            "handler": self.handler_name,
            "context": self.context,
            "original_error": {
                "type": type(self.original_error).__name__,
                "message": str(self.original_error)
            } if self.original_error else None
        }


class InputHandlerException(HandlerException):
    """Raised when input handler fails"""
    pass


class ProcessingHandlerException(HandlerException):
    """Raised when processing handler fails"""
    pass


class OutputHandlerException(HandlerException):
    """Raised when output handler fails"""
    severity = HandlerErrorSeverity.CRITICAL


class ValidationException(HandlerException):
    """Raised when data validation fails"""
    severity = HandlerErrorSeverity.WARNING


class ConfigurationException(HandlerException):
    """Raised when handler configuration is invalid"""
    severity = HandlerErrorSeverity.CRITICAL


class HandlerNotFoundException(HandlerException):
    """Raised when requested handler is not registered"""
    severity = HandlerErrorSeverity.CRITICAL


class LLMException(ProcessingHandlerException):
    """Raised when LLM API calls fail"""
    
    def __init__(
        self,
        message: str,
        handler_name: str,
        llm_name: Optional[str] = None,
        llm_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        enhanced_context = context or {}
        if llm_name:
            enhanced_context["llm_name"] = llm_name
        if llm_id:
            enhanced_context["llm_id"] = llm_id
        
        super().__init__(
            message=message,
            handler_name=handler_name,
            context=enhanced_context,
            original_error=original_error
        )
