# Handler-Agent Pattern

Das Handler-Agent Pattern ist das zentrale Architekturmuster in BF Agent.

## Grundprinzip

```
┌─────────────────────────────────────────────────────────────────┐
│  HANDLER (Orchestration Layer)                                   │
│  ✅ Touch Database (DB I/O)                                      │
│  ✅ Load/Save Data                                               │
│  ✅ Coordinate Workflows                                         │
│  ✅ Handle Errors for Users                                      │
│  ❌ DON'T: Contain AI Logic                                      │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  AGENT (Pure AI Layer)                                           │
│  ✅ Pure Functions (state in → state out)                        │
│  ✅ LLM Calls and Prompt Building                                │
│  ✅ Data Transformation                                          │
│  ❌ DON'T: Touch Database (NEVER .objects.aget())                │
│  ❌ DON'T: Save to DB                                            │
│  ❌ DON'T: Access File System                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Beispiel

### Handler (Orchestration)

```python
class ChapterGenerationHandler:
    async def generate_chapter(self, beat_id: int):
        # DB READ
        context = await self._load_from_db(beat_id)
        
        # STATE INIT
        state = ChapterState.from_beat(context)
        
        # AI PROCESSING (delegiert an Agent)
        result = await self.workflow.run(state)
        
        # DB WRITE
        chapter = await self._save_to_db(result)
        return chapter
```

### Agent (Pure AI)

```python
class StoryArchitectAgent:
    async def execute(self, state: ChapterState) -> ChapterState:
        # BUILD PROMPT
        prompt = self._build_prompt(state)
        
        # LLM CALL
        response = await self.llm.ainvoke(prompt)
        
        # RETURN NEW STATE (immutable!)
        return state.model_copy(update={'plan': response})
```

## State Management

### Regeln

- **Pydantic BaseModel** mit `frozen=True`
- **Store IDs**, NOT objects
- **Keep state < 10KB** serialized
- **Use `model_copy(update={...})`** for changes

### Beispiel

```python
class ChapterState(BaseModel):
    beat_id: int = Field(frozen=True)
    story_bible_id: int = Field(frozen=True)
    plan: Optional[ChapterPlan] = None
    
    class Config:
        frozen = True
    
    def with_plan(self, plan: ChapterPlan) -> 'ChapterState':
        return self.model_copy(update={'plan': plan})
```

## Async/Await Rules

Django ORM async Methoden:

| Sync | Async |
|------|-------|
| `.get()` | `await .aget()` |
| `.filter()` | `async for in .afilter()` |
| `.create()` | `await .acreate()` |
| `.save()` | `await .asave()` |

## Error Handling (3-Tier)

1. **Agent Level**: Retry LLM errors
2. **Workflow Level**: Fallbacks & retries
3. **Handler Level**: User-friendly messages

**Regel:** Never let raw exceptions reach users
