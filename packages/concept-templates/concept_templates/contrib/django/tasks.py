"""Reusable Celery task factory for concept document processing (ADR-147).

Consumer apps call ``make_extract_and_analyze_task()`` once at module level
to get a ready-to-use Celery shared_task. Only two things are repo-specific:

1. ``model_class`` — the concrete ConceptDocument model
2. ``get_pdf_bytes`` — a callable that fetches PDF bytes for a given doc
3. ``llm_fn`` — optional LLM callable for structure analysis

Example (ausschreibungs-hub/tasks.py):

    from concept_templates.contrib.django.tasks import make_extract_and_analyze_task
    from ausschreibungen.models import AusschreibungDocument

    def get_pdf_bytes(doc, tenant_id):
        return doc.file.read()  # or S3 download

    def llm_wrapper(system, user):
        from aifw.service import sync_completion
        result = sync_completion(action_code="concept_analysis", ...)
        return result.content

    extract_and_analyze_task = make_extract_and_analyze_task(
        model_class=AusschreibungDocument,
        get_pdf_bytes=get_pdf_bytes,
        llm_fn=llm_wrapper,
        task_name="ausschreibungen.tasks.extract_and_analyze",
    )
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


def make_extract_and_analyze_task(
    model_class: type,
    get_pdf_bytes: Callable[[Any, UUID], bytes | None],
    llm_fn: Callable[[str, str], str] | None = None,
    task_name: str = "concept_templates.extract_and_analyze",
    max_retries: int = 2,
    default_retry_delay: int = 30,
) -> Any:
    """Create a Celery shared_task for extract + analyze pipeline.

    Args:
        model_class: Concrete Django model (subclass of AbstractConceptDocument).
        get_pdf_bytes: Callable(concept_doc, tenant_id) -> bytes | None.
        llm_fn: Optional LLM callable (system, user) -> str.
        task_name: Celery task name (must be unique per app).
        max_retries: Max Celery retries.
        default_retry_delay: Seconds between retries.

    Returns:
        A Celery shared_task function.
    """
    from celery import shared_task

    @shared_task(
        name=task_name,
        max_retries=max_retries,
        default_retry_delay=default_retry_delay,
        acks_late=True,
    )
    def _extract_and_analyze_task(
        concept_doc_id: str,
        tenant_id: str,
    ) -> dict:
        doc_id = UUID(concept_doc_id)
        tid = UUID(tenant_id)

        try:
            concept_doc = model_class.objects.get(id=doc_id, tenant_id=tid)
        except model_class.DoesNotExist:
            logger.error(
                "%s %s not found for tenant %s",
                model_class.__name__, doc_id, tid,
            )
            return {"status": "error", "error": "Document not found"}

        # Get PDF bytes via app-specific callback
        pdf_bytes = None
        if not concept_doc.has_extracted_text:
            pdf_bytes = get_pdf_bytes(concept_doc, tid)
            if pdf_bytes is None:
                concept_doc.status = "failed"
                concept_doc.error_message = "PDF-Bytes konnten nicht geladen werden."
                concept_doc.save(update_fields=["status", "error_message"])
                return {"status": "error", "error": "No PDF bytes"}

        # Run the shared pipeline
        from concept_templates.contrib.django.services import extract_and_analyze

        return extract_and_analyze(
            concept_doc=concept_doc,
            pdf_bytes=pdf_bytes or b"",
            llm_fn=llm_fn,
        )

    return _extract_and_analyze_task
