# Workflow System

Das Workflow System automatisiert Content-Generierung durch verkettete Handler und Agents.

## Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                    Workflow Execution                            │
├─────────────────────────────────────────────────────────────────┤
│  Step 1: CharacterHandler                                        │
│    → Load context → Generate characters → Save to DB             │
├─────────────────────────────────────────────────────────────────┤
│  Step 2: OutlineHandler                                          │
│    → Load characters → Generate outline → Save to DB             │
├─────────────────────────────────────────────────────────────────┤
│  Step 3: ChapterWriter                                           │
│    → Load outline → Generate chapters → Save to DB               │
├─────────────────────────────────────────────────────────────────┤
│  Step 4: EditorHandler                                           │
│    → Load chapters → Review & edit → Update DB                   │
└─────────────────────────────────────────────────────────────────┘
```

## Handler

### CharacterHandler

```python
class CharacterHandler:
    async def generate_characters(
        self,
        workflow_id: int,
        count: int = 3,
        genre: str = "fantasy",
        use_ai: bool = False,
    ) -> list[Character]:
        # Load context
        workflow = await Workflow.objects.aget(id=workflow_id)
        
        # Generate (AI or Mock)
        if use_ai:
            characters = await self._generate_with_ai(genre, count)
        else:
            characters = self._generate_mock(genre, count)
        
        # Save to DB
        return await self._save_characters(workflow, characters)
```

### ChapterWriter

```python
class ChapterWriter:
    async def write_chapters(
        self,
        workflow_id: int,
        chapter_count: int = 3,
    ) -> list[Chapter]:
        # Load context
        context = await self._load_context(workflow_id)
        
        # Generate chapters
        chapters = []
        for i in range(chapter_count):
            chapter = await self._generate_chapter(context, i + 1)
            chapters.append(chapter)
        
        return chapters
```

## Context Propagation

Context fließt zwischen Handlern:

```python
context = {
    "workflow_id": 4,
    "genre": "fantasy",
    "characters": [26, 27, 28],  # IDs, nicht Objekte!
    "outline_id": 12,
    "settings": {...},
}
```

## n8n Integration

Visual Workflow Builder für externe Orchestrierung:

```
n8n (5679) → Django API (/api/n8n/) → Workflow System → Handlers → DB
```

### API Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /api/n8n/health` | Health Check |
| `POST /api/n8n/workflow/execute` | Workflow starten |
| `GET /api/n8n/workflow/{id}/status` | Status prüfen |
| `POST /api/n8n/characters/generate` | Charaktere generieren |
| `POST /api/n8n/chapters/generate` | Kapitel generieren |

## Test Commands

```bash
# Test Handlers
python manage.py test_character_handler --workflow-id 4
python manage.py test_chapter_writer --workflow-id 4 --chapter-count 3
python manage.py test_editor_handler --workflow-id 4

# Test AI Mode
python manage.py test_ai_character --workflow-id 4 --genre fantasy --use-ai
```
