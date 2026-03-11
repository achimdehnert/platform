---
id: ADR-096
title: "authoringfw — Content Orchestration Scope, Architecture, and Domain Boundaries"
status: accepted
date: 2026-03-02
author: Achim Dehnert
owner: Achim Dehnert
decision-makers: [Achim Dehnert]
consulted: []
informed: [bfagent, travel-beat, weltenhub, pptx-hub, risk-hub teams]
scope: authoringfw package + all consumer apps using content generation
tags: [authoringfw, orchestration, writing, research, analysis, architecture, package-design]
related: [ADR-050, ADR-057, ADR-068, ADR-089, ADR-093, ADR-095]
supersedes: []
amends: [ADR-050]
last_verified: 2026-03-11
implementation_status: implemented
implementation_evidence:
  - "authoringfw v0.7.0: PyPI published, 124 tests green"
  - "src/authoringfw/schema/: 5 Pydantic schemas (character, scene, story, style, world)"
  - "src/authoringfw/adapters/: 6 CRUD adapter interfaces"
  - "src/authoringfw/writing/: ChapterOrchestrator, SummaryOrchestrator"
  - "src/authoringfw/research/: ResearchOrchestrator"
  - "src/authoringfw/analysis/: StyleAnalysis, PlotAnalysis"
  - "src/authoringfw/text/: TextReformatter"
  - "src/authoringfw/formats/: FormatProfile, WorkflowPhase"
---

# ADR-096: authoringfw — Content Orchestration Scope, Architecture, and Domain Boundaries

| Field | Value |
|-------|-------|
| Status | **Accepted** (reviewed 2026-03-11) |
| Date | 2026-03-02 |
| Author | Achim Dehnert |
| Scope | `authoringfw` package + `bfagent`, `travel-beat`, `weltenhub`, `pptx-hub` |
| Amends | ADR-050 §3 (Hub Landscape — adds `authoringfw` as explicit shared package) |
| Related | ADR-050 (Platform Decomposition), ADR-057 (Test Strategy), ADR-068 (Agent Routing), ADR-095 (Quality-Level Routing), ADR-089 (LiteLLM), ADR-093 (AI Config) |

---

## 1. Context and Problem Statement

### 1.1 Background

ADR-095 (Quality-Level Routing) introduced `authoringfw` as the platform's content workflow orchestrator and defined its canonical `BaseContentOrchestrator` pattern. ADR-050 (Platform Decomposition) defines the hub landscape but does not formally define `authoringfw` as a shared package — it is mentioned only incidentally in migration planning.

This ADR resolves **OQ-3 from ADR-095**: *"authoringfw scope formalisation — separate ADR for Research + Analysis orchestration patterns beyond Writing?"*

### 1.2 Current State

`authoringfw` exists as a package but its scope is informally defined:

| Problem | Consequence |
|---------|-------------|
| No formal domain boundary | Consumer apps call `aifw.sync_completion()` directly for content tasks, duplicating orchestration logic across repos |
| No canonical base class | Each consumer app implements its own LLM call pattern; `get_action_config()` (ADR-095) is not yet adopted |
| Research and Analysis orchestration undefined | `bfagent` research and `travel-beat` story analysis use ad-hoc patterns |
| No contract between `authoringfw` and `promptfw`/`aifw` | Template key resolution and model selection are entangled in consumer code |
| `authoringfw` confused with a "master controller" | Early discussions suggested it should "trigger" `aifw` and `promptfw`; this is architecturally wrong |

### 1.3 The Three Domain Problem

Content generation on this platform spans three distinct cognitive domains:

| Domain | Core Activity | Key Distinction |
|--------|--------------|----------------|
| **Writing** | Generate structured narrative content | Output is primary artefact (chapters, stories, outlines) |
| **Research** | Gather, synthesise, and verify information | Output feeds other tasks (facts, sources, summaries) |
| **Analysis** | Evaluate and score existing content | Output is metadata about existing artefacts (scores, tags, classifications) |

These three domains share infrastructure (`aifw`, `promptfw`) but have fundamentally different task lifecycles, output contracts, and error semantics. Without formal boundaries, they collapse into a single tangled orchestrator.

### 1.4 What `authoringfw` Is NOT

Clarifying the non-scope is as important as the scope:

| Anti-Pattern | Why Wrong |
|-------------|----------|
| Universal LLM gateway for all platform apps | `risk-hub` (occupational safety) has no content domain; routing through `authoringfw` would create wrong cross-domain coupling (ADR-050) |
| Master controller that "triggers" `aifw` and `promptfw` | `aifw` and `promptfw` are independent packages; `authoringfw` is a *consumer* of both, not their controller |
| Agent orchestrator for the AI Engineering Squad | ADR-068 owns agent-tier routing inside `orchestrator_mcp`; `authoringfw` is for end-user content tasks, not developer agent workflows |
| Replacement for direct `aifw.sync_completion()` calls | Non-content apps (`risk-hub`, `pptx-hub` for infra tasks) call `aifw` directly — this is correct and must remain possible |

---

## 2. Decision Drivers

- **Domain clarity** — Writing, Research, Analysis are distinct enough to warrant separate base classes and task contracts, but share enough infrastructure to live in one package
- **Eliminate duplication** — Orchestration logic (config lookup → prompt render → LLM call → result mapping) must be written once in `authoringfw`, not re-implemented per consumer app
- **Composability** — Research outputs must be consumable by Writing tasks; Analysis outputs must be consumable by both. Task composition must be explicit, not implicit
- **Testability** — Each domain orchestrator must be independently testable with mocked `aifw` and `promptfw` calls (ADR-057)
- **Consumer-app simplicity** — Consumer apps should call one method with a typed task object; all infrastructure complexity is hidden in `authoringfw`
- **Backwards compatibility** — Existing direct `aifw.sync_completion()` call sites in consumer apps remain valid; `authoringfw` adoption is incremental

---

## 3. Considered Options

### Option A — Single `BaseContentOrchestrator` for all three domains
One base class handles Writing, Research, and Analysis uniformly.

**Assessment:** Works for the ADR-095 example but breaks down in practice. Research tasks require source management and citation handling that Writing tasks do not need. Analysis tasks produce structured scores, not prose — their output contract is entirely different. A single base class either becomes bloated or forces wrong abstractions. **Rejected for deep tasks; retained as the minimal shared base.**

### Option B — Three independent packages (`writingfw`, `researchfw`, `analysisfw`)
Separate packages per domain.

**Assessment:** Over-engineered for the current scale. All three domains share `aifw` + `promptfw` integration, task lifecycle, caching, and error handling. Three separate packages create three separate versioning and deployment problems. **Rejected.**

### Option C — One package (`authoringfw`), three domain sub-modules with shared base *(chosen)*
`authoringfw` contains `writing/`, `research/`, `analysis/` sub-modules, each with a domain-specific orchestrator extending `BaseContentOrchestrator`. Shared infrastructure (config lookup, prompt rendering, LLM dispatch, result mapping) lives in `base.py`.

**Assessment:** Single versioning unit. Shared base eliminates duplication. Domain sub-modules allow independent evolution. Consumer apps import from the specific sub-module (`from authoringfw.writing import StoryOrchestrator`). **Accepted.**

### Option D — Domain orchestrators as Django apps inside `bfagent`
Keep orchestration logic in `bfagent` as Django apps.

**Assessment:** Violates ADR-050 — `bfagent` is being decomposed, not extended. `travel-beat` and `weltenhub` also need the same orchestration. Coupling to `bfagent`'s Django app structure prevents reuse. **Rejected.**

---

## 4. Decision

### 4.1 `authoringfw` Package Scope

`authoringfw` is the platform's **content workflow orchestration package**. Its scope is:

**IN SCOPE:**
- Orchestrating LLM tasks that produce or evaluate **narrative or informational content** for end users
- Coordinating `aifw.get_action_config()` + `promptfw.render()` + `aifw.sync_completion()` into typed, reusable task pipelines
- Providing domain-specific task types (`StoryTask`, `ResearchTask`, `AnalysisTask`) and result types
- Managing multi-step content workflows (e.g., outline → chapter → review)
- Providing `BaseContentOrchestrator` as the canonical integration point with ADR-095 routing

**OUT OF SCOPE:**
- LLM provider management (owned by `aifw`)
- Prompt template storage and rendering (owned by `promptfw`)
- Agent-tier routing and quality feedback loops (owned by ADR-068 / `orchestrator_mcp`)
- Non-content LLM tasks in `risk-hub`, `pptx-hub` infra tasks (call `aifw` directly)
- User authentication, tenancy, or HTTP handling (consumer app responsibility)

### 4.2 Package Structure

```
authoringfw/
├── __init__.py              # Exports: BaseContentOrchestrator, QualityLevel
├── base.py                  # BaseContentOrchestrator — shared lifecycle
├── types.py                 # ContentTask, ContentResult, ActionConfig protocol
├── exceptions.py            # OrchestrationError, TemplateNotFoundError
│
├── writing/
│   ├── __init__.py          # Exports: StoryOrchestrator, OutlineOrchestrator
│   ├── orchestrators.py     # StoryOrchestrator, ChapterOrchestrator, OutlineOrchestrator
│   ├── tasks.py             # StoryTask, ChapterTask, OutlineTask (typed Pydantic models)
│   └── results.py           # StoryResult, ChapterResult (typed Pydantic models)
│
├── research/
│   ├── __init__.py          # Exports: ResearchOrchestrator, FactCheckOrchestrator
│   ├── orchestrators.py     # ResearchOrchestrator, FactCheckOrchestrator, SynthesisOrchestrator
│   ├── tasks.py             # ResearchTask, FactCheckTask, SynthesisTask
│   └── results.py           # ResearchResult, FactCheckResult (with source citations)
│
└── analysis/
    ├── __init__.py          # Exports: ContentAnalyser, StyleAnalyser
    ├── orchestrators.py     # ContentAnalyser, StyleAnalyser, ReadabilityScorer
    ├── tasks.py             # AnalysisTask, StyleTask, ReadabilityTask
    └── results.py           # AnalysisResult, StyleScore, ReadabilityScore (structured scores)
```

### 4.3 `BaseContentOrchestrator` — Canonical Implementation

The canonical base class implementing the ADR-095 §5.8 pattern, with full error handling and observability:

```python
# authoringfw/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
import logging

from aifw import get_action_config, sync_completion, QualityLevel
import promptfw

from .types import ContentTask, ContentResult
from .exceptions import OrchestrationError

logger = logging.getLogger(__name__)


class BaseContentOrchestrator(ABC):
    """
    Canonical orchestration base for all authoringfw domain orchestrators.

    Lifecycle:
        1. get_action_config()  — resolve model + template key (cached, single DB call)
        2. promptfw.render()    — render prompt from template key
        3. sync_completion()    — execute LLM call
        4. _map_result()        — domain-specific result mapping (subclass responsibility)
    """

    @property
    @abstractmethod
    def action_code(self) -> str:
        """The aifw action_code identifying this orchestrator's task type."""

    def execute(
        self,
        task: ContentTask,
        quality_level: int = QualityLevel.BALANCED,
        priority: str | None = None,
    ) -> ContentResult:
        """
        Execute a content task with the given quality level.

        Args:
            task:          Typed task object (domain-specific subclass of ContentTask)
            quality_level: 1-9 integer (use QualityLevel constants). None = catch-all.
            priority:      "fast"|"balanced"|"quality"|None. Explicit override only —
                           never auto-derived from quality_level.
        """
        try:
            # Step 1 — Resolve model + template (single cached DB call via ADR-095)
            config = get_action_config(
                action_code=self.action_code,
                quality_level=quality_level,
                priority=priority,
            )
            logger.debug(
                "authoringfw: resolved config for %s (ql=%s, prio=%s): model=%s, template=%s",
                self.action_code, quality_level, priority,
                config["model"], config.get("prompt_template_key"),
            )

            # Step 2 — Render prompt via promptfw
            template_key = config.get("prompt_template_key") or self.action_code
            messages = promptfw.render(template_key, context=task.to_context())

            # Step 3 — Execute LLM call
            llm_result = sync_completion(
                action_code=self.action_code,
                messages=messages,
                quality_level=quality_level,
                priority=priority,
            )

            # Step 4 — Domain-specific result mapping
            return self._map_result(llm_result, task, config)

        except Exception as exc:
            raise OrchestrationError(
                f"{self.__class__.__name__}.execute() failed for "
                f"action_code={self.action_code!r}: {exc}"
            ) from exc

    @abstractmethod
    def _map_result(
        self,
        llm_result: Any,
        task: ContentTask,
        config: dict,
    ) -> ContentResult:
        """Map raw LLMResult to the domain-specific ContentResult type."""
```

### 4.4 Domain Task and Result Contracts

All tasks and results are **Pydantic v2 models** (frozen, validated):

```python
# authoringfw/types.py
from __future__ import annotations
from abc import abstractmethod
from pydantic import BaseModel, ConfigDict, Field


class ContentTask(BaseModel):
    """Base for all domain-specific task types."""
    model_config = ConfigDict(frozen=True)

    @abstractmethod
    def to_context(self) -> dict:
        """Render task data as promptfw template context dict."""


class ContentResult(BaseModel):
    """Base for all domain-specific result types."""
    model_config = ConfigDict(frozen=True)

    action_code: str
    model_used: str
    quality_level: int | None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    success: bool
```

**Writing domain example:**

```python
# authoringfw/writing/tasks.py
class ChapterTask(ContentTask):
    title: str = Field(description="Chapter title")
    genre: str = Field(description="Genre e.g. 'fantasy', 'thriller'")
    outline: str = Field(description="Chapter outline / beat sheet")
    style_notes: str | None = Field(default=None, description="Author style guidance")
    word_count_target: int = Field(default=1500, description="Target word count")

    def to_context(self) -> dict:
        return self.model_dump()

# authoringfw/writing/results.py
class ChapterResult(ContentResult):
    content: str = Field(description="Generated chapter text")
    word_count: int = Field(description="Actual word count of generated content")

# authoringfw/writing/orchestrators.py
class ChapterOrchestrator(BaseContentOrchestrator):
    action_code = "chapter_writing"

    def _map_result(self, llm_result, task, config) -> ChapterResult:
        content = llm_result.content
        return ChapterResult(
            action_code=self.action_code,
            model_used=llm_result.model,
            quality_level=llm_result.quality_level,
            input_tokens=llm_result.input_tokens,
            output_tokens=llm_result.output_tokens,
            latency_ms=llm_result.latency_ms,
            success=llm_result.success,
            content=content,
            word_count=len(content.split()),
        )
```

**Research domain example:**

```python
# authoringfw/research/tasks.py
class ResearchTask(ContentTask):
    query: str = Field(description="Research question or topic")
    depth: int = Field(default=3, ge=1, le=5, description="Research depth 1-5")
    source_hints: list[str] = Field(default_factory=list, description="Known source URLs or names")
    output_format: str = Field(default="structured_summary", description="Output format")

    def to_context(self) -> dict:
        return self.model_dump()

# authoringfw/research/results.py
class ResearchResult(ContentResult):
    summary: str = Field(description="Synthesised research summary")
    key_facts: list[str] = Field(description="Extracted key facts")
    sources: list[str] = Field(description="Referenced sources (URLs or titles)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
```

**Analysis domain example:**

```python
# authoringfw/analysis/tasks.py
class StyleAnalysisTask(ContentTask):
    content: str = Field(description="Text to analyse")
    target_style: str | None = Field(default=None, description="Reference style to compare against")
    metrics: list[str] = Field(
        default_factory=lambda: ["readability", "tone", "pacing"],
        description="Metrics to evaluate"
    )

    def to_context(self) -> dict:
        return self.model_dump()

# authoringfw/analysis/results.py
class StyleScore(BaseModel):
    model_config = ConfigDict(frozen=True)
    metric: str
    score: float = Field(ge=0.0, le=1.0)
    explanation: str

class StyleAnalysisResult(ContentResult):
    scores: list[StyleScore]
    overall_score: float = Field(ge=0.0, le=1.0)
    recommendations: list[str]
```

### 4.5 Multi-Step Workflow Composition

Research outputs composing into Writing tasks is an explicit, typed pattern:

```python
# Example: bfagent book chapter generation with prior research
from authoringfw.research import ResearchOrchestrator
from authoringfw.writing import ChapterOrchestrator
from authoringfw.writing.tasks import ChapterTask

research_orch = ResearchOrchestrator()
chapter_orch = ChapterOrchestrator()

# Step 1: Research phase (economy quality — background facts)
research = research_orch.execute(
    ResearchTask(query="Victorian-era industrial London atmosphere"),
    quality_level=QualityLevel.ECONOMY,
)

# Step 2: Writing phase (premium quality — actual content)
chapter = chapter_orch.execute(
    ChapterTask(
        title="The Fog of Whitechapel",
        genre="historical fiction",
        outline="Detective arrives at crime scene...",
        style_notes=f"Incorporate: {'; '.join(research.key_facts[:5])}",
    ),
    quality_level=QualityLevel.PREMIUM,
)
```

### 4.6 Consumer-App Integration Pattern

Consumer apps interact with `authoringfw` through a thin service layer — the quality_level resolution and tier mapping stay in the consumer app:

```python
# bfagent/apps/writing_hub/services.py
from aifw import get_quality_level_for_tier
from authoringfw.writing import ChapterOrchestrator
from authoringfw.writing.tasks import ChapterTask

_orchestrator = ChapterOrchestrator()  # singleton — stateless, safe to share

def generate_chapter(chapter: Chapter, user) -> str:
    quality = get_quality_level_for_tier(getattr(user, "subscription", None))
    result = _orchestrator.execute(
        ChapterTask(
            title=chapter.title,
            genre=chapter.book.genre,
            outline=chapter.outline,
        ),
        quality_level=quality,
    )
    return result.content
```

### 4.7 Package Dependency Contract

```
promptfw    — no aifw dep, no authoringfw dep
aifw        — no promptfw dep, no authoringfw dep
                      ↓
authoringfw — deps: aifw, promptfw, pydantic
                      ↓
consumer-app — deps: authoringfw (for content tasks), aifw (for non-content tasks)
```

**Forbidden imports:**
- `aifw` must never import from `authoringfw`
- `promptfw` must never import from `authoringfw` or `aifw`
- Consumer apps must never re-implement `BaseContentOrchestrator` logic

### 4.8 Relationship to ADR-068 (Agent Routing)

ADR-068's `TaskRouter` selects an agent tier (e.g., `standard_coding`) for developer workflow tasks inside `orchestrator_mcp`. When that agent tier executes a content generation task (e.g., writing a README), it uses `authoringfw` orchestrators — `authoringfw` is the execution layer, ADR-068 is the routing layer above it. They do not overlap.

| ADR-068 | ADR-096 |
|---------|---------|
| Selects agent tier for developer tasks | Orchestrates content tasks for end users |
| Inside `orchestrator_mcp` | Inside `authoringfw` package |
| Input: developer task + complexity | Input: end-user content request + quality_level |
| Output: agent execution result | Output: typed content artefact |

---

## 5. Consequences

### 5.1 Positive

- **Single implementation of the ADR-095 lifecycle** — `BaseContentOrchestrator` implements the full `get_action_config() → promptfw.render() → sync_completion()` chain once; all consumer apps benefit automatically
- **Typed task/result contracts** — Pydantic v2 models catch schema errors at import time, not at runtime in production
- **Domain isolation** — Writing, Research, and Analysis orchestrators evolve independently; a change to `ChapterOrchestrator` cannot break `ResearchOrchestrator`
- **Composability** — Research → Writing pipelines are explicit and type-safe
- **Testability** — `BaseContentOrchestrator` can be tested with mocked `aifw` and `promptfw`; no HTTP, no DB required for unit tests
- **Consumer-app simplicity** — `_orchestrator.execute(task, quality_level=quality)` is the entire integration surface

### 5.2 Negative

- **New package dependency** — Consumer apps that previously called `aifw` directly must add `iil-authoringfw` to `requirements.txt`. Non-breaking (direct `aifw` calls remain valid), but a conscious adoption step per app.
- **Pydantic v2 task models require discipline** — Every new content task type requires a Pydantic model with `to_context()`. Teams used to passing raw dicts will need to adjust.
- **`_map_result()` boilerplate per orchestrator** — Each domain orchestrator must implement result mapping. Minimal but unavoidable.
- **Research result quality depends on model** — Economy-tier models (quality_level 1–3) produce lower-confidence research results. Consumer apps must communicate this to users.

---

## 6. Migration Path

| Phase | Action | Repo | Breaking? |
|-------|--------|------|-----------|
| 1 | Implement `base.py`, `types.py`, `exceptions.py` | `authoringfw` | No |
| 1 | Implement `writing/` sub-module (ChapterOrchestrator, StoryOrchestrator) | `authoringfw` | No |
| 2 | Implement `research/` sub-module | `authoringfw` | No |
| 2 | Implement `analysis/` sub-module | `authoringfw` | No |
| 3 | `bfagent`: replace direct `sync_completion()` calls for writing tasks with `ChapterOrchestrator` | `bfagent` | No |
| 3 | `travel-beat`: adopt `StoryOrchestrator` for story generation | `travel-beat` | No |
| 3 | `weltenhub`: adopt `StoryOrchestrator` / `ResearchOrchestrator` | `weltenhub` | No |
| 4 | Extend with multi-step workflow helpers (Research→Writing pipeline) | `authoringfw` | No |

**Phase 1 prerequisite:** `aifw` 0.6.0 must be deployed (ADR-097 Phase 1) before `authoringfw` Phase 1 can use `get_action_config()`.

---

## 7. Testing Requirements (ADR-057)

| Level | Test | Location |
|-------|------|---------|
| Unit | `BaseContentOrchestrator.execute()` with mocked `aifw` and `promptfw` | `authoringfw/tests/test_base.py` |
| Unit | All task `to_context()` methods — correct dict shape | `authoringfw/tests/test_tasks.py` |
| Unit | All `_map_result()` implementations — correct result type and fields | `authoringfw/tests/test_orchestrators.py` |
| Integration | `ChapterOrchestrator` end-to-end with real `aifw` catch-all config | `authoringfw/tests/integration/test_chapter.py` |
| Contract | `ContentResult` base fields present on all result types | `authoringfw/tests/test_contracts.py` |

---

## 8. Open Questions

| ID | Question | Tracking |
|----|----------|---------|
| OQ-1 | Async support — `async_execute()` for Django async views? | Future minor version |
| OQ-2 | Multi-turn research (iterative deepening with follow-up LLM calls)? | Future research sub-module |
| OQ-3 | Should `authoringfw` emit `platform_context.audit.emit_audit_event()`? | Discuss in implementation |

---

## 9. References

- [ADR-050: Platform Decomposition](ADR-050-platform-decomposition-hub-landscape.md) — hub landscape; this ADR amends §3 to add `authoringfw` as explicit shared package
- [ADR-057: Four-Level Test Strategy](ADR-057-platform-test-strategy.md) — test requirements (§7)
- [ADR-068: Adaptive Model Routing](ADR-068-adaptive-model-routing.md) — agent-tier routing (orthogonal — see §4.8)
- [ADR-089: bfagent-llm LiteLLM](ADR-089-bfagent-llm-litellm-db-driven-architecture.md) — `aifw` backend
- [ADR-095: aifw Quality-Level Routing](ADR-095-aifw-quality-level-routing.md) — `get_action_config()`, `BaseContentOrchestrator` pattern, `QualityLevel` constants
- [ADR-097: aifw 0.6.0 Implementation Contract](ADR-097-aifw-060-implementation-contract.md) — technical implementation prerequisite
- `iil-authoringfw`: https://github.com/achimdehnert/authoringfw
- `iil-aifw`: https://github.com/achimdehnert/aifw
- `iil-promptfw`: https://github.com/achimdehnert/promptfw
