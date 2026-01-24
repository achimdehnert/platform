.. _prompt-system-technical:

=====================================================
Image Prompt System - Technische Referenz
=====================================================

.. contents:: Inhalt
   :local:
   :depth: 3

Architektur Übersicht
=====================

Das Image Prompt System implementiert ein **komponentenbasiertes Prompt-Building** 
für konsistente Bildgenerierung in Buchprojekten.

.. mermaid::

   classDiagram
       class PromptMasterStyle {
           +project: BookProjects
           +preset: StylePreset
           +style_base_prompt: str
           +negative_prompt: str
           +guidance_scale: float
           +get_full_style_prompt()
           +build_combined_prompt()
       }
       
       class PromptCharacter {
           +project: BookProjects
           +name: str
           +role: Role
           +appearance_prompt: str
           +clothing_prompt: str
           +get_full_prompt(age_variant)
       }
       
       class PromptLocation {
           +project: BookProjects
           +name: str
           +location_type: LocationType
           +environment_prompt: str
           +get_full_prompt(time_of_day)
       }
       
       class PromptBuilderHandler {
           +project_id: int
           +build_prompt()
           +build_chapter_prompt()
           +log_generation()
       }
       
       class ScenePromptBuilder {
           +project_id: int
           +build_from_analysis()
           +build_optimized()
       }
       
       PromptBuilderHandler --> PromptMasterStyle
       PromptBuilderHandler --> PromptCharacter
       PromptBuilderHandler --> PromptLocation
       ScenePromptBuilder --> PromptMasterStyle
       ScenePromptBuilder --> PromptCharacter

Datenbank-Schema
================

Tabellen-Übersicht
------------------

.. code-block:: text

   writing_prompt_master_styles      → Projekt-Stil-Definition
   writing_prompt_characters         → Charakter-Visuals
   writing_prompt_locations          → Ort-Beschreibungen
   writing_prompt_cultural_elements  → Kulturelles Glossar
   writing_prompt_scene_templates    → Szenen-Vorlagen
   writing_prompt_generation_logs    → Audit-Trail

Entity-Relationship
-------------------

.. mermaid::

   erDiagram
       BookProjects ||--o| PromptMasterStyle : has
       BookProjects ||--o{ PromptCharacter : has
       BookProjects ||--o{ PromptLocation : has
       BookProjects ||--o{ PromptCulturalElement : has
       BookProjects ||--o{ PromptSceneTemplate : has
       BookProjects ||--o{ PromptGenerationLog : logs
       
       PromptCharacter ||--o| Characters : links_to
       PromptGenerationLog }o--o{ PromptCharacter : uses
       PromptGenerationLog }o--o| PromptLocation : uses
       PromptGenerationLog }o--o| PromptSceneTemplate : uses

Models
======

PromptMasterStyle
-----------------

**Datei:** ``apps/writing_hub/models_prompt_system.py``

**Tabelle:** ``writing_prompt_master_styles``

Der Master-Stil definiert die visuelle Identität eines Projekts.

.. code-block:: python

   class PromptMasterStyle(models.Model):
       """
       Master style definition for all images in a project.
       Defines the visual DNA that gets applied to every generated image.
       """
       
       class StylePreset(models.TextChoices):
           FAIRY_TALE = 'fairy_tale', '🧚 Märchen (Ivan Bilibin)'
           CINEMATIC = 'cinematic', '🎬 Cinematisch'
           WATERCOLOR = 'watercolor', '🎨 Aquarell Kinderbuch'
           MANGA = 'manga', '📚 Manga/Anime'
           REALISTIC = 'realistic', '📷 Fotorealistisch'
           # ... weitere Presets
       
       project = models.OneToOneField('bfagent.BookProjects', ...)
       name = models.CharField(max_length=100)
       preset = models.CharField(max_length=20, choices=StylePreset.choices)
       
       # Core prompts
       style_base_prompt = models.TextField()
       style_modifiers = models.TextField(blank=True)
       master_prompt = models.TextField(blank=True)  # Finale, editierbare Version
       negative_prompt = models.TextField()
       
       # Cultural context
       cultural_context = models.TextField(blank=True)
       artistic_references = models.TextField(blank=True)
       
       # Technical defaults
       default_width = models.IntegerField(default=1024)
       default_height = models.IntegerField(default=768)
       guidance_scale = models.FloatField(default=7.5)
       inference_steps = models.IntegerField(default=28)
       
       # Consistency
       use_fixed_seed = models.BooleanField(default=False)
       fixed_seed = models.IntegerField(null=True, blank=True)

**Wichtige Methoden:**

.. code-block:: python

   def get_preset_style_prompt(self) -> str:
       """Gibt Preset-spezifischen Stil-Prompt zurück."""
       
   def build_combined_prompt(self) -> str:
       """Kombiniert alle Prompt-Komponenten."""
       
   def get_full_style_prompt(self) -> str:
       """Finaler Prompt: master_prompt wenn gesetzt, sonst build_combined_prompt."""

PromptCharacter
---------------

**Tabelle:** ``writing_prompt_characters``

.. code-block:: python

   class PromptCharacter(models.Model):
       """Reusable character visual definition."""
       
       class Role(models.TextChoices):
           PROTAGONIST = 'protagonist', '⭐ Protagonist'
           ANTAGONIST = 'antagonist', '👿 Antagonist'
           MENTOR = 'mentor', '🧙 Mentor'
           SIDEKICK = 'sidekick', '🤝 Sidekick'
           LOVE_INTEREST = 'love_interest', '💕 Love Interest'
           SUPPORTING = 'supporting', '👥 Nebenrolle'
       
       project = models.ForeignKey('bfagent.BookProjects', ...)
       book_character = models.OneToOneField('bfagent.Characters', null=True)
       
       name = models.CharField(max_length=100)
       role = models.CharField(max_length=20, choices=Role.choices)
       
       # Visual prompts
       appearance_prompt = models.TextField()
       clothing_prompt = models.TextField()
       props_prompt = models.TextField(blank=True)
       expression_default = models.CharField(max_length=100, blank=True)
       
       # Age variations
       age_child_prompt = models.TextField(blank=True)
       age_elder_prompt = models.TextField(blank=True)
       
       # Consistency
       reference_seed = models.IntegerField(null=True, blank=True)

**Wichtige Methoden:**

.. code-block:: python

   def get_full_prompt(self, age_variant: str = 'default') -> str:
       """
       Generiert vollständigen Charakter-Prompt.
       
       Args:
           age_variant: 'default', 'child', oder 'elder'
       
       Returns:
           Kombinierter Prompt aus appearance, clothing, props, expression
       """

PromptLocation
--------------

**Tabelle:** ``writing_prompt_locations``

.. code-block:: python

   class PromptLocation(models.Model):
       """Reusable location/environment definitions."""
       
       class LocationType(models.TextChoices):
           INTERIOR = 'interior', '🏠 Innenraum'
           EXTERIOR = 'exterior', '🌄 Außenbereich'
           LANDSCAPE = 'landscape', '🏞️ Landschaft'
           URBAN = 'urban', '🏙️ Stadt'
           SUPERNATURAL = 'supernatural', '✨ Übernatürlich'
       
       class TimeOfDay(models.TextChoices):
           DAWN = 'dawn', '🌅 Morgendämmerung'
           DAY = 'day', '☀️ Tag'
           DUSK = 'dusk', '🌆 Abenddämmerung'
           NIGHT = 'night', '🌙 Nacht'
       
       project = models.ForeignKey('bfagent.BookProjects', ...)
       name = models.CharField(max_length=100)
       location_type = models.CharField(max_length=20)
       
       # Visual prompts
       environment_prompt = models.TextField()
       architecture_prompt = models.TextField(blank=True)
       nature_prompt = models.TextField(blank=True)
       
       # Lighting variations
       lighting_default = models.TextField(blank=True)
       lighting_dawn = models.TextField(blank=True)
       lighting_night = models.TextField(blank=True)
       
       # Atmosphere
       atmosphere_prompt = models.TextField(blank=True)
       weather_default = models.CharField(max_length=100, blank=True)

**Wichtige Methoden:**

.. code-block:: python

   def get_full_prompt(self, time_of_day: str = 'day') -> str:
       """
       Generiert Ort-Prompt mit passender Beleuchtung.
       
       Args:
           time_of_day: 'dawn', 'day', 'dusk', oder 'night'
       """

PromptCulturalElement
---------------------

**Tabelle:** ``writing_prompt_cultural_elements``

Glossar für kulturelle Authentizität.

.. code-block:: python

   class PromptCulturalElement(models.Model):
       """Cultural glossary for authentic visual representation."""
       
       class Category(models.TextChoices):
           CLOTHING = 'clothing', '👗 Kleidung'
           ARCHITECTURE = 'architecture', '🏛️ Architektur'
           OBJECTS = 'objects', '🏺 Gegenstände'
           ANIMALS = 'animals', '🐎 Tiere'
           NATURE = 'nature', '🌿 Natur'
           SYMBOLS = 'symbols', '🔷 Symbole'
           FOOD = 'food', '🍜 Essen'
           MUSIC = 'music', '🎵 Musik'
       
       project = models.ForeignKey('bfagent.BookProjects', ...)
       
       term_local = models.CharField(max_length=100)   # z.B. "Kiiz üy"
       term_english = models.CharField(max_length=100) # z.B. "Yurt"
       term_german = models.CharField(max_length=100)  # z.B. "Jurte"
       category = models.CharField(max_length=20)
       
       description = models.TextField()
       visual_prompt = models.TextField()  # Wie es dargestellt werden soll
       usage_context = models.TextField(blank=True)

PromptSceneTemplate
-------------------

**Tabelle:** ``writing_prompt_scene_templates``

Templates für typische Szenentypen mit Platzhaltern.

.. code-block:: python

   class PromptSceneTemplate(models.Model):
       """Templates for common scene types with placeholders."""
       
       class SceneType(models.TextChoices):
           ESTABLISHING = 'establishing', '🏠 Establishing Shot'
           ACTION = 'action', '⚔️ Action/Kampf'
           EMOTIONAL = 'emotional', '💔 Emotional'
           DIALOGUE = 'dialogue', '💬 Dialog'
           DISCOVERY = 'discovery', '🔍 Entdeckung'
           TRANSFORMATION = 'transformation', '✨ Transformation'
           JOURNEY = 'journey', '🚶 Reise'
           CONFRONTATION = 'confrontation', '🆚 Konfrontation'
           CELEBRATION = 'celebration', '🎉 Feier'
           TRAGEDY = 'tragedy', '😢 Tragödie'
       
       class AspectRatio(models.TextChoices):
           LANDSCAPE_16_9 = '16:9', '🖼️ Landscape 16:9'
           LANDSCAPE_2_1 = '2:1', '📖 Book Spread 2:1'
           PORTRAIT_3_4 = '3:4', '📱 Portrait 3:4'
           SQUARE = '1:1', '⬜ Square 1:1'
       
       project = models.ForeignKey('bfagent.BookProjects', ...)
       name = models.CharField(max_length=100)
       scene_type = models.CharField(max_length=20)
       
       # Template with placeholders
       template_prompt = models.TextField()
       # Platzhalter: {character}, {location}, {action}, {emotion}
       
       composition_hints = models.TextField(blank=True)
       recommended_aspect_ratio = models.CharField(max_length=10)
       
       # Technical overrides
       override_steps = models.IntegerField(null=True, blank=True)
       override_guidance = models.FloatField(null=True, blank=True)

**Wichtige Methoden:**

.. code-block:: python

   def render_prompt(self, character='', location='', action='', emotion='') -> str:
       """Rendert Template mit Werten."""
       
   def get_dimensions(self) -> tuple:
       """Returns (width, height) based on aspect ratio."""

PromptGenerationLog
-------------------

**Tabelle:** ``writing_prompt_generation_logs``

Audit-Trail für alle generierten Prompts.

.. code-block:: python

   class PromptGenerationLog(models.Model):
       """Logs all generated prompts for analysis."""
       
       class Rating(models.IntegerChoices):
           TERRIBLE = 1, '⭐ Schlecht'
           POOR = 2, '⭐⭐ Mäßig'
           ACCEPTABLE = 3, '⭐⭐⭐ OK'
           GOOD = 4, '⭐⭐⭐⭐ Gut'
           EXCELLENT = 5, '⭐⭐⭐⭐⭐ Exzellent'
       
       project = models.ForeignKey('bfagent.BookProjects', ...)
       chapter = models.ForeignKey('bfagent.BookChapters', null=True)
       illustration = models.ForeignKey('ChapterIllustration', null=True)
       
       # Components used
       master_style = models.ForeignKey(PromptMasterStyle, null=True)
       characters_used = models.ManyToManyField(PromptCharacter)
       location_used = models.ForeignKey(PromptLocation, null=True)
       template_used = models.ForeignKey(PromptSceneTemplate, null=True)
       
       # Prompts
       scene_description = models.TextField()
       final_prompt = models.TextField()
       negative_prompt = models.TextField()
       
       # Technical settings
       width = models.IntegerField()
       height = models.IntegerField()
       steps = models.IntegerField()
       guidance_scale = models.FloatField()
       seed_used = models.IntegerField(null=True)
       
       # Results
       generation_successful = models.BooleanField()
       generation_time_seconds = models.FloatField(null=True)
       error_message = models.TextField(blank=True)
       
       # User feedback
       user_rating = models.IntegerField(choices=Rating.choices, null=True)
       user_notes = models.TextField(blank=True)

Handler
=======

PromptBuilderHandler
--------------------

**Datei:** ``apps/writing_hub/handlers/prompt_builder_handler.py``

Hauptklasse für Prompt-Assembly aus Datenbank-Komponenten.

.. code-block:: python

   from apps.writing_hub.handlers.prompt_builder_handler import PromptBuilderHandler
   
   # Initialisierung
   handler = PromptBuilderHandler(project_id=17)
   
   # Prompt bauen
   result = handler.build_prompt(
       scene_description="Arman rides across the steppe at dawn",
       character_names=["Arman"],
       location_name="Die Steppe",
       scene_type="journey",
       time_of_day="dawn"
   )
   
   if result.success:
       print(result.prompt)           # Finaler Prompt
       print(result.negative_prompt)  # Negative Prompt
       print(result.width, result.height)
       print(result.components_used)  # Welche DB-Komponenten verwendet

**PromptResult Dataclass:**

.. code-block:: python

   @dataclass
   class PromptResult:
       success: bool
       prompt: str
       negative_prompt: str
       width: int
       height: int
       steps: int
       guidance_scale: float
       seed: Optional[int]
       components_used: Dict[str, Any]
       error: Optional[str] = None

**Methoden:**

.. py:method:: build_prompt(scene_description, character_names=None, location_name=None, scene_type='establishing', time_of_day='day', age_variant='default', override_width=None, override_height=None)

   Baut vollständigen Prompt aus Komponenten.
   
   :param scene_description: Basis-Szenenbeschreibung
   :param character_names: Liste von Charakternamen (max 2)
   :param location_name: Name des Ortes
   :param scene_type: Szenentyp für Template-Auswahl
   :param time_of_day: dawn/day/dusk/night
   :param age_variant: default/child/elder
   :returns: PromptResult

.. py:method:: build_chapter_prompt(chapter, scene_type='establishing', time_of_day='day')

   Baut Prompt für Kapitel-Illustration.
   Erkennt Charaktere und Orte automatisch aus Kapiteltext.

.. py:method:: log_generation(result, chapter=None, illustration=None, ...)

   Protokolliert Prompt-Generierung für Analyse.

ScenePromptBuilder
------------------

**Datei:** ``apps/writing_hub/services/scene_prompt_builder.py``

Spezialisiert für Prompts aus Szenenanalysen.

.. code-block:: python

   from apps.writing_hub.services.scene_prompt_builder import ScenePromptBuilder
   
   builder = ScenePromptBuilder(project_id=17)
   
   # Aus Szenenanalyse
   result = builder.build_from_analysis(analysis, scene_index=0)
   
   # Mit LLM-Optimierung
   result = builder.build_optimized(scene_data, use_llm=True)

**Mood Modifiers:**

Der Builder enthält vordefinierte Stimmungs-Modifikatoren:

.. code-block:: python

   MOOD_MODIFIERS = {
       'mysterious': {
           'lighting': 'dramatic shadows, chiaroscuro lighting',
           'colors': 'deep blues, purples, and dark greens',
           'atmosphere': 'misty, ethereal, enigmatic',
       },
       'romantic': {
           'lighting': 'soft golden hour light, warm glow',
           'colors': 'warm pinks, soft reds, gentle oranges',
           'atmosphere': 'dreamy, intimate, tender',
       },
       'tense': { ... },
       'peaceful': { ... },
       'dramatic': { ... },
       'melancholic': { ... },
       'joyful': { ... },
       'action': { ... },
       'dark': { ... },
   }

Preset Factory
==============

**Datei:** ``apps/writing_hub/handlers/prompt_builder_handler.py``

Factory für vordefinierte Projekt-Konfigurationen.

.. code-block:: python

   from apps.writing_hub.handlers.prompt_builder_handler import PromptPresetFactory
   
   # Kasachisches Märchen Preset
   result = PromptPresetFactory.create_kazakh_fairytale_preset(project_id=17)
   
   # Ergebnis:
   # {
   #     'master_style': <PromptMasterStyle>,
   #     'characters': [<PromptCharacter>, ...],
   #     'locations': [<PromptLocation>, ...],
   #     'elements': [<PromptCulturalElement>, ...],
   #     'templates': [<PromptSceneTemplate>, ...],
   # }

Eigene Presets erstellen
------------------------

.. code-block:: python

   class PromptPresetFactory:
       
       @staticmethod
       def create_my_custom_preset(project_id: int) -> Dict[str, Any]:
           """Custom preset for specific project type."""
           from apps.bfagent.models import BookProjects
           
           project = BookProjects.objects.get(id=project_id)
           created = {
               'master_style': None, 
               'characters': [], 
               'locations': [], 
               'elements': [], 
               'templates': []
           }
           
           # Master Style
           master_style, _ = PromptMasterStyle.objects.update_or_create(
               project=project,
               defaults={
                   'name': 'My Custom Style',
                   'preset': 'custom',
                   'style_base_prompt': 'Your style prompt here',
                   # ...
               }
           )
           created['master_style'] = master_style
           
           # Add characters, locations, etc.
           # ...
           
           return created

Management Commands
===================

create_prompt_preset
--------------------

.. code-block:: bash

   python manage.py create_prompt_preset --project-id=17 --preset=kazakh_fairytale

load_prompt_templates
---------------------

.. code-block:: bash

   python manage.py load_prompt_templates --project-id=17 --file=templates.json

Admin Integration
=================

**Datei:** ``apps/writing_hub/admin_prompt_system.py``

Alle Models sind im Django Admin verfügbar:

- ``/admin/writing_hub/promptmasterstyle/``
- ``/admin/writing_hub/promptcharacter/``
- ``/admin/writing_hub/promptlocation/``
- ``/admin/writing_hub/promptculturalelement/``
- ``/admin/writing_hub/promptscenetemplate/``
- ``/admin/writing_hub/promptgenerationlog/``

Erweiterung
===========

Neuen Style Preset hinzufügen
-----------------------------

1. Preset zu ``StylePreset`` Enum hinzufügen:

.. code-block:: python

   class StylePreset(models.TextChoices):
       # Bestehende...
       MY_NEW_STYLE = 'my_new_style', '🎨 Mein Neuer Stil'

2. Preset-Prompt in ``get_preset_style_prompt()`` hinzufügen:

.. code-block:: python

   def get_preset_style_prompt(self) -> str:
       preset_prompts = {
           # Bestehende...
           'my_new_style': 'your style description here',
       }

3. Migration erstellen und anwenden.

Neuen Szenentyp hinzufügen
--------------------------

1. Zu ``SceneType`` Enum hinzufügen:

.. code-block:: python

   class SceneType(models.TextChoices):
       # Bestehende...
       MY_SCENE = 'my_scene', '🎬 Mein Szenentyp'

2. In ``ScenePromptBuilder`` Mood-Modifier hinzufügen (falls benötigt).

3. Migration erstellen.

Integration mit Bildgeneratoren
-------------------------------

Das System ist Backend-agnostisch. Integration mit ComfyUI:

.. code-block:: python

   from apps.writing_hub.handlers.prompt_builder_handler import PromptBuilderHandler
   from apps.media_hub.services.comfyui_service import ComfyUIService
   
   # Prompt bauen
   handler = PromptBuilderHandler(project_id=17)
   result = handler.build_chapter_prompt(chapter)
   
   if result.success:
       # An ComfyUI senden
       comfy = ComfyUIService()
       image = comfy.generate(
           prompt=result.prompt,
           negative_prompt=result.negative_prompt,
           width=result.width,
           height=result.height,
           steps=result.steps,
           cfg_scale=result.guidance_scale,
           seed=result.seed
       )

Testing
=======

.. code-block:: python

   # tests/test_prompt_system.py
   
   from django.test import TestCase
   from apps.writing_hub.handlers.prompt_builder_handler import (
       PromptBuilderHandler, PromptPresetFactory
   )
   from apps.writing_hub.models_prompt_system import PromptMasterStyle
   
   class PromptBuilderTests(TestCase):
       
       def setUp(self):
           # Projekt und Master-Stil erstellen
           self.project = BookProjects.objects.create(title="Test")
           PromptMasterStyle.objects.create(
               project=self.project,
               name="Test Style",
               preset="fairy_tale",
               style_base_prompt="test prompt"
           )
       
       def test_build_prompt_success(self):
           handler = PromptBuilderHandler(project_id=self.project.id)
           result = handler.build_prompt("A hero in the forest")
           
           self.assertTrue(result.success)
           self.assertIn("test prompt", result.prompt)
       
       def test_build_prompt_no_master_style(self):
           # Projekt ohne Master-Stil
           other_project = BookProjects.objects.create(title="No Style")
           handler = PromptBuilderHandler(project_id=other_project.id)
           result = handler.build_prompt("A scene")
           
           self.assertFalse(result.success)
           self.assertIn("Kein Master-Stil", result.error)

Performance
===========

- Lazy Loading für Komponenten (Characters, Locations werden bei Bedarf geladen)
- Caching der Komponenten innerhalb einer Handler-Instanz
- Effiziente Charakter-Erkennung durch Case-Insensitive String-Matching
- Batch-Verarbeitung für Multiple Scenes

Weiterführende Dokumentation
============================

- :ref:`prompt-system-user` - Benutzerhandbuch
- :doc:`../hubs/writing_hub` - Writing Hub Dokumentation
- :doc:`handlers` - Handler-Referenz
- :doc:`models` - Model-Referenz

