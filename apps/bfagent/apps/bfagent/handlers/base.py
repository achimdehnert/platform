"""
Base Handler Classes for BF Agent
Defines the contract for Input, Processing, and Output handlers
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseInputHandler(ABC):
    """Base class for input validation and preparation"""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate input data"""
        pass

    @abstractmethod
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and prepare input data"""
        pass

    def get_info(self) -> Dict[str, str]:
        """Get handler information"""
        return {
            "name": self.name,
            "version": self.version,
            "type": "input"
        }


class BaseProcessingHandler(ABC):
    """Base class for business logic processing"""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute processing logic"""
        pass

    def get_info(self) -> Dict[str, str]:
        """Get handler information"""
        return {
            "name": self.name,
            "version": self.version,
            "type": "processing"
        }


class BaseOutputHandler(ABC):
    """Base class for output and persistence"""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version

    @abstractmethod
    def save(self, data: Dict[str, Any]) -> Any:
        """Save/persist data"""
        pass

    def get_info(self) -> Dict[str, str]:
        """Get handler information"""
        return {
            "name": self.name,
            "version": self.version,
            "type": "output"
        }


class HandlerException(Exception):
    """Base exception for handler errors"""
    pass


class ValidationError(HandlerException):
    """Raised when input validation fails"""
    pass


class ProcessingError(HandlerException):
    """Raised when processing fails"""
    pass


class OutputError(HandlerException):
    """Raised when output/save fails"""
    pass
