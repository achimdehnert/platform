---
status: proposed
date: 2026-04-04
decision-makers: Achim Dehnert
implementation_status: not_started
implementation_evidence: []
tags: [promptfw, prompt-management, cross-hub, database, django, CRUD]
related: [ADR-083, ADR-089, ADR-093, ADR-121, ADR-133]
---

# ADR-146: Hub-übergreifendes DB-Prompt-Management — promptfw als SSoT für editierbare Prompts

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-04-04 |
| **Author** | Achim Dehnert |
| **Decision-Makers** | Achim Dehnert |
| **Related** | ADR-083 (promptfw Integration writing-hub), ADR-089 (LiteLLM DB-driven), ADR-093 (AI Config App), ADR-121 (outlinefw), ADR-133 (Shared AI Services), promptfw ADR-001 (Four-Layer Stack), promptfw ADR-002 (YAML vs DB Registry), promptfw ADR-003 (Extension Roadmap) |
| **Scope** | Platform-wide (alle Hubs mit LLM-Nutzung) |

---

## 1. Context and Problem Statement

Prompts sind das **Kernstück jeder LLM-Nutzung**. Die Qualität der Ergebnisse steht und fällt mit der Qualität der Prompts. Aktuell existieren über die Plattform hinweg **~84 Prompts in 4 inkompatiblen Patterns**, verteilt auf 3+ Hubs — ohne einheitliche CRUD-Oberfläche, ohne Versionierung, ohne die Möglichkeit, Prompts live anzupassen.

### 1.1 Bestandsaufnahme: 4 Prompt-Patterns, 0 Konsistenz

| Hub | Pattern | Prompts | Editierbar? | Variablen? | Defaults? | Versioniert? |
|-----|---------|---------|-------------|------------|-----------|--------------|
| **writing-hub** | `.jinja2` Frontmatter-Files via `render_prompt()` | **46** | Nur via Deploy | Jinja2 `{{ var }}` | Nein | Git only |
| **travel-beat** | `PromptTemplateSpec` Dataclasses + `InMemoryRegistry` + `render_template()` via promptfw | **5 registriert** + **~30 inline** | Hardcoded | `PromptVariable` (typed, default) | Ja | Nein |
| **research-hub** | Raw f-strings in Services | **~3** | Hardcoded | f-string only | Nein | Nein |
| **bfagent** (Legacy) | Django `PromptTemplate` Model + `PromptFactory` + `PromptStackService` | **~50+** | DB + Admin | required + optional vars | Ja | DB-Versions |

**Gesamt: ~84 aktive Prompts + ~50 Legacy-Prompts in bfagent.**

### 1.2 Was promptfw heute bereits bietet (v0.7.0)

| Modul | Zweck | Status |
|-------|-------|--------|
| `PromptTemplate` (schema.py) | 5-Layer Dataclass (id, layer, template, variables, version, output_schema, response_format, metadata) | Stabil |
| `TemplateRegistry` (registry.py) | In-Memory Registry mit `register()`, `get()`, `from_directory()` | Stabil |
| `DjangoTemplateRegistry` (django_registry.py) | Laedt aus Django ORM Queryset mit konfigurierbarem `FieldMap`, SYSTEM/TASK-Split | Implementiert |
| `DBPromptResolver` (db_resolver.py) | 3-Tier Resolution: DB → promptfw Stack → Generic Fallback | Implementiert |
| `PromptRenderer` (renderer.py) | Jinja2 Rendering mit StrictUndefined | Stabil |
| `PromptStack` (stack.py) | Multi-Template Stack-Assembly | Stabil |
| Built-in Stacks | `planning.py`, `writing.py`, `lektorat.py`, `concept_analysis.py` | Stabil |
| `parsing.py` | `extract_json()`, `extract_json_list()`, `strip_reasoning_tags()` | Stabil |
| `frontmatter.py` | `.jinja2` YAML-Frontmatter Rendering | v0.7.0 |

**Kritische Erkenntnis:** promptfw hat bereits die Bausteine fuer DB-backed Prompts (`DjangoTemplateRegistry`, `DBPromptResolver`), aber es fehlt:

1. **Ein shared Django Model** — jeder Hub muesste sein eigenes Model mitbringen
2. **CRUD Admin UI** — `DjangoTemplateRegistry` liest nur, schreibt nicht
3. **Einheitliche Resolution-API** — `render_prompt()` in writing-hub und `render_template()` in travel-beat sind inkompatibel
4. **Variable-Schema + Defaults** — travel-beat hat es, writing-hub nicht
5. **Migrations-Tooling** — kein `seed_prompts` / `export_prompts`

### 1.3 Konkrete Schmerzen

| Schmerz | Beispiel | Auswirkung |
|---------|----------|------------|
| **Prompt-Aenderung erfordert Deploy** | writing-hub: Stil-Anweisung in `chapter_write_production.jinja2` aendern → Git commit, Docker build, Deploy | ~10 min statt 10 sec |
| **Inkonsistente Qualitaet** | research-hub: Prompt ist ein nackter f-string ohne System-Prompt → schlechtere Ergebnisse | Qualitaetsverlust |
| **Keine Variablen-Dokumentation** | writing-hub `.jinja2`: Welche Variablen erwartet `chapter_analyze.jinja2`? → Source-Code lesen | Developer-Overhead |
| **Keine Defaults** | writing-hub: `render_prompt()` crashed wenn Variable fehlt statt Default zu nutzen | Fragile Integration |
| **Kein A/B-Testing** | Welcher Chapter-Prompt liefert bessere Ergebnisse? → Nicht testbar ohne Code-Aenderung | Keine Optimierung |
| **Duplizierung** | ~30 Inline-Prompts in travel-beat sind nicht in der Registry | Wartungsaufwand |

### 1.4 travel-beat als Vorbild

travel-beat hat mit `PromptTemplateSpec` + `StoryFocusConfig` bereits das richtige Pattern etabliert:

```python
# travel-beat/apps/stories/prompts/__init__.py — BEREITS VORHANDEN
@dataclass
class PromptTemplateSpec:
    template_key: str       # "story.chapter.v2"
    domain_code: str        # "story"
    name: str               # "Story Chapter Generator"
    description: str
    system_prompt: str       # Jinja2 Template
    user_prompt: str         # Jinja2 Template
    variables: list[PromptVariable]  # typed, required, default
    llm_config: LLMConfig   # tier, temperature, max_tokens
    tags: list[str]
```

```python
# travel-beat/apps/stories/models/config.py — DB-DRIVEN PROMPT ADDITIONS
class StoryFocusConfig(models.Model):
    storyline_prompt_addition = models.TextField(blank=True)  # editierbar via Admin
    outline_prompt_addition = models.TextField(blank=True)
    chapter_prompt_addition = models.TextField(blank=True)
```

**Dieses Pattern muss plattformweit verfuegbar und vereinheitlicht werden.**

---

## 2. Decision Drivers

1. **Live-Editierbarkeit**: Prompts MUESSEN ohne Deploy aenderbar sein — Prompt-Tuning ist iterativ
2. **Hub-Unabhaengigkeit**: Loesung muss in writing-hub, travel-beat, research-hub und zukuenftigen Hubs funktionieren
3. **Defaults + Fallback**: Wenn kein DB-Eintrag existiert → File-basiertes Template → Built-in → klar definierter Error
4. **Variablen-Schema**: Welche Variablen ein Prompt erwartet, welche Pflicht sind, welche Defaults haben → dokumentiert und validiert
5. **Versionierung + Rollback**: Prompt v1 → bearbeiten → v2. Rollback = alte Version aktivieren
6. **promptfw bleibt Django-frei**: Core-Library hat keine Django-Dependency. DB-Integration ist ein optionaler `contrib`-Layer
7. **Bestehende Infrastruktur nutzen**: `DjangoTemplateRegistry` und `DBPromptResolver` existieren — nicht neu erfinden
8. **SSoT**: Ein Prompt, eine Quelle der Wahrheit. Nicht gleichzeitig in DB und File.

---

## 3. Considered Options

### Option A: `promptfw.contrib.django` — Shared Django App im promptfw-Repo (gewaehlt)

Ein optionaler Django-App-Layer direkt im promptfw-Repo. Enthaelt Model, Admin, Resolution-API, Migration-Tooling.

```
promptfw/
  src/promptfw/
    contrib/
      django/
        __init__.py
        apps.py           # PromptfwConfig (Django AppConfig)
        models.py          # PromptTemplate (DB Model)
        admin.py           # CRUD via Django Admin
        resolution.py      # render_prompt() mit DB->File->Built-in Fallback
        management/
          commands/
            seed_prompts.py     # File -> DB Import
            export_prompts.py   # DB -> File Backup
```

**Pro:**

- promptfw IST SSoT fuer Prompts → DB-Layer gehoert dorthin
- `DjangoTemplateRegistry` + `DBPromptResolver` sind schon da → natuerliche Erweiterung
- Alle Hubs: `pip install iil-promptfw[django]` → `INSTALLED_APPS += ["promptfw.contrib.django"]`
- Einheitliche `render_prompt()` API ueber alle Hubs
- Optional: Hubs ohne Django nutzen weiterhin YAML/In-Code

**Contra:**

- Django-Migrations in einem Library-Package → Versionierung kritisch
- `promptfw` waechst — koennte "too much" werden

### Option B: `iil-promptdb` — Eigenstaendiges Django-Package

Separates Package nur fuer DB-Prompt-Management. Nutzt promptfw als Dependency.

```
packages/iil-promptdb/
  src/promptdb/
    models.py
    admin.py
    resolution.py
    ...
```

**Pro:**

- Klare Trennung: promptfw = Rendering, promptdb = Persistierung
- Eigener Release-Zyklus

**Contra:**

- Neue Dependency fuer alle Hubs
- Dupliziert Teile von `DjangoTemplateRegistry` / `DBPromptResolver`
- Zwei Packages fuer ein kohaerentes Feature

### Option C: In `aifw` integrieren (neben AIActionType)

`aifw` hat bereits DB-driven `AIActionType` fuer LLM-Routing-Parameter. Prompt-Templates als zweites Model daneben.

**Pro:**

- aifw ist in allen Hubs installiert
- LLM-Routing + Prompt-Template am selben Ort

**Contra:**

- aifw's Zustaendigkeit ist LLM-Routing (Model, Temperature, Fallback) — NICHT Prompt-Inhalt
- Vermischt Concerns: "Welches Model?" (aifw) vs. "Was sage ich dem Model?" (promptfw)
- promptfw's `DjangoTemplateRegistry` muesste aifw importieren → Circular-Dependency-Risiko

### Option D: Pro-Hub eigene Models (Status Quo verbessert)

Jeder Hub bringt sein eigenes `PromptTemplate`-Model mit und nutzt `DjangoTemplateRegistry` als Bridge.

**Pro:**

- Hub-spezifische Felder moeglich (z.B. `StoryFocusConfig.chapter_prompt_addition`)
- Keine neue shared Dependency

**Contra:**

- Keine Hub-uebergreifende Konsistenz
- Duplizierter Admin-Code
- Kein einheitliches Migrations-Tooling

---

## 4. Decision Outcome

**Gewaehlt: Option A — `promptfw.contrib.django`**

### Begruendung

- **SSoT-Prinzip**: promptfw ist bereits die Single Source of Truth fuer Prompt-Rendering. Die DB-Persistierung ist die logische Ergaenzung, nicht ein separates Package.
- **Bestehende Bausteine**: `DjangoTemplateRegistry` (liest aus ORM), `DBPromptResolver` (3-Tier-Resolution) und `PromptTemplate` (Schema) existieren bereits. `contrib.django` bringt nur das fehlende DB-Model + Admin + CLI.
- **promptfw ADR-002** hat `DjangoTemplateRegistry` als geplantes `promptfw[django]`-Extra bereits vorgesehen.
- **promptfw ADR-003** hat den Extension-Path `contrib/django.py` dokumentiert.
- **travel-beat-Validierung**: `PromptTemplateSpec` mit typed Variables + Defaults + LLMConfig beweist, dass das Pattern funktioniert. Es muss nur auf DB-Level gehoben werden.

---

## 5. Solution Design

### 5.1 DB Model: `PromptTemplate`

```python
# promptfw/src/promptfw/contrib/django/models.py

from django.conf import settings
from django.db import models


class PromptTemplate(models.Model):
    """DB-managed prompt template with CRUD, versioning, defaults, and variable schema.

    Resolution order (via PromptResolver):
      1. DB: PromptTemplate.objects.filter(action_code=X, is_active=True)
      2. File: PROMPTS_DIR / f"{action_code}.jinja2" (writing-hub pattern)
      3. Built-in: promptfw.writing / promptfw.planning stacks
      4. Error: PromptNotFoundError
    """

    # === Identity ===
    action_code = models.CharField(
        max_length=200, db_index=True,
        help_text='Unique prompt identifier. Convention: "{hub}.{domain}.{action}" '
                  'e.g. "travel-beat.story.chapter", "writing-hub.authoring.chapter_write"'
    )
    version = models.PositiveIntegerField(default=1)

    # === Content (Jinja2 Templates) ===
    system_template = models.TextField(
        blank=True,
        help_text="System-Prompt (Jinja2). Variablen: {{ var_name }}. "
                  "Leer = kein System-Prompt."
    )
    user_template = models.TextField(
        help_text="User-Prompt (Jinja2). Variablen: {{ var_name }}. Pflichtfeld."
    )

    # === Parametrisierung ===
    defaults = models.JSONField(
        default=dict, blank=True,
        help_text='Default-Werte wenn Caller keine uebergibt. '
                  'z.B. {"language": "de", "genre": "Romantic Suspense", "target_words": 2500}'
    )
    variables_schema = models.JSONField(
        default=dict, blank=True,
        help_text='Variablen-Schema fuer Validierung + Admin-UI. '
                  'z.B. {"genre": {"type": "string", "required": true}, '
                  '"target_words": {"type": "integer", "required": false, "default": 2500}}'
    )

    # === LLM Hints (optional — aifw bleibt Routing-SSoT) ===
    suggested_max_tokens = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Empfohlene max_tokens. Wird als llm_overrides an aifw uebergeben."
    )
    suggested_temperature = models.FloatField(
        null=True, blank=True,
        help_text="Empfohlene Temperature (0.0-2.0)."
    )
    response_format = models.CharField(
        max_length=20, blank=True,
        choices=[("text", "Text"), ("json_object", "JSON Object"), ("json_schema", "JSON Schema")],
        help_text="Erwartetes Antwortformat."
    )
    output_schema = models.JSONField(
        default=dict, blank=True,
        help_text="JSON Schema wenn response_format=json_schema."
    )

    # === Metadata ===
    name = models.CharField(max_length=200, blank=True, help_text="Menschenlesbarer Name")
    description = models.TextField(blank=True, help_text="Was tut dieser Prompt?")
    hub = models.CharField(
        max_length=50, blank=True, db_index=True,
        help_text="Quell-Hub: travel-beat, writing-hub, research-hub"
    )
    domain = models.CharField(
        max_length=50, blank=True, db_index=True,
        help_text="Domain: story, authoring, research, worlds"
    )
    tags = models.JSONField(default=list, blank=True)

    # === Lifecycle ===
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True, help_text="Interne Notizen / Aenderungsgrund")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "promptfw"
        db_table = "promptfw_template"
        unique_together = [("action_code", "version")]
        ordering = ["action_code", "-version"]
        indexes = [
            models.Index(fields=["hub", "is_active"]),
            models.Index(fields=["domain", "is_active"]),
            models.Index(fields=["action_code", "is_active", "-version"]),
        ]

    def __str__(self):
        return f"{self.action_code} v{self.version} ({'active' if self.is_active else 'inactive'})"
```

### 5.2 Resolution API: `render_prompt()`

```python
# promptfw/src/promptfw/contrib/django/resolution.py

from __future__ import annotations
import logging
from typing import Any
from jinja2 import Template as Jinja2Template, StrictUndefined
from promptfw.exceptions import TemplateNotFoundError

logger = logging.getLogger(__name__)

_PROMPTS_DIR = None  # Set via configure()


def configure(prompts_dir=None):
    """Configure file-based fallback directory."""
    global _PROMPTS_DIR
    _PROMPTS_DIR = prompts_dir


def render_prompt(action_code: str, **context: Any) -> list[dict[str, str]]:
    """
    Unified prompt resolution — single API for all hubs.

    Resolution order:
      1. DB: PromptTemplate(action_code=X, is_active=True, latest version)
      2. File: PROMPTS_DIR / f"{action_code}.jinja2" (Frontmatter)
      3. Error: TemplateNotFoundError

    Variable merging: defaults (from DB) | context (from caller) — caller wins.

    Returns:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    # 1. DB lookup
    tpl = _load_from_db(action_code)
    if tpl:
        merged = {**tpl.defaults, **context}
        return _render_db_template(tpl, merged)

    # 2. File fallback
    if _PROMPTS_DIR:
        messages = _render_from_file(action_code, context)
        if messages:
            return messages

    # 3. Error
    raise TemplateNotFoundError(
        f"No prompt template found for action_code='{action_code}'. "
        f"Neither in DB (promptfw_template) nor in files ({_PROMPTS_DIR})."
    )


def _load_from_db(action_code: str):
    """Load active template from DB (latest version)."""
    from promptfw.contrib.django.models import PromptTemplate
    return PromptTemplate.objects.filter(
        action_code=action_code, is_active=True
    ).order_by("-version").first()


def _render_db_template(tpl, context: dict) -> list[dict[str, str]]:
    """Render DB template with Jinja2."""
    messages = []
    if tpl.system_template:
        sys_rendered = Jinja2Template(
            tpl.system_template, undefined=StrictUndefined
        ).render(**context).strip()
        if sys_rendered:
            messages.append({"role": "system", "content": sys_rendered})

    user_rendered = Jinja2Template(
        tpl.user_template, undefined=StrictUndefined
    ).render(**context).strip()
    messages.append({"role": "user", "content": user_rendered})
    return messages


def _render_from_file(action_code: str, context: dict):
    """Fallback: render from .jinja2 frontmatter file."""
    from pathlib import Path
    path = Path(_PROMPTS_DIR) / f"{action_code.replace('.', '/')}.jinja2"
    if not path.exists():
        # Try flat layout (writing-hub pattern)
        path = Path(_PROMPTS_DIR) / f"{action_code}.jinja2"
    if not path.exists():
        return None
    try:
        from promptfw.frontmatter import render_frontmatter_file
        return render_frontmatter_file(str(path), context)
    except Exception as exc:
        logger.warning("File fallback failed for %s: %s", action_code, exc)
        return None
```

### 5.3 Admin UI

```python
# promptfw/src/promptfw/contrib/django/admin.py

from django.contrib import admin
from .models import PromptTemplate


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ["action_code", "version", "name", "hub", "domain", "is_active", "updated_at"]
    list_filter = ["hub", "domain", "is_active", "response_format"]
    search_fields = ["action_code", "name", "description", "system_template", "user_template"]
    readonly_fields = ["created_at", "updated_at", "created_by"]

    fieldsets = [
        ("Identity", {
            "fields": ["action_code", "version", "name", "description"]
        }),
        ("Content", {
            "fields": ["system_template", "user_template"],
            "description": "Jinja2-Templates. Variablen: {{ var_name }}"
        }),
        ("Parametrisierung", {
            "fields": ["defaults", "variables_schema"],
            "classes": ["collapse"]
        }),
        ("LLM Hints", {
            "fields": ["suggested_max_tokens", "suggested_temperature",
                       "response_format", "output_schema"],
            "classes": ["collapse"]
        }),
        ("Metadata", {
            "fields": ["hub", "domain", "tags", "notes", "is_active"]
        }),
        ("Audit", {
            "fields": ["created_by", "created_at", "updated_at"]
        }),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
```

### 5.4 Migration CLI

```bash
# Import: .jinja2 Files -> DB
python manage.py seed_prompts --from-dir templates/prompts/ --hub writing-hub

# Import: travel-beat PromptTemplateSpec -> DB
python manage.py seed_prompts --from-registry travel-beat

# Export: DB -> .jinja2 Files (Git-Backup)
python manage.py export_prompts --hub writing-hub --output-dir templates/prompts/

# Validate: Pruefe ob alle action_codes in DB oder Files vorhanden
python manage.py validate_prompts
```

### 5.5 Abgrenzung: promptfw vs. aifw

| Concern | Zustaendig | Beispiel |
|---------|-----------|---------|
| **Was sage ich dem LLM?** | **promptfw** (Prompt-Inhalt, Templates, Variablen, Defaults) | `system_template = "Du bist ein erfahrener Reiseschriftsteller..."` |
| **Welches Model antwortet?** | **aifw** (LLM-Routing, Provider, Fallback) | `AIActionType(code="chapter_write", model="gpt-4o-mini")` |
| **Wie antwortet das Model?** | **Beide** — promptfw: `response_format`, aifw: `temperature`, `max_tokens` | promptfw schlaegt vor, aifw ueberschreibt bei Bedarf |

**Regel:** `PromptTemplate.suggested_max_tokens` / `suggested_temperature` sind **Hinweise** (Defaults). `AIActionType` in aifw hat Vorrang — es ist SSoT fuer LLM-Routing-Parameter.

---

## 6. Variable-Schema + Defaults Design

### Schema-Format

```json
{
  "genre": {
    "type": "string",
    "required": true,
    "description": "Genre der Geschichte",
    "enum": ["romance", "adventure", "thriller", "literary"]
  },
  "target_words": {
    "type": "integer",
    "required": false,
    "default": 2500,
    "min": 500,
    "max": 10000,
    "description": "Ziel-Wortanzahl"
  },
  "language": {
    "type": "string",
    "required": false,
    "default": "de",
    "enum": ["de", "en", "fr", "es"]
  }
}
```

### Resolution-Logik fuer Variablen

```
1. Caller uebergibt context = {"genre": "thriller", "target_words": 3000}
2. DB-Template hat defaults = {"language": "de", "target_words": 2500}
3. Merged: {"genre": "thriller", "target_words": 3000, "language": "de"}
   -> Caller gewinnt bei Konflikten (target_words: 3000 statt 2500)
   -> Default greift nur wenn Caller nichts uebergibt (language: "de")
4. Validierung gegen variables_schema:
   -> genre ist required + vorhanden
   -> target_words ist optional + vorhanden + im Range
   -> language kommt aus defaults
```

---

## 7. Versioning + Rollback Strategy

```
Prompt erstellt:   action_code="story.chapter", version=1, is_active=True
Prompt editiert:   -> Admin klickt "Neue Version"
                   -> version=1 wird is_active=False
                   -> version=2 wird is_active=True (Kopie mit Aenderungen)
Rollback:          -> version=2 wird is_active=False
                   -> version=1 wird is_active=True
```

**Invariante:** Fuer ein `action_code` ist maximal ein `PromptTemplate` mit `is_active=True` zulaessig. Erzwungen via `save()` Override oder DB Trigger.

---

## 8. Migration Plan

### Phase 1 — Foundation (promptfw v0.8.0, Aufwand: 1-2 Tage)

| # | Task | Dateien |
|---|------|---------|
| 1.1 | `promptfw/contrib/django/` Package anlegen | `__init__.py`, `apps.py`, `models.py`, `admin.py`, `resolution.py` |
| 1.2 | Model `PromptTemplate` mit Migrations | `models.py`, `migrations/0001_initial.py` |
| 1.3 | `render_prompt()` Resolution-API | `resolution.py` |
| 1.4 | Admin CRUD | `admin.py` |
| 1.5 | `seed_prompts` Management Command | `management/commands/seed_prompts.py` |
| 1.6 | `export_prompts` Management Command | `management/commands/export_prompts.py` |
| 1.7 | Tests (>=20) | `tests/test_contrib_django.py` |
| 1.8 | `pyproject.toml`: `promptfw[django]` Extra | `pyproject.toml` |
| 1.9 | promptfw v0.8.0 Release | Tag + PyPI |

### Phase 2 — writing-hub Migration (Aufwand: 0.5-1 Tag)

| # | Task | Details |
|---|------|---------|
| 2.1 | `pip install iil-promptfw[django]>=0.8.0` | `requirements.txt` |
| 2.2 | `INSTALLED_APPS += ["promptfw.contrib.django"]` | `config/settings/base.py` |
| 2.3 | `python manage.py migrate promptfw` | Initial-Migration |
| 2.4 | `python manage.py seed_prompts --from-dir templates/prompts/ --hub writing-hub` | 46 Templates -> DB |
| 2.5 | `apps/core/prompt_utils.py` -> `from promptfw.contrib.django.resolution import render_prompt` | Thin-Wrapper wird Einzeiler |
| 2.6 | Verify: alle 46 Prompts per Admin editierbar | Manueller Test |
| 2.7 | `.jinja2`-Files bleiben als Fallback (git-tracked) | Sicherheitsnetz |

### Phase 3 — travel-beat Migration (Aufwand: 1-2 Tage)

| # | Task | Details |
|---|------|---------|
| 3.1 | `INSTALLED_APPS += ["promptfw.contrib.django"]` | `config/settings/base.py` |
| 3.2 | 5 registrierte `PromptTemplateSpec` -> DB via Seed-Script | `seed_prompts --from-registry travel-beat` |
| 3.3 | `InMemoryRegistry` -> DB-backed Resolution | `render_template()` nutzt `render_prompt()` |
| 3.4 | ~30 Inline-Prompts schrittweise extrahieren (Strangler Fig) | Pro Service: f-string -> `render_prompt(action_code, **vars)` |
| 3.5 | `StoryFocusConfig.chapter_prompt_addition` -> `PromptTemplate.defaults` oder Composition | Prompt-Additions als Variablen injizieren |

### Phase 4 — research-hub + weitere Hubs (Aufwand: je 0.5 Tag)

| # | Task |
|---|------|
| 4.1 | research-hub: 3 Inline-Prompts -> DB (`research.summarize`, `research.deep_analysis`, `research.fact_check`) |
| 4.2 | cad-hub, risk-hub, coach-hub: bei naechster Feature-Arbeit migrieren |
| 4.3 | `validate_prompts` in CI integrieren |

---

## 9. Consequences

### 9.1 Positive

- **Live-Editierbarkeit**: Prompt-Tuning via Django Admin in Sekunden statt Deploy-Zyklen
- **Hub-Konsistenz**: Einheitliche `render_prompt()` API ueber alle Hubs
- **Variablen-Dokumentation**: Schema zeigt sofort welche Variablen erwartet werden
- **Defaults eliminieren Fehler**: Fehlende Variablen nutzen Defaults statt zu crashen
- **Versionierung + Rollback**: Aenderungen nachvollziehbar, Rollback in einem Klick
- **Graceful Fallback**: DB -> File -> Error — bestehende `.jinja2`-Files bleiben als Sicherheitsnetz
- **promptfw bleibt Django-frei**: Core-API hat keine Django-Dependency; `contrib.django` ist optional
- **travel-beat-Pattern validiert**: `PromptTemplateSpec` beweist dass typed Variables + Defaults funktionieren

### 9.2 Negative

- **Zusaetzliche DB-Tabelle** (`promptfw_template`) in jedem Hub
- **Django-Migrations** in einem Library-Package — Versionierung muss sorgfaeltig sein
- **Initiale Migration** aller bestehenden Prompts erfordert Aufwand
- **DB als SPOF**: Wenn DB nicht erreichbar → Prompts nicht verfuegbar (mitigiert durch File-Fallback)

### 9.3 Risks + Mitigations

| Risiko | Schwere | Mitigation |
|--------|---------|------------|
| DB nicht erreichbar | MEDIUM | File-Fallback bleibt aktiv; `.jinja2`-Files werden nicht geloescht |
| Prompt-Injection via Admin | HIGH | Jinja2 `SandboxedEnvironment` + Admin-Zugriff nur fuer Admins |
| Migration bricht bestehende Prompts | HIGH | `seed_prompts` ist idempotent (skip existing); `export_prompts` als Backup |
| Django-Migration-Konflikt zwischen Hubs | MEDIUM | Shared Migrations in promptfw-Package; Hubs fuehren nur `migrate promptfw` aus |
| Performance (DB-Lookup pro LLM-Call) | LOW | Cache mit 5min TTL (Django Cache Framework); ~84 Prompts passen in Memory |

---

## 10. What This ADR Does NOT Cover

| Nicht-Scope | Warum | Wo stattdessen |
|-------------|-------|----------------|
| A/B-Testing von Prompts | Feature fuer spaetere Phase; bfagent hatte es, war nie produktiv genutzt | Backlog |
| Multi-Language Prompt-Varianten | Aktuell nur Deutsch; bei Bedarf `language`-Feld auf Model | Spaetere ADR |
| Prompt-Analytics (Usage-Tracking) | Braucht Event-System; aifw `AIUsageLog` trackt bereits Models | aifw |
| Approval-Workflow fuer Prompt-Aenderungen | Overkill fuer aktuelles Team; bei Bedarf Django-Reversion | Spaetere Phase |
| REST-API fuer Prompt-CRUD | Django Admin reicht initial; API wenn Frontend benoetigt | Backlog |

---

## 11. Compatibility with Existing ADRs

| ADR | Beziehung |
|-----|-----------|
| **ADR-083** (promptfw Integration writing-hub) | Wird vervollstaendigt: writing-hub wechselt von File-only auf DB+File |
| **ADR-089** (LiteLLM DB-driven) | Komplementaer: aifw = Model-Routing, promptfw = Prompt-Content |
| **ADR-093** (AI Config App) | `AIActionType` bleibt SSoT fuer LLM-Routing; `PromptTemplate` fuer Prompt-Inhalt |
| **ADR-121** (outlinefw) | outlinefw-Prompts koennten ebenfalls in DB migriert werden |
| **ADR-133** (Shared AI Services) | Ergaenzt: aifw = Shared Service, promptfw = Shared Prompts |
| **promptfw ADR-002** | Erfuellt die dort geplante `DjangoTemplateRegistry`-Integration |
| **promptfw ADR-003** | Liefert den dort skizzierten `contrib/django.py`-Extension-Path |

---

## 12. Implementation Evidence (nach Umsetzung auszufuellen)

- [ ] `promptfw.contrib.django` Package in promptfw Repo angelegt
- [ ] PromptTemplate Model mit Migrations
- [ ] Admin CRUD funktional
- [ ] `render_prompt()` Resolution: DB -> File -> Error
- [ ] `seed_prompts` Command
- [ ] `export_prompts` Command
- [ ] >=20 Tests in `test_contrib_django.py`
- [ ] promptfw v0.8.0 auf PyPI publiziert
- [ ] writing-hub: 46 Prompts in DB migriert
- [ ] travel-beat: 5 Registry-Prompts in DB migriert
- [ ] research-hub: 3 Inline-Prompts extrahiert und in DB
- [ ] Alle 3 Hubs: `render_prompt()` als einheitliche API
