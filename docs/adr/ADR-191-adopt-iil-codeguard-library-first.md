---
status: accepted
decision_date: 2026-05-09
amended: 2026-05-10
deciders:
  - Achim Dehnert
reviewed_by:
  - Claude (Sparring Review, 2026-05-09)
depends_on:
  - ADR-190 (iil-adrfw Tooling Framework)
  - ADR-048 (HTMX Playbook)
  - ADR-056 (Deployment Pre-Flight Validation)
  - ADR-010 (MCP Tool Governance)
  - ADR-075 (Read-Only MCP / Write via GitHub Actions)
repo: platform
consumers:
  - dev-hub
  - travel-beat
  - bfagent
  - risk-hub
  - weltenhub
  - wedding-hub
  - coach-hub
domains:
  - django/views
  - django/models
  - htmx
  - deployment
  - mcp
implementation_status: verified
implementation_evidence:
  - "achimdehnert/iil-codeguard v2026.05.1 published to PyPI (2026-05-10)"
  - "Phase 1a-c complete: ORM Detector (SL-001..006), HTMX scanner (HX-001..009), SARIF/JSON/Text reporters"
  - "Phase 2a-c complete: CLI, MCP server (3 read-only tools), Compose (DC-001..009) + Dockerfile (DF-001..009) checkers"
  - "Phase 3 underway: dev-hub integrated via PR #25 (pre-commit + GitHub Action + Code Scanning SARIF)"
  - "69/69 tests passing, ruff clean, CI green on Python 3.12+3.13"
  - "Empirical: 17 critical findings + 1,062 errors across 5 platform repos that REFLEX missed"
  - "MCP registered in mcp_config.json as mcp3_iil-codeguard (3 tools: codeguard_audit, codeguard_check_file, codeguard_list_rules)"
staleness_months: 6
last_reviewed: 2026-05-10
drift_check_paths:
  - iil-codeguard/src/
---

<!-- Drift-Detector-Felder: staleness_months: 6, drift_check_paths: iil-codeguard/src/, supersedes_check: ADR-191 v1.0 -->

# ADR-191: Adopt iil-codeguard — Library-First Code Compliance Tooling

> **Historie:** Frühere Abhängigkeit ADR-009 (Service Layer Architecture) ist archiviert (`docs/adr/archive/`) und wurde aus `depends_on` entfernt.

| Metadaten | |
|-----------|---|
| **Status** | Accepted (v1.1, amended 2026-05-10) — Implementation verified |
| **Datum** | 2026-05-09 (v1.0), 2026-05-10 (v1.1) |
| **Autor** | Achim Dehnert |
| **Reviewer** | Claude (Sparring Review) |
| **Depends On** | ADR-190, ADR-009, ADR-048, ADR-056, ADR-010, ADR-075 |
| **Consumers** | dev-hub, travel-beat, bfagent, risk-hub, weltenhub, wedding-hub, coach-hub |

---

## v1.0 → v1.1 — Was sich geändert hat

| Aspekt | v1.0 | v1.1 (nach Sparring) |
|--------|------|----------------------|
| **Architektur** | "Extend platform-context MCP" | **Library-First** — eigenes `iil-codeguard` Package, MCP als dünner Wrapper |
| **Service-Layer Check** | View ruft Service auf? | **Inversion**: View enthält ORM? (beweisbar, CBV-kompatibel) |
| **Output-Format** | Strukturiertes JSON | **SARIF 2.1.0** + JSON + Text (GitHub Code Scanning native) |
| **CBV-Support** | Open Question (verschoben) | **Phase 1** (empirisch: dev-hub 93%, weltenhub 88%) |
| **Integrationen** | MCP-only initial | **CLI + MCP + pre-commit + GitHub Action** ab Phase 1 |

## Context and Problem Statement

Die IIL Platform setzt Architektur-Standards über drei Mechanismen durch:

1. **Windsurf Rules** (`.windsurf/rules/`) — Agent-Instruktionen, nur in Cascade-Sessions wirksam
2. **platform-context MCP** (4 Tools) — String-Pattern-Matching gegen Banned Patterns
3. **iil-reflex** (CLI) — Regex-basierter Scanner über 19 Repos

**Empirisch belegte Lücke** (Stakeholder-Validation 2026-05-10):

| Repo | Views.py-Anteil CBV | HTMX-Elements mit Django-Tags | Aktueller Coverage |
|------|---------------------|-------------------------------|---------------------|
| dev-hub | 93% (62/67) | 33% (18/55) | ❌ String-match findet Service-Verstöße in CBV nicht |
| weltenhub | 88% (43/49) | 66% (19/29) | ❌ Gleiche Lücke |
| bfagent | 1% (1/156) | 42% (290/697) | ⚠️ FBV gut, HTMX-Templates ungeprüft |
| travel-beat | 2% (1/45) + 12% async | 48% (61/126) | ⚠️ Async-Views ungeprüft |

**Problem**: Keine der drei vorhandenen Mechanismen kann strukturelle Fragen beantworten:
- "Greift die `form_valid()`-Methode in einer CBV auf das ORM zu?"
- "Haben alle HTMX-Elemente in `templates/` die Pflichtattribute?"
- "Existiert eine `services.py` für jede App mit Views?"

ADR-190 (iil-adrfw) hat bewiesen, dass das MCP-First-Pattern funktioniert. **Aber**: ADR-190 ist ein eigenes Package mit CLI + MCP-Server. Ein reiner MCP-Tool-Ansatz würde Compliance-Checks aus folgenden Pfaden ausschließen:

- Dependabot-PRs (kein Cascade-Run)
- Manuelle GitHub-Web-Edits (kein lokales Tooling)
- Pre-Commit Hooks für lokale Devs ohne Cascade-Subscription
- External Contributors

## Decision Drivers

1. **Coverage**: Tool muss CBV (88-93% in 2 Hauptrepos), async views (12% in travel-beat) und HTMX-Templates erfassen
2. **Integrierbarkeit**: CLI ab Tag 1, damit Pre-Commit + GitHub Action sofort möglich
3. **Output-Standard**: SARIF 2.1.0 für native GitHub Code Scanning Integration
4. **Wartbarkeit**: Eigenes Repo mit eigenem Release-Zyklus, nicht in platform-monorepo
5. **Konsistenz**: Gleiches Pattern wie iil-adrfw (Library + CLI + MCP)
6. **Performance**: <5 Sekunden pro PR-Audit (Pflicht für Akzeptanz)

## Decision Outcome

**Wir adoptieren `iil-codeguard` als eigenständiges PyPI-Package mit Library-First-Architektur.**

```
┌─────────────────────────────────────────────────────────────┐
│  iil-codeguard (PyPI, eigenes Repo, achimdehnert/)          │
│                                                             │
│  Core Library                                               │
│  ├── checkers/                                              │
│  │   ├── orm_in_view.py        (Python ast, CBV+async)      │
│  │   ├── htmx_required_attrs.py (html.parser + HX-009)      │
│  │   ├── compose_security.py   (pyyaml)                     │
│  │   └── dockerfile_audit.py   (line-based)                 │
│  ├── reporters/                                             │
│  │   ├── sarif.py    (GitHub Code Scanning)                 │
│  │   ├── json.py     (MCP)                                  │
│  │   └── text.py     (Terminal)                             │
│  ├── api.py          (Python API für Embedding)             │
│  └── cli.py          (codeguard audit . --format sarif)     │
│                                                             │
│  Adapters                                                   │
│  ├── mcp_server/     (2 Tools: codeguard_audit,             │
│  │                    codeguard_check_file)                 │
│  ├── pre_commit_hooks.yaml                                  │
│  └── github_actions/codeguard.yml                           │
└─────────────────────────────────────────────────────────────┘
```

**Begründung der gewählten Option:**
- CLI-First erlaubt Integration in **alle** PR-Pfade (nicht nur Cascade)
- 2 MCP-Tools statt 4 → vermeidet "god server" Anti-Pattern
- SARIF macht GitHub Code Scanning Native (rote X im PR direkt am Code)
- Eigenes Repo erlaubt unabhängiges Versioning + CalVer (`2026.05.x`)

## Considered Options

### Option A: Extend platform-context with 4 MCP tools (v1.0 Vorschlag, verworfen)
- **Pro**: Schnell (4-6 Tage), nutzt vorhandene Infrastruktur
- **Con**: God-Server-Risiko, kein CLI, schließt 4 von 5 PR-Pfaden aus, spätere Extraction kostet 2-3 zusätzliche Tage in inkonsistentem Zustand

### Option B: iil-codeguard als Library-First Package (gewählt)
- **Pro**: CLI ab Tag 1, SARIF-Native, kein god-server, gleiches Pattern wie iil-adrfw, zukunftsfähig
- **Con**: ~1 Tag Mehraufwand für Repo-Setup + GitHub Action Template

### Option C: iil-reflex erweitern um AST
- **Pro**: 19 Repos schon onboarded
- **Con**: REFLEX ist intentional regex-basiert für Speed. AST-Umbau verändert Architektur grundlegend

### Option D: Ruff Custom Rules
- **Pro**: Sehr schnell, bekanntes Tool
- **Con**: Plugin-System unterstützt keine Django-spezifische Domain-Logik (Service-Layer-Pattern, Template-Scanning)

### Option E: Semgrep
- **Pro**: Mächtige Pattern-Sprache
- **Con**: Heavy Dependency (~200 MB), Custom-Rules in YAML schwer testbar, Overkill für unsere ~10 Rules

## Pros and Cons of the Options

| Kriterium | A (extend) | **B (codeguard)** | C (reflex) | D (ruff) | E (semgrep) |
|-----------|:----------:|:-----------------:|:----------:|:--------:|:-----------:|
| CLI-Integration | ❌ | ✅ | ✅ | ✅ | ✅ |
| GitHub Action ready | ❌ | ✅ | ⚠️ | ⚠️ | ✅ |
| pre-commit ready | ❌ | ✅ | ⚠️ | ✅ | ⚠️ |
| MCP-Integration | ✅ | ✅ | ❌ | ❌ | ❌ |
| SARIF-Output | ❌ | ✅ | ❌ | ⚠️ | ✅ |
| CBV-Support nativ | ❌ | ✅ | ❌ | ⚠️ | ✅ |
| Stdlib-First | ❌ | ✅ | ✅ | ❌ | ❌ |
| Aufwand | 4-6d | 6-8d | 10-12d | 8d | 10d |

## Output Schema (SARIF 2.1.0)

Alle Reporter produzieren Findings im selben internen Format, dann gerendert in:

```json
{
  "version": "2.1.0",
  "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
  "runs": [{
    "tool": {"driver": {"name": "iil-codeguard", "version": "2026.05.0"}},
    "results": [{
      "ruleId": "SL-001",
      "level": "error",
      "message": {"text": "Direct ORM access in view function. Move to services.py."},
      "locations": [{
        "physicalLocation": {
          "artifactLocation": {"uri": "apps/trips/views.py"},
          "region": {"startLine": 42, "startColumn": 8}
        }
      }],
      "fixes": [{"description": {"text": "Replace with trip_service.create_trip(...)"}}]
    }]
  }]
}
```

## MCP Tools (2, nicht 4)

| Tool | Input | Output | Read-Only |
|------|-------|--------|----------|
| `codeguard_audit` | `repo`, optional `severity_threshold`, optional `summary_only` | SARIF JSON, paginated | ✅ |
| `codeguard_check_file` | `repo`, `file_path` | SARIF JSON für eine Datei | ✅ |

**Pagination & Token Budget**: `codeguard_audit` defaultet auf `summary_only=True` (counts pro rule_id). Voller Output nur bei expliziter Anforderung mit `severity_threshold` und `max_results`.

## Suppression Mechanism

Inline-Suppressions (Phase 2):
```python
queryset = Trip.objects.filter(...)  # codeguard: disable=SL-001 (legacy migration)
```

Repo-weite Suppressions in `pyproject.toml`:
```toml
[tool.codeguard]
suppress = ["SL-001:apps/legacy/**"]
```

## Rule ID Convention

`{CATEGORY}-{NUMBER}` mit stabilen IDs:
- `SL-NNN` Service Layer (ADR-009)
- `HX-NNN` HTMX (ADR-048)
- `DC-NNN` Docker Compose (ADR-021, ADR-022)
- `DF-NNN` Dockerfile (ADR-056)
- `NX-NNN` Nginx (ADR-060)
- `MD-NNN` Models / Database (ADR-022, ADR-043)

Rule-IDs sind **stabil** über Versionen — Verschärfung einer Rule erzeugt eine neue ID (z.B. `SL-001` strict → `SL-001a`).

## Performance Strategy

| Optimierung | Phase | Impact |
|-------------|------:|--------|
| Per-File Content-Hash Cache | 1 | -80% bei zweitem Run |
| `concurrent.futures.ProcessPoolExecutor` für AST | 1 | -70% bei Multi-File |
| `git diff` inkrementell für PR-Mode | 2 | <2s pro PR |
| Lazy import von Checkers | 1 | <100ms Startup |

**Ziel-Budget**: <5s für ein durchschnittliches PR-Diff (10 Files), <30s für Full-Repo-Audit.

## Consequences

### Good
- Erfasst alle PR-Pfade (Cascade, Web-UI, Dependabot, External)
- SARIF + GitHub Code Scanning = rote X direkt am betroffenen Code im PR
- 2 MCP-Tools vs 4 → kein god-server
- Eigenes Repo = eigener Release-Zyklus + CalVer
- ORM-Inversion erfasst CBV + async ohne Sonderfälle
- Empirisch validiert: 940 HTMX-Elements + 388 Views in 7 Repos analysiert

### Bad
- ~1 Tag Mehraufwand für Repo-Setup + Workflows
- Eigenes Repo = eigene Issue-Tracker + Release-Pipeline
- SARIF-Generation hat Lernkurve
- 19 bestehende Repos müssen `pre-commit` config aktualisieren

### Confirmation

**Wie wird Compliance dieses ADRs verifiziert?**
1. Existenz: `https://github.com/achimdehnert/iil-codeguard` Repo vorhanden
2. PyPI: `pip install iil-codeguard` funktioniert
3. CLI: `codeguard --version` und `codeguard audit .` funktionieren
4. MCP: 2 Tools (`codeguard_audit`, `codeguard_check_file`) im `mcp_config.json` registriert
5. Integrationen: Mindestens 1 Repo nutzt `pre-commit-hooks.yaml`, mindestens 1 Repo hat GitHub Action aktiv
6. SARIF: Output validiert gegen `https://json.schemastore.org/sarif-2.1.0.json`

## Implementation Plan

| Phase | Scope | Aufwand |
|-------|-------|---------|
| **Phase 0** | Repo-Setup (`achimdehnert/iil-codeguard`), CalVer, CI, PyPI-Publish-Workflow | 1 Tag |
| **Phase 1a** | Core Library + ORM-Detector (Python ast, CBV+async) | 1.5 Tage |
| **Phase 1b** | HTMX-Scanner (html.parser + HX-009 Trip-Wire für `{% %}` zwischen Attrs) | 1 Tag |
| **Phase 1c** | SARIF Reporter + JSON + Text | 1 Tag |
| **Phase 2a** | CLI + GitHub Action Template + pre-commit Hook | 1 Tag |
| **Phase 2b** | MCP Server (2 Tools) | 1 Tag |
| **Phase 2c** | Compose + Dockerfile Checker | 1 Tag |
| **Phase 3** | Integration in 7 Consumer-Repos (Pre-Commit + Action) | 1 Tag |
| **Total** | | **8.5 Tage** |

## Open Questions

- **OQ-1** (~~Blocker~~ ✅ entschieden): CBV-Support in Phase 1 — empirisch validiert mit dev-hub (93%) und weltenhub (88%)
- **OQ-2**: SARIF-Schema für `fixes`-Feld — wie repräsentieren wir "Move ORM to services.py" als Auto-Fix? (Phase 2)
- **OQ-3**: Versionierung der Rule-Sets — was passiert wenn `SL-001` schärfer wird, alte PRs aber unter v2026.05 geprüft wurden? Vorschlag: Rule-Frozen-IDs (`SL-001a` für Verschärfungen)
- **OQ-4**: Performance-Ziel <5s pro PR — Caching-Strategie (mtime vs content-hash)? Vorschlag: content-hash, identisch zu Ruff
- **OQ-5**: i18n der Violation-Messages — Phase 3 oder Phase 1? Vorschlag: Phase 1 mit `gettext`-Vorbereitung, EN als Default

## Related ADRs

- **ADR-190**: iil-adrfw Tooling Framework — Pattern-Vorbild (Library + CLI + MCP)
- **ADR-009**: Service Layer Architecture — Quelle der SL-Rules
- **ADR-048**: HTMX Playbook — Quelle der HX-Rules
- **ADR-022, ADR-056**: Deployment Standards — Quelle der DC/DF-Rules
- **ADR-010**: MCP Tool Governance — Read-Only-Markierung, Token-Budget
- **ADR-075**: Read-Only MCP / Write via GHA — Audit ist read-only-konform

## Sparring Review (2026-05-09)

Empirische Validierung führte zu folgenden Anpassungen vom v1.0-Vorschlag:

| Sparring-Punkt | Empirie | Aktion |
|----------------|---------|--------|
| html.parser unzuverlässig | 0/940 Pathological-Cases | html.parser beibehalten + HX-009 Trip-Wire |
| ast unzuverlässig (libcst empfohlen) | ast.lineno funktioniert für CBV+async | stdlib ast beibehalten |
| MCP-only Anti-Pattern | bestätigt | Library-First übernommen |
| Service-Match → ORM-Inversion | bestätigt | Inversion übernommen |
| CBV als Phase-1-Blocker | dev-hub 93%, weltenhub 88% | Phase 1 inklusive CBV |
| SARIF-Output | Architektur-Argument | Übernommen |
| Suppression-Mechanismus | fehlte | Hinzugefügt |
| Token-Budget | fehlte | Hinzugefügt (summary-only Default) |

## Glossar

- **AST** — Abstract Syntax Tree, Baum-Repräsentation von Quellcode für strukturelle Analyse
- **CBV** — Class-Based View (Django-View als Klasse, z.B. `CreateView`, `UpdateView`)
- **FBV** — Function-Based View (Django-View als Funktion, `def my_view(request)`)
- **CalVer** — Calendar Versioning (`YYYY.MM.PATCH`, z.B. `2026.05.0`)
- **HTMX** — Frontend-Library für AJAX/Hypermedia-Interaktionen via HTML-Attribute
- **MCP** — Model Context Protocol, Standard für AI-Tool-Server (Anthropic)
- **ORM** — Object-Relational Mapper (Django: `Model.objects.filter(...)`)
- **SARIF** — Static Analysis Results Interchange Format, OASIS-Standard für Linter-Output
- **stdlib** — Python Standard Library (kein zusätzliches Package nötig)
