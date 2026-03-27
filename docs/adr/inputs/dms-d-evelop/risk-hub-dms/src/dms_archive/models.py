"""
src/dms_archive/models.py
==========================
Tracking-Model für alle DMS-Archivierungen aus dem risk-hub.

Platform-Standards (ADR-038 Review-Erkenntnisse angewendet):
  - UUID PK
  - tenant_id UUIDField (risk-hub-Pattern)
  - UniqueConstraint statt unique=True
  - on_delete=PROTECT auf Document-Referenz
  - TextChoices mit max_length
  - kein JSONField — alles normalisiert
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class DmsArchiveRecord(models.Model):
    """
    Lückenloser Audit-Trail jeder DMS-Archivierung.

    Wird IMMER beim Ablegen eines Dokuments im d.velop DMS erzeugt —
    egal ob erfolgreich oder fehlgeschlagen. Nie löschen, nie updaten.
    """

    class DocumentType(models.TextChoices):
        PRIVACY_AUDIT      = "PRIVACY_AUDIT",      "Datenschutz-Audit"
        AUDIT_FINDING      = "AUDIT_FINDING",       "Audit-Befund"
        DATA_BREACH        = "DATA_BREACH",         "Datenpanne"
        VVT                = "VVT",                 "Verarbeitungsverzeichnis"
        DSFA               = "DSFA",                "Datenschutz-Folgenabschätzung"
        AVV                = "AVV",                 "Auftragsverarbeitungsvertrag"
        RISK_ASSESSMENT    = "RISK_ASSESSMENT",     "Gefährdungsbeurteilung"
        INCIDENT_REPORT    = "INCIDENT_REPORT",     "Vorfallsbericht"
        JAHRESBERICHT      = "JAHRESBERICHT",       "Jahresbericht"

    class ArchiveStatus(models.TextChoices):
        PENDING   = "PENDING",   "Ausstehend"
        SUCCESS   = "SUCCESS",   "Erfolgreich archiviert"
        FAILED    = "FAILED",    "Fehlgeschlagen"
        RETRYING  = "RETRYING",  "Wird wiederholt"

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id      = models.UUIDField(db_index=True)

    # Referenz auf das risk-hub Quell-Objekt (lose Kopplung per UUID)
    source_type    = models.CharField(max_length=30, choices=DocumentType.choices)
    source_id      = models.UUIDField(db_index=True, help_text="UUID des Quell-Objekts im risk-hub")
    source_label   = models.CharField(max_length=500, help_text="Lesbarer Titel des Dokuments")

    # DMS-Seite (erst nach erfolgreichem Upload befüllt)
    dms_document_id   = models.CharField(max_length=255, blank=True, db_index=True)
    dms_repository_id = models.CharField(max_length=255, blank=True)
    dms_category      = models.CharField(max_length=100, blank=True)

    # Status
    status         = models.CharField(
        max_length=10, choices=ArchiveStatus.choices,
        default=ArchiveStatus.PENDING, db_index=True,
    )
    retry_count    = models.PositiveSmallIntegerField(default=0)
    error_message  = models.TextField(blank=True)

    # Wer hat archiviert?
    archived_by_id = models.UUIDField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True)

    created_at     = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dms_archive_record"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "source_type", "status"]),
            models.Index(fields=["tenant_id", "source_id"]),
        ]
        constraints = [
            # Genau ein erfolgreicher Archiveintrag pro Quell-Objekt
            models.UniqueConstraint(
                fields=["tenant_id", "source_id", "status"],
                condition=models.Q(status="SUCCESS"),
                name="uq_dmsarchive_one_success_per_source",
            )
        ]

    def __str__(self) -> str:
        return f"{self.source_type} {self.source_id} → DMS [{self.status}]"

    @property
    def is_archived(self) -> bool:
        return self.status == self.ArchiveStatus.SUCCESS

    def mark_success(self, dms_doc_id: str, repo_id: str, category: str) -> None:
        self.status           = self.ArchiveStatus.SUCCESS
        self.dms_document_id  = dms_doc_id
        self.dms_repository_id = repo_id
        self.dms_category     = category
        self.error_message    = ""
        self.save(update_fields=[
            "status", "dms_document_id", "dms_repository_id",
            "dms_category", "error_message", "updated_at",
        ])

    def mark_failed(self, error: str) -> None:
        self.status        = self.ArchiveStatus.FAILED
        self.error_message = error
        self.retry_count   += 1
        self.save(update_fields=["status", "error_message", "retry_count", "updated_at"])
