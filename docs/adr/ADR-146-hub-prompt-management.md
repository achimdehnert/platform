---
status: accepted
date: 2026-04-04
decision-makers: Achim Dehnert
implementation_status: not_started
implementation_evidence: []
tags: [promptfw, prompt-management, cross-hub, database, django, CRUD]
related: [ADR-083, ADR-089, ADR-093, ADR-121, ADR-133]
review: reviews/review-adr-146.md
review_status: accepted
---

# ADR-146: Hub-übergreifendes DB-Prompt-Management — promptfw als SSoT für editierbare Prompts

| Metadata | Value |
|----------|-------|
| **Status** | **Accepted** (2026-04-04) |
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
8. **SSoT im Betrieb**: DB ist die primaere Quelle der Wahrheit. File-basierte Templates dienen als Read-Only-Fallback waehrend der Migration und koennen nach Phase 4 via `PROMPTFW_FILE_FALLBACK=False` deaktiviert werden.

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

import uuid

from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


# --- Pydantic v2 Schemas fuer JSONField-Validierung (KRITISCH-1) ---
from pydantic import BaseModel, Field
from typing import Any


class PromptVariableSchema(BaseModel):
    type: str
    required: bool = False
    default: Any = None
    description: str = ""
    enum: list[str] | None = None
    min: int | None = None
    max: int | None = None


class PromptVariablesSchema(BaseModel):
    variables: dict[str, PromptVariableSchema] = Field(default_factory=dict)


# --- Enums (HOCH-3, MEDIUM-1) ---

class HubChoices(models.TextChoices):
    WRITING = "writing-hub", _("Writing Hub")
    TRAVEL_BEAT = "travel-beat", _("Travel Beat / DriftTales")
    RESEARCH = "research-hub", _("Research Hub")
    CAD = "cad-hub", _("CAD Hub")
    RISK = "risk-hub", _("Risk Hub")
    COACH = "coach-hub", _("Coach Hub")
    OTHER = "other", _("Other / Platform-wide")


class ResponseFormat(models.TextChoices):
    TEXT = "text", _("Text")
    JSON_OBJECT = "json_object", _("JSON Object")
    JSON_SCHEMA = "json_schema", _("JSON Schema")


# --- action_code Convention Validator (HOCH-2) ---
action_code_validator = RegexValidator(
    regex=r'^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*){1,3}$',
    message=_('Format: "{hub}.{domain}.{action}" — nur Kleinbuchstaben, Ziffern, Bindestriche'),
)


class PromptTemplate(models.Model):
    """DB-managed prompt template with CRUD, versioning, defaults, and variable schema.

    Resolution order (via PromptResolver):
      1. DB: PromptTemplate.objects.filter(action_code=X, is_active=True)
      2. File: settings.PROMPTFW_PROMPTS_DIR / f"{action_code}.jinja2"
      3. Error: PromptNotFoundError
    """

    # === Platform-Standard-Felder (BLOCKER-2) ===
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True,
        verbose_name=_("public ID"),
    )
    # tenant_id ist ab Phase 1 als Feld vorhanden, wird aber erst bei Bedarf
    # (tax-hub SaaS) aktiv genutzt. Resolution + Cache ignorieren tenant_id
    # solange PROMPTFW_MULTI_TENANT=False (default). Siehe Abschnitt 5.7.
    tenant_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("tenant ID"),
        help_text=_("Multi-Tenancy Isolation (null = platform-wide). "
                    "Erst aktiv wenn settings.PROMPTFW_MULTI_TENANT=True."),
    )

    # === Identity ===
    action_code = models.CharField(
        max_length=100, db_index=True,
        validators=[action_code_validator],
        verbose_name=_("action code"),
        help_text=_('Unique prompt identifier. Convention: "{hub}.{domain}.{action}" '
                    'e.g. "travel-beat.story.chapter", "writing-hub.authoring.chapter-write"'),
    )
    version = models.PositiveIntegerField(
        default=1,
        verbose_name=_("version"),
    )

    # === Content (Jinja2 Templates) ===
    system_template = models.TextField(
        blank=True,
        verbose_name=_("system template"),
        help_text=_("System-Prompt (Jinja2). Variablen: {{ var_name }}. "
                    "Leer = kein System-Prompt."),
    )
    user_template = models.TextField(
        verbose_name=_("user template"),
        help_text=_("User-Prompt (Jinja2). Variablen: {{ var_name }}. Pflichtfeld."),
    )

    # === Parametrisierung ===
    defaults = models.JSONField(
        default=dict, blank=True,
        verbose_name=_("defaults"),
        help_text=_("Default-Werte wenn Caller keine uebergibt."),
    )
    variables_schema = models.JSONField(
        default=dict, blank=True,
        verbose_name=_("variables schema"),
        help_text=_("Variablen-Schema (Pydantic-validiert). "
                    'z.B. {"genre": {"type": "string", "required": true}}'),
    )

    # === LLM Hints (optional — aifw bleibt Routing-SSoT) ===
    suggested_max_tokens = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name=_("suggested max tokens"),
        help_text=_("Empfohlene max_tokens. Wird als llm_overrides an aifw uebergeben."),
    )
    suggested_temperature = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        verbose_name=_("suggested temperature"),
        help_text=_("Empfohlene Temperature (0.0-2.0)."),
    )
    response_format = models.CharField(
        max_length=20, blank=True,
        choices=ResponseFormat.choices,
        verbose_name=_("response format"),
        help_text=_("Erwartetes Antwortformat."),
    )
    output_schema = models.JSONField(
        default=dict, blank=True,
        verbose_name=_("output schema"),
        help_text=_("JSON Schema wenn response_format=json_schema."),
    )

    # === Metadata ===
    name = models.CharField(
        max_length=200, blank=True,
        verbose_name=_("name"),
        help_text=_("Menschenlesbarer Name"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
        help_text=_("Was tut dieser Prompt?"),
    )
    hub = models.CharField(
        max_length=50, blank=True, db_index=True,
        choices=HubChoices.choices,
        verbose_name=_("hub"),
    )
    domain = models.CharField(
        max_length=50, blank=True, db_index=True,
        verbose_name=_("domain"),
        help_text=_("Domain: story, authoring, research, worlds"),
    )
    tags = models.JSONField(
        default=list, blank=True,
        verbose_name=_("tags"),
    )

    # === Lifecycle ===
    is_active = models.BooleanField(
        default=True, db_index=True,
        verbose_name=_("is active"),
    )
    deleted_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        verbose_name=_("deleted at"),
        help_text=_("Soft-Delete Timestamp (null = nicht geloescht)"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("notes"),
        help_text=_("Interne Notizen / Aenderungsgrund"),
    )

    # MEDIUM-3: CharField statt ForeignKey — vermeidet Migrations-Abhaengigkeit auf AUTH_USER_MODEL
    created_by = models.CharField(
        max_length=150, blank=True,
        verbose_name=_("created by"),
        help_text=_("Username des Erstellers"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "promptfw"
        db_table = "promptfw_template"
        ordering = ["action_code", "-version"]
        verbose_name = _("prompt template")
        verbose_name_plural = _("prompt templates")
        # BLOCKER-1: UniqueConstraint statt unique_together
        constraints = [
            models.UniqueConstraint(
                fields=["action_code", "version"],
                name="promptfw_template_action_version_uniq",
            ),
            # BLOCKER-3: Erzwingt max. 1 is_active=True pro action_code auf DB-Ebene
            # Bei Multi-Tenancy (PROMPTFW_MULTI_TENANT=True) muss dieser Constraint
            # via Migration auf (action_code, tenant_id) erweitert werden.
            models.UniqueConstraint(
                fields=["action_code"],
                condition=models.Q(is_active=True),
                name="promptfw_template_action_active_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["hub", "is_active"]),
            models.Index(fields=["domain", "is_active"]),
            models.Index(fields=["action_code", "is_active", "-version"]),
            models.Index(fields=["tenant_id", "is_active"]),
        ]

    def __str__(self):
        return f"{self.action_code} v{self.version} ({'active' if self.is_active else 'inactive'})"

    def clean(self):
        """Pydantic v2 Validierung fuer JSONFields (KRITISCH-1)."""
        from pydantic import ValidationError as PydanticValidationError
        from django.core.exceptions import ValidationError
        if self.variables_schema:
            try:
                PromptVariablesSchema(variables=self.variables_schema)
            except PydanticValidationError as e:
                raise ValidationError({"variables_schema": str(e)})
        # Cross-Validierung: defaults-Keys muessen im Schema existieren
        if self.variables_schema and self.defaults:
            unknown = set(self.defaults.keys()) - set(self.variables_schema.keys())
            if unknown:
                raise ValidationError(
                    {"defaults": f"Keys nicht im variables_schema: {unknown}"}
                )
```

### 5.2 Resolution API: `render_prompt()`

```python
# promptfw/src/promptfw/contrib/django/resolution.py

from __future__ import annotations
import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)

# BLOCKER-4: SandboxedEnvironment verhindert Jinja2-Introspection-Angriffe
_JINJA_ENV = SandboxedEnvironment(undefined=StrictUndefined)

# BLOCKER-5: Cache-TTL (ueberschreibbar via settings.PROMPTFW_CACHE_TTL)
_CACHE_TTL = 300  # 5 Minuten


class PromptNotFoundError(Exception):
    """Raised when no prompt template found for action_code."""


class PromptValidationError(Exception):
    """Raised when required variables are missing or invalid."""


def _get_prompts_dir():
    """KRITISCH-6: Django-Setting statt globaler mutabler State."""
    return getattr(settings, "PROMPTFW_PROMPTS_DIR", None)


def _get_cache_ttl():
    return getattr(settings, "PROMPTFW_CACHE_TTL", _CACHE_TTL)


def _get_file_fallback_enabled():
    """HOCH-1: Deaktivierbar nach Abschluss aller Migrationen."""
    return getattr(settings, "PROMPTFW_FILE_FALLBACK", True)


def _is_multi_tenant():
    return getattr(settings, "PROMPTFW_MULTI_TENANT", False)


def render_prompt(action_code: str, *, tenant_id: int | None = None, **context: Any) -> list[dict[str, str]]:
    """
    Unified prompt resolution — single API for all hubs.

    Resolution order:
      1. DB: PromptTemplate(action_code=X, is_active=True, latest version)
      2. File: settings.PROMPTFW_PROMPTS_DIR / f"{action_code}.jinja2" (if enabled)
      3. Error: PromptNotFoundError

    Variable merging: defaults (from DB) | context (from caller) — caller wins.
    Schema validation: required variables checked if variables_schema is defined.

    Args:
        action_code: Prompt identifier (e.g. "writing-hub.authoring.chapter-write")
        tenant_id: Optional tenant isolation (only when PROMPTFW_MULTI_TENANT=True)
        **context: Variables to render into the template

    Returns:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    # 1. DB lookup (cached, tenant-aware wenn aktiviert)
    tpl = _load_from_db(action_code, tenant_id=tenant_id)
    if tpl:
        merged = {**tpl.defaults, **context}
        _validate_context(tpl, merged)
        return _render_db_template(tpl, merged)

    # 2. File fallback (deaktivierbar via settings.PROMPTFW_FILE_FALLBACK=False)
    prompts_dir = _get_prompts_dir()
    if prompts_dir and _get_file_fallback_enabled():
        messages = _render_from_file(action_code, context, prompts_dir)
        if messages:
            return messages

    # 3. Error
    raise PromptNotFoundError(
        f"No prompt template found for action_code='{action_code}'. "
        f"Neither in DB (promptfw_template) nor in files ({prompts_dir})."
    )


def _validate_context(tpl, merged: dict) -> None:
    """Validate merged context against variables_schema (if defined)."""
    if not tpl.variables_schema:
        return
    for var_name, spec in tpl.variables_schema.items():
        if spec.get("required") and var_name not in merged:
            raise PromptValidationError(
                f"Required variable '{var_name}' missing for "
                f"action_code='{tpl.action_code}'. "
                f"Expected variables: {list(tpl.variables_schema.keys())}"
            )


def _load_from_db(action_code: str, *, tenant_id: int | None = None):
    """Load active template from DB (latest version) with cache.

    Cache-Key ist tenant-aware wenn PROMPTFW_MULTI_TENANT=True.
    """
    suffix = f":{tenant_id}" if _is_multi_tenant() and tenant_id else ""
    cache_key = f"promptfw:template:{action_code}{suffix}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached if cached != "__NONE__" else None

    from promptfw.contrib.django.models import PromptTemplate
    qs = PromptTemplate.objects.filter(
        action_code=action_code, is_active=True, deleted_at__isnull=True,
    )
    if _is_multi_tenant() and tenant_id is not None:
        qs = qs.filter(models.Q(tenant_id=tenant_id) | models.Q(tenant_id__isnull=True))
    tpl = qs.order_by("-version").first()

    cache.set(cache_key, tpl if tpl else "__NONE__", timeout=_get_cache_ttl())
    return tpl


def _render_db_template(tpl, context: dict) -> list[dict[str, str]]:
    """Render DB template with SandboxedEnvironment (BLOCKER-4)."""
    messages = []
    if tpl.system_template:
        sys_rendered = _JINJA_ENV.from_string(tpl.system_template).render(**context).strip()
        if sys_rendered:
            messages.append({"role": "system", "content": sys_rendered})

    user_rendered = _JINJA_ENV.from_string(tpl.user_template).render(**context).strip()
    messages.append({"role": "user", "content": user_rendered})
    return messages


def _render_from_file(action_code: str, context: dict, prompts_dir: str):
    """Fallback: render from .jinja2 frontmatter file.

    No Silent Degradation: Rendering-Fehler werden NICHT geschluckt.
    Nur 'Datei nicht gefunden' gibt None zurueck (= weiter zu Error).
    """
    from pathlib import Path
    path = Path(prompts_dir) / f"{action_code.replace('.', '/')}.jinja2"
    if not path.exists():
        path = Path(prompts_dir) / f"{action_code}.jinja2"
    if not path.exists():
        return None
    # Datei existiert -> Rendering MUSS funktionieren, sonst Error propagieren
    from promptfw.frontmatter import render_frontmatter_file
    return render_frontmatter_file(str(path), context)
```

**Django-Settings fuer promptfw.contrib.django:**

```python
# config/settings/base.py (pro Hub)
PROMPTFW_PROMPTS_DIR = BASE_DIR / "templates" / "prompts"  # File-Fallback-Verzeichnis
PROMPTFW_CACHE_TTL = 300         # Cache-TTL in Sekunden (default: 5 min)
PROMPTFW_FILE_FALLBACK = True    # False nach Abschluss aller Migrationen
PROMPTFW_MULTI_TENANT = False    # True wenn tenant-isolierte Prompts benoetigt
```

### 5.3 Admin UI

```python
# promptfw/src/promptfw/contrib/django/admin.py

import uuid

from django.contrib import admin
from django.core.cache import cache
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .models import PromptTemplate


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ["action_code", "version", "name", "hub", "domain", "is_active", "updated_at"]
    list_filter = ["hub", "domain", "is_active", "response_format"]
    search_fields = ["action_code", "name", "description", "system_template", "user_template"]
    readonly_fields = ["public_id", "created_at", "updated_at", "created_by"]

    fieldsets = [
        (_("Identity"), {
            "fields": ["action_code", "version", "name", "description", "public_id"]
        }),
        (_("Content"), {
            "fields": ["system_template", "user_template"],
            "description": _("Jinja2-Templates (SandboxedEnvironment). Variablen: {{ var_name }}")
        }),
        (_("Parametrisierung"), {
            "fields": ["defaults", "variables_schema"],
            "classes": ["collapse"]
        }),
        (_("LLM Hints"), {
            "fields": ["suggested_max_tokens", "suggested_temperature",
                       "response_format", "output_schema"],
            "classes": ["collapse"]
        }),
        (_("Metadata"), {
            "fields": ["hub", "domain", "tags", "notes", "is_active", "tenant_id"]
        }),
        (_("Audit"), {
            "fields": ["created_by", "created_at", "updated_at", "deleted_at"]
        }),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user.username
        super().save_model(request, obj, form, change)
        # BLOCKER-5: Cache-Invalidierung bei Save
        cache.delete(f"promptfw:template:{obj.action_code}")

    def delete_model(self, request, obj):
        # Soft-Delete statt Hard-Delete
        from django.utils import timezone
        obj.deleted_at = timezone.now()
        obj.is_active = False
        obj.save(update_fields=["deleted_at", "is_active"])
        cache.delete(f"promptfw:template:{obj.action_code}")

    def delete_queryset(self, request, queryset):
        # Bulk Soft-Delete (Admin "Delete selected" Action)
        from django.utils import timezone
        action_codes = set(queryset.values_list("action_code", flat=True))
        queryset.update(deleted_at=timezone.now(), is_active=False)
        for ac in action_codes:
            cache.delete(f"promptfw:template:{ac}")

    # KRITISCH-4: Atomare "Neue Version erstellen" Admin-Action
    @admin.action(description=_("Neue Version erstellen (Kopie mit inkrementierter Version)"))
    def create_new_version(self, request, queryset):
        count = 0
        for tpl in queryset.filter(is_active=True):
            with transaction.atomic():
                new_version = tpl.version + 1
                # Altes deaktivieren
                tpl.is_active = False
                tpl.save(update_fields=["is_active"])
                # Neue Version als Kopie
                tpl.pk = None
                tpl.public_id = uuid.uuid4()
                tpl.version = new_version
                tpl.is_active = True
                tpl.created_by = request.user.username
                tpl.deleted_at = None
                tpl.save()
                cache.delete(f"promptfw:template:{tpl.action_code}")
                count += 1
        self.message_user(request, _(f"{count} neue Version(en) erstellt."))

    actions = [create_new_version]
```

### 5.4 Migration CLI

```bash
# Import: .jinja2 Files -> DB
python manage.py seed_prompts --from-dir templates/prompts/ --hub writing-hub

# Import: travel-beat — Einmaliger YAML-Export der InMemoryRegistry, dann YAML -> DB
# (HOCH-4: Statisches YAML statt Laufzeit-Registry-Import — explizit + versionierbar)
python manage.py seed_prompts --from-yaml prompts/travel-beat-export.yaml --hub travel-beat

# Export: DB -> YAML (Git-Backup + Seed-Quelle fuer andere Hubs)
python manage.py export_prompts --hub writing-hub --output-dir prompts/ --format yaml

# Validate: Pruefe ob alle action_codes in DB oder Files vorhanden (CI-Gate)
python manage.py validate_prompts
```

**`validate_prompts` Command-Design:**

| Check | Was | Fehler-Level |
|-------|-----|-------------|
| **Schema-Syntax** | Pydantic-Validierung aller `variables_schema` JSONFields | ERROR |
| **Required-Variables** | Fuer jede aktive PromptTemplate: `defaults` deckt alle `required=true` ab | WARNING |
| **Jinja2-Syntax** | System- und User-Templates durch `SandboxedEnvironment.parse()` | ERROR |
| **Orphaned References** | action_codes in Code referenziert aber nicht in DB/File | WARNING |
| **Duplicate Active** | Mehr als 1 `is_active=True` pro `action_code` (sollte durch Constraint verhindert sein) | ERROR |
| **Hub-Konsistenz** | `hub`-Feld gesetzt und valider `HubChoices`-Wert | WARNING |

Exit-Code: `0` wenn keine ERRORs, `1` bei mindestens einem ERROR. WARNINGs werden ausgegeben aber blockieren CI nicht.

### 5.5 Package-Export (`__init__.py`)

```python
# promptfw/src/promptfw/contrib/django/__init__.py
__all__ = [
    "PromptTemplate",
    "render_prompt",
    "PromptNotFoundError",
    "PromptValidationError",
]

from .models import PromptTemplate
from .resolution import PromptNotFoundError, PromptValidationError, render_prompt
```

### 5.6 AppConfig

```python
# promptfw/src/promptfw/contrib/django/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PromptfwConfig(AppConfig):
    name = "promptfw.contrib.django"
    label = "promptfw"
    verbose_name = _("Prompt Framework")
    default_auto_field = "django.db.models.BigAutoField"
```

### 5.7 Multi-Tenancy Strategie

`tenant_id` ist ab Phase 1 als Feld auf dem Model vorhanden, wird aber **nicht aktiv genutzt** bis ein Hub Multi-Tenancy benoetigt (z.B. tax-hub SaaS).

| Aspekt | Phase 1 (default) | Multi-Tenant (spaeter) |
|--------|-------------------|------------------------|
| `settings.PROMPTFW_MULTI_TENANT` | `False` | `True` |
| `tenant_id` Feld | Vorhanden, immer `null` | Gesetzt pro Tenant |
| `render_prompt()` Signatur | `tenant_id` Parameter ignoriert | Filtert nach tenant_id + null (Fallback auf platform-wide) |
| Cache-Key | `promptfw:template:{action_code}` | `promptfw:template:{action_code}:{tenant_id}` |
| UniqueConstraint | `(action_code)` bei `is_active=True` | Muss via Migration auf `(action_code, tenant_id)` erweitert werden |

**Entscheidung:** Feld jetzt anlegen, Logik spaeter aktivieren. Vermeidet Schema-Migration wenn Multi-Tenancy benoetigt wird.

### 5.8 Abgrenzung: promptfw vs. aifw

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

**Invariante:** Fuer ein `action_code` ist maximal ein `PromptTemplate` mit `is_active=True` zulaessig. **Erzwungen via partiellem `UniqueConstraint` auf DB-Ebene** (`promptfw_template_action_active_uniq`) — nicht ueber `save()` Override (der bei `QuerySet.update()` und `bulk_update()` umgangen wird).

Der Admin stellt eine atomare **"Neue Version erstellen"** Action bereit, die in einer `transaction.atomic()` die alte Version deaktiviert und die neue anlegt.

---

## 8. Migration Plan

### Phase 1 — Foundation (promptfw v0.8.0, Aufwand: 1-2 Tage)

| # | Task | Dateien |
|---|------|---------|
| 1.1 | `promptfw/contrib/django/` Package anlegen | `__init__.py`, `apps.py`, `models.py`, `admin.py`, `resolution.py` |
| 1.2 | Model `PromptTemplate` mit Migrations (`SeparateDatabaseAndState` fuer bfagent-Legacy-Kompatibilitaet) | `models.py`, `migrations/0001_initial.py` |
| 1.3 | `render_prompt()` Resolution-API | `resolution.py` |
| 1.4 | Admin CRUD | `admin.py` |
| 1.5 | `seed_prompts` Management Command | `management/commands/seed_prompts.py` |
| 1.6 | `export_prompts` Management Command | `management/commands/export_prompts.py` |
| 1.7 | `validate_prompts` Management Command (CI-Gate) | `management/commands/validate_prompts.py` |
| 1.8 | Tests (>=20) | `tests/test_contrib_django.py` |
| 1.9 | `pyproject.toml`: `promptfw[django]` Extra | `pyproject.toml` |
| 1.10 | promptfw v0.8.0 Release | Tag + PyPI |

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
| 3.2 | 5 registrierte `PromptTemplateSpec` -> YAML-Export -> DB | Einmaliger Export der `InMemoryRegistry` nach `prompts/travel-beat-export.yaml`, dann `seed_prompts --from-yaml` |
| 3.3 | `InMemoryRegistry` -> DB-backed Resolution | `render_template()` nutzt `render_prompt()` |
| 3.4 | ~30 Inline-Prompts schrittweise extrahieren (Strangler Fig) | Pro Service: f-string -> `render_prompt(action_code, **vars)` |
| 3.5 | `StoryFocusConfig.chapter_prompt_addition` -> `PromptTemplate.defaults` oder Composition | Prompt-Additions als Variablen injizieren |

### Phase 4 — research-hub + weitere Hubs (Aufwand: je 0.5 Tag)

| # | Task |
|---|------|
| 4.1 | research-hub: 3 Inline-Prompts -> DB (`research.summarize`, `research.deep_analysis`, `research.fact_check`) |
| 4.2 | cad-hub, risk-hub, coach-hub: bei naechster Feature-Arbeit migrieren |
| 4.3 | `validate_prompts` in CI integrieren (ADR-057 CI-Pipeline, pre-deploy Step) |

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
| Prompt-Injection via Admin | HIGH | Jinja2 `SandboxedEnvironment` (implementiert in `_render_db_template()`) + Admin-Zugriff nur fuer Staff-User |
| Migration bricht bestehende Prompts | HIGH | `seed_prompts` ist idempotent (skip existing); `export_prompts` als Backup |
| Django-Migration-Konflikt zwischen Hubs | MEDIUM | Shared Migrations in promptfw-Package; Hubs fuehren nur `migrate promptfw` aus |
| Performance (DB-Lookup pro LLM-Call) | LOW | Cache mit 5min TTL (implementiert in `_load_from_db()` + Invalidierung in `save_model()`); ~84 Prompts passen in Memory. TTL via `settings.PROMPTFW_CACHE_TTL` konfigurierbar. |

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
- [ ] PromptTemplate Model mit Platform-Standard-Feldern (`public_id`, `tenant_id`, `deleted_at`)
- [ ] `UniqueConstraint` statt `unique_together` (inkl. partieller Index fuer `is_active`)
- [ ] Pydantic v2 Validierung fuer `variables_schema` in `clean()`
- [ ] `SandboxedEnvironment` in Resolution-API
- [ ] Cache-Layer mit Invalidierung im Admin
- [ ] i18n (`gettext_lazy`) auf allen Feldern und Admin-Fieldsets
- [ ] `HubChoices` + `ResponseFormat` TextChoices Enums
- [ ] `action_code` RegexValidator
- [ ] `suggested_temperature` MinValue/MaxValue Validators
- [ ] Admin: "Neue Version erstellen" Action (atomar)
- [ ] Admin: Soft-Delete statt Hard-Delete
- [ ] `SeparateDatabaseAndState` Migration
- [ ] `render_prompt()` Resolution: DB (cached) -> File (settings-basiert) -> PromptNotFoundError
- [ ] `seed_prompts` Command (--from-dir, --from-yaml)
- [ ] `export_prompts` Command (--format yaml)
- [ ] `validate_prompts` Command (CI-Gate)
- [ ] `__all__` Export in `__init__.py`
- [ ] Django-Settings: `PROMPTFW_PROMPTS_DIR`, `PROMPTFW_CACHE_TTL`, `PROMPTFW_FILE_FALLBACK`
- [ ] `PromptValidationError` bei fehlenden required-Variables
- [ ] `validate_prompts` Command: Schema + Jinja2-Syntax + Required-Check
- [ ] `apps.py` `PromptfwConfig` mit `label="promptfw"`
- [ ] Admin `delete_queryset()` fuer Bulk Soft-Delete
- [ ] `PROMPTFW_MULTI_TENANT` Setting + tenant-aware Cache-Key + DB-Filter
- [ ] No Silent Degradation: File-Fallback propagiert Rendering-Fehler
- [ ] `defaults` Cross-Validierung gegen `variables_schema` in `clean()`
- [ ] >=25 Tests in `test_contrib_django.py`
- [ ] promptfw v0.8.0 auf PyPI publiziert
- [ ] writing-hub: 46 Prompts in DB migriert
- [ ] travel-beat: 5 Registry-Prompts via YAML in DB migriert
- [ ] research-hub: 3 Inline-Prompts extrahiert und in DB
- [ ] Alle 3 Hubs: `render_prompt()` als einheitliche API

---

## 13. Review-Tracker

| Finding | Severity | Status | Revision |
|---------|----------|--------|----------|
| BLOCKER-1: `UniqueConstraint` statt `unique_together` | BLOCKER | Fixed | v1 |
| BLOCKER-2: Platform-Standard-Felder (`public_id`, `tenant_id`, `deleted_at`) | BLOCKER | Fixed | v1 |
| BLOCKER-3: Versioning-Invariante via partiellen Index | BLOCKER | Fixed | v1 |
| BLOCKER-4: `SandboxedEnvironment` | BLOCKER | Fixed | v1 |
| BLOCKER-5: Cache-Layer implementiert | BLOCKER | Fixed | v1 |
| KRITISCH-1: Pydantic v2 fuer JSONFields | KRITISCH | Fixed | v1 |
| KRITISCH-2: `suggested_temperature` Validator | KRITISCH | Fixed | v1 |
| KRITISCH-3: i18n (`gettext_lazy`) | KRITISCH | Fixed | v1 |
| KRITISCH-4: Admin "Neue Version" Action | KRITISCH | Fixed | v1 |
| KRITISCH-5: `SeparateDatabaseAndState` erwaehnt | KRITISCH | Fixed | v1 |
| KRITISCH-6: Django-Settings statt `_PROMPTS_DIR` global | KRITISCH | Fixed | v1 |
| HOCH-1: SSoT Decision Driver umformuliert | HOCH | Fixed | v1 |
| HOCH-2: `action_code` RegexValidator | HOCH | Fixed | v1 |
| HOCH-3: `HubChoices` TextChoices Enum | HOCH | Fixed | v1 |
| HOCH-4: `seed_prompts --from-yaml` statt `--from-registry` | HOCH | Fixed | v1 |
| HOCH-5: `validate_prompts` in Phase 1 Tasks | HOCH | Fixed | v1 |
| MEDIUM-1: `ResponseFormat` TextChoices | MEDIUM | Fixed | v1 |
| MEDIUM-2: `__all__` Export | MEDIUM | Fixed | v1 |
| MEDIUM-3: `created_by` als CharField statt FK | MEDIUM | Fixed | v1 |
| MEDIUM-4: CI-Referenz (ADR-057) | MEDIUM | Fixed | v1 |
| MEDIUM-5: `PromptNotFoundError` konsistent | MEDIUM | Fixed | v1 |
| OPT-1: `tenant_id` durchgaengig (Constraint, Cache, Resolution) | HOCH | Fixed | v2 |
| OPT-2: `variables_schema` Render-Validierung + `PromptValidationError` | HOCH | Fixed | v2 |
| OPT-3: Silent Degradation in `_render_from_file()` | MEDIUM | Fixed | v2 |
| OPT-4: Admin `delete_queryset()` Bulk Soft-Delete | MEDIUM | Fixed | v2 |
| OPT-5: `apps.py` `PromptfwConfig` definiert | MEDIUM | Fixed | v2 |
| OPT-6: `validate_prompts` Command-Design dokumentiert | MEDIUM | Fixed | v2 |
