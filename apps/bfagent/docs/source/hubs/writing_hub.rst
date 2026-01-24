===========
Writing Hub
===========

.. note::
   **Kreatives Schreiben & Buchproduktion** | Status: Production Ready

Übersicht
=========

Der Writing Hub ist das Herzstück für kreatives Schreiben und Buchproduktion:

- **Projekte**: Buchprojekte verwalten
- **Kapitel**: Kapitel schreiben und strukturieren
- **Charaktere**: Charakterentwicklung mit AI-Unterstützung
- **Welten**: World-Building für Fiction
- **Lektorat**: Stilanalyse und Korrekturen
- **Prompts**: Template-basierte AI-Generierung

Architektur
===========

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                      WRITING HUB                             │
   ├─────────────────────────────────────────────────────────────┤
   │                                                             │
   │  BookProject ──→ Chapter ──→ Character ──→ World           │
   │       │             │            │            │             │
   │       ↓             ↓            ↓            ↓             │
   │  Outline      Content       Profile      Locations         │
   │       │             │            │            │             │
   │       ↓             ↓            ↓            ↓             │
   │  PromptTemplate ←── LLM Integration ←── Style Analysis     │
   │                                                             │
   └─────────────────────────────────────────────────────────────┘

Models
======

Kern-Models
-----------

.. code-block:: python

   # models.py (Auszug)
   
   class BookProject(models.Model):
       """Buchprojekt als Container."""
       title = models.CharField(max_length=200)
       genre = models.ForeignKey(Genre, on_delete=models.SET_NULL)
       target_audience = models.ForeignKey(TargetAudience, on_delete=models.SET_NULL)
       status = models.CharField(choices=STATUS_CHOICES)
       word_count_target = models.IntegerField(default=80000)
   
   class Chapter(models.Model):
       """Einzelnes Kapitel."""
       project = models.ForeignKey(BookProject, on_delete=models.CASCADE)
       title = models.CharField(max_length=200)
       number = models.IntegerField()
       content = models.TextField(blank=True)
       status = models.CharField(choices=STATUS_CHOICES)
       word_count = models.IntegerField(default=0)
   
   class Character(models.Model):
       """Charakter mit Profil."""
       project = models.ForeignKey(BookProject, on_delete=models.CASCADE)
       name = models.CharField(max_length=100)
       role = models.CharField(choices=ROLE_CHOICES)
       profile_data = models.JSONField(default=dict)
       backstory = models.TextField(blank=True)

Model-Gruppen
-------------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Modul
     - Models
     - Zweck
   * - ``models.py``
     - BookProject, Chapter, Character
     - Kern-Entitäten
   * - ``models_world.py``
     - World, Location, WorldRule
     - World-Building
   * - ``models_lektorat.py``
     - StyleAnalysis, Correction
     - Lektorat & Korrektur
   * - ``models_prompt_system.py``
     - WritingPrompt, PromptExecution
     - AI-Prompts
   * - ``models_style.py``
     - StyleProfile, StyleRule
     - Stilanalyse
   * - ``models_quality.py``
     - QualityCheck, QualityScore
     - Qualitätskontrolle

Handlers
========

Der Writing Hub nutzt das Handler-System für AI-Integration:

.. code-block:: python

   # handlers/ Verzeichnis
   
   OutlineGenerationHandler    # Outline generieren
   CharacterGenerationHandler  # Charaktere erstellen
   ChapterWriterHandler        # Kapitel schreiben
   EditingHandler              # Lektorat
   SceneAnalyzerHandler        # Szenen analysieren
   WorldGeneratorHandler       # Welten generieren

Handler-Verwendung
------------------

.. code-block:: python

   from apps.writing_hub.handlers import CharacterGenerationHandler
   
   handler = CharacterGenerationHandler()
   result = handler.execute({
       "project_id": project.id,
       "role": "protagonist",
       "genre": "fantasy",
       "use_ai": True,
   })
   
   character = result.data["character"]

Views
=====

Haupt-Views
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - View
     - URL
     - Funktion
   * - ``dashboard``
     - ``/writing-hub/``
     - Übersicht
   * - ``project_list``
     - ``/writing-hub/projects/``
     - Projekte auflisten
   * - ``project_detail``
     - ``/writing-hub/projects/<id>/``
     - Projekt-Details
   * - ``chapter_editor``
     - ``/writing-hub/chapters/<id>/edit/``
     - Kapitel bearbeiten
   * - ``character_creator``
     - ``/writing-hub/characters/create/``
     - Charakter erstellen

Spezial-Views
-------------

.. code-block:: python

   # views_creative.py - Kreative Funktionen
   # views_lektorat.py - Lektorat & Stil
   # views_world.py - World-Building
   # views_style_lab.py - Stil-Experimente
   # views_import.py - Dokument-Import

Lektorat-System
===============

Stilanalyse
-----------

.. code-block:: python

   # models_lektorat.py
   
   class StyleAnalysis(models.Model):
       chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
       readability_score = models.FloatField()
       sentence_variety = models.FloatField()
       word_repetitions = models.JSONField()
       suggestions = models.JSONField()

Korrekturen
-----------

.. code-block:: python

   class Correction(models.Model):
       CORRECTION_TYPES = [
           ("grammar", "Grammatik"),
           ("style", "Stil"),
           ("repetition", "Wiederholung"),
           ("consistency", "Konsistenz"),
       ]
       
       chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
       correction_type = models.CharField(choices=CORRECTION_TYPES)
       original_text = models.TextField()
       suggested_text = models.TextField()
       status = models.CharField(choices=STATUS_CHOICES)

Prompt System
=============

Writing-Prompts werden DB-gesteuert verwaltet:

.. code-block:: python

   # models_prompt_system.py
   
   class WritingPrompt(models.Model):
       name = models.CharField(max_length=200)
       category = models.CharField(choices=CATEGORY_CHOICES)
       system_prompt = models.TextField()
       user_template = models.TextField()
       variables = models.JSONField(default=list)
       
       # LLM Config
       preferred_llm = models.ForeignKey(LLM, null=True)
       temperature = models.FloatField(default=0.7)
       max_tokens = models.IntegerField(default=2000)

URLs
====

.. code-block:: python

   # urls.py (Hauptstruktur)
   
   urlpatterns = [
       # Dashboard
       path("", views.dashboard, name="dashboard"),
       
       # Projects CRUD
       path("projects/", views.project_list, name="project_list"),
       path("projects/create/", views.project_create, name="project_create"),
       path("projects/<uuid:pk>/", views.project_detail, name="project_detail"),
       
       # Chapters
       path("chapters/<uuid:pk>/", views.chapter_detail, name="chapter_detail"),
       path("chapters/<uuid:pk>/edit/", views.chapter_edit, name="chapter_edit"),
       
       # Characters
       path("characters/", views.character_list, name="character_list"),
       path("characters/create/", views.character_create, name="character_create"),
       
       # World Building
       path("worlds/", include("apps.writing_hub.urls_world")),
       
       # Lektorat
       path("lektorat/", include("apps.writing_hub.urls_lektorat")),
       
       # Style Lab
       path("style-lab/", include("apps.writing_hub.urls_style")),
   ]

Admin
=====

Der Writing Hub hat umfangreiche Admin-Konfiguration:

.. code-block:: python

   # admin.py - Kern-Entitäten
   # admin_lektorat.py - Lektorat
   # admin_prompt_system.py - Prompts
   # admin_quality.py - Qualität
   # admin_story_elements.py - Story-Elemente
   # admin_style.py - Stil

Siehe auch
==========

.. toctree::
   :maxdepth: 1

   control_center
   ../guides/session_handling_controlling
