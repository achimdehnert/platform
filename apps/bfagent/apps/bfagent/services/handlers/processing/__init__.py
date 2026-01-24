"""Processing Handlers for Pipeline System"""

from ..base.processing import BaseProcessingHandler
from .template_renderer import TemplateRendererHandler
from .llm_processor import LLMProcessingHandler
from .framework_generator import FrameworkGeneratorHandler
from .prompt_template_processor import PromptTemplateProcessingHandler

# Handlers are auto-registered by registries.auto_register_handlers()

__all__ = [
    "BaseProcessingHandler",
    "TemplateRendererHandler",
    "LLMProcessingHandler",
    "FrameworkGeneratorHandler",
    "PromptTemplateProcessingHandler",
]
