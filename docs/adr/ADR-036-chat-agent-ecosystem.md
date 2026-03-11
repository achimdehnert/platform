---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
implementation_status: implemented
implementation_evidence:
  - "bfagent: chat agent ecosystem with DomainToolkits"
---

# ADR-036: Chat-Agent Ecosystem — DomainToolkits, Research Integration & Shared Chat-Widget

| Metadata    | Value |
| ----------- | ----- |
| **Status**  | Proposed |
| **Date**    | 2026-02-15 |
| **Author**  | Achim Dehnert / Cascade AI |
| **Scope**   | platform, travel-beat, bfagent, weltenhub |
| **Related** | ADR-025 (3-Phase Pipeline), ADR-026 (Enrichment v2), ADR-034 (Chat-Agent Platform) |
| **Packages**| `chat-agent` (existing), `chat-widget` (new) |

---

## 1. Executive Summary

ADR-034 established the `chat-agent` platform package with `ChatAgent`, `DomainToolkit`,
and `CompletionBackend`. This ADR defines **the ecosystem built on top of it**:

1. **StoryToolkit** (travel-beat) — Conversational story configuration with POI/culture integration
2. **ResearchToolkit** (bfagent) — Scientific research, literature review, and paper writing
3. **Shared Chat-Widget** (platform) — Reusable HTMX chat component for all apps
4. **PubMed/arXiv API Clients** (bfagent) — Academic literature search backends
5. **Chat Endpoints** — Per-app `/api/chat/` endpoints with streaming support

**Key Insight**: The `chat-agent` package is domain-agnostic by design.
Each app contributes a `DomainToolkit`; the platform provides shared infrastructure.
No new repositories are needed — everything fits into existing repos.

---

## 2. Context & Problem Statement

### 2.1 Current State (post ADR-034)

| Component | Status | Location |
|-----------|--------|----------|
| `ChatAgent` core loop | Implemented | `platform/packages/chat-agent/` |
| `DomainToolkit` ABC | Implemented | `platform/packages/chat-agent/` |
| `CompletionBackend` protocol | Implemented | `platform/packages/chat-agent/` |
| `TravelBeatToolkit` (8 trip tools) | Implemented | `travel-beat/apps/trips/agent/toolkit.py` |
| `BookFactoryToolkit` (6 book tools) | Implemented | `bfagent/apps/bfagent/agents/toolkit.py` |
| `CADToolkit` (6 CAD tools) | Implemented | `platform/packages/cad-services/contrib/` |
| `ToolkitRegistry` | Declared in `__init__.py` | Not yet implemented |

### 2.2 Gaps Identified

| ID | Gap | Impact |
|----|-----|--------|
| G-01 | Story generation uses only genre/spice_level/ending_type as user input | Generic stories, no POI/culture integration |
| G-02 | Stop.enrichment_data POIs (ADR-026) not flowing into story prompts | Rich data collected but wasted |
| G-03 | No conversational story configuration | Users fill a wizard instead of describing what they want |
| G-04 | ResearchAgent (bfagent) not exposed as DomainToolkit | Cannot be used in ChatAgent loop |
| G-05 | Academic skills (citations, BibTeX) exist but are isolated | Not accessible via conversation |
| G-06 | No shared chat UI component | Each app would build its own, duplicating effort |
| G-07 | No streaming support in ChatAgent | UX suffers for long responses |
| G-08 | Science Writer domain is scaffold-only (7-phase plan, empty views) | No models, no services |

### 2.3 Stakeholder Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| R-01 | Story focus control: immersive / cultural / touristic | Travel agencies (B2B) |
| R-02 | DB-driven prompt configuration, no hardcoded text | Platform governance |
| R-03 | Smart defaults derived from trip type, overridable by user | UX best practice |
| R-04 | Conversational story setup as alternative to wizard | Chat-Agent value proposition |
| R-05 | Scientific paper writing with literature review and citations | bfagent roadmap |
| R-06 | Fact-checking integrated into research workflow | Academic integrity |
| R-07 | Shared chat widget across all apps | DRY, consistent UX |
| R-08 | No new repositories | Infrastructure budget |

---

## 3. Architecture

### 3.1 Ecosystem Overview

```
platform/packages/
    chat-agent/          ← ADR-034 (existing)
    chat-widget/         ← NEW: shared HTMX component

travel-beat/
    apps/stories/
        models/config.py ← StoryFocusConfig (DB-driven)
        models/story.py  ← 5 new fields (premise, atmosphere, themes, ...)
    apps/stories/agent/
        toolkit.py       ← NEW: StoryToolkit (6 tools)
    apps/trips/agent/
        toolkit.py       ← TravelBeatToolkit (8 tools, existing)

bfagent/
    apps/bfagent/agents/
        toolkit.py       ← BookFactoryToolkit (existing)
        research_toolkit.py ← NEW: ResearchToolkit (9 tools)
    apps/bfagent/agents/
        research_agent.py ← ResearchAgent (existing)
    apps/research/services/
        pubmed_client.py  ← NEW: PubMed API
        arxiv_client.py   ← NEW: arXiv API
    domains/science_writer/
        models.py         ← NEW: ResearchProject, Source, ...
```

### 3.2 Toolkit Composition per App

Each app creates a composite agent by merging its toolkits:

**travel-beat:**
```python
agent = ChatAgent(
    toolkit=CompositeToolkit([
        TravelBeatToolkit(),   # 8 tools: trip CRUD
        StoryToolkit(),        # 6 tools: story config + POI
    ]),
    completion=LiteLLMAdapter(action_code="chat"),
    session_backend=RedisSessionBackend(redis),
    system_prompt=DRIFTTALES_SYSTEM_PROMPT,
)
```

**bfagent:**
```python
agent = ChatAgent(
    toolkit=CompositeToolkit([
        BookFactoryToolkit(),  # 6 tools: project/chapter CRUD
        ResearchToolkit(),     # 9 tools: search, cite, fact-check
    ]),
    completion=LiteLLMAdapter(action_code="research"),
    session_backend=RedisSessionBackend(redis),
    system_prompt=RESEARCH_SYSTEM_PROMPT,
)
```

### 3.3 CompositeToolkit (Missing from ADR-034)

ADR-034 declared `ToolkitRegistry` but did not implement it.
This ADR specifies `CompositeToolkit` as the concrete implementation:

```python
class CompositeToolkit(DomainToolkit):
    """Merges multiple DomainToolkits into one."""

    def __init__(self, toolkits: list[DomainToolkit]):
        self._toolkits = toolkits
        self._dispatch: dict[str, DomainToolkit] = {}
        for tk in toolkits:
            for schema in tk.tool_schemas:
                name = schema["function"]["name"]
                self._dispatch[name] = tk

    @property
    def name(self) -> str:
        return "+".join(tk.name for tk in self._toolkits)

    @property
    def tool_schemas(self) -> list[dict]:
        schemas = []
        for tk in self._toolkits:
            schemas.extend(tk.tool_schemas)
        return schemas

    async def execute(self, tool_name, arguments, ctx):
        tk = self._dispatch.get(tool_name)
        if not tk:
            return ToolResult(success=False, error=f"Unknown: {tool_name}")
        return await tk.execute(tool_name, arguments, ctx)
```

Location: `platform/packages/chat-agent/src/chat_agent/composite.py`

---

## 4. Phase 1: StoryToolkit (travel-beat)

### 4.1 StoryFocusConfig (DB-Driven, Implemented)

New model in `stories/models/config.py`:

| Field | Type | Purpose |
|-------|------|---------|
| `slug` | SlugField(unique) | Reference key (immersive/cultural/touristic) |
| `name_de` | CharField | User-facing German label |
| `icon` | CharField | Bootstrap icon for wizard card |
| `subtitle_de` | CharField | Description for wizard card |
| `storyline_prompt_addition` | TextField | Injected into STORYLINE_TEMPLATE |
| `outline_prompt_addition` | TextField | Injected into SCENE_OUTLINE_TEMPLATE |
| `chapter_prompt_addition` | TextField | Injected into CHAPTER_TEMPLATE |
| `max_pois_per_stop` | PositiveInteger | 0=none, 3=subtle, 5=prominent |
| `include_poi_narrative` | Boolean | Include LLM-generated POI narratives |
| `include_culture_details` | Boolean | Include cuisine, language, customs |

**Migration**: `0016_story_focus_config.py` — schema + 3 seed configs (immersive, cultural, touristic).

### 4.2 Story Model Extensions (Implemented)

5 new fields on `Story`:

| Field | Type | Default | Source |
|-------|------|---------|--------|
| `premise` | TextField | blank | User/Agent/LLM |
| `atmosphere` | CharField(200) | blank | User/Agent |
| `themes` | JSONField | [] | User/Agent |
| `narrative_voice` | CharField choices | third_person | User/Agent |
| `story_focus` | SlugField | immersive | Derived from TripType, overridable |

### 4.3 TripTypeConfig Extension (Implemented)

New field `default_story_focus` on `TripTypeConfig`:

| Trip Type | Default Focus | Rationale |
|-----------|--------------|-----------|
| city | cultural | Cities = culture |
| beach | immersive | Romance focus |
| wellness | immersive | Character focus |
| backpacking | cultural | Discovery |
| business | immersive | Plot focus |
| family | cultural | Activities |
| adventure | immersive | Action focus |
| cruise | cultural | Ports & culture |
| roadtrip | cultural | Landscape & places |

**Migration**: `0020_triptype_default_story_focus.py`

### 4.4 StoryToolkit Tools (6 tools)

| Tool | Type | Description |
|------|------|-------------|
| `get_stop_enrichment` | READ | POIs + culture + weather for a stop |
| `get_story_settings` | READ | Current story preferences for a trip |
| `preview_focus` | READ | What POIs/culture would be included per focus |
| `set_story_preferences` | WRITE | Set genre, focus, premise, atmosphere, themes |
| `suggest_premise` | AI | LLM-generated premises based on trip + enrichment |
| `generate_story` | TRIGGER | Kick off Celery story generation task |

### 4.5 Pipeline Integration (Phase B)

**TripInputHandler** change:
- Read `StoryFocusConfig` for the story's `story_focus` slug
- If `max_pois_per_stop > 0`: include top N POIs per stop in `input_context`
- If `include_culture_details`: include culture data

**StorylineGenerator** change:
- Pass `focus_instruction` (from `StoryFocusConfig.storyline_prompt_addition`) as template variable
- Pass `poi_context` (formatted POIs) as template variable
- Pass `premise`, `atmosphere`, `themes`, `narrative_voice` as template variables

**STORYLINE_TEMPLATE** change:
- 6 new `PromptVariable` entries (focus_instruction, poi_context, premise, atmosphere, themes, narrative_voice)
- Template text references `{{ focus_instruction }}` and `{{ poi_context }}`

### 4.6 Wizard UI (Phase D)

Add Story-Stil card selector to `step3_preferences.html`:
- 3 cards derived from `StoryFocusConfig.objects.filter(is_enabled=True)`
- Default pre-selected from `TripTypeConfig.default_story_focus`
- Follows existing genre-card pattern (radio + icon + label)

---

## 5. Phase 2: ResearchToolkit (bfagent)

### 5.1 Decision: bfagent, Not Separate Repo

A scientific paper is a `BookProjects` with `book_type="academic"`.
All required infrastructure already exists in bfagent:

| Component | Status | Reuse Strategy |
|-----------|--------|----------------|
| `ResearchAgent` (search, fact-check) | Implemented | Wrap in toolkit |
| Academic skills (citations, BibTeX) | Implemented (seed command) | Expose as tools |
| `BookProjects` model | Implemented | Add `book_type` choices |
| `BookChapters` model | Implemented | Paper sections = chapters |
| `ContextEnrichment` models | Implemented | Sources = enrichment |
| LLM infrastructure | Implemented | Shared |

**No new repo.** Overhead avoided: Docker, DB, port, Nginx, CI/CD, GHCR.

### 5.2 Science Writer Models

New models in `domains/science_writer/models.py`:

```python
class ResearchProject(models.Model):
    """Extends BookProjects for academic workflow."""
    project = models.OneToOneField(
        "bfagent.BookProjects",
        on_delete=models.CASCADE,
        related_name="research_extension",
    )
    research_question = models.TextField()
    methodology = models.CharField(max_length=100)
    current_phase = models.CharField(
        max_length=30,
        choices=ResearchPhase.choices,
        default=ResearchPhase.PLANNING,
    )
    target_journal = models.CharField(max_length=200, blank=True)
    citation_style = models.CharField(
        max_length=20,
        choices=CitationStyle.choices,
        default=CitationStyle.APA7,
    )

class Source(models.Model):
    """Academic source with full citation metadata."""
    project = models.ForeignKey(
        "bfagent.BookProjects",
        on_delete=models.CASCADE,
        related_name="sources",
    )
    doi = models.CharField(max_length=100, blank=True, db_index=True)
    title = models.CharField(max_length=500)
    authors = models.JSONField(default=list)
    year = models.PositiveIntegerField(null=True)
    journal = models.CharField(max_length=300, blank=True)
    abstract = models.TextField(blank=True)
    url = models.URLField(blank=True)
    bibtex = models.TextField(blank=True)
    relevance_score = models.FloatField(default=0.0)
    notes = models.TextField(blank=True)
```

### 5.3 ResearchToolkit Tools (9 tools)

| Tool | Type | Backend |
|------|------|---------|
| `search_literature` | READ | ResearchAgent.full_research() + PubMed/arXiv |
| `get_paper_details` | READ | DOI resolver → Source metadata |
| `add_source` | WRITE | Create Source record |
| `create_literature_review` | WRITE | LLM synthesis → Chapter |
| `fact_check_claim` | READ | ResearchAgent.fact_check() |
| `format_citation` | READ | Academic skills (APA, MLA, Chicago, ...) |
| `generate_section` | WRITE | LLM → Chapter (Abstract, Methods, Results, ...) |
| `get_project_sources` | READ | List sources for a project |
| `suggest_next_step` | READ | Phase-aware workflow guidance |

### 5.4 7-Phase Workflow (Agent-Guided)

| Phase | Enum | Agent Behavior |
|-------|------|----------------|
| PLANNING | planning | Ask research question, scope, methodology |
| LITERATURE_REVIEW | literature | Search, filter, synthesize sources |
| METHODOLOGY | methodology | Design and document approach |
| DATA_ANALYSIS | analysis | Describe and interpret results |
| WRITING | writing | Generate sections iteratively |
| QUALITY | quality | Fact-check, plagiarism, consistency |
| FINALIZATION | finalization | Format citations, export |

The agent tracks `ResearchProject.current_phase` and uses
`suggest_next_step` to guide the conversation.

### 5.5 API Clients

**PubMed** (`apps/research/services/pubmed_client.py`):
- E-utilities API: `esearch.fcgi` + `efetch.fcgi`
- Rate limit: 3 req/sec (NCBI policy)
- Returns: PMID, title, authors, abstract, DOI, MeSH terms
- Caching: Redis, 24h TTL

**arXiv** (`apps/research/services/arxiv_client.py`):
- Atom API: `api.arxiv.org/query`
- Rate limit: 1 req/3sec (arXiv policy)
- Returns: arXiv ID, title, authors, abstract, PDF link, categories
- Caching: Redis, 24h TTL

**Semantic Scholar** (optional, Phase 2+):
- REST API: `api.semanticscholar.org/graph/v1`
- Citation graph, influence scores
- Free tier: 100 req/5min

---

## 6. Phase 3: Shared Chat-Widget (platform)

### 6.1 Architecture

Location: `platform/packages/chat-widget/`

```
chat-widget/
    templates/
        chat_widget/
            chat.html          # Main template (includable)
            _message.html      # Single message partial (HTMX)
            _typing.html       # Typing indicator partial
    static/
        chat_widget/
            chat.js            # HTMX event handlers, streaming
            chat.css           # Tailwind-based, themeable
    templatetags/
        chat_widget_tags.py    # {% chat_widget endpoint="/api/chat/" %}
```

### 6.2 Usage in Apps

```html
{% load chat_widget_tags %}

<!-- Floating chat button + sidebar -->
{% chat_widget endpoint="/api/chat/" title="DriftTales Assistent" %}
```

### 6.3 Features

| Feature | Implementation |
|---------|---------------|
| Floating button | Fixed-position button, opens sidebar |
| Message history | HTMX swap into message container |
| Streaming | SSE via `hx-ext="sse"` or chunked transfer |
| Theming | CSS variables (--chat-primary, --chat-bg) |
| Session | Cookie-based session_id, server-side storage |
| Mobile | Responsive, full-screen on mobile |
| Markdown | Marked.js for LLM response rendering |

### 6.4 Backend Contract

Each app provides a POST endpoint:

```python
# Input
{"message": "Ich moechte eine Story fuer meine Barcelona-Reise"}

# Output (non-streaming)
{
    "response": "Deine Barcelona-Reise hat tolle Orte! ...",
    "session_id": "abc-123",
    "tool_calls_made": 2
}
```

---

## 7. Implementation Plan

### 7.1 Phases & Dependencies

```
Phase A [DONE]  StoryFocusConfig + Story fields + Migrations
    |
Phase B         Pipeline integration (TripInputHandler + StorylineGenerator)
    |
Phase C         StoryToolkit (6 tools + tests)
    |
Phase D         Wizard Step 3 UI (story-stil cards)
    |
Phase E         CompositeToolkit + create_trip_agent() with Travel+Story
    |
Phase F         Chat-Widget (platform shared component)
    |
Phase G         Chat endpoint (travel-beat /api/chat/)
    |
Phase H         Science Writer models (bfagent)
    |
Phase I         ResearchToolkit (9 tools, wraps ResearchAgent)
    |
Phase J         PubMed/arXiv clients
    |
Phase K         Chat endpoint (bfagent /api/chat/)
```

### 7.2 Effort Estimates

| Phase | Scope | Size | Risk |
|-------|-------|------|------|
| A | Models + Migrations (travel-beat) | S | Low |
| B | Pipeline integration (travel-beat) | M | Medium — prompt tuning |
| C | StoryToolkit (travel-beat) | M | Low |
| D | Wizard UI (travel-beat) | S | Low |
| E | CompositeToolkit (platform) | S | Low |
| F | Chat-Widget (platform) | M | Medium — UX polish |
| G | Chat endpoint (travel-beat) | S | Low |
| H | Science Writer models (bfagent) | M | Low |
| I | ResearchToolkit (bfagent) | M | Low — wraps existing |
| J | PubMed/arXiv clients (bfagent) | M | Medium — rate limits |
| K | Chat endpoint (bfagent) | S | Low |

### 7.3 Critical Path

**Minimum Viable**: A → B → C → E (StoryToolkit with focus-aware prompts)
**Full DriftTales**: + D + F + G (Wizard UI + Chat)
**Full Research**: + H + I + J + K (Science Writer + Chat)

---

## 8. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Prompt quality varies by focus level | Stories feel forced or generic | Medium | A/B test prompt additions in StoryFocusConfig; iterate via Django Admin |
| POI data gaps (not all stops enriched) | touristic focus falls back to immersive | Low | Graceful degradation: if no POIs, omit poi_context |
| PubMed/arXiv rate limits | Research slowed | Medium | Redis caching (24h), async queuing, user feedback |
| Chat-Widget complexity | Delays delivery | Medium | Start with non-streaming MVP; add SSE later |
| Tool name collisions across toolkits | CompositeToolkit dispatch fails | Low | Naming convention: `{domain}_{action}` (e.g. story_set_preferences) |
| LLM token budget with POI injection | Cost increase per story | Medium | StoryFocusConfig.max_pois_per_stop limits injection size |

---

## 9. Testing Strategy

### 9.1 Unit Tests

| Component | Test Focus | Framework |
|-----------|-----------|-----------|
| `StoryFocusConfig` | CRUD, get_by_slug, get_default, caching | pytest-django |
| `StoryToolkit` | Tool schemas, execute dispatch, error handling | pytest + AsyncMock |
| `CompositeToolkit` | Merge, dispatch, name collision detection | pytest |
| `ResearchToolkit` | Tool schemas, wraps ResearchAgent correctly | pytest + AsyncMock |
| `PubMed/arXiv clients` | Response parsing, rate limit compliance, caching | pytest + responses |

### 9.2 Integration Tests

| Scenario | Validates |
|----------|-----------|
| Wizard → generate with touristic focus | POIs appear in story |
| Chat agent: "set focus to cultural" | Story.story_focus updated |
| Chat agent: "search papers on ML" | ResearchAgent called, sources returned |
| Chat-Widget: send message → receive response | Full stack E2E |

---

## 10. Decision Record

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| StoryFocusConfig as DB model | Runtime changes without deployment | Hardcoded prompt text, env vars |
| Focus as slug on Story, not FK | Simpler, works without StoryFocusConfig existing | FK (migration dependency), JSON (no validation) |
| ResearchToolkit in bfagent, not new repo | Paper = BookProject with book_type; avoids infra overhead | Separate research-hub repo (Docker, DB, port, Nginx) |
| Chat-Widget as platform package | DRY across apps; consistent UX | Per-app duplication, external SaaS |
| CompositeToolkit over ToolkitRegistry | Simpler, explicit, no global state | Global registry (import-order dependent) |
| Smart defaults from TripType, overridable | Zero-friction UX; power users can override | Always ask user (friction), never ask (no control) |

---

## 11. Appendix: Existing Components Inventory

### 11.1 Reusable in bfagent (already implemented)

| Component | File | Reuse |
|-----------|------|-------|
| `ResearchAgent` | `agents/research_agent.py` | Wrap in ResearchToolkit |
| `BraveSearchService` | `research/services/brave_search_service.py` | Backend for search_literature |
| `seed_academic_skills` | `management/commands/seed_academic_skills.py` | Citation formatting |
| `BookFactoryToolkit` | `agents/toolkit.py` | Merge with ResearchToolkit |
| `ContextEnrichment` | `models_context_enrichment.py` | Source metadata storage |

### 11.2 Reusable in travel-beat (already implemented)

| Component | File | Reuse |
|-----------|------|-------|
| `TravelBeatToolkit` | `trips/agent/toolkit.py` | Merge with StoryToolkit |
| `LiteLLMAdapter` | `trips/agent/adapter.py` | CompletionBackend for all agents |
| `Stop.enrichment_data` | `trips/models/trip.py` | POI/culture data source |
| `StorylineGenerator` | `stories/services/storyline_generator.py` | Focus-aware prompt injection |
| `ChapterPlanGenerator` | `stories/services/chapter_planner.py` | Focus-aware theme extraction |

### 11.3 Reusable in platform (already implemented)

| Component | File | Reuse |
|-----------|------|-------|
| `ChatAgent` | `chat-agent/src/chat_agent/agent.py` | Core loop |
| `DomainToolkit` | `chat-agent/src/chat_agent/toolkit.py` | ABC for all toolkits |
| `SessionBackend` | `chat-agent/src/chat_agent/session.py` | Redis + InMemory |
| `PromptTemplateSpec` | `creative-services/` | DB-driven prompts |
