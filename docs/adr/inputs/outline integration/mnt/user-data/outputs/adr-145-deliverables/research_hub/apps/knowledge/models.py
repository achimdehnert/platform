"""research-hub: KnowledgeDocument model.

Fixes B3: Full Platform Standards compliance:
  - BigAutoField PK + public_id UUIDField
  - tenant_id = BigIntegerField(db_index=True)
  - deleted_at for soft-delete
  - UniqueConstraint (not unique_together)
  - i18n: _() from tag 1
  - Business logic in service layer only (see services.py)
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class KnowledgeDocumentStatus(models.TextChoices):
    """Processing status of the Knowledge Document enrichment pipeline."""

    PENDING = "pending", _("Ausstehend")
    ENRICHING = "enriching", _("Wird angereichert")
    ENRICHED = "enriched", _("Angereichert")
    ERROR = "error", _("Fehler")
    STALE = "stale", _("Veraltet")  # set after 90 days without outline update


class KnowledgeDocumentType(models.TextChoices):
    """Maps to Outline collection categories."""

    RUNBOOK = "runbook", _("Runbook")
    CONCEPT = "concept", _("Architektur-Konzept")
    LESSON_LEARNED = "lesson_learned", _("Lesson Learned")
    ADR_DRAFT = "adr_draft", _("ADR-Entwurf")
    HUB_DOCS = "hub_docs", _("Hub-Dokumentation")
    ADR_MIRROR = "adr_mirror", _("ADR Mirror (Read-Only)")
    OTHER = "other", _("Sonstiges")


class KnowledgeDocument(models.Model):
    """Mirror of an Outline document with AI-enrichment metadata.

    Platform Standards:
        ✅ BigAutoField PK (default via settings DEFAULT_AUTO_FIELD)
        ✅ public_id UUIDField
        ✅ tenant_id BigIntegerField(db_index=True)
        ✅ deleted_at soft-delete
        ✅ UniqueConstraint (not unique_together)
        ✅ i18n via _()

    The outline_id is the Outline document UUID (source of truth).
    This model stores enrichment metadata — the canonical content is in Outline.
    """

    # ------------------------------------------------------------------
    # Platform-required fields
    # ------------------------------------------------------------------
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Öffentliche ID"),
    )
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Mandanten-ID"),
        help_text=_("Referenz auf den Mandanten (kein FK — Platform-Standard)."),
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Gelöscht am"),
    )

    # ------------------------------------------------------------------
    # Outline-specific fields
    # ------------------------------------------------------------------
    outline_id = models.CharField(
        max_length=36,
        verbose_name=_("Outline Dokument-UUID"),
        help_text=_("UUID des Outline-Dokuments (unveränderlich nach Erstanlage)."),
    )
    outline_collection_id = models.CharField(
        max_length=36,
        verbose_name=_("Outline Collection-UUID"),
    )
    outline_url = models.URLField(
        max_length=500,
        verbose_name=_("Outline URL"),
    )
    doc_type = models.CharField(
        max_length=20,
        choices=KnowledgeDocumentType.choices,
        default=KnowledgeDocumentType.OTHER,
        verbose_name=_("Dokumenttyp"),
    )

    # ------------------------------------------------------------------
    # Content snapshot (for embedding / search without live API call)
    # ------------------------------------------------------------------
    title = models.CharField(max_length=500, verbose_name=_("Titel"))
    content_snapshot = models.TextField(
        blank=True,
        verbose_name=_("Inhalts-Snapshot"),
        help_text=_("Markdown-Inhalt zum Zeitpunkt der letzten Synchronisation."),
    )
    outline_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Zuletzt in Outline geändert"),
    )

    # ------------------------------------------------------------------
    # AI-Enrichment fields (populated by Celery tasks)
    # ------------------------------------------------------------------
    enrichment_status = models.CharField(
        max_length=20,
        choices=KnowledgeDocumentStatus.choices,
        default=KnowledgeDocumentStatus.PENDING,
        db_index=True,
        verbose_name=_("Anreicherungsstatus"),
    )
    summary = models.TextField(
        blank=True,
        verbose_name=_("KI-Zusammenfassung"),
    )
    keywords = models.JSONField(
        default=list,
        verbose_name=_("KI-Schlüsselwörter"),
        help_text=_("Extrahierte Suchbegriffe für semantische Suche."),
    )
    related_adrs = models.JSONField(
        default=list,
        verbose_name=_("Verwandte ADRs"),
        help_text=_('Liste von ADR-IDs, z.B. ["ADR-132", "ADR-145"].'),
    )
    enrichment_error = models.TextField(
        blank=True,
        verbose_name=_("Anreicherungsfehler"),
        help_text=_("Fehlerdetails des letzten fehlgeschlagenen Enrichment-Laufs."),
    )
    enriched_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Zuletzt angereichert"),
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Erstellt am"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Geändert am"))

    class Meta:
        app_label = "knowledge"
        verbose_name = _("Knowledge-Dokument")
        verbose_name_plural = _("Knowledge-Dokumente")
        ordering = ["-outline_updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "doc_type"], name="idx_kd_tenant_type"),
            models.Index(
                fields=["tenant_id", "enrichment_status"],
                name="idx_kd_tenant_enrich_status",
            ),
            models.Index(fields=["outline_id"], name="idx_kd_outline_id"),
        ]
        constraints = [
            # One active document per tenant per outline document (soft-delete aware)
            models.UniqueConstraint(
                fields=["tenant_id", "outline_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_knowledge_document_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.get_doc_type_display()}] {self.title} (tenant={self.tenant_id})"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_stale(self) -> bool:
        """True if enrichment_status is STALE or document not updated in 90 days."""
        from datetime import UTC, datetime, timedelta

        if self.enrichment_status == KnowledgeDocumentStatus.STALE:
            return True
        if self.outline_updated_at is None:
            return True
        age = datetime.now(UTC) - self.outline_updated_at
        return age > timedelta(days=90)
