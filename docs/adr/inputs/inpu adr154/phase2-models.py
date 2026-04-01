"""
orchestrator_mcp/models.py

AgentMemoryEntry — pgvector-backed semantic memory store für Cascade AI-Sessions.

Platform Standards:
  - BigAutoField PK + public_id UUIDField
  - tenant_id BigIntegerField(db_index=True)
  - Soft-Delete via deleted_at
  - UniqueConstraint (nicht unique_together)
  - i18n via gettext_lazy
"""
from __future__ import annotations

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from pgvector.django import VectorField  # pip: pgvector


class EntryType(models.TextChoices):
    ERROR_PATTERN = "error_pattern", _("Error Pattern")
    LESSON_LEARNED = "lesson_learned", _("Lesson Learned")
    DECISION = "decision", _("Decision")
    CONTEXT = "context", _("Session Context")
    TASK_RESULT = "task_result", _("Task Result")
    RULE_VIOLATION = "rule_violation", _("Rule Violation")
    REPO_FACT = "repo_fact", _("Repo Fact")


class ActiveMemoryManager(models.Manager):
    """Standardmäßig nur nicht-gelöschte Einträge."""

    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().filter(deleted_at__isnull=True)


class AgentMemoryEntry(models.Model):
    """
    Semantischer Memory-Eintrag für Cascade AI-Sessions.

    Lifecycle:
      - Schreiben: MemoryService.upsert_entry()
      - Suchen: MemoryService.search_similar()
      - Archivieren: MemoryService.decay_old_entries() (Celery Beat)
      - Soft-Delete: MemoryService.soft_delete()
    """

    # ------------------------------------------------------------------
    # PKs & Identität
    # ------------------------------------------------------------------
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Public ID"),
    )
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
        help_text=_("Isoliert Einträge pro Tenant (iil-Platform multi-tenant)."),
    )

    # ------------------------------------------------------------------
    # Klassifikation
    # ------------------------------------------------------------------
    entry_key = models.CharField(
        max_length=512,
        verbose_name=_("Entry Key"),
        help_text=_(
            "Deterministischer Schlüssel: '<type>:<repo>:<hash16>'. "
            "Z.B. 'error_pattern:risk-hub:a3f9c1d2'"
        ),
    )
    entry_type = models.CharField(
        max_length=64,
        choices=EntryType.choices,
        db_index=True,
        verbose_name=_("Entry Type"),
    )
    repo = models.CharField(
        max_length=256,
        blank=True,
        db_index=True,
        verbose_name=_("Repository"),
        help_text=_("Repo-Name aus repos.json, z.B. 'risk-hub'. Leer = plattformweit."),
    )

    # ------------------------------------------------------------------
    # Inhalt
    # ------------------------------------------------------------------
    title = models.CharField(max_length=512, verbose_name=_("Title"))
    content = models.TextField(verbose_name=_("Content"))
    tags = models.JSONField(
        default=list,
        verbose_name=_("Tags"),
        help_text=_("List[str] — für Filterung und Retrieval."),
    )
    structured_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Structured Data"),
        help_text=_(
            "Optionale strukturierte Daten je nach entry_type. "
            "ErrorPattern: {symptom, root_cause, fix, prevention}. "
            "Decision: {options_considered, chosen, rationale}."
        ),
    )

    # ------------------------------------------------------------------
    # Vector Embedding (pgvector)
    # ------------------------------------------------------------------
    embedding = VectorField(
        dimensions=1536,
        null=True,
        blank=True,
        verbose_name=_("Embedding"),
        help_text=_("OpenAI text-embedding-3-small (1536 dims)."),
    )

    # ------------------------------------------------------------------
    # Qualität & Decay
    # ------------------------------------------------------------------
    relevance_score = models.FloatField(
        default=1.0,
        verbose_name=_("Relevance Score"),
        help_text=_("0.0–1.0. Sinkt durch Temporal Decay. <0.1 → archivieren."),
    )
    access_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Access Count"),
        help_text=_("Erhöht bei jedem Retrieval-Treffer."),
    )
    last_accessed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Accessed"),
    )

    # ------------------------------------------------------------------
    # Timestamps & Soft-Delete
    # ------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Deleted At"),
        help_text=_("Soft-Delete. Null = aktiv."),
    )

    # ------------------------------------------------------------------
    # Manager
    # ------------------------------------------------------------------
    objects = ActiveMemoryManager()
    all_objects = models.Manager()  # inkl. soft-deleted, für Admin / Archivierung

    class Meta:
        verbose_name = _("Agent Memory Entry")
        verbose_name_plural = _("Agent Memory Entries")
        ordering = ["-relevance_score", "-updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "entry_type", "repo"]),
            models.Index(fields=["tenant_id", "updated_at"]),
            models.Index(fields=["entry_type", "relevance_score"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "entry_key"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_entry_key_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.entry_type}] {self.title[:60]}"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    @property
    def is_stale(self) -> bool:
        """Eintrag gilt als veraltet wenn relevance_score < 0.1."""
        return self.relevance_score < 0.1


class AgentSession(models.Model):
    """
    Tracks eine einzelne Cascade-Coding-Session.

    Ermöglicht Delta-Detection (O-9): "Was hat sich seit letzter Session geändert?"
    Löst R-11: Timestamp-Lookup auf AgentSession statt pgvector.
    """

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    tenant_id = models.BigIntegerField(db_index=True)

    repo = models.CharField(max_length=256, db_index=True)
    task_description = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True, db_index=True)

    error_count = models.PositiveIntegerField(default=0)
    correction_count = models.PositiveIntegerField(default=0)
    memory_entries_written = models.PositiveIntegerField(default=0)

    # Soft-Delete (Platform-Standard, auch wenn Sessions nicht gelöscht werden)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = ActiveMemoryManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _("Agent Session")
        verbose_name_plural = _("Agent Sessions")
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["tenant_id", "repo", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"Session {self.public_id} [{self.repo}] {self.started_at:%Y-%m-%d %H:%M}"
