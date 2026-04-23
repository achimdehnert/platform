"""Django models for content_store (ADR-130).

Platform-standards:
  - BigAutoField PK (ADR-022)
  - tenant_id BigIntegerField (ADR-109)
  - Service-Layer access only (ADR-041)
"""

from __future__ import annotations

import hashlib

from django.db import models
from django.utils.translation import gettext_lazy as _


class ContentSource(models.TextChoices):
    TRAVEL_BEAT = "travel-beat", _("Travel Beat")
    WELTENHUB = "weltenhub", _("Weltenhub")
    BFAGENT = "bfagent", _("BF Agent")
    PPTX_HUB = "pptx-hub", _("PPTX Hub")
    CAD_HUB = "cad-hub", _("CAD Hub")
    COACH_HUB = "coach-hub", _("Coach Hub")
    AGENT_TEAM = "agent-team", _("Agent Team")


class ContentType(models.TextChoices):
    STORY = "story", _("Story")
    CHAPTER = "chapter", _("Chapter")
    WORLD = "world", _("World")
    SCENE = "scene", _("Scene")
    CHARACTER = "character", _("Character")
    ADR = "adr", _("ADR")
    DRAFT = "draft", _("Draft")
    PRESENTATION = "presentation", _("Presentation")
    CAD_MODEL = "cad_model", _("CAD Model")
    PROMPT_RESULT = "prompt_result", _("Prompt Result")


class ContentItem(models.Model):
    """KI-generierter Inhalt — plattformweit, tenant-isoliert."""

    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
        help_text=_("0 = platform-internal"),
    )
    source = models.CharField(
        max_length=30,
        choices=ContentSource.choices,
        verbose_name=_("Source"),
    )
    type = models.CharField(
        max_length=30,
        choices=ContentType.choices,
        verbose_name=_("Content Type"),
    )
    ref_id = models.CharField(
        max_length=255,
        verbose_name=_("Reference ID"),
        help_text=_("App-seitige ID des Quellobjekts"),
    )
    content = models.TextField(verbose_name=_("Content"))
    sha256 = models.CharField(
        max_length=64,
        verbose_name=_("SHA-256"),
        help_text=_("Auto-computed on save"),
    )
    version = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Version"),
    )
    meta = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Metadata"),
    )
    model_used = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("LLM Model"),
        help_text=_("e.g. gpt-4o-mini, claude-sonnet-4-20250514"),
    )
    prompt_key = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name=_("Prompt Key"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )

    class Meta:
        app_label = "content_store"
        verbose_name = _("Content Item")
        verbose_name_plural = _("Content Items")
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "source"],
                name="cs_tenant_source_idx",
            ),
            models.Index(
                fields=["tenant_id", "type"],
                name="cs_tenant_type_idx",
            ),
            models.Index(
                fields=["ref_id"],
                name="cs_ref_id_idx",
            ),
            models.Index(
                fields=["sha256"],
                name="cs_sha256_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        self.sha256 = hashlib.sha256(
            self.content.encode("utf-8")
        ).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"ContentItem("
            f"{self.source}/{self.type} "
            f"ref={self.ref_id} v{self.version})"
        )


class ContentRelation(models.Model):
    """Beziehung zwischen zwei ContentItems."""

    source_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="outgoing_relations",
        verbose_name=_("Source Item"),
    )
    target_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="incoming_relations",
        verbose_name=_("Target Item"),
    )
    relation_type = models.CharField(
        max_length=50,
        verbose_name=_("Relation Type"),
        help_text=_(
            "e.g. 'derived_from', 'chapter_of', 'revision_of'"
        ),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    class Meta:
        app_label = "content_store"
        verbose_name = _("Content Relation")
        verbose_name_plural = _("Content Relations")
        unique_together = [
            ("source_item", "target_item", "relation_type"),
        ]

    def __str__(self) -> str:
        return (
            f"ContentRelation("
            f"{self.source_item_id} "
            f"--{self.relation_type}--> "
            f"{self.target_item_id})"
        )


class ComplianceStatus(models.TextChoices):
    COMPLIANT = "compliant", _("Compliant")
    WARNING = "warning", _("Warning")
    VIOLATION = "violation", _("Violation")


class AdrCompliance(models.Model):
    """ADR Drift-Detector Compliance-Ergebnis — tenant-isoliert."""

    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
    )
    adr_id = models.CharField(
        max_length=20,
        verbose_name=_("ADR ID"),
    )
    checked_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Checked At"),
    )
    drift_score = models.FloatField(
        verbose_name=_("Drift Score"),
    )
    status = models.CharField(
        max_length=20,
        choices=ComplianceStatus.choices,
        verbose_name=_("Status"),
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Details"),
    )

    class Meta:
        app_label = "content_store"
        verbose_name = _("ADR Compliance")
        verbose_name_plural = _("ADR Compliance Records")
        ordering = ["-checked_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "adr_id"],
                name="cs_compliance_tenant_adr_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"AdrCompliance("
            f"ADR-{self.adr_id} "
            f"score={self.drift_score:.2f} "
            f"status={self.status})"
        )
