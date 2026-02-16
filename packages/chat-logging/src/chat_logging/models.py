"""Django models for chat conversation logging & QM.

Per ADR-037: ChatConversation, ChatMessage, UseCaseCandidate,
EvaluationScore.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class ChatConversation(models.Model):
    """A complete chat session between a user and an agent."""

    class GoalType(models.TextChoices):
        TRIP_PLANNING = "trip_planning", "Reiseplanung"
        STORY_CONFIG = "story_config", "Story-Konfiguration"
        ENRICHMENT = "enrichment", "Anreicherung"
        CHAPTER_WRITING = "chapter_writing", "Kapitel-Schreiben"
        RESEARCH = "research", "Recherche"
        GENERAL = "general", "Allgemein"

    class OutcomeStatus(models.TextChoices):
        COMPLETED = "completed", "Erfolgreich"
        PARTIAL = "partial", "Teilweise"
        ABANDONED = "abandoned", "Abgebrochen"
        ERROR = "error", "Fehlgeschlagen"

    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Offen"
        REVIEWED = "reviewed", "Geprüft"
        ACTION_TAKEN = "action_taken", "Maßnahme eingeleitet"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    session_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="ChatAgent session ID",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_conversations",
    )
    app_name = models.CharField(
        max_length=50,
        db_index=True,
        help_text="e.g. drifttales, bfagent, weltenhub",
    )
    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )

    # --- Context (Goal) ---
    goal_type = models.CharField(
        max_length=30,
        choices=GoalType.choices,
        default=GoalType.GENERAL,
    )
    goal_summary = models.TextField(
        blank=True,
        help_text="Auto-extracted or manually set conversation goal",
    )

    # --- Outcome ---
    outcome_status = models.CharField(
        max_length=20,
        choices=OutcomeStatus.choices,
        default=OutcomeStatus.PARTIAL,
    )
    outcome_summary = models.TextField(blank=True)
    outcome_artifacts = models.JSONField(
        default=dict,
        blank=True,
        help_text='e.g. {"trip_id": 42, "stops_created": 3}',
    )

    # --- QM (Quality Management) ---
    satisfaction_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="User rating 1-5 (if collected)",
    )
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    review_notes = models.TextField(blank=True)
    improvement_tags = models.JSONField(
        default=list,
        blank=True,
        help_text='e.g. ["prompt_unclear", "wrong_tool", "slow"]',
    )

    # --- Metrics ---
    message_count = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    total_tool_calls = models.PositiveIntegerField(default=0)
    total_latency_ms = models.PositiveIntegerField(default=0)
    models_used = models.JSONField(
        default=list,
        blank=True,
        help_text="List of LLM model names used",
    )

    # --- Timestamps ---
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["app_name", "started_at"]),
            models.Index(fields=["outcome_status", "app_name"]),
            models.Index(fields=["review_status"]),
            models.Index(fields=["goal_type", "app_name"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.app_name}:{self.session_id[:12]} "
            f"({self.outcome_status})"
        )

    @property
    def duration_seconds(self) -> float | None:
        """Duration of the conversation in seconds."""
        if self.ended_at and self.started_at:
            return (
                self.ended_at - self.started_at
            ).total_seconds()
        return None


class ChatMessage(models.Model):
    """A single message in a chat conversation."""

    class Role(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
    )
    content = models.TextField(blank=True, default="")
    model = models.CharField(max_length=100, blank=True)
    tool_calls = models.JSONField(
        default=list,
        blank=True,
        help_text="Tool calls made in this message",
    )
    tool_call_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="For tool-result messages",
    )
    name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Tool name (tool role only)",
    )
    tokens_used = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["conversation", "created_at"]
            ),
            models.Index(fields=["role"]),
        ]

    def __str__(self) -> str:
        preview = self.content[:80] if self.content else "(empty)"
        return f"[{self.role}] {preview}"


class UseCaseCandidate(models.Model):
    """A detected user need that the agent could not fulfill."""

    class DetectionMethod(models.TextChoices):
        NO_TOOL_MATCH = "no_tool_match", "Kein passendes Tool"
        EXPLICIT_DECLINE = (
            "explicit_decline",
            "Agent lehnt ab",
        )
        REPEATED_REPHRASE = (
            "repeated_rephrase",
            "User wiederholt sich",
        )
        SESSION_ABANDONED = (
            "session_abandoned",
            "Session abgebrochen",
        )
        TOOL_ERROR = "tool_error", "Tool-Fehler"
        MANUAL = "manual", "Manuell markiert"

    class Status(models.TextChoices):
        NEW = "new", "Neu"
        CONFIRMED = "confirmed", "Bestätigt"
        PLANNED = "planned", "Geplant"
        IMPLEMENTED = "implemented", "Umgesetzt"
        REJECTED = "rejected", "Abgelehnt"

    class Priority(models.TextChoices):
        LOW = "low", "Niedrig"
        MEDIUM = "medium", "Mittel"
        HIGH = "high", "Hoch"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="use_case_candidates",
    )
    trigger_message = models.ForeignKey(
        ChatMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    detection_method = models.CharField(
        max_length=30,
        choices=DetectionMethod.choices,
    )
    user_intent = models.TextField(
        help_text="What the user wanted to achieve",
    )
    app_name = models.CharField(
        max_length=50,
        db_index=True,
    )
    frequency = models.PositiveIntegerField(
        default=1,
        help_text="How often this use case was detected",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-frequency", "-created_at"]
        indexes = [
            models.Index(fields=["status", "app_name"]),
            models.Index(fields=["detection_method"]),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.status}] {self.user_intent[:60]} "
            f"(x{self.frequency})"
        )


class EvaluationScore(models.Model):
    """Evaluation score for a conversation."""

    class Evaluator(models.TextChoices):
        DEEPEVAL = "deepeval", "DeepEval"
        LANGFUSE = "langfuse", "LangFuse"
        CUSTOM = "custom", "Custom"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="evaluation_scores",
    )
    evaluator = models.CharField(
        max_length=20,
        choices=Evaluator.choices,
    )
    metric_name = models.CharField(
        max_length=100,
        help_text="e.g. answer_relevancy, tool_correctness",
    )
    score = models.FloatField(
        help_text="Score value (0.0-1.0 for most metrics)",
    )
    reason = models.TextField(
        blank=True,
        help_text="LLM-generated explanation for the score",
    )
    metadata = models.JSONField(default=dict, blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-evaluated_at"]
        indexes = [
            models.Index(
                fields=["conversation", "metric_name"]
            ),
            models.Index(
                fields=["evaluator", "metric_name"]
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "conversation",
                    "evaluator",
                    "metric_name",
                ],
                name="unique_eval_per_conversation",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.metric_name}: {self.score:.2f} "
            f"({self.evaluator})"
        )
