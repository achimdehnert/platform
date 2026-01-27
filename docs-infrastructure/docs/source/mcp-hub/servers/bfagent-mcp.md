# BFAgent MCP

BF Agent Integration Server für Requirements, Feedback und Domain-Wissen.

## Installation

```bash
cd mcp-hub/bfagent_mcp
pip install -e .
```

## Konfiguration

```json
{
  "mcpServers": {
    "bfagent-mcp": {
      "command": "python",
      "args": ["-m", "bfagent_mcp.server"],
      "env": {
        "BFAGENT_API_URL": "http://localhost:8000",
        "BFAGENT_DB_PATH": "/path/to/db.sqlite3"
      }
    }
  }
}
```

## Tools

### get_requirement

Requirement/Bug Details abrufen.

```python
result = await get_requirement(
    requirement_id="uuid-here",
    include_feedback=True,
)
```

### add_feedback

Feedback zu einem Requirement hinzufügen.

```python
result = await add_feedback(
    requirement_id="uuid-here",
    content="Progress update: Fixed the bug",
    feedback_type="progress",  # comment, progress, blocker, question, solution
)
```

### update_requirement_status

Status eines Requirements aktualisieren.

```python
result = await update_requirement_status(
    requirement_id="uuid-here",
    status="done",  # draft, ready, in_progress, done, completed, blocked
    notes="Completed and tested",
)
```

### list_domains

Alle BF Agent Domains auflisten.

```python
result = await list_domains(
    status_filter="production",  # production, beta, development
    include_handlers=True,
)
```

### get_domain

Domain-Details mit Handlern und Phasen.

```python
result = await get_domain(
    domain_id="books",
    include_handlers=True,
    include_phases=True,
)
```

### search_handlers

Handler nach Funktionalität suchen.

```python
result = await search_handlers(
    query="PDF parsing",
    domain_filter="books",
    limit=10,
)
```

### check_path_protection

Prüfen ob ein Dateipfad geschützt ist.

```python
result = await check_path_protection(
    file_path="apps/books/handlers/chapter_handler.py",
)
```

### get_best_practices

Best Practices für ein Thema abrufen.

```python
result = await get_best_practices(
    topic="handlers",  # handlers, pydantic, ai_integration, testing
    include_examples=True,
)
```

## Resources

### Domain Knowledge

```
resource://bfagent/domains
resource://bfagent/handlers
resource://bfagent/naming-conventions
```

### Workflow Rules

```
resource://bfagent/workflow-rules
resource://bfagent/component-types
```

## Integration mit BF Agent Django

Der Server kommuniziert mit der BF Agent Django-Anwendung über:

1. **REST API** - Für CRUD-Operationen
2. **SQLite** - Für schnelle Lesezugriffe (via bfagent_sqlite_mcp)
3. **PostgreSQL** - Für Produktionsdaten (via bfagent-db MCP)
