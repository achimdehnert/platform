# Writing Hub

**Status:** ✅ Production  
**Domain:** `writing_hub`  
**URL:** `/writing-hub/`

---

## Übersicht

Der Writing Hub ist die zentrale Anwendung für AI-gestützte Bucherstellung. Er unterstützt den kompletten Workflow von der Idee bis zum fertigen Buch.

```{mermaid}
flowchart LR
    A[Idee] --> B[Projekt]
    B --> C[Charaktere]
    B --> D[Welten]
    C --> E[Outline]
    D --> E
    E --> F[Kapitel]
    F --> G[Lektorat]
    G --> H[Export]
```

## Features

- **Buchprojekte:** Verwaltung von Buchprojekten mit Metadaten
- **Charaktere:** AI-generierte Charakterprofile mit Beziehungen
- **Welten:** Worldbuilding mit Locations und Regeln
- **Kapitel:** AI-gestützte Kapitelgenerierung
- **Style Lab:** Analyse und Training von Schreibstilen
- **Lektorat:** Korrektur und Verbesserungsvorschläge

## Schnellstart

### Projekt erstellen

```python
from apps.writing_hub.models import BookProject

project = BookProject.objects.create(
    title="Mein Roman",
    genre="fantasy",
    description="Eine epische Geschichte...",
    target_word_count=80000
)
```

### Charakter hinzufügen

```python
from apps.bfagent.models import Characters

character = Characters.objects.create(
    book_project=project,
    name="Elena",
    role="protagonist",
    age=25,
    description="Die mutige Heldin...",
    backstory="Geboren in einem kleinen Dorf..."
)
```

## Handler

Der Writing Hub nutzt folgende Handler:

| Handler | Typ | Beschreibung |
|---------|-----|--------------|
| `CharacterGeneratorHandler` | 🤖 AI | Generiert Charakterprofile |
| `ChapterWriterHandler` | 🤖 AI | Schreibt Kapitel |
| `StoryStructureHandler` | ⚙️ Rule | Wendet Story-Strukturen an |
| `IllustrationHandler` | 🤖 AI | Generiert Illustrationen |
| `PDFExportHandler` | 🔧 Utility | Exportiert als PDF |

### World Handlers (NEU)

AI-gestützte Weltengenerierung via LLMAgent:

| Handler | Quality | Beschreibung |
|---------|---------|--------------|
| `WorldGeneratorHandler` | balanced | Generiert Weltgrundlagen (Beschreibung, Geographie, Kultur) |
| `WorldExpanderHandler` | balanced | Erweitert Aspekte (Magie, Politik, Wirtschaft, Geschichte) |
| `LocationGeneratorHandler` | fast | Generiert Orte (Kontinente, Städte, Wahrzeichen) |
| `WorldRuleGeneratorHandler` | fast | Generiert Weltregeln pro Kategorie |
| `WorldConsistencyCheckerHandler` | best | Prüft Konsistenz, findet Widersprüche |

**Unterstützte Sprachen:** 🇩🇪 Deutsch, 🇬🇧 English, 🇪🇸 Español, 🇫🇷 Français, 🇮🇹 Italiano, 🇵🇹 Português

```python
# Beispiel: Welt generieren
from apps.writing_hub.handlers.world_handlers import WorldGeneratorHandler

result = WorldGeneratorHandler.handle({
    "name": "Eldoria",
    "world_type": "fantasy",
    "seed_idea": "Eine Welt wo Magie aus Emotionen entsteht",
    "language": "de"  # Ausgabesprache
})

if result["success"]:
    print(result["description"])
    print(result["geography"])
    print(result["culture"])
```

**API Endpoints:**

| Endpoint | Beschreibung |
|----------|--------------|
| `POST /writing-hub/worlds/ai/generate/` | Welt-Grundlagen generieren |
| `POST /writing-hub/worlds/<id>/ai/expand/` | Aspekt erweitern |
| `POST /writing-hub/worlds/<id>/ai/locations/` | Orte generieren |
| `POST /writing-hub/worlds/<id>/ai/rules/` | Regeln generieren |
| `POST /writing-hub/worlds/<id>/ai/consistency/` | Konsistenzprüfung |

### Beispiel: Kapitel generieren

```python
from apps.writing_hub.handlers import ChapterWriterHandler

handler = ChapterWriterHandler()
result = await handler.execute({
    "project_id": project.id,
    "chapter_number": 1,
    "outline_beat": "Der Held verlässt sein Dorf",
    "word_count": 3000
})

print(result.content)
```

## Models

### BookProject

Hauptmodell für Buchprojekte.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `title` | CharField | Buchtitel |
| `genre` | CharField | Genre (fantasy, scifi, etc.) |
| `description` | TextField | Kurzbeschreibung |
| `target_word_count` | IntegerField | Ziel-Wortanzahl |
| `status` | CharField | Status (draft, writing, editing, published) |
| `created_at` | DateTimeField | Erstellungsdatum |

### Chapter

Kapitel eines Buchprojekts.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `book` | ForeignKey | Zugehöriges Buch |
| `chapter_number` | IntegerField | Kapitelnummer |
| `title` | CharField | Kapiteltitel |
| `content` | TextField | Kapitelinhalt |
| `word_count` | IntegerField | Aktuelle Wortanzahl |
| `status` | CharField | Status (draft, review, final) |

### Character

Charaktere in einem Buchprojekt.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `book_project` | ForeignKey | Zugehöriges Buch |
| `name` | CharField | Charaktername |
| `role` | CharField | Rolle (protagonist, antagonist, supporting) |
| `description` | TextField | Beschreibung |
| `backstory` | TextField | Hintergrundgeschichte |
| `profile_data` | JSONField | Erweiterte Profilinformationen |

## Views & URLs

| URL | View | Beschreibung |
|-----|------|--------------|
| `/writing-hub/` | `dashboard` | Dashboard mit Statistiken |
| `/writing-hub/projects/` | `projects_list` | Projektliste |
| `/writing-hub/project/<id>/` | `project_detail` | Projektdetails |
| `/writing-hub/project/<id>/chapters/` | `chapter_list` | Kapitelliste |
| `/writing-hub/style-lab/` | `style_lab_dashboard` | Style Lab |
| `/writing-hub/worlds/` | `world_dashboard` | Welten-Dashboard |

## Konfiguration

### AI-Provider

```python
# In Django Admin: /admin/bfagent/llm/
# Oder via Code:
from apps.bfagent.models import Llms

llm = Llms.objects.get(name="gpt-4")
# Wird automatisch für AI-Handler verwendet
```

### Story-Strukturen

Verfügbare Strukturen:
- **Save the Cat** - 15 Beats für emotionale Resonanz
- **Hero's Journey** - 12 Stufen der Heldenreise
- **Three-Act Structure** - Klassische Drei-Akt-Struktur

## Siehe auch

- {doc}`/reference/handlers` - Handler API-Referenz
- {doc}`/reference/models` - Model API-Referenz
- {doc}`/guides/ai-integration` - AI Integration Guide
