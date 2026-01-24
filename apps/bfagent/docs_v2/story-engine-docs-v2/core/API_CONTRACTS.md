# Story Engine - API Contracts

> **Focus**: Interface Definitions, Type Safety, Integration Points  
> **Status**: Production Planning  
> **Updated**: 2025-11-09

---

## 📋 Table of Contents

1. [Handler Interfaces](#handler-interfaces)
2. [Agent Interfaces](#agent-interfaces)
3. [State Contracts](#state-contracts)
4. [Database Models](#database-models)
5. [REST API](#rest-api)
6. [Type Safety](#type-safety)

---

## 🔌 Handler Interfaces

### IChapterHandler

```python
# apps/bfagent/handlers/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class GenerationConfig(BaseModel):
    """Configuration for chapter generation"""
    
    model: str = "claude-sonnet-4.5"
    temperature: float = 0.7
    max_tokens: int = 8000
    max_iterations: int = 3
    quality_threshold: float = 0.7
    enable_human_review: bool = False

class GenerationResult(BaseModel):
    """Result of chapter generation"""
    
    status: str  # 'success', 'validation_error', 'error'
    chapter_id: Optional[int] = None
    word_count: Optional[int] = None
    quality_score: Optional[float] = None
    errors: list = []
    message: Optional[str] = None

class IChapterHandler(ABC):
    """
    Interface for chapter generation handlers.
    
    Guarantees:
    - Database transactions are atomic
    - Errors are properly classified
    - Results are always saved (even partial)
    """
    
    @abstractmethod
    async def generate_chapter(
        self,
        beat_id: int,
        config: Optional[GenerationConfig] = None
    ) -> GenerationResult:
        """
        Generate chapter from beat.
        
        Args:
            beat_id: Database ID of ChapterBeat
            config: Optional generation configuration
            
        Returns:
            GenerationResult with status and chapter info
            
        Raises:
            Never raises - returns error in result
        """
        pass
    
    @abstractmethod
    async def get_generation_status(
        self,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Get status of async generation.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            {
                'state': 'pending' | 'processing' | 'completed' | 'failed',
                'progress': 0-100,
                'current_step': str,
                'chapter_id': Optional[int]
            }
        """
        pass
    
    @abstractmethod
    async def validate_chapter(
        self,
        chapter_id: int
    ) -> Dict[str, Any]:
        """
        Re-validate existing chapter.
        
        Args:
            chapter_id: Database ID of Chapter
            
        Returns:
            {
                'valid': bool,
                'errors': List[Dict],
                'quality_score': float
            }
        """
        pass
```

---

## 🤖 Agent Interfaces

### IStoryAgent

```python
# apps/story_engine/agents/interfaces.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from pydantic import BaseModel

StateT = TypeVar('StateT', bound=BaseModel)

class AgentMetadata(BaseModel):
    """Metadata about agent execution"""
    
    agent_name: str
    execution_time: float
    tokens_used: int
    model: str
    success: bool
    error: Optional[str] = None

class IStoryAgent(ABC, Generic[StateT]):
    """
    Base interface for all story agents.
    
    Contract:
    - Must accept state of type StateT
    - Must return state of type StateT
    - Must be idempotent (same input → same output)
    - Must track performance metrics
    - Must handle errors gracefully
    """
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Unique name for this agent"""
        pass
    
    @abstractmethod
    async def execute(self, state: StateT) -> StateT:
        """
        Execute agent logic on state.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with agent's contributions
            
        Raises:
            AgentError: On execution failure
        """
        pass
    
    @abstractmethod
    async def validate_input(self, state: StateT) -> bool:
        """
        Validate that state is ready for this agent.
        
        Args:
            state: State to validate
            
        Returns:
            True if state is valid for this agent
        """
        pass
    
    @abstractmethod
    async def validate_output(self, state: StateT) -> bool:
        """
        Validate that agent produced valid output.
        
        Args:
            state: State after agent execution
            
        Returns:
            True if output is valid
        """
        pass
```

### Specific Agent Interfaces

```python
class IArchitectAgent(IStoryAgent[ChapterState]):
    """Interface for story planning agent"""
    
    @abstractmethod
    async def plan_chapter(
        self,
        beat: ChapterBeat,
        context: StoryContext
    ) -> ChapterPlan:
        """
        Create chapter plan.
        
        Args:
            beat: Chapter beat with key events
            context: Story bible, characters, previous chapters
            
        Returns:
            Structured chapter plan
        """
        pass

class IWriterAgent(IStoryAgent[ChapterState]):
    """Interface for prose generation agent"""
    
    @abstractmethod
    async def write_prose(
        self,
        plan: ChapterPlan,
        style: ProseStyle
    ) -> str:
        """
        Generate prose from plan.
        
        Args:
            plan: Chapter structure from architect
            style: Prose style guidelines
            
        Returns:
            Generated prose (2000-3000 words)
        """
        pass

class IContinuityCheckerAgent(IStoryAgent[ChapterState]):
    """Interface for consistency validation agent"""
    
    @abstractmethod
    async def check_consistency(
        self,
        content: str,
        story_bible: StoryBible
    ) -> List[ConsistencyIssue]:
        """
        Check content for consistency.
        
        Args:
            content: Generated chapter content
            story_bible: Source of truth for world rules
            
        Returns:
            List of issues found (empty if consistent)
        """
        pass

class IEditorAgent(IStoryAgent[ChapterState]):
    """Interface for content polishing agent"""
    
    @abstractmethod
    async def edit_chapter(
        self,
        draft: str,
        issues: List[ConsistencyIssue]
    ) -> str:
        """
        Polish chapter content.
        
        Args:
            draft: Raw generated content
            issues: Known issues to fix
            
        Returns:
            Polished, publication-ready content
        """
        pass
```

---

## 📊 State Contracts

### ChapterState (Complete Definition)

```python
# apps/story_engine/state.py
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum

class Severity(str, Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    MINOR = "minor"

class IssueType(str, Enum):
    """Types of consistency issues"""
    CHARACTER_CONTRADICTION = "character_contradiction"
    TIMELINE_INCONSISTENCY = "timeline_inconsistency"
    WORLD_RULE_VIOLATION = "world_rule_violation"
    PLOT_HOLE = "plot_hole"

class ConsistencyIssue(BaseModel):
    """Structured issue from continuity checker"""
    
    severity: Severity
    type: IssueType
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    
    def is_critical(self) -> bool:
        return self.severity == Severity.CRITICAL

class ChapterPlan(BaseModel):
    """Architect agent output"""
    
    opening_scene: str = Field(..., min_length=50, max_length=500)
    plot_points: List[str] = Field(..., min_length=2, max_length=10)
    character_moments: List[str] = Field(default_factory=list)
    closing_hook: str = Field(..., min_length=50, max_length=300)
    estimated_word_count: int = Field(default=2500, ge=1500, le=4000)
    
    @field_validator('plot_points')
    @classmethod
    def validate_plot_points(cls, v):
        if len(v) < 2:
            raise ValueError("Must have at least 2 plot points")
        return v

class ProseStyle(BaseModel):
    """Style guide for writer agent"""
    
    voice: Literal["first_person", "third_limited", "third_omniscient"]
    tone: Literal["tense", "calm", "dramatic", "philosophical"]
    pacing: Literal["slow", "medium", "fast"]
    description_density: Literal["sparse", "balanced", "rich"]

class ChapterState(BaseModel):
    """
    Complete state for chapter generation workflow.
    
    Immutability Rules:
    - Input fields (beat_*, story_*) are frozen
    - Context fields are set once
    - Output fields are updated by agents
    - Metadata is automatically tracked
    """
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )
    
    # ========== INPUTS (Frozen) ==========
    beat_id: int = Field(frozen=True)
    story_bible_id: int = Field(frozen=True)
    beat_description: str = Field(frozen=True)
    beat_title: str = Field(frozen=True)
    target_word_count: int = Field(frozen=True, default=2500)
    
    # ========== CONTEXT (Set Once) ==========
    world_rules: List[Dict] = Field(default_factory=list)
    character_profiles: List[Dict] = Field(default_factory=list)
    previous_summaries: List[str] = Field(default_factory=list)
    prose_style: ProseStyle
    
    # ========== AGENT OUTPUTS ==========
    plan: Optional[ChapterPlan] = None
    draft: Optional[str] = None
    issues: List[ConsistencyIssue] = Field(default_factory=list)
    final_text: Optional[str] = None
    summary: Optional[str] = None
    
    # ========== QUALITY METRICS ==========
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    consistency_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    readability_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    
    # ========== WORKFLOW METADATA ==========
    iteration: int = Field(default=0, ge=0, le=10)
    current_agent: Optional[str] = None
    generation_time: float = 0.0
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    
    # ========== VALIDATION ==========
    
    def has_critical_issues(self) -> bool:
        """Check if there are blocking issues"""
        return any(issue.is_critical() for issue in self.issues)
    
    def is_ready_for_writer(self) -> bool:
        """Validate state is ready for writer agent"""
        return (
            self.plan is not None and
            len(self.world_rules) > 0 and
            len(self.character_profiles) > 0
        )
    
    def is_ready_for_checker(self) -> bool:
        """Validate state is ready for checker agent"""
        return (
            self.draft is not None and
            len(self.draft.split()) >= self.target_word_count * 0.8
        )
    
    def is_complete(self) -> bool:
        """Check if workflow is complete"""
        return (
            self.final_text is not None and
            self.quality_score is not None and
            self.quality_score >= 0.7 and
            not self.has_critical_issues()
        )
    
    @field_validator('draft', 'final_text')
    @classmethod
    def validate_text_length(cls, v, info):
        """Ensure text meets minimum length"""
        if v is not None:
            word_count = len(v.split())
            if word_count < 1000:
                raise ValueError(
                    f"Text too short: {word_count} words (min 1000)"
                )
        return v
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        return self.model_dump(mode='json')
    
    @classmethod
    def from_beat(
        cls,
        beat: 'ChapterBeat',
        story_bible: 'StoryBible',
        previous_chapters: List['Chapter'],
        characters: List['Character']
    ) -> 'ChapterState':
        """
        Factory method to create state from Django models.
        
        This is the Handler → LangGraph conversion point.
        """
        return cls(
            beat_id=beat.id,
            story_bible_id=story_bible.id,
            beat_description=beat.description,
            beat_title=beat.title,
            target_word_count=beat.target_word_count,
            
            world_rules=story_bible.world_rules,
            character_profiles=[
                {
                    'name': c.name,
                    'traits': c.personality_traits,
                    'bio_snippet': c.biography[:300]
                }
                for c in characters
            ],
            previous_summaries=[
                c.summary for c in previous_chapters[:3]
            ],
            prose_style=ProseStyle(
                voice=beat.pov_style or "third_limited",
                tone=beat.emotional_tone or "balanced",
                pacing=beat.pacing or "medium",
                description_density="balanced"
            )
        )
```

---

## 💾 Database Models

### Model Interfaces

```python
# apps/bfagent/models_story.py
from django.db import models
from typing import Dict, List

class IStoryModel:
    """Interface for story-related models"""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for agents"""
        raise NotImplementedError
    
    def validate_business_rules(self) -> List[str]:
        """Validate model-specific business rules"""
        raise NotImplementedError

class StoryBible(models.Model, IStoryModel):
    """
    Story universe definition.
    
    Contract:
    - world_rules must be list of dicts with 'rule' key
    - timeline must be chronologically ordered
    - scientific_concepts must use consistent terminology
    """
    
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=100)
    
    # Structured data (JSON)
    scientific_concepts = models.JSONField(
        default=dict,
        help_text="Key scientific concepts, format: {concept: explanation}"
    )
    world_rules = models.JSONField(
        default=list,
        help_text="List of world rules, format: [{rule: str, established_in: str}]"
    )
    timeline = models.JSONField(
        default=list,
        help_text="Chronological events, format: [{year: int, event: str}]"
    )
    
    # Style
    prose_style = models.TextField()
    tone = models.CharField(max_length=100)
    
    def to_dict(self) -> Dict:
        """Convert to agent-friendly format"""
        return {
            'id': self.id,
            'title': self.title,
            'genre': self.genre,
            'scientific_concepts': self.scientific_concepts,
            'world_rules': self.world_rules,
            'timeline': self.timeline,
            'prose_style': self.prose_style,
            'tone': self.tone
        }
    
    def validate_business_rules(self) -> List[str]:
        """Validate story bible rules"""
        errors = []
        
        # Validate world_rules format
        if not isinstance(self.world_rules, list):
            errors.append("world_rules must be a list")
        else:
            for i, rule in enumerate(self.world_rules):
                if not isinstance(rule, dict):
                    errors.append(f"world_rules[{i}] must be a dict")
                elif 'rule' not in rule:
                    errors.append(f"world_rules[{i}] missing 'rule' key")
        
        # Validate timeline chronology
        if self.timeline:
            years = [e['year'] for e in self.timeline if 'year' in e]
            if years != sorted(years):
                errors.append("timeline not in chronological order")
        
        return errors

class Chapter(models.Model, IStoryModel):
    """
    Generated chapter.
    
    Contract:
    - content must be > 1000 words
    - quality_score must be 0.0-1.0
    - status must be one of: draft, review, published
    """
    
    story_bible = models.ForeignKey(StoryBible, on_delete=models.CASCADE)
    
    chapter_number = models.IntegerField()
    title = models.CharField(max_length=200)
    content = models.TextField()
    summary = models.TextField()
    word_count = models.IntegerField()
    
    quality_score = models.FloatField(null=True)
    consistency_score = models.FloatField(null=True)
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('review', 'Needs Review'),
        ('published', 'Published')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    class Meta:
        unique_together = ['story_bible', 'chapter_number']
        indexes = [
            models.Index(fields=['story_bible', 'chapter_number']),
            models.Index(fields=['status'])
        ]
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'chapter_number': self.chapter_number,
            'title': self.title,
            'content': self.content,
            'summary': self.summary,
            'word_count': self.word_count,
            'quality_score': self.quality_score
        }
    
    def validate_business_rules(self) -> List[str]:
        errors = []
        
        if self.word_count < 1000:
            errors.append("Chapter too short (< 1000 words)")
        
        if self.quality_score is not None:
            if not 0.0 <= self.quality_score <= 1.0:
                errors.append("quality_score must be 0.0-1.0")
        
        return errors
```

---

## 🌐 REST API

### Endpoints

```python
# apps/bfagent/api/story_endpoints.py
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

class GenerationRequestSerializer(serializers.Serializer):
    """Request to generate chapter"""
    
    beat_id = serializers.IntegerField(required=True)
    model = serializers.CharField(default="claude-sonnet-4.5")
    temperature = serializers.FloatField(default=0.7, min_value=0.0, max_value=2.0)
    max_iterations = serializers.IntegerField(default=3, min_value=1, max_value=5)

class GenerationResponseSerializer(serializers.Serializer):
    """Response from chapter generation"""
    
    status = serializers.ChoiceField(
        choices=['success', 'validation_error', 'error']
    )
    task_id = serializers.CharField(required=False)
    chapter_id = serializers.IntegerField(required=False)
    word_count = serializers.IntegerField(required=False)
    quality_score = serializers.FloatField(required=False)
    errors = serializers.ListField(required=False)
    message = serializers.CharField(required=False)

class ChapterViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for chapter operations.
    
    Endpoints:
    - POST /api/chapters/generate/ - Start chapter generation
    - GET /api/chapters/status/<task_id>/ - Check generation status
    - POST /api/chapters/<id>/validate/ - Re-validate chapter
    """
    
    @action(detail=False, methods=['post'])
    async def generate(self, request):
        """
        Generate chapter from beat.
        
        POST /api/chapters/generate/
        {
            "beat_id": 123,
            "model": "claude-sonnet-4.5",
            "temperature": 0.7
        }
        
        Response:
        {
            "status": "success",
            "task_id": "abc-123",
            "chapter_id": 45
        }
        """
        serializer = GenerationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        handler = ChapterGenerationHandler()
        result = await handler.generate_chapter(
            beat_id=serializer.validated_data['beat_id'],
            config=GenerationConfig(**serializer.validated_data)
        )
        
        return Response(
            GenerationResponseSerializer(result).data
        )
```

---

## 🎯 Type Safety

### MyPy Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_reexport = true

# Django-specific
plugins = ["mypy_django_plugin.main"]

[tool.django-stubs]
django_settings_module = "config.settings"
```

### Type Checking Examples

```python
# Type-safe handler
from typing import Protocol

class HandlerProtocol(Protocol):
    """Protocol for type checking handlers"""
    
    async def generate_chapter(
        self,
        beat_id: int,
        config: Optional[GenerationConfig]
    ) -> GenerationResult:
        ...

def use_handler(handler: HandlerProtocol) -> None:
    """Type checker ensures handler has correct signature"""
    result = await handler.generate_chapter(beat_id=1)
    assert isinstance(result, GenerationResult)
```

---

## 📚 See Also

- [STORY_ENGINE_ARCHITECTURE.md](./STORY_ENGINE_ARCHITECTURE.md) - System design
- [ERROR_HANDLING.md](./ERROR_HANDLING.md) - Error handling
- [STORY_ENGINE_DATABASE.md](./STORY_ENGINE_DATABASE.md) - Database models
- [TESTING_STRATEGY.md](./TESTING_STRATEGY.md) - Testing approach

---

**API Contracts Version**: 1.0  
**Last Updated**: 2025-11-09  
**Status**: Production-Ready Interfaces
