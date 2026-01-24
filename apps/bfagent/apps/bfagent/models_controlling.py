# -*- coding: utf-8 -*-
"""
Agent/LLM Controlling Models.

Tracking und Controlling für:
- LLM-Kosten und Token-Verbrauch
- Agent-Performance und Qualität
- Validierungen und verhinderte Fehler
- Baseline-Messungen für Vergleich
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class LLMUsageLog(models.Model):
    """
    Tracking aller LLM-Aufrufe.
    
    Erfasst Kosten, Performance und Qualität jedes LLM-Calls.
    """
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Kontext
    agent = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Agent-Name (z.B. 'DjangoAgent', 'DocAgent', 'direct')"
    )
    task = models.CharField(
        max_length=100,
        help_text="Task-Name (z.B. 'validate_view', 'translate_docstring')"
    )
    
    # Model/Provider
    model = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Model-Name (z.B. 'gpt-4o', 'llama-3.1-8b')"
    )
    provider = models.CharField(
        max_length=30,
        default="unknown",
        help_text="Provider (z.B. 'openai', 'groq', 'gemini')"
    )
    
    # Token & Kosten
    tokens_in = models.IntegerField(default=0, help_text="Input Tokens")
    tokens_out = models.IntegerField(default=0, help_text="Output Tokens")
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=Decimal("0.000000"),
        help_text="Kosten in USD"
    )
    
    # Performance
    latency_ms = models.FloatField(default=0.0, help_text="Latenz in Millisekunden")
    cached = models.BooleanField(default=False, help_text="Aus Cache beantwortet?")
    fallback_used = models.BooleanField(default=False, help_text="Fallback-Model verwendet?")
    
    # Qualität
    success = models.BooleanField(default=True, help_text="Erfolgreich abgeschlossen?")
    error_message = models.TextField(null=True, blank=True, help_text="Fehlermeldung bei Fehler")
    
    # Zusätzlicher Kontext
    request_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Hash des Requests für Deduplizierung"
    )
    
    # Prompt & Response Content (für Debugging/Analyse)
    prompt_text = models.TextField(
        null=True,
        blank=True,
        help_text="Der gesendete Prompt (gekürzt auf 2000 Zeichen)"
    )
    response_text = models.TextField(
        null=True,
        blank=True,
        help_text="Die LLM-Antwort (gekürzt auf 4000 Zeichen)"
    )
    
    # Kontext-Metadaten (für Code-Generierung)
    context_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Zusätzliche Metadaten: file_path, task_type, etc."
    )
    
    # Session-Tracking für Call-Tree
    session_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Session-ID für Gruppierung zusammengehöriger Calls"
    )
    orchestration_call = models.ForeignKey(
        'OrchestrationCall',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='llm_calls',
        help_text="Zugehöriger Orchestration-Call"
    )
    
    class Meta:
        verbose_name = "LLM Usage Log"
        verbose_name_plural = "LLM Usage Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp", "agent"]),
            models.Index(fields=["timestamp", "model"]),
            models.Index(fields=["agent", "task"]),
        ]
    
    def __str__(self):
        return f"{self.agent}/{self.task} - {self.model} ({self.timestamp:%Y-%m-%d %H:%M})"
    
    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out
    
    @classmethod
    def get_cost_summary(cls, days: int = 30) -> dict:
        """Kosten-Zusammenfassung für Zeitraum."""
        since = timezone.now() - timedelta(days=days)
        logs = cls.objects.filter(timestamp__gte=since)
        
        from django.db.models import Sum, Count, Avg
        
        summary = logs.aggregate(
            total_cost=Sum("cost_usd"),
            total_calls=Count("id"),
            total_tokens_in=Sum("tokens_in"),
            total_tokens_out=Sum("tokens_out"),
            avg_latency=Avg("latency_ms"),
        )
        
        # Nach Provider aufschlüsseln
        by_provider = logs.values("provider").annotate(
            cost=Sum("cost_usd"),
            calls=Count("id"),
        ).order_by("-cost")
        
        # Nach Agent aufschlüsseln
        by_agent = logs.values("agent").annotate(
            cost=Sum("cost_usd"),
            calls=Count("id"),
        ).order_by("-cost")
        
        return {
            "period_days": days,
            "summary": summary,
            "by_provider": list(by_provider),
            "by_agent": list(by_agent),
        }


class AgentValidationLog(models.Model):
    """
    Tracking Agent-Validierungen.
    
    Erfasst alle Validierungen durch Agents wie DjangoAgent,
    inklusive verhinderte Fehler.
    """
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Agent & Aktion
    agent = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Agent-Name (z.B. 'DjangoAgent')"
    )
    action = models.CharField(
        max_length=50,
        help_text="Validierungs-Aktion (z.B. 'validate_python_file')"
    )
    
    # Ergebnis
    passed = models.BooleanField(
        help_text="Validierung bestanden (keine Fehler)?"
    )
    errors_count = models.IntegerField(
        default=0,
        help_text="Anzahl gefundener Fehler"
    )
    warnings_count = models.IntegerField(
        default=0,
        help_text="Anzahl gefundener Warnungen"
    )
    
    # Details
    errors_prevented = models.JSONField(
        default=list,
        help_text="Liste der verhinderten Fehler (Rule + Message)"
    )
    
    # Kontext
    file_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Geprüfte Datei"
    )
    cascade_session_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Cascade Session ID für Zuordnung"
    )
    
    class Meta:
        verbose_name = "Agent Validation Log"
        verbose_name_plural = "Agent Validation Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp", "agent"]),
            models.Index(fields=["agent", "action"]),
        ]
    
    def __str__(self):
        status = "✅" if self.passed else f"❌ {self.errors_count}"
        return f"{self.agent}/{self.action} {status} ({self.timestamp:%Y-%m-%d %H:%M})"
    
    @classmethod
    def get_quality_summary(cls, days: int = 30) -> dict:
        """Qualitäts-Zusammenfassung für Zeitraum."""
        since = timezone.now() - timedelta(days=days)
        logs = cls.objects.filter(timestamp__gte=since)
        
        from django.db.models import Sum, Count, Avg
        
        summary = logs.aggregate(
            total_validations=Count("id"),
            total_passed=Count("id", filter=models.Q(passed=True)),
            total_failed=Count("id", filter=models.Q(passed=False)),
            total_errors_prevented=Sum("errors_count"),
        )
        
        # Erfolgsrate berechnen
        if summary["total_validations"] > 0:
            summary["success_rate"] = (
                summary["total_passed"] / summary["total_validations"] * 100
            )
        else:
            summary["success_rate"] = 100.0
        
        # Nach Agent aufschlüsseln
        by_agent = logs.values("agent").annotate(
            validations=Count("id"),
            passed=Count("id", filter=models.Q(passed=True)),
            errors_prevented=Sum("errors_count"),
        ).order_by("-validations")
        
        # Häufigste verhinderte Fehler
        # (Aggregation über JSONField ist komplex, daher Python-basiert)
        error_types = {}
        for log in logs.filter(passed=False):
            for error in log.errors_prevented:
                rule = error.get("rule", "unknown")
                error_types[rule] = error_types.get(rule, 0) + 1
        
        top_errors = sorted(error_types.items(), key=lambda x: -x[1])[:10]
        
        return {
            "period_days": days,
            "summary": summary,
            "by_agent": list(by_agent),
            "top_error_types": top_errors,
        }


class ControllingBaseline(models.Model):
    """
    Baseline-Messungen für Vergleich.
    
    Speichert historische Baselines um Verbesserungen zu messen.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    
    metric_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Metrik-Typ (z.B. 'django_errors', 'llm_cost', 'quality')"
    )
    
    period_days = models.IntegerField(
        default=30,
        help_text="Zeitraum der Messung in Tagen"
    )
    
    # Messdaten als JSON
    data = models.JSONField(
        help_text="Baseline-Daten als JSON"
    )
    
    # Beschreibung
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Beschreibung der Baseline"
    )
    
    class Meta:
        verbose_name = "Controlling Baseline"
        verbose_name_plural = "Controlling Baselines"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.metric_type} Baseline ({self.created_at:%Y-%m-%d})"
    
    @classmethod
    def get_latest(cls, metric_type: str) -> "ControllingBaseline":
        """Holt die letzte Baseline für einen Metrik-Typ."""
        return cls.objects.filter(metric_type=metric_type).first()
    
    @classmethod
    def compare_with_current(cls, metric_type: str, current_data: dict) -> dict:
        """Vergleicht aktuelle Daten mit Baseline."""
        baseline = cls.get_latest(metric_type)
        
        if not baseline:
            return {"has_baseline": False, "message": "Keine Baseline vorhanden"}
        
        comparison = {
            "has_baseline": True,
            "baseline_date": baseline.created_at.isoformat(),
            "baseline_data": baseline.data,
            "current_data": current_data,
            "changes": {},
        }
        
        # Vergleich für bekannte Metriken
        if metric_type == "django_errors":
            baseline_total = baseline.data.get("django_errors", {}).get("total", 0)
            current_total = current_data.get("django_errors", {}).get("total", 0)
            
            if baseline_total > 0:
                change_pct = ((current_total - baseline_total) / baseline_total) * 100
            else:
                change_pct = 0
            
            comparison["changes"]["django_errors"] = {
                "baseline": baseline_total,
                "current": current_total,
                "change_percent": round(change_pct, 1),
                "improved": current_total < baseline_total,
            }
        
        return comparison


class ControllingAlert(models.Model):
    """
    Alerts für Controlling-Schwellwerte.
    """
    ALERT_TYPES = [
        ("budget_warning", "Budget Warnung"),
        ("budget_exceeded", "Budget überschritten"),
        ("error_rate_high", "Hohe Fehlerrate"),
        ("latency_high", "Hohe Latenz"),
        ("fallback_frequent", "Häufige Fallbacks"),
    ]
    
    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warnung"),
        ("critical", "Kritisch"),
    ]
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    alert_type = models.CharField(
        max_length=30,
        choices=ALERT_TYPES,
        db_index=True
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="warning"
    )
    
    message = models.TextField(help_text="Alert-Nachricht")
    
    # Schwellwerte
    threshold_value = models.FloatField(
        null=True,
        help_text="Schwellwert der überschritten wurde"
    )
    actual_value = models.FloatField(
        null=True,
        help_text="Tatsächlicher Wert"
    )
    
    # Status
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        verbose_name = "Controlling Alert"
        verbose_name_plural = "Controlling Alerts"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.get_severity_display()}: {self.get_alert_type_display()}"
    
    def acknowledge(self, by: str = None):
        """Markiert Alert als bestätigt."""
        self.acknowledged = True
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = by
        self.save()


class OrchestrationCall(models.Model):
    """
    Call-Hierarchie-Tracking für Orchestrierung.
    
    Erfasst die komplette Aufruf-Hierarchie:
    - Request empfangen
    - Task-Liste erstellt
    - Routing initiiert
    - Tasks abgearbeitet
    - Ergebnis zurückgemeldet
    """
    CALL_TYPES = [
        ('request', 'Request Received'),
        ('planning', 'Task Planning'),
        ('routing', 'Task Routing'),
        ('execution', 'Task Execution'),
        ('llm_call', 'LLM Call'),
        ('tool_call', 'Tool Call'),
        ('result', 'Result Returned'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=None, editable=False)
    
    # Hierarchie
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        help_text="Parent-Call in der Hierarchie"
    )
    session_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Session-ID für Gruppierung"
    )
    sequence = models.IntegerField(
        default=0,
        help_text="Reihenfolge innerhalb des Parents"
    )
    depth = models.IntegerField(
        default=0,
        help_text="Tiefe in der Hierarchie (0 = Root)"
    )
    
    # Call-Details
    call_type = models.CharField(
        max_length=20,
        choices=CALL_TYPES,
        db_index=True
    )
    name = models.CharField(
        max_length=200,
        help_text="Name des Calls (z.B. 'generate_django_view')"
    )
    description = models.TextField(
        blank=True,
        help_text="Beschreibung/Input"
    )
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    
    # Status & Result
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    result_summary = models.TextField(
        blank=True,
        help_text="Kurze Zusammenfassung des Ergebnisses"
    )
    error_message = models.TextField(
        null=True,
        blank=True
    )
    
    # Metrics (für LLM-Calls)
    tokens_in = models.IntegerField(null=True, blank=True)
    tokens_out = models.IntegerField(null=True, blank=True)
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Zusätzliche Metadaten"
    )
    
    class Meta:
        verbose_name = "Orchestration Call"
        verbose_name_plural = "Orchestration Calls"
        ordering = ["session_id", "depth", "sequence"]
        indexes = [
            models.Index(fields=["session_id", "started_at"]),
            models.Index(fields=["call_type", "status"]),
            models.Index(fields=["parent", "sequence"]),
        ]
    
    def save(self, *args, **kwargs):
        import uuid
        if self.id is None:
            self.id = uuid.uuid4()
        if self.ended_at and self.started_at:
            self.duration_ms = int((self.ended_at - self.started_at).total_seconds() * 1000)
        super().save(*args, **kwargs)
    
    def __str__(self):
        indent = "  " * self.depth
        status_icon = {"success": "✅", "failed": "❌", "running": "🔄", "pending": "⏳"}.get(self.status, "")
        return f"{indent}{status_icon} {self.call_type}: {self.name}"
    
    def complete(self, success: bool, result_summary: str = "", error: str = None):
        """Markiert Call als abgeschlossen."""
        self.ended_at = timezone.now()
        self.status = 'success' if success else 'failed'
        self.result_summary = result_summary
        self.error_message = error
        self.save()
    
    @classmethod
    def start_session(cls, description: str) -> 'OrchestrationCall':
        """Startet eine neue Orchestrierungs-Session."""
        import uuid
        session_id = str(uuid.uuid4())[:8]
        return cls.objects.create(
            session_id=session_id,
            call_type='request',
            name='Session Start',
            description=description,
            status='running'
        )
    
    def add_child(self, call_type: str, name: str, description: str = "") -> 'OrchestrationCall':
        """Fügt einen Child-Call hinzu."""
        max_seq = self.children.aggregate(models.Max('sequence'))['sequence__max'] or 0
        return OrchestrationCall.objects.create(
            parent=self,
            session_id=self.session_id,
            sequence=max_seq + 1,
            depth=self.depth + 1,
            call_type=call_type,
            name=name,
            description=description,
            status='running'
        )
    
    @classmethod
    def get_session_tree(cls, session_id: str) -> list:
        """Gibt die komplette Session-Hierarchie zurück."""
        calls = cls.objects.filter(session_id=session_id).order_by('depth', 'sequence')
        return list(calls)
