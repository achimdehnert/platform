"""Document template models (generalized from ExDocTemplate/ExDocInstance)."""

import json
import uuid

from django.db import models

# Graceful import for TenantManager
try:
    from django_tenancy.managers import TenantManager
except ImportError:
    TenantManager = models.Manager


class DocumentTemplate(models.Model):
    """Wiederverwendbare Dokumentvorlage (modulübergreifend).

    Struktur als JSON:
    {
      "sections": [
        {
          "key": "section_1",
          "label": "1. Allgemeines",
          "fields": [
            {"key": "inhalt", "label": "Inhalt", "type": "textarea"}
          ]
        }
      ]
    }
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        ACCEPTED = "accepted", "Akzeptiert"
        ARCHIVED = "archived", "Archiviert"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    scope = models.CharField(
        max_length=50, blank=True, default="",
        help_text="Fachbereich, z.B. explosionsschutz, brandschutz, gbu, risk",
    )
    structure_json = models.TextField(
        default='{"sections": []}',
        help_text="Template-Struktur als JSON",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT,
    )
    source_filename = models.CharField(max_length=255, blank=True, default="")
    source_text = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "doc_template"
        verbose_name = "Dokumentvorlage"
        verbose_name_plural = "Dokumentvorlagen"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="ix_doctmpl_tenant_st"),
            models.Index(fields=["tenant_id", "scope"], name="ix_doctmpl_tenant_scope"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"

    @property
    def section_count(self) -> int:
        try:
            data = json.loads(self.structure_json)
            return len(data.get("sections", []))
        except (json.JSONDecodeError, TypeError):
            return 0

    @property
    def field_count(self) -> int:
        try:
            data = json.loads(self.structure_json)
            return sum(len(s.get("fields", [])) for s in data.get("sections", []))
        except (json.JSONDecodeError, TypeError):
            return 0

    def get_structure(self) -> dict:
        """Parse and return structure from JSON."""
        try:
            return json.loads(self.structure_json)
        except (json.JSONDecodeError, TypeError):
            return {"sections": []}

    def get_sections(self) -> list[dict]:
        """Return sections list from structure."""
        return self.get_structure().get("sections", [])


class DocumentInstance(models.Model):
    """Ausgefülltes Dokument basierend auf einem Template.

    Werte als JSON:
    {
      "section_1": {
        "inhalt": "Dieses Dokument..."
      }
    }
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        REVIEW = "review", "In Prüfung"
        APPROVED = "approved", "Freigegeben"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    template = models.ForeignKey(
        DocumentTemplate, on_delete=models.PROTECT, related_name="instances",
    )
    name = models.CharField(max_length=255)
    values_json = models.TextField(
        default="{}", help_text="Ausgefüllte Werte als JSON",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT,
    )
    source_filename = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Dateiname des importierten Dokuments",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "doc_instance"
        verbose_name = "Dokument"
        verbose_name_plural = "Dokumente"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="ix_docinst_tenant_st"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"

    def get_values(self) -> dict:
        """Parse and return values from JSON."""
        try:
            return json.loads(self.values_json)
        except (json.JSONDecodeError, TypeError):
            return {}
