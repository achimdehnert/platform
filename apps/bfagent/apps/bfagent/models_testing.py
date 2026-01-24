"""
Testing & Requirements Management System

This module provides comprehensive test management with bidirectional traceability
between requirements and test cases, supporting Robot Framework, pytest, and Playwright.

Key Features:
- Requirements capture with Gherkin format
- Test case auto-generation from acceptance criteria
- Requirement-to-test traceability
- Test execution tracking
- Coverage reporting
- Manual test session recording
"""

from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
import json

User = get_user_model()


# ============================================================================
# INITIATIVES (EPICS) - Konzepte mit mehreren Requirements
# ============================================================================

class Initiative(models.Model):
    """
    Initiative/Epic: Ein übergeordnetes Konzept das mehrere Requirements gruppiert.
    
    Standard-Workflow:
    1. CREATED → Initiative anlegen mit Beschreibung
    2. ANALYSIS → Ist-Stand analysieren, Code durchsuchen, Erkenntnisse dokumentieren
    3. CONCEPT → Lösungskonzept ausarbeiten, Requirements ableiten
    4. PLANNING → Tasks priorisieren, Aufwand schätzen
    5. IN_PROGRESS → Requirements einzeln abarbeiten
    6. REVIEW → Ergebnisse prüfen, Dokumentation vervollständigen
    7. COMPLETED → Abschluss, Lessons Learned dokumentieren
    
    MCP Tools:
    - bfagent_start_initiative: Startet Workflow, lädt Kontext
    - bfagent_log_initiative_activity: Dokumentiert jeden Schritt
    - bfagent_update_initiative: Aktualisiert Status/Analyse/Konzept
    - bfagent_create_initiative: Erstellt mit optionalen Tasks
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    title = models.CharField(
        max_length=200,
        help_text="Titel der Initiative/des Konzepts"
    )
    
    description = models.TextField(
        help_text="Ausführliche Beschreibung des Konzepts"
    )
    
    # Analysis & Concept
    analysis = models.TextField(
        blank=True,
        help_text="Analyse-Ergebnisse und Erkenntnisse"
    )
    
    concept = models.TextField(
        blank=True,
        help_text="Ausgearbeitetes Konzept/Lösung"
    )
    
    # Domain & Categorization
    domain = models.CharField(
        max_length=50,
        choices=[
            ('writing_hub', 'Writing Hub'),
            ('cad_hub', 'CAD Hub'),
            ('mcp_hub', 'MCP Hub'),
            ('medtrans', 'MedTrans'),
            ('control_center', 'Control Center'),
            ('genagent', 'GenAgent'),
            ('core', 'Core/Shared'),
            ('multi', 'Multi-Domain'),
        ],
        default='core',
        help_text="Hauptbereich der Initiative"
    )
    
    # Priority & Status
    priority = models.CharField(
        max_length=20,
        choices=[
            ('critical', 'Critical'),
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ],
        default='medium'
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('analysis', 'In Analyse'),
            ('concept', 'Konzept-Phase'),
            ('planning', 'Task-Planung'),
            ('in_progress', 'In Bearbeitung'),
            ('review', 'Review'),
            ('completed', 'Abgeschlossen'),
            ('on_hold', 'Pausiert'),
            ('cancelled', 'Abgebrochen'),
        ],
        default='analysis'
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiatives_created'
    )
    
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags für Filterung"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # =========================================================================
    # WORKFLOW & DOCUMENTATION
    # =========================================================================
    
    # Workflow Phase Details
    workflow_phase = models.CharField(
        max_length=20,
        choices=[
            ('kickoff', 'Kickoff'),
            ('research', 'Recherche'),
            ('analysis', 'Analyse'),
            ('design', 'Design'),
            ('implementation', 'Implementierung'),
            ('testing', 'Testing'),
            ('documentation', 'Dokumentation'),
            ('review', 'Review'),
            ('deployment', 'Deployment'),
        ],
        default='kickoff',
        help_text="Aktuelle Workflow-Phase"
    )
    
    # Documentation
    lessons_learned = models.TextField(
        blank=True,
        help_text="Was wurde gelernt? Best Practices, Probleme, Lösungen"
    )
    
    next_steps = models.TextField(
        blank=True,
        help_text="Nächste geplante Schritte"
    )
    
    blockers = models.TextField(
        blank=True,
        help_text="Aktuelle Blocker/Hindernisse"
    )
    
    # References
    related_files = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste relevanter Dateipfade"
    )
    
    related_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="Externe Links, Docs, Issues"
    )
    
    # Progress tracking
    estimated_hours = models.IntegerField(
        null=True,
        blank=True,
        help_text="Geschätzte Stunden für die gesamte Initiative"
    )
    
    class Meta:
        db_table = 'bfagent_initiative'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['domain']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    @property
    def requirements_count(self):
        """Anzahl der verknüpften Requirements"""
        return self.requirements.count()
    
    @property
    def completed_requirements(self):
        """Anzahl der abgeschlossenen Requirements"""
        return self.requirements.filter(status__in=['done', 'completed']).count()
    
    @property
    def progress_percentage(self):
        """Fortschritt in Prozent"""
        total = self.requirements_count
        if total == 0:
            return 0
        return int((self.completed_requirements / total) * 100)
    
    def log_activity(self, action: str, details: str = "", actor: str = "system", 
                     mcp_tool: str = "", tokens_used: int = 0, cost: float = 0):
        """Log an activity for this initiative"""
        return InitiativeActivity.objects.create(
            initiative=self,
            action=action,
            details=details,
            actor=actor,
            mcp_tool_used=mcp_tool,
            tokens_used=tokens_used,
            estimated_cost=cost
        )
    
    def transition_status(self, new_status: str, actor: str = "system", reason: str = ""):
        """Transition to a new status with logging"""
        old_status = self.status
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        
        self.log_activity(
            action=f"status_change",
            details=f"{old_status} → {new_status}" + (f": {reason}" if reason else ""),
            actor=actor
        )
        return self


class InitiativeActivity(models.Model):
    """
    Activity log for initiatives - tracks all actions, MCP tool usage, and costs.
    
    Provides transparency into:
    - Workflow steps (analysis, concept, planning)
    - MCP tool invocations
    - LLM token usage and costs
    - Status transitions
    """
    
    class ActionType(models.TextChoices):
        CREATED = 'created', 'Initiative erstellt'
        STATUS_CHANGE = 'status_change', 'Status geändert'
        ANALYSIS_STARTED = 'analysis_started', 'Analyse gestartet'
        ANALYSIS_COMPLETED = 'analysis_completed', 'Analyse abgeschlossen'
        CONCEPT_ADDED = 'concept_added', 'Konzept hinzugefügt'
        REQUIREMENT_ADDED = 'requirement_added', 'Requirement hinzugefügt'
        REQUIREMENT_COMPLETED = 'requirement_completed', 'Requirement abgeschlossen'
        MCP_TOOL_CALLED = 'mcp_tool_called', 'MCP Tool aufgerufen'
        LLM_INVOKED = 'llm_invoked', 'LLM aufgerufen'
        COMMENT = 'comment', 'Kommentar'
        ERROR = 'error', 'Fehler'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    initiative = models.ForeignKey(
        Initiative,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    
    # Action details
    action = models.CharField(max_length=50, choices=ActionType.choices)
    details = models.TextField(blank=True)
    actor = models.CharField(max_length=100, default='system', help_text="cascade, user, system")
    
    # MCP/LLM tracking
    mcp_tool_used = models.CharField(max_length=100, blank=True)
    llm_model = models.CharField(max_length=100, blank=True)
    tokens_used = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    duration_ms = models.IntegerField(default=0, help_text="Duration in milliseconds")
    
    class Meta:
        db_table = 'bfagent_initiative_activity'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['initiative', '-created_at']),
            models.Index(fields=['action']),
            models.Index(fields=['mcp_tool_used']),
        ]
    
    def __str__(self):
        return f"{self.initiative.title[:30]} - {self.get_action_display()}"


# ============================================================================
# MCP USAGE TRACKING
# ============================================================================

class MCPUsageLog(models.Model):
    """
    Tracks all MCP tool invocations for transparency and analytics.
    
    Provides visibility into:
    - Which tools are used most frequently
    - Average execution times per tool
    - Token consumption when LLMs are involved
    - Cost tracking per tool/session/user
    - Error rates and patterns
    
    Can be linked to Initiative/Requirement for context.
    """
    
    class Status(models.TextChoices):
        SUCCESS = 'success', 'Erfolgreich'
        ERROR = 'error', 'Fehler'
        TIMEOUT = 'timeout', 'Timeout'
        CANCELLED = 'cancelled', 'Abgebrochen'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tool identification
    tool_name = models.CharField(max_length=100, db_index=True)
    tool_category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Category: domain, handler, refactor, initiative, task, rules"
    )
    
    # Invocation details
    arguments = models.JSONField(default=dict, blank=True)
    result_summary = models.TextField(blank=True, help_text="First 500 chars of result")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS)
    error_message = models.TextField(blank=True)
    
    # Context links (optional)
    initiative = models.ForeignKey(
        Initiative,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mcp_usage_logs'
    )
    requirement = models.ForeignKey(
        'TestRequirement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mcp_usage_logs'
    )
    
    # User/Session tracking
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mcp_usage_logs'
    )
    session_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # LLM usage (if tool invoked LLM)
    llm_model = models.CharField(max_length=100, blank=True)
    tokens_input = models.IntegerField(default=0)
    tokens_output = models.IntegerField(default=0)
    tokens_total = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    duration_ms = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'bfagent_mcp_usage_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tool_name', '-created_at']),
            models.Index(fields=['tool_category']),
            models.Index(fields=['status']),
            models.Index(fields=['session_id']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'MCP Usage Log'
        verbose_name_plural = 'MCP Usage Logs'
    
    def __str__(self):
        return f"{self.tool_name} ({self.status}) - {self.created_at:%Y-%m-%d %H:%M}"
    
    @classmethod
    def log_call(cls, tool_name: str, arguments: dict = None, **kwargs):
        """Convenience method to log a tool call."""
        # Determine category from tool name
        category = ''
        if tool_name.startswith('bfagent_'):
            parts = tool_name.replace('bfagent_', '').split('_')
            if parts[0] in ['list', 'get', 'search']:
                category = 'query'
            elif parts[0] in ['create', 'update', 'delete']:
                category = 'mutation'
            elif 'initiative' in tool_name:
                category = 'initiative'
            elif 'requirement' in tool_name or 'task' in tool_name:
                category = 'task'
            elif 'domain' in tool_name or 'handler' in tool_name:
                category = 'domain'
            elif 'refactor' in tool_name:
                category = 'refactor'
            elif 'rule' in tool_name:
                category = 'rules'
        
        return cls.objects.create(
            tool_name=tool_name,
            tool_category=category,
            arguments=arguments or {},
            **kwargs
        )
    
    @classmethod
    def get_stats(cls, days: int = 7):
        """Get usage statistics for the last N days."""
        from django.db.models import Count, Avg, Sum
        from django.utils import timezone
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        qs = cls.objects.filter(created_at__gte=since)
        
        return {
            'total_calls': qs.count(),
            'success_rate': qs.filter(status=cls.Status.SUCCESS).count() / max(qs.count(), 1) * 100,
            'avg_duration_ms': qs.aggregate(avg=Avg('duration_ms'))['avg'] or 0,
            'total_tokens': qs.aggregate(total=Sum('tokens_total'))['total'] or 0,
            'total_cost': qs.aggregate(total=Sum('estimated_cost'))['total'] or 0,
            'by_tool': list(qs.values('tool_name').annotate(
                count=Count('id'),
                avg_ms=Avg('duration_ms')
            ).order_by('-count')[:10]),
            'by_category': list(qs.values('tool_category').annotate(
                count=Count('id')
            ).order_by('-count')),
        }


# ============================================================================
# REQUIREMENTS & ACCEPTANCE CRITERIA
# ============================================================================

class TestRequirement(models.Model):
    """
    Test requirements with acceptance criteria in Gherkin format
    
    Can be linked to features, user stories, or standalone requirements.
    Supports structured acceptance criteria that can auto-generate test code.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(
        max_length=200,
        help_text="Requirement name/title"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description"
    )
    
    # Categorization
    category = models.CharField(
        max_length=50,
        choices=[
            ('feature', 'Feature Requirement'),
            ('bug_fix', 'Bug Fix'),
            ('enhancement', 'Enhancement'),
            ('refactor', 'Refactoring'),
            ('performance', 'Performance'),
            ('security', 'Security'),
        ],
        default='feature'
    )
    
    # Priority & Status
    priority = models.CharField(
        max_length=20,
        choices=[
            ('critical', 'Critical - Must Test'),
            ('high', 'High - Should Test'),
            ('medium', 'Medium - Nice to Test'),
            ('low', 'Low - Optional')
        ],
        default='medium'
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('ready', 'Ready for Testing'),
            ('in_progress', 'Testing in Progress'),
            ('done', 'Done'),
            ('completed', 'Testing Completed'),
            ('blocked', 'Blocked'),
            ('obsolete', 'Obsolete/Redundant'),
            ('archived', 'Archived'),
        ],
        default='draft'
    )
    
    # Acceptance Criteria (Gherkin Format)
    acceptance_criteria = models.JSONField(
        default=list,
        help_text="""
        List of acceptance criteria in Gherkin format.
        Example: [{
            "id": "ac_1",
            "scenario": "User can add feedback",
            "given": "User is logged in and has a chapter",
            "when": "User clicks add comment button",
            "then": "Comment form should appear",
            "test_type": "ui",
            "priority": "high"
        }]
        """
    )
    
    # UI Testing Requirements
    ui_requirements = models.JSONField(
        default=dict,
        help_text="""
        UI-specific requirements. Example: {
            "elements_to_test": ["buttons", "forms", "navigation"],
            "responsive": true,
            "accessibility": ["aria", "keyboard"],
            "constraints": "Button must be visible within 2 seconds"
        }
        """
    )
    
    # Test Coverage Target
    test_coverage_target = models.IntegerField(
        default=80,
        help_text="Target test coverage percentage"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='test_requirements_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Tags for filtering
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for filtering and categorization (list of strings)"
    )
    
    # Initiative (Parent Epic/Concept)
    initiative = models.ForeignKey(
        'Initiative',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requirements',
        help_text="Übergeordnete Initiative/Konzept"
    )
    
    # Dependency on another requirement
    depends_on = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocks',
        help_text="Dieses Requirement kann erst gestartet werden, wenn das verknüpfte erledigt ist"
    )
    
    # Cross-Domain Support (Quick Win)
    domain = models.CharField(
        max_length=50,
        choices=[
            ('writing_hub', 'Writing Hub'),
            ('cad_hub', 'CAD Hub'),
            ('mcp_hub', 'MCP Hub'),
            ('medtrans', 'MedTrans'),
            ('control_center', 'Control Center'),
            ('genagent', 'GenAgent'),
            ('core', 'Core/Shared'),
        ],
        default='core',
        help_text="Which domain/app does this requirement belong to?"
    )
    
    # Bug-specific fields
    url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL where the bug was found"
    )
    actual_behavior = models.TextField(
        blank=True,
        help_text="What actually happens (bug description)"
    )
    expected_behavior = models.TextField(
        blank=True,
        help_text="What should happen instead"
    )
    screenshot = models.ImageField(
        upload_to='bug_screenshots/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Screenshot des Bugs (Ctrl+V zum Einfügen)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes and comments"
    )
    
    # Complexity & LLM Selection (Auto + Override)
    complexity = models.CharField(
        max_length=20,
        choices=[
            ('auto', 'Auto (Heuristik)'),
            ('low', 'Low - Einfach'),
            ('medium', 'Medium - Moderat'),
            ('high', 'High - Komplex'),
        ],
        default='auto',
        help_text="Komplexität des Tasks (auto = automatische Erkennung)"
    )
    
    llm_override = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requirement_overrides',
        help_text="LLM-Override (leer = automatisch basierend auf Complexity)"
    )
    
    # === DOCUMENTATION INTEGRATION ===
    doc_status = models.CharField(
        max_length=20,
        choices=[
            ('not_checked', 'Nicht geprüft'),
            ('exists', 'Dokumentation vorhanden'),
            ('needs_update', 'Aktualisierung nötig'),
            ('needs_creation', 'Neu zu erstellen'),
            ('updated', 'Aktualisiert'),
            ('created', 'Erstellt'),
        ],
        default='not_checked',
        help_text="Status der zugehörigen Dokumentation"
    )
    
    doc_notes = models.TextField(
        blank=True,
        help_text="Welche Dokumentation muss erstellt/aktualisiert werden?"
    )
    
    doc_files = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste verknüpfter Dokumentations-Dateien (Pfade)"
    )
    
    doc_checked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Wann wurde die Dokumentation zuletzt geprüft?"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),
            models.Index(fields=['domain', 'status']),  # Cross-domain queries
        ]
    
    def __str__(self):
        return f"{self.name} ({self.priority})"
    
    @property
    def can_start(self):
        """Check if this requirement can be started (dependency resolved)."""
        if not self.depends_on:
            return True
        return self.depends_on.status in ['done', 'completed']
    
    @property
    def is_blocked_by_dependency(self):
        """Check if blocked by unfinished dependency."""
        if not self.depends_on:
            return False
        return self.depends_on.status not in ['done', 'completed']
    
    def get_total_criteria(self):
        """Count total acceptance criteria"""
        return len(self.acceptance_criteria)
    
    def get_criteria_with_tests(self):
        """Count criteria that have linked tests"""
        return RequirementTestLink.objects.filter(
            requirement=self,
            status__in=['implemented', 'passing', 'failing']
        ).count()
    
    def calculate_coverage(self):
        """Calculate test coverage percentage"""
        total = self.get_total_criteria()
        if total == 0:
            return 0.0
        
        tested = self.get_criteria_with_tests()
        return (tested / total) * 100
    
    def estimate_complexity(self) -> str:
        """
        Schätzt Komplexität basierend auf Heuristiken.
        Returns: 'low', 'medium', 'high'
        """
        score = 0
        
        # Kategorie-basiert
        if self.category in ['refactor', 'security', 'performance']:
            score += 2
        elif self.category == 'feature':
            score += 1
        
        # Keywords in Beschreibung
        complex_keywords = ['migration', 'refactor', 'database', 'architecture', 
                          'api', 'authentication', 'permission', 'model']
        simple_keywords = ['typo', 'text', 'label', 'css', 'color', 'button', 
                          'style', 'spacing', 'icon']
        
        desc = (self.description or '').lower() + ' ' + (self.name or '').lower()
        score += sum(2 for kw in complex_keywords if kw in desc)
        score -= sum(1 for kw in simple_keywords if kw in desc)
        
        # Acceptance Criteria Anzahl
        criteria_count = len(self.acceptance_criteria) if self.acceptance_criteria else 0
        if criteria_count >= 4:
            score += 2
        elif criteria_count >= 2:
            score += 1
        
        # Domain-basiert
        if self.domain in ['core', 'auth']:
            score += 2
        elif self.domain in ['control_center', 'genagent']:
            score += 1
        
        # Beschreibungslänge
        if len(self.description or '') > 500:
            score += 1
        
        # Result
        if score <= 1:
            return 'low'
        elif score <= 4:
            return 'medium'
        return 'high'
    
    def get_effective_complexity(self) -> str:
        """Gibt effektive Complexity zurück (explizit oder auto)"""
        if self.complexity and self.complexity != 'auto':
            return self.complexity
        return self.estimate_complexity()
    
    def get_llm(self):
        """
        Gibt das zu verwendende LLM zurück.
        Priorität: 1) Expliziter Override, 2) Auto basierend auf Complexity
        """
        from apps.bfagent.models_main import Llms
        
        # Expliziter Override
        if self.llm_override:
            return self.llm_override
        
        # Auto-Mapping basierend auf Complexity
        complexity = self.get_effective_complexity()
        
        llm_mapping = {
            'low': ['gpt-4o-mini', 'claude-3-haiku', 'gpt-3.5-turbo'],
            'medium': ['claude-3-5-sonnet', 'gpt-4o', 'claude-3-sonnet'],
            'high': ['claude-opus-4', 'claude-3-opus', 'gpt-4-turbo'],
        }
        
        preferred_models = llm_mapping.get(complexity, llm_mapping['medium'])
        
        # Versuche Models in Reihenfolge zu finden
        for model_name in preferred_models:
            llm = Llms.objects.filter(name__icontains=model_name, is_active=True).first()
            if llm:
                return llm
        
        # Fallback: Irgendein aktives LLM
        return Llms.objects.filter(is_active=True).first()


# ============================================================================
# TEST CASE MANAGEMENT
# ============================================================================

class TestCase(models.Model):
    """
    Individual test case definition
    
    Can be auto-generated from requirements or manually created.
    Supports multiple test frameworks (Robot, pytest, Playwright).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    test_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique test identifier (e.g., test_user_login)"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Test Framework
    framework = models.CharField(
        max_length=50,
        choices=[
            ('robot', 'Robot Framework'),
            ('pytest', 'Pytest'),
            ('playwright', 'Playwright'),
            ('manual', 'Manual Test'),
        ],
        default='robot'
    )
    
    # Test Type
    test_type = models.CharField(
        max_length=50,
        choices=[
            ('unit', 'Unit Test'),
            ('integration', 'Integration Test'),
            ('ui', 'UI Test'),
            ('api', 'API Test'),
            ('e2e', 'End-to-End Test'),
            ('performance', 'Performance Test'),
            ('security', 'Security Test'),
        ],
        default='integration'
    )
    
    # Test Code
    test_code = models.TextField(
        help_text="Generated or manually written test code"
    )
    
    file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relative path to test file in project"
    )
    
    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="List of tags"
    )
    
    priority = models.IntegerField(
        default=3,
        help_text="Test priority (1=highest, 5=lowest)"
    )
    
    estimated_duration = models.IntegerField(
        default=30,
        help_text="Estimated execution time in seconds"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('disabled', 'Disabled'),
            ('deprecated', 'Deprecated'),
        ],
        default='active'
    )
    
    # Auto-generation tracking
    is_auto_generated = models.BooleanField(
        default=False,
        help_text="Was this test auto-generated from requirements?"
    )
    
    generation_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadata about auto-generation process"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['priority', 'name']
        indexes = [
            models.Index(fields=['framework', 'test_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.test_id} ({self.framework})"


# ============================================================================
# REQUIREMENT-TEST TRACEABILITY
# ============================================================================

class RequirementTestLink(models.Model):
    """
    Bidirectional link between requirements and test cases
    
    Provides traceability from acceptance criteria to tests
    and back from test results to requirements.
    """
    
    requirement = models.ForeignKey(
        TestRequirement,
        on_delete=models.CASCADE,
        related_name='test_links'
    )
    
    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name='requirement_links'
    )
    
    # Specific acceptance criterion ID (from JSON)
    criterion_id = models.CharField(
        max_length=50,
        help_text="ID of specific acceptance criterion this test covers"
    )
    
    # Link type
    link_type = models.CharField(
        max_length=20,
        choices=[
            ('auto', 'Auto-Generated'),
            ('manual', 'Manually Linked'),
        ],
        default='auto'
    )
    
    # Current status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Test Pending'),
            ('implemented', 'Test Implemented'),
            ('passing', 'Test Passing'),
            ('failing', 'Test Failing'),
        ],
        default='pending'
    )
    
    # Last test execution info
    last_test_result = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('passed', 'Passed'),
            ('failed', 'Failed'),
            ('skipped', 'Skipped'),
            ('error', 'Error'),
        ]
    )
    
    last_executed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['requirement', 'criterion_id']
        indexes = [
            models.Index(fields=['requirement', 'status']),
            models.Index(fields=['test_case', 'last_test_result']),
        ]
    
    def __str__(self):
        return f"{self.requirement.name} -> {self.test_case.test_id}"


# ============================================================================
# TEST EXECUTION TRACKING
# ============================================================================

class BugFixPlan(models.Model):
    """
    Proposed fix plan for a bug (requires approval before execution)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Linked bug requirement
    requirement = models.ForeignKey(
        TestRequirement,
        on_delete=models.CASCADE,
        related_name='fix_plans'
    )
    
    # Fix details
    fix_type = models.CharField(
        max_length=100,
        help_text="Type of fix: create_chapter, fix_url, etc."
    )
    
    fix_description = models.TextField(
        help_text="Human-readable description of what will be done"
    )
    
    fix_actions = models.JSONField(
        default=dict,
        help_text="Detailed fix steps and parameters"
    )
    
    # Handler information
    handler_id = models.CharField(
        max_length=200,
        help_text="ID of handler that will execute this fix"
    )
    
    handler_code = models.TextField(
        blank=True,
        help_text="Generated handler code (if auto-generated)"
    )
    
    # Approval workflow
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('executing', 'Executing'),
            ('executed', 'Executed'),
            ('failed', 'Failed'),
            ('rolled_back', 'Rolled Back')
        ],
        default='pending'
    )
    
    # Users
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_fix_plans'
    )
    
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_fix_plans'
    )
    
    # Execution tracking
    execution_result = models.JSONField(
        default=dict,
        blank=True,
        help_text="Result of fix execution"
    )
    
    execution_log = models.TextField(
        blank=True,
        help_text="Detailed execution log"
    )
    
    # Rollback
    rollback_possible = models.BooleanField(
        default=False,
        help_text="Whether this fix can be rolled back"
    )
    
    rollback_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Data needed for rollback"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['requirement', 'status']),
        ]
    
    def __str__(self):
        return f"{self.fix_type} for {self.requirement.name} ({self.status})"


class TestExecution(models.Model):
    """
    Track individual test executions
    
    Records results from automated test runs and manual testing sessions.
    """
    
    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    
    # Execution metadata
    executed_at = models.DateTimeField(auto_now_add=True)
    executed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Result
    result = models.CharField(
        max_length=20,
        choices=[
            ('passed', 'Passed'),
            ('failed', 'Failed'),
            ('skipped', 'Skipped'),
            ('error', 'Error'),
        ]
    )
    
    duration = models.FloatField(
        help_text="Execution time in seconds"
    )
    
    # Error details
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)
    
    # Environment info
    environment = models.CharField(
        max_length=50,
        default='development'
    )
    
    git_commit = models.CharField(
        max_length=40,
        blank=True,
        help_text="Git commit hash when test was run"
    )
    
    # Output artifacts
    log_file_path = models.CharField(max_length=500, blank=True)
    screenshot_paths = models.JSONField(
        default=list,
        blank=True,
        help_text="List of screenshot file paths"
    )
    
    # Additional data
    execution_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional execution context"
    )
    
    class Meta:
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['test_case', 'result']),
            models.Index(fields=['executed_at']),
        ]
    
    def __str__(self):
        return f"{self.test_case.test_id} - {self.result} @ {self.executed_at}"


# ============================================================================
# MANUAL TEST SESSIONS
# ============================================================================

class TestSession(models.Model):
    """
    Manual test session with auto-capture
    
    Tracks manual testing activities with automatic screenshot capture,
    request logging, and bug reporting.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Session info
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    test_type = models.CharField(
        max_length=50,
        default='manual',
        choices=[
            ('manual', 'Manual Exploratory'),
            ('regression', 'Regression Testing'),
            ('smoke', 'Smoke Testing'),
            ('acceptance', 'Acceptance Testing'),
        ]
    )
    
    # Associated requirement
    requirement = models.ForeignKey(
        TestRequirement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_sessions'
    )
    
    # Session notes
    notes = models.TextField(blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('abandoned', 'Abandoned'),
        ],
        default='active'
    )
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Test Session {self.id} by {self.user.username}"
    
    @property
    def duration_seconds(self):
        """Calculate session duration"""
        if not self.ended_at:
            return (timezone.now() - self.started_at).total_seconds()
        return (self.ended_at - self.started_at).total_seconds()


class TestLog(models.Model):
    """Request/Response log during test session"""
    
    session = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    url = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    response_status = models.IntegerField(null=True)
    response_time = models.DateTimeField(null=True)
    
    request_data = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.method} {self.url} - {self.response_status}"


class TestScreenshot(models.Model):
    """Captured screenshot during test session"""
    
    session = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name='screenshots'
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    page_url = models.CharField(max_length=500)
    image = models.ImageField(upload_to='test_screenshots/%Y/%m/%d/')
    
    notes = models.TextField(blank=True)
    is_bug_screenshot = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Screenshot @ {self.page_url}"


class TestBug(models.Model):
    """Bug reported during test session"""
    
    session = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name='bugs'
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    severity = models.CharField(
        max_length=20,
        choices=[
            ('critical', 'Critical'),
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ],
        default='medium'
    )
    
    page_url = models.CharField(max_length=500)
    screenshot = models.ForeignKey(
        TestScreenshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('open', 'Open'),
            ('in_progress', 'In Progress'),
            ('resolved', 'Resolved'),
            ('wont_fix', "Won't Fix"),
        ],
        default='open'
    )
    
    reported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-reported_at']
    
    def __str__(self):
        return f"{self.title} ({self.severity})"


# ============================================================================
# COVERAGE REPORTING
# ============================================================================

class TestCoverageReport(models.Model):
    """
    Coverage report for a requirement
    
    Tracks test coverage metrics and updates automatically
    based on test execution results.
    """
    
    requirement = models.OneToOneField(
        TestRequirement,
        on_delete=models.CASCADE,
        related_name='coverage_report'
    )
    
    # Coverage metrics
    total_criteria = models.IntegerField(default=0)
    criteria_with_tests = models.IntegerField(default=0)
    tests_passing = models.IntegerField(default=0)
    tests_failing = models.IntegerField(default=0)
    tests_pending = models.IntegerField(default=0)
    
    coverage_percentage = models.FloatField(default=0.0)
    
    # Last update
    last_updated = models.DateTimeField(auto_now=True)
    last_test_run = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-coverage_percentage']
    
    def __str__(self):
        return f"Coverage: {self.requirement.name} - {self.coverage_percentage:.1f}%"
    
    def update_coverage(self):
        """Recalculate coverage metrics"""
        links = RequirementTestLink.objects.filter(requirement=self.requirement)
        
        self.total_criteria = self.requirement.get_total_criteria()
        self.criteria_with_tests = links.filter(
            status__in=['implemented', 'passing', 'failing']
        ).count()
        self.tests_passing = links.filter(status='passing').count()
        self.tests_failing = links.filter(status='failing').count()
        self.tests_pending = links.filter(status='pending').count()
        
        if self.total_criteria > 0:
            self.coverage_percentage = (self.tests_passing / self.total_criteria) * 100
        else:
            self.coverage_percentage = 0.0
        
        self.save()


# ============================================================================
# REQUIREMENT FEEDBACK SYSTEM
# ============================================================================

class RequirementFeedback(models.Model):
    """
    Feedback/Kommentare zu einem Requirement/Bug.
    Ermöglicht Fortschritts-Tracking und Kommunikation.
    """
    
    class FeedbackType(models.TextChoices):
        COMMENT = 'comment', 'Kommentar'
        PROGRESS = 'progress', 'Fortschritt'
        BLOCKER = 'blocker', 'Blocker'
        QUESTION = 'question', 'Frage'
        SOLUTION = 'solution', 'Lösung'
        SCREENSHOT = 'screenshot', 'Screenshot'
    
    requirement = models.ForeignKey(
        TestRequirement,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requirement_feedbacks'
    )
    
    feedback_type = models.CharField(
        max_length=20,
        choices=FeedbackType.choices,
        default=FeedbackType.COMMENT
    )
    
    content = models.TextField(
        help_text="Feedback-Inhalt"
    )
    
    screenshot = models.ImageField(
        upload_to='requirement_feedback/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Optional: Screenshot als Beleg"
    )
    
    is_from_cascade = models.BooleanField(
        default=False,
        help_text="True wenn von Cascade AI generiert"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bfagent_requirement_feedback'
        ordering = ['-created_at']
        verbose_name = 'Requirement Feedback'
        verbose_name_plural = 'Requirement Feedbacks'
    
    def __str__(self):
        author_name = self.author.username if self.author else 'Cascade'
        return f"{self.get_feedback_type_display()} von {author_name} @ {self.created_at:%d.%m.%Y %H:%M}"
    
    @classmethod
    def add_feedback(cls, requirement, content, feedback_type='comment', author=None, is_cascade=False, screenshot=None):
        """Helper to add feedback quickly"""
        return cls.objects.create(
            requirement=requirement,
            content=content,
            feedback_type=feedback_type,
            author=author,
            is_from_cascade=is_cascade,
            screenshot=screenshot
        )


# ============================================================================
# TEST CASE FEEDBACK SYSTEM
# ============================================================================

class TestCaseFeedback(models.Model):
    """
    Feedback/Kommentare zu einem Test Case.
    Ermöglicht Fortschritts-Tracking und Kommunikation.
    """
    
    class FeedbackType(models.TextChoices):
        COMMENT = 'comment', 'Kommentar'
        PROGRESS = 'progress', 'Fortschritt'
        BLOCKER = 'blocker', 'Blocker'
        QUESTION = 'question', 'Frage'
        SOLUTION = 'solution', 'Lösung'
        SCREENSHOT = 'screenshot', 'Screenshot'
        BUG = 'bug', 'Bug gefunden'
        FLAKY = 'flaky', 'Flaky Test'
    
    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testcase_feedbacks'
    )
    
    feedback_type = models.CharField(
        max_length=20,
        choices=FeedbackType.choices,
        default=FeedbackType.COMMENT
    )
    
    content = models.TextField(
        help_text="Feedback-Inhalt"
    )
    
    screenshot = models.ImageField(
        upload_to='testcase_feedback/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Optional: Screenshot als Beleg"
    )
    
    is_from_cascade = models.BooleanField(
        default=False,
        help_text="True wenn von Cascade AI generiert"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bfagent_testcase_feedback'
        ordering = ['-created_at']
        verbose_name = 'Test Case Feedback'
        verbose_name_plural = 'Test Case Feedbacks'
    
    def __str__(self):
        author_name = self.author.username if self.author else 'Cascade'
        return f"{self.get_feedback_type_display()} von {author_name} @ {self.created_at:%d.%m.%Y %H:%M}"
    
    @classmethod
    def add_feedback(cls, test_case, content, feedback_type='comment', author=None, is_cascade=False, screenshot=None):
        """Helper to add feedback quickly"""
        return cls.objects.create(
            test_case=test_case,
            content=content,
            feedback_type=feedback_type,
            author=author,
            is_from_cascade=is_cascade,
            screenshot=screenshot
        )


# ============================================================================
# BUG-LLM ASSIGNMENT & COST TRACKING
# ============================================================================

class BugLLMAssignment(models.Model):
    """
    Tracking der LLM-Zuweisung und Kosten pro Bug/Requirement.
    
    Ermöglicht:
    - Automatische Tier-Zuweisung
    - Eskalations-Tracking
    - Kosten-Analyse
    - Erfolgsraten-Statistiken
    """
    
    class Tier(models.TextChoices):
        TIER_1 = 'tier_1', '💚 Tier 1 (Günstig)'
        TIER_2 = 'tier_2', '💛 Tier 2 (Standard)'
        TIER_3 = 'tier_3', '🔴 Tier 3 (Premium)'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ausstehend'
        IN_PROGRESS = 'in_progress', 'In Bearbeitung'
        RESOLVED = 'resolved', 'Gelöst'
        ESCALATED = 'escalated', 'Eskaliert'
        FAILED = 'failed', 'Fehlgeschlagen'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Verknüpfung zum Requirement/Bug
    requirement = models.ForeignKey(
        TestRequirement,
        on_delete=models.CASCADE,
        related_name='llm_assignments'
    )
    
    # Tier-Zuweisung
    initial_tier = models.CharField(
        max_length=20,
        choices=Tier.choices,
        default=Tier.TIER_1,
        help_text="Ursprünglich zugewiesener Tier"
    )
    current_tier = models.CharField(
        max_length=20,
        choices=Tier.choices,
        default=Tier.TIER_1,
        help_text="Aktueller Tier (nach Eskalationen)"
    )
    complexity_score = models.IntegerField(
        default=0,
        help_text="Berechneter Komplexitäts-Score"
    )
    
    # LLM-Tracking
    llm_used = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bug_assignments'
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
    
    # Ergebnis
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
    
    # Attempt-History (JSON)
    attempt_history = models.JSONField(
        default=list,
        help_text="""
        Historie aller Versuche. Format:
        [{
            "attempt": 1,
            "tier": "tier_1",
            "llm": "gpt-3.5-turbo",
            "tokens": 1500,
            "cost": 0.0015,
            "success": false,
            "error": "Tests failed",
            "timestamp": "2026-01-10T15:00:00Z"
        }]
        """
    )
    
    class Meta:
        db_table = 'bug_llm_assignments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'current_tier']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.requirement.name} - {self.current_tier} ({self.status})"
    
    @property
    def total_tokens(self):
        return self.tokens_input + self.tokens_output
    
    @property
    def duration_seconds(self):
        if self.started_at and self.resolved_at:
            return (self.resolved_at - self.started_at).total_seconds()
        return None
    
    def escalate(self, error_reason: str = None):
        """Eskaliert zum nächsten Tier."""
        tier_order = [self.Tier.TIER_1, self.Tier.TIER_2, self.Tier.TIER_3]
        current_index = tier_order.index(self.current_tier)
        
        if current_index < len(tier_order) - 1:
            self.current_tier = tier_order[current_index + 1]
            self.escalation_count += 1
            self.status = self.Status.ESCALATED
            
            # Log attempt
            self.attempt_history.append({
                'attempt': self.attempts,
                'tier': tier_order[current_index],
                'escalated_to': self.current_tier,
                'reason': error_reason,
                'timestamp': timezone.now().isoformat()
            })
            self.save()
            return True
        return False
    
    def record_attempt(self, llm_name: str, tokens: int, cost: float, 
                       success: bool, error: str = None):
        """Zeichnet einen LLM-Versuch auf."""
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
        """Berechnet Ersparnis vs. immer Tier 3."""
        # Tier 3 Kosten für gleiche Token-Menge
        tier_3_cost_per_1m = 30.0  # $30/1M tokens (GPT-4)
        tier_3_would_cost = (self.total_tokens / 1_000_000) * tier_3_cost_per_1m
        
        return float(tier_3_would_cost - float(self.cost_usd))


class BugResolutionStats(models.Model):
    """Monatliche Statistiken für Kosten-Optimierung."""
    
    month = models.DateField(unique=True)
    
    # Tier-Verteilung
    tier_1_count = models.IntegerField(default=0)
    tier_2_count = models.IntegerField(default=0)
    tier_3_count = models.IntegerField(default=0)
    
    # Erfolgsraten (0-1)
    tier_1_success_rate = models.FloatField(default=0)
    tier_2_success_rate = models.FloatField(default=0)
    tier_3_success_rate = models.FloatField(default=0)
    
    # Kosten
    total_cost_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_saved_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Tokens
    total_tokens = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'bug_resolution_stats'
        ordering = ['-month']
    
    def __str__(self):
        return f"Stats {self.month.strftime('%Y-%m')}"
    
    @classmethod
    def calculate_for_month(cls, year: int, month: int):
        """Berechnet Statistiken für einen Monat."""
        from django.db.models import Sum, Count, Avg
        from datetime import date
        
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)
        
        assignments = BugLLMAssignment.objects.filter(
            created_at__gte=start,
            created_at__lt=end
        )
        
        stats, created = cls.objects.get_or_create(month=start)
        
        # Tier-Counts
        stats.tier_1_count = assignments.filter(initial_tier='tier_1').count()
        stats.tier_2_count = assignments.filter(initial_tier='tier_2').count()
        stats.tier_3_count = assignments.filter(initial_tier='tier_3').count()
        
        # Erfolgsraten
        def calc_success_rate(tier):
            total = assignments.filter(initial_tier=tier).count()
            if total == 0:
                return 0
            success = assignments.filter(
                initial_tier=tier,
                status='resolved',
                escalation_count=0
            ).count()
            return success / total
        
        stats.tier_1_success_rate = calc_success_rate('tier_1')
        stats.tier_2_success_rate = calc_success_rate('tier_2')
        stats.tier_3_success_rate = calc_success_rate('tier_3')
        
        # Kosten
        agg = assignments.aggregate(
            total_cost=Sum('cost_usd'),
            total_tokens=Sum('tokens_input') + Sum('tokens_output')
        )
        stats.total_cost_usd = agg['total_cost'] or 0
        stats.total_tokens = agg['total_tokens'] or 0
        
        # Ersparnis berechnen
        savings = sum(a.calculate_savings() for a in assignments)
        stats.cost_saved_usd = savings
        
        stats.save()
        return stats


# ============================================================================
# SIGNALS: AUTO-ASSIGNMENT BEI BUG-ERSTELLUNG (Hybrid-Workflow)
# ============================================================================

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Hybrid-Workflow Konfiguration
BUG_LLM_CONFIG = getattr(settings, 'BUG_LLM_ROUTER', {
    'AUTO_START_MAX_SCORE': 3,      # Score <= 3 → Auto Tier 1
    'AUTO_ESCALATE_TIER_1': True,   # T1→T2 automatisch
    'AUTO_ESCALATE_TIER_2': False,  # T2→T3 braucht Bestätigung
    'DAILY_COST_LIMIT_USD': 10.0,
    'WARN_AT_COST_USD': 5.0,
})


@receiver(post_save, sender=TestRequirement)
def auto_assign_llm_tier(sender, instance, created, **kwargs):
    """
    Hybrid-Workflow: Automatische Tier-Zuweisung bei Bug-Erstellung.
    
    Regeln:
    - Score <= 3: Auto-Start mit Tier 1 (keine UI)
    - Score 4-6: Assignment erstellen, UI zeigt Empfehlung
    - Score > 6: Assignment erstellen, manuelle Auswahl erforderlich
    """
    # Nur bei neuen Bug-Fixes
    if not created or instance.category != 'bug_fix':
        return
    
    try:
        from apps.bfagent.services.bug_llm_router import BugLLMRouter
        
        router = BugLLMRouter()
        assignment = router.create_assignment(instance)
        
        # Komplexitäts-Score für Entscheidung
        score = assignment.complexity_score
        auto_threshold = BUG_LLM_CONFIG.get('AUTO_START_MAX_SCORE', 3)
        
        if score <= auto_threshold:
            # Einfacher Bug: Auto-Start mit Tier 1
            assignment.status = BugLLMAssignment.Status.PENDING
            assignment.save()
            logger.info(f"[HYBRID] Bug '{instance.name}' auto-assigned to {assignment.current_tier} (score={score})")
        else:
            # Komplexerer Bug: Warte auf UI-Bestätigung
            assignment.status = BugLLMAssignment.Status.PENDING
            assignment.save()
            logger.info(f"[HYBRID] Bug '{instance.name}' needs confirmation (score={score}, tier={assignment.current_tier})")
    
    except Exception as e:
        logger.error(f"[HYBRID] Error auto-assigning LLM tier: {e}")


# ============================================================================
# CODE REFACTOR SESSION - LLM-gestütztes Code-Refactoring
# ============================================================================

class CodeRefactorSession(models.Model):
    """
    Code Refactoring Session für LLM-gestützte Code-Änderungen.
    
    Workflow:
    1. DRAFT: Session erstellt, Datei und Instruktion definiert
    2. GENERATING: LLM generiert Vorschlag
    3. PENDING_REVIEW: Vorschlag liegt vor, User prüft Diff
    4. APPROVED: User hat genehmigt, bereit zum Apply
    5. APPLIED: Änderung wurde angewendet
    6. REJECTED: User hat abgelehnt
    7. REVERTED: Änderung wurde zurückgesetzt
    
    Features:
    - Vollständiger Backup für Rollback
    - Diff-Generierung für Review
    - Token-Tracking für Kosten
    - Verknüpfung mit Requirement für Traceability
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # === Beziehungen ===
    requirement = models.ForeignKey(
        'TestRequirement',
        on_delete=models.CASCADE,
        related_name='refactor_sessions',
        help_text="Das Requirement, das dieses Refactoring auslöste"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_refactor_sessions'
    )
    
    # === Ziel-Datei ===
    file_path = models.CharField(
        max_length=500,
        db_index=True,
        help_text="Relativer Pfad zur Datei (z.B. 'apps/bfagent/services/llm_client.py')"
    )
    
    # === Refactoring-Instruktion ===
    instruction = models.TextField(
        help_text="Was soll refactored/optimiert werden?"
    )
    
    # === Code-Inhalte ===
    original_content = models.TextField(
        blank=True,
        help_text="Originaler Datei-Inhalt (für Rollback und Diff)"
    )
    original_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 Hash des Originals (für Konflikt-Erkennung)"
    )
    proposed_content = models.TextField(
        blank=True,
        help_text="Vom LLM vorgeschlagener neuer Inhalt"
    )
    unified_diff = models.TextField(
        blank=True,
        help_text="Diff zwischen Original und Vorschlag (für Review-UI)"
    )
    
    # === Status ===
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Entwurf'
        GENERATING = 'generating', 'LLM generiert...'
        PENDING_REVIEW = 'pending_review', 'Wartet auf Review'
        APPROVED = 'approved', 'Genehmigt'
        APPLIED = 'applied', 'Angewendet'
        REJECTED = 'rejected', 'Abgelehnt'
        REVERTED = 'reverted', 'Zurückgesetzt'
        ERROR = 'error', 'Fehler'
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    error_message = models.TextField(
        blank=True,
        help_text="Fehlermeldung falls Status=ERROR"
    )
    
    # === LLM-Metadaten ===
    llm_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Verwendetes LLM (z.B. 'gpt-4o-mini')"
    )
    llm_tokens_input = models.IntegerField(default=0)
    llm_tokens_output = models.IntegerField(default=0)
    llm_duration_ms = models.IntegerField(default=0)
    
    # === Backup für Rollback ===
    backup_content = models.TextField(
        blank=True,
        help_text="Backup vor Apply (für Revert)"
    )
    
    # === Review-Daten ===
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_refactor_sessions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # === Anwendungs-Daten ===
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applied_refactor_sessions'
    )
    reverted_at = models.DateTimeField(null=True, blank=True)
    
    # === Timestamps ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bfagent_code_refactor_session'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['requirement', 'status']),
            models.Index(fields=['file_path']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Refactor: {self.file_path} ({self.status})"
    
    @property
    def tokens_total(self) -> int:
        return self.llm_tokens_input + self.llm_tokens_output
    
    @property
    def can_apply(self) -> bool:
        """Prüft ob Änderung angewendet werden kann."""
        return self.status == self.Status.APPROVED and self.proposed_content
    
    @property
    def can_revert(self) -> bool:
        """Prüft ob Änderung zurückgesetzt werden kann."""
        return self.status == self.Status.APPLIED and self.backup_content
    
    @property
    def lines_added(self) -> int:
        """Anzahl hinzugefügter Zeilen aus Diff."""
        if not self.unified_diff:
            return 0
        return self.unified_diff.count('\n+') - self.unified_diff.count('\n+++')
    
    @property
    def lines_removed(self) -> int:
        """Anzahl entfernter Zeilen aus Diff."""
        if not self.unified_diff:
            return 0
        return self.unified_diff.count('\n-') - self.unified_diff.count('\n---')
