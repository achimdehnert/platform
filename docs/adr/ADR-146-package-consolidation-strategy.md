---
status: "proposed"
date: 2026-03-25
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-022-platform-consistency-standard.md", "ADR-027-shared-backend-services.md", "ADR-028-platform-context.md", "ADR-035-shared-django-tenancy.md", "ADR-044-mcp-hub-architecture-consolidation.md", "ADR-050-platform-decomposition-hub-landscape.md"]
implementation_status: not_started
implementation_evidence: []
review_status: "pending"
---

# ADR-146: Package Consolidation Strategy — 36 → 18 Packages

## Context and Problem Statement

Die IIL-Plattform hat organisch **36 Python-Packages** über 5 Repos/Registries
angesammelt. Dieses Wachstum erzeugt:

1. **Wartungslast**: 36 pyproject.toml, 36 Changelogs, 36 Release-Pipelines
2. **Dependency-Chaos**: nl2cad hat 7 PyPI-Packages für nur 2 Consumer
3. **Naming-Inkonsistenz**: `iil-*`, `nl2cad-*`, `riskfw` (ohne Prefix)
4. **Orphan-Packages**: 4 Packages mit 0 Consumer (`iil-cad-services`, etc.)
5. **Fragile Installs**: `git+https://...#subdirectory=` statt PyPI-Pins
6. **Cognitive Load**: Entwickler müssen 36 Package-Namen und deren Zweck kennen

### Bestandsaufnahme (März 2026)

| Kategorie | Packages | Beschreibung |
|-----------|----------|--------------|
| nl2cad-Ökosystem | 7 | IFC/DXF, DIN 277, Brandschutz, GAEB, NLP |
| AI/LLM Frameworks | 4 | aifw, promptfw, authoringfw, task-scorer |
| Platform-Infra | 11 | platform-context, django-commons, tenancy, shop, etc. |
| Domain-Frameworks | 7 | learnfw, weltenfw, outlinefw, researchfw, illustrationfw, riskfw, brandschutzfw |
| Tooling | 5 | testkit, docs-agent, chat-agent, creative-services, mcp-governance |
| **Gesamt** | **36** (davon 4 Orphans, 2 Redirects) | |

### Consumer-Analyse

| Package | Consumer-Count | Hubs |
|---------|---------------|------|
| iil-promptfw | 6 | risk, cad, trading, pptx, writing, bfagent |
| iil-authoringfw | 6 | risk, cad, trading, pptx, writing, bfagent |
| iil-aifw | 4 | risk, pptx, writing, bfagent |
| nl2cad-core | 2 | risk-hub, cad-hub |
| nl2cad-brandschutz | 1 | cad-hub (risk-hub migriert: b59155d) |
| iil-cad-services | 0 | — |
| iil-platform-search | 0 | — |
| iil-content-store | 0 | — |
| iil-illustrationfw | 0 | — |

## Decision Drivers

- **Weniger Packages = weniger Wartung** (Releases, CVE-Updates, CI/CD)
- **Konsistentes Naming** für Developer Experience
- **Extras statt Micro-Packages** wo sinnvoll (pip install X[feature])
- **1-Consumer-Packages** gehören ins Consumer-Repo (kein separates Package)
- **0-Consumer-Packages** werden gelöscht oder depreciert
- **PyPI statt git+https** für reproduzierbare Builds

## Considered Options

### Option A: Status quo beibehalten
- Pro: Kein Migrationsaufwand
- Contra: Wartungslast steigt weiter, Orphans bleiben

### Option B: Moderate Konsolidierung (36 → 24)
- Nur Orphans löschen, Redirects entfernen, 1-Consumer nach innen ziehen
- Pro: Geringes Risiko
- Contra: Strukturprobleme (nl2cad-Zersplitterung, Platform-Fragmentierung) bleiben

### Option C: Aggressive Konsolidierung (36 → 18) ✅
- nl2cad: 7 → 1 (mit Extras)
- Platform: 11 → 5 (1 Kern + 4 bfagent-interne)
- Domain: 7 → 6 (illustrationfw deprecieren)
- Orphans: alle entfernen
- Pro: 50% Reduktion, klare Architektur
- Contra: Mehr Migrationsaufwand, Breaking Changes

## Decision Outcome

**Option C: Aggressive Konsolidierung (36 → 18)**

### Konsolidierungs-Map

#### Tier 1: Sofort löschen/deprecaten (Phase 1)

| Package | Aktion | Begründung |
|---------|--------|------------|
| `nl2cad` | PyPI yanken | Redirect-Package, nutzlos |
| `iil-nl2cadfw` | Deprecaten | Meta-Package ohne eigenen Code |
| `nl2cad-brandschutz` | Deprecaten auf PyPI | Lebt jetzt in risk-hub (b59155d) |
| `iil-cad-services` | Löschen (platform/) | 0 Consumer |
| `iil-platform-search` | Löschen (platform/) | 0 Consumer |
| `iil-content-store` | Löschen (platform/) | 0 Consumer |
| `iil-illustrationfw` | Deprecaten | 0 Consumer |

**Ergebnis: −7 Packages**

#### Tier 2: nl2cad konsolidieren (Phase 2)

7 Packages → 1 Package mit Extras:

```toml
# nl2cad-core/pyproject.toml — wird zum einzigen Package
[project]
name = "nl2cad-core"
version = "0.2.0"

[project.optional-dependencies]
areas = []       # DIN 277 (bisher nl2cad-areas)
gaeb = ["lxml"]  # GAEB X81-X85 (bisher nl2cad-gaeb)
nlp = ["spacy"]  # NL2CAD Intent (bisher nl2cad-nlp)
all = ["nl2cad-core[areas,gaeb,nlp]"]
```

Subpackage-Struktur bleibt intern:
```
nl2cad/
  core/       → nl2cad-core (Basis)
  areas/      → nl2cad-core[areas]
  gaeb/       → nl2cad-core[gaeb]
  nlp/        → nl2cad-core[nlp]
```

Consumer-Migration:
- `risk-hub`: `nl2cad-core[areas,gaeb]` (kein brandschutz, kein nlp)
- `cad-hub`: `nl2cad-core[areas,gaeb,nlp]` + eigenes brandschutz

Compat-Redirect: `nl2cad-areas>=0.2.0` → `install_requires = ["nl2cad-core[areas]"]`
für 1 Release, dann deprecate.

**Ergebnis: −6 Packages (7→1)**

#### Tier 3: Platform konsolidieren (Phase 3)

11 Packages → 1 Kern-Package + bfagent-interne:

```toml
# iil-platform/pyproject.toml
[project]
name = "iil-platform"
version = "1.0.0"
description = "IIL Platform Foundation — Context, Commons, Health, Security"

[project.optional-dependencies]
tenancy = []          # bisher iil-django-tenancy
shop = []             # bisher iil-django-module-shop
notifications = []    # bisher iil-platform-notifications
full = ["iil-platform[tenancy,shop,notifications]"]
```

| VORHER | NACHHER |
|--------|---------|
| iil-platform-context | → `iil-platform` (Kern) |
| iil-django-commons | → `iil-platform` (merge) |
| iil-django-tenancy | → `iil-platform[tenancy]` |
| iil-django-module-shop | → `iil-platform[shop]` |
| iil-platform-notifications | → `iil-platform[notifications]` |
| iil-bfagent-core | → `bfagent/` Repo intern |
| iil-bfagent-llm | → `bfagent/` Repo intern |
| iil-chat-logging | → `bfagent/` Repo intern |
| iil-chat-agent | → `bfagent/` Repo intern |
| iil-creative-services | → `bfagent/` Repo intern |

**Ergebnis: −6 Packages (11→5)**

#### Tier 4: Naming-Konsistenz (Phase 4)

| VORHER | NACHHER |
|--------|---------|
| `riskfw` | `iil-riskfw` |

Alle Packages tragen `iil-` Prefix. Ausnahme: `nl2cad-core` (eigene Marke).

### Ergebnis-Übersicht

| Kategorie | Vorher | Nachher | Packages |
|-----------|--------|---------|----------|
| nl2cad | 7 | 1 | nl2cad-core (mit Extras) |
| AI/LLM | 4 | 4 | aifw, promptfw, authoringfw, task-scorer |
| Platform | 11 | 1+4 | iil-platform + 4× bfagent-intern |
| Domain | 7 | 6 | learnfw, weltenfw, outlinefw, researchfw, riskfw, brandschutzfw* |
| Tooling | 5 | 2 | testkit, mcp-governance |
| **Gesamt** | **36** | **18** | **−50%** |

*brandschutzfw wird erst bei cad-hub-Productionisierung als `iil-brandschutzfw` extrahiert.

## Migration Plan

### Phase 1: Aufräumen (Woche 1) — Risiko: Null

1. PyPI: `nl2cad` yanken (Redirect)
2. PyPI: `nl2cad-brandschutz` deprecation notice (README + final release)
3. PyPI: `iil-nl2cadfw` deprecation notice
4. `platform/packages/`: `cad-services/`, `platform-search/`, `content-store/` entfernen
5. `illustration-fw/`: Repo archivieren (GitHub)

### Phase 2: nl2cad → nl2cad-core[extras] (Woche 2–3) — Risiko: Mittel

1. nl2cad Mono-Repo: Code von areas, gaeb, nlp in nl2cad-core als Subpackages
2. nl2cad-core 0.2.0 mit `[areas]`, `[gaeb]`, `[nlp]` Extras releasen
3. Compat-Releases: nl2cad-areas 0.2.0 → `requires = ["nl2cad-core[areas]>=0.2"]`
4. risk-hub: `requirements.txt` → `nl2cad-core[areas,gaeb]>=0.2`
5. cad-hub: `requirements.txt` → `nl2cad-core[areas,gaeb,nlp]>=0.2`
6. 1 Release-Zyklus warten
7. nl2cad-areas, nl2cad-gaeb, nl2cad-nlp auf PyPI deprecaten

### Phase 3: iil-platform (Woche 4–5) — Risiko: Hoch

1. Neues Package `iil-platform` aus platform-context + django-commons erstellen
2. Extras: `[tenancy]`, `[shop]`, `[notifications]` einrichten
3. Compat-Release: `iil-platform-context 0.6.0` → `requires = ["iil-platform>=1.0"]`
4. Alle Consumer migrieren (risk-hub, coach-hub, billing-hub, wedding-hub)
5. bfagent-interne Packages in bfagent/ Repo verschieben
6. Alte Packages deprecaten

### Phase 4: Naming + Cleanup (Woche 6) — Risiko: Niedrig

1. `riskfw` → `iil-riskfw` (rename + compat redirect)
2. Alle `git+https://` Installs durch PyPI-Pins ersetzen
3. INDEX.md aktualisieren
4. Finale Dokumentation

## Compliance Notes

- **Zero Breaking Changes**: Jede Phase hat Compat-Redirects für 1 Release
- **ADR-022**: Konsistenz-Standard wird durch einheitliches Naming gestärkt
- **ADR-050**: Hub-Landscape wird vereinfacht (weniger externe Dependencies)
- **CI/CD**: Weniger Package-Releases = weniger Pipeline-Durchläufe

## Risks and Mitigations

| Risiko | Impact | Mitigation |
|--------|--------|------------|
| Breaking Imports | Hoch | Compat-Redirects für 1 Release-Zyklus |
| PyPI Yank irreversibel | Mittel | Nur `nl2cad` (Redirect) yanken, Rest deprecaten |
| bfagent-interne Packages | Niedrig | Graduelle Migration, bfagent-Tests als Gate |
| iil-platform zu gross | Mittel | Extras halten es modular, nur Kern ist Pflicht |
| Parallele Arbeit blockiert | Mittel | Phase 1 (Orphans) ist unabhängig, sofort machbar |
