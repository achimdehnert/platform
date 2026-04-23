"""Service-layer functions for concept-template Django integration (ADR-147).

Provides reusable extract + analyze pipeline for ANY consumer app.
All functions are synchronous — call from Celery tasks.

Usage in a consumer app (e.g. ausschreibungs-hub):

    from concept_templates.contrib.django.services import extract_and_analyze

    result = extract_and_analyze(
        concept_doc=my_doc_instance,
        pdf_bytes=raw_bytes,
        llm_fn=my_llm_wrapper,  # (system, user) -> str
    )
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from concept_templates.extractor import extract_text_from_bytes
from concept_templates.schemas import AnalysisResult, ExtractionResult

if TYPE_CHECKING:
    from django.db import models

logger = logging.getLogger(__name__)

# Type alias — same as analyzer.LLMCallable
LLMCallable = Callable[[str, str], str]


def extract_document_text(
    concept_doc: models.Model,
    pdf_bytes: bytes,
    content_type: str = "application/pdf",
) -> ExtractionResult:
    """Extract text from a PDF and update the ConceptDocument instance.

    Args:
        concept_doc: Instance of a concrete AbstractConceptDocument subclass.
        pdf_bytes: Raw bytes of the uploaded PDF.
        content_type: MIME type of the file.

    Returns:
        ExtractionResult from the extraction.
    """
    concept_doc.status = "extracting"
    concept_doc.save(update_fields=["status"])

    try:
        result = extract_text_from_bytes(pdf_bytes, content_type=content_type)

        concept_doc.extracted_text = result.text
        concept_doc.page_count = result.page_count
        concept_doc.extraction_warnings = json.dumps(result.warnings)
        concept_doc.status = "extracted"
        concept_doc.save(
            update_fields=[
                "extracted_text",
                "page_count",
                "extraction_warnings",
                "status",
            ]
        )

        logger.info(
            "Extracted %d chars from %d pages for '%s'",
            len(result.text),
            result.page_count,
            concept_doc.title,
        )
        return result

    except Exception as exc:
        concept_doc.status = "failed"
        concept_doc.error_message = str(exc)
        concept_doc.save(update_fields=["status", "error_message"])
        logger.warning("Extraction failed for '%s': %s", concept_doc.title, exc)
        raise


def analyze_document(
    concept_doc: models.Model,
    llm_fn: LLMCallable,
) -> AnalysisResult:
    """Run LLM structure analysis on an already-extracted ConceptDocument.

    Args:
        concept_doc: Must have extracted_text populated.
        llm_fn: Callable (system_prompt, user_prompt) -> raw_response.

    Returns:
        AnalysisResult with proposed template and confidence.
    """
    if not concept_doc.has_extracted_text:
        raise ValueError(f"ConceptDocument '{concept_doc.title}' has no extracted text.")

    concept_doc.status = "analyzing"
    concept_doc.save(update_fields=["status"])

    try:
        from concept_templates.analyzer import analyze_document_structure
        from concept_templates.export import to_json

        analysis = analyze_document_structure(
            text=concept_doc.extracted_text,
            scope=concept_doc.scope,
            title=concept_doc.title,
            page_count=concept_doc.page_count or 0,
            llm_fn=llm_fn,
        )

        concept_doc.template_json = to_json(analysis.proposed_template)
        concept_doc.analysis_confidence = analysis.confidence
        concept_doc.status = "analyzed"
        concept_doc.save(
            update_fields=[
                "template_json",
                "analysis_confidence",
                "status",
            ]
        )

        logger.info(
            "Analyzed '%s': confidence=%.2f, %d sections",
            concept_doc.title,
            analysis.confidence,
            len(analysis.proposed_template.sections),
        )
        return analysis

    except Exception as exc:
        concept_doc.status = "failed"
        concept_doc.error_message = f"Analyse fehlgeschlagen: {exc}"
        concept_doc.save(update_fields=["status", "error_message"])
        logger.warning("Analysis failed for '%s': %s", concept_doc.title, exc)
        raise


def extract_and_analyze(
    concept_doc: models.Model,
    pdf_bytes: bytes,
    llm_fn: LLMCallable | None = None,
    content_type: str = "application/pdf",
) -> dict:
    """Full pipeline: extract text + optionally analyze via LLM.

    This is the main entry point for consumer apps. Call from a Celery task
    with the app-specific llm_fn and pdf_bytes retrieval.

    Args:
        concept_doc: Instance of a concrete AbstractConceptDocument subclass.
        pdf_bytes: Raw PDF bytes.
        llm_fn: Optional LLM callable. If None, only extraction is performed.
        content_type: MIME type of the file.

    Returns:
        dict with status, page_count, and optionally confidence + sections.
    """
    # Step 1: Extract
    if not concept_doc.has_extracted_text:
        extract_document_text(concept_doc, pdf_bytes, content_type)

    # Step 2: Analyze (if llm_fn provided)
    if llm_fn and concept_doc.has_extracted_text and not concept_doc.has_template:
        analysis = analyze_document(concept_doc, llm_fn)
        return {
            "status": "analyzed",
            "page_count": concept_doc.page_count,
            "confidence": analysis.confidence,
            "sections": len(analysis.proposed_template.sections),
        }

    return {
        "status": concept_doc.status,
        "page_count": concept_doc.page_count,
    }
