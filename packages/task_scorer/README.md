# task-scorer

Shared scoring and routing engine for task complexity estimation.

Zero-dependency Python package that provides weighted multi-dimension
keyword scoring with sigmoid confidence calibration. Consolidates
scoring logic from BFAgent (TestRequirement, LLMRouter) and
Orchestrator MCP (analyzer).

**ADR**: [ADR-023 Shared Scoring and Routing Engine](../../docs/adr/ADR-023-shared-scoring-routing-engine.md)

## Installation

```bash
# From git (recommended for Docker)
pip install "task-scorer @ git+ssh://git@github.com/achimdehnert/platform.git@main#subdirectory=packages/task_scorer"

# Local development
pip install -e ".[dev]"
```

## Usage

```python
from task_scorer import score_task, ScoringConfig, Tier

# With defaults
result = score_task("fix the authentication bug in the API")
print(result.top_type)    # "security"
print(result.tier)        # Tier.HIGH
print(result.confidence)  # 0.87
print(result.signals)     # ["security(auth)", "bug(fix)"]
print(result.is_ambiguous)  # False

# With custom config (e.g. from DB lookup tables)
config = ScoringConfig(
    keywords={"security": ["auth", "cve", "credential"]},
    weights={"security": 2.0},
    tier_boundaries=(0.5, 1.5),
)
result = score_task("check auth flow", config=config)

# With structured metadata
result = score_task(
    "refactor the authentication module",
    category="security",
    acceptance_criteria_count=5,
    files_affected=8,
)
```

## API

### `score_task(description, config=None, category=None, acceptance_criteria_count=0, files_affected=0) -> ScoringResult`

Main entry point. Scores a task description against all configured
task types using weighted keyword matching.

### `ScoringResult`

| Field | Type | Description |
|-------|------|-------------|
| `scores` | `dict[str, float]` | All type scores |
| `top_type` | `str` | Highest scoring type |
| `tier` | `Tier` | LOW / MEDIUM / HIGH |
| `confidence` | `float` | Sigmoid confidence [0, 1] |
| `signals` | `list[str]` | Debug signals |
| `is_ambiguous` | `bool` | True if confidence < threshold |
| `raw_score` | `float` | Winner's weighted score |

### `ScoringConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `keywords` | `dict[str, list[str]]` | 10 types, 85 keywords | Task type keywords |
| `weights` | `dict[str, float]` | 0.5 - 1.5 | Type weight multipliers |
| `tier_boundaries` | `tuple[float, float]` | (1.0, 4.0) | LOW/MEDIUM/HIGH boundaries |
| `confidence_steepness` | `float` | 8.0 | Sigmoid steepness |
| `confidence_threshold` | `float` | 0.65 | Ambiguity threshold |

## Testing

```bash
cd packages/task_scorer
pip install -e ".[dev]"
python3 -m pytest tests/ -v
```

## Architecture

```
src/task_scorer/
├── __init__.py    # Public API exports
├── types.py       # ScoringConfig, ScoringResult, Tier, DEFAULT_KEYWORDS
└── scorer.py      # score_task, _score_all_types, _sigmoid_confidence
```

- **Zero dependencies** — stdlib only (math, dataclasses, enum)
- **Frozen dataclasses** — immutable config and results
- **Config injection** — defaults in code, DB-driven override via ScoringConfig
- **Tenant-agnostic** — pure function, no database access
