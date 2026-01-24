"""Block Handlers Module - Modular PPTX Block Rendering"""

from .base_handler import BaseBlockHandler
from .text_handlers import TitleHandler, QuoteHandler, TextBoxHandler
from .list_handlers import BulletListHandler, ObjectivesBoxHandler
from .layout_handlers import TwoColumnComparisonHandler, DefinitionBoxHandler
from .complex_handlers import VerticalBoxesHandler, FunctionListHandler
from .fallback_handler import FallbackHandler

__all__ = [
    'BaseBlockHandler',
    'TitleHandler',
    'QuoteHandler',
    'TextBoxHandler',
    'BulletListHandler',
    'ObjectivesBoxHandler',
    'TwoColumnComparisonHandler',
    'DefinitionBoxHandler',
    'VerticalBoxesHandler',
    'FunctionListHandler',
    'FallbackHandler',
]
