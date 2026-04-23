"""Service layer for doc_templates (ADR-041: views → services → models)."""

from .llm_service import build_prefill_prompt, execute_llm_prefill
from .pdf_service import extract_pdf_text, import_text_into_template, text_to_structure
from .retriever import get_source_content, register_source_retriever
from .template_service import (
    merge_values_into_structure,
    parse_form_values,
)

__all__ = [
    "build_prefill_prompt",
    "execute_llm_prefill",
    "extract_pdf_text",
    "get_source_content",
    "import_text_into_template",
    "merge_values_into_structure",
    "parse_form_values",
    "register_source_retriever",
    "text_to_structure",
]
