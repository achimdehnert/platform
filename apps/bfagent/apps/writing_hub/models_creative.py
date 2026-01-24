"""
Creative Agent System - Kreativ-Phase für Buchideen
====================================================

Interaktives Brainstorming VOR Projektanlage.
Hilft Autoren, vage Ideen zu konkreten Buchkonzepten zu entwickeln.

Workflow:
1. User startet Session mit vager Idee/Genre
2. Kreativagent generiert 3-5 Buchideen (Skizzen)
3. User wählt/verfeinert → Agent vertieft
4. User klickt "Premise generieren" → Detaillierte Premise
5. User zufrieden → Projekt anlegen mit Premise

Naming Convention: writing_* Präfix für alle Tabellen.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class CreativeSession(models.Model):
    """
    Eine Kreativ-Brainstorming-Session.
    
    Ermöglicht interaktives Entwickeln von Buchideen
    bevor ein Projekt angelegt wird.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # ===== ZUORDNUNG =====
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='creative_sessions'
    )
    
    style_dna = models.ForeignKey(
        'writing_hub.AuthorStyleDNA',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='creative_sessions',
        help_text="Optional: Style DNA für passende Ideen"
    )
    
    llm = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='creative_sessions',
        help_text="LLM für diese Kreativ-Session"
    )
    
    # ===== SESSION INFO =====
    name = models.CharField(
        max_length=200,
        help_text="Session-Name, z.B. 'Thriller-Ideen Januar 2026'"
    )
    
    initial_input = models.TextField(
        blank=True,
        help_text="Initiale Idee/Inspiration des Users"
    )
    
    preferred_genres = models.JSONField(
        default=list,
        help_text="Bevorzugte Genres, z.B. ['Thriller', 'SciFi']"
    )
    
    constraints = models.JSONField(
        default=dict,
        help_text="Einschränkungen: target_length, target_audience, etc."
    )
    
    # ===== PHASE TRACKING =====
    class Phase(models.TextChoices):
        BRAINSTORM = 'brainstorm', 'Brainstorming'
        REFINING = 'refining', 'Idee verfeinern'
        PREMISE = 'premise', 'Premise erstellen'
        COMPLETED = 'completed', 'Abgeschlossen'
        CANCELLED = 'cancelled', 'Abgebrochen'
    
    current_phase = models.CharField(
        max_length=20,
        choices=Phase.choices,
        default=Phase.BRAINSTORM
    )
    
    # ===== RESULT =====
    selected_idea = models.ForeignKey(
        'BookIdea',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='selected_in_sessions',
        help_text="Die ausgewählte Idee für Projekt-Erstellung"
    )
    
    created_project = models.ForeignKey(
        'writing_hub.BookProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='creative_sessions',
        help_text="Das aus dieser Session erstellte Projekt"
    )
    
    # ===== TIMESTAMPS =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'writing_creative_sessions'
        verbose_name = 'Creative Session'
        verbose_name_plural = 'Creative Sessions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.current_phase})"
    
    def complete(self):
        """Mark session as completed."""
        self.current_phase = self.Phase.COMPLETED
        self.completed_at = timezone.now()
        self.save()


class BookIdea(models.Model):
    """
    Eine generierte Buchidee innerhalb einer Session.
    
    Startet als Skizze, kann zu voller Premise ausgebaut werden.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    session = models.ForeignKey(
        CreativeSession,
        on_delete=models.CASCADE,
        related_name='ideas'
    )
    
    # ===== IDEE-KERN (Skizze) =====
    title_sketch = models.CharField(
        max_length=200,
        help_text="Arbeitstitel der Idee"
    )
    
    hook = models.TextField(
        help_text="Der 'Hook' - was macht die Idee spannend? (1-2 Sätze)"
    )
    
    genre = models.CharField(
        max_length=100,
        blank=True,
        help_text="Haupt-Genre"
    )
    
    setting_sketch = models.TextField(
        blank=True,
        help_text="Setting-Beschreibung"
    )
    
    protagonist_sketch = models.TextField(
        blank=True,
        help_text="Protagonist-Beschreibung"
    )
    
    conflict_sketch = models.TextField(
        blank=True,
        help_text="Zentraler Konflikt"
    )
    
    # ===== VOLLE PREMISE (auf Anforderung) =====
    has_full_premise = models.BooleanField(default=False)
    
    full_premise = models.TextField(
        blank=True,
        help_text="Ausführliche Premise (2-3 Absätze)"
    )
    
    themes = models.JSONField(
        default=list,
        help_text="Identifizierte Themen"
    )
    
    unique_selling_points = models.JSONField(
        default=list,
        help_text="Was macht diese Geschichte einzigartig?"
    )
    
    # ===== USER FEEDBACK =====
    class Rating(models.TextChoices):
        UNRATED = 'unrated', 'Nicht bewertet'
        LOVE = 'love', '❤️ Liebe es'
        LIKE = 'like', '👍 Gefällt mir'
        MAYBE = 'maybe', '🤔 Vielleicht'
        DISLIKE = 'dislike', '👎 Nicht so'
    
    user_rating = models.CharField(
        max_length=20,
        choices=Rating.choices,
        default=Rating.UNRATED
    )
    
    user_notes = models.TextField(
        blank=True,
        help_text="Notizen/Feedback des Users"
    )
    
    # ===== REFINEMENT =====
    refinement_count = models.PositiveIntegerField(default=0)
    refinement_history = models.JSONField(
        default=list,
        help_text="Historie der Verfeinerungen"
    )
    
    # ===== EXTRACTED CHARACTERS & WORLD =====
    characters_data = models.JSONField(
        default=list,
        help_text="Extrahierte Charaktere [{name, role, description, motivation}]"
    )
    
    world_data = models.JSONField(
        default=dict,
        help_text="Extrahierte Welt {name, description, key_features, atmosphere}"
    )
    
    # ===== METADATA =====
    generation_order = models.PositiveIntegerField(
        default=0,
        help_text="Reihenfolge der Generierung"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_book_ideas'
        verbose_name = 'Book Idea'
        verbose_name_plural = 'Book Ideas'
        ordering = ['session', 'generation_order']
    
    def __str__(self):
        return f"{self.title_sketch} ({self.user_rating})"


class CreativeMessage(models.Model):
    """
    Chat-Nachricht in einer Creative Session.
    Ermöglicht interaktiven Dialog mit dem Kreativagenten.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    session = models.ForeignKey(
        CreativeSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    # ===== SENDER =====
    class Sender(models.TextChoices):
        USER = 'user', 'User'
        AGENT = 'agent', 'Kreativagent'
        SYSTEM = 'system', 'System'
    
    sender = models.CharField(
        max_length=20,
        choices=Sender.choices
    )
    
    # ===== CONTENT =====
    content = models.TextField(
        help_text="Nachrichteninhalt"
    )
    
    # ===== MESSAGE TYPE =====
    class MessageType(models.TextChoices):
        TEXT = 'text', 'Text'
        IDEAS = 'ideas', 'Ideen-Liste'
        PREMISE = 'premise', 'Premise'
        QUESTION = 'question', 'Rückfrage'
        ACTION = 'action', 'Aktion'
    
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT
    )
    
    # ===== LINKED DATA =====
    linked_ideas = models.ManyToManyField(
        BookIdea,
        blank=True,
        related_name='messages',
        help_text="Mit dieser Nachricht verknüpfte Ideen"
    )
    
    metadata = models.JSONField(
        default=dict,
        help_text="Zusätzliche Daten (LLM usage, etc.)"
    )
    
    # ===== TIMESTAMP =====
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_creative_messages'
        verbose_name = 'Creative Message'
        verbose_name_plural = 'Creative Messages'
        ordering = ['session', 'created_at']
    
    def __str__(self):
        return f"[{self.sender}] {self.content[:50]}..."
