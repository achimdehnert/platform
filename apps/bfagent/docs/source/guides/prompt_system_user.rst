.. _prompt-system-user:

=========================================
Image Prompt System - Benutzerhandbuch
=========================================

.. contents:: Inhalt
   :local:
   :depth: 2

Übersicht
=========

Das **Image Prompt System** ermöglicht die konsistente Generierung von Buchillustrationen 
durch datenbankgesteuerte Prompt-Komponenten. Statt für jedes Bild manuell Prompts zu 
schreiben, definieren Sie einmalig Stile, Charaktere und Orte - das System kombiniert 
diese automatisch.

.. note::
   Das Prompt System ist Teil des Writing Hub und speziell für Buchprojekte optimiert.

Kernkonzepte
============

Das System basiert auf **5 Komponenten**, die zusammen den finalen Bildprompt bilden:

.. mermaid::

   flowchart TB
       MS[🎨 Master-Stil] --> FP[Finaler Prompt]
       PC[👤 Charaktere] --> FP
       PL[🏠 Orte] --> FP
       CE[🌍 Kulturelle Elemente] --> FP
       ST[📋 Szenen-Templates] --> FP
       FP --> IMG[🖼️ Generiertes Bild]

1. **Master-Stil** - Das visuelle "DNA" aller Bilder im Projekt
2. **Charaktere** - Wiederverwendbare Charakterbeschreibungen
3. **Orte** - Umgebungen und Locations
4. **Kulturelle Elemente** - Glossar für authentische Details
5. **Szenen-Templates** - Vorlagen für typische Szenentypen

Schnellstart
============

1. Master-Stil erstellen
------------------------

Der Master-Stil definiert die visuelle Identität Ihres gesamten Buchprojekts.

**Navigation:** Admin → Writing Hub → Prompt Master-Stile → Hinzufügen

.. code-block:: text

   Projekt:        [Ihr Buchprojekt auswählen]
   Name:           Märchen-Stil
   Preset:         🧚 Märchen (Ivan Bilibin)
   
   Basis-Prompt:   Digital fairy tale illustration, 
                   rich jewel tones, cinematic composition
   
   Negative Prompt: blurry, low quality, text, watermark

**Presets verfügbar:**

+-----------------------+----------------------------------+
| Preset                | Beschreibung                     |
+=======================+==================================+
| 🧚 Märchen            | Ivan Bilibin inspiriert          |
+-----------------------+----------------------------------+
| 🎬 Cinematisch        | Filmische Kompositionen          |
+-----------------------+----------------------------------+
| 🎨 Aquarell           | Weiche Kinderbuch-Illustration   |
+-----------------------+----------------------------------+
| 📚 Manga/Anime        | Japanischer Stil                 |
+-----------------------+----------------------------------+
| 📷 Fotorealistisch    | Hoher Realismus                  |
+-----------------------+----------------------------------+
| 🐉 Fantasy/Episch     | Dramatische Fantasy-Kunst        |
+-----------------------+----------------------------------+
| ⚙️ Steampunk          | Viktorianisch-industriell        |
+-----------------------+----------------------------------+

2. Charaktere definieren
------------------------

Erstellen Sie visuelle Definitionen für Ihre Buchcharaktere.

**Navigation:** Admin → Writing Hub → Charakter-Prompts → Hinzufügen

.. code-block:: text

   Name:           Arman
   Rolle:          ⭐ Protagonist
   
   Erscheinung:    Young Kazakh hero, 16-18 years old, 
                   athletic build, almond-shaped dark eyes
   
   Kleidung:       Traditional chapan in deep blue with 
                   gold geometric patterns, leather boots
   
   Gegenstände:    Ancestral dagger with turquoise inlay
   
   Standard-Ausdruck: expression of courage and wonder

**Rollen-Typen:**

- **⭐ Protagonist** - Hauptfigur
- **👿 Antagonist** - Gegenspieler
- **🧙 Mentor** - Weise Figur
- **🤝 Sidekick** - Begleiter
- **💕 Love Interest** - Romantische Verbindung
- **👥 Nebenrolle** - Supporting Character

3. Orte anlegen
---------------

Definieren Sie wiederkehrende Schauplätze.

**Navigation:** Admin → Writing Hub → Ort-Prompts → Hinzufügen

.. code-block:: text

   Name:           Die Steppe
   Typ:            🏞️ Landschaft
   
   Umgebung:       Vast golden Kazakh steppe, wind sweeping 
                   through feather grass, endless horizon
   
   Beleuchtung (Tag):    Golden sunlight, dramatic sky
   Beleuchtung (Nacht):  Star-filled sky, moonlit landscape
   
   Atmosphäre:     Epic and mystical atmosphere

**Ort-Typen:**

- 🏠 Innenraum
- 🌄 Außenbereich
- 🏞️ Landschaft
- 🏙️ Stadt
- ✨ Übernatürlich

4. Kulturelle Elemente (Optional)
---------------------------------

Für authentische kulturelle Darstellung.

.. code-block:: text

   Lokaler Begriff:    Kiiz üy
   Englisch:           Yurt
   Deutsch:            Jurte
   Kategorie:          🏛️ Architektur
   
   Visual Prompt:      Traditional Kazakh felt tent with 
                       shyrdak carpets and ornate decorations

Das System ersetzt automatisch kulturelle Begriffe durch ihre visuellen Beschreibungen.

Verwendung im Writing Hub
=========================

Automatische Prompt-Generierung
-------------------------------

1. Öffnen Sie ein Kapitel in Ihrem Buchprojekt
2. Klicken Sie auf **"Illustration generieren"**
3. Das System:
   
   - Analysiert den Kapiteltext
   - Erkennt erwähnte Charaktere automatisch
   - Wählt passende Orte aus
   - Wendet den Master-Stil an
   - Generiert den optimierten Prompt

Manuelle Anpassung
------------------

Sie können den generierten Prompt vor der Bildgenerierung anpassen:

.. code-block:: text

   [Automatisch generiert]
   Arman standing in the vast steppe at dawn...
   
   ✏️ [Hier können Sie den Prompt editieren]
   
   [Generieren]

Best Practices
==============

1. Master-Stil zuerst
---------------------

Definieren Sie immer zuerst den Master-Stil, bevor Sie andere Komponenten anlegen.
Der Master-Stil wird zu **jedem** generierten Prompt hinzugefügt.

2. Konsistente Beschreibungen
-----------------------------

Verwenden Sie konsistente Terminologie in allen Komponenten:

.. code-block:: text

   ✅ GUT:
   "golden steppe" (überall gleich)
   
   ❌ SCHLECHT:
   "golden steppe" / "yellow grassland" / "amber plains"
   (inkonsistent)

3. Charaktere verknüpfen
------------------------

Verknüpfen Sie Prompt-Charaktere mit Ihren Story-Charakteren:

.. code-block:: text

   Prompt-Charakter "Arman" 
        ↓
   Story-Charakter "Arman" (aus Characters-Tabelle)

4. Negative Prompts nutzen
--------------------------

Definieren Sie was **nicht** im Bild erscheinen soll:

.. code-block:: text

   Standard:  blurry, low quality, text, watermark, 
              signature, ugly, deformed
   
   Erweitert: photo, 3d render, anime, cartoon
              (wenn Sie einen bestimmten Stil wollen)

Presets verwenden
=================

Kasachisches Märchen Preset
---------------------------

Für orientalische Märchenillustrationen:

.. code-block:: python

   # In Django Shell
   from apps.writing_hub.handlers.prompt_builder_handler import PromptPresetFactory
   
   # Preset für Projekt erstellen
   result = PromptPresetFactory.create_kazakh_fairytale_preset(project_id=17)
   
   # Erstellte Komponenten:
   # - Master-Stil: "Kasachisches Märchen"
   # - 2 Charaktere: Arman, Baqsy
   # - 2 Orte: Die Steppe, Die Jurte
   # - 5 Kulturelle Elemente
   # - 4 Szenen-Templates

Eigene Presets erstellen
------------------------

Sie können eigene Presets für wiederkehrende Projekttypen erstellen.
Siehe :ref:`prompt-system-technical` für Details.

Fehlerbehebung
==============

"Kein Master-Stil definiert"
----------------------------

**Problem:** Bildgenerierung schlägt fehl.

**Lösung:** Erstellen Sie einen Master-Stil für das Projekt im Admin.

Charaktere werden nicht erkannt
-------------------------------

**Problem:** Charaktere im Text werden nicht automatisch erkannt.

**Lösung:** 

1. Prüfen Sie die Schreibweise des Namens
2. Der Name muss exakt übereinstimmen (case-insensitive)
3. Aktivieren Sie den Charakter (``is_active=True``)

Stil sieht inkonsistent aus
---------------------------

**Problem:** Bilder haben unterschiedliche Stile.

**Lösung:**

1. Prüfen Sie ``guidance_scale`` - niedrigere Werte = mehr Variation
2. Aktivieren Sie ``use_fixed_seed`` für Konsistenz
3. Vereinheitlichen Sie den ``style_base_prompt``

Weiterführende Dokumentation
============================

- :ref:`prompt-system-technical` - Technische Referenz für Entwickler
- :doc:`../hubs/writing-hub` - Writing Hub Übersicht
- :doc:`../reference/handlers` - Handler-Referenz

