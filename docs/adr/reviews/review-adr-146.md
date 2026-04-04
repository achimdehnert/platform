# Review: ADR-146 — Hub-übergreifendes DB-Prompt-Management (promptfw.contrib.django)

**Reviewer:** Claude (Senior IT Architect / Python Dev Review)  
**Datum:** 2026-04-04  
**ADR-Version:** Proposed  
**Gesamtbewertung:** ⛔ REJECT — 5 BLOCKERs, 6 KRITISCHe Punkte vor Acceptance zu beheben

---

## Gesamtbild

Das ADR ist **architektonisch solide und gut motiviert**. Die Problemanalyse (4 Patterns, 84 Prompts, 0 Konsistenz) ist präzise, die Entscheidung für Option A (`promptfw.contrib.django`) korrekt begründet, und der Migrations-Plan ist realistisch. **Die Richtung stimmt vollständig.**

Jedoch enthält das ADR **5 Platform-Standard-Verletzungen auf BLOCKER-Niveau** und mehrere sicherheits- und architekturrrelevante Lücken, die vor Implementierung behoben werden müssen.

---

## BLOCKER — Muss vor Umsetzung behoben werden

### BLOCKER-1 · `unique_together` statt `UniqueConstraint` (Platform-Standard-Verletzung)

**Fundstelle:** `models.py`, Zeile `unique_together = [("action_code", "version")]`

Platform-Standard ist explizit: `UniqueConstraint` mit `condition` — kein `unique_together`.  
Und hier ist `UniqueConstraint` mit Condition sogar die **architektonisch überlegene Lösung**, weil die Versioning-Invariante (maximal ein `is_active=True` pro `action_code`) über einen **partiellen Index** korrekt erzwungen wird:

```python
# ✅ KORREKT — ersetzt BEIDE Constraints:
class Meta:
    constraints = [
        # Verhindert doppelte Versions-Nummern
        models.UniqueConstraint(
            fields=["action_code", "version"],
            name="promptfw_template_action_version_uniq",
        ),
        # Erzwingt max. ein is_active=True pro action_code — DB-Level, nicht save()
        models.UniqueConstraint(
            fields=["action_code"],
            condition=models.Q(is_active=True),
            name="promptfw_template_action_active_uniq",
        ),
    ]
```

---

### BLOCKER-2 · Fehlende Platform-Standard-Felder auf dem Model

**Fundstelle:** `models.py` — `PromptTemplate` Model

Folgende Non-Negotiable-Felder fehlen vollständig:

| Feld | Platform-Standard | Impact |
|------|------------------|--------|
| `public_id` | `UUIDField(default=uuid.uuid4, editable=False, unique=True)` | Externe API-Referenz, DSGVO-safe |
| `tenant_id` | `BigIntegerField(null=True, blank=True, db_index=True)` | Multi-Tenancy (tax-hub SaaS!) |
| `deleted_at` | `DateTimeField(null=True, blank=True)` | Soft-Delete statt Hard-Delete |

```python
# ✅ Pflicht-Felder ergänzen:
import uuid
from django.db import models

class PromptTemplate(models.Model):
    id = models.BigAutoField(primary_key=True)  # explizit wenn DEFAULT_AUTO_FIELD nicht gesetzt
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    tenant_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # ... rest of fields
```

**Besonders kritisch:** Ohne `tenant_id` können Hubs wie tax-hub (Multi-Tenant SaaS) keine tenant-isolierten Prompts haben. Prompt-Leakage zwischen Tenants wäre eine DSGVO-Verletzung.

---

### BLOCKER-3 · Versioning-Invariante über `save()` Override ist unsicher

**Fundstelle:** Kapitel 8, "Invariante: Erzwungen via `save()` Override oder DB Trigger"

`save()` Override wird bei `QuerySet.update()`, `bulk_update()` und direkten DB-Zugriffen **nicht aufgerufen**. Das Fallback "oder DB Trigger" ist vage.

**Lösung:** Der partielle `UniqueConstraint` aus BLOCKER-1 löst dieses Problem vollständig auf DB-Ebene — ohne `save()` Override, ohne Trigger. Zusätzlich braucht der Admin eine explizite **"Neue Version erstellen"** Action (siehe KRITISCH-5).

---

### BLOCKER-4 · `SandboxedEnvironment` nicht implementiert (Security Gap)

**Fundstelle:** `resolution.py` — `_render_db_template()`

Das Risk-Register (Abschnitt 9.3) nennt **Jinja2 `SandboxedEnvironment`** als Mitigation gegen Prompt-Injection via Admin. Der Implementations-Code nutzt aber `Jinja2Template(tpl.system_template, undefined=StrictUndefined)` — **kein** `SandboxedEnvironment`.

Admin-Nutzer könnten Jinja2-Expressions wie `{{ ''.__class__.__mro__[1].__subclasses__() }}` einschleusen und Python-Introspection ausführen.

```python
# ❌ AKTUELL — unsicher:
from jinja2 import Template as Jinja2Template, StrictUndefined
Jinja2Template(tpl.system_template, undefined=StrictUndefined).render(**context)

# ✅ KORREKT — SandboxedEnvironment:
from jinja2.sandbox import SandboxedEnvironment
_JINJA_ENV = SandboxedEnvironment(undefined=StrictUndefined)

def _render_db_template(tpl, context: dict) -> list[dict[str, str]]:
    messages = []
    if tpl.system_template:
        sys_rendered = _JINJA_ENV.from_string(tpl.system_template).render(**context).strip()
        if sys_rendered:
            messages.append({"role": "system", "content": sys_rendered})
    user_rendered = _JINJA_ENV.from_string(tpl.user_template).render(**context).strip()
    messages.append({"role": "user", "content": user_rendered})
    return messages
```

---

### BLOCKER-5 · Cache-Implementierung fehlt, aber als Mitigation deklariert

**Fundstelle:** Risk-Register (9.3): "Cache mit 5min TTL (Django Cache Framework)" als Mitigation für Performance-Risiko  
**Fundstelle:** `resolution.py` — `render_prompt()` / `_load_from_db()`

Jeder LLM-Call triggert einen DB-Lookup. Bei writing-hub mit 46 Prompts und parallelen Celery-Tasks ist das ein ungepuffertes N+1-Pattern. Das ADR nennt Caching als Mitigation, aber der Code implementiert es nicht. Das macht die Risk-Mitigation zum leeren Versprechen.

```python
# ✅ Cache-Layer in _load_from_db():
from django.core.cache import cache

_CACHE_TTL = 300  # 5 Minuten, via settings.PROMPTFW_CACHE_TTL überschreibbar

def _load_from_db(action_code: str):
    cache_key = f"promptfw:template:{action_code}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    from promptfw.contrib.django.models import PromptTemplate
    tpl = PromptTemplate.objects.filter(
        action_code=action_code, is_active=True, deleted_at__isnull=True
    ).order_by("-version").first()
    cache.set(cache_key, tpl, timeout=_CACHE_TTL)
    return tpl
```

**Dazu zwingend:** Cache-Invalidierung im Admin-`save_model()`:
```python
def save_model(self, request, obj, form, change):
    if not change:
        obj.created_by = request.user
    super().save_model(request, obj, form, change)
    cache.delete(f"promptfw:template:{obj.action_code}")  # Invalidate on save
```

---

## KRITISCH — Vor Go-Live zu beheben

### KRITISCH-1 · Keine Pydantic v2 Validierung für JSONFields

**Fundstelle:** `variables_schema` und `defaults` JSONFields

Platform-Standard: Pydantic v2 für Schema-Validierung. Das ADR definiert das JSON-Schema-Format in Kapitel 7 exzellent, aber es gibt weder Pydantic-Modelle noch Validierung bei `clean()` oder in `render_prompt()`.

```python
# ✅ Pydantic v2 Schema-Modelle:
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

# In models.py — clean():
def clean(self):
    from pydantic import ValidationError
    if self.variables_schema:
        try:
            PromptVariablesSchema(variables=self.variables_schema)
        except ValidationError as e:
            raise ValidationError({"variables_schema": str(e)})
```

---

### KRITISCH-2 · `suggested_temperature` ohne Validator

**Fundstelle:** `models.py`, `suggested_temperature = models.FloatField(...)`

Der help_text sagt "0.0-2.0", aber es gibt keine DB- oder Model-Validierung. Admin-Nutzer könnten `-1.5` oder `99.0` eingeben.

```python
# ✅ Korrekt:
from django.core.validators import MinValueValidator, MaxValueValidator

suggested_temperature = models.FloatField(
    null=True, blank=True,
    validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
    help_text="Empfohlene Temperature (0.0-2.0)."
)
```

---

### KRITISCH-3 · i18n fehlt komplett (Platform-Standard)

**Fundstelle:** `models.py`, `admin.py` — alle `verbose_name`, `help_text`, Fieldset-Titel

Platform-Standard: i18n from day one. Kein einziges Feld nutzt `gettext_lazy`.

```python
# ✅ Standard-Pattern:
from django.utils.translation import gettext_lazy as _

action_code = models.CharField(
    max_length=200,
    db_index=True,
    verbose_name=_("action code"),
    help_text=_('Unique prompt identifier. Convention: "{hub}.{domain}.{action}"'),
)
```

---

### KRITISCH-4 · Admin hat keine "Neue Version erstellen" Aktion

**Fundstelle:** `admin.py` — Kapitel 8 beschreibt den Versioning-Workflow, Admin-Code implementiert ihn nicht

Ohne diese Action ist der Versioning-Flow broken: Der Admin müsste manuell die `version`-Nummer erhöhen und das alte Objekt deaktivieren — fehleranfällig und nicht atomar.

```python
# ✅ Admin-Action für atomares Versionieren:
@admin.action(description=_("Neue Version erstellen"))
def create_new_version(self, request, queryset):
    from django.db import transaction
    for tpl in queryset.filter(is_active=True):
        with transaction.atomic():
            new_version = tpl.version + 1
            # Altes deaktivieren
            tpl.is_active = False
            tpl.save(update_fields=["is_active"])
            # Neue Version anlegen
            tpl.pk = None
            tpl.public_id = uuid.uuid4()
            tpl.version = new_version
            tpl.is_active = True
            tpl.created_by = request.user
            tpl.deleted_at = None
            tpl.save()
    self.message_user(request, f"{queryset.count()} neue Version(en) erstellt.")

actions = [create_new_version]
```

---

### KRITISCH-5 · `SeparateDatabaseAndState` Migration nicht adressiert

**Fundstelle:** Phase 1, Task 1.2: `migrations/0001_initial.py` — keine Erwähnung von `SeparateDatabaseAndState`

Platform-Standard ist explizit. Die initiale Migration eines Library-Packages das über mehrere Hubs deployed wird, ist ein klassischer Anwendungsfall für `SeparateDatabaseAndState` — insbesondere wenn Hubs die Tabelle bereits in einer Vorgänger-Form haben könnten (bfagent-Legacy).

---

### KRITISCH-6 · `_PROMPTS_DIR` als globales Modul-State (Thread-Unsafe)

**Fundstelle:** `resolution.py` — `_PROMPTS_DIR = None` + `configure()`

Globaler mutabler State ist in ASGI/Async-Kontexten (Gunicorn gthread) fehleranfällig und macht Unit-Tests fragil (State-Leakage zwischen Tests).

```python
# ✅ Besser: Django-Setting mit Fallback
from django.conf import settings

def _get_prompts_dir():
    return getattr(settings, "PROMPTFW_PROMPTS_DIR", None)
```

Das `configure()`-Interface kann als Alias für Rückwärtskompatibilität bleiben, aber die primäre Quelle sollte settings sein.

---

## HOCH — Sollte vor Release behoben werden

### HOCH-1 · SSoT-Widerspruch im Decision-Driver vs. Resolution-API

**Fundstelle:** Decision Driver #8: "SSoT: Ein Prompt, eine Quelle der Wahrheit. Nicht gleichzeitig in DB und File."  
**Widerspruch:** `render_prompt()` erlaubt genau das — transparenter Fallback DB → File.

Das ist kein Fehler im Code, aber ein **konzeptueller Widerspruch im ADR**. Entweder:
- **Option a)** Decision Driver #8 umformulieren zu "SSoT im Betrieb; File bleibt Read-Only-Fallback während Migration"
- **Option b)** Nach Phase 4 (alle Prompts migriert) den File-Fallback per `PROMPTFW_FILE_FALLBACK=False` deaktivierbar machen

Empfehlung: Option a) mit explizitem Migrations-Gate nach Phase 4.

---

### HOCH-2 · `action_code` Convention nicht enforced

**Fundstelle:** `models.py` — `action_code` CharField ohne Validator

Convention `{hub}.{domain}.{action}` ist dokumentiert aber nicht validiert.

```python
from django.core.validators import RegexValidator

action_code = models.CharField(
    max_length=100,  # 200 ist überdimensioniert für "writing-hub.authoring.chapter_write"
    validators=[RegexValidator(
        regex=r'^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*){1,3}$',
        message='Format: "{hub}.{domain}.{action}" — nur Kleinbuchstaben, Ziffern, Bindestriche'
    )],
    ...
)
```

---

### HOCH-3 · `hub` als freies CharField (Tippfehler-anfällig)

**Fundstelle:** `models.py` — `hub = models.CharField(max_length=50, blank=True)`

Ohne Choices-Enum führt `"writing hub"` (Leerzeichen), `"writinghub"` (ohne Bindestrich) oder `"Writing-Hub"` (Großschreibung) zu kaputten Filter-Queries.

```python
# ✅ TextChoices Enum:
class HubChoices(models.TextChoices):
    WRITING = "writing-hub", "Writing Hub"
    TRAVEL_BEAT = "travel-beat", "Travel Beat / DriftTales"
    RESEARCH = "research-hub", "Research Hub"
    CAD = "cad-hub", "CAD Hub"
    RISK = "risk-hub", "Risk Hub"
    COACH = "coach-hub", "Coach Hub"
    OTHER = "other", "Other / Platform-wide"

hub = models.CharField(
    max_length=50, blank=True, db_index=True,
    choices=HubChoices.choices,
)
```

---

### HOCH-4 · `seed_prompts --from-registry` Design ist fragil

**Fundstelle:** Phase 3, Task 3.2: `seed_prompts --from-registry travel-beat`

`InMemoryRegistry` in travel-beat ist ein Laufzeit-Objekt, das bei App-Import registriert wird. Ein Management Command müsste travel-beat's Django-App importieren und die Registry-Initialisierung triggern. Das ist implizit und fragil — bricht bei Refactoring der Registry-Initialisierung.

**Empfehlung:** Statt `--from-registry` einen statischen `prompts.yaml`-Export je Hub als Seedquelle nutzen. Registry → YAML (einmalig manuell), YAML → DB (via `seed_prompts`). Explizit und versionierbar.

---

### HOCH-5 · `validate_prompts` Command in Phase 1 Tasks nicht gelistet

**Fundstelle:** Phase 1 Task-Liste endet bei 1.9 — `validate_prompts` fehlt  
**Fundstelle:** CLI-Design Abschnitt 5.4 listet es als vierten Command

Phase 1 ist unvollständig. `validate_prompts` gehört in Phase 1 (Task 1.6) oder muss als separater Task ergänzt werden. Es ist die CI-Gate-Grundlage für Phase 4.3.

---

## MEDIUM — Vor nächstem Release zu adressieren

### MEDIUM-1 · `response_format` als Tuple-Choices statt `TextChoices`

```python
# ✅ Besser:
class ResponseFormat(models.TextChoices):
    TEXT = "text", _("Text")
    JSON_OBJECT = "json_object", _("JSON Object")
    JSON_SCHEMA = "json_schema", _("JSON Schema")

response_format = models.CharField(max_length=20, blank=True, choices=ResponseFormat.choices)
```

---

### MEDIUM-2 · Kein `__all__` Export in `promptfw.contrib.django`

Platform-Standard (analog zu `iil-testkit`): Alle öffentlichen Symbole in `__all__` in `__init__.py` deklarieren.

```python
# promptfw/contrib/django/__init__.py
__all__ = ["PromptTemplate", "render_prompt", "configure"]
```

---

### MEDIUM-3 · `created_by` ForeignKey erzeugt Migrations-Abhängigkeit

`ForeignKey(settings.AUTH_USER_MODEL)` erzeugt eine Migration-Dependency auf den Auth-User des jeweiligen Hubs. Bei `SeparateDatabaseAndState` und library-owned Migrations kann das zu Konflikten führen. Alternativ: `GenericForeignKey` oder nur Username als CharField speichern.

---

### MEDIUM-4 · Kein `validate_prompts` in ADR-076 CI-Strategie verankert

Das ADR erwähnt `validate_prompts` in CI (Phase 4.3), aber es fehlt eine explizite Referenz zu ADR-076 und wie der Command in die bestehende CI-Pipeline integriert wird (pre-deploy step, separate job, etc.).

---

### MEDIUM-5 · `PromptNotFoundError` / `TemplateNotFoundError` Inkonsistenz

**Fundstelle:** `resolution.py` importiert `TemplateNotFoundError` aus `promptfw.exceptions`  
**Fundstelle:** Kapitel 5.1 Docstring nennt `PromptNotFoundError`

Welche Exception ist korrekt? Das muss vereinheitlicht werden. Empfehlung: `PromptNotFoundError` als sprechendere Exception, ggf. als Subclass von `TemplateNotFoundError`.

---

## Zusammenfassung

| Severity | Anzahl | Status |
|----------|--------|--------|
| BLOCKER | 5 | ⛔ Alle beheben vor Umsetzung |
| KRITISCH | 6 | 🔴 Alle beheben vor Go-Live |
| HOCH | 5 | 🟠 Vor Phase-1-Release |
| MEDIUM | 5 | 🟡 Vor nächstem Release |

### Korrektur-Priorität

1. **Model überarbeiten** (BLOCKER-1+2, KRITISCH-1+2+3): Platform-Standard-Felder, `UniqueConstraint`, Pydantic-Validation, i18n, Validators
2. **Resolution-API absichern** (BLOCKER-4+5, KRITISCH-6): `SandboxedEnvironment`, Cache-Layer, Django-Settings statt globaler State
3. **Admin vervollständigen** (BLOCKER-3+5, KRITISCH-4): "Neue Version" Action + Cache-Invalidierung im `save_model`
4. **ADR-Text korrigieren** (HOCH-1+5, KRITISCH-5): SSoT-Widerspruch, `validate_prompts` in Phase 1, `SeparateDatabaseAndState`

### Was gut ist (kein Änderungsbedarf)

- ✅ Architektur-Entscheidung Option A: korrekt und gut begründet
- ✅ 3-Tier Resolution (DB → File → Error): solides Pattern
- ✅ Variable-Schema-Design (Kapitel 7): vollständig und praxistauglich  
- ✅ Abgrenzung promptfw vs. aifw (Kapitel 5.5): klar und konsistent
- ✅ Kompatibilitäts-Tabelle ADR-083/089/093/121/133: vollständig
- ✅ Migrations-Plan Phasen 1-4: realistisch und geordnet
- ✅ "What This ADR Does NOT Cover" (Kapitel 10): Scope-Abgrenzung präzise
