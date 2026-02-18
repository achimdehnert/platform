# Docs Agent

AI-assisted documentation quality tool for Python projects.

Scans codebases for docstring coverage, classifies documentation files using the
[DIATAXIS framework](https://diataxis.fr/), and generates missing docstrings via LLM.

## Features

- **Docstring Coverage Audit** — AST-based scanning of Python files with per-module reporting
- **DIATAXIS Classification** — Heuristic + LLM-powered classification of docs into tutorial/guide/reference/explanation
- **LLM Docstring Generation** — Batch generation of Google-style docstrings via llm_mcp gateway or OpenAI API
- **Non-Destructive Code Insertion** — Insert generated docstrings using libcst while preserving all formatting
- **Pre-Commit Hooks** — Enforce coverage thresholds in CI/CD pipelines
- **CI Integration** — GitHub Actions workflow for automated testing

## Installation

```bash
# From platform monorepo (editable, recommended)
pip install -e packages/docs-agent

# With LLM support (httpx, openai, libcst)
pip install -e "packages/docs-agent[llm]"

# With dev tools (pytest, coverage)
pip install -e "packages/docs-agent[dev]"

# From GitHub (in requirements.txt)
docs-agent @ git+https://github.com/achimdehnert/platform.git@main#subdirectory=packages/docs-agent
```

## Quick Start

```bash
# Audit docstring coverage
docs-agent audit /path/to/repo

# Audit only apps/ directory
docs-agent audit /path/to/repo --apps-only

# JSON output for CI
docs-agent audit /path/to/repo --output json

# Fail if coverage < 60%
docs-agent audit /path/to/repo --min-coverage 60

# DIATAXIS only
docs-agent audit /path/to/repo --scope diataxis

# Refine low-confidence classifications via LLM
docs-agent audit /path/to/repo --scope diataxis --refine
```

## CLI Reference

### `docs-agent audit`

Audit a repository for documentation quality.

```text
Usage: docs-agent audit [OPTIONS] REPO_PATH

Arguments:
  REPO_PATH    Path to the repository root [required]

Options:
  --scope TEXT           Audit scope: docstrings, diataxis, or all [default: all]
  --apps-only            Only scan apps/ directory for docstrings
  --min-coverage FLOAT   Fail if docstring coverage is below this %
  --output TEXT          Output format: table or json [default: table]
  --refine               Use LLM to refine low-confidence DIATAXIS classifications
  --llm-url TEXT         URL of the llm_mcp HTTP gateway [default: http://localhost:8100]
```

### `docs-agent generate`

Generate docstrings for undocumented code items via LLM.

```text
Usage: docs-agent generate [OPTIONS] REPO_PATH

Arguments:
  REPO_PATH    Path to the repository root [required]

Options:
  --apps-only            Only scan apps/ directory
  --dry-run / --apply    Preview changes (default) or apply them
  --max-items INTEGER    Maximum items to generate docstrings for [default: 20]
  --llm-url TEXT         URL of the llm_mcp HTTP gateway [default: http://localhost:8100]
  --model TEXT           LLM model name [default: gpt-4o-mini]
```

## Example Output

### Docstring Coverage Table

```text
                    Module Coverage
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Module                        ┃ Items ┃ Documented ┃ Coverage ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╉━━━━━━━╉━━━━━━━━━━━━╉━━━━━━━━━━┩
│ apps/core/models.py           │    12 │          8 │ 67%      │
│ apps/core/services.py         │     6 │          6 │ 100%     │
│ apps/core/views.py            │     9 │          3 │ 33%      │
└───────────────────────────────┴───────┴────────────┴──────────┘

Total: 17/27 items documented (63.0%)
```

### DIATAXIS Classification

```text
              DIATAXIS Classification
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Document                    ┃  Quadrant   ┃ Confidence ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╉━━━━━━━━━━━━━╉━━━━━━━━━━━━┩
│ docs/getting-started.md     │  tutorial   │        85% │
│ docs/deploy-guide.md        │    guide    │        72% │
│ docs/api-reference.md       │  reference  │        90% │
│ docs/adr/ADR-001.md         │ explanation │        78% │
└─────────────────────────────┴─────────────┴────────────┘
```

## Pre-Commit Integration

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/achimdehnert/platform
    rev: main
    hooks:
      - id: docs-agent-coverage
        args: ["--scope", "docstrings", "--min-coverage", "50"]
```

## Architecture

```text
docs_agent/
├── analyzer/
│   ├── ast_scanner.py          # AST-based docstring coverage scanning
│   ├── diataxis_classifier.py  # Heuristic DIATAXIS classification
│   └── llm_classifier.py       # LLM fallback for low-confidence docs
├── generator/
│   ├── docstring_gen.py         # Batch LLM docstring generation
│   └── code_inserter.py         # Non-destructive libcst insertion
├── cli.py                       # Typer CLI (audit + generate commands)
├── llm_client.py                # HTTP gateway + OpenAI fallback
├── models.py                    # Data models (CodeItem, Coverage, etc.)
└── prompts.py                   # LLM prompt templates
```

## Configuration

### Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `DOCS_AGENT_LLM_URL` | `http://localhost:8100` | llm_mcp gateway URL |
| `DOCS_AGENT_LLM_MODEL` | `gpt-4o-mini` | LLM model name |
| `OPENAI_API_KEY` | — | Direct OpenAI fallback (optional) |

### LLM Backend

The docs-agent tries backends in this order:

1. **llm_mcp HTTP gateway** (default, `http://localhost:8100`) — production setup
2. **Direct OpenAI API** — fallback if gateway is down and `OPENAI_API_KEY` is set

## Development

```bash
cd packages/docs-agent

# Install with dev + LLM extras
pip install -e ".[dev,llm]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=docs_agent --cov-report=term-missing
```

## Related

- **ADR-046**: Documentation Quality Standards (defines the docs-agent specification)
- **DIATAXIS**: <https://diataxis.fr/> — Documentation framework
- **Platform**: <https://github.com/achimdehnert/platform> — Monorepo

## License

MIT
