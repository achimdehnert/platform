"""Service-layer functions for concept-template Django integration (ADR-147).

All functions are synchronous. LLM calls belong in Celery tasks (Phase C).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from concept_templates.extractor import extract_text_from_bytes
from concept_templates.schemas import ExtractionResult

if TYPE_CHECKING:
    from django.db import models

logger = logging.getLogger(__name__)


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
