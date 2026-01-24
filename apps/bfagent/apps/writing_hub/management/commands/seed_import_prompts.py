"""
Management command to seed ImportPromptTemplate for Import Framework V2.

These prompts define the multi-step LLM pipeline for document analysis.

Usage:
    python manage.py seed_import_prompts
    python manage.py seed_import_prompts --clear
"""

from django.core.management.base import BaseCommand
from apps.writing_hub.models_import_framework import ImportPromptTemplate


PROMPT_TEMPLATES = [
    # Step 1: Type Detection
    {
        'step_code': 'type_detection',
        'step_name': 'Document Type Detection',
        'step_name_de': 'Dokumenttyp-Erkennung',
        'description': 'Erkennt den Typ des hochgeladenen Dokuments (Exposé, Manuskript, Serie, etc.)',
        'step_order': 10,
        'system_prompt': '''Du bist ein Experte für Buchanalyse und Dokumentklassifikation.
Analysiere das Dokument und bestimme den Typ.''',
        'user_prompt_template': '''Analysiere dieses Dokument und bestimme den Typ:

DOKUMENT:
---
{content}
---

Antworte NUR als JSON:
{{
  "document_type": "expose|manuscript|outline|character_sheet|world_bible|series_bible|mixed",
  "confidence": 0.0-1.0,
  "is_series": true|false,
  "book_number": 1,
  "total_planned_books": 1,
  "language": "de|en",
  "word_count_estimate": 0,
  "completeness": "complete|partial|fragment",
  "indicators": ["Indikator 1", "Indikator 2"]
}}''',
        'output_schema': {
            'type': 'object',
            'required': ['document_type', 'confidence'],
            'properties': {
                'document_type': {'type': 'string', 'enum': ['expose', 'manuscript', 'outline', 'character_sheet', 'world_bible', 'series_bible', 'mixed']},
                'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
                'is_series': {'type': 'boolean'},
                'book_number': {'type': 'integer'},
                'total_planned_books': {'type': 'integer'},
                'language': {'type': 'string'},
                'word_count_estimate': {'type': 'integer'},
                'completeness': {'type': 'string'},
                'indicators': {'type': 'array', 'items': {'type': 'string'}}
            }
        },
        'temperature': 0.1,
        'max_tokens': 500,
        'preferred_model': 'gpt-4o',
        'fallback_model': 'gpt-4o-mini',
    },
    
    # Step 2: Metadata Extraction
    {
        'step_code': 'metadata_extraction',
        'step_name': 'Metadata Extraction',
        'step_name_de': 'Metadaten-Extraktion',
        'description': 'Extrahiert Titel, Genre, Themen, Stil und weitere Metadaten',
        'step_order': 20,
        'system_prompt': '''Du bist ein Experte für Buchanalyse.
Extrahiere alle relevanten Metadaten aus dem Dokument.''',
        'user_prompt_template': '''Extrahiere die Metadaten aus diesem {document_type}:

DOKUMENT:
---
{content}
---

Antworte NUR als JSON:
{{
  "title": "Titel des Werks",
  "subtitle": "Untertitel oder null",
  "genre_primary": "Hauptgenre",
  "genre_secondary": ["Nebengenre 1", "Nebengenre 2"],
  "format_type": "standalone|series|trilogy",
  "planned_books": 1,
  "book_number": 1,
  "logline": "Ein-Satz-Zusammenfassung",
  "premise": "Erweiterte Prämisse (2-5 Sätze)",
  "central_question": "Thematische Kernfrage",
  "themes": ["Thema 1", "Thema 2"],
  "setting_time": "Zeitraum",
  "setting_location": "Hauptschauplatz",
  "pov": "first_person|third_limited|dual_pov|multiple|omniscient",
  "tense": "present|past",
  "narrative_voice": "Beschreibung der Erzählstimme",
  "prose_style": "Beschreibung des Prosa-Stils",
  "pacing": "Tempo-Beschreibung",
  "dialogue_style": "Dialog-Stil",
  "spice_level": "none|low|medium|high|null",
  "content_warnings": ["Warning 1"],
  "comparable_titles": ["Vergleichstitel 1"],
  "target_word_count": 80000,
  "target_audience": "Zielgruppe"
}}''',
        'temperature': 0.2,
        'max_tokens': 2000,
        'preferred_model': 'gpt-4o',
        'fallback_model': 'gpt-4o-mini',
    },
    
    # Step 3: Character Extraction
    {
        'step_code': 'character_extraction',
        'step_name': 'Character Extraction',
        'step_name_de': 'Charakter-Extraktion',
        'description': 'Extrahiert alle Charaktere mit psychologischer Tiefe',
        'step_order': 30,
        'system_prompt': '''Du bist ein Experte für Charakteranalyse.
Extrahiere ALLE Charaktere mit maximaler Detailtiefe.''',
        'user_prompt_template': '''Extrahiere ALLE Charaktere aus diesem Dokument:

METADATEN-KONTEXT:
Titel: {title}
Genre: {genre}
Themen: {themes}

DOKUMENT:
---
{content}
---

Für JEDEN Charakter extrahiere (soweit vorhanden):

Antworte NUR als JSON:
{{
  "characters": [
    {{
      "name": "Vollständiger Name",
      "aliases": ["Spitzname"],
      "role": "protagonist|antagonist|love_interest|mentor|ally|minor",
      "importance": 1-5,
      "age": "Alter oder Altersbereich",
      "gender": "female|male|nonbinary|null",
      "nationality": "Nationalität",
      "ethnicity": "Ethnische Herkunft",
      "occupation": "Beruf",
      "organization": "Firma/Organisation",
      "background": "Kurzbiografie",
      "motivation": "Was treibt sie an",
      "wound": "Innere Verletzung/Trauma",
      "strengths": ["Stärke 1", "Stärke 2"],
      "weaknesses": ["Schwäche 1", "Schwäche 2"],
      "secret": "Verborgenes Geheimnis",
      "dark_trait": "Dunkle Seite",
      "arc": "Von X zu Y Entwicklung",
      "voice_sample": "Beispiel-Dialog",
      "speech_patterns": "Sprachmuster",
      "personality": "Persönlichkeitsbeschreibung",
      "appearance": "Physische Beschreibung",
      "relationships": [
        {{"to": "Anderer Charakter", "type": "love_interest|enemy|family|colleague|friend"}}
      ],
      "source_confidence": "explicit|inferred"
    }}
  ]
}}''',
        'temperature': 0.2,
        'max_tokens': 4000,
        'preferred_model': 'gpt-4o',
        'fallback_model': 'gpt-4o-mini',
    },
    
    # Step 4: World/Location Extraction
    {
        'step_code': 'world_extraction',
        'step_name': 'World & Location Extraction',
        'step_name_de': 'Welt- und Schauplatz-Extraktion',
        'description': 'Extrahiert alle Schauplätze und Welten hierarchisch',
        'step_order': 40,
        'system_prompt': '''Du bist ein Experte für Weltenbau und Setting-Analyse.
Extrahiere ALLE Schauplätze und Welten hierarchisch.''',
        'user_prompt_template': '''Extrahiere ALLE Schauplätze und Welten aus diesem Dokument:

KONTEXT:
Titel: {title}
Setting: {setting_time} - {setting_location}

DOKUMENT:
---
{content}
---

Erstelle eine HIERARCHISCHE Struktur: Land → Stadt → Stadtteil → Gebäude → Raum

Antworte NUR als JSON:
{{
  "locations": [
    {{
      "name": "Name des Ortes",
      "type": "country|city|district|building|room|region|world",
      "parent": "Name des übergeordneten Ortes oder null",
      "description": "Beschreibung",
      "atmosphere": "Stimmung/Atmosphäre",
      "features": ["Merkmal 1", "Merkmal 2"],
      "symbolism": "Symbolische Bedeutung",
      "time_period": "Zeitraum",
      "scenes": ["Kapitel/Szene wo der Ort vorkommt"]
    }}
  ]
}}''',
        'temperature': 0.2,
        'max_tokens': 3000,
        'preferred_model': 'gpt-4o',
        'fallback_model': 'gpt-4o-mini',
    },
    
    # Step 5: Structure Extraction
    {
        'step_code': 'structure_extraction',
        'step_name': 'Structure Extraction',
        'step_name_de': 'Struktur-Extraktion',
        'description': 'Extrahiert Kapitel, Akte und Plot Points',
        'step_order': 50,
        'system_prompt': '''Du bist ein Experte für Buchstruktur und Plot-Analyse.
Erkenne die narrative Struktur und ordne Kapitel den Akten zu.''',
        'user_prompt_template': '''Extrahiere die Buchstruktur: Akte, Kapitel, Plot Points.

KONTEXT:
Titel: {title}
Genre: {genre}

DOKUMENT:
---
{content}
---

Erkenne die narrative Struktur und ordne Kapitel den Akten zu.

Antworte NUR als JSON:
{{
  "structure_type": "three_act|five_act|heroes_journey|episodic|custom",
  "chapters": [
    {{
      "number": 1,
      "title": "Kapiteltitel",
      "summary": "Kurze Zusammenfassung",
      "pov_character": "POV-Charakter oder null",
      "location": "Hauptschauplatz",
      "plot_function": "exposition|inciting_incident|rising_action|midpoint|crisis|climax|resolution",
      "act": 1,
      "key_events": ["Event 1", "Event 2"]
    }}
  ],
  "plot_points": [
    {{
      "type": "opening_image|catalyst|midpoint|all_is_lost|climax|final_image",
      "description": "Was passiert",
      "chapter": 1,
      "act": 1
    }}
  ],
  "series_context": {{
    "series_arc": "Übergreifender Serien-Arc",
    "threads_to_continue": ["Offener Handlungsstrang 1"]
  }}
}}''',
        'temperature': 0.2,
        'max_tokens': 4000,
        'preferred_model': 'gpt-4o',
        'fallback_model': 'gpt-4o-mini',
    },
]


class Command(BaseCommand):
    help = 'Seed ImportPromptTemplate for Import Framework V2 LLM pipeline'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing templates before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing prompt templates...')
            ImportPromptTemplate.objects.all().delete()

        self.stdout.write('Creating prompt templates...')
        
        for tpl_data in PROMPT_TEMPLATES:
            tpl, created = ImportPromptTemplate.objects.update_or_create(
                step_code=tpl_data['step_code'],
                defaults=tpl_data
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'  {status}: {tpl.step_name} (order: {tpl.step_order})')

        self.stdout.write(self.style.SUCCESS(
            f'Done! Created {len(PROMPT_TEMPLATES)} prompt templates for LLM pipeline.'
        ))
