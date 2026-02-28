---
status: proposed
date: 2026-02-28
decision-makers: Achim Dehnert
---

# ADR-094: Shared AI Services als wiederverwendbare Python-Pakete

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-28 |
| **Author** | Achim Dehnert |
| **Related** | ADR-089 (LiteLLM DB-driven), ADR-093 (AI Config App), ADR-091 (Shared Backend Services) |

---

## Context

Vier Projekte der Plattform implementieren AI-gestütztes Schreiben und LLM-Integration:

| Projekt | AI-Nutzung | `ai_services` App | Story/Scene-Modelle |
|---------|-----------|-------------------|---------------------|
| **bfagent** | Writing Hub, Agents, Research | ✅ vollständig | ✅ |
| **travel-beat** | Reise-Geschichten via Claude | ✅ | ✅ |
| **weltenhub** | Story Universe, Szenen, Charaktere | ✅ | ✅ |
| **coach-hub** | KI-gestützte Lernpfade | vermutlich | — |

**Beobachtung:** Alle Projekte haben nahezu identischen Code dreifach kopiert:

- `LLMProvider`, `LLMModel`, `AIActionType`, `AIUsageLog` — **gleiche Django-Models**
- `llm_service.py` (LiteLLM-Wrapper, DB-driven, `completion()` / `sync_completion()`) — **gleiche Logik**
- `LLMResult`, `ToolCall` Dataclasses — **gleiche Schnittstellen**

Parallel dazu existiert in `bfagent/docs/adr/input/` ein ausgearbeitetes Konzept für:
1. **`llm-prompt-stack`** — generische 4-Layer Jinja2-Template-Engine (Django-unabhängig)
2. **`authoring-templates`** — domänenspezifische Schreib-Schemas (FormatProfile, StyleProfile, WorkflowPhase)

### Problem

- Bugfixes und Verbesserungen (z.B. `sync_completion()` Thread-Pool-Fix in bfagent) werden **nicht** in travel-beat und weltenhub übernommen
- Jedes Projekt führt eigene Migrations für identische Tabellen
- `llm_service.py` ist in weltenhub eine ältere, funktionsärmere Version als in bfagent

---

## Decision

**Drei Pakete in drei Phasen extrahieren**, priorisiert nach aktuellem Duplikationsgrad:

### Paket 1 (sofort): `iil-django-ai-services`

Django-App-Paket mit den gemeinsamen AI-Service-Bausteinen.

**Entscheidung: Eigenes Paket in `platform/packages/`**, nicht Teil von `iil_django_commons`.

**Begründung:**
- `iil_django_commons` ist framework-utility (Cache, Health, Ratelimit, Logging) — kein LLM-Business-Logic
- `iil-django-ai-services` hat eigene Django-Migrations → separates Versionierungsbedürfnis
- Unabhängig deploybar: Projekte ohne LLM-Bedarf (wedding-hub) müssen die Dep nicht ziehen

**Scope:**
```
iil_django_commons/               ← unverändert (Cache, Health, Ratelimit, ...)
packages/iil-django-ai-services/
  src/iil_ai_services/
    __init__.py
    apps.py
    models.py          # LLMProvider, LLMModel, AIActionType, AIUsageLog
    service.py         # completion(), sync_completion(), completion_with_fallback()
    schema.py          # LLMResult, ToolCall
    admin.py
    migrations/
```

### Paket 2 (Phase 2): `llm-prompt-stack`

Django-unabhängige 4-Layer Template-Engine.

**Lebt in: `bfagent/packages/llm-prompt-stack/`** (kein Django-Bezug → nicht in platform).

```
packages/llm-prompt-stack/
  src/prompt_stack/
    schema.py          # PromptTemplate, RenderedPrompt, TemplateLayer
    registry.py        # TemplateRegistry (Wildcard-Lookup)
    renderer.py        # PromptRenderer (Jinja2, StrictUndefined)
    router.py          # LLMRouter (multi-provider)
    budget.py          # TokenBudgetManager
    logging.py         # PromptLogEntry
    providers/         # anthropic.py, openai.py, local.py
```

### Paket 3 (Phase 3): `authoring-templates`

Domänenspezifische Schemas für Schreib-Applikationen.

**Validierungsbedingung:** Erst extrahieren, wenn mindestens 2 Projekte dieselben Schemas aktiv nutzen.

**Kandidaten für gemeinsame Schemas** (nach Analyse):
```
authoring_templates/
  formats/             # FormatProfile (Roman, Essay, Serie, Scientific)
  schema/
    style.py           # StyleProfile
    character.py       # CharacterProfile (weltenhub + bfagent + travel-beat)
    world.py           # WorldContext
    versioning.py      # VersionMetadata, PhaseSnapshot
  adapters/
    interfaces.py      # IStyleAdapter, IWorldAdapter (Protocol)
  templates/           # YAML-Bibliothek (Jinja2)
```

---

## Dependency-Graph

```
iil-django-ai-services     (Django, LiteLLM, DB-driven)
        │
        └── llm-prompt-stack  (pure Python, Jinja2, kein Django)
                │
                └── authoring-templates  (domänenspezifisch)
                        │
                        └── bfagent / travel-beat / weltenhub  (Apps)
```

**Regel:** Abhängigkeiten gehen nur nach oben. `iil-django-ai-services` kennt `llm-prompt-stack` **nicht** (andere Abstraktionsebene).

---

## Consequences

### Positiv

- **Ein Bugfix gilt für alle Projekte** — `sync_completion()` Thread-Pool-Verbesserung sofort in allen Projekten
- **Einheitliche Migrations** — `LLMProvider`, `LLMModel` etc. laufen in allen Projekten identisch
- **Klare API-Grenze** — `LLMResult`, `ToolCall`, `completion()` als stabile Schnittstelle
- **Passt zur bestehenden Infrastruktur** — `iil_django_commons` zeigt, dass dieses Pattern funktioniert

### Negativ / Risiken

- **Migration bestehender Projekte** — travel-beat und weltenhub müssen `ai_services` App durch `iil_ai_services` ersetzen (Breaking Change in Migrations)
- **Abhängigkeits-Overhead** — drei separate Versionierungszyklen

### Migration-Strategie

1. `iil-django-ai-services` in platform als neues Paket anlegen
2. bfagent als erster Konsument (Referenz-Implementierung)
3. travel-beat + weltenhub migrieren nach bfagent-Stabilisierung
4. `ai_services` Apps in den jeweiligen Projekten deprecaten

---

## Implementation Plan

### Phase 1 — `iil-django-ai-services` (Priorität: Hoch)

- [ ] `platform/packages/iil-django-ai-services/` anlegen (pyproject.toml, src-Layout)
- [ ] Models aus bfagent extrahieren (LLMProvider, LLMModel, AIActionType, AIUsageLog)
- [ ] `service.py` aus bfagent übernehmen (neueste Version mit Thread-Pool-Fix)
- [ ] Migrations initial anlegen
- [ ] Unit-Tests (mocked LiteLLM)
- [ ] bfagent auf neues Paket migrieren (vendor/ oder direkte Dep)

### Phase 2 — `llm-prompt-stack` (Priorität: Mittel)

- [ ] `bfagent/packages/llm-prompt-stack/` anlegen
- [ ] Implementierung nach Konzept in `docs/adr/input/pypi_library_concept.md`
- [ ] bfagent writing_hub als erster Konsument
- [ ] travel-beat story-generation migrieren

### Phase 3 — `authoring-templates` (Priorität: Niedrig)

- [ ] Trigger: travel-beat **und** weltenhub nutzen aktiv dieselben Schemas
- [ ] Cross-Repo-Analyse: gemeinsame Character/World-Schemas identifizieren
- [ ] Extraktion mit Adapter-Protocol-Pattern

---

## Alternatives Considered

### A: Monorepo für alle AI-Projekte
Alle vier Projekte in einem Repo zusammenführen.
→ **Abgelehnt:** Zu viel Umbauaufwand, unterschiedliche Deploy-Zyklen, bestehende CI/CD-Infrastruktur pro Repo.

### B: iil_django_commons erweitern
`ai_services` als Submodul in `iil_django_commons` integrieren.
→ **Abgelehnt:** Vermischt Framework-Utilities (Cache, Health) mit Business-Logic (LLM). Zieht LiteLLM als Dep für alle Projekte, auch ohne LLM-Bedarf.

### C: Vendor-Packages (wie wedding-hub)
Code als Vendor-Verzeichnis in jedem Projekt kopieren.
→ **Abgelehnt:** Löst das Synchronisationsproblem nicht — ist der aktuelle Ist-Zustand.

### D: PyPI-Publikation (öffentlich)
`llm-prompt-stack` auf PyPI veröffentlichen.
→ **Zurückgestellt:** Erst wenn API stabil und zweiter externer Konsument existiert.
