---
status: "proposed"
date: 2026-03-25
updated: 2026-03-25
version: 2
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: ["ADR-027-shared-backend-services.md"]
amends: []
related: ["ADR-022-platform-consistency-standard.md", "ADR-028-platform-context.md", "ADR-035-shared-django-tenancy.md", "ADR-044-mcp-hub-architecture-consolidation.md", "ADR-050-platform-decomposition-hub-landscape.md"]
implementation_status: not_started
implementation_evidence: []
review_status: "reviewed — v2 addresses 14 findings from ADR-146-review.md"
---

# ADR-146: Package Consolidation Strategy — 34 → 22 Packages (v2)

## Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| v1 | 2026-03-25 | Initialer Entwurf (36→18) |
| v2 | 2026-03-25 | Review-Findings eingearbeitet: korrigiertes Inventar (34→22), ADR-027 supersede, Umbrella statt Merge (Tier 3), Import-Pfad-Stabilität, realistische Timeline, Akzeptanz-Kriterien |

## Context and Problem Statement

Die IIL-Plattform hat organisch **34 Python-Packages** über 5+ Repos/Registries
angesammelt. Dieses Wachstum erzeugt:

1. **Wartungslast**: Dutzende pyproject.toml, Changelogs, Release-Pipelines
2. **Dependency-Chaos**: nl2cad hat 7 PyPI-Packages für nur 2 Consumer
3. **Naming-Inkonsistenz**: `iil-*`, `nl2cad-*`, `riskfw` (ohne Prefix)
4. **Orphan-Packages**: 4+ Packages mit 0 Consumer (`iil-cad-services`, etc.)
5. **Fragile Installs**: `git+https://...#subdirectory=` statt PyPI-Pins
6. **Cognitive Load**: Entwickler müssen zahlreiche Package-Namen und deren Zweck kennen

### Supersede-Begründung: ADR-027

ADR-027 entschied "Option A — Modulare Packages in `platform/packages/`" und lehnte
"Option B — Standalone PyPI / Ein Package mit Extras" ab. Die Erfahrung seit Februar 2026
zeigt jedoch, dass 11 Einzelpackages in `platform/packages/` zu hoher Wartungslast führen
und Consumer 3–5 separate `git+https://` Einträge in requirements.txt benötigen.
ADR-146 wählt einen **Umbrella-Package-Ansatz als Kompromiss**: Sub-Packages bleiben
intern eigenständig, werden aber über `iil-platform` gebündelt verteilt.

### Bestandsaufnahme (März 2026)

#### A) pip-distributed Packages (22)

| # | Kategorie | Packages | Count |
|---|-----------|----------|-------|
| 1 | nl2cad-Ökosystem | nl2cad, iil-nl2cadfw, nl2cad-core, nl2cad-areas, nl2cad-brandschutz, nl2cad-gaeb, nl2cad-nlp | 7 |
| 2 | AI/LLM Frameworks | iil-aifw, iil-promptfw, iil-authoringfw | 3 |
| 3 | Platform (pip) | iil-platform-context, iil-django-commons, iil-django-tenancy, iil-django-module-shop, iil-platform-notifications | 5 |
| 4 | Domain Frameworks | iil-learnfw, iil-weltenfw, iil-outlinefw, iil-researchfw, iil-illustrationfw, riskfw | 6 |
| 5 | Shared Tools | iil-testkit | 1 |
| | **Subtotal pip-distributed** | | **22** |

#### B) Interne Platform-Packages (nicht pip-distributed, 12)

Diese Packages existieren in `platform/packages/` aber werden **nicht per pip installiert**.
Sie werden direkt per `git+https://...#subdirectory=` oder lokal eingebunden.

| Package | Genutzt von | Status |
|---------|-------------|--------|
| iil-bfagent-core | bfagent (intern) | Aktiv, nicht pip-distributed |
| iil-bfagent-llm | bfagent (intern) | Aktiv, nicht pip-distributed |
| iil-chat-agent | bfagent (1 Import), cad-hub (vendored) | Aktiv, nicht pip-distributed |
| iil-chat-logging | Prüfen | Evtl. Orphan |
| iil-creative-services | cad-hub (vendored in `vendor/`) | Aktiv, nicht pip-distributed |
| iil-content-store | — | 0 Consumer (Orphan) |
| iil-platform-search | — | 0 Consumer (Orphan) |
| iil-cad-services | — | 0 Consumer (Orphan) |
| iil-task-scorer | orchestrator_mcp (intern) | Aktiv, intern |
| iil-docs-agent | CLI-Tool | Aktiv, intern |
| iil-mcp-governance | mcp-hub (intern) | Aktiv, intern |
| iil-inception-mcp | mcp-hub (intern) | Aktiv, intern |

#### C) Sonderfälle

| Befund | Details |
|--------|---------|
| cad-hub `vendor/creative_services/` | Copy-Paste von iil-creative-services (~20 Files). Keine pip-Dependency, sondern vendored. |
| `riskfw` | Nur 1 Consumer (risk-hub). Nach "1-Consumer"-Regel: Inline-Kandidat. |
| `nl2cad-brandschutz` | Migriert nach risk-hub (b59155d). Nur noch cad-hub als Consumer. |

### Consumer-Analyse

| Package | Consumer-Count | Hubs |
|---------|---------------|------|
| iil-promptfw | 6 | risk, cad, trading, pptx, writing, bfagent |
| iil-authoringfw | 6 | risk, cad, trading, pptx, writing, bfagent |
| iil-aifw | 4 | risk, pptx, writing, bfagent |
| iil-platform-context | 4+ | risk, coach, billing, wedding |
| iil-django-tenancy | 4+ | risk, coach, billing, wedding |
| nl2cad-core | 2 | risk-hub, cad-hub |
| nl2cad-brandschutz | 1 | cad-hub (risk-hub migriert: b59155d) |
| riskfw | 1 | risk-hub |
| iil-cad-services | 0 | — |
| iil-platform-search | 0 | — |
| iil-content-store | 0 | — |
| iil-illustrationfw | 0 | — |

## Decision Drivers

- **Weniger Packages = weniger Wartung** (Releases, CVE-Updates, CI/CD)
- **Konsistentes Naming** für Developer Experience
- **Import-Pfad-Stabilität**: Python-Import-Pfade dürfen sich NICHT ändern
- **Extras steuern Drittanbieter-Deps**, nicht Code-Auslieferung
- **1-Consumer-Packages** gehören ins Consumer-Repo (kein separates Package)
- **0-Consumer-Packages** werden gelöscht oder depreciert
- **PyPI statt git+https** für reproduzierbare Builds
- **Kein PyPI Yank** — irreversibel, bricht Lockfiles. Stattdessen: Deprecation-Release.

## Considered Options

### Option A: Status quo beibehalten
- Pro: Kein Migrationsaufwand
- Contra: Wartungslast steigt weiter, Orphans bleiben

### Option B: Moderate Konsolidierung (34 → 26)
- Nur Orphans löschen, Redirects entfernen, 1-Consumer nach innen ziehen
- Pro: Geringes Risiko
- Contra: Strukturprobleme (nl2cad-Zersplitterung, Platform-Fragmentierung) bleiben

### Option C: Konsolidierung mit Umbrella-Packages (34 → 22) ✅
- nl2cad: 7 → 1 (Mono-Distribution, Extras für Drittanbieter-Deps)
- Platform: 5 pip-Packages → 1 Umbrella-Package (Sub-Packages bleiben intern)
- Domain: riskfw inline in risk-hub (1-Consumer-Regel)
- Orphans: alle entfernen
- Import-Pfade bleiben stabil
- Pro: −35% Reduktion, keine Breaking Imports
- Contra: Migrationsaufwand, Umbrella ist Meta-Package (Sub-Packages existieren weiter)

### Option D: Aggressiver Merge (v1-Ansatz, verworfen)
- Code-Merge von platform-context + django-commons + tenancy in ein Package
- Pro: Maximale Reduktion
- Contra: **Bricht 20+ Import-Pfade** in Consumer-Repos (`from platform_context`, `from django_tenancy`, `from iil_commons`). Python-Imports können nicht per pip umgeleitet werden. Widerspricht ADR-027 ohne adäquaten Ersatz.

## Decision Outcome

**Option C: Konsolidierung mit Umbrella-Packages (34 → 22)**

### Kernprinzipien

1. **Import-Pfade sind heilig**: `from platform_context import ...`, `from django_tenancy import ...`, `from nl2cad.areas import ...` — diese ändern sich NIE.
2. **pip-Name ≠ Import-Pfad**: Das pip-Distribution-Package darf anders heißen als der Python-Import.
3. **Extras steuern Drittanbieter-Deps**: `pip install nl2cad-core[gaeb]` installiert `lxml` dazu — der Code von `nl2cad.gaeb` wird IMMER mitgeliefert.
4. **Kein PyPI Yank**: Deprecation-Release mit `Development Status :: 7 - Inactive` statt Yank.

### Konsolidierungs-Map

#### Tier 1: Sofort löschen/deprecaten (Phase 1)

| Package | Aktion | Begründung |
|---------|--------|------------|
| `nl2cad` | Deprecation-Release | Redirect-Package, nutzlos |
| `iil-nl2cadfw` | Deprecation-Release | Meta-Package ohne eigenen Code |
| `nl2cad-brandschutz` | Deprecation-Release | Lebt jetzt in risk-hub (b59155d) |
| `iil-cad-services` | `git rm -r` (platform/packages/) | 0 Consumer |
| `iil-platform-search` | `git rm -r` (platform/packages/) | 0 Consumer |
| `iil-content-store` | `git rm -r` (platform/packages/) | 0 Consumer, supersedes ADR-130 |
| `iil-illustrationfw` | Repo archivieren (GitHub) | 0 Consumer |
| `iil-chat-logging` | Prüfen → ggf. `git rm -r` | Consumer-Check pending |
| `riskfw` | Inline in risk-hub/src/ | 1 Consumer (analog brandschutz-Migration) |

**Ergebnis: −8 bis −9 pip-distributed Packages**

#### Tier 2: nl2cad Mono-Distribution (Phase 2)

7 Packages → 1 Distribution-Package. **Aller Code wird IMMER mitgeliefert.**
Extras steuern nur Drittanbieter-Dependencies.

```toml
# nl2cad/packages/nl2cad-core/pyproject.toml
[project]
name = "nl2cad-core"
version = "0.2.0"
description = "NL2CAD — IFC/DXF parsing, DIN 277 areas, GAEB export, NLP intent"
requires-python = ">=3.11"

dependencies = [
    "ezdxf>=0.19",
]

[project.optional-dependencies]
ifc = ["ifcopenshell>=0.8"]     # Für IFC-Modell-Analyse
gaeb = ["lxml>=5.0"]            # Für GAEB X81-X85 XML
nlp = ["spacy>=3.7"]            # Für NL2CAD Intent-Erkennung
all = ["nl2cad-core[ifc,gaeb,nlp]"]

[tool.hatch.build.targets.wheel]
packages = ["src/nl2cad"]
```

Import-Pfade bleiben stabil:
```python
# VORHER und NACHHER — identisch
from nl2cad.core.models.ifc import IFCModel
from nl2cad.core.constants import FLUCHTWEG_KEYWORDS
from nl2cad.areas.din277 import DIN277Calculator
from nl2cad.gaeb.generator import GAEBGenerator
```

Consumer-Migration:
- `risk-hub`: `nl2cad-core[gaeb]>=0.2` (statt 3× git+https)
- `cad-hub`: `nl2cad-core[ifc,gaeb,nlp]>=0.2`

Compat-Redirect für Übergangszeit:
```toml
# nl2cad-areas/pyproject.toml — v0.2.0 (Compat)
[project]
name = "nl2cad-areas"
version = "0.2.0"
description = "DEPRECATED — use nl2cad-core>=0.2.0 instead"
classifiers = ["Development Status :: 7 - Inactive"]
dependencies = ["nl2cad-core>=0.2.0"]
```

**Ergebnis: −6 Packages (7→1)**

#### Tier 3: Platform Umbrella-Package (Phase 3)

**KEIN Code-Merge.** Import-Pfade bleiben stabil.
`iil-platform` ist ein Umbrella/Meta-Package das bestehende Packages bündelt.
Sub-Packages werden weiterhin in `platform/packages/` entwickelt und versioniert.

```toml
# platform/packages/iil-platform/pyproject.toml
[project]
name = "iil-platform"
version = "1.0.0"
description = "IIL Platform Foundation — Umbrella for Context, Commons, Tenancy"
requires-python = ">=3.11"

dependencies = [
    "iil-platform-context>=0.5.1",
    "iil-django-commons>=0.3.0",
    "iil-django-tenancy>=0.1.0",
]

[project.optional-dependencies]
shop = ["iil-django-module-shop>=0.2.0"]
notifications = ["iil-platform-notifications>=0.1.0"]
full = ["iil-platform[shop,notifications]"]
```

Import-Pfade bleiben stabil:
```python
# VORHER und NACHHER — identisch
from platform_context import context as pc
from platform_context.testing.assertions import assert_login_required
from django_tenancy.managers import TenantManager
from django_tenancy.module_models import ModuleSubscription
from iil_commons.health import liveness_check
from django_module_shop.catalogue import ModuleCatalogue
```

| VORHER (requirements.txt) | NACHHER |
|---------------------------|---------|
| 3–5 separate `git+https://` Einträge | `iil-platform[shop]>=1.0.0` |

Django-Apps mit Migrations (django_tenancy, django_module_shop) behalten ihren
`app_label`. Keine `MIGRATION_MODULES`-Anpassung nötig.

bfagent-interne Packages bleiben in `platform/packages/` — sie werden nicht per pip
verteilt und erzeugen keine Consumer-Wartungslast:

| Package | Verbleibt in | Begründung |
|---------|-------------|------------|
| iil-bfagent-core | platform/packages/ | Intern, nicht pip-distributed |
| iil-bfagent-llm | platform/packages/ | Intern, nicht pip-distributed |
| iil-chat-agent | platform/packages/ | bfagent + cad-hub (vendored) |
| iil-creative-services | platform/packages/ | cad-hub (vendored) |

**Ergebnis: Consumer sehen 1 Dependency statt 5, Sub-Packages existieren weiter intern**

#### Tier 4: Naming + git+https Cleanup (Phase 4)

| Aktion | Details |
|--------|---------|
| Alle `git+https://` eliminieren | Alle Sub-Packages auf PyPI publishen, Consumer auf PyPI-Pins migrieren |
| `iil-` Prefix konsequent | Alle pip-Packages tragen `iil-` Prefix. Ausnahme: `nl2cad-core` (eigene Marke). |
| INDEX.md aktualisieren | ADR-146 accepted, ADR-027 superseded |
| Package-Inventar | `platform/docs/guides/package-inventory.md` mit Consumer-Matrix |

### Ergebnis-Übersicht

| Kategorie | Vorher | Nachher | Details |
|-----------|--------|---------|---------|
| nl2cad | 7 | 1 | nl2cad-core (Mono-Distribution mit Extras) |
| AI/LLM | 3 | 3 | iil-aifw, iil-promptfw, iil-authoringfw |
| Platform (pip) | 5 | 1 | iil-platform (Umbrella, Sub-Packages intern) |
| Domain | 6 | 5 | learnfw, weltenfw, outlinefw, researchfw, brandschutzfw* |
| Shared Tools | 1 | 1 | iil-testkit |
| **pip-distributed** | **22** | **11** | **−50%** |
| Interne (platform/) | 12 | 8 | Orphans entfernt, Rest bleibt |
| **Gesamt** | **34** | **19** | **−44%** |

*riskfw wird in risk-hub/src/ integriert (1-Consumer-Regel, analog brandschutz).
*brandschutzfw wird erst bei cad-hub-Productionisierung als `iil-brandschutzfw` extrahiert.

## Migration Plan

### Vorbedingung: Alle Sub-Packages auf PyPI

Bevor `iil-platform` als Umbrella funktioniert, MÜSSEN alle Sub-Packages auf PyPI sein:

| Package | PyPI-Status | Aktion |
|---------|-------------|--------|
| iil-platform-context | Prüfen | Falls fehlt → Release 0.5.1 |
| iil-django-commons | 0.3.0 ✅ | Keine |
| iil-django-tenancy | Prüfen | Falls fehlt → Release 0.1.0 |
| iil-django-module-shop | Prüfen | Falls fehlt → Release 0.2.0 |
| iil-platform-notifications | Prüfen | Falls fehlt → Release 0.1.0 |

### Phase 1: Aufräumen (April 2026) — Risiko: Null

1. PyPI: Deprecation-Releases für `nl2cad`, `iil-nl2cadfw`, `nl2cad-brandschutz`
   (Classifier `Development Status :: 7 - Inactive`, leere Dependencies)
2. `platform/packages/`: `cad-services/`, `platform-search/`, `content-store/` entfernen
3. `iil-chat-logging`: Consumer-Check → falls 0 Consumer: entfernen
4. `illustration-fw/`: GitHub-Repo archivieren
5. `riskfw`: Code in risk-hub/src/riskfw/ integrieren (analog brandschutz-Migration b59155d)

**Rollback**: `git revert` des Lösch-Commits. Packages existieren weiter auf PyPI.

### Phase 2: nl2cad Mono-Distribution (Mai 2026) — Risiko: Mittel

1. nl2cad Mono-Repo: Code von areas, gaeb, nlp in nl2cad-core/src/nl2cad/ als Subpackages
2. nl2cad-core 0.2.0 mit `[ifc]`, `[gaeb]`, `[nlp]` Extras auf PyPI releasen
3. Import-Pfade verifizieren: `from nl2cad.areas.*`, `from nl2cad.gaeb.*` müssen funktionieren
4. Compat-Releases: nl2cad-areas 0.2.0 → `dependencies = ["nl2cad-core>=0.2"]`
5. risk-hub: `requirements.txt` → `nl2cad-core[gaeb]>=0.2` (statt 3× git+https)
6. cad-hub: `requirements.txt` → `nl2cad-core[ifc,gaeb,nlp]>=0.2`
7. 2 Wochen Prod-Betrieb abwarten
8. nl2cad-areas, nl2cad-gaeb, nl2cad-nlp: Deprecation-Releases auf PyPI

**Rollback**: git+https Einträge in requirements.txt wiederherstellen.

### Phase 3: iil-platform Umbrella (Juni–Juli 2026) — Risiko: Mittel

1. Sub-Packages auf PyPI publishen (Vorbedingung)
2. `platform/packages/iil-platform/` erstellen (pyproject.toml + README.md, kein Code)
3. `iil-platform 1.0.0` auf PyPI releasen
4. Consumer migrieren: risk-hub, coach-hub, billing-hub, wedding-hub
   (`iil-platform[shop]>=1.0` statt 3–5 einzelne Einträge)
5. 2 Wochen Prod-Betrieb abwarten
6. Alte Einzel-Einträge in Consumer-requirements.txt bereinigen

**Rollback**: Alte requirements.txt wiederherstellen (`git checkout requirements.txt`).

### Phase 4: Naming + Cleanup (Juli 2026) — Risiko: Niedrig

1. Alle verbleibenden `git+https://` Installs durch PyPI-Pins ersetzen
2. INDEX.md: ADR-146 → accepted, ADR-027 → superseded
3. `platform/docs/guides/package-inventory.md` erstellen
4. Finale Dokumentation

**Rollback**: pip install alte Versionen.

## Acceptance Criteria

1. **0 `git+https://`** in allen Hub requirements.txt
2. **0 Orphan-Packages** (0-Consumer) auf PyPI aktiv (alle auf `Inactive`)
3. **Alle Hub-CIs grün** nach Migration (risk, cad, coach, billing, wedding, bfagent, writing, trading, pptx, learn)
4. **Import-Pfade unverändert**: `platform_context`, `django_tenancy`, `iil_commons`, `django_module_shop`, `nl2cad.*`
5. **PyPI-Download-Count** der neuen Packages > 0
6. **Keine DeprecationWarning** in Prod-Logs nach 30 Tagen
7. **package-inventory.md** in platform/docs/guides/ aktuell

## Timeline

| Phase | Inhalt | Dauer | Deadline |
|-------|--------|-------|----------|
| 1 | Orphans + riskfw-Inline | 1–2 Wochen | April 2026 |
| 2 | nl2cad Mono-Distribution | 3–4 Wochen | Mai 2026 |
| 3 | iil-platform Umbrella | 4–6 Wochen | Juni–Juli 2026 |
| 4 | Naming + Cleanup | 2 Wochen | Juli 2026 |
| | **Gesamt** | **~4 Monate** | **Q3/2026** |

## Compliance Notes

- **Zero Breaking Imports**: Import-Pfade ändern sich nie. Nur pip-Distribution ändert sich.
- **Kein PyPI Yank**: Ausschließlich Deprecation-Releases mit `Inactive` Classifier.
- **ADR-022**: Konsistenz-Standard wird durch einheitliches Naming gestärkt
- **ADR-027**: Superseded — Umbrella-Approach als pragmatischer Kompromiss zwischen
  Einzelpackages (zu viele) und Monolith-Merge (bricht Imports)
- **ADR-050**: Hub-Landscape wird vereinfacht (weniger externe Dependencies)
- **CI/CD**: Weniger Package-Releases = weniger Pipeline-Durchläufe

## Risks and Mitigations

| Risiko | Impact | Mitigation |
|--------|--------|------------|
| Import-Bruch durch Code-Merge | Hoch | **KEIN Code-Merge** — Umbrella-Package statt Merge |
| Compat-Redirect bricht Imports | Hoch | Import-Pfade bleiben stabil, nur pip-Distribution ändert sich |
| PyPI Yank irreversibel | Mittel | Kein Yank — ausschließlich Deprecation-Releases |
| Sub-Packages nicht auf PyPI | Mittel | Phase 3 Vorbedingung: alle Sub-Packages publishen |
| Umbrella-Package zu gross | Niedrig | Umbrella hat keinen eigenen Code, nur Dependencies |
| Parallele Arbeit blockiert | Mittel | Phase 1 (Orphans) ist unabhängig, sofort machbar |
| Rollback nötig | Mittel | Jede Phase hat dokumentierte Rollback-Strategie |
| riskfw-Inline bricht Imports | Niedrig | Analog brandschutz-Migration (b59155d), bewährt |
