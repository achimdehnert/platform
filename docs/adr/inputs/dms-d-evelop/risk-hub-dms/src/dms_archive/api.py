"""
src/dms_archive/api.py
=======================
Django Ninja API-Endpunkte für DMS-Archivierungs-Status.
Dünne Views — alle Logik in services.py.

Einbinden in risk-hub/config/urls.py:
    api.add_router("/dms-archive/", dms_archive_router)
"""
from __future__ import annotations

from uuid import UUID

from ninja import Router
from ninja.errors import HttpError

from .models import DmsArchiveRecord
from .services import DmsArchiveService

router = Router(tags=["DMS Archive"])


# ── Schema ──────────────────────────────────────────────────────────────────

from ninja import Schema
from datetime import datetime


class ArchiveStatusOut(Schema):
    record_id:          UUID
    source_type:        str
    source_label:       str
    status:             str
    dms_document_id:    str
    retry_count:        int
    error_message:      str
    created_at:         datetime
    updated_at:         datetime


class RetryOut(Schema):
    record_id: UUID
    status:    str
    message:   str


# ── Endpunkte ────────────────────────────────────────────────────────────────

@router.get("/status/{source_id}", response=ArchiveStatusOut | None)
def get_archive_status(request, source_id: UUID):
    """Archivierungs-Status eines risk-hub Objekts abfragen."""
    tenant_id = request.auth.tenant_id  # via risk-hub Auth-Middleware
    record = DmsArchiveService.get_archive_status(tenant_id, source_id)
    if not record:
        return None
    return ArchiveStatusOut(
        record_id       = record.id,
        source_type     = record.source_type,
        source_label    = record.source_label,
        status          = record.status,
        dms_document_id = record.dms_document_id,
        retry_count     = record.retry_count,
        error_message   = record.error_message,
        created_at      = record.created_at,
        updated_at      = record.updated_at,
    )


@router.post("/retry/{source_id}", response=RetryOut)
def retry_archival(request, source_id: UUID):
    """Fehlgeschlagene Archivierung manuell wiederholen (max. 3×)."""
    tenant_id = request.auth.tenant_id
    performed_by = request.auth.user_id

    try:
        record = DmsArchiveService.retry_failed(tenant_id, source_id, performed_by)
    except ValueError as exc:
        raise HttpError(400, str(exc))

    if not record:
        raise HttpError(404, f"Kein fehlgeschlagener Archiv-Eintrag für {source_id} gefunden.")

    return RetryOut(
        record_id = record.id,
        status    = record.status,
        message   = f"Archivierung wird wiederholt (Versuch {record.retry_count + 1}/3).",
    )


@router.get("/failed", response=list[ArchiveStatusOut])
def list_failed_archives(request):
    """Alle fehlgeschlagenen Archivierungen des Mandanten."""
    tenant_id = request.auth.tenant_id
    records   = DmsArchiveRecord.objects.filter(
        tenant_id=tenant_id,
        status=DmsArchiveRecord.ArchiveStatus.FAILED,
    ).order_by("-created_at")[:50]

    return [
        ArchiveStatusOut(
            record_id       = r.id,
            source_type     = r.source_type,
            source_label    = r.source_label,
            status          = r.status,
            dms_document_id = r.dms_document_id,
            retry_count     = r.retry_count,
            error_message   = r.error_message,
            created_at      = r.created_at,
            updated_at      = r.updated_at,
        )
        for r in records
    ]
