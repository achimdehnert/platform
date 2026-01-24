# Import Framework Konzept
## Prompt-Framework + Template-Framework für intelligenten Buchimport

---

## 1. ARCHITEKTUR-ÜBERSICHT

```
┌─────────────────────────────────────────────────────────────────┐
│                     IMPORT PIPELINE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ Dokument │───▶│ Typ-Erkennung│───▶│ Template-Auswahl     │  │
│  │ (.md)    │    │ (LLM Step 1) │    │ (Serie/Standalone/   │  │
│  └──────────┘    └──────────────┘    │  Exposé/Manuskript)  │  │
│                                       └──────────────────────┘  │
│                                                 │                │
│                                                 ▼                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              PROMPT CHAIN (LLM Steps 2-N)                 │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Step 2: Metadaten extrahieren (Titel, Genre, Format)     │  │
│  │ Step 3: Charaktere extrahieren (mit Schema-Validierung)  │  │
│  │ Step 4: Welten/Locations extrahieren (Hierarchie)        │  │
│  │ Step 5: Struktur extrahieren (Kapitel, Akte, Plots)      │  │
│  │ Step 6: Beziehungen erkennen (Char↔Char, Char↔World)     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                 │                │
│                                                 ▼                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              UNIFIED IMPORT SCHEMA                        │  │
│  │  (JSON → Django Models → Database)                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. PROMPT-FRAMEWORK

### 2.1 Prompt Registry (DB-gesteuert)

```python
# apps/writing_hub/models_prompts.py

class ImportPromptTemplate(models.Model):
    """Prompt-Templates für verschiedene Extraktionsschritte"""
    
    name = models.CharField(max_length=100, unique=True)
    step = models.CharField(max_length=50, choices=[
        ('type_detection', 'Typ-Erkennung'),
        ('metadata', 'Metadaten'),
        ('characters', 'Charaktere'),
        ('worlds', 'Welten/Locations'),
        ('structure', 'Struktur/Kapitel'),
        ('relationships', 'Beziehungen'),
    ])
    system_prompt = models.TextField()
    user_prompt_template = models.TextField()  # Mit {content}, {context} Platzhaltern
    output_schema = models.JSONField()  # JSON Schema für Validierung
    
    # LLM-Einstellungen
    temperature = models.FloatField(default=0.2)
    max_tokens = models.IntegerField(default=2000)
    
    # Versionierung
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['step', 'version']
```

### 2.2 Prompt-Templates

#### Step 1: Typ-Erkennung
```yaml
name: "detect_document_type"
step: "type_detection"
system_prompt: |
  Du bist ein Experte für Buchmanuskript-Analyse.
  Erkenne den Dokumenttyp anhand der Struktur.
  
user_prompt_template: |
  Analysiere dieses Dokument und bestimme den Typ:
  
  DOKUMENT (erste 2000 Zeichen):
  ---
  {content_preview}
  ---
  
  Mögliche Typen:
  - SERIE: Mehrere Bände, Serienübersicht, durchgehende Charaktere
  - STANDALONE: Einzelnes Buch, keine Bandstruktur
  - EXPOSE: Verlagsformat mit Pitch, Inhaltsangabe, Marktpotenzial
  - MANUSKRIPT: Fertiger Text mit Kapiteln
  - PLANNING: Outline, Notizen, Ideen
  - MIXED: Kombination aus mehreren
  
  Antworte als JSON:
  {
    "document_type": "SERIE|STANDALONE|EXPOSE|MANUSKRIPT|PLANNING|MIXED",
    "confidence": 0.0-1.0,
    "detected_elements": ["logline", "characters", "chapters", ...],
    "suggested_template": "serie_full|standalone_full|expose|manuscript"
  }

output_schema:
  type: object
  required: [document_type, confidence]
  properties:
    document_type:
      type: string
      enum: [SERIE, STANDALONE, EXPOSE, MANUSKRIPT, PLANNING, MIXED]
    confidence:
      type: number
      minimum: 0
      maximum: 1
```

#### Step 2: Metadaten-Extraktion
```yaml
name: "extract_metadata"
step: "metadata"
system_prompt: |
  Extrahiere Buchmetadaten. Sei präzise und erfinde nichts.
  
user_prompt_template: |
  Extrahiere die Metadaten aus diesem Dokument:
  
  DOKUMENT:
  ---
  {content}
  ---
  
  JSON-Format:
  {
    "title": "Haupttitel",
    "subtitle": "Untertitel oder null",
    "genre": "Thriller|Romance|Fantasy|SciFi|...",
    "subgenre": ["Dark Romance", "Eco-Thriller", ...],
    "logline": "Ein-Satz-Zusammenfassung",
    "premise": "Ausführliche Prämisse (2-5 Sätze)",
    "themes": ["Thema 1", "Thema 2", ...],
    "setting_time": "2026|Mittelalter|...",
    "setting_location": "München|Berlin|Fantasy-Welt",
    "format": {
      "type": "serie|standalone|trilogie",
      "planned_books": 1-N,
      "current_status": "planning|writing|complete"
    },
    "target_audience": {
      "age_range": "25-55",
      "gender_focus": "all|female|male",
      "comparable_authors": ["Fitzek", "Link", ...]
    },
    "word_count_estimate": 50000
  }
```

#### Step 3: Charakter-Extraktion
```yaml
name: "extract_characters"
step: "characters"
system_prompt: |
  Du bist Experte für Charakteranalyse in Buchmanuskripten.
  Extrahiere ALLE Charaktere mit maximaler Detailtiefe.
  Unterscheide zwischen explizit genannten und implizierten Informationen.

user_prompt_template: |
  Extrahiere alle Charaktere aus diesem Dokument:
  
  BEREITS ERKANNTE METADATEN:
  {metadata_context}
  
  DOKUMENT:
  ---
  {content}
  ---
  
  Für JEDEN Charakter, extrahiere (wenn vorhanden):
  {
    "characters": [
      {
        "name": "Vollständiger Name",
        "aliases": ["Spitzname", "Alias"],
        "role": "protagonist|antagonist|love_interest|mentor|ally|minor",
        "importance": 1-5,
        
        "demographics": {
          "age": 36,
          "age_description": "Mitte 30",
          "gender": "female|male|nonbinary",
          "nationality": "deutsch",
          "ethnicity": "deutsch-spanisch"
        },
        
        "profession": {
          "job_title": "Staatsanwältin",
          "organization": "Staatsanwaltschaft Berlin",
          "status": "aktiv|ehemalig|undercover"
        },
        
        "psychology": {
          "background": "Kurzbiografie",
          "motivation": "Was treibt sie an?",
          "wound": "Innere Verletzung/Trauma",
          "strength": "Hauptstärke",
          "weakness": "Hauptschwäche",
          "secret": "Verborgenes Geheimnis",
          "arc": "Von X zu Y Entwicklung"
        },
        
        "appearance": "Physische Beschreibung falls vorhanden",
        
        "relationships": [
          {"to": "Anderer Charakter", "type": "love_interest|enemy|family|colleague"}
        ],
        
        "source_confidence": "explicit|inferred"
      }
    ]
  }
```

#### Step 4: Welten/Locations-Extraktion
```yaml
name: "extract_worlds"
step: "worlds"
system_prompt: |
  Extrahiere alle Schauplätze und Welten mit Hierarchie.
  Erkenne: Land → Stadt → Stadtteil → Konkreter Ort
  
user_prompt_template: |
  Extrahiere alle Locations aus diesem Dokument:
  
  KONTEXT:
  {metadata_context}
  
  DOKUMENT:
  ---
  {content}
  ---
  
  Hierarchische Struktur:
  {
    "worlds": [
      {
        "name": "Deutschland",
        "type": "country",
        "children": [
          {
            "name": "Berlin 2027",
            "type": "city",
            "time_period": "2027",
            "description": "Beschreibung der Stadt",
            "atmosphere": "Stimmung",
            "features": ["Merkmal 1", "Merkmal 2"],
            "children": [
              {
                "name": "BRS-Zentrale (Lichtenberg)",
                "type": "building",
                "description": "Ehemaliges Stasi-Archiv",
                "symbolism": "Neue Überwachung auf alten Fundamenten",
                "scenes": ["Kapitel 3", "Kapitel 15"]
              }
            ]
          }
        ]
      }
    ]
  }
```

#### Step 5: Struktur-Extraktion
```yaml
name: "extract_structure"
step: "structure"
system_prompt: |
  Extrahiere die Buchstruktur: Akte, Kapitel, Plot Points.
  Erkenne narrative Strukturen (3-Akt, 5-Akt, Hero's Journey).

user_prompt_template: |
  Extrahiere die Struktur:
  
  DOKUMENT:
  ---
  {content}
  ---
  
  {
    "structure_type": "three_act|five_act|heroes_journey|episodic",
    "pov": "first_person|third_limited|third_omniscient|dual_pov|multiple",
    "timeline": "linear|nonlinear|parallel",
    
    "acts": [
      {
        "number": 1,
        "name": "Der Verdacht",
        "description": "Exposition und Inciting Incident",
        "chapters": [
          {
            "number": 1,
            "title": "Der Morgen danach",
            "summary": "Kurze Zusammenfassung",
            "pov_character": "Mira",
            "location": "München",
            "plot_function": "exposition|inciting_incident|rising_action|midpoint|climax|resolution"
          }
        ]
      }
    ],
    
    "plot_points": [
      {
        "type": "inciting_incident|first_plot_point|midpoint|all_is_lost|climax|resolution",
        "description": "Was passiert",
        "chapter": 3
      }
    ],
    
    "series_structure": {
      "books": [
        {
          "number": 1,
          "title": "Schwarzwasser",
          "focus": "Der Mord, Lena vs. Max",
          "romance_arc": "Enemies to reluctant allies",
          "ending_type": "cliffhanger|resolution|open"
        }
      ]
    }
  }
```

---

## 3. TEMPLATE-FRAMEWORK

### 3.1 Eingabe-Templates (für User-Dokumente)

```python
# apps/writing_hub/templates_import.py

IMPORT_TEMPLATES = {
    "serie_full": {
        "name": "Serie (Vollständig)",
        "description": "Für mehrbändige Serien mit detaillierten Charakterprofilen",
        "sections": [
            {"name": "Titel", "marker": "# ", "required": True},
            {"name": "Logline", "marker": "## Logline", "required": True},
            {"name": "Premise", "marker": "## Premise", "required": True},
            {"name": "Themen", "marker": "## Themen", "required": False},
            {"name": "Charaktere", "marker": "## Charaktere", "required": True},
            {"name": "Welten", "marker": "## Welten", "required": False},
            {"name": "Struktur", "marker": "## Kapitel", "required": False},
            {"name": "Serienübersicht", "marker": "## Serienübersicht", "required": False},
        ],
        "character_schema": "detailed",  # age, background, wound, arc, etc.
        "world_schema": "hierarchical",   # Land → Stadt → Ort
    },
    
    "standalone_simple": {
        "name": "Standalone (Einfach)",
        "description": "Einzelbuch mit Basis-Informationen",
        "sections": [
            {"name": "Titel", "marker": "# ", "required": True},
            {"name": "Logline", "marker": "## Logline", "required": True},
            {"name": "Charaktere", "marker": "## Charaktere", "required": True},
            {"name": "Handlung", "marker": "## Handlung", "required": False},
        ],
        "character_schema": "simple",  # name, role, description
        "world_schema": "flat",        # Nur Namen
    },
    
    "expose": {
        "name": "Exposé (Verlagsformat)",
        "description": "Für Verlagseinreichungen",
        "sections": [
            {"name": "Bibliografie", "marker": "## Bibliografische", "required": True},
            {"name": "Pitch", "marker": "## Kurzinhalt", "required": True},
            {"name": "Inhaltsangabe", "marker": "## Inhaltsangabe", "required": True},
            {"name": "Figuren", "marker": "## Figuren", "required": True},
            {"name": "Themen", "marker": "## Themen", "required": False},
            {"name": "Markt", "marker": "## Marktpotenzial", "required": False},
        ],
        "character_schema": "compact",
        "world_schema": "minimal",
    },
    
    "manuscript": {
        "name": "Manuskript",
        "description": "Fertiger Text mit Kapiteln",
        "sections": [
            {"name": "Kapitel", "marker": "## Kapitel", "required": True, "repeating": True},
        ],
        "character_schema": "inferred",  # Aus Text extrahieren
        "world_schema": "inferred",
    },
}
```

### 3.2 Ausgabe-Templates (für Django Models)

```python
# Mapping: Import Schema → Django Models

MODEL_MAPPING = {
    "metadata": {
        "model": "BookProjects",
        "fields": {
            "title": "title",
            "logline": "tagline",
            "premise": "story_premise",
            "genre": "genre",
            "setting_location": "setting_location",
            "word_count_estimate": "target_word_count",
        }
    },
    
    "characters": {
        "model": "Characters",
        "fields": {
            "name": "name",
            "role": "role",
            "demographics.age": "age",
            "psychology.background": "background",
            "psychology.motivation": "motivation",
            "psychology.arc": "arc",
            "appearance": "appearance",
        }
    },
    
    "worlds": {
        "model": "Worlds",
        "fields": {
            "name": "name",
            "description": "description",
            # Hierarchie über parent_id
        }
    },
    
    "chapters": {
        "model": "BookChapters",
        "fields": {
            "number": "chapter_number",
            "title": "title",
            "summary": "summary",
            "pov_character": "pov_character",
        }
    },
}
```

---

## 4. IMPLEMENTIERUNGS-FLOW

### 4.1 Import Service (Refactored)

```python
# apps/writing_hub/services/import_service.py

class SmartImportService:
    """Intelligenter Import mit Prompt Chain"""
    
    LLM_GATEWAY = "http://127.0.0.1:8100"
    
    def __init__(self):
        self.prompts = self._load_prompts()
    
    async def import_document(self, content: str, filename: str) -> ImportResult:
        """Haupt-Import-Pipeline"""
        
        # Step 1: Typ erkennen
        doc_type = await self._detect_type(content)
        
        # Step 2: Template auswählen
        template = IMPORT_TEMPLATES[doc_type.suggested_template]
        
        # Step 3-N: Extraktions-Chain
        metadata = await self._extract_metadata(content, template)
        characters = await self._extract_characters(content, metadata, template)
        worlds = await self._extract_worlds(content, metadata, template)
        structure = await self._extract_structure(content, metadata, template)
        
        # Step N+1: Beziehungen
        relationships = await self._extract_relationships(characters, worlds)
        
        # Validieren und zusammenführen
        return ImportResult(
            metadata=metadata,
            characters=characters,
            worlds=worlds,
            structure=structure,
            relationships=relationships,
            template_used=template['name'],
            confidence=self._calculate_confidence([metadata, characters, worlds])
        )
    
    async def _call_llm(self, prompt_name: str, **kwargs) -> dict:
        """LLM-Aufruf über MCP Gateway"""
        prompt = self.prompts[prompt_name]
        
        user_prompt = prompt['user_prompt_template'].format(**kwargs)
        
        response = await httpx.post(
            f"{self.LLM_GATEWAY}/generate",
            json={
                "prompt": user_prompt,
                "system_prompt": prompt['system_prompt'],
                "temperature": prompt.get('temperature', 0.2),
                "max_tokens": prompt.get('max_tokens', 2000),
                "response_format": "json"
            }
        )
        
        result = response.json()
        
        # Schema-Validierung
        if prompt.get('output_schema'):
            self._validate_schema(result['content'], prompt['output_schema'])
        
        return result['content']
```

---

## 5. VORTEILE

| Aspekt | Ohne Framework | Mit Framework |
|--------|----------------|---------------|
| **Flexibilität** | Hardcoded Prompts | DB-gesteuerte Prompts |
| **Wartbarkeit** | Code-Änderungen nötig | Admin-Panel reicht |
| **Qualität** | Inkonsistente Extraktion | Schema-Validierung |
| **Erweiterbarkeit** | Neuer Code pro Format | Neues Template anlegen |
| **Debugging** | Schwer nachvollziehbar | Step-by-Step Logging |
| **A/B Testing** | Nicht möglich | Prompt-Versionierung |

---

## 6. NÄCHSTE SCHRITTE

1. **Models erstellen**: `ImportPromptTemplate`, `ImportTemplate`
2. **Migration**: Prompt-Templates in DB laden
3. **Service refactoren**: `SmartImportService` implementieren
4. **Admin-Interface**: Prompts bearbeitbar machen
5. **Tests**: Mit allen 3 Dokumenttypen testen
