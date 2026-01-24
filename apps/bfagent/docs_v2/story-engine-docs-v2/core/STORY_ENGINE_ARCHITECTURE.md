# Story Engine - Technical Architecture

> **Focus**: System Design, Technology Stack, Integration Patterns  
> **Audience**: Developers, Technical Decision Makers  
> **Status**: Production Planning  
> **Updated**: 2025-11-09  
> **Version**: 2.0 (LangGraph Best Practices)

---

## 📋 Table of Contents

1. [System Layers](#system-layers)
2. [Technology Stack](#technology-stack)
3. [Handler-Agent Integration](#handler-agent-integration)
4. [Data Flow](#data-flow)
5. [State Management Strategy](#state-management-strategy)
6. [Project Structure](#project-structure)
7. [Integration Patterns](#integration-patterns)

---

## 🏗️ System Layers

### Layer 1: Presentation Layer (Django + HTMX)
**Responsibility**: User Interface & Interaction

```python
# Django Views (apps/bfagent/views/story_views.py)
from django.shortcuts import render
from django.http import JsonResponse
from apps.bfagent.handlers.story_handlers import ChapterGenerationHandler

def chapter_generation_view(request, beat_id):
    """Trigger chapter generation via HTMX"""
    if request.method == 'POST':
        handler = ChapterGenerationHandler()
        task_id = handler.start_generation(beat_id)
        
        return JsonResponse({
            'task_id': task_id,
            'status': 'processing',
            'poll_url': f'/api/story/status/{task_id}/'
        })
    
    # GET: Show generation form
    beat = ChapterBeat.objects.get(id=beat_id)
    return render(request, 'story/generate_chapter.html', {'beat': beat})

def generation_status_view(request, task_id):
    """Poll for generation status (HTMX polling)"""
    handler = ChapterGenerationHandler()
    status = handler.get_status(task_id)
    
    if status['state'] == 'completed':
        return render(request, 'story/chapter_result.html', {
            'chapter': status['chapter']
        })
    
    return render(request, 'story/generation_progress.html', {
        'progress': status['progress'],
        'current_step': status['current_step']
    })
```

**UI Components:**
- Django Templates with TailwindCSS
- HTMX for dynamic updates (no page reload)
- Real-time progress indicators
- Django Admin for configuration

---

### Layer 2: Orchestration Layer (Handlers)
**Responsibility**: State Management, Database I/O, Error Handling

```python
# apps/bfagent/handlers/story_handlers.py
from typing import Optional, Dict
from apps.bfagent.models_story import Chapter, ChapterBeat, StoryBible
from apps.story_engine.workflows.chapter_workflow import ChapterWorkflow
from apps.story_engine.state import ChapterState
import structlog

logger = structlog.get_logger()

class ChapterGenerationHandler:
    """
    Handler orchestrates between Django models and LangGraph agents.
    
    Responsibilities:
    - Load data from database
    - Convert to LangGraph state
    - Invoke workflow
    - Save results back to database
    - Handle errors gracefully
    """
    
    def __init__(self):
        self.workflow = ChapterWorkflow()
    
    async def generate_chapter(
        self, 
        beat_id: int,
        config: Optional[Dict] = None
    ) -> Chapter:
        """
        Main entry point for chapter generation.
        
        Args:
            beat_id: Database ID of ChapterBeat
            config: Optional workflow configuration
            
        Returns:
            Generated Chapter object (saved to DB)
            
        Raises:
            ChapterGenerationError: On workflow failure
        """
        
        try:
            # 1. LOAD: Get data from database
            context = await self._load_context(beat_id)
            
            # 2. CONVERT: Database → LangGraph State
            initial_state = ChapterState.from_beat(
                beat=context['beat'],
                story_bible=context['story_bible'],
                previous_chapters=context['previous_chapters'],
                characters=context['characters']
            )
            
            # 3. EXECUTE: Run LangGraph workflow
            graph_config = {
                "configurable": {
                    "thread_id": f"beat-{beat_id}",
                    "checkpoint_ns": f"story-{context['story_bible'].id}"
                }
            }
            
            final_state = await self.workflow.run(
                state=initial_state,
                config=graph_config
            )
            
            # 4. SAVE: Results → Database
            chapter = await self._save_chapter(
                state=final_state,
                beat_id=beat_id
            )
            
            logger.info(
                "chapter_generated",
                chapter_id=chapter.id,
                word_count=chapter.word_count,
                quality_score=final_state.quality_score
            )
            
            return chapter
            
        except Exception as e:
            logger.error(
                "chapter_generation_failed",
                beat_id=beat_id,
                error=str(e),
                exc_info=True
            )
            raise ChapterGenerationError(
                f"Failed to generate chapter for beat {beat_id}"
            ) from e
    
    async def _load_context(self, beat_id: int) -> Dict:
        """Load all required data from database"""
        beat = await ChapterBeat.objects.select_related(
            'story_bible', 'strand'
        ).aget(id=beat_id)
        
        story_bible = beat.story_bible
        
        # Get previous chapters for context
        previous_chapters = Chapter.objects.filter(
            story_bible=story_bible,
            chapter_number__lt=beat.beat_number
        ).order_by('-chapter_number')[:3]
        
        # Get relevant characters
        characters = Character.objects.filter(
            story_bible=story_bible
        )
        
        return {
            'beat': beat,
            'story_bible': story_bible,
            'previous_chapters': list(previous_chapters),
            'characters': list(characters)
        }
    
    async def _save_chapter(
        self, 
        state: ChapterState,
        beat_id: int
    ) -> Chapter:
        """Save generated content to database"""
        beat = await ChapterBeat.objects.aget(id=beat_id)
        
        chapter = await Chapter.objects.acreate(
            story_bible=beat.story_bible,
            strand=beat.strand,
            chapter_number=beat.beat_number,
            title=beat.title,
            content=state.final_text,
            summary=state.summary,
            word_count=len(state.final_text.split()),
            pov_character_id=beat.character_focus_id,
            generation_method='langgraph_agents',
            quality_score=state.quality_score,
            consistency_score=state.consistency_score,
            status='draft',
            version=1
        )
        
        # Store generation metadata
        await ChapterMetadata.objects.acreate(
            chapter=chapter,
            agent_iterations=state.iteration,
            issues_found=len(state.issues),
            generation_time=state.generation_time,
            token_usage=state.total_tokens
        )
        
        return chapter
```

**Handler Principles:**
- **Single Responsibility**: One handler per domain workflow
- **Database-First**: Always read/write from PostgreSQL
- **Type Safety**: Use Pydantic for validation
- **Error Boundaries**: Never let exceptions escape unhandled
- **Logging**: Structured logging for observability

---

### Layer 3: Agent Orchestration (LangGraph)
**Responsibility**: AI Workflow Execution

```python
# apps/story_engine/workflows/chapter_workflow.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from typing import Dict
from apps.story_engine.state import ChapterState
from apps.story_engine.agents import (
    StoryArchitectAgent,
    WriterAgent,
    ContinuityCheckerAgent,
    EditorAgent
)
import structlog

logger = structlog.get_logger()

class ChapterWorkflow:
    """
    LangGraph workflow for chapter generation.
    
    Implements: Architect → Writer → Checker → Editor pipeline
    with conditional retry logic.
    """
    
    def __init__(self):
        self.graph = self._build_graph()
        self._setup_checkpointing()
    
    def _build_graph(self) -> StateGraph:
        """Build the chapter generation graph"""
        
        graph = StateGraph(ChapterState)
        
        # Initialize agents
        architect = StoryArchitectAgent()
        writer = WriterAgent()
        checker = ContinuityCheckerAgent()
        editor = EditorAgent()
        
        # Add nodes
        graph.add_node("architect", architect.plan_chapter)
        graph.add_node("writer", writer.write_prose)
        graph.add_node("checker", checker.check_consistency)
        graph.add_node("editor", editor.edit_chapter)
        
        # Define edges
        graph.add_edge("architect", "writer")
        
        # Conditional: Checker decides if revision needed
        graph.add_conditional_edges(
            "checker",
            self._should_revise,
            {
                "revise": "writer",  # Loop back
                "edit": "editor"     # Continue
            }
        )
        
        graph.add_edge("editor", END)
        
        # Set entry point
        graph.set_entry_point("architect")
        
        return graph
    
    def _should_revise(self, state: ChapterState) -> str:
        """
        Decide if chapter needs revision based on issues found.
        
        LangGraph Best Practice: Keep decision logic simple and bounded.
        """
        # Critical issues require revision
        critical_issues = [
            i for i in state.issues 
            if i.severity == "critical"
        ]
        
        # Prevent infinite loops
        max_iterations = 3
        
        if critical_issues and state.iteration < max_iterations:
            logger.info(
                "revision_required",
                iteration=state.iteration,
                critical_issues=len(critical_issues)
            )
            return "revise"
        
        return "edit"
    
    def _setup_checkpointing(self):
        """
        Setup PostgreSQL checkpointer for durability.
        
        LangGraph Best Practice: Use PostgreSQL for production.
        """
        from django.conf import settings
        
        db_uri = settings.LANGGRAPH_DB_URI
        pool = ConnectionPool(conninfo=db_uri, max_size=10)
        
        with pool.connection() as conn:
            saver = PostgresSaver(conn)
            saver.setup()  # Create tables if needed
        
        self.compiled = self.graph.compile(checkpointer=saver)
    
    async def run(
        self, 
        state: ChapterState,
        config: Dict
    ) -> ChapterState:
        """
        Execute the workflow.
        
        Args:
            state: Initial chapter state
            config: LangGraph config with thread_id
            
        Returns:
            Final state after all agents
        """
        return await self.compiled.ainvoke(state, config)
```

**LangGraph Best Practices Applied:**
1. ✅ **Small, Typed State** (Pydantic model)
2. ✅ **Simple Edges** (no complex conditionals)
3. ✅ **Bounded Cycles** (max 3 iterations)
4. ✅ **PostgreSQL Checkpointer** (durability)
5. ✅ **Explicit Thread IDs** (thread_id pattern)

---

### Layer 4: Agent Implementation
**Responsibility**: AI-Powered Content Generation

```python
# apps/story_engine/agents/base_agent.py
from abc import ABC, abstractmethod
from langchain_anthropic import ChatAnthropic
from typing import Dict, Any
from contextlib import asynccontextmanager
from time import perf_counter
import structlog

logger = structlog.get_logger()

class BaseStoryAgent(ABC):
    """
    Base class for all story agents.
    
    Provides:
    - LLM initialization
    - Performance tracking
    - Error handling
    - Logging
    """
    
    def __init__(
        self,
        model: str = "claude-sonnet-4.5",
        temperature: float = 0.7,
        max_tokens: int = 8000
    ):
        self.llm = ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        self.agent_name = self.__class__.__name__
    
    @asynccontextmanager
    async def track_performance(self, operation: str):
        """Track agent execution metrics"""
        start = perf_counter()
        
        try:
            yield
            
            duration = perf_counter() - start
            logger.info(
                "agent_success",
                agent=self.agent_name,
                operation=operation,
                duration_seconds=duration
            )
            
        except Exception as e:
            duration = perf_counter() - start
            logger.error(
                "agent_failed",
                agent=self.agent_name,
                operation=operation,
                duration_seconds=duration,
                error=str(e)
            )
            raise
    
    @abstractmethod
    async def execute(self, state: Any) -> Any:
        """Each agent must implement this"""
        pass
```

---

## 🔧 Technology Stack

### Core Framework
```yaml
Backend:
  - Django 5.0+           # Web framework
  - PostgreSQL 16+        # Primary database
  - Redis 7+              # Caching & task queue

AI/ML:
  - LangGraph 0.2.50+     # Agent orchestration
  - LangChain 0.3+        # LLM framework
  - Anthropic Claude 4    # Primary LLM (Sonnet 4.5)
  - OpenAI GPT-4          # Fallback LLM

State & Storage:
  - PostgreSQL            # LangGraph checkpointer
  - ChromaDB (optional)   # Vector search index
  - S3/MinIO              # File storage

Frontend:
  - HTMX 2.0+            # Dynamic updates
  - TailwindCSS 3+       # Styling
  - Alpine.js            # Light JS framework

Development:
  - Python 3.11+         # Language
  - Poetry/pip          # Package management
  - pytest              # Testing
  - Ruff/Black          # Linting/formatting
```

### Dependencies
```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.11"
django = "^5.0"
psycopg = {extras = ["binary", "pool"], version = "^3.1"}
langgraph = "^0.2.50"
langchain = "^0.3.0"
langchain-anthropic = "^0.1.0"
langchain-openai = "^0.1.0"
pydantic = "^2.8"
structlog = "^24.1"
redis = "^5.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
pytest-django = "^4.8"
ruff = "^0.5"
mypy = "^1.10"
```

---

## 🔄 Data Flow

### Complete Request Flow

```
1. USER ACTION (Browser)
   ↓
   POST /story/generate/beat/123/
   
2. DJANGO VIEW (Presentation Layer)
   ↓
   StoryGenerationHandler.generate_chapter(123)
   
3. HANDLER (Orchestration Layer)
   ↓
   a) Load from DB: beat, story_bible, chapters, characters
   ↓
   b) Convert to ChapterState (Pydantic)
   ↓
   c) Invoke LangGraph workflow
   
4. LANGGRAPH WORKFLOW (Agent Orchestration)
   ↓
   a) Architect Agent: Create plan
   ↓
   b) Writer Agent: Generate prose
   ↓
   c) Checker Agent: Validate consistency
   ↓   ↓
   │   └─ If critical issues → Loop back to Writer
   ↓
   d) Editor Agent: Polish text
   ↓
   Return final ChapterState
   
5. HANDLER (Orchestration Layer)
   ↓
   Save Chapter to PostgreSQL
   
6. DJANGO VIEW (Presentation Layer)
   ↓
   Return JSON response
   
7. BROWSER (HTMX)
   ↓
   Update UI without reload
```

---

## 📊 State Management Strategy

### LangGraph State Design (2025 Best Practices)

```python
# apps/story_engine/state.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime
from apps.bfagent.models_story import ChapterBeat, StoryBible, Character

class ConsistencyIssue(BaseModel):
    """Type-safe issue representation"""
    severity: Literal["critical", "warning", "minor"]
    type: str
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None

class ChapterPlan(BaseModel):
    """Architect agent output"""
    opening_scene: str
    plot_points: List[str]
    character_moments: List[str]
    closing_hook: str
    estimated_word_count: int

class ChapterState(BaseModel):
    """
    Central state object for chapter generation workflow.
    
    LangGraph Best Practices:
    - Small: Only essential data
    - Typed: Pydantic for validation
    - Immutable fields: Use Field(frozen=True) where appropriate
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Input (frozen after creation)
    beat_id: int = Field(frozen=True)
    story_bible_id: int = Field(frozen=True)
    beat_description: str = Field(frozen=True)
    
    # Context (loaded once)
    world_rules: List[Dict] = Field(default_factory=list)
    character_profiles: List[Dict] = Field(default_factory=list)
    previous_chapter_summaries: List[str] = Field(default_factory=list)
    
    # Agent outputs (populated by workflow)
    plan: Optional[ChapterPlan] = None
    draft: Optional[str] = None
    issues: List[ConsistencyIssue] = Field(default_factory=list)
    final_text: Optional[str] = None
    summary: Optional[str] = None
    
    # Workflow metadata
    iteration: int = 0
    quality_score: Optional[float] = None
    consistency_score: Optional[float] = None
    
    # Performance tracking
    generation_time: float = 0.0
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def from_beat(
        cls,
        beat: ChapterBeat,
        story_bible: StoryBible,
        previous_chapters: List,
        characters: List[Character]
    ) -> "ChapterState":
        """
        Factory method to create state from Django models.
        
        Handler → LangGraph conversion point.
        """
        return cls(
            beat_id=beat.id,
            story_bible_id=story_bible.id,
            beat_description=beat.description,
            world_rules=story_bible.world_rules,
            character_profiles=[
                {
                    'name': c.name,
                    'traits': c.personality_traits,
                    'bio': c.biography[:500]  # Truncate for token efficiency
                }
                for c in characters
            ],
            previous_chapter_summaries=[
                c.summary for c in previous_chapters[:3]  # Last 3 only
            ]
        )
```

**State Design Principles:**
1. **Minimal**: Only data needed across nodes
2. **Typed**: Pydantic validation at runtime
3. **Immutable Inputs**: Frozen fields prevent accidental mutation
4. **No Transient Data**: Don't store intermediate LLM responses
5. **Factory Methods**: Clean conversion from DB models

---

## 📁 Project Structure

```
bfagent/                              # Main Django app
├── models/
│   ├── __init__.py
│   ├── models_story.py               # Story models (Bible, Chapter, etc.)
│   └── models_core.py                # Core bfagent models
│
├── handlers/
│   ├── __init__.py
│   └── story_handlers.py             # Handler orchestration
│
├── views/
│   ├── __init__.py
│   └── story_views.py                # Django views
│
└── admin.py                          # Django Admin configuration

apps/story_engine/                    # LangGraph agents package
├── __init__.py
├── state.py                          # State definitions
├── config.py                         # Agent configuration
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py                 # Base agent class
│   ├── story_architect.py            # Planning agent
│   ├── writer.py                     # Content generation
│   ├── continuity_checker.py         # Validation agent
│   └── editor.py                     # Polish agent
│
├── workflows/
│   ├── __init__.py
│   └── chapter_workflow.py           # LangGraph workflow
│
├── prompts/
│   ├── __init__.py
│   ├── architect_prompts.py          # Prompt templates
│   ├── writer_prompts.py
│   └── checker_prompts.py
│
└── utils/
    ├── __init__.py
    ├── metrics.py                    # Performance tracking
    ├── retry.py                      # Retry logic
    └── validators.py                 # Content validation

tests/
├── test_handlers/
│   └── test_story_handlers.py
├── test_agents/
│   ├── test_architect.py
│   └── test_writer.py
└── test_workflows/
    └── test_chapter_workflow.py
```

---

## 🔗 Integration Patterns

### Pattern 1: Django ↔ LangGraph Bridge

```python
# Clean separation via Handler
class Handler:
    """
    Django side:  Models, QuerySets, Database
    LangGraph side: State, Agents, Workflows
    
    Handler bridges the gap.
    """
    
    async def execute(self, db_input_id: int):
        # Django → LangGraph
        django_data = await self._load_from_db(db_input_id)
        lg_state = State.from_django(django_data)
        
        # LangGraph execution
        result_state = await self.workflow.run(lg_state)
        
        # LangGraph → Django
        await self._save_to_db(result_state)
```

### Pattern 2: Error Boundaries

```python
# Three-tier error handling
try:
    # 1. Handler level: Database errors
    context = await handler.load_context(beat_id)
    
    try:
        # 2. Workflow level: Agent errors
        state = await workflow.run(initial_state)
        
        # 3. Agent level: LLM errors (inside agents)
        # Agents handle retries internally
        
    except AgentError as e:
        # Workflow can retry or escalate
        logger.error("agent_failed", error=e)
        raise
        
except DatabaseError as e:
    # Handler escalates to view
    logger.error("db_failed", error=e)
    raise ChapterGenerationError() from e
```

### Pattern 3: Async All The Way

```python
# ✅ CORRECT: Async end-to-end
async def view(request):
    handler = Handler()
    result = await handler.execute(beat_id)  # Async
    return JsonResponse(result)

async def handler.execute():
    data = await self.load_data()            # Async DB
    state = await self.workflow.run()        # Async LangGraph
    await self.save_data()                   # Async DB
    return state

# Agent
async def agent.generate():
    response = await self.llm.ainvoke()      # Async LLM
    return response
```

---

## 🎯 Architecture Decisions

### Why LangGraph over CrewAI?
- **State Management**: Built-in persistent state
- **Durability**: PostgreSQL checkpointing
- **Flexibility**: Custom graph structures
- **Production-Ready**: Mature error handling

### Why Database-First?
- **Single Source of Truth**: PostgreSQL is authoritative
- **Easier Testing**: Mock DB, not AI
- **Flexibility**: Change agents without losing data
- **Cost Control**: Cache expensive operations

### Why Handler Pattern?
- **Separation of Concerns**: Django ≠ LangGraph
- **Error Boundaries**: Failures don't cascade
- **Type Safety**: Pydantic validation at boundaries
- **Testability**: Mock handlers, test agents separately

---

## 📚 See Also

- [STORY_ENGINE_AGENTS.md](./STORY_ENGINE_AGENTS.md) - Agent implementation details
- [STORY_ENGINE_DATABASE.md](./STORY_ENGINE_DATABASE.md) - Database schema
- [ERROR_HANDLING.md](./ERROR_HANDLING.md) - Error handling strategy
- [API_CONTRACTS.md](./API_CONTRACTS.md) - Interface definitions
- [STORY_ENGINE_IMPLEMENTATION.md](./STORY_ENGINE_IMPLEMENTATION.md) - Step-by-step guide

---

**Architecture Version**: 2.0  
**Last Updated**: 2025-11-09  
**Status**: Production-Ready Design
