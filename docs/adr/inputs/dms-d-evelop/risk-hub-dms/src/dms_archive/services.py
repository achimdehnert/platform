"""
src/dms_archive/services.py
============================
Service Layer für die DMS-Archivierung aus risk-hub.

Verantwortlich für:
  1. PDF-Generierung des risk-hub Dokuments
  2. Übertragung an d.velop DMS via dms_hub Client
  3. Persistierung des Archiv-Status
  4. Dispatch des Celery-Tasks

Aufruf-Punkte (nur aus anderen services.py, nie aus Views):
  - dsb/services/audit_service.py   → nach Audit-Abschluss
  - dsb/services/breach_service.py  → nach Datenpannen-Meldung
  - dsb/services/report_service.py  → nach Jahresbericht-Generierung
  - risk/services/assessment_service.py → nach Beurteilungs-Export
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from django.db import transaction

if TYPE_CHECKING:
    from .models import DmsArchiveRecord

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Payload-Dataclass (typisierte Übergabe an den Task)
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class ArchiveRequest:
    tenant_id:    UUID
    source_type:  str          # DmsArchiveRecord.DocumentType value
    source_id:    UUID         # PK des Quell-Objekts
    source_label: str          # Lesbare Bezeichnung für DMS
    performed_by: UUID | None  # User-UUID

    # DMS-Metadaten für d.velop Mapping
    dms_category:  str                    # d.velop Kategorie-ID
    dms_properties: dict[str, str]        # Freitext-Eigenschaften


# ────────────────────────────────────────────────────────────────────────────
# Haupt-Service
# ────────────────────────────────────────────────────────────────────────────

class DmsArchiveService:

    @staticmethod
    @transaction.atomic
    def schedule_archival(request: ArchiveRequest) -> "DmsArchiveRecord":
        """
        Legt einen PENDING-Datensatz an und dispatcht den Celery-Task.
        Idempotent: gibt bestehenden SUCCESS-Eintrag zurück, ohne neu zu archivieren.
        """
        from .models import DmsArchiveRecord  # avoid circular at module level

        # Idempotenz-Check: schon erfolgreich archiviert?
        existing = DmsArchiveRecord.objects.filter(
            tenant_id=request.tenant_id,
            source_id=request.source_id,
            status=DmsArchiveRecord.ArchiveStatus.SUCCESS,
        ).first()
        if existing:
            logger.info(
                "dms_archive.already_archived",
                extra={"source_id": str(request.source_id), "dms_doc_id": existing.dms_document_id},
            )
            return existing

        record = DmsArchiveRecord.objects.create(
            tenant_id    = request.tenant_id,
            source_type  = request.source_type,
            source_id    = request.source_id,
            source_label = request.source_label,
            archived_by_id = request.performed_by,
            status       = DmsArchiveRecord.ArchiveStatus.PENDING,
        )

        # Task NACH dem DB-Commit dispatchen (transaction.on_commit)
        from .tasks import archive_document_to_dms  # noqa: PLC0415
        transaction.on_commit(
            lambda: archive_document_to_dms.apply_async(
                kwargs={
                    "record_id":       str(record.id),
                    "source_type":     request.source_type,
                    "source_id":       str(request.source_id),
                    "tenant_id":       str(request.tenant_id),
                    "dms_category":    request.dms_category,
                    "dms_properties":  request.dms_properties,
                    "source_label":    request.source_label,
                },
                queue="dms",
            )
        )
        return record

    @staticmethod
    def get_archive_status(tenant_id: UUID, source_id: UUID) -> "DmsArchiveRecord | None":
        from .models import DmsArchiveRecord  # noqa: PLC0415
        return DmsArchiveRecord.objects.filter(
            tenant_id=tenant_id,
            source_id=source_id,
        ).order_by("-created_at").first()

    @staticmethod
    def retry_failed(tenant_id: UUID, source_id: UUID, performed_by: UUID) -> "DmsArchiveRecord | None":
        """Schlägt nach 3 Versuchen fehl — danach manueller Eingriff nötig."""
        from .models import DmsArchiveRecord  # noqa: PLC0415

        record = DmsArchiveRecord.objects.filter(
            tenant_id=tenant_id,
            source_id=source_id,
            status=DmsArchiveRecord.ArchiveStatus.FAILED,
        ).first()

        if not record:
            return None
        if record.retry_count >= 3:
            raise ValueError(
                f"Maximale Anzahl Wiederholungen (3) für {source_id} erreicht. "
                "Bitte manuell prüfen."
            )

        record.status = DmsArchiveRecord.ArchiveStatus.RETRYING
        record.save(update_fields=["status", "updated_at"])

        from .tasks import archive_document_to_dms  # noqa: PLC0415
        archive_document_to_dms.apply_async(
            kwargs={
                "record_id":     str(record.id),
                "source_type":   record.source_type,
                "source_id":     str(record.source_id),
                "tenant_id":     str(record.tenant_id),
                "dms_category":  record.dms_category,
                "dms_properties": {},
                "source_label":  record.source_label,
            },
            queue="dms",
        )
        return record


# ────────────────────────────────────────────────────────────────────────────
# PDF-Export-Router
# ────────────────────────────────────────────────────────────────────────────

class RiskHubPdfExporter:
    """
    Erzeugt ein PDF-Byte-Objekt für das jeweilige risk-hub Dokument.
    Dispatcher: leitet an den zuständigen Domain-Service weiter.
    """

    @staticmethod
    def export(source_type: str, source_id: UUID, tenant_id: UUID) -> tuple[bytes, str]:
        """
        Returns: (pdf_bytes, filename)
        Raises:  ValueError bei unbekanntem source_type
                 ObjectDoesNotExist wenn Objekt nicht gefunden
        """
        from .models import DmsArchiveRecord  # noqa: PLC0415

        exporters = {
            DmsArchiveRecord.DocumentType.PRIVACY_AUDIT:   _export_privacy_audit,
            DmsArchiveRecord.DocumentType.AUDIT_FINDING:   _export_audit_finding,
            DmsArchiveRecord.DocumentType.DATA_BREACH:     _export_data_breach,
            DmsArchiveRecord.DocumentType.VVT:             _export_vvt,
            DmsArchiveRecord.DocumentType.RISK_ASSESSMENT: _export_risk_assessment,
            DmsArchiveRecord.DocumentType.JAHRESBERICHT:   _export_jahresbericht,
        }
        exporter = exporters.get(source_type)
        if not exporter:
            raise ValueError(f"Kein Exporter für source_type '{source_type}' registriert.")
        return exporter(source_id, tenant_id)


# ── Einzelne Exporter (rufen vorhandene report_service.py-Methoden auf) ────

def _export_privacy_audit(source_id: UUID, tenant_id: UUID) -> tuple[bytes, str]:
    from src.dsb.models.audit import PrivacyAudit  # noqa: PLC0415
    from src.dsb.services.report_service import DsbReportService  # noqa: PLC0415

    audit = PrivacyAudit.objects.get(id=source_id, tenant_id=tenant_id)
    pdf   = DsbReportService.export_audit_pdf(audit)
    filename = f"Datenschutz-Audit_{audit.mandate.name}_{audit.audit_date:%Y-%m-%d}.pdf"
    return pdf, filename


def _export_audit_finding(source_id: UUID, tenant_id: UUID) -> tuple[bytes, str]:
    from src.dsb.models.audit import AuditFinding  # noqa: PLC0415
    from src.dsb.services.report_service import DsbReportService  # noqa: PLC0415

    finding  = AuditFinding.objects.get(id=source_id, tenant_id=tenant_id)
    pdf      = DsbReportService.export_finding_pdf(finding)
    filename = f"Audit-Befund_{finding.title[:40]}_{finding.created_at:%Y-%m-%d}.pdf"
    return pdf, filename


def _export_data_breach(source_id: UUID, tenant_id: UUID) -> tuple[bytes, str]:
    from src.dsb.models.breach import Breach  # noqa: PLC0415
    from src.dsb.services.breach_service import BreachService  # noqa: PLC0415

    breach   = Breach.objects.get(id=source_id, tenant_id=tenant_id)
    pdf      = BreachService.export_breach_report_pdf(breach)
    filename = f"Datenpanne_{breach.mandate.name}_{breach.discovered_at:%Y-%m-%d}.pdf"
    return pdf, filename


def _export_vvt(source_id: UUID, tenant_id: UUID) -> tuple[bytes, str]:
    from src.dsb.models.vvt import ProcessingActivity  # noqa: PLC0415
    from src.dsb.services.vvt_service import VvtService  # noqa: PLC0415

    vvt      = ProcessingActivity.objects.get(id=source_id, tenant_id=tenant_id)
    pdf      = VvtService.export_vvt_pdf(vvt)
    filename = f"VVT_{vvt.name[:50]}_{vvt.number}.pdf"
    return pdf, filename


def _export_risk_assessment(source_id: UUID, tenant_id: UUID) -> tuple[bytes, str]:
    from src.risk.models import Assessment  # noqa: PLC0415
    from src.risk.services.assessment_service import AssessmentService  # noqa: PLC0415

    assessment = Assessment.objects.get(id=source_id, tenant_id=tenant_id)
    pdf        = AssessmentService.export_pdf(assessment)
    filename   = f"Gefährdungsbeurteilung_{assessment.title[:50]}_{assessment.created_at:%Y-%m-%d}.pdf"
    return pdf, filename


def _export_jahresbericht(source_id: UUID, tenant_id: UUID) -> tuple[bytes, str]:
    from src.dsb.services.report_service import DsbReportService  # noqa: PLC0415

    pdf, meta = DsbReportService.export_jahresbericht_pdf(source_id, tenant_id)
    filename  = f"DSB-Jahresbericht_{meta['year']}_{meta['mandate_name']}.pdf"
    return pdf, filename
