# ============================================================================
# DOMAIN DEVELOPMENT LIFECYCLE - DJANGO MODELS
# Step 2: Django Models for Business Cases, Use Cases, ADRs
# ============================================================================
#
# Part of: Domain Development Lifecycle System
# Compatible with: ADR-015 Platform Governance System
# Location: platform/governance/models/domain_models.py
#
# ============================================================================

"""
Django Models für das Domain Development Lifecycle System.

Diese Models bilden die dom_* Tabellen ab und integrieren sich
mit dem ADR-015 Lookup-System (lkp_choice).

Usage:
    from governance.models import BusinessCase, UseCase, ADR
    
    # Neuen Business Case erstellen
    bc = BusinessCase.objects.create(
        title="Reisekostenabrechnung",
        problem_statement="Manuelle Erfassung ist zeitaufwändig",
        category=LookupService.get_choice('bc_category', 'neue_domain'),
    )
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models import Q, QuerySet
from django.utils import timezone

if TYPE_CHECKING:
    from django.contrib.auth.models import User


# ============================================================================
# SECTION 1: ABSTRACT BASE MODELS
# ============================================================================

class TimestampedModel(models.Model):
    """
    Abstract base model mit Timestamps und Soft Delete.
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Erstellt am",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Aktualisiert am",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Gelöscht am",
    )

    class Meta:
        abstract = True

    def soft_delete(self) -> None:
        """Soft delete - setzt deleted_at."""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self) -> None:
        """Stellt soft-deleted Objekt wieder her."""
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_deleted(self) -> bool:
        """Prüft ob Objekt soft-deleted ist."""
        return self.deleted_at is not None


class ActiveManager(models.Manager):
    """
    Manager der nur nicht-gelöschte Objekte zurückgibt.
    """
    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(deleted_at__isnull=True)


class SearchableModel(TimestampedModel):
    """
    Abstract base model mit Full-Text Search Support.
    """
    search_vector = SearchVectorField(
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


# ============================================================================
# SECTION 2: BUSINESS CASE MODEL
# ============================================================================

class BusinessCase(SearchableModel):
    """
    Business Case - Einstiegspunkt für Domain Development Lifecycle.
    
    Ein Business Case beschreibt ein Geschäftsproblem und dessen
    erwartete Lösung. Aus einem BC werden Use Cases abgeleitet.
    
    Attributes:
        code: Eindeutiger Code (BC-001, BC-002, ...)
        title: Kurztitel des Business Cases
        category: Kategorie (neue_domain, integration, ...)
        status: Aktueller Status im Workflow
        problem_statement: Beschreibung des Problems
        ...
    
    Example:
        bc = BusinessCase.objects.create(
            title="Automatisierte Reisekostenabrechnung",
            problem_statement="Manuelle Erfassung dauert zu lange",
            category_id=LookupService.get_choice_id('bc_category', 'neue_domain'),
            status_id=LookupService.get_choice_id('bc_status', 'draft'),
        )
    """
    
    # Identification
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Code",
        help_text="Eindeutiger Code (BC-001, BC-002, ...)",
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Titel",
    )
    
    # Classification (FK to lkp_choice)
    category = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.PROTECT,
        related_name='business_cases_by_category',
        verbose_name="Kategorie",
        limit_choices_to={'domain__code': 'bc_category'},
    )
    status = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.PROTECT,
        related_name='business_cases_by_status',
        verbose_name="Status",
        limit_choices_to={'domain__code': 'bc_status'},
    )
    
    # Core Content
    problem_statement = models.TextField(
        verbose_name="Problembeschreibung",
        help_text="Was ist das Problem, das gelöst werden soll?",
    )
    target_audience = models.TextField(
        blank=True,
        verbose_name="Zielgruppe",
        help_text="Wer sind die Nutzer/Betroffenen?",
    )
    expected_benefits = models.TextField(
        blank=True,
        verbose_name="Erwarteter Nutzen",
        help_text="Welcher Nutzen wird erwartet?",
    )
    scope = models.TextField(
        blank=True,
        verbose_name="Scope",
        help_text="Was ist Teil des Projekts?",
    )
    out_of_scope = models.TextField(
        blank=True,
        verbose_name="Out of Scope",
        help_text="Was ist explizit NICHT Teil des Projekts?",
    )
    
    # Structured Data (JSONField)
    success_criteria = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Erfolgskriterien",
        help_text='Liste der Erfolgskriterien ["Kriterium 1", ...]',
    )
    assumptions = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Annahmen",
    )
    constraints = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Einschränkungen",
    )
    risks = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Risiken",
        help_text='[{"risk": "...", "mitigation": "..."}]',
    )
    stakeholders = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Stakeholder",
        help_text='[{"name": "...", "role": "..."}]',
    )
    
    # Inception Tracking
    original_input = models.TextField(
        blank=True,
        verbose_name="Ursprüngliche Eingabe",
        help_text="Der ursprüngliche Freitext vom Benutzer",
    )
    inception_session_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="Inception Session ID",
    )
    inception_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Inception abgeschlossen am",
    )
    
    # Architecture Basis
    architecture_basis = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Architektur-Basis",
        help_text='{"database": "postgresql", "backend": "django", ...}',
    )
    
    # Ownership
    owner = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_business_cases',
        verbose_name="Owner",
    )
    team_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="Team ID",
    )
    
    # Domain Context
    domain_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="Domain ID",
    )
    
    # Managers
    objects = ActiveManager()
    all_objects = models.Manager()
    
    class Meta:
        db_table = 'platform"."dom_business_case'
        verbose_name = "Business Case"
        verbose_name_plural = "Business Cases"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['owner']),
            GinIndex(fields=['search_vector']),
        ]

    def __str__(self) -> str:
        return f"{self.code}: {self.title}"

    def save(self, *args, **kwargs) -> None:
        # Auto-generate code if not set
        if not self.code:
            self.code = self._generate_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_code() -> str:
        """Generiert den nächsten BC-Code."""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT platform.next_code('BC', 'seq_business_case_code')")
            return cursor.fetchone()[0]

    @property
    def use_case_count(self) -> int:
        """Anzahl der zugehörigen Use Cases."""
        return self.use_cases.count()

    @property
    def adr_count(self) -> int:
        """Anzahl der zugehörigen ADRs."""
        return self.adrs.count()

    @property
    def is_editable(self) -> bool:
        """Prüft ob BC bearbeitet werden kann."""
        return self.status.metadata.get('editable', False)

    @property
    def allowed_transitions(self) -> list[str]:
        """Liste der erlaubten Status-Übergänge."""
        return self.status.metadata.get('transitions', [])

    def can_transition_to(self, new_status_code: str) -> bool:
        """Prüft ob Übergang zu neuem Status erlaubt ist."""
        return new_status_code in self.allowed_transitions

    def transition_to(self, new_status_code: str, user: Optional['User'] = None, reason: str = "") -> None:
        """
        Führt Status-Übergang durch.
        
        Args:
            new_status_code: Ziel-Status Code
            user: Benutzer der den Übergang durchführt
            reason: Grund für den Übergang
            
        Raises:
            ValueError: Wenn Übergang nicht erlaubt
        """
        if not self.can_transition_to(new_status_code):
            raise ValueError(
                f"Übergang von '{self.status.code}' zu '{new_status_code}' nicht erlaubt. "
                f"Erlaubt: {self.allowed_transitions}"
            )
        
        from governance.services import LookupService
        
        old_status = self.status
        new_status = LookupService.get_choice('bc_status', new_status_code)
        
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        
        # Status History erstellen
        StatusHistory.objects.create(
            entity_type='business_case',
            entity_id=self.id,
            old_status=old_status,
            new_status=new_status,
            changed_by=user,
            reason=reason,
        )


# ============================================================================
# SECTION 3: USE CASE MODEL
# ============================================================================

class UseCase(SearchableModel):
    """
    Use Case - Funktionale Anforderung abgeleitet aus Business Case.
    
    Ein Use Case beschreibt eine konkrete Interaktion zwischen
    einem Akteur und dem System.
    
    Attributes:
        code: Eindeutiger Code (UC-001, UC-002, ...)
        business_case: Zugehöriger Business Case
        title: Kurztitel des Use Cases
        actor: Primärer Akteur
        main_flow: Hauptablauf als strukturierte Liste
        ...
    """
    
    # Identification
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Code",
    )
    business_case = models.ForeignKey(
        BusinessCase,
        on_delete=models.CASCADE,
        related_name='use_cases',
        verbose_name="Business Case",
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Titel",
    )
    
    # Classification
    status = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.PROTECT,
        related_name='use_cases_by_status',
        verbose_name="Status",
        limit_choices_to={'domain__code': 'uc_status'},
    )
    priority = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.PROTECT,
        related_name='use_cases_by_priority',
        verbose_name="Priorität",
        limit_choices_to={'domain__code': 'uc_priority'},
    )
    complexity = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='use_cases_by_complexity',
        verbose_name="Komplexität",
        limit_choices_to={'domain__code': 'uc_complexity'},
    )
    
    # Core Content
    description = models.TextField(
        blank=True,
        verbose_name="Beschreibung",
    )
    actor = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Akteur",
        help_text="Primärer Akteur (z.B. 'Mitarbeiter', 'Administrator')",
    )
    preconditions = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Vorbedingungen",
    )
    postconditions = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Nachbedingungen",
    )
    business_rules = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Geschäftsregeln",
    )
    
    # Flows
    main_flow = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Hauptablauf",
        help_text='[{"step": 1, "type": "user_action", "description": "..."}]',
    )
    alternative_flows = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Alternative Abläufe",
    )
    exception_flows = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Ausnahme-Abläufe",
    )
    
    # UI/UX
    ui_mockup_url = models.URLField(
        blank=True,
        verbose_name="UI Mockup URL",
    )
    ui_notes = models.TextField(
        blank=True,
        verbose_name="UI Notizen",
    )
    
    # Technical
    technical_notes = models.TextField(
        blank=True,
        verbose_name="Technische Notizen",
    )
    api_endpoints = models.JSONField(
        default=list,
        blank=True,
        verbose_name="API Endpoints",
    )
    
    # Estimation
    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Geschätzte Stunden",
    )
    actual_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Tatsächliche Stunden",
    )
    
    # Dependencies
    depends_on = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Abhängigkeiten",
        help_text='[{"use_case_id": 1, "type": "requires"}]',
    )
    
    # Ordering
    sort_order = models.IntegerField(
        default=0,
        verbose_name="Sortierung",
    )
    
    # Managers
    objects = ActiveManager()
    all_objects = models.Manager()
    
    class Meta:
        db_table = 'platform"."dom_use_case'
        verbose_name = "Use Case"
        verbose_name_plural = "Use Cases"
        ordering = ['business_case', 'sort_order', 'code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['business_case']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            GinIndex(fields=['search_vector']),
        ]

    def __str__(self) -> str:
        return f"{self.code}: {self.title}"

    def save(self, *args, **kwargs) -> None:
        if not self.code:
            self.code = self._generate_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_code() -> str:
        """Generiert den nächsten UC-Code."""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT platform.next_code('UC', 'seq_use_case_code')")
            return cursor.fetchone()[0]

    @property
    def story_points(self) -> Optional[int]:
        """Story Points basierend auf Komplexität."""
        if self.complexity and self.complexity.metadata:
            return self.complexity.metadata.get('story_points')
        return None

    @property
    def main_flow_step_count(self) -> int:
        """Anzahl der Schritte im Hauptablauf."""
        return len(self.main_flow) if self.main_flow else 0

    def get_dependencies(self) -> QuerySet['UseCase']:
        """Gibt abhängige Use Cases zurück."""
        if not self.depends_on:
            return UseCase.objects.none()
        
        dep_ids = [d['use_case_id'] for d in self.depends_on if 'use_case_id' in d]
        return UseCase.objects.filter(id__in=dep_ids)


# ============================================================================
# SECTION 4: ADR MODEL
# ============================================================================

class ADR(SearchableModel):
    """
    Architecture Decision Record - Dokumentiert Architekturentscheidungen.
    
    Ein ADR beschreibt eine wichtige Architekturentscheidung,
    deren Kontext, Alternativen und Konsequenzen.
    
    Attributes:
        code: Eindeutiger Code (ADR-001, ADR-002, ...)
        title: Titel der Entscheidung
        context: Warum ist diese Entscheidung nötig?
        decision: Was wurde entschieden?
        consequences: Was sind die Konsequenzen?
        ...
    """
    
    # Identification
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Code",
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Titel",
    )
    
    # Classification
    status = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.PROTECT,
        related_name='adrs_by_status',
        verbose_name="Status",
        limit_choices_to={'domain__code': 'adr_status'},
    )
    
    # Relationships
    business_case = models.ForeignKey(
        BusinessCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adrs',
        verbose_name="Business Case",
    )
    supersedes = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='superseded_by',
        verbose_name="Ersetzt ADR",
    )
    
    # ADR Content (Classic Format)
    context = models.TextField(
        verbose_name="Kontext",
        help_text="Warum ist diese Entscheidung nötig?",
    )
    decision = models.TextField(
        verbose_name="Entscheidung",
        help_text="Was wurde entschieden?",
    )
    consequences = models.TextField(
        blank=True,
        verbose_name="Konsequenzen",
        help_text="Was sind die positiven und negativen Konsequenzen?",
    )
    
    # Extended Content
    alternatives = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Alternativen",
        help_text='[{"name": "...", "pros": [...], "cons": [...], "score": 7}]',
    )
    decision_drivers = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Entscheidungstreiber",
    )
    
    # Technical Details
    affected_components = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Betroffene Komponenten",
    )
    implementation_notes = models.TextField(
        blank=True,
        verbose_name="Implementierungshinweise",
    )
    
    # Review & Approval
    reviewers = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Reviewer",
        help_text='[{"user_id": 1, "approved": true, "date": "..."}]',
    )
    decision_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Entscheidungsdatum",
    )
    review_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Review-Datum",
    )
    
    # Managers
    objects = ActiveManager()
    all_objects = models.Manager()
    
    class Meta:
        db_table = 'platform"."dom_adr'
        verbose_name = "ADR"
        verbose_name_plural = "ADRs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status']),
            models.Index(fields=['business_case']),
            GinIndex(fields=['search_vector']),
        ]

    def __str__(self) -> str:
        return f"{self.code}: {self.title}"

    def save(self, *args, **kwargs) -> None:
        if not self.code:
            self.code = self._generate_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_code() -> str:
        """Generiert den nächsten ADR-Code."""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT platform.next_code('ADR', 'seq_adr_code')")
            return cursor.fetchone()[0]

    @property
    def status_badge(self) -> Optional[str]:
        """Badge für Anzeige (ACCEPTED, REJECTED, etc.)."""
        if self.status and self.status.metadata:
            return self.status.metadata.get('badge')
        return None

    def get_use_cases(self) -> QuerySet[UseCase]:
        """Gibt verknüpfte Use Cases zurück."""
        return UseCase.objects.filter(
            id__in=self.use_case_links.values_list('use_case_id', flat=True)
        )


# ============================================================================
# SECTION 5: CONVERSATION MODEL
# ============================================================================

class Conversation(models.Model):
    """
    Inception Dialog - Speichert den Q&A Dialog während der BC-Erstellung.
    
    Jede Nachricht im Inception-Prozess wird hier gespeichert,
    um Nachvollziehbarkeit zu gewährleisten.
    """
    
    # Context
    business_case = models.ForeignKey(
        BusinessCase,
        on_delete=models.CASCADE,
        related_name='conversations',
        verbose_name="Business Case",
    )
    session_id = models.UUIDField(
        verbose_name="Session ID",
    )
    
    # Message
    turn_number = models.IntegerField(
        verbose_name="Turn Nummer",
    )
    role = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.PROTECT,
        related_name='conversations_by_role',
        verbose_name="Rolle",
        limit_choices_to={'domain__code': 'conversation_role'},
    )
    message = models.TextField(
        verbose_name="Nachricht",
    )
    
    # Agent-specific data
    extracted_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Extrahierte Daten",
    )
    next_question = models.TextField(
        blank=True,
        verbose_name="Nächste Frage",
    )
    question_context = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Frage-Kontext",
        help_text="Welches Feld betrifft diese Frage?",
    )
    
    # Metadata
    tokens_used = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Tokens verwendet",
    )
    model_used = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Verwendetes Modell",
    )
    processing_time_ms = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Verarbeitungszeit (ms)",
    )
    
    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Erstellt am",
    )
    
    class Meta:
        db_table = 'platform"."dom_conversation'
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ['session_id', 'turn_number']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['business_case']),
            models.Index(fields=['session_id', 'turn_number']),
        ]

    def __str__(self) -> str:
        return f"Turn {self.turn_number} ({self.role.code})"


# ============================================================================
# SECTION 6: LINK TABLES
# ============================================================================

class ADRUseCaseLink(models.Model):
    """
    Verknüpfung zwischen ADR und Use Case.
    
    Beziehungstypen werden aus lkp_choice geladen (domain='adr_uc_relationship').
    Verfügbare Typen: implements, affects, references
    """
    
    # KEINE hardcoded RELATIONSHIP_TYPES - ADR-015 konform!
    # Typen kommen aus: platform.lkp_choice WHERE domain='adr_uc_relationship'
    
    adr = models.ForeignKey(
        ADR,
        on_delete=models.CASCADE,
        related_name='use_case_links',
        verbose_name="ADR",
    )
    use_case = models.ForeignKey(
        UseCase,
        on_delete=models.CASCADE,
        related_name='adr_links',
        verbose_name="Use Case",
    )
    relationship_type = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.PROTECT,
        related_name='adr_use_case_links',
        verbose_name="Beziehungstyp",
        limit_choices_to={'domain__code': 'adr_uc_relationship'},
        help_text="Typ der Beziehung (implements, affects, references)",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notizen",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Erstellt am",
    )
    
    class Meta:
        db_table = 'platform"."dom_adr_use_case'
        verbose_name = "ADR-Use Case Verknüpfung"
        verbose_name_plural = "ADR-Use Case Verknüpfungen"
        unique_together = [['adr', 'use_case']]

    def __str__(self) -> str:
        return f"{self.adr.code} → {self.use_case.code} ({self.relationship_type})"


# ============================================================================
# SECTION 7: REVIEW & AUDIT MODELS
# ============================================================================

class Review(models.Model):
    """
    Review - Genehmigungsworkflow für BC, UC, ADR.
    
    Entity-Typen und Entscheidungen aus lkp_choice (ADR-015 konform).
    - entity_type: domain='review_entity_type'
    - decision: domain='review_decision'
    """
    
    # KEINE hardcoded ENTITY_TYPES oder DECISIONS - ADR-015 konform!
    # Typen kommen aus: platform.lkp_choice
    
    # What is being reviewed
    entity_type = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.PROTECT,
        related_name='reviews_by_entity_type',
        verbose_name="Entity-Typ",
        limit_choices_to={'domain__code': 'review_entity_type'},
        help_text="business_case, use_case, oder adr",
    )
    entity_id = models.BigIntegerField(
        verbose_name="Entity ID",
    )
    
    # Reviewer
    reviewer = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Reviewer",
    )
    
    # Review Content
    decision = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.PROTECT,
        related_name='reviews_by_decision',
        verbose_name="Entscheidung",
        limit_choices_to={'domain__code': 'review_decision'},
        help_text="approved, rejected, oder changes_requested",
    )
    comments = models.TextField(
        blank=True,
        verbose_name="Kommentare",
    )
    requested_changes = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Angeforderte Änderungen",
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Erstellt am",
    )
    
    class Meta:
        db_table = 'platform"."dom_review'
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['reviewer']),
        ]

    def __str__(self) -> str:
        return f"Review {self.entity_type}:{self.entity_id} by {self.reviewer}"

    def get_entity(self) -> Optional[models.Model]:
        """Gibt das reviewte Objekt zurück."""
        entity_code = self.entity_type.code if self.entity_type else None
        if entity_code == 'business_case':
            return BusinessCase.objects.filter(id=self.entity_id).first()
        elif entity_code == 'use_case':
            return UseCase.objects.filter(id=self.entity_id).first()
        elif entity_code == 'adr':
            return ADR.objects.filter(id=self.entity_id).first()
        return None


class StatusHistory(models.Model):
    """
    Status History - Audit Trail für Status-Änderungen.
    
    Entity-Typen aus lkp_choice (ADR-015 konform).
    - entity_type: domain='review_entity_type' (gleiche Domain wie Review)
    """
    
    # KEINE hardcoded ENTITY_TYPES - ADR-015 konform!
    # Typen kommen aus: platform.lkp_choice WHERE domain='review_entity_type'
    
    # What changed
    entity_type = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.PROTECT,
        related_name='status_history_by_entity_type',
        verbose_name="Entity-Typ",
        limit_choices_to={'domain__code': 'review_entity_type'},
        help_text="business_case, use_case, oder adr",
    )
    entity_id = models.BigIntegerField(
        verbose_name="Entity ID",
    )
    
    # Status Change
    old_status = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_history_old',
        verbose_name="Alter Status",
    )
    new_status = models.ForeignKey(
        'governance.LookupChoice',
        on_delete=models.PROTECT,
        related_name='status_history_new',
        verbose_name="Neuer Status",
    )
    
    # Who and Why
    changed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_changes',
        verbose_name="Geändert von",
    )
    reason = models.TextField(
        blank=True,
        verbose_name="Grund",
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Erstellt am",
    )
    
    class Meta:
        db_table = 'platform"."dom_status_history'
        verbose_name = "Status History"
        verbose_name_plural = "Status Histories"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        old = self.old_status.code if self.old_status else 'None'
        return f"{self.entity_type}:{self.entity_id} {old} → {self.new_status.code}"


# ============================================================================
# SECTION 8: MODEL EXPORTS
# ============================================================================

__all__ = [
    'BusinessCase',
    'UseCase',
    'ADR',
    'Conversation',
    'ADRUseCaseLink',
    'Review',
    'StatusHistory',
]
