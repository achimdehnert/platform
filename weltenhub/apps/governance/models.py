"""
DDL Governance Models
=====================

ADR-017: Domain Development Lifecycle

Tables (all in 'platform' schema):
- lkp_domain: Lookup domains (categories of choices)
- lkp_choice: Lookup choices (actual values)
- dom_business_case: Business Cases
- dom_use_case: Use Cases
- dom_adr: Architecture Decision Records
- dom_conversation: Inception conversations
- dom_adr_use_case: ADR-UseCase links
- dom_review: Reviews
- dom_status_history: Audit trail

NO HARDCODED ENUMS - everything from lkp_choice (ADR-015 compliant).
"""

from django.db import models
from django.contrib.auth import get_user_model
from typing import Optional


User = get_user_model()


# =============================================================================
# LOOKUP TABLES (ADR-015 Pattern)
# =============================================================================

class LookupDomain(models.Model):
    """
    Lookup Domain - Categories of choices.
    
    Examples: bc_status, uc_priority, adr_status, review_decision
    """
    
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Machine-readable code (e.g., 'bc_status')",
    )
    name = models.CharField(
        max_length=100,
        help_text="English display name",
    )
    name_de = models.CharField(
        max_length=100,
        blank=True,
        help_text="German display name",
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this domain",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform"."lkp_domain'
        verbose_name = "Lookup Domain"
        verbose_name_plural = "Lookup Domains"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}: {self.name}"


class LookupChoice(models.Model):
    """
    Lookup Choice - Actual values within a domain.
    
    Examples: draft, submitted, approved (for bc_status domain)
    """
    
    domain = models.ForeignKey(
        LookupDomain,
        on_delete=models.CASCADE,
        related_name="choices",
        verbose_name="Domain",
    )
    code = models.CharField(
        max_length=50,
        help_text="Machine-readable code (e.g., 'draft')",
    )
    name = models.CharField(
        max_length=100,
        help_text="English display name",
    )
    name_de = models.CharField(
        max_length=100,
        blank=True,
        help_text="German display name",
    )
    description = models.TextField(
        blank=True,
    )
    sort_order = models.IntegerField(
        default=0,
        db_index=True,
    )
    color = models.CharField(
        max_length=7,
        default="#3498db",
        help_text="Color for UI (hex)",
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon class (e.g., 'bi-check')",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata as JSON",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform"."lkp_choice'
        verbose_name = "Lookup Choice"
        verbose_name_plural = "Lookup Choices"
        ordering = ["domain", "sort_order", "code"]
        unique_together = [["domain", "code"]]
        indexes = [
            models.Index(fields=["domain", "is_active"]),
        ]

    def __str__(self):
        return f"{self.domain.code}.{self.code}: {self.name}"


# =============================================================================
# ABSTRACT BASE
# =============================================================================

class TimestampedModel(models.Model):
    """Abstract base with created/updated timestamps."""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# =============================================================================
# BUSINESS CASE
# =============================================================================

class BusinessCase(TimestampedModel):
    """
    Business Case - Describes a business need or feature request.
    
    Status values from: lkp_choice WHERE domain='bc_status'
    Category values from: lkp_choice WHERE domain='bc_category'
    Priority values from: lkp_choice WHERE domain='bc_priority'
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique code (e.g., 'BC-042')",
    )
    title = models.CharField(
        max_length=200,
        help_text="Short descriptive title",
    )
    
    # All choices from lkp_choice - NO ENUMS!
    category = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="business_cases_by_category",
        limit_choices_to={"domain__code": "bc_category"},
        verbose_name="Category",
    )
    status = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="business_cases_by_status",
        limit_choices_to={"domain__code": "bc_status"},
        verbose_name="Status",
    )
    priority = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="business_cases_by_priority",
        limit_choices_to={"domain__code": "bc_priority"},
        verbose_name="Priority",
        null=True,
        blank=True,
    )
    
    # Content
    problem_statement = models.TextField(
        help_text="What problem does this solve?",
    )
    target_audience = models.TextField(
        blank=True,
        help_text="Who benefits from this?",
    )
    expected_benefits = models.JSONField(
        default=list,
        blank=True,
        help_text="List of expected benefits",
    )
    scope = models.TextField(
        blank=True,
        help_text="What's included?",
    )
    out_of_scope = models.JSONField(
        default=list,
        blank=True,
        help_text="What's explicitly excluded?",
    )
    success_criteria = models.JSONField(
        default=list,
        blank=True,
        help_text="Measurable success criteria",
    )
    assumptions = models.JSONField(
        default=list,
        blank=True,
    )
    risks = models.JSONField(
        default=list,
        blank=True,
        help_text="List of risk objects with description, probability, impact",
    )
    
    # Architecture
    requires_adr = models.BooleanField(
        default=False,
        help_text="Does this require an ADR?",
    )
    adr_reason = models.TextField(
        blank=True,
        help_text="Why is an ADR required?",
    )
    
    # Ownership
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_business_cases",
    )

    class Meta:
        db_table = 'platform"."dom_business_case'
        verbose_name = "Business Case"
        verbose_name_plural = "Business Cases"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.code}: {self.title}"


# =============================================================================
# USE CASE
# =============================================================================

class UseCase(TimestampedModel):
    """
    Use Case - Derived from Business Case, describes user interaction.
    
    Status/Priority from lkp_choice.
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique code (e.g., 'UC-042-01')",
    )
    title = models.CharField(
        max_length=200,
    )
    
    # Parent
    business_case = models.ForeignKey(
        BusinessCase,
        on_delete=models.CASCADE,
        related_name="use_cases",
    )
    
    # Status from lkp_choice
    status = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="use_cases_by_status",
        limit_choices_to={"domain__code": "uc_status"},
    )
    priority = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="use_cases_by_priority",
        limit_choices_to={"domain__code": "uc_priority"},
        null=True,
        blank=True,
    )
    
    # Content
    actor = models.CharField(
        max_length=100,
        help_text="Primary actor (e.g., 'Registered User')",
    )
    preconditions = models.JSONField(
        default=list,
        blank=True,
    )
    postconditions = models.JSONField(
        default=list,
        blank=True,
    )
    main_flow = models.JSONField(
        default=list,
        blank=True,
        help_text="Main success scenario steps",
    )
    alternative_flows = models.JSONField(
        default=list,
        blank=True,
    )
    exception_flows = models.JSONField(
        default=list,
        blank=True,
    )
    
    # Estimation
    complexity = models.ForeignKey(
        LookupChoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="use_cases_by_complexity",
        limit_choices_to={"domain__code": "uc_complexity"},
    )
    estimated_effort = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., '3-5 days'",
    )

    class Meta:
        db_table = 'platform"."dom_use_case'
        verbose_name = "Use Case"
        verbose_name_plural = "Use Cases"
        ordering = ["business_case", "code"]
        indexes = [
            models.Index(fields=["business_case"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.code}: {self.title}"


# =============================================================================
# ADR (Architecture Decision Record)
# =============================================================================

class ADR(TimestampedModel):
    """
    Architecture Decision Record.
    
    Status from lkp_choice (domain='adr_status').
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="e.g., 'ADR-017'",
    )
    title = models.CharField(
        max_length=200,
    )
    
    # Status
    status = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="adrs_by_status",
        limit_choices_to={"domain__code": "adr_status"},
    )
    
    # Content (following ADR template)
    context = models.TextField(
        help_text="What is the context and problem?",
    )
    decision = models.TextField(
        help_text="What is the decision?",
    )
    consequences = models.TextField(
        blank=True,
        help_text="What are the consequences?",
    )
    alternatives = models.JSONField(
        default=list,
        blank=True,
        help_text="Considered alternatives",
    )
    
    # Relations
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseded_by",
        help_text="Previous ADR this supersedes",
    )
    
    # File reference
    file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path to ADR markdown file",
    )

    class Meta:
        db_table = 'platform"."dom_adr'
        verbose_name = "ADR"
        verbose_name_plural = "ADRs"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.code}: {self.title}"


# =============================================================================
# ADR-USE CASE LINK
# =============================================================================

class ADRUseCaseLink(TimestampedModel):
    """
    Links ADRs to Use Cases.
    
    Relationship type from lkp_choice (domain='adr_uc_relationship').
    """
    
    adr = models.ForeignKey(
        ADR,
        on_delete=models.CASCADE,
        related_name="use_case_links",
    )
    use_case = models.ForeignKey(
        UseCase,
        on_delete=models.CASCADE,
        related_name="adr_links",
    )
    relationship_type = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="adr_use_case_links",
        limit_choices_to={"domain__code": "adr_uc_relationship"},
        help_text="implements, affects, or references",
    )
    notes = models.TextField(
        blank=True,
    )

    class Meta:
        db_table = 'platform"."dom_adr_use_case'
        verbose_name = "ADR-Use Case Link"
        verbose_name_plural = "ADR-Use Case Links"
        unique_together = [["adr", "use_case"]]

    def __str__(self):
        return f"{self.adr.code} → {self.use_case.code}"


# =============================================================================
# CONVERSATION (Inception Dialog)
# =============================================================================

class Conversation(TimestampedModel):
    """
    Inception Conversation - Dialog between user and AI.
    """
    
    session_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique session identifier",
    )
    business_case = models.ForeignKey(
        BusinessCase,
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True,
    )
    status = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="conversations_by_status",
        limit_choices_to={"domain__code": "conversation_status"},
    )
    started_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'platform"."dom_conversation'
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Conversation {self.session_id}"


class ConversationTurn(TimestampedModel):
    """
    Single turn in a conversation.
    """
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="turns",
    )
    turn_number = models.PositiveIntegerField()
    role = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="conversation_turns_by_role",
        limit_choices_to={"domain__code": "conversation_role"},
        help_text="user, assistant, or system",
    )
    content = models.TextField()
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Token usage, model info, etc.",
    )

    class Meta:
        db_table = 'platform"."dom_conversation_turn'
        verbose_name = "Conversation Turn"
        verbose_name_plural = "Conversation Turns"
        ordering = ["conversation", "turn_number"]
        unique_together = [["conversation", "turn_number"]]

    def __str__(self):
        return f"Turn {self.turn_number} ({self.role.code})"


# =============================================================================
# REVIEW
# =============================================================================

class Review(TimestampedModel):
    """
    Review for BC, UC, or ADR.
    
    Entity type and decision from lkp_choice.
    """
    
    entity_type = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="reviews_by_entity_type",
        limit_choices_to={"domain__code": "review_entity_type"},
        help_text="business_case, use_case, or adr",
    )
    entity_id = models.BigIntegerField(
        help_text="ID of the reviewed entity",
    )
    
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    decision = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="reviews_by_decision",
        limit_choices_to={"domain__code": "review_decision"},
        help_text="approved, rejected, or changes_requested",
    )
    comments = models.TextField(
        blank=True,
    )
    requested_changes = models.JSONField(
        default=list,
        blank=True,
    )

    class Meta:
        db_table = 'platform"."dom_review'
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["reviewer"]),
        ]

    def __str__(self):
        return f"Review {self.entity_type.code}:{self.entity_id}"

    def get_entity(self) -> Optional[models.Model]:
        """Returns the reviewed entity."""
        entity_code = self.entity_type.code if self.entity_type else None
        if entity_code == "business_case":
            return BusinessCase.objects.filter(id=self.entity_id).first()
        elif entity_code == "use_case":
            return UseCase.objects.filter(id=self.entity_id).first()
        elif entity_code == "adr":
            return ADR.objects.filter(id=self.entity_id).first()
        return None


# =============================================================================
# STATUS HISTORY (Audit Trail)
# =============================================================================

class StatusHistory(TimestampedModel):
    """
    Audit trail for status changes.
    """
    
    entity_type = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="status_history_by_entity_type",
        limit_choices_to={"domain__code": "review_entity_type"},
    )
    entity_id = models.BigIntegerField()
    
    old_status = models.ForeignKey(
        LookupChoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_history_old",
    )
    new_status = models.ForeignKey(
        LookupChoice,
        on_delete=models.PROTECT,
        related_name="status_history_new",
    )
    
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_changes",
    )
    reason = models.TextField(
        blank=True,
    )

    class Meta:
        db_table = 'platform"."dom_status_history'
        verbose_name = "Status History"
        verbose_name_plural = "Status Histories"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        old = self.old_status.code if self.old_status else "None"
        return f"{self.entity_type.code}:{self.entity_id} {old} → {self.new_status.code}"
