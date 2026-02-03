"""
PPTX-Hub: Production-ready PowerPoint processing platform.

A database-driven platform for processing, translating, and transforming
PowerPoint presentations with multi-tenancy support.
"""

__version__ = "0.1.0"
__author__ = "Your Organization"
__license__ = "MIT"

from pptx_hub.core.services import TextExtractor, Repackager, SlideAnalyzer

__all__ = [
    "__version__",
    "TextExtractor",
    "Repackager",
    "SlideAnalyzer",
]
