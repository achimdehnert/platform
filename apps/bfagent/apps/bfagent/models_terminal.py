# -*- coding: utf-8 -*-
"""
Terminal Error Capture Models.

MVP für Terminal-Output-Erfassung und KI-gestützte Fehlerbehebung.
"""
import uuid
import hashlib
from django.db import models
from django.utils import timezone


class TerminalSession(models.Model):
    """Eine Terminal-Session (z.B. ein Django runserver Prozess)."""
    
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('crashed', 'Crashed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process_name = models.CharField(max_length=100, help_text="z.B. runserver, pytest, npm")
    command = models.TextField(blank=True, help_text="Vollständiger Befehl")
    
    # Zeitstempel
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # Log-Datei
    log_file = models.CharField(max_length=500, help_text="Pfad zur JSONL Log-Datei")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    exit_code = models.IntegerField(null=True, blank=True)
    
    # Statistiken
    total_lines = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    warning_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'bfagent_terminal_sessions'
        ordering = ['-started_at']
        verbose_name = 'Terminal Session'
        verbose_name_plural = 'Terminal Sessions'
    
    def __str__(self):
        return f"{self.process_name} ({self.started_at:%Y-%m-%d %H:%M})"
    
    @property
    def duration(self):
        """Dauer der Session."""
        end = self.ended_at or timezone.now()
        return end - self.started_at


class TerminalError(models.Model):
    """Erkannter Fehler aus Terminal-Output mit KI-Lösungsvorschlag."""
    
    ERROR_TYPE_CHOICES = [
        ('import_error', 'Import Error'),
        ('template_error', 'Template Error'),
        ('syntax_error', 'Syntax Error'),
        ('database_error', 'Database Error'),
        ('url_error', 'URL/Routing Error'),
        ('attribute_error', 'Attribute Error'),
        ('type_error', 'Type Error'),
        ('value_error', 'Value Error'),
        ('key_error', 'Key Error'),
        ('runtime_error', 'Runtime Error'),
        ('npm_error', 'NPM/Node Error'),
        ('browser_error', 'Browser/JS Error'),
        ('other', 'Other'),
    ]
    
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('analyzing', 'AI Analyzing'),
        ('ready', 'Fix Ready'),
        ('in_progress', 'Fix In Progress'),
        ('fixed', 'Fixed'),
        ('verified', 'Verified'),
        ('ignored', 'Ignored'),
        ('wont_fix', "Won't Fix"),
    ]
    
    SOURCE_CHOICES = [
        ('django', 'Django'),
        ('python', 'Python'),
        ('npm', 'NPM/Node'),
        ('browser', 'Browser Console'),
        ('test', 'Test Runner'),
        ('migration', 'Migration'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    error_hash = models.CharField(max_length=64, unique=True, help_text="SHA256 für Deduplizierung")
    
    # Verknüpfung zur Session
    session = models.ForeignKey(
        TerminalSession, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='errors'
    )
    
    # Klassifizierung
    error_type = models.CharField(max_length=50, choices=ERROR_TYPE_CHOICES, default='other')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='django')
    
    # Fehler-Details
    error_class = models.CharField(max_length=100, blank=True, help_text="z.B. ImportError, TemplateDoesNotExist")
    message = models.TextField(help_text="Fehlermeldung")
    file_path = models.CharField(max_length=500, blank=True, null=True)
    line_number = models.IntegerField(null=True, blank=True)
    column_number = models.IntegerField(null=True, blank=True)
    function_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Kontext
    code_snippet = models.TextField(blank=True, null=True, help_text="Code um die Fehlerzeile")
    stack_trace = models.TextField(blank=True, null=True)
    raw_output = models.TextField(help_text="Original Terminal-Output")
    
    # Tracking
    occurrence_count = models.IntegerField(default=1)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    # KI-Analyse & Lösungsvorschlag
    ai_analysis = models.TextField(blank=True, null=True, help_text="KI-Analyse des Fehlers")
    ai_solution_steps = models.JSONField(
        default=list, 
        blank=True,
        help_text="Liste der Lösungsschritte von der KI"
    )
    ai_confidence = models.FloatField(null=True, blank=True, help_text="Konfidenz der KI (0-1)")
    ai_analyzed_at = models.DateTimeField(null=True, blank=True)
    
    # Manuelle Notizen
    notes = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='resolved_terminal_errors'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'bfagent_terminal_errors'
        ordering = ['-last_seen']
        verbose_name = 'Terminal Error'
        verbose_name_plural = 'Terminal Errors'
        indexes = [
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['error_type', 'source']),
            models.Index(fields=['first_seen']),
            models.Index(fields=['last_seen']),
        ]
    
    def __str__(self):
        return f"[{self.error_type}] {self.message[:80]}"
    
    def save(self, *args, **kwargs):
        # Hash generieren für Deduplizierung
        if not self.error_hash:
            hash_input = f"{self.error_type}:{self.error_class}:{self.message}:{self.file_path}:{self.line_number}"
            self.error_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_or_increment(cls, error_data: dict) -> 'TerminalError':
        """Findet existierenden Fehler oder erstellt neuen, erhöht occurrence_count."""
        hash_input = f"{error_data.get('error_type', 'other')}:{error_data.get('error_class', '')}:{error_data.get('message', '')}:{error_data.get('file_path', '')}:{error_data.get('line_number', '')}"
        error_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        try:
            error = cls.objects.get(error_hash=error_hash)
            error.occurrence_count += 1
            error.last_seen = timezone.now()
            error.raw_output = error_data.get('raw_output', error.raw_output)
            error.save(update_fields=['occurrence_count', 'last_seen', 'raw_output'])
            return error
        except cls.DoesNotExist:
            error_data['error_hash'] = error_hash
            return cls.objects.create(**error_data)


class TerminalErrorFixAttempt(models.Model):
    """Dokumentiert jeden manuellen Fix-Versuch."""
    
    RESULT_CHOICES = [
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    error = models.ForeignKey(
        TerminalError, 
        on_delete=models.CASCADE, 
        related_name='fix_attempts'
    )
    
    # Wer hat gefixt
    user = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='terminal_fix_attempts'
    )
    attempted_at = models.DateTimeField(auto_now_add=True)
    
    # Was wurde gemacht
    description = models.TextField(help_text="Beschreibung was gemacht wurde")
    files_changed = models.JSONField(default=list, help_text="Liste der geänderten Dateien")
    
    # KI-Unterstützung
    used_ai_suggestion = models.BooleanField(default=False)
    ai_step_followed = models.IntegerField(null=True, blank=True, help_text="Welcher KI-Schritt befolgt wurde")
    
    # Ergebnis
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='success')
    result_notes = models.TextField(blank=True, null=True)
    
    # Verifizierung
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_method = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="z.B. 'rerun', 'test', 'manual'"
    )
    
    class Meta:
        db_table = 'bfagent_terminal_fix_attempts'
        ordering = ['-attempted_at']
        verbose_name = 'Fix Attempt'
        verbose_name_plural = 'Fix Attempts'
    
    def __str__(self):
        return f"Fix for {self.error.error_class} by {self.user} ({self.result})"
