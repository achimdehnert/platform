================
Illustration MCP
================

.. note::
   **ComfyUI Integration für Buch-Illustrationen** | 6 Tools | Status: Production

Übersicht
=========

Der Illustration MCP Server integriert ComfyUI für AI-gesteuerte
Buch-Illustrationen mit konsistentem Stil.

Features:

- **Kapitel-Illustrationen**: Szenen-basierte Generierung
- **Character Portraits**: Konsistente Charakter-Darstellung
- **Batch Generation**: Alle Illustrationen eines Kapitels
- **Style Management**: Projekt-spezifische Stilprofile
- **ComfyUI Status**: GPU und Modell-Überwachung

Voraussetzungen
===============

ComfyUI Installation
--------------------

.. code-block:: bash

   # ComfyUI starten
   cd ~/ai-tools/ComfyUI
   python main.py --listen 0.0.0.0 --port 8181

Umgebungsvariablen
------------------

.. code-block:: bash

   export BFAGENT_PROJECT_ROOT=/path/to/bfagent
   export DJANGO_SETTINGS_MODULE=config.settings
   export COMFYUI_URL=http://localhost:8181

Start
-----

.. code-block:: bash

   cd packages/illustration_mcp
   python server.py

Tools
=====

Status & Konfiguration
----------------------

.. function:: check_comfyui_status()

   Prüft ComfyUI-Verbindung und System-Status.
   
   :return: Connection Status, GPU Info, installierte Modelle, Style Presets
   
   Beispiel-Ausgabe:
   
   .. code-block:: json
   
      {
        "connected": true,
        "url": "http://localhost:8181",
        "models_installed": ["sdxl_base", "sdxl_refiner", "flux"],
        "model_count": 3,
        "system_stats": {
          "gpu": "NVIDIA RTX 4090",
          "vram_used": "8GB",
          "vram_total": "24GB"
        },
        "style_presets": ["watercolor", "oil_painting", "digital_art"]
      }

.. function:: list_available_styles()

   Listet alle verfügbaren Illustration-Stile.
   
   :return: ComfyUI Presets + Genre-basierte Presets aus DB
   
   Kombiniert:
   
   - ComfyUI Style Presets (watercolor, oil_painting, etc.)
   - Genre-spezifische Stile (fantasy, scifi, romance)
   - Projekt-definierte Stile (aus IllustrationStyle Model)

.. function:: get_project_style(project_id)

   Holt Illustrations-Stil für ein Buchprojekt.
   
   :param project_id: BookProject ID
   :return: Style-Konfiguration für das Projekt
   
   Style-Parameter:
   
   - Base Model (SDXL, Flux, etc.)
   - Positive/Negative Prompts
   - Sampler Settings
   - Color Palette
   - Aspect Ratio

Illustration Generation
-----------------------

.. function:: generate_chapter_illustration(chapter_id, scene_index?, scene_description?, style_preset?, width?, height?)

   Generiert Illustration für eine Kapitel-Szene.
   
   :param chapter_id: Kapitel ID
   :param scene_index: Szenen-Index aus Kapitel-Analyse (default: 0)
   :param scene_description: Optional: Custom Szenen-Beschreibung
   :param style_preset: Optional: Style-Preset Override
   :param width: Bildbreite (default: 1024)
   :param height: Bildhöhe (default: 768)
   :return: Generiertes Bild, Prompt, Metadata
   
   Workflow:
   
   1. Kapitel laden und analysieren (falls nicht vorhanden)
   2. Szene aus Analyse extrahieren oder custom description nutzen
   3. Projekt-Style laden
   4. Prompt generieren (Szene + Style + Charakter-Referenzen)
   5. ComfyUI Workflow ausführen
   6. Bild speichern und verknüpfen

.. function:: generate_character_portrait(project_id, character_name, character_description, pose?, style_preset?)

   Generiert Charakter-Portrait mit Projekt-Stil.
   
   :param project_id: BookProject ID
   :param character_name: Name des Charakters
   :param character_description: Visuelle Beschreibung
   :param pose: portrait, full_body, action, profile (default: portrait)
   :param style_preset: Optional Style Override
   :return: Portrait-Bild, Prompt, Metadata
   
   Features:
   
   - Konsistenter Stil über alle Portraits
   - Gesichtskonsistenz via Reference Images
   - Verschiedene Posen für Charakter-Sheet

.. function:: batch_generate_chapter(chapter_id, max_illustrations?)

   Generiert alle Illustrationen für ein Kapitel.
   
   :param chapter_id: Kapitel ID
   :param max_illustrations: Maximum (default: 3)
   :return: Liste generierter Bilder
   
   Basiert auf Szenen-Analyse des Kapitels.
   Generiert für die wichtigsten Szenen.

Style Presets
=============

ComfyUI Presets
---------------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Preset
     - Beschreibung
   * - watercolor
     - Aquarell-Stil, weiche Farben, Papier-Textur
   * - oil_painting
     - Klassischer Ölgemälde-Stil, reich an Details
   * - digital_art
     - Moderner Digital-Art Stil
   * - pencil_sketch
     - Bleistiftzeichnung, schwarz-weiß
   * - comic_book
     - Comic-Stil mit Outlines und Flat Colors
   * - anime
     - Anime/Manga Stil
   * - photorealistic
     - Fotorealistische Darstellung

Genre-basierte Presets
----------------------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Genre
     - Stil-Eigenschaften
   * - fantasy
     - Magische Atmosphäre, saturierte Farben, ethereal lighting
   * - scifi
     - Technisch, neon accents, clean lines
   * - romance
     - Weich, warm, bokeh effects
   * - thriller
     - Dunkel, kontrastreich, dramatic lighting
   * - historical
     - Period-accurate, sepia tones, classical composition
   * - children
     - Bunt, freundlich, vereinfachte Formen

Beispiele
=========

Kapitel illustrieren
--------------------

.. code-block:: python

   # Status prüfen
   check_comfyui_status()
   
   # Einzelne Szene
   generate_chapter_illustration(
       chapter_id=42,
       scene_index=0,
       width=1024,
       height=768
   )
   
   # Alle Szenen
   batch_generate_chapter(
       chapter_id=42,
       max_illustrations=5
   )

Charakter-Portrait
------------------

.. code-block:: python

   generate_character_portrait(
       project_id=1,
       character_name="Elena",
       character_description="Young woman, 25, auburn hair, green eyes, determined expression",
       pose="portrait",
       style_preset="fantasy"
   )

Custom Style
------------

.. code-block:: python

   # Projekt-Stil abrufen
   style = get_project_style(project_id=1)
   
   # Mit Custom Description
   generate_chapter_illustration(
       chapter_id=42,
       scene_description="Elena stands at the edge of the cliff, looking out at the stormy sea",
       style_preset="oil_painting"
   )

Integration
===========

Writing Hub
-----------

Die generierten Illustrationen werden automatisch mit dem Writing Hub verknüpft:

- ``ChapterIllustration`` Model für Kapitel-Bilder
- ``CharacterPortrait`` Model für Charakter-Portraits
- Gallery-View im Writing Hub
- HTMX-basierte Generierung aus dem Editor

ComfyUI Workflows
-----------------

Der Server nutzt optimierte ComfyUI Workflows:

.. code-block:: text

   workflows/
   ├── chapter_illustration.json    # Standard Kapitel-Bild
   ├── character_portrait.json      # Portrait mit Face Fix
   ├── batch_generation.json        # Optimiert für Batch
   └── style_transfer.json          # Stil-Konsistenz

Troubleshooting
===============

ComfyUI nicht erreichbar
------------------------

.. code-block:: bash

   # ComfyUI starten
   cd ~/ai-tools/ComfyUI
   python main.py --listen 0.0.0.0 --port 8181
   
   # Oder via Docker
   docker run -p 8181:8181 --gpus all comfyui

VRAM Probleme
-------------

.. code-block:: python

   # Kleinere Bilder generieren
   generate_chapter_illustration(
       chapter_id=42,
       width=768,
       height=512
   )

Stil-Inkonsistenz
-----------------

1. Projekt-Style korrekt konfiguriert?
2. Reference Images vorhanden?
3. Seed für Reproduzierbarkeit nutzen
