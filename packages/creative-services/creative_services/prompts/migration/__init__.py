"""
Migration module for BFAgent compatibility.

Provides adapters and converters for migrating from BFAgent's
PromptTemplate model to the new PromptTemplateSpec.
"""

from .bfagent_adapter import (
    BFAgentTemplateAdapter,
    convert_bfagent_template,
    convert_to_bfagent_format,
)

__all__ = [
    "BFAgentTemplateAdapter",
    "convert_bfagent_template",
    "convert_to_bfagent_format",
]
