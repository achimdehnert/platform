"""Expert Hub Services."""

from .document_generator import ExSchutzDocumentGenerator, generate_exschutz_document
from .pdf_extractor import SDSPDFExtractor, extract_sds_data
from .content_merger import SmartContentMerger, get_merge_preview_html

# Aliases
ContentMerger = SmartContentMerger
merge_ai_content = get_merge_preview_html
from .llm_client import generate_sync, generate_async, check_gateway_health, list_available_models

__all__ = [
    'ExSchutzDocumentGenerator',
    'SDSPDFExtractor',
    'extract_sds_data',
    'ContentMerger',
    'merge_ai_content',
    'generate_sync',
    'generate_async',
    'check_gateway_health',
    'list_available_models',
]
