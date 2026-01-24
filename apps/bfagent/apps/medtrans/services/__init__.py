"""
Medical Translation Services
XML-based PowerPoint translation services
"""

from .translation_providers import DeepLProvider
from .xml_direct_translator import XMLDirectTranslator
from .xml_text_extractor import PPTXExtractor

__all__ = [
    "PPTXExtractor",
    "XMLDirectTranslator",
    "DeepLProvider",
]
