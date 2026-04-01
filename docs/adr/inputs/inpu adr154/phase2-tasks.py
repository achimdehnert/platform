"""
orchestrator_mcp/tasks.py

Celery-Tasks für orchestrator_mcp:
  - generate_memory_embedding: Embedding für AgentMemoryEntry generieren
  - decay_old_memories: Temporal Decay (R-17, O-9)

Platform Standards:
  - acks_late=True auf allen Tasks
  - Dispatch via transaction.on_commit() (in services.py)
  - read_secret() für API-Key
  - asgiref.async_to_sync falls async benötigt
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    acks_late=True,
    max_retries=3,
    default_retry_delay=30,
    queue="embeddings",
)
def generate_memory_embedding(self, entry_id: int) -> dict:
    """
    Generiert OpenAI-Embedding für einen AgentMemoryEntry.

    Dispatch: MemoryService.upsert_entry() via transaction.on_commit()
    Retry: 3x mit 30s Delay bei API-Fehlern
    """
    from orchestrator_mcp.models import AgentMemoryEntry
    from platform_context.secrets import read_secret
    import openai

    try:
        entry = AgentMemoryEntry.all_objects.filter(id=entry_id, deleted_at__isnull=True).first()
        if not entry:
            logger.warning("generate_memory_embedding: Entry %s nicht gefunden oder deleted", entry_id)
            return {"skipped": True, "reason": "not_found_or_deleted"}

        if entry.embedding is not None:
            logger.debug("generate_memory_embedding: Entry %s hat bereits Embedding", entry_id)
            return {"skipped": True, "reason": "already_embedded"}

        # Embedding-Text: title + content (truncated)
        embed_text = f"{entry.title}\n\n{entry.content}"[:8000]

        client = openai.OpenAI(api_key=read_secret("OPENAI_API_KEY"))
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=embed_text,
        )
        embedding_vector = response.data[0].embedding

        with transaction.atomic():
            AgentMemoryEntry.all_objects.filter(id=entry_id).update(
                embedding=embedding_vector
            )

        logger.info(
            "generate_memory_embedding: Entry %s embedded (%d dims)",
            entry_id, len(embedding_vector),
        )
        return {"success": True, "entry_id": entry_id, "dims": len(embedding_vector)}

    except openai.RateLimitError as exc:
        logger.warning("generate_memory_embedding: Rate limit — retry in 60s")
        raise self.retry(exc=exc, countdown=60)
    except openai.APIError as exc:
        logger.error("generate_memory_embedding: OpenAI API error: %s", exc)
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception("generate_memory_embedding: Unerwarteter Fehler für Entry %s", entry_id)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    acks_late=True,
    max_retries=1,
    queue="maintenance",
)
def decay_old_memories(self, tenant_id: int = 1) -> dict:
    """
    Temporal Decay für AgentMemoryEntry (R-17, O-9).

    Schedule: Täglich via Celery Beat.
    Entries mit relevance_score < 0.1 werden soft-deleted.
    """
    from orchestrator_mcp.services.memory_service import MemoryService

    try:
        archived = MemoryService.decay_old_entries(tenant_id=tenant_id)
        logger.info("decay_old_memories: tenant=%s archived=%s", tenant_id, archived)
        return {"success": True, "archived": archived, "tenant_id": tenant_id}
    except Exception as exc:
        logger.exception("decay_old_memories: Fehler")
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Celery Beat Schedule (in settings/celery.py eintragen)
# ---------------------------------------------------------------------------
#
# CELERY_BEAT_SCHEDULE = {
#     "decay-old-memories-daily": {
#         "task": "orchestrator_mcp.tasks.decay_old_memories",
#         "schedule": crontab(hour=3, minute=0),  # 03:00 UTC täglich
#         "kwargs": {"tenant_id": 1},
#     },
# }
