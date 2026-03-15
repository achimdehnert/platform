"""research-hub knowledge Celery tasks.

Fixes K2: async_to_sync (NOT asyncio.run()) for LLM calls in Celery context.
         aifw integration for all LLM calls (M2 fix).
         Platform Standard: asgiref.sync.async_to_sync (ADR-062, ADR-079).
"""

from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="knowledge.enrich_knowledge_document",
)
def enrich_knowledge_document(self, knowledge_doc_id: int) -> None:
    """Enrich a KnowledgeDocument with AI-generated summary, keywords and ADR links.

    Pipeline:
        1. Load document from DB
        2. Fetch full content from Outline API (async → sync via async_to_sync)
        3. aifw: generate summary (quality_level=MEDIUM)
        4. aifw: extract keywords (quality_level=FAST)
        5. Extract ADR references from content
        6. Persist enrichment results via service layer

    K2 fix: All async operations use asgiref.sync.async_to_sync, never asyncio.run().
    M2 fix: All LLM calls use aifw (ADR-095-097 Quality-Level-Routing).
    """
    from .models import KnowledgeDocument, KnowledgeDocumentStatus
    from .services import KnowledgeDocumentService

    service = KnowledgeDocumentService()

    try:
        doc = KnowledgeDocument.objects.get(pk=knowledge_doc_id, deleted_at__isnull=True)
    except KnowledgeDocument.DoesNotExist:
        logger.warning("enrich_knowledge_document: doc %s not found, skipping.", knowledge_doc_id)
        return

    if doc.enrichment_status not in (
        KnowledgeDocumentStatus.PENDING,
        KnowledgeDocumentStatus.ERROR,
    ):
        logger.debug(
            "enrich_knowledge_document: doc %s already enriched (%s), skipping.",
            knowledge_doc_id,
            doc.enrichment_status,
        )
        return

    # Mark as in-progress
    KnowledgeDocument.objects.filter(pk=knowledge_doc_id).update(
        enrichment_status=KnowledgeDocumentStatus.ENRICHING
    )

    try:
        # Step 1: Fetch full content from Outline API
        # K2 fix: async_to_sync wraps the async client call
        content = async_to_sync(_fetch_outline_content)(doc.outline_id)

        # Step 2: AI Enrichment via aifw (M2 fix: no direct LLM call)
        summary, keywords, related_adrs = async_to_sync(_run_enrichment)(
            title=doc.title,
            content=content,
            doc_type=doc.doc_type,
        )

        # Step 3: Persist
        service.mark_enriched(
            doc_id=knowledge_doc_id,
            summary=summary,
            keywords=keywords,
            related_adrs=related_adrs,
            content_snapshot=content,
        )

        logger.info(
            "enrich_knowledge_document: doc %s enriched successfully. keywords=%d",
            knowledge_doc_id,
            len(keywords),
        )

    except Exception as exc:
        logger.exception(
            "enrich_knowledge_document: doc %s enrichment failed: %s",
            knowledge_doc_id,
            exc,
        )
        service.mark_enrichment_error(knowledge_doc_id, str(exc))
        raise self.retry(exc=exc)


async def _fetch_outline_content(outline_id: str) -> str:
    """Fetch full Markdown content from Outline API.

    Called via async_to_sync — never via asyncio.run() (K2 fix).
    """
    import httpx
    from django.conf import settings

    base_url = getattr(settings, "OUTLINE_URL", "").rstrip("/")
    api_token = getattr(settings, "OUTLINE_API_TOKEN", "")

    async with httpx.AsyncClient(
        base_url=base_url,
        headers={"Authorization": f"Bearer {api_token}"},
        timeout=30.0,
    ) as client:
        response = await client.post("/api/documents.info", json={"id": outline_id})
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("text", "")


async def _run_enrichment(
    title: str,
    content: str,
    doc_type: str,
) -> tuple[list[str], list[str], list[str]]:
    """Generate summary, keywords and ADR references via aifw.

    M2 fix: uses aifw.generate() with quality_level routing (ADR-095-097).
    K2 fix: called via async_to_sync — never via asyncio.run().

    Returns: (summary_lines, keywords, related_adrs)
    """
    import re

    # Import aifw — platform-standard LLM interface
    from aifw import QualityLevel, generate  # type: ignore[import]

    # Summary (Medium quality — needs good coherence)
    summary_prompt = (
        f"Du bist ein technischer Dokumentations-Assistent.\n\n"
        f"Erstelle eine prägnante Zusammenfassung (3-5 Sätze) des folgenden "
        f"{doc_type}-Dokuments auf Deutsch.\n\n"
        f"# {title}\n\n{content[:3000]}"
    )
    summary_result = await generate(
        prompt=summary_prompt,
        quality_level=QualityLevel.MEDIUM,
        max_tokens=300,
    )
    summary = summary_result.content.strip()

    # Keywords (Fast quality — simple extraction)
    keywords_prompt = (
        f"Extrahiere 5-10 technische Schlüsselwörter aus diesem Dokument.\n"
        f"Antworte NUR mit einer kommagetrennten Liste, kein anderer Text.\n\n"
        f"# {title}\n\n{content[:2000]}"
    )
    keywords_result = await generate(
        prompt=keywords_prompt,
        quality_level=QualityLevel.FAST,
        max_tokens=100,
    )
    raw_keywords = keywords_result.content.strip()
    keywords = [kw.strip() for kw in raw_keywords.split(",") if kw.strip()][:10]

    # ADR reference extraction (regex — no LLM needed)
    adr_pattern = re.compile(r"\bADR-\d{3}\b")
    related_adrs = sorted(set(adr_pattern.findall(content)))

    return summary, keywords, related_adrs
