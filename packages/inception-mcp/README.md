# Inception MCP Server

**ADR-017: Domain Development Lifecycle**

MCP Server for AI-driven Business Case creation through conversational interface.

## Overview

This MCP server provides tools for creating, refining, and finalizing Business Cases through a structured question-answer workflow. It integrates with the governance database and optionally uses LLM for intelligent extraction.

## Tools

| Tool | Description |
|------|-------------|
| `start_business_case` | Start new BC from free-text description |
| `answer_question` | Answer clarifying questions |
| `finalize_business_case` | Finalize BC and derive Use Cases |
| `list_business_cases` | List BCs with filters |
| `get_business_case` | Get full BC details |
| `get_categories` | Get available categories |
| `submit_for_review` | Submit BC for review |
| `get_session_status` | Check inception session status |

## Installation

```bash
cd packages/inception-mcp
pip install -e .
```

## Configuration

Environment variables:

```bash
# Database connection
DATABASE_URL=postgresql://user:pass@localhost:5432/platform

# LLM Gateway (optional)
LLM_GATEWAY_URL=http://localhost:8080/v1
LLM_API_KEY=sk-...
LLM_MODEL=claude-3-sonnet
```

## Usage

### Run as MCP Server

```bash
inception-mcp
```

### Configure in Windsurf/Claude Desktop

Add to `mcp_config.json`:

```json
{
  "mcpServers": {
    "inception": {
      "command": "inception-mcp",
      "env": {
        "DATABASE_URL": "postgresql://..."
      }
    }
  }
}
```

## Workflow

1. **Start**: Call `start_business_case` with initial description
2. **Refine**: Answer questions via `answer_question` (7 questions)
3. **Finalize**: Call `finalize_business_case` to complete
4. **Review**: Submit via `submit_for_review` when ready

### Example Session

```
User: Create BC for "Wir brauchen eine bessere Suchfunktion"

→ start_business_case(initial_description="Wir brauchen...")
← session_id, bc_code="BC-001", question="Wer ist die Zielgruppe?"

User: Alle registrierten Benutzer

→ answer_question(session_id, answer="Alle registrierten Benutzer")
← question="Welche konkreten Vorteile werden erwartet?"

... (5 more questions) ...

→ finalize_business_case(session_id, derive_use_cases=true)
← bc_code="BC-001", derived_use_cases=[...], next_steps=[...]
```

## Questions

The inception workflow asks these questions in order:

1. **target_audience**: Who benefits?
2. **expected_benefits**: What benefits are expected?
3. **scope**: What's included?
4. **out_of_scope**: What's excluded?
5. **success_criteria**: How to measure success?
6. **risks**: What risks exist?
7. **requires_adr**: Is an ADR needed?

## Database Schema

Uses tables from `apps.governance`:

- `platform.dom_business_case`
- `platform.dom_use_case`
- `platform.dom_conversation`
- `platform.dom_conversation_turn`
- `platform.dom_status_history`
- `platform.lkp_domain` / `platform.lkp_choice`

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Related

- **ADR-015**: Platform Governance System
- **ADR-017**: Domain Development Lifecycle
- **governance app**: Django models and admin
