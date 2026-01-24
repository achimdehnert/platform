"""
Core Handlers - Central Handler System for BF Agent

This module provides the central handler registry and base classes
used by all domain applications (bookwriting, medtrans, genagent).

Architecture:
- BaseHandler: Abstract base class for all handlers
- HandlerRegistry: Central registry for handler discovery
- Decorators: @register_handler for easy registration

Usage:
    from apps.core.handlers import register_handler, BaseHandler

    @register_handler("bookwriting.book.create", "1.0.0")
    class BookCreateHandler(BaseHandler):
        def execute(self, context):
            return {'status': 'success'}
"""

from .base import BaseHandler, InputHandler, OutputHandler, ProcessingHandler
from .registry import HandlerRegistry, get_handler, register_handler

__all__ = [
    "BaseHandler",
    "InputHandler",
    "ProcessingHandler",
    "OutputHandler",
    "HandlerRegistry",
    "register_handler",
    "get_handler",
]
