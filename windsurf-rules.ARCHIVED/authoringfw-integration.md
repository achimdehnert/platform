# authoringfw Integration — Rules

> Glob-Activated: `**/services/*.py`, `**/models/*.py`, `**/schema*.py`, `requirements.txt`
> PyPI: `iil-authoringfw>=0.3.0` — domain schemas for AI-assisted creative writing

## What authoringfw Provides

| Export | Purpose |
|---|---|
| `StyleProfile` | Writing style definition (tone, POV, language register) |
| `CharacterProfile` | Character schema (name, traits, arc, relationships) |
| `WorldContext` | Story world (setting, rules, geography, lore) |
| `VersionMetadata` | Content versioning (change tracking, phase snapshots) |
| `ChangeType` | Enum for version change classification |
| `PhaseSnapshot` | Point-in-time snapshot of a writing phase |
| `FormatProfile` | Output format (novel, screenplay, short story, etc.) |
| `WorkflowPhase` | Enum for authoring workflow phases |
| `get_format` | Lookup `FormatProfile` by name |
| `ConsistencyChecker` | Cross-document consistency validation |
| `ConsistencyReport` | Result of consistency check |
| `ConsistencyIssue` | Individual consistency violation |
| `PlanningFieldConfig` | Config for planning phase field definitions |
| `get_planning_config` | Get planning config by format |

## Import Pattern (MANDATORY)

```python
# CORRECT — use authoringfw schemas as canonical domain models
from authoringfw import CharacterProfile, WorldContext, StyleProfile
from authoringfw import ConsistencyChecker, FormatProfile, get_format

character = CharacterProfile(
    name="Elena",
    role="protagonist",
    traits=["determined", "empathetic"],
)

world = WorldContext(
    name="Aethoria",
    setting="Fantasy",
    rules=["Magic requires sacrifice"],
)

# BANNED — local dataclasses that duplicate authoringfw
@dataclass
class Character:
    name: str
    description: str  # already in CharacterProfile

class WorldContext:  # name collision — never redefine
    ...
```

## Combined Pipeline with aifw + promptfw

```python
# CORRECT — full pipeline
from authoringfw import CharacterProfile, WorldContext, StyleProfile
from promptfw import get_writing_stack, PromptRenderer
from aifw import sync_completion

def enrich_character(character: CharacterProfile, world: WorldContext) -> CharacterProfile:
    stack = get_writing_stack()
    rendered = PromptRenderer().render(stack, context={
        "character": character.model_dump(),
        "world": world.model_dump(),
    })
    result = sync_completion(rendered, action_code="character_enrichment")
    # parse and update character from result.content
    return character
```

## Consistency Checking

```python
# CORRECT — use ConsistencyChecker before persisting AI-generated content
from authoringfw import ConsistencyChecker, ConsistencyReport

checker = ConsistencyChecker()
report: ConsistencyReport = checker.check(chapters=chapters, characters=characters)
if report.has_issues:
    for issue in report.issues:
        logger.warning("Consistency: %s", issue.description)

# BANNED — skipping consistency checks before saving AI content
chapter.save()  # without consistency validation
```

## Versioning

```python
# CORRECT — track content changes with VersionMetadata
from authoringfw import VersionMetadata, ChangeType, PhaseSnapshot

version = VersionMetadata(
    change_type=ChangeType.AI_ENRICHMENT,
    author="aifw",
    note="Character backstory enriched",
)

# BANNED — no versioning on AI-modified content
chapter.content = ai_result  # no version tracking
chapter.save()
```

## Refactoring Trigger Patterns

| Found Pattern | Replace With |
|---|---|
| Local `Character`, `Person`, `Actor` dataclass | `CharacterProfile` from `authoringfw` |
| Local `World`, `Setting`, `Universe` dataclass | `WorldContext` from `authoringfw` |
| Local `Style`, `WritingStyle`, `Tone` dataclass | `StyleProfile` from `authoringfw` |
| Manual cross-chapter consistency checks | `ConsistencyChecker` |
| `version = 1` / `updated_at = now()` for AI content | `VersionMetadata` with `ChangeType` |
| `format_type = "novel"` hardcoded string | `get_format("novel")` → `FormatProfile` |

## BANNED

- Redefining domain schemas (`Character`, `World`, `Style`) locally when `authoringfw` covers them
- Saving AI-generated content without `ConsistencyChecker` validation
- Skipping `VersionMetadata` for AI-modified creative content
- Using `dict` instead of typed `authoringfw` Pydantic models in service signatures
