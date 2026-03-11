---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
implementation_status: implemented
implementation_evidence:
  - "platform/docs/: documentation governance active"
---

# ADR-046: Documentation Governance — Hygiene, DIATAXIS & Docs Agent

| Metadata | Value |
| --------- | ----- |
| **Status** | Accepted |
| **Date** | 2026-02-18 |
| **Author** | Achim Dehnert |
| **Reviewers** | — |
| **Relation to ADR-020** | ADR-020 → Status: **Deferred** (Sphinx deferred, DB-Docs-Konzept adoptiert) |
| **Incorporates** | docs-agent-concept.md (2026-02-18, archiviert nach Merge) |
| **Related** | ADR-043 (Platform Context Store) |
| **Scope** | Alle 10 Repositories + zukünftige |
| **Note** | Compound ADR — trifft zwei verwandte Entscheidungen: Hygiene (Section 2) und Docs Agent (Section 3). Hygiene definiert Governance-Regeln, der Agent automatisiert deren Durchsetzung. Beide Concerns sind architektonisch gekoppelt, daher in einem ADR vereint |

---

## 1. Context

### 1.1 Problem Statement

Die `docs/` Verzeichnisse sind über Monate organisch gewachsen. Eine Analyse
aller 10 Repositories zeigt systematische Probleme:

| Problem | Betroffene Repos | Umfang |
| ------- | ---------------- | ------ |
| Sphinx-Build-Artefakte in Git | platform, travel-beat, risk-hub | ~170 Dateien |
| Code (.py) in docs/ | platform, travel-beat, risk-hub | ~50+ Dateien |
| Binärdateien (.pdf, .docx, .zip) | platform, travel-beat | ~10 Dateien, ~4 MB |
| Leerzeichen in Dateinamen | platform, travel-beat, risk-hub | ~8 Dateien |
| ADR-Nummern-Kollisionen | platform | 6 Nummern |
| Review/Input-Dokumente neben ADRs | platform, mcp-hub | ~30 Dateien |
| Docstring-Lücken (geschätzt ~60% undokumentiert, zu validieren in Phase 3) | alle Django-Repos | plattformweit |
| Keine DIATAXIS-Struktur | alle Repos | plattformweit |
| Kein automatischer Quality-Gate | alle Repos | plattformweit |

**Auswirkungen:**

- **AI-Kontext-Verschwendung**: Cascade indiziert Build-Artefakte, Duplikate,
  archivierte Konzepte — verbraucht Token-Budget ohne Mehrwert (x10 Repos)
- **Git aufgebläht**: ~4 MB Binaries, nie löschbar ohne `git filter-repo`
- **Code am falschen Ort**: .py in docs/ wird nicht getestet/gelinted
- **Pattern-Wiederholung**: Ohne Standard wiederholen sich Fehler in jedem Repo

### 1.2 Bestehende Tooling-Bausteine

| Baustein | Ort | Fähigkeit |
| -------- | --- | --------- |
| **LLM Client** | `bfagent/apps/core/services/llm/` | `get_client()`, `generate()`, `generate_structured()`, OpenAI + Anthropic |
| **LLM MCP** | `mcp-hub/llm_mcp/` | Multi-Provider (OpenAI, Anthropic, Ollama, Groq, Gemini), DB-backed Config |
| **DB MCP** | `postgres-*` MCP Server | Direkter SQL-Zugriff auf alle 5 App-Datenbanken |
| **Deployment MCP** | `mcp-hub/deployment_mcp/` | SSH, Docker, File-Ops auf Server |
| **Cascade** | Windsurf IDE | Code lesen, Dateien schreiben, MCP-Tools nutzen |

### 1.3 DIATAXIS Framework — AI-native Adoption

DIATAXIS (diataxis.fr) definiert 4 Dokumenttypen. Traditionell als "erfordert
dedizierte Tech-Writer" eingestuft — **überholt durch AI-Assistenten**, die die
Rolle des Tech-Writers übernehmen.

```text
                    PRAKTISCH
                       │
          Tutorials    │    Guides
        (Lern-orientiert) │  (Aufgaben-orientiert)
                       │
   LERNEN ─────────────┼──────────────── ARBEITEN
                       │
         Explanation   │    Reference
      (Verständnis-    │  (Informations-
       orientiert)     │   orientiert)
                       │
                   THEORETISCH
```

| Quadrant | Relevanz | AI-Umsetzung |
| -------- | -------- | ------------ |
| **Tutorials** | Mittel (steigt bei Teamwachstum) | Cascade erstellt Getting-Started-Guides |
| **Guides** | Hoch | Deploy-, Debug-, Migrations-Anleitungen |
| **Reference** | **Hoch (AI-generiert)** | Models, Lookups, API, Config via MCP-DB |
| **Explanation** | Hoch | ADRs + Architektur-Dokumente |

### 1.4 Sphinx & DB-driven Docs (ADR-020)

| Aspekt | Entscheidung |
| ------ | ------------ |
| **Sphinx-Infrastruktur** | **Deferred.** ADR-020 → Status "Deferred". Build-Pipeline nicht aktiv gepflegt. `source/` bleibt erhalten, kann reaktiviert werden wenn Team wächst oder `sphinx-autoapi` für Python-API-Reference benötigt wird |
| **DB-driven Docs** | **Adoptiert — via AI+MCP statt Sphinx.** Cascade generiert Reference-Docs direkt als Markdown via MCP-DB-Zugriff. Kein `manage.py generate_db_docs` nötig |

### 1.5 Best Practices

| Quelle | Anwendung |
| ------ | --------- |
| **DIATAXIS** (diataxis.fr) | 4 Quadranten als Verzeichnisstruktur, AI-enforced |
| **ADR Convention** (adr.github.io) | Eine Nummer = Eine Entscheidung, Status-Lifecycle |
| **Docs-as-Code** (writethedocs.org) | Docs reviewen, linten, testen |
| **Google Engineering Practices** | Build-Artefakte nie in VCS |
| **Mermaid** (mermaid.js.org) | Diagramme als Code statt Binary |

---

## 2. Decision: Documentation Hygiene

### 2.1 Standard-Verzeichnisstruktur (docs/)

```text
<repo>/docs/
├── tutorials/              # Learning-oriented: Getting Started, Walkthroughs
├── guides/                 # Task-oriented: Deployment, Migration, Debugging
├── reference/              # Information-oriented (AI-generiert via MCP)
│   ├── models.md           #   Django-Models (Cascade generiert)
│   ├── lookups.md          #   Lookup-Tabellen (Cascade generiert)
│   ├── api.md              #   URL-Patterns, Endpoints (Cascade generiert)
│   └── config.md           #   Environment-Variablen (Cascade generiert)
├── adr/                    # Architecture Decision Records (Explanation-Quadrant)
│   └── _archive/           #   inputs/, reviews/, superseded/
├── explanation/            # Understanding-oriented
│   └── architecture/       #   System design documents
├── source/                 # Sphinx-Quelle (deferred, optional)
└── _archive/               # Repo-weites Archiv (AI-Kontext ausgeschlossen)
```

**Nicht erlaubt in docs/:** `src/`, `apps/`, `infra/`, `scripts/`, `*.py`
(außer conf.py), Binaries, `_build/`, `docker-compose.yml`, Testdaten.

### 2.2 ADR-Status-Lifecycle

```text
Proposed → Accepted → Deprecated / Superseded by ADR-NNN
                ↘ Rejected
                ↘ Deferred
```

Nur "Superseded" → `_archive/superseded/`. Alle anderen bleiben in `adr/`.

### 2.3 Regeln (R-01 bis R-15)

| # | Regel | Geltung |
| - | ----- | ------- |
| R-01 | **Eine ADR-Nummer = Eine aktive Datei.** Kollision → ältere nach `_archive/superseded/` | Alle |
| R-02 | **Kein Binary in Git.** Diagramme als Mermaid. Falls unvermeidbar: Git LFS | Alle |
| R-03 | **Build-Output gitignored.** `_build/`, `build/`, `*.doctree` | Alle |
| R-04 | **Kein Code in docs/.** Ausnahme: Sphinx `conf.py` | Alle |
| R-05 | **Input nach Konsum archivieren.** Konzeptpapier → `_archive/inputs/` | Alle |
| R-06 | **Keine Infrastruktur in docs/.** docker-compose, terraform → Projekt-Root | Alle |
| R-07 | **ADR-Dateiname:** `ADR-{NNN}-{kebab-case}.md` — keine `-v2`, `-FINAL` Suffixe | Alle |
| R-08 | **Keine Sonderzeichen.** Keine Leerzeichen, Umlaute, Klammern. `kebab-case` | Alle |
| R-09 | **OS-Artefakte gitignored.** `*.Zone.Identifier`, `.DS_Store`, `Thumbs.db` | Alle |
| R-10 | **Reviews in eigenem Verzeichnis.** `_archive/reviews/`, nicht neben ADRs | Alle |
| R-11 | **Keine redundanten Verzeichnisse.** Ein Sphinx-Source, ein ADR-Verzeichnis | Alle |
| R-12 | **Testdaten nicht in docs/.** → `tests/fixtures/` | Alle |
| R-13 | **Neue Repos starten sauber.** `/onboard-repo` prüft docs/-Struktur | Neue |
| R-14 | **Quartalsweise Review.** docs/ aller Repos gegen Regeln prüfen | Alle |
| R-15 | **AI-Kontext-Ausschluss.** `.windsurf/rules/docs-hygiene.md` in jedem Repo | Alle |

### 2.4 AI-Kontext-Optimierung

Jedes Repo MUSS `.windsurf/rules/docs-hygiene.md` enthalten mit:
DIATAXIS-Enforcement, AI-generierte Reference-Docs, Kontext-Ausschluss
(`_archive/`, `_build/`, `source/`), Datei-Regeln, ADR-Lifecycle.

Referenz-Implementation: `platform/.windsurf/rules/docs-hygiene.md`

---

## 3. Decision: Docs Agent — AI-gestützte Qualitätssicherung

### 3.1 Architektur-Übersicht

```text
┌─────────────────────────────────────────────────────────┐
│                    Docs Agent                            │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  Analyzer     │  │  Generator   │  │  Classifier   │ │
│  │  (AST-based)  │  │  (LLM-based) │  │  (Heuristik   │ │
│  │              │  │              │  │   + LLM)      │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘ │
│         │                 │                  │          │
│  ┌──────▼─────────────────▼──────────────────▼────────┐ │
│  │              LLM Backend                             │ │
│  │  Primär:   llm_mcp (MCP Tool, DB-backed Config)    │ │
│  │  Fallback: apps.core.services.llm.get_client()     │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Komponenten

#### Analyzer: Docstring-Coverage (AST-basiert, kein LLM)

Scannt Python-Module via `ast`-Modul und berichtet undokumentierte Items:

- Klassen, Funktionen, Methoden ohne Docstring
- Coverage-Prozent pro Modul und gesamt
- Output: Markdown-Report oder JSON

#### Generator: Docstring-Erzeugung (LLM-basiert)

Generiert fehlende Docstrings via LLM mit Google-Style:

- Nutzt `generate_structured()` mit Pydantic-Model für validierte Ausgabe
- Code-Einfügung via `libcst` (non-destructive AST-Manipulation)
- Tier-Routing: FAST (gpt-4o-mini) für Docstrings, STANDARD (Claude Sonnet) für Guides

#### Classifier: DIATAXIS-Zuordnung (2-stufig)

1. **Heuristik** (schnell, kein LLM): Pattern-Matching auf Trigger-Wörter

   | Quadrant | Trigger-Wörter |
   | -------- | -------------- |
   | Tutorial | "step 1", "getting started", "learn", "we will" |
   | Guide | "how to", "configure", "deploy", "fix", "troubleshoot" |
   | Reference | "API", "parameter", "returns", "type:", "automodule" |
   | Explanation | "why", "architecture", "design", "rationale" |

2. **LLM-Feinklassifizierung** bei Confidence < 0.7 — erkennt Mixed Content

### 3.3 Betriebsmodi

| Modus | Trigger | Werkzeug | Beschreibung |
| ----- | ------- | -------- | ------------ |
| **Development** | Code-Änderung | Cascade + Windsurf-Rule | Echtzeit: Cascade aktualisiert Docs bei Model-/URL-/Settings-Änderungen |
| **Audit** | On-demand / Quartal | CLI: `docs-agent audit` | Scannt alle Repos, berichtet Coverage + DIATAXIS-Compliance |
| **Generate** | On-demand | CLI: `docs-agent generate` | Generiert fehlende Docstrings, Reference-Docs |
| **Scheduled** | Wöchentlich (optional) | Celery Beat / Management Command | Regeneriert Reference-Docs aus DB |

### 3.4 CLI Design (MVP)

```bash
# Docstring-Coverage Report (kein LLM, rein AST)
docs-agent audit /path/to/repo --scope docstrings

# DIATAXIS-Compliance (Heuristik + optional LLM)
docs-agent audit /path/to/repo --scope diataxis

# Fehlende Docstrings generieren (dry-run)
docs-agent generate docstrings /path/to/repo --dry-run

# Docstrings einfügen (via libcst)
docs-agent generate docstrings /path/to/repo --apply

# Alle Repos auditen
docs-agent audit-all --config docs-agent.yaml
```

### 3.5 Technologie-Entscheidungen

| Aspekt | Entscheidung | Begründung |
| ------ | ------------ | ---------- |
| LLM-Backend | `llm_mcp` (primär), `get_client()` (Fallback) | DB-backed Config, Multi-Provider, bereits deployed |
| AST-Manipulation | `libcst` | Non-destructive, preserviert Formatierung |
| CLI Framework | `typer` | Leichtgewichtig, auto-generierte --help |
| Docstring-Style | Google-Style | Platform-Standard (user rules) |
| Prompts | Python-Strings in `prompts.py` | Einfach, keine YAML-Overhead |
| Package-Ort | `platform/packages/docs-agent/` | Zentral, von allen Repos nutzbar |

### 3.6 Koexistenz: AI-Docs + Sphinx

| Aspekt | AI-generierte Markdown (primär) | Sphinx + autoapi (optional) |
| ------ | ------------------------------- | --------------------------- |
| Scope | Business-Logik: Models, Lookups, Workflows | Python-API: Signaturen, Docstrings |
| Quelle | DB-Schema + Code + LLM-Erklärungen | Python-Docstrings direkt |
| Trigger | Windsurf-Rule / Agent CLI | `sphinx-build` (CI oder lokal) |
| Status | **Aktiv (ab sofort)** | **Deferred** (bei Teamwachstum aktivieren) |

Wenn Sphinx reaktiviert wird: `myst-parser` für Markdown-Kompatibilität,
`furo`-Theme, `sphinx-autoapi` für Python-API-Reference.

---

## 4. Implementation Plan

### Phase 1: Hygiene-Grundlagen ✅

- `.gitignore` in allen 10 Repos mit ADR-046 Block
- `.windsurf/rules/docs-hygiene.md` in platform (Referenz)

### Phase 2: Cleanup (Repos bereinigen)

| Prio | Repo | Umfang | Kernaktion |
| ---- | ---- | ------ | ---------- |
| P1 | platform | ~1h | ADR-Kollisionen, Binaries, Reviews → `_archive/` |
| P1 | travel-beat | ~2h | 35 .py + Binaries + `_build/` → `_archive/` |
| P1 | risk-hub | ~2h | Ganzes Projekt-Scaffolding in docs/ → `_archive/` |
| P2 | bfagent, mcp-hub | ~30min | Reviews verschieben, `_build/` prüfen |
| P3 | odoo-hub, pptx-hub | ~30min | Testdaten, leere Verzeichnisse |

Cleanup-Script: `platform/docs/adr/input/adr046-cleanup.sh`

### Phase 3: Docs Agent MVP (~2 Tage)

| Task | Aufwand | Abhängigkeit |
| ---- | ------- | ------------ |
| Package-Scaffolding `packages/docs-agent/` | 2h | — |
| `analyzer/ast_scanner.py` — Docstring Coverage | 4h | — |
| `analyzer/diataxis_classifier.py` — Heuristik | 3h | — |
| CLI (`audit` command) via Typer | 2h | Scanner |
| Tests + Fixtures | 2h | Alle |

**Deliverable:** `docs-agent audit /path/to/repo` → Coverage-Report + DIATAXIS-Compliance

### Phase 4: Docs Agent LLM-Integration (~2 Tage)

| Task | Aufwand |
| ---- | ------- |
| `generator/docstring_gen.py` — LLM via `llm_mcp` | 4h |
| `generator/code_inserter.py` — libcst Integration | 4h |
| CLI (`generate` command) | 2h |
| LLM-Fallback-Classifier (Confidence < 0.7) | 3h |
| Tests | 2h |

**Deliverable:** `docs-agent generate docstrings --apply`

### Phase 5: Automatisierung (langfristig, optional)

| Tool | Zweck |
| ---- | ----- |
| Pre-commit Hook | Blockiert Binaries in docs/ |
| CI Lint-Check | Keine .py in docs/, keine Leerzeichen, .gitignore vollständig |
| CI Docs-Gate | `docs-agent audit --min-coverage 80 --fail-on-warnings` |
| Onboarding-Workflow | `/onboard-repo` erstellt korrekte docs/-Struktur |

---

## 5. Consequences

### Positive

- **Konsistenz über alle Repos**: DIATAXIS-Struktur + einheitliche Regeln
- **~300 Dateien weniger in Git**: Build-Artefakte, Binaries, Duplikate entfernt
- **Automatische Doku-Qualität**: AI generiert Reference-Docs + Docstrings
- **Skaliert für Teams**: Struktur + Agent sofort nutzbar bei Teamwachstum
- **Messbar**: Coverage-Reports, DIATAXIS-Compliance als Metriken

### Negative

- **Einmaliger Cleanup-Aufwand**: ~5-6h für alle Repos
- **Git-History-Brüche**: Umbenannte Dateien verlieren `git log --follow`
- **LLM-Kosten**: ~$0.01 pro Docstring-Generierung, ~$0.05 pro Guide

### Risiko-Mitigation

| Risiko | Mitigation |
| ------ | ---------- |
| Versehentlich aktive ADR archiviert | `_archive/` im selben Repo, wiederherstellbar |
| LLM generiert falsche Docstrings | dry-run Default, Review-Pflicht, Qualitäts-Prompt |
| AST-Manipulation bricht Code | libcst (non-destructive), Git-Rollback, Tests |
| Agent wird nicht genutzt | Development-Mode via Cascade-Rule als primärer Kanal |

---

## 6. Success Criteria

| Metrik | Vorher | Ziel Phase 2 | Ziel Phase 4 |
| ------ | ------ | ------------ | ------------ |
| Dateien in docs/_build/ | ~170 | 0 | 0 |
| Binaries in docs/ | ~10 | 0 | 0 |
| .py in docs/ (außer conf.py) | ~50 | 0 | 0 |
| ADR-Nummern-Kollisionen | 6 | 0 | 0 |
| Docstring Coverage (Ø) | geschätzt ~40% (Baseline in Phase 3) | — | 80% |
| Repos mit DIATAXIS-Struktur | 0/10 | 3/10 | 6/10 |
| Repos mit docs-hygiene Rule | 1/10 | 10/10 | 10/10 |

---

## 7. References

- [DIATAXIS Framework](https://diataxis.fr/)
- [ADR Convention](https://adr.github.io/) (Michael Nygard)
- [Docs-as-Code](https://www.writethedocs.org/guide/docs-as-code/)
- [Mermaid](https://mermaid.js.org/) — Diagramme als Code
- [ADR-020: Documentation Strategy](./ADR-020-documentation-strategy.md) — Status: **Deferred**
- [ADR-043: Platform Context Store](./ADR-043-platform-context-store.md)

---

## 8. Changelog

| Datum | Autor | Änderung |
| ----- | ----- | -------- |
| 2026-02-18 | Achim Dehnert | Initial Draft — Cross-Repo-Analyse, 15 Regeln, 6-Phasen-Plan |
| 2026-02-18 | Achim Dehnert | Review v1: ADR-Lifecycle, AI-Kontext, DIATAXIS/Sphinx-Bewertung |
| 2026-02-18 | Achim Dehnert | Review v2: DIATAXIS adoptiert (AI-enforced), DB-Docs via AI+MCP |
| 2026-02-18 | Achim Dehnert | **Merge mit docs-agent-concept.md**: Docs Agent (Section 3), LLM-Integration korrigiert (creative-services → llm_mcp + get_client), howto/ → guides/, 25d → 4d MVP, Redundanzen bereinigt, Sphinx-Koexistenz definiert |
| 2026-02-18 | Achim Dehnert | **Review-Fixes**: K-01 ADRs bei docs/adr/ belassen (nicht explanation/adr/), K-02 Metadata korrigiert (Deferred ≠ Superseded), K-03 Compound-ADR erklärt, S-01 Status→Accepted, S-02 Coverage als Schätzung, S-05 LLM-Priorisierung im Diagramm |
