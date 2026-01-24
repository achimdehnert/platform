# Story Engine - Implementation Guide

> **Focus**: Development Roadmap, Step-by-Step Implementation  
> **Status**: Planning  
> **Updated**: 2024-11-07

---

## 📅 Development Phases

### Phase 1: Foundation (4-6 Wochen)
**Goal**: Basic infrastructure working

#### Week 1-2: Django Models
**Tasks:**
- [ ] Create `models_story.py`
- [ ] Implement core models:
  - `StoryBible`
  - `StoryStrand`
  - `Character`
  - `Chapter`
  - `ChapterBeat`
- [ ] Create migrations
- [ ] Test models in Django shell
- [ ] Basic Admin interface

**Deliverable:** Working Django models with CRUD via Admin

---

#### Week 3-4: LangGraph Setup
**Tasks:**
- [ ] Create `apps/story_engine/` package
- [ ] Install LangGraph + dependencies
- [ ] Implement first agent (Story Architect)
- [ ] Simple workflow: Input → Agent → Output
- [ ] Test agent in isolation

**Deliverable:** One working Agent that can generate text

---

#### Week 5-6: Handler Integration
**Tasks:**
- [ ] Create `StoryGenerationHandler`
- [ ] Connect Handler → Agent
- [ ] Connect Handler → Database
- [ ] Extend `AgentAction` model with handler fields
- [ ] Create test view
- [ ] End-to-end test

**Deliverable:** Generate 1 chapter from UI via Handler → Agent

---

### Phase 2: Agent System (6-8 Wochen)
**Goal**: Multi-agent workflows

#### Week 7-10: Agent Crew
**Tasks:**
- [ ] Implement Writer Agent
- [ ] Implement Continuity Checker Agent
- [ ] Implement Editor Agent
- [ ] Create LangGraph workflow
- [ ] Agent collaboration tests
- [ ] Quality metrics

**Deliverable:** Multi-agent chapter generation pipeline

---

#### Week 11-14: Advanced Features
**Tasks:**
- [ ] Character Memory System
- [ ] Timeline Management
- [ ] Quality Assurance Checks
- [ ] Optional: Vector Store integration
- [ ] Performance optimization
- [ ] Error handling improvements

**Deliverable:** Production-ready generation system

---

### Phase 3: PoC Teaser (2-4 Wochen)
**Goal**: Real content generation

#### Week 15-16: Story Development
**Tasks:**
- [ ] Develop "Das Erwachen" Story Bible
- [ ] Create character dossiers
- [ ] Define world rules
- [ ] Plan 8-10 chapter beats
- [ ] Test with 1-2 chapters

**Deliverable:** Complete Story Bible

---

#### Week 17-18: Generation & Iteration
**Tasks:**
- [ ] Generate all chapters
- [ ] Quality review
- [ ] Continuity checks
- [ ] Iteration & refinement
- [ ] Final polish

**Deliverable:** Complete 15-20k word Teaser

---

## 👨‍💻 Step-by-Step: First Implementation

### Step 1: Create Story Models

```bash
# Create new file
touch apps/bfagent/models_story.py
```

```python
# apps/bfagent/models_story.py
from django.db import models
from django.utils import timezone

class StoryBible(models.Model):
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default='planning')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'story_bibles'
    
    def __str__(self):
        return self.title

# Add to apps/bfagent/models.py:
from .models_story import StoryBible, Character, Chapter
```

```bash
# Create migration
python manage.py makemigrations
python manage.py migrate
```

---

### Step 2: Setup story_engine Package

```bash
# Create package structure
mkdir -p apps/story_engine/agents
mkdir -p apps/story_engine/graphs
mkdir -p apps/story_engine/prompts
touch apps/story_engine/__init__.py
touch apps/story_engine/agents/__init__.py
```

```python
# apps/story_engine/agents/base_agent.py
from langchain_anthropic import ChatAnthropic
from typing import Dict, Any

class BaseStoryAgent:
    def __init__(self, model="claude-sonnet-4.5"):
        self.llm = ChatAnthropic(model=model)
    
    async def generate(self, prompt: str) -> str:
        response = await self.llm.ainvoke(prompt)
        return response.content
```

---

### Step 3: First Agent - Story Architect

```python
# apps/story_engine/agents/story_architect.py
from .base_agent import BaseStoryAgent
from typing import Dict, List

class StoryArchitectAgent(BaseStoryAgent):
    """Plans chapter structure before writing"""
    
    async def plan_chapter(self, beat: Dict, context: Dict) -> Dict:
        prompt = f"""
You are a story architect planning a chapter.

Chapter Beat:
{beat['description']}

Context:
- Previous chapters: {context.get('previous_chapters', [])}
- Characters: {context.get('characters', [])}

Create a detailed chapter plan including:
1. Opening scene
2. Key plot points
3. Character development moments
4. Closing hook

Return as JSON.
"""
        
        response = await self.generate(prompt)
        return self.parse_plan(response)
```

---

### Step 4: First Handler

```python
# apps/bfagent/handlers/story_handlers.py
from apps.bfagent.models_story import StoryBible, Chapter
from apps.story_engine.agents.story_architect import StoryArchitectAgent
import logging

logger = logging.getLogger(__name__)

class ChapterGenerationHandler:
    def __init__(self):
        self.architect = StoryArchitectAgent()
    
    async def generate_chapter(self, chapter_beat_id: int) -> Chapter:
        """Generate chapter from beat using AI agents"""
        
        try:
            # 1. Load context from DB
            beat = ChapterBeat.objects.get(id=chapter_beat_id)
            story_bible = beat.story_bible
            previous_chapters = Chapter.objects.filter(
                story_bible=story_bible,
                chapter_number__lt=beat.beat_number
            ).order_by('-chapter_number')[:3]
            
            context = {
                'story_bible': story_bible.to_dict(),
                'previous_chapters': [c.content for c in previous_chapters]
            }
            
            # 2. Plan chapter structure
            plan = await self.architect.plan_chapter(
                beat=beat.to_dict(),
                context=context
            )
            
            # 3. Save to database
            chapter = Chapter.objects.create(
                story_bible=story_bible,
                strand=beat.strand,
                chapter_number=beat.beat_number,
                title=beat.title,
                content=plan['full_text'],  # From agent
                word_count=len(plan['full_text'].split()),
                generation_method='agent_system',
                status='draft'
            )
            
            logger.info(f"Generated chapter {chapter.id}")
            return chapter
            
        except Exception as e:
            logger.error(f"Chapter generation failed: {e}")
            raise
```

---

### Step 5: Create View

```python
# apps/bfagent/views/story_views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from apps.bfagent.handlers.story_handlers import ChapterGenerationHandler
from apps.bfagent.models_story import ChapterBeat
import asyncio

def generate_chapter_view(request, beat_id):
    """Generate chapter from beat"""
    handler = ChapterGenerationHandler()
    
    # Run async handler
    chapter = asyncio.run(handler.generate_chapter(beat_id))
    
    return JsonResponse({
        'success': True,
        'chapter_id': chapter.id,
        'word_count': chapter.word_count
    })
```

---

## 🛠️ Dependencies

### requirements/story_engine.txt
```
# AI & Agents
langgraph>=0.2.0
langchain>=0.2.0
langchain-anthropic>=0.1.0
langchain-openai>=0.1.0

# Optional: Vector Store
chromadb>=0.5.0

# Utilities
pydantic>=2.0
```

### Install
```bash
pip install -r requirements/story_engine.txt
```

---

## ✅ Testing Strategy

### Unit Tests
```python
# tests/test_story_agents.py
import pytest
from apps.story_engine.agents.story_architect import StoryArchitectAgent

@pytest.mark.asyncio
async def test_story_architect_planning():
    agent = StoryArchitectAgent()
    
    beat = {
        'description': 'Sarah discovers anomalies',
        'emotional_tone': 'tense'
    }
    
    plan = await agent.plan_chapter(beat, context={})
    
    assert 'opening_scene' in plan
    assert 'plot_points' in plan
```

### Integration Tests
```python
# tests/test_chapter_generation.py
import pytest
from apps.bfagent.handlers.story_handlers import ChapterGenerationHandler
from apps.bfagent.models_story import StoryBible, ChapterBeat

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_full_chapter_generation():
    # Setup
    story_bible = StoryBible.objects.create(title="Test Story")
    beat = ChapterBeat.objects.create(
        story_bible=story_bible,
        description="Test beat"
    )
    
    # Execute
    handler = ChapterGenerationHandler()
    chapter = await handler.generate_chapter(beat.id)
    
    # Assert
    assert chapter.id is not None
    assert chapter.word_count > 0
    assert chapter.status == 'draft'
```

---

## 📊 Progress Tracking

Create `PROGRESS.md` to track development:

```markdown
# Story Engine Development Progress

## Phase 1: Foundation
- [x] Django Models created
- [x] Migrations run
- [ ] First Agent implemented
- [ ] Handler-Agent integration
- [ ] End-to-end test passed

## Phase 2: Agent System
- [ ] Writer Agent
- [ ] Continuity Checker
- [ ] Editor Agent
- [ ] Multi-agent workflow

## Phase 3: PoC
- [ ] Story Bible developed
- [ ] Teaser generated
```

---

## 📚 See Also

- [STORY_ENGINE_OVERVIEW.md](./STORY_ENGINE_OVERVIEW.md) - Project overview
- [STORY_ENGINE_ARCHITECTURE.md](./STORY_ENGINE_ARCHITECTURE.md) - System design
- [STORY_ENGINE_AGENTS.md](./STORY_ENGINE_AGENTS.md) - Agent details
- [STORY_ENGINE_DATABASE.md](./STORY_ENGINE_DATABASE.md) - Database schema
