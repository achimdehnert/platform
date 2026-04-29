---
description: Check platform governance before implementing new functionality
---

# Platform Governance Check Workflow

**IMPORTANT**: Run this workflow BEFORE implementing any new functionality.
Für neue Features: zuerst `/pre-code` (Contract Verification), dann dieser Check.

> ⚠️ MCP-Prefix ist environment-spezifisch — `<ctx>` = Platform-Context-Prefix aus `project-facts.md`.

## Step 1: Existing Component Check

Existiert die Funktionalität bereits? Erst suchen, dann implementieren:

```bash
# Codebase-Suche nach ähnlichen Implementierungen
grep -r "<funktionsbeschreibung>" src/ --include="*.py" -l | head -10
```

```
MCP: <ctx>_get_context_for_task(repo="<repo>", file_type="<datei>")
→ Liefert: Architektur-Regeln, ADR-Referenzen, Banned Patterns, Repo-Facts
```

## Step 2: Governance Rules prüfen

### LLM Access (BLOCK)
- ❌ Niemals `import anthropic`, `import openai`, `import litellm` direkt in Django-Apps
- ✅ `from aifw import sync_completion` — action_code-basiert, DB-driven routing
- ✅ Ausnahme: Standalone CI-Scripts ohne Django-DB → `litellm` direkt erlaubt

### Database Access
- ❌ Kein raw `psycopg2` in Application-Code
- ✅ Django ORM ausschließlich

### Status Choices (Platform Standard)
- ❌ `STATUS_CHOICES = [('active', 'Active'), ...]` — veraltet
- ✅ `class Status(models.TextChoices): ACTIVE = 'active', _('Aktiv')`

### Prompts
- ❌ Inline f-Strings für komplexe Multi-Layer-Prompts
- ✅ `from promptfw import PromptTemplate` (wenn iil-promptfw verfügbar)

### iil-* Packages (PyPI-First Principle)
Vor eigener Implementierung prüfen:
```bash
pip list | grep iil
```
→ Bekannte Packages: `aifw`, `iil-promptfw`, `iil-authoringfw`, `iil-weltenfw`, `iil-nl2cadfw`, `iil-testkit`

## Step 3: Korrekte Services verwenden

| Bedarf | Verwende | NICHT |
|--------|----------|-------|
| LLM-Calls | `aifw.sync_completion(action_code, messages)` | `openai`, `anthropic` direkt |
| Status/Choices | `models.TextChoices` | Hardcoded Tupel-Listen |
| Prompts | `promptfw.PromptTemplate` | Inline f-Strings |
| ADR-Check | `<ctx>_check_violations(code_snippet)` | Manuell |

## Step 4: Architektur-Verletzungen prüfen

```
MCP: <ctx>_check_violations(code_snippet="<generierter Code>")
MCP: <ctx>_get_banned_patterns(context="<views|models|htmx|deployment>")
```

→ Blockiert bei CRITICAL Violations. Kein Weiter ohne grünen Check.

## Step 5: HTMX-Detection prüfen (wenn Templates betroffen)

> Detection ist **repo-spezifisch** — `project-facts.md` prüfen!

```bash
# django-htmx installiert?
grep "django-htmx\|django_htmx" requirements.txt
```

| Ergebnis | Korrekte Detection |
|----------|--------------------|
| `django-htmx` vorhanden | `if request.htmx:` |
| Nicht installiert | `if request.headers.get("HX-Request"):` |

❌ Nie mischen — `request.htmx` ohne Package crashärt lautlos.
