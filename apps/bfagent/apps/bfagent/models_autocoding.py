"""
Autocoding Models
=================

Models für das Autorouting/Autocoding-System.

Hauptkomponenten:
- AutocodingRun: Ein vollständiger Autocoding-Durchlauf
- ToolCall: Audit-Trail für jeden Tool-Aufruf
- Artifact: Artefakte (Patches, Reports, Outputs)

Integration:
- TestRequirement → AutocodingRun → ToolCalls → Artifacts
- AutocodingRun → CodeRefactorSessions (für Code-Änderungen)
"""

import uuid
import hashlib
from django.db import models
from django.conf import settings
from django.utils import timezone


# =============================================================================
# AutocodingRun
# =============================================================================

class AutocodingRun(models.Model):
    """
    Haupt-Entität für einen Autocoding-Durchlauf.
    
    Workflow:
    1. CREATED: Run erstellt aus Requirement
    2. ANALYZING: LLM analysiert Task
    3. PLANNING: Tasks werden extrahiert
    4. EXECUTING: Tasks werden ausgeführt
    5. REVIEWING: Ergebnisse warten auf Review
    6. COMPLETED: Erfolgreich abgeschlossen
    7. FAILED: Fehlgeschlagen
    """
    
    class Status(models.TextChoices):
        CREATED = 'created', 'Erstellt'
        ANALYZING = 'analyzing', 'Analysiert...'
        PLANNING = 'planning', 'Plant...'
        EXECUTING = 'executing', 'Führt aus...'
        REVIEWING = 'reviewing', 'Wartet auf Review'
        COMPLETED = 'completed', 'Abgeschlossen'
        FAILED = 'failed', 'Fehlgeschlagen'
        CANCELLED = 'cancelled', 'Abgebrochen'
    
    class Complexity(models.TextChoices):
        SMALL = 'S', 'Klein'
        MEDIUM = 'M', 'Mittel'
        LARGE = 'L', 'Groß'
    
    class Risk(models.TextChoices):
        LOW = 'low', 'Niedrig'
        MEDIUM = 'medium', 'Mittel'
        HIGH = 'high', 'Hoch'
    
    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # === Verknüpfungen ===
    requirement = models.ForeignKey(
        'bfagent.TestRequirement',
        on_delete=models.CASCADE,
        related_name='autocoding_runs',
        help_text='Verknüpftes Requirement aus Test Studio'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='autocoding_runs_created'
    )
    
    # === Task Definition ===
    task_text = models.TextField(
        help_text='Vollständige Aufgabenbeschreibung für LLM'
    )
    
    # === Repository (optional) ===
    repo_url = models.URLField(
        blank=True,
        help_text='Git Repository URL'
    )
    base_branch = models.CharField(
        max_length=100,
        default='main',
        blank=True
    )
    workspace_path = models.CharField(
        max_length=500,
        blank=True,
        help_text='Lokaler Workspace-Pfad'
    )
    
    # === Klassifikation ===
    complexity = models.CharField(
        max_length=1,
        choices=Complexity.choices,
        default=Complexity.SMALL
    )
    risk = models.CharField(
        max_length=10,
        choices=Risk.choices,
        default=Risk.LOW
    )
    
    # === LLM Routing ===
    llm = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Verwendetes LLM'
    )
    routing_reason = models.CharField(
        max_length=200,
        blank=True,
        help_text='Grund für LLM-Auswahl'
    )
    
    # === Status & Progress ===
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True
    )
    current_iteration = models.PositiveIntegerField(default=0)
    max_iterations = models.PositiveIntegerField(default=6)
    error_message = models.TextField(blank=True)
    
    # === Ergebnisse ===
    analysis_result = models.JSONField(
        default=dict,
        blank=True,
        help_text='LLM-Analyse Ergebnis'
    )
    tasks_extracted = models.JSONField(
        default=list,
        blank=True,
        help_text='Extrahierte Tasks'
    )
    
    # === Kosten-Tracking ===
    total_tokens_input = models.PositiveIntegerField(default=0)
    total_tokens_output = models.PositiveIntegerField(default=0)
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0
    )
    
    # === Timestamps ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'bfagent_autocoding_runs'
        ordering = ['-created_at']
        verbose_name = 'Autocoding Run'
        verbose_name_plural = 'Autocoding Runs'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['requirement', 'status']),
        ]
    
    def __str__(self):
        return f"Run {str(self.id)[:8]} - {self.requirement.name[:30]}"
    
    @property
    def total_tokens(self) -> int:
        return self.total_tokens_input + self.total_tokens_output
    
    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0
    
    @property
    def refactor_sessions(self):
        """Verknüpfte CodeRefactorSessions."""
        from .models_testing import CodeRefactorSession
        return CodeRefactorSession.objects.filter(requirement=self.requirement)
    
    def start(self):
        """Startet den Run."""
        self.status = self.Status.ANALYZING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def complete(self, success: bool = True, error: str = ''):
        """Beendet den Run."""
        self.status = self.Status.COMPLETED if success else self.Status.FAILED
        self.completed_at = timezone.now()
        self.error_message = error
        self.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])
    
    def add_tokens(self, input_tokens: int, output_tokens: int, cost: float = 0):
        """Fügt Token-Verbrauch hinzu."""
        self.total_tokens_input += input_tokens
        self.total_tokens_output += output_tokens
        self.total_cost += cost
        self.save(update_fields=['total_tokens_input', 'total_tokens_output', 'total_cost'])


# =============================================================================
# ToolCall
# =============================================================================

class ToolCall(models.Model):
    """
    Audit-Trail für jeden Tool-Aufruf innerhalb eines Runs.
    
    Speichert:
    - Redaktierte Args/Output (keine Secrets)
    - SHA256 Hashes der Original-Daten
    - Timing und Exit-Codes
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    run = models.ForeignKey(
        AutocodingRun,
        on_delete=models.CASCADE,
        related_name='tool_calls'
    )
    
    # === Tool Information ===
    tool_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Name des Tools (z.B. git.clone, build.run)'
    )
    handler_class = models.CharField(
        max_length=200,
        blank=True,
        help_text='Python-Klasse des Handlers'
    )
    
    # === Arguments (redaktiert) ===
    args_redacted = models.JSONField(
        default=dict,
        help_text='Redaktierte Argumente (keine Secrets)'
    )
    args_sha256 = models.CharField(
        max_length=64,
        blank=True,
        help_text='SHA256 Hash der Original-Args'
    )
    
    # === Execution ===
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    duration_ms = models.PositiveIntegerField(default=0)
    
    # === Results ===
    ok = models.BooleanField(default=False)
    exit_code = models.IntegerField(default=0)
    stdout_redacted = models.TextField(
        blank=True,
        help_text='Redaktierter stdout (max 10KB)'
    )
    stderr_redacted = models.TextField(
        blank=True,
        help_text='Redaktierter stderr (max 10KB)'
    )
    stdout_sha256 = models.CharField(max_length=64, blank=True)
    stderr_sha256 = models.CharField(max_length=64, blank=True)
    
    # === Metadata ===
    artifacts_meta = models.JSONField(
        default=dict,
        blank=True,
        help_text='Metadaten zu erstellten Artifacts'
    )
    policy_events = models.JSONField(
        default=dict,
        blank=True,
        help_text='Policy-Checks und Events'
    )
    
    class Meta:
        db_table = 'bfagent_autocoding_tool_calls'
        ordering = ['started_at']
        verbose_name = 'Tool Call'
        verbose_name_plural = 'Tool Calls'
        indexes = [
            models.Index(fields=['run', 'tool_name']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"{self.tool_name} ({self.run_id})"
    
    def save(self, *args, **kwargs):
        if self.started_at and self.ended_at:
            self.duration_ms = int((self.ended_at - self.started_at).total_seconds() * 1000)
        super().save(*args, **kwargs)
    
    @staticmethod
    def create_hash(text: str) -> str:
        """Erstellt SHA256 Hash."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()


# =============================================================================
# Artifact
# =============================================================================

class Artifact(models.Model):
    """
    Artefakte eines Runs (Patches, Reports, Output).
    
    Ermöglicht:
    - Reproduzierbarkeit (SHA256 Hashes)
    - Verknüpfung mit CodeRefactorSession
    - Audit-Trail
    """
    
    class Kind(models.TextChoices):
        PATCH = 'patch', 'Patch (Unified Diff)'
        CODE_BLOCK = 'code_block', 'Code Block'
        STDOUT = 'stdout', 'Standard Output'
        STDERR = 'stderr', 'Standard Error'
        REPORT = 'report', 'Report'
        ANALYSIS = 'analysis', 'Analyse-Ergebnis'
        META = 'meta', 'Metadata'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    run = models.ForeignKey(
        AutocodingRun,
        on_delete=models.CASCADE,
        related_name='artifacts'
    )
    tool_call = models.ForeignKey(
        ToolCall,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='artifacts'
    )
    
    # === Artifact Data ===
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        db_index=True
    )
    file_path = models.CharField(
        max_length=500,
        help_text='Relativer Pfad im Workspace'
    )
    content = models.TextField(
        blank=True,
        help_text='Inhalt (für kleine Artifacts)'
    )
    sha256 = models.CharField(
        max_length=64,
        help_text='SHA256 Hash des Inhalts'
    )
    size_bytes = models.PositiveIntegerField(default=0)
    
    # === Verknüpfung zu CodeRefactorSession ===
    refactor_session = models.ForeignKey(
        'bfagent.CodeRefactorSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='artifacts',
        help_text='Automatisch erstellte Refactor-Session'
    )
    
    # === Metadata ===
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bfagent_autocoding_artifacts'
        ordering = ['-created_at']
        verbose_name = 'Artifact'
        verbose_name_plural = 'Artifacts'
        indexes = [
            models.Index(fields=['run', 'kind']),
            models.Index(fields=['sha256']),
        ]
    
    def __str__(self):
        return f"{self.kind}: {self.file_path}"
    
    def save(self, *args, **kwargs):
        if self.content and not self.sha256:
            self.sha256 = hashlib.sha256(self.content.encode('utf-8')).hexdigest()
            self.size_bytes = len(self.content.encode('utf-8'))
        super().save(*args, **kwargs)
