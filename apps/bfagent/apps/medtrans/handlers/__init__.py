"""
Medical Translation Handlers
Handler-based architecture for PowerPoint translation
"""

from apps.genagent.handlers import BaseHandler, register_handler

# Handler Registry for Medical Translation
MEDTRANS_HANDLERS = {}


def register_medtrans_handler(cls):
    """Register medical translation handler"""
    # Register in GenAgent registry
    register_handler(cls)
    # Also track in local registry
    MEDTRANS_HANDLERS[cls.__name__] = cls
    return cls


# Import handlers to trigger registration
from .extract_handler import ExtractTextsHandler
from .translate_handler import TranslateTextsHandler
from .repackage_handler import RepackagePPTXHandler


__all__ = [
    'ExtractTextsHandler',
    'TranslateTextsHandler',
    'RepackagePPTXHandler',
    'register_medtrans_handler',
]
