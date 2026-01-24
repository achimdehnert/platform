# Django-HTMX MCP Server

Ein [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) Server für Django + HTMX Entwicklung. Generiert produktionsreifen Code mit Best Practices.

## Features

### 🏗️ Model Generation
- Django Models mit Timestamps, UUID PKs, Soft Delete
- Custom Managers und QuerySets
- TextChoices/IntegerChoices Klassen

### 👁️ View Generation  
- Class-Based Views mit HTMX Support
- HTMX Action Views (Toggle, Inline Edit, Bulk Actions)
- Live Search Views

### 📄 Template Generation
- HTMX-optimierte List/Detail/Form Templates
- Partial Templates für HTMX Requests
- UI-Komponenten (Toast, Modal, Loading, etc.)

### 📝 Form Generation
- ModelForms mit Crispy Forms Support
- django-filter FilterSets
- Search Forms mit HTMX
- Bulk Action Forms

### 🔗 URL Generation
- CRUD URL Patterns
- HTMX Action URLs
- DRF API URLs

### 🧪 Test Generation
- pytest-django Tests
- Factory Boy Factories
- HTMX-spezifische Tests

### 🏭 Scaffolding
- Komplette Django Apps
- HTMX Komponenten (Infinite Scroll, Live Search, etc.)

### 🔍 Analysis & Refactoring
- View-Analyse für HTMX-Optimierung
- FBV → CBV Konvertierung
- Template-Analyse
- HTMX Pattern Vorschläge

## Installation

```bash
pip install django-htmx-mcp
```

Oder für Entwicklung:

```bash
git clone https://github.com/you/django-htmx-mcp.git
cd django-htmx-mcp
pip install -e ".[dev]"
```

## Verwendung

### Als MCP Server

```json
// In Ihrer MCP Client Konfiguration (z.B. Claude Desktop)
{
  "mcpServers": {
    "django-htmx": {
      "command": "django-htmx-mcp"
    }
  }
}
```

### Verfügbare Tools

#### Model Tools

```python
# Django Model generieren
generate_django_model(
    model_name="Task",
    fields=[
        {"name": "title", "type": "CharField", "max_length": 200},
        {"name": "completed", "type": "BooleanField", "default": False},
        {"name": "assignee", "type": "ForeignKey", "to": "User", "on_delete": "CASCADE", "null": True},
    ],
    with_timestamps=True,
    with_soft_delete=True
)

# Choices Klasse generieren
generate_choices_class(
    name="TaskStatus",
    choices=[("PENDING", "Pending"), ("DONE", "Done")]
)

# Custom Manager generieren
generate_model_manager(
    model_name="Task",
    with_soft_delete=True,
    custom_methods=[{"name": "pending", "filter": {"status": "pending"}}]
)
```

#### View Tools

```python
# Class-Based View generieren
generate_cbv(
    view_name="TaskListView",
    view_type="ListView",
    model="Task",
    htmx_enabled=True,
    paginate_by=25
)

# HTMX Action View
generate_htmx_action_view(
    view_name="TaskToggleView",
    model="Task",
    action="toggle",
    field="completed"
)

# Live Search View
generate_htmx_search_view(
    view_name="TaskSearchView",
    model="Task",
    search_fields=["title", "description"]
)
```

#### Template Tools

```python
# List Template mit Partial
generate_htmx_list_template(
    model="Task",
    columns=[
        {"field": "title", "label": "Title", "sortable": True},
        {"field": "status", "label": "Status"},
    ],
    with_search=True,
    with_pagination=True,
    infinite_scroll=False
)

# Form Template
generate_htmx_form_template(
    model="Task",
    form_type="modal"  # oder "page", "inline"
)

# UI Komponenten
generate_htmx_component(
    component_type="toast"  # oder "confirmation_modal", "loading_indicator", etc.
)
```

#### Scaffolding Tools

```python
# Komplette App scaffolden
scaffold_django_app(
    app_name="tasks",
    models=[{
        "name": "Task",
        "fields": [
            {"name": "title", "type": "CharField", "max_length": 200},
            {"name": "completed", "type": "BooleanField", "default": False},
        ]
    }],
    with_admin=True,
    with_tests=True,
    template_style="htmx"
)

# HTMX Komponente scaffolden
scaffold_htmx_component(
    component_name="TaskSearch",
    component_type="live_search",
    model="Task"
)
```

#### Analysis Tools

```python
# View analysieren
analyze_view_for_htmx(view_code="...")

# FBV zu CBV konvertieren
convert_fbv_to_cbv(function_view_code="...")

# HTMX Pattern vorschlagen
suggest_htmx_pattern(use_case="infinite_scroll")

# Migration planen
generate_htmx_migration_plan(
    app_name="tasks",
    views=["TaskListView", "TaskCreateView"],
    templates=["task_list.html", "task_form.html"]
)
```

## Beispiel-Workflow

```
User: Erstelle eine Task-Management App mit HTMX

Claude (mit MCP):
1. scaffold_django_app("tasks", models=[...])
2. generate_htmx_list_template("Task", with_search=True)
3. generate_htmx_form_template("Task", form_type="modal")
4. scaffold_htmx_component("TaskSearch", "live_search", "Task")
5. generate_view_tests("Task", "tasks", "list", with_htmx=True)
```

## Entwicklung

```bash
# Tests ausführen
pytest

# Linting
ruff check .
ruff format .
```

## Lizenz

MIT

## Beitragen

Beiträge sind willkommen! Bitte öffne ein Issue oder Pull Request.
