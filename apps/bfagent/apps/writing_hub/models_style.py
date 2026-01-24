"""
Style Generation & Adoption System (SGAS) Models
=================================================

Systematischer, datenbankgetriebener Prozess für:
- Autorenindividuelle Stile generieren
- Stile validieren, fixieren und versionieren
- Autoren Stile übernehmen lassen
- Produktions-LLMs konsistent im Stil schreiben

Kernprinzip: Stil ist ein Produkt, kein Prompt.

Naming Convention: writing_* Präfix für alle Tabellen.
"""

import uuid
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# =============================================================================
# AUTHOR STYLE DNA (Persönlicher Stil, projektübergreifend)
# =============================================================================

class AuthorStyleDNA(models.Model):
    """
    Persönliches Stilprofil eines Autors.
    Projektübergreifend - definiert "was macht diesen Autor aus".
    
    Wächst mit jedem Projekt und Feedback.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='style_dnas'
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Name des Stils, z.B. 'Mein Hauptstil', 'Thriller-Stil'"
    )
    
    version = models.PositiveIntegerField(default=1)
    
    is_primary = models.BooleanField(
        default=False,
        help_text="Hauptstil des Autors"
    )
    
    # ===== SIGNATURE MOVES =====
    signature_moves = models.JSONField(
        default=list,
        help_text="Was macht diesen Stil einzigartig? z.B. ['entlarvende Metaphern', 'knappe Absätze']"
    )
    
    # ===== DO / DON'T LISTS =====
    do_list = models.JSONField(
        default=list,
        help_text="Was der Stil tun soll, z.B. ['konkrete Verben verwenden', 'Subtext vor Erklärung']"
    )
    
    dont_list = models.JSONField(
        default=list,
        help_text="Was der Stil vermeiden soll, z.B. ['abstrakte Emotionslabels', 'Pathos']"
    )
    
    taboo_list = models.JSONField(
        default=list,
        help_text="Absolut verbotene Wörter/Phrasen"
    )
    
    # ===== PREFERRED LLM =====
    preferred_llm = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='style_dnas',
        help_text="Bevorzugtes LLM für diesen Stil"
    )
    
    # ===== RHYTHM TARGETS =====
    rhythm_profile = models.JSONField(
        default=dict,
        help_text="Zielwerte für Rhythmus: avg_sentence_len_range, sentence_mix (short/medium/long)"
    )
    
    # ===== LENS / POV TARGETS =====
    lens_profile = models.JSONField(
        default=dict,
        help_text="POV-Einstellungen: pov_distance (close/medium/distant), introspection_ratio_max"
    )
    
    # ===== DIALOGUE TARGETS =====
    dialogue_profile = models.JSONField(
        default=dict,
        help_text="Dialog-Stil: subtext_level (low/medium/high), tag_density_max"
    )
    
    # ===== IMAGERY =====
    imagery_profile = models.JSONField(
        default=dict,
        help_text="Bildsprache: metaphor_density, preferred_domains, sensory_anchors"
    )
    
    # ===== STATUS =====
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Entwurf'
        IN_LAB = 'in_lab', 'Im Labor'
        REVIEW = 'review', 'Zur Prüfung'
        PRODUCTION_READY = 'production_ready', 'Produktionsreif'
        ARCHIVED = 'archived', 'Archiviert'
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # ===== METADATA =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_author_style_dna'
        verbose_name = 'Author Style DNA'
        verbose_name_plural = 'Author Style DNAs'
        unique_together = ['author', 'name', 'version']
        ordering = ['author', '-is_primary', 'name']
    
    def __str__(self):
        return f"{self.author.username}: {self.name} v{self.version}"
    
    def create_new_version(self):
        """Create a new version of this style DNA"""
        new_dna = AuthorStyleDNA.objects.create(
            author=self.author,
            name=self.name,
            version=self.version + 1,
            is_primary=False,
            signature_moves=self.signature_moves.copy(),
            do_list=self.do_list.copy(),
            dont_list=self.dont_list.copy(),
            taboo_list=self.taboo_list.copy(),
            rhythm_profile=self.rhythm_profile.copy(),
            lens_profile=self.lens_profile.copy(),
            dialogue_profile=self.dialogue_profile.copy(),
            imagery_profile=self.imagery_profile.copy(),
            status=AuthorStyleDNA.Status.DRAFT
        )
        return new_dna


# =============================================================================
# STYLE LAB SESSION (Stil-Entwicklung)
# =============================================================================

class StyleLabSession(models.Model):
    """
    Eine Stil-Entwicklungs-Session im Style Lab.
    
    Phasen:
    1. EXTRACTION - Beispieltexte analysieren
    2. SYNTHESIS - Test-Szenen generieren
    3. FEEDBACK - Autor gibt Feedback
    4. FIXATION - Stil fixieren
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # ===== ZUORDNUNG =====
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='style_lab_sessions'
    )
    
    target_dna = models.ForeignKey(
        AuthorStyleDNA,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lab_sessions',
        help_text="Ziel-DNA, die entwickelt/verfeinert wird"
    )
    
    project = models.ForeignKey(
        'writing_hub.BookProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='style_lab_sessions',
        help_text="Optional: Projekt für das der Stil entwickelt wird"
    )
    
    # ===== LLM KONFIGURATION =====
    # HINWEIS: Feld wird erst nach Migration aktiv. Bis dahin: System-Default LLM.
    # SQL: ALTER TABLE writing_style_lab_sessions ADD COLUMN llm_id INTEGER NULL REFERENCES llms(id);
    # llm = models.ForeignKey(
    #     'bfagent.Llms',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='style_lab_sessions',
    #     help_text="LLM für Stil-Analyse und Generierung. Leer = System-Default (bevorzugt Ollama)"
    # )
    
    @property
    def llm(self):
        """Temporärer Fallback bis Migration angewendet wird."""
        return None
    
    @property
    def selected_ollama_model(self):
        """Extrahiert Ollama-Modellname aus Session-Name (z.B. 'test [llama3:8b]' -> 'llama3:8b')."""
        import re
        match = re.search(r'\[([^\]]+)\]', self.name)
        if match:
            return match.group(1)
        return None
    
    # ===== SESSION INFO =====
    name = models.CharField(max_length=200)
    
    purpose = models.CharField(
        max_length=20,
        choices=[
            ('new_style', 'Neuen Stil entwickeln'),
            ('adapt_existing', 'Bestehenden Stil anpassen'),
            ('hybrid', 'Stile kombinieren'),
            ('refine', 'Stil verfeinern'),
        ],
        default='new_style'
    )
    
    target_genres = models.JSONField(
        default=list,
        help_text="Ziel-Genres, z.B. ['Roman', 'Thriller', 'SciFi']"
    )
    
    # ===== PHASE TRACKING =====
    class Phase(models.TextChoices):
        INIT = 'init', 'Initialisierung'
        EXTRACTION = 'extraction', 'Stil-Extraktion'
        SYNTHESIS = 'synthesis', 'Stil-Synthese'
        FEEDBACK = 'feedback', 'Autor-Feedback'
        FIXATION = 'fixation', 'Stil-Fixierung'
        COMPLETED = 'completed', 'Abgeschlossen'
        CANCELLED = 'cancelled', 'Abgebrochen'
    
    current_phase = models.CharField(
        max_length=20,
        choices=Phase.choices,
        default=Phase.INIT
    )
    
    # ===== TIMESTAMPS =====
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'writing_style_lab_sessions'
        verbose_name = 'Style Lab Session'
        verbose_name_plural = 'Style Lab Sessions'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.name} ({self.current_phase})"


# =============================================================================
# STYLE OBSERVATION (Phase 1: Extraktion)
# =============================================================================

class StyleObservation(models.Model):
    """
    Beobachtungen aus der Stil-Analyse von Beispieltexten.
    
    LLM analysiert Texte und extrahiert Stil-Merkmale.
    Noch keine Regeln - nur Beschreibungen!
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    session = models.ForeignKey(
        StyleLabSession,
        on_delete=models.CASCADE,
        related_name='observations'
    )
    
    # ===== INPUT =====
    source_text = models.TextField(
        help_text="Analysierter Beispieltext"
    )
    
    source_type = models.CharField(
        max_length=50,
        choices=[
            ('author_sample', 'Eigener Text des Autors'),
            ('reference', 'Referenztext (Vorbild)'),
            ('anti_reference', 'Anti-Referenz (so nicht)'),
        ],
        default='author_sample'
    )
    
    source_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name/Titel des Quelltexts"
    )
    
    # ===== OBSERVATIONS (LLM Output) =====
    observations = models.JSONField(
        default=dict,
        help_text="Extrahierte Merkmale: voice, rhythm, metaphors, pov, dialogue, etc."
    )
    
    contradictions = models.JSONField(
        default=list,
        help_text="Widersprüche zu anderen Texten der Session"
    )
    
    metrics = models.JSONField(
        default=dict,
        help_text="Messbare Metriken: word_count, avg_sentence_length, dialogue_ratio, etc."
    )
    
    # ===== METADATA =====
    analyzed_at = models.DateTimeField(auto_now_add=True)
    llm_used = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'writing_style_observations'
        verbose_name = 'Style Observation'
        verbose_name_plural = 'Style Observations'
        ordering = ['session', 'analyzed_at']
    
    def __str__(self):
        return f"Observation: {self.source_name or 'Unnamed'}"


# =============================================================================
# STYLE CANDIDATE (Phase 2: Synthese)
# =============================================================================

class StyleCandidate(models.Model):
    """
    Synthese-Text: LLM schreibt im extrahierten Stil.
    
    Verschiedene Szenentypen werden generiert, um den Stil zu testen.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    session = models.ForeignKey(
        StyleLabSession,
        on_delete=models.CASCADE,
        related_name='candidates'
    )
    
    # ===== SCENE TYPE =====
    scene_type = models.CharField(
        max_length=50,
        choices=[
            ('arrival', 'Ankunft/Einführung'),
            ('dialogue', 'Dialog-Szene'),
            ('action', 'Action/Spannung'),
            ('introspection', 'Innenschau'),
            ('description', 'Beschreibung/Setting'),
            ('conflict', 'Konflikt'),
            ('resolution', 'Auflösung'),
        ]
    )
    
    scene_prompt = models.TextField(
        help_text="Szenen-Vorgabe für die Synthese"
    )
    
    # ===== GENERATED TEXT =====
    generated_text = models.TextField(
        help_text="Vom LLM generierter Text"
    )
    
    used_features = models.JSONField(
        default=list,
        help_text="Genutzte Stil-Features, z.B. ['reduced_metaphor', 'cool_observer']"
    )
    
    # ===== METADATA =====
    generated_at = models.DateTimeField(auto_now_add=True)
    llm_used = models.CharField(max_length=100, blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'writing_style_candidates'
        verbose_name = 'Style Candidate'
        verbose_name_plural = 'Style Candidates'
        ordering = ['session', 'scene_type']
    
    def __str__(self):
        return f"Candidate: {self.scene_type}"


# =============================================================================
# STYLE FEEDBACK (Phase 3: Autor-Feedback)
# =============================================================================

class SentenceFeedback(models.Model):
    """
    Satz-Level Feedback für granulare Stil-Bewertung (HTMX-basiert).
    
    Jeder Satz im Synthese-Text kann einzeln bewertet werden.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    candidate = models.ForeignKey(
        'StyleCandidate',
        on_delete=models.CASCADE,
        related_name='sentence_feedbacks'
    )
    
    sentence_index = models.PositiveIntegerField(
        help_text="0-basierter Index des Satzes im Text"
    )
    
    sentence_text = models.TextField(
        help_text="Der bewertete Satz (für Referenz)"
    )
    
    class Rating(models.TextChoices):
        ACCEPTED = 'accepted', '✅ Passt'
        PARTIAL = 'partial', '⚠️ Fast'
        REJECTED = 'rejected', '❌ Nein'
    
    rating = models.CharField(
        max_length=20,
        choices=Rating.choices
    )
    
    comment = models.TextField(
        blank=True,
        help_text="Optionaler Kommentar zum Satz"
    )
    
    pattern_tag = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optionaler Pattern-Tag, z.B. 'cool_observer', 'too_explanatory'"
    )
    
    given_at = models.DateTimeField(auto_now_add=True)
    given_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        db_table = 'writing_style_sentence_feedbacks'
        verbose_name = 'Sentence Feedback'
        verbose_name_plural = 'Sentence Feedbacks'
        ordering = ['candidate', 'sentence_index']
        unique_together = [['candidate', 'sentence_index']]
    
    def __str__(self):
        return f"Sentence {self.sentence_index}: {self.rating}"


class StyleFeedback(models.Model):
    """
    Autor-Feedback zu einem Synthese-Text (Gesamt-Bewertung).
    
    Der Autor:
    - markiert (✅ ❌ ⚠️)
    - formuliert punktuell um
    - hinterlässt Kommentare
    
    Dies ist der eigentliche Stil-Kern!
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    candidate = models.ForeignKey(
        StyleCandidate,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    
    # ===== OVERALL RATING =====
    class Rating(models.TextChoices):
        ACCEPTED = 'accepted', '✅ Akzeptiert'
        REJECTED = 'rejected', '❌ Abgelehnt'
        PARTIAL = 'partial', '⚠️ Teilweise'
    
    rating = models.CharField(
        max_length=20,
        choices=Rating.choices
    )
    
    # ===== DETAILED FEEDBACK =====
    accepted_patterns = models.JSONField(
        default=list,
        help_text="Akzeptierte Stil-Muster aus diesem Text"
    )
    
    rejected_patterns = models.JSONField(
        default=list,
        help_text="Abgelehnte Stil-Muster"
    )
    
    # ===== AUTHOR EDITS =====
    author_edits = models.JSONField(
        default=list,
        help_text="Autor-Korrekturen: [{original, edit, reason}]"
    )
    
    # ===== COMMENTS =====
    general_comment = models.TextField(
        blank=True,
        help_text="Allgemeiner Kommentar des Autors"
    )
    
    # ===== METADATA =====
    given_at = models.DateTimeField(auto_now_add=True)
    given_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        db_table = 'writing_style_feedbacks'
        verbose_name = 'Style Feedback'
        verbose_name_plural = 'Style Feedbacks'
        ordering = ['candidate', 'given_at']
    
    def __str__(self):
        return f"Feedback: {self.rating} for {self.candidate}"


# =============================================================================
# STYLE ACCEPTANCE TEST (Phase 4: Fixierung)
# =============================================================================

class StyleAcceptanceTest(models.Model):
    """
    Automatische Prüfungen für einen Stil.
    
    Definiert must_have und must_not_have Kriterien.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    style_dna = models.ForeignKey(
        AuthorStyleDNA,
        on_delete=models.CASCADE,
        related_name='acceptance_tests'
    )
    
    name = models.CharField(max_length=200)
    
    # ===== TEST TYPE =====
    class TestType(models.TextChoices):
        MUST_HAVE = 'must_have', 'Muss enthalten'
        MUST_NOT_HAVE = 'must_not_have', 'Darf nicht enthalten'
        METRIC_RANGE = 'metric_range', 'Metrik im Bereich'
        PATTERN_MATCH = 'pattern_match', 'Pattern vorhanden'
        PATTERN_ABSENT = 'pattern_absent', 'Pattern abwesend'
    
    test_type = models.CharField(
        max_length=20,
        choices=TestType.choices
    )
    
    # ===== TEST CONFIG =====
    test_config = models.JSONField(
        help_text="Test-Konfiguration je nach Type"
    )
    
    # ===== SEVERITY =====
    severity = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1=Info, 2=Hinweis, 3=Wichtig, 4=Kritisch, 5=Blocker"
    )
    
    is_active = models.BooleanField(default=True)
    
    # ===== METADATA =====
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_style_acceptance_tests'
        verbose_name = 'Style Acceptance Test'
        verbose_name_plural = 'Style Acceptance Tests'
        ordering = ['style_dna', '-severity', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.test_type})"


# =============================================================================
# STYLE ADOPTION (Stil-Zuweisung)
# =============================================================================

class StyleAdoption(models.Model):
    """
    Verknüpfung: Wer nutzt welchen Stil für was?
    
    Ermöglicht:
    - Autor übernimmt Stil
    - Projekt nutzt Stil
    - Ghostwriter/Co-Autoren
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # ===== WER =====
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='style_adoptions'
    )
    
    # ===== WELCHER STIL =====
    style_dna = models.ForeignKey(
        AuthorStyleDNA,
        on_delete=models.CASCADE,
        related_name='adoptions'
    )
    
    # ===== FÜR WAS =====
    project = models.ForeignKey(
        'writing_hub.BookProject',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='style_adoptions',
        help_text="Optional: Nur für dieses Projekt"
    )
    
    # ===== ROLLE =====
    role = models.CharField(
        max_length=20,
        choices=[
            ('primary', 'Hauptstil'),
            ('secondary', 'Nebenstil'),
            ('experimental', 'Experimentell'),
        ],
        default='primary'
    )
    
    # ===== RECHTE =====
    can_modify = models.BooleanField(
        default=False,
        help_text="Darf dieser Autor den Stil modifizieren?"
    )
    
    # ===== METADATA =====
    adopted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'writing_style_adoptions'
        verbose_name = 'Style Adoption'
        verbose_name_plural = 'Style Adoptions'
        unique_together = ['author', 'style_dna', 'project']
        ordering = ['author', '-is_active', 'role']
    
    def __str__(self):
        project_str = f" ({self.project.title})" if self.project else ""
        return f"{self.author.username} → {self.style_dna.name}{project_str}"


# =============================================================================
# AUTHOR (Externe Autoren wie "Freida McFadden")
# =============================================================================

class Author(models.Model):
    """
    Externe Autorenprofile für Stilvorlagen.
    
    Ermöglicht:
    - Autoren wie "Freida McFadden" als Stilvorlagen zu definieren
    - Mehrere Schreibstile pro Autor
    - Multi-Autoren-Bücher (verschiedene Kapitel von verschiedenen Autoren)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(
        max_length=200,
        help_text="Name des Autors, z.B. 'Freida McFadden'"
    )
    
    bio = models.TextField(
        blank=True,
        help_text="Kurze Biografie oder Beschreibung des Autors"
    )
    
    genres = models.JSONField(
        default=list,
        help_text="Genres des Autors, z.B. ['Thriller', 'Suspense']"
    )
    
    # Bild/Avatar (optional)
    avatar_url = models.URLField(
        blank=True,
        help_text="URL zum Autorenbild"
    )
    
    # Erstellt von (welcher User hat diesen Autor angelegt)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_authors'
    )
    
    is_public = models.BooleanField(
        default=False,
        help_text="Öffentlich für alle User sichtbar?"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_authors'
        verbose_name = 'Author'
        verbose_name_plural = 'Authors'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def default_style(self):
        """Gibt den Standard-Schreibstil zurück"""
        return self.writing_styles.filter(is_default=True).first() or self.writing_styles.first()


class WritingStyle(models.Model):
    """
    Schreibstil eines Autors mit LLM-Konfiguration.
    
    Ein Autor kann mehrere Stile haben (z.B. für verschiedene Serien/Genres).
    Enthält alle Informationen, die das LLM braucht, um in diesem Stil zu schreiben.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name='writing_styles'
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Name des Stils, z.B. 'Thriller 1. Person', 'Suspense 3. Person'"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Beschreibung des Stils"
    )
    
    is_default = models.BooleanField(
        default=False,
        help_text="Standard-Stil für diesen Autor"
    )
    
    # ===== LLM KONFIGURATION =====
    llm = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='writing_styles',
        help_text="Bevorzugtes LLM für diesen Stil"
    )
    
    temperature = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        help_text="Kreativitätsparameter (0.0-2.0)"
    )
    
    max_tokens = models.PositiveIntegerField(
        default=4000,
        help_text="Maximale Token pro Generierung"
    )
    
    # ===== STIL-PROMPTS =====
    system_prompt = models.TextField(
        blank=True,
        help_text="System-Prompt für das LLM (beschreibt den Schreibstil)"
    )
    
    style_instructions = models.TextField(
        blank=True,
        help_text="Detaillierte Stilanweisungen"
    )
    
    # ===== DO / DON'T LISTEN =====
    do_list = models.JSONField(
        default=list,
        help_text="Was der Stil tun soll"
    )
    
    dont_list = models.JSONField(
        default=list,
        help_text="Was der Stil vermeiden soll"
    )
    
    taboo_words = models.JSONField(
        default=list,
        help_text="Verbotene Wörter/Phrasen"
    )
    
    # ===== BEISPIELTEXTE =====
    example_texts = models.JSONField(
        default=list,
        help_text="Beispieltexte im Stil des Autors"
    )
    
    # ===== POV-EINSTELLUNGEN =====
    class POV(models.TextChoices):
        FIRST_PERSON = 'first', 'Ich-Erzähler (1. Person)'
        THIRD_LIMITED = 'third_limited', 'Personaler Erzähler (3. Person limitiert)'
        THIRD_OMNISCIENT = 'third_omni', 'Auktorialer Erzähler (3. Person allwissend)'
        SECOND_PERSON = 'second', 'Du-Erzähler (2. Person)'
    
    default_pov = models.CharField(
        max_length=20,
        choices=POV.choices,
        default=POV.THIRD_LIMITED,
        help_text="Standard-Erzählperspektive"
    )
    
    # ===== ZEITFORM =====
    class Tense(models.TextChoices):
        PAST = 'past', 'Vergangenheit (Präteritum)'
        PRESENT = 'present', 'Gegenwart (Präsens)'
    
    default_tense = models.CharField(
        max_length=10,
        choices=Tense.choices,
        default=Tense.PAST,
        help_text="Standard-Zeitform"
    )
    
    # ===== METADATA =====
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_styles'
        verbose_name = 'Writing Style'
        verbose_name_plural = 'Writing Styles'
        ordering = ['author', '-is_default', 'name']
        unique_together = ['author', 'name']
    
    def __str__(self):
        return f"{self.author.name}: {self.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default style per author
        if self.is_default:
            WritingStyle.objects.filter(
                author=self.author, 
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    def get_full_system_prompt(self):
        """Generiert den vollständigen System-Prompt für das LLM"""
        parts = []
        
        if self.system_prompt:
            parts.append(self.system_prompt)
        
        if self.style_instructions:
            parts.append(f"\n## Stilanweisungen:\n{self.style_instructions}")
        
        if self.do_list:
            parts.append(f"\n## Was du tun sollst:\n" + "\n".join(f"- {item}" for item in self.do_list))
        
        if self.dont_list:
            parts.append(f"\n## Was du vermeiden sollst:\n" + "\n".join(f"- {item}" for item in self.dont_list))
        
        if self.taboo_words:
            parts.append(f"\n## Verbotene Wörter/Phrasen:\n" + ", ".join(self.taboo_words))
        
        parts.append(f"\n## Erzählperspektive: {self.get_default_pov_display()}")
        parts.append(f"## Zeitform: {self.get_default_tense_display()}")
        
        return "\n".join(parts)


class ProjectAuthor(models.Model):
    """
    Verknüpfung zwischen Projekt und Autor mit Stil.
    
    Ermöglicht Multi-Autoren-Bücher mit verschiedenen Stilen pro Autor.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='project_authors'
    )
    
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name='author_projects'
    )
    
    writing_style = models.ForeignKey(
        WritingStyle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_assignments',
        help_text="Spezifischer Stil für dieses Projekt (sonst Default-Stil)"
    )
    
    is_primary = models.BooleanField(
        default=False,
        help_text="Hauptautor des Projekts"
    )
    
    # Reihenfolge für Anzeige
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_project_authors'
        verbose_name = 'Project Author'
        verbose_name_plural = 'Project Authors'
        ordering = ['project', 'order', '-is_primary']
        unique_together = ['project', 'author']
    
    def __str__(self):
        style_str = f" ({self.writing_style.name})" if self.writing_style else ""
        return f"{self.project.title} → {self.author.name}{style_str}"
    
    def get_effective_style(self):
        """Gibt den effektiven Stil zurück (spezifisch oder Default)"""
        return self.writing_style or self.author.default_style
    
    def save(self, *args, **kwargs):
        # Ensure only one primary author per project
        if self.is_primary:
            ProjectAuthor.objects.filter(
                project=self.project, 
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
