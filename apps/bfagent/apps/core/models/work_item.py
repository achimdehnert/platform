# -*- coding: utf-8 -*-
"""
Unified Work Item System

Single Source of Truth für Bug, Feature, Task Management.
Ersetzt die fragmentierten TestRequirement + ComponentRegistry Ansätze.

Prinzipien:
- Ein Basis-Model (WorkItem) mit Type-Discriminator
- Spezialisierung via 1:1 Detail-Models (Komposition)
- Einheitliches LLM-Routing für alle Types
- Konsistente Status, Priority, Domain-Zuordnung
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator
import uuid
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS (als TextChoices für DB-Konsistenz)
# =============================================================================

class WorkItemType(models.TextChoices):
    """Work Item Typen - Discriminator"""
    BUG = 'bug', '🐛 Bug'
    FEATURE = 'feature', '✨ Feature'
    TASK = 'task', '📋 Task'
    ENHANCEMENT = 'enhancement', '🔧 Enhancement'
    REFACTOR = 'refactor', '♻️ Refactor'


class WorkItemStatus(models.TextChoices):
    """Universeller Status für alle Work Items"""
    BACKLOG = 'backlog', '📦 Backlog'
    TODO = 'todo', '📝 To Do'
    IN_PROGRESS = 'in_progress', '🚧 In Progress'
    IN_REVIEW = 'in_review', '👀 In Review'
    TESTING = 'testing', '🧪 Testing'
    DONE = 'done', '✅ Done'
    BLOCKED = 'blocked', '🚫 Blocked'
    CANCELLED = 'cancelled', '❌ Cancelled'


class WorkItemPriority(models.TextChoices):
    """Prioritäten"""
    CRITICAL = 'critical', '🔥 Critical'
    HIGH = 'high', '🔴 High'
    MEDIUM = 'medium', '🟡 Medium'
    LOW = 'low', '🔵 Low'


class LLMTier(models.TextChoices):
    """LLM Tier für Autorouting"""
    TIER_1 = 'tier_1', '💚 Tier 1 (Günstig)'
    TIER_2 = 'tier_2', '💛 Tier 2 (Standard)'
    TIER_3 = 'tier_3', '🔴 Tier 3 (Premium)'


class Complexity(models.TextChoices):
    """Komplexitätsstufen"""
    AUTO = 'auto', '🤖 Auto-Detect'
    LOW = 'low', '🟢 Low'
    MEDIUM = 'medium', '🟡 Medium'
    HIGH = 'high', '🔴 High'


# =============================================================================
# WORK ITEM - HAUPTMODEL
# =============================================================================

class WorkItem(models.Model):
    """
    Unified Work Item - Basis für Bug, Feature, Task
    
    Ersetzt:
    - TestRequirement (models_testing.py) - war überladen
    - ComponentRegistry Missbrauch für Features (models_registry.py)
    
    Vorteile:
    - Single Source of Truth
    - Konsistentes LLM-Routing (MCP Autorouting)
    - Einheitliches Kanban für alle Types
    - Klare Separation of Concerns
    """
    
    # === IDENTITY ===
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    identifier = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Human-readable ID: BUG-0001, FEAT-0042, TASK-0123"
    )
    
    # === TYPE (Discriminator) ===
    item_type = models.CharField(
        max_length=20,
        choices=WorkItemType.choices,
        default=WorkItemType.TASK,
        db_index=True,
        help_text="Art des Work Items"
    )
    
    # === CORE FIELDS ===
    title = models.CharField(
        max_length=300,
        help_text="Titel/Zusammenfassung"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Detaillierte Beschreibung"
    )
    
    # === CLASSIFICATION ===
    status = models.CharField(
        max_length=20,
        choices=WorkItemStatus.choices,
        default=WorkItemStatus.BACKLOG,
        db_index=True
    )
    
    priority = models.CharField(
        max_length=20,
        choices=WorkItemPriority.choices,
        default=WorkItemPriority.MEDIUM,
        db_index=True
    )
    
    # === DOMAIN (Cross-Domain Support) ===
    domain = models.ForeignKey(
        'bfagent.DomainArt',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_items',
        help_text="Zugehörige Domain (writing_hub, control_center, etc.)"
    )
    
    # === OWNERSHIP ===
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_work_items'
    )
    
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_work_items'
    )
    
    # === LLM ROUTING (MCP Autorouting) ===
    complexity = models.CharField(
        max_length=20,
        choices=Complexity.choices,
        default=Complexity.AUTO,
        help_text="Komplexität (auto = automatische Erkennung)"
    )
    
    llm_tier = models.CharField(
        max_length=20,
        choices=LLMTier.choices,
        blank=True,
        help_text="Empfohlener/zugewiesener LLM Tier"
    )
    
    llm_override = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_item_overrides',
        help_text="Manueller LLM Override"
    )
    
    # === TAGS & METADATA ===
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags für Filterung (Liste von Strings)"
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Zusätzliche Metadaten (flexibles Schema)"
    )
    
    # === TIMESTAMPS ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # === HIERARCHIE (Parent/Child) ===
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        help_text="Parent Work Item (z.B. Feature → Tasks)"
    )
    
    # === LEGACY REFERENCE (für Migration) ===
    legacy_requirement_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID des ursprünglichen TestRequirement (für Migration)"
    )
    
    class Meta:
        db_table = 'work_items'
        verbose_name = 'Work Item'
        verbose_name_plural = 'Work Items'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['item_type', 'status']),
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.identifier or self.id} - {self.title[:50]}"
    
    def save(self, *args, **kwargs):
        # Auto-generate identifier if not set
        if not self.identifier:
            self.identifier = self._generate_identifier()
        
        # Auto-detect complexity and LLM tier
        if self.complexity == Complexity.AUTO and not self.llm_tier:
            self._auto_classify()
        
        # Set started_at when moving to in_progress
        if self.status == WorkItemStatus.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
        
        # Set completed_at when done
        if self.status == WorkItemStatus.DONE and not self.completed_at:
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def _generate_identifier(self) -> str:
        """Generiert human-readable Identifier"""
        prefix_map = {
            WorkItemType.BUG: 'BUG',
            WorkItemType.FEATURE: 'FEAT',
            WorkItemType.TASK: 'TASK',
            WorkItemType.ENHANCEMENT: 'ENH',
            WorkItemType.REFACTOR: 'REF',
        }
        prefix = prefix_map.get(self.item_type, 'ITEM')
        
        # Zähle existierende Items dieses Typs
        count = WorkItem.objects.filter(item_type=self.item_type).count() + 1
        return f"{prefix}-{count:04d}"
    
    def _auto_classify(self):
        """MCP Autorouting: Klassifiziert nach Komplexität"""
        try:
            # Versuche MCP TaskClassifier zu nutzen
            from bfagent_mcp.tools.autocoding import task_classifier
            
            text = f"{self.title} {self.description}"
            result = task_classifier.classify(text)
            
            # Map complexity to tier
            tier_map = {
                'low': LLMTier.TIER_1,
                'medium': LLMTier.TIER_2,
                'high': LLMTier.TIER_3,
            }
            complexity_lower = result.complexity.lower() if hasattr(result, 'complexity') else 'medium'
            self.llm_tier = tier_map.get(complexity_lower, LLMTier.TIER_2)
            
            logger.info(f"[WorkItem] Auto-classified {self.identifier}: {self.llm_tier}")
            
        except ImportError:
            # Fallback: Einfache Heuristik
            self._fallback_classify()
        except Exception as e:
            logger.warning(f"[WorkItem] Auto-classify failed: {e}")
            self._fallback_classify()
    
    def _fallback_classify(self):
        """Fallback-Klassifikation ohne MCP"""
        text = f"{self.title} {self.description}".lower()
        
        # High complexity indicators
        high_keywords = ['migration', 'refactor', 'architecture', 'security', 
                        'authentication', 'database', 'performance', 'api']
        # Low complexity indicators
        low_keywords = ['typo', 'text', 'label', 'css', 'color', 'button', 
                       'style', 'icon', 'spacing']
        
        high_count = sum(1 for kw in high_keywords if kw in text)
        low_count = sum(1 for kw in low_keywords if kw in text)
        
        if high_count >= 2 or self.item_type == WorkItemType.REFACTOR:
            self.llm_tier = LLMTier.TIER_3
        elif low_count >= 2:
            self.llm_tier = LLMTier.TIER_1
        else:
            self.llm_tier = LLMTier.TIER_2
    
    def get_effective_complexity(self) -> str:
        """Gibt effektive Complexity zurück"""
        if self.complexity != Complexity.AUTO:
            return self.complexity
        
        # Ableiten aus llm_tier
        tier_to_complexity = {
            LLMTier.TIER_1: Complexity.LOW,
            LLMTier.TIER_2: Complexity.MEDIUM,
            LLMTier.TIER_3: Complexity.HIGH,
        }
        return tier_to_complexity.get(self.llm_tier, Complexity.MEDIUM)
    
    def get_llm(self):
        """Gibt das zu verwendende LLM zurück"""
        # Expliziter Override
        if self.llm_override:
            return self.llm_override
        
        # Auto-Mapping basierend auf Tier
        from apps.bfagent.models_main import Llms
        
        tier_models = {
            LLMTier.TIER_1: ['gpt-4o-mini', 'claude-3-haiku', 'gpt-3.5-turbo'],
            LLMTier.TIER_2: ['claude-3-5-sonnet', 'gpt-4o', 'claude-3-sonnet'],
            LLMTier.TIER_3: ['claude-opus-4', 'claude-3-opus', 'gpt-4-turbo'],
        }
        
        preferred = tier_models.get(self.llm_tier, tier_models[LLMTier.TIER_2])
        
        for model_name in preferred:
            llm = Llms.objects.filter(name__icontains=model_name, is_active=True).first()
            if llm:
                return llm
        
        return Llms.objects.filter(is_active=True).first()
    
    @property
    def is_bug(self) -> bool:
        return self.item_type == WorkItemType.BUG
    
    @property
    def is_feature(self) -> bool:
        return self.item_type == WorkItemType.FEATURE
    
    @property
    def is_task(self) -> bool:
        return self.item_type == WorkItemType.TASK
    
    @property
    def duration_days(self) -> int | None:
        """Berechnet Dauer in Tagen"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).days
        return None


# =============================================================================
# BUG DETAILS (1:1 zu WorkItem)
# =============================================================================

class BugDetails(models.Model):
    """
    Bug-spezifische Details.
    Nur für WorkItems mit item_type='bug'.
    """
    
    work_item = models.OneToOneField(
        WorkItem,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='bug_details'
    )
    
    # Bug-spezifische Felder
    url = models.URLField(
        max_length=500,
        blank=True,
        help_text="URL wo der Bug gefunden wurde"
    )
    
    actual_behavior = models.TextField(
        blank=True,
        help_text="Was passiert aktuell (Ist-Zustand)"
    )
    
    expected_behavior = models.TextField(
        blank=True,
        help_text="Was sollte passieren (Soll-Zustand)"
    )
    
    steps_to_reproduce = models.TextField(
        blank=True,
        help_text="Schritte zur Reproduktion"
    )
    
    # Acceptance Criteria (Gherkin Format)
    acceptance_criteria = models.JSONField(
        default=list,
        blank=True,
        help_text="Acceptance Criteria im Gherkin Format"
    )
    
    # Browser/Environment
    environment = models.JSONField(
        default=dict,
        blank=True,
        help_text="Browser, OS, etc."
    )
    
    # Screenshots
    screenshot = models.ImageField(
        upload_to='work_items/bugs/%Y/%m/',
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'work_item_bug_details'
        verbose_name = 'Bug Details'
        verbose_name_plural = 'Bug Details'
    
    def __str__(self):
        return f"Bug Details: {self.work_item.identifier}"


# =============================================================================
# FEATURE DETAILS (1:1 zu WorkItem)
# =============================================================================

class FeatureDetails(models.Model):
    """
    Feature-spezifische Details.
    Nur für WorkItems mit item_type='feature'.
    """
    
    work_item = models.OneToOneField(
        WorkItem,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='feature_details'
    )
    
    # Feature-spezifische Felder
    user_story = models.TextField(
        blank=True,
        help_text="User Story: Als [Rolle] möchte ich [Funktion] damit [Nutzen]"
    )
    
    specification = models.TextField(
        blank=True,
        help_text="Technische Spezifikation"
    )
    
    # Code-Referenz
    module_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Python Module Path (z.B. apps.writing_hub.handlers)"
    )
    
    file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relativer Dateipfad"
    )
    
    # Acceptance Criteria
    acceptance_criteria = models.JSONField(
        default=list,
        blank=True,
        help_text="Acceptance Criteria"
    )
    
    # Design Docs (Relation zu FeatureDocument bleibt bestehen)
    
    class Meta:
        db_table = 'work_item_feature_details'
        verbose_name = 'Feature Details'
        verbose_name_plural = 'Feature Details'
    
    def __str__(self):
        return f"Feature Details: {self.work_item.identifier}"


# =============================================================================
# TASK DETAILS (1:1 zu WorkItem)
# =============================================================================

class TaskDetails(models.Model):
    """
    Task-spezifische Details.
    Nur für WorkItems mit item_type='task'.
    """
    
    work_item = models.OneToOneField(
        WorkItem,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='task_details'
    )
    
    # Zeit-Tracking
    estimated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Geschätzte Stunden"
    )
    
    actual_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Tatsächliche Stunden"
    )
    
    # Execution
    execution_log = models.TextField(
        blank=True,
        help_text="Ausführungs-Log"
    )
    
    # Checklist
    checklist = models.JSONField(
        default=list,
        blank=True,
        help_text="Task Checklist: [{text: str, done: bool}]"
    )
    
    class Meta:
        db_table = 'work_item_task_details'
        verbose_name = 'Task Details'
        verbose_name_plural = 'Task Details'
    
    def __str__(self):
        return f"Task Details: {self.work_item.identifier}"
    
    @property
    def checklist_progress(self) -> tuple[int, int]:
        """Returns (done, total) für Checklist"""
        if not self.checklist:
            return (0, 0)
        done = sum(1 for item in self.checklist if item.get('done', False))
        return (done, len(self.checklist))


# =============================================================================
# LLM ASSIGNMENT (für alle Work Items)
# =============================================================================

class WorkItemLLMAssignment(models.Model):
    """
    Unified LLM Assignment für ALLE Work Item Types.
    
    Ersetzt: BugLLMAssignment (nur für Bugs)
    Neu: Für Bugs, Features, Tasks gleichermaßen
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', '⏳ Pending'
        IN_PROGRESS = 'in_progress', '🔄 In Progress'
        RESOLVED = 'resolved', '✅ Resolved'
        ESCALATED = 'escalated', '⬆️ Escalated'
        FAILED = 'failed', '❌ Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    work_item = models.ForeignKey(
        WorkItem,
        on_delete=models.CASCADE,
        related_name='llm_assignments'
    )
    
    # Tier-Tracking
    initial_tier = models.CharField(
        max_length=20,
        choices=LLMTier.choices,
        default=LLMTier.TIER_1,
        help_text="Ursprünglich zugewiesener Tier"
    )
    
    current_tier = models.CharField(
        max_length=20,
        choices=LLMTier.choices,
        default=LLMTier.TIER_1,
        help_text="Aktueller Tier (nach Eskalationen)"
    )
    
    complexity_score = models.IntegerField(
        default=0,
        help_text="Berechneter Komplexitäts-Score (0-10)"
    )
    
    # LLM-Tracking
    llm_used = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_item_assignments'
    )
    
    attempts = models.IntegerField(default=0)
    escalation_count = models.IntegerField(default=0)
    
    # Kosten-Tracking
    tokens_input = models.IntegerField(default=0)
    tokens_output = models.IntegerField(default=0)
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
        help_text="Kosten in USD"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    resolution_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Konfidenz der Lösung (0-1)"
    )
    
    resolution_notes = models.TextField(
        blank=True,
        help_text="Notizen zur Lösung"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Attempt History
    attempt_history = models.JSONField(
        default=list,
        help_text="Historie aller Versuche"
    )
    
    class Meta:
        db_table = 'work_item_llm_assignments'
        verbose_name = 'LLM Assignment'
        verbose_name_plural = 'LLM Assignments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'current_tier']),
            models.Index(fields=['work_item', 'status']),
        ]
    
    def __str__(self):
        return f"{self.work_item.identifier} - {self.current_tier} ({self.status})"
    
    @property
    def total_tokens(self) -> int:
        return self.tokens_input + self.tokens_output
    
    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.resolved_at:
            return (self.resolved_at - self.started_at).total_seconds()
        return None
    
    def escalate(self, error_reason: str = None) -> bool:
        """Eskaliert zum nächsten Tier"""
        tier_order = [LLMTier.TIER_1, LLMTier.TIER_2, LLMTier.TIER_3]
        
        try:
            current_index = tier_order.index(self.current_tier)
        except ValueError:
            return False
        
        if current_index < len(tier_order) - 1:
            old_tier = self.current_tier
            self.current_tier = tier_order[current_index + 1]
            self.escalation_count += 1
            self.status = self.Status.ESCALATED
            
            self.attempt_history.append({
                'attempt': self.attempts,
                'tier': old_tier,
                'escalated_to': self.current_tier,
                'reason': error_reason,
                'timestamp': timezone.now().isoformat()
            })
            self.save()
            
            logger.info(f"[LLMAssignment] {self.work_item.identifier} escalated: {old_tier} → {self.current_tier}")
            return True
        
        return False
    
    def record_attempt(self, llm_name: str, tokens: int, cost: float,
                      success: bool, error: str = None):
        """Zeichnet einen LLM-Versuch auf"""
        self.attempts += 1
        self.tokens_input += tokens
        self.cost_usd += cost
        
        self.attempt_history.append({
            'attempt': self.attempts,
            'tier': self.current_tier,
            'llm': llm_name,
            'tokens': tokens,
            'cost': float(cost),
            'success': success,
            'error': error,
            'timestamp': timezone.now().isoformat()
        })
        
        if success:
            self.status = self.Status.RESOLVED
            self.resolved_at = timezone.now()
        
        self.save()
    
    def calculate_savings(self) -> float:
        """Berechnet Ersparnis vs. immer Tier 3"""
        tier_3_cost_per_1m = 30.0  # $30/1M tokens (GPT-4)
        tier_3_would_cost = (self.total_tokens / 1_000_000) * tier_3_cost_per_1m
        return float(tier_3_would_cost - float(self.cost_usd))


# =============================================================================
# WORK ITEM COMMENT/FEEDBACK
# =============================================================================

class WorkItemComment(models.Model):
    """
    Kommentare/Feedback zu Work Items.
    Ersetzt RequirementFeedback und TestCaseFeedback.
    """
    
    class CommentType(models.TextChoices):
        COMMENT = 'comment', '💬 Kommentar'
        PROGRESS = 'progress', '📈 Fortschritt'
        BLOCKER = 'blocker', '🚫 Blocker'
        QUESTION = 'question', '❓ Frage'
        SOLUTION = 'solution', '💡 Lösung'
        REVIEW = 'review', '👀 Review'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    work_item = models.ForeignKey(
        WorkItem,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_item_comments'
    )
    
    comment_type = models.CharField(
        max_length=20,
        choices=CommentType.choices,
        default=CommentType.COMMENT
    )
    
    content = models.TextField()
    
    is_from_cascade = models.BooleanField(
        default=False,
        help_text="True wenn von Cascade AI generiert"
    )
    
    screenshot = models.ImageField(
        upload_to='work_items/comments/%Y/%m/',
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'work_item_comments'
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'
        ordering = ['-created_at']
    
    def __str__(self):
        author_name = self.author.username if self.author else 'Cascade'
        return f"{self.comment_type}: {author_name} @ {self.created_at:%d.%m.%Y}"
