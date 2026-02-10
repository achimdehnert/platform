Enrichment Actions
==================

.. note::
   Diese Seite wird zukünftig automatisch aus ``lkp_enrichment_action`` generiert
   via ``python manage.py generate_db_docs --include enrichment``.

Übersicht
---------

Die AI-Enrichment-Aktionen sind vollständig datenbankgetrieben.
Jede Aktion definiert:

- **Prompt-Template** mit Platzhaltern
- **Zielfelder** auf dem Entity-Model
- **Entity-Typ** (World, Character, Story, Scene)

Aktionen
--------

+---------------------+---------------+----------------------------------------+
| Code                | Entity        | Beschreibung                           |
+=====================+===============+========================================+
| world_describe      | World         | Welt-Beschreibung generieren           |
+---------------------+---------------+----------------------------------------+
| world_history       | World         | Geschichte der Welt                    |
+---------------------+---------------+----------------------------------------+
| character_backstory | Character     | Charakter-Hintergrundgeschichte        |
+---------------------+---------------+----------------------------------------+
| character_arc       | Character     | Charakter-Entwicklungsbogen            |
+---------------------+---------------+----------------------------------------+
| story_outline       | Story         | Story-Outline generieren               |
+---------------------+---------------+----------------------------------------+
| story_chapters      | Story         | Kapitelstruktur vorschlagen            |
+---------------------+---------------+----------------------------------------+
| scene_describe      | Scene         | Szenenbeschreibung                     |
+---------------------+---------------+----------------------------------------+
| scene_dialog        | Scene         | Dialog-Vorschlag                       |
+---------------------+---------------+----------------------------------------+

Charakter-Aktionen (seit 2026-02-10)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

+-------------------------+---------------+----------------------------------------+
| Code                    | Entity        | Beschreibung                           |
+=========================+===============+========================================+
| character_full_profile  | Character     | Vollständiges Charakterprofil (8 Felder)|
+-------------------------+---------------+----------------------------------------+
| character_profile       | Character     | Profil generieren                      |
+-------------------------+---------------+----------------------------------------+
| character_motivation    | Character     | Motivation generieren                  |
+-------------------------+---------------+----------------------------------------+

Flow
----

.. code-block:: text

   1. User wählt Aktion → HTMX POST /enrichment/<type>/<uuid>/execute/
   2. Service liest Prompt aus lkp_enrichment_action
   3. LLM generiert Text → Parse labeled fields
   4. Preview gespeichert in wh_enrichment_log (status=preview)
   5. User klickt "Übernehmen" → POST /apply/<log_id>/
   6. apply_preview() liest output_data aus Log
   7. Felder auf Entity gesetzt (mit CharField-Truncation)
   8. Log-Status → success

Character Trait Integration
--------------------------

Charaktere besitzen **bipolare Trait-Slider** (0–100) aus
``lkp_character_trait`` (z.B. Vorsichtig ↔ Mutig).

Die ``_build_context()`` Funktion in ``enrichment/services.py``
konvertiert Slider-Werte in natürlichsprachliche Beschreibungen:

- Wert ≤ 20 → "sehr {low_label}"
- Wert ≤ 40 → "eher {low_label}"
- Wert ≥ 60 → "eher {high_label}"
- Wert ≥ 80 → "sehr {high_label}"

Diese werden als ``{traits}`` Platzhalter im Prompt übergeben.
