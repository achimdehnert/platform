"""
Handler Registry for BF Agent
Central registration and management of all handlers
"""

import logging
from typing import Dict, List, Optional

from .base import BaseInputHandler, BaseOutputHandler, BaseProcessingHandler

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """Central registry for all BF Agent handlers"""

    _instance = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.input_handlers: Dict[str, BaseInputHandler] = {}
        self.processing_handlers: Dict[str, BaseProcessingHandler] = {}
        self.output_handlers: Dict[str, BaseOutputHandler] = {}
        self._initialized = True

        logger.info("HandlerRegistry initialized")

    def register_input_handler(
        self, name: str, handler: BaseInputHandler
    ) -> None:
        """Register an input handler"""
        self.input_handlers[name] = handler
        logger.info(f"✅ Registered InputHandler: {name} ({handler.version})")

    def register_processing_handler(
        self, name: str, handler: BaseProcessingHandler
    ) -> None:
        """Register a processing handler"""
        self.processing_handlers[name] = handler
        logger.info(f"✅ Registered ProcessingHandler: {name} ({handler.version})")

    def register_output_handler(
        self, name: str, handler: BaseOutputHandler
    ) -> None:
        """Register an output handler"""
        self.output_handlers[name] = handler
        logger.info(f"✅ Registered OutputHandler: {name} ({handler.version})")

    def get_input_handler(self, name: str) -> Optional[BaseInputHandler]:
        """Get an input handler by name"""
        return self.input_handlers.get(name)

    def get_processing_handler(
        self, name: str
    ) -> Optional[BaseProcessingHandler]:
        """Get a processing handler by name"""
        return self.processing_handlers.get(name)

    def get_output_handler(self, name: str) -> Optional[BaseOutputHandler]:
        """Get an output handler by name"""
        return self.output_handlers.get(name)

    def list_input_handlers(self) -> List[str]:
        """List all registered input handlers"""
        return list(self.input_handlers.keys())

    def list_processing_handlers(self) -> List[str]:
        """List all registered processing handlers"""
        return list(self.processing_handlers.keys())

    def list_output_handlers(self) -> List[str]:
        """List all registered output handlers"""
        return list(self.output_handlers.keys())

    def get_all_handlers(self) -> Dict[str, List[str]]:
        """Get all registered handlers grouped by type"""
        return {
            "input": self.list_input_handlers(),
            "processing": self.list_processing_handlers(),
            "output": self.list_output_handlers(),
        }

    def clear(self) -> None:
        """Clear all registered handlers (for testing)"""
        self.input_handlers.clear()
        self.processing_handlers.clear()
        self.output_handlers.clear()
        logger.info("HandlerRegistry cleared")
