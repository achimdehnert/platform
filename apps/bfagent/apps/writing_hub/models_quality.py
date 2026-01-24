"""
Quality Scoring & Series Memory Models
======================================

Strikt DB-getrieben, keine Hardcoded-Werte.
Alle Enums als Lookup-Tabellen für maximale Flexibilität.

Naming Convention: writing_* Präfix für alle Tabellen.
"""
import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# =============================================================================
# LOOKUP TABLES (Enum-Ersatz, DB-getrieben)
# =============================================================================


class QualityDimension(models.Model):
    """
    Lookup: Qualitätsdimensionen für Kapitel-Bewertung.
    
    Beispiele: style, genre, scene, serial_logic, pacing, dialogue
    Erlaubt flexible Erweiterung ohne Schema-Änderung.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name_de = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    weight = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=1.0,
        help_text="Gewichtung für Overall-Score Berechnung"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'writing_quality_dimensions'
        ordering = ['sort_order', 'code']
        verbose_name = 'Quality Dimension'
        verbose_name_plural = 'Quality Dimensions'

    def __str__(self):
        return f"{self.name_de} ({self.code})"


class GateDecisionType(models.Model):
    """
    Lookup: Quality Gate Entscheidungen.
    
    Beispiele: approve, review, revise, reject
    Statt Hardcoded-Strings, vollständig DB-getrieben.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True, db_index=True)
    name_de = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=20, 
        default='secondary',
        help_text="Bootstrap color class (success, warning, danger, etc.)"
    )
    icon = models.CharField(
        max_length=50, 
        default='bi-question-circle',
        help_text="Bootstrap Icon class"
    )
    allows_commit = models.BooleanField(
        default=False,
        help_text="Erlaubt Kapitel-Commit/Lock"
    )
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'writing_gate_decision_types'
        ordering = ['sort_order']
        verbose_name = 'Gate Decision Type'
        verbose_name_plural = 'Gate Decision Types'

    def __str__(self):
        return f"{self.name_de} ({self.code})"


class PromiseStatus(models.Model):
    """
    Lookup: Story Promise/Hook Status.
    
    Beispiele: open, reinforced, twisted, paid, retired
    Für Langbogen-Tracking über mehrere Bände.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True, db_index=True)
    name_de = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_terminal = models.BooleanField(
        default=False,
        help_text="True = Promise ist abgeschlossen (paid/retired)"
    )
    color = models.CharField(max_length=20, default='secondary')
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'writing_promise_statuses'
        ordering = ['sort_order']
        verbose_name = 'Promise Status'
        verbose_name_plural = 'Promise Statuses'

    def __str__(self):
        return f"{self.name_de} ({self.code})"


# =============================================================================
# QUALITY SCORING (Kapitel-Ebene)
# =============================================================================


class ChapterQualityScore(models.Model):
    """
    Qualitätsbewertung für ein Kapitel.
    
    Keine Hardcoded-Score-Felder - Dimensionen flexibel via ChapterDimensionScore.
    Gate-Entscheidung als FK zu Lookup-Tabelle.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.CASCADE,
        related_name='quality_scores'
    )
    
    scored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chapter_scores'
    )
    scored_at = models.DateTimeField(auto_now_add=True)
    
    gate_decision = models.ForeignKey(
        GateDecisionType,
        on_delete=models.PROTECT,
        related_name='chapter_scores'
    )
    
    overall_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Gewichteter Durchschnitt aller Dimension-Scores"
    )
    
    findings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Strukturierte Findings: {deviations: [], suggestions: []}"
    )
    
    pipeline_execution = models.ForeignKey(
        'writing_hub.AgentPipelineExecution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quality_scores',
        help_text="Verknüpfung zum LLM-Run der die Bewertung erstellt hat"
    )
    
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'writing_chapter_quality_scores'
        ordering = ['-scored_at']
        verbose_name = 'Chapter Quality Score'
        verbose_name_plural = 'Chapter Quality Scores'
        get_latest_by = 'scored_at'

    def __str__(self):
        return f"Score {self.overall_score} für {self.chapter}"

    @property
    def is_approved(self):
        return self.gate_decision.allows_commit


class ChapterDimensionScore(models.Model):
    """
    Einzelne Dimension-Bewertung für einen ChapterQualityScore.
    
    M2M-Beziehung zwischen Score und Dimension.
    Erlaubt flexible Dimensionen ohne Schema-Änderung.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    quality_score = models.ForeignKey(
        ChapterQualityScore,
        on_delete=models.CASCADE,
        related_name='dimension_scores'
    )
    dimension = models.ForeignKey(
        QualityDimension,
        on_delete=models.PROTECT,
        related_name='chapter_scores'
    )
    score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'writing_chapter_dimension_scores'
        unique_together = ['quality_score', 'dimension']
        verbose_name = 'Chapter Dimension Score'
        verbose_name_plural = 'Chapter Dimension Scores'

    def __str__(self):
        return f"{self.dimension.code}: {self.score}"


# =============================================================================
# QUALITY GATE CONFIG (Projekt-Ebene)
# =============================================================================


class ProjectQualityConfig(models.Model):
    """
    Konfigurierbare Quality Gates pro Projekt.
    
    Globale Schwellenwerte + Dimension-spezifische via ProjectDimensionThreshold.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    project = models.OneToOneField(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='quality_config'
    )
    
    min_overall_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Minimum Overall Score für 'review'"
    )
    auto_approve_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=9.0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Über diesem Wert: automatische Freigabe"
    )
    auto_reject_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=5.0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Unter diesem Wert: automatische Ablehnung"
    )
    
    hard_block_severity = models.IntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Issues mit dieser Severity blockieren Gate"
    )
    max_open_blockers = models.IntegerField(
        default=0,
        help_text="Max erlaubte offene Blocker für Freigabe"
    )
    
    require_manual_approval = models.BooleanField(
        default=False,
        help_text="Immer manuelle Freigabe erforderlich"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'writing_project_quality_configs'
        verbose_name = 'Project Quality Config'
        verbose_name_plural = 'Project Quality Configs'

    def __str__(self):
        return f"Quality Config für {self.project}"


class ProjectDimensionThreshold(models.Model):
    """
    Schwellenwert pro Dimension pro Projekt.
    
    Flexibel erweiterbar ohne Schema-Änderung.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    config = models.ForeignKey(
        ProjectQualityConfig,
        on_delete=models.CASCADE,
        related_name='dimension_thresholds'
    )
    dimension = models.ForeignKey(
        QualityDimension,
        on_delete=models.CASCADE,
        related_name='project_thresholds'
    )
    min_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=7.0,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    is_blocking = models.BooleanField(
        default=True,
        help_text="Unter min_score blockiert Gate"
    )

    class Meta:
        db_table = 'writing_project_dimension_thresholds'
        unique_together = ['config', 'dimension']
        verbose_name = 'Project Dimension Threshold'
        verbose_name_plural = 'Project Dimension Thresholds'

    def __str__(self):
        return f"{self.dimension.code} >= {self.min_score}"


# =============================================================================
# SERIES MEMORY (Canon & Promises)
# =============================================================================


class CanonFact(models.Model):
    """
    Kanonische Fakten der Serienwelt.
    
    Key-Value Store für etablierte Wahrheiten.
    Hierarchischer Key (z.B. "character.mara.homeworld").
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='canon_facts'
    )
    
    fact_key = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Hierarchischer Key: 'character.name.attribute'"
    )
    fact_value = models.JSONField(
        help_text="Wert als JSON (String, Number, Object, Array)"
    )
    
    introduced_chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='introduced_facts',
        help_text="Kapitel in dem der Fakt etabliert wurde"
    )
    
    confidence = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="1.0 = sicher, 0.5 = vage/angedeutet"
    )
    
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Kategorisierung: ['worldbuilding', 'character', ...]"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="False = Fakt wurde später widerlegt/geändert"
    )
    superseded_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supersedes',
        help_text="Neuerer Fakt der diesen ersetzt"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'writing_canon_facts'
        unique_together = ['project', 'fact_key']
        indexes = [
            models.Index(fields=['project', 'fact_key']),
            models.Index(fields=['project', 'is_active']),
        ]
        verbose_name = 'Canon Fact'
        verbose_name_plural = 'Canon Facts'

    def __str__(self):
        return f"{self.fact_key}: {self.fact_value}"


class StoryPromise(models.Model):
    """
    Hooks & Payoffs über die Serie.
    
    Zentrales Tracking für Langbogen.
    Ein Promise ist eine offene Frage/Hook die später eingelöst werden muss.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='story_promises'
    )
    
    promise_key = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Eindeutiger Key: 'who_destroyed_station'"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    status = models.ForeignKey(
        PromiseStatus,
        on_delete=models.PROTECT,
        related_name='promises'
    )
    
    introduced_chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='introduced_promises',
        help_text="Kapitel in dem der Hook eingeführt wurde"
    )
    
    paid_chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paid_promises',
        help_text="Kapitel in dem der Hook eingelöst wurde"
    )
    
    priority = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1=Haupt-Plot, 5=Minor Detail"
    )
    
    tags = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'writing_story_promises'
        unique_together = ['project', 'promise_key']
        ordering = ['priority', 'introduced_chapter__chapter_number', 'title']
        verbose_name = 'Story Promise'
        verbose_name_plural = 'Story Promises'

    def __str__(self):
        return f"{self.title} [{self.status.code}]"


# =============================================================================
# STYLE ISSUES (Stil-Probleme)
# =============================================================================


class StyleIssueType(models.Model):
    """
    Lookup: Stil-Problem-Typen.
    
    Beispiele: taboo_word, passive_voice, repetition, dont_violation
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name_de = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    severity = models.IntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="1=info, 2=warning, 3=error, 4=blocker"
    )
    auto_fixable = models.BooleanField(
        default=False,
        help_text="Kann automatisch korrigiert werden"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'writing_style_issue_types'
        ordering = ['sort_order', 'severity', 'code']
        verbose_name = 'Style Issue Type'
        verbose_name_plural = 'Style Issue Types'

    def __str__(self):
        return f"{self.name_de} (Severity {self.severity})"


class StyleIssue(models.Model):
    """
    Gefundene Stil-Probleme in einem Kapitel.
    
    Verknüpft mit ChapterQualityScore und StyleIssueType.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    quality_score = models.ForeignKey(
        ChapterQualityScore,
        on_delete=models.CASCADE,
        related_name='style_issues'
    )
    issue_type = models.ForeignKey(
        StyleIssueType,
        on_delete=models.PROTECT,
        related_name='issues'
    )
    
    text_excerpt = models.TextField(
        help_text="Original-Text mit dem Problem"
    )
    line_number = models.IntegerField(
        null=True, blank=True,
        help_text="Zeile im Kapiteltext"
    )
    char_position = models.IntegerField(
        null=True, blank=True,
        help_text="Zeichenposition im Text"
    )
    
    suggestion = models.TextField(
        blank=True,
        help_text="Vorgeschlagene Korrektur"
    )
    explanation = models.TextField(
        blank=True,
        help_text="Erklärung warum es ein Problem ist"
    )
    
    is_fixed = models.BooleanField(default=False)
    fixed_at = models.DateTimeField(null=True, blank=True)
    fixed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fixed_style_issues'
    )
    is_ignored = models.BooleanField(
        default=False,
        help_text="Bewusst ignoriert (false positive)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'writing_style_issues'
        ordering = ['-issue_type__severity', 'line_number']
        verbose_name = 'Style Issue'
        verbose_name_plural = 'Style Issues'

    def __str__(self):
        status = "✓" if self.is_fixed else "✗" if self.is_ignored else "○"
        return f"{status} {self.issue_type.code}: {self.text_excerpt[:50]}..."


# =============================================================================
# PROMISE TRACKING
# =============================================================================


class PromiseEvent(models.Model):
    """
    Event-Log für Promise-Lifecycle.
    
    Trackt jede Interaktion mit einem Promise:
    introduce, reinforce, twist, partial_payoff, payoff, close
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    promise = models.ForeignKey(
        StoryPromise,
        on_delete=models.CASCADE,
        related_name='events'
    )
    chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.CASCADE,
        related_name='promise_events'
    )
    
    event_type = models.CharField(
        max_length=30,
        db_index=True,
        help_text="introduce, reinforce, twist, partial_payoff, payoff, close"
    )
    note = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'writing_promise_events'
        ordering = ['chapter__chapter_number', 'created_at']
        verbose_name = 'Promise Event'
        verbose_name_plural = 'Promise Events'

    def __str__(self):
        return f"{self.event_type} @ Ch.{self.chapter.chapter_number}"
