"""
src/dms_archive/tasks.py
========================
Celery-Task für asynchrone DMS-Archivierung.

Platform-Regeln:
  - asgiref.async_to_sync → KEIN asyncio.run() in Celery
  - bind=True für self.retry()
  - max_retries=3, exponentielles Backoff
  - Alle Exceptions werden geloggt + im DmsArchiveRecord persistiert
  - Queue: "dms" (dedizierte Worker-Queue, nicht default)
"""
from __future__ import annotations

import logging
from uuid import UUID

from celery import shared_task

logger = logging.getLogger(__name__)

# DMS-Konfiguration: lokale Kategorie-ID → d.velop Kategorie-ID
# Wird ergänzt sobald d.velop-Repository konfiguriert ist
DVELOP_CATEGORY_MAP = {
    "PRIVACY_AUDIT":   "DSGVO_AUDIT",
    "AUDIT_FINDING":   "DSGVO_BEFUND",
    "DATA_BREACH":     "DSGVO_PANNE",
    "VVT":             "DSGVO_VVT",
    "DSFA":            "DSGVO_DSFA",
    "AVV":             "DSGVO_AVV",
    "RISK_ASSESSMENT": "GB_BERICHT",
    "INCIDENT_REPORT": "GB_VORFALL",
    "JAHRESBERICHT":   "DSGVO_JAHRESBERICHT",
}


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,          # 1 min → 2 min → 4 min (exponentiell)
    queue="dms",
    name="dms_archive.archive_document",
    acks_late=True,                   # ACK erst nach erfolgreichem Abschluss
    reject_on_worker_lost=True,
)
def archive_document_to_dms(
    self,
    *,
    record_id: str,
    source_type: str,
    source_id: str,
    tenant_id: str,
    dms_category: str,
    dms_properties: dict,
    source_label: str,
) -> dict:
    """
    Haupttask: Holt PDF aus risk-hub, lädt es ins d.velop DMS hoch,
    aktualisiert DmsArchiveRecord.

    Returns: {"status": "success", "dms_doc_id": "..."}
    """
    from .models import DmsArchiveRecord  # noqa: PLC0415
    from .services import RiskHubPdfExporter  # noqa: PLC0415

    try:
        record = DmsArchiveRecord.objects.get(id=record_id)
    except DmsArchiveRecord.DoesNotExist:
        logger.error("dms_archive.record_not_found", extra={"record_id": record_id})
        return {"status": "error", "reason": "record_not_found"}

    # Task-ID im Record speichern (für Monitoring)
    record.celery_task_id = self.request.id
    record.save(update_fields=["celery_task_id"])

    logger.info(
        "dms_archive.task_started",
        extra={
            "record_id": record_id,
            "source_type": source_type,
            "source_id": source_id,
            "attempt": self.request.retries + 1,
        },
    )

    try:
        # 1. PDF generieren
        pdf_bytes, filename = RiskHubPdfExporter.export(
            source_type=source_type,
            source_id=UUID(source_id),
            tenant_id=UUID(tenant_id),
        )

        # 2. DMS-Client holen (Repository für diesen Mandanten)
        dms_doc_id, repo_id = _upload_to_dms(
            tenant_id=UUID(tenant_id),
            filename=filename,
            pdf_bytes=pdf_bytes,
            dms_category=dms_category,
            dms_properties={
                **dms_properties,
                "Quelle": "risk-hub",
                "Dokumenttyp": source_type,
                "Mandant-ID": tenant_id,
            },
        )

        # 3. Record aktualisieren
        record.mark_success(
            dms_doc_id=dms_doc_id,
            repo_id=repo_id,
            category=dms_category,
        )

        logger.info(
            "dms_archive.task_success",
            extra={"record_id": record_id, "dms_doc_id": dms_doc_id},
        )
        return {"status": "success", "dms_doc_id": dms_doc_id}

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.warning(
            "dms_archive.task_failed",
            extra={
                "record_id": record_id,
                "error": error_msg,
                "attempt": self.request.retries + 1,
            },
            exc_info=True,
        )
        record.mark_failed(error_msg)

        # Retry mit exponentiellem Backoff
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries),  # 60s, 120s, 240s
        )


# ────────────────────────────────────────────────────────────────────────────
# Helper: DMS-Upload
# ────────────────────────────────────────────────────────────────────────────

def _upload_to_dms(
    tenant_id: UUID,
    filename: str,
    pdf_bytes: bytes,
    dms_category: str,
    dms_properties: dict[str, str],
) -> tuple[str, str]:
    """
    Holt den DMS-Client für den Mandanten und lädt das Dokument hoch.
    Returns: (dms_document_id, repo_id)
    """
    # Importiere dms-hub Client (cross-hub via REST oder direkte Library-Nutzung)
    # Option A: dms-hub ist installiertes Package → direkter Import
    # Option B: REST-Call an dms-hub API
    # → Wir nutzen Option A (dms_hub als lokales Package im risk-hub venv)
    from dms_hub.client.dvelop_client import DvelopDmsClient  # noqa: PLC0415

    # Repository-Konfiguration für diesen Mandanten aus DB lesen
    repo_id, base_url = _get_tenant_dms_config(tenant_id)

    from platform_context.secrets import read_secret  # noqa: PLC0415
    api_key = read_secret("DVELOP_API_KEY")

    with DvelopDmsClient(base_url=base_url, api_key=api_key) as client:
        doc_id = client.upload_document(
            repo_id,
            filename=filename,
            file_content=pdf_bytes,
            category=dms_category,
            properties=dms_properties,
            content_type="application/pdf",
        )
    return doc_id, repo_id


def _get_tenant_dms_config(tenant_id: UUID) -> tuple[str, str]:
    """Holt repo_id + base_url aus der DmsRepository-Konfiguration."""
    # Entweder aus dms_hub DB-Model (wenn im selben Django-Projekt):
    try:
        from dms_hub.models import DmsRepository  # noqa: PLC0415
        repo = DmsRepository.objects.get(
            tenant_id=str(tenant_id),
            is_active=True,
            deleted_at__isnull=True,
        )
        return repo.repo_id, repo.base_url
    except Exception:
        # Fallback: aus Settings (für risk-hub als eigenständigen Service)
        from django.conf import settings  # noqa: PLC0415
        return (
            settings.DVELOP_DEFAULT_REPO_ID,
            settings.DVELOP_BASE_URL,
        )
