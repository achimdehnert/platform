---
description: Check platform governance before implementing new functionality
---

# Platform Governance Check Workflow

**IMPORTANT**: Run this workflow BEFORE implementing any new functionality.

## Step 1: Check Registry for Existing Components

Before implementing anything new, check if it already exists:

```
Use registry_mcp.check_existing with the functionality description
```

This searches across:
- MCP Servers
- Internal Services  
- Handlers
- Design Patterns
- AI Agents

## Step 2: Review Governance Rules

Key rules to follow:

### LLM Access (BLOCK)
- ❌ Never `import anthropic` or `import openai` directly
- ✅ Use `llm_mcp` tools: `llm_complete`, `llm_stream`, `llm_chat`

### Database Access (WARN)
- ❌ Avoid raw `psycopg2` in application code
- ✅ Use Django ORM or `LookupService`

### Lookups (WARN)
- ❌ No hardcoded `STATUS_CHOICES = [('active', 'Active'), ...]`
- ✅ Use `LookupService.get_for_django_choices("status")`

### Prompts (LOG)
- ❌ Avoid inline prompt strings
- ✅ Use `PromptFrameworkService.render("template_name", context)`

## Step 3: Use Correct Services

| Need | Use This | NOT This |
|------|----------|----------|
| LLM calls | `llm_mcp` | `anthropic`, `openai` |
| Status/choices | `LookupService` | Python enums |
| Prompts | `PromptFrameworkService` | Inline strings |
| Component discovery | `registry_mcp` | Manual search |

## Step 4: Register New Components

After implementing, register in the platform registry:

```sql
INSERT INTO platform.reg_service (name, code, fqn, description, ...)
VALUES ('YourService', 'your_service', 'apps.yourapp.services.YourService', ...);
```
