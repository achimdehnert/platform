# ADR-146 Implementierungsplan (nach Review v1)

> **Datum**: 2026-03-25
> **Basis**: ADR-146-review.md Findings (2B, 3K, 5H, 4M)
> **Korrigiertes Ziel**: 34 → 22 Packages (−35%)

---

## Vorbedingung: ADR-146 v2 schreiben

Bevor Implementierung beginnt, ADR-146 überarbeiten:

| Finding | Fix im ADR |
|---------|-----------|
| B1 (Inventar falsch) | Korrigiertes Inventar: 22 pip-distributed + 12 intern |
| B2 (ADR-027 Widerspruch) | `supersedes: ["ADR-027"]` + Begründung: "Erfahrung zeigt dass 11 Einzelpackages zu hohe Wartungslast erzeugen; Umbrella-Approach als Kompromiss" |
| K1 (Import-Bruch) | Tier 3: Umbrella-Package statt Merge. Import-Pfade bleiben. |
| K2 (Extras ≠ Code) | Tier 2: Mono-Distribution, Extras nur für Drittanbieter-Deps |
| K3 (Compat-Redirect limitiert) | Migration Plan: Import-Pfade bleiben stabil, nur pip-Name ändert sich |
| H5 (Akzeptanz-Kriterien) | Section "Acceptance Criteria" ergänzen |

---

## Phase 0: ADR Housekeeping (Tag 1)

### 0.1 ADR-146 v2 committen

```
platform/docs/adr/ADR-146-package-consolidation-strategy.md
  → Findings einarbeiten (s.o.)
  → review_status: "reviewed — 14 findings, v2 addresses all"
  → supersedes: ["ADR-027-shared-backend-services.md"]
```

### 0.2 ADR-130 prüfen

```bash
# Prüfen ob iil-content-store in ADR-130 referenziert wird
grep -r "content.store\|content_store" platform/docs/adr/ADR-130*.md
# Falls ja: ADR-130 Status → "superseded by ADR-146"
```

### 0.3 Akzeptanz-Kriterien definieren

```markdown
## Acceptance Criteria

1. Kein `git+https://` mehr in requirements.txt (alle Hubs)
2. 0 Orphan-Packages (0-Consumer) auf PyPI aktiv
3. Alle Hub-CIs grün nach Migration
4. Import-Pfade unverändert (kein `from iil_platform` o.ä.)
5. PyPI-Download-Count der neuen Packages > 0
6. Keine `DeprecationWarning` in Prod-Logs nach 30 Tagen
```

---

## Phase 1: Orphans entfernen (Woche 1–2) — Risiko: Null

### 1.1 PyPI Deprecation Notices

| Package | Aktion | Letzte Version |
|---------|--------|----------------|
| `nl2cad` | Final Release mit "DEPRECATED" in README + Description | 0.3.0 |
| `iil-nl2cadfw` | Final Release mit "DEPRECATED" | 0.2.0 |
| `nl2cad-brandschutz` | Final Release: "Migrated to risk-hub, use brandschutz app" | 0.2.0 |

**KEIN PyPI Yank** — Yank ist irreversibel und bricht bestehende Lockfiles.
Stattdessen: Deprecation-Release mit `classifiers = ["Development Status :: 7 - Inactive"]`.

### 1.2 Deprecation-Release Template

```toml
# pyproject.toml für deprecated Package
[project]
name = "nl2cad-brandschutz"
version = "0.2.0"
description = "DEPRECATED — migrated to risk-hub brandschutz app. Do not use."
classifiers = [
    "Development Status :: 7 - Inactive",
]
dependencies = []  # Keine Abhängigkeiten mehr

[project.urls]
"Migration Guide" = "https://github.com/achimdehnert/risk-hub/blob/main/src/brandschutz/README.md"
```

### 1.3 platform/packages/ aufräumen

```bash
# Dateien
platform/packages/cad-services/       → git rm -r
platform/packages/platform-search/    → git rm -r
platform/packages/content-store/      → git rm -r

# Commit
git commit -m "chore: remove orphan packages (ADR-146 Phase 1)

Removed 0-consumer packages:
- iil-cad-services (0 imports anywhere)
- iil-platform-search (0 imports anywhere)
- iil-content-store (ADR-130 superseded)
"
```

### 1.4 illustration-fw Repo archivieren

```bash
# GitHub: Settings → Archive repository
# achimdehnert/illustration-fw → archived
```

### 1.5 Verifizierung Phase 1

```bash
# Alle Hub-CIs müssen weiter grün sein (keine Dependency auf gelöschte Packages)
for repo in risk-hub cad-hub coach-hub bfagent; do
    echo "=== $repo ==="
    grep -rn "cad.services\|platform.search\|content.store\|illustrationfw" \
        /home/dehnert/github/$repo/ --include="*.py" --include="*.txt" --include="*.toml" \
        2>/dev/null | grep -v __pycache__ | grep -v .venv
done
# Erwartung: 0 Treffer
```

**Rollback**: `git revert` des Lösch-Commits. Packages existieren weiter auf PyPI.

---

## Phase 2: nl2cad Mono-Distribution (Woche 3–6) — Risiko: Mittel

### 2.1 Zielstruktur

```
nl2cad/packages/nl2cad-core/
├── pyproject.toml          # name = "nl2cad-core", version = "0.2.0"
├── src/nl2cad/
│   ├── __init__.py
│   ├── core/               # Bestehender Code (IFC/DXF Parser)
│   │   ├── __init__.py
│   │   ├── models/
│   │   ├── constants.py
│   │   └── ...
│   ├── areas/              # ← Code aus nl2cad-areas hierher
│   │   ├── __init__.py
│   │   ├── din277.py
│   │   └── woflv.py
│   ├── gaeb/               # ← Code aus nl2cad-gaeb hierher
│   │   ├── __init__.py
│   │   ├── generator.py
│   │   └── converter.py
│   └── nlp/                # ← Code aus nl2cad-nlp hierher
│       ├── __init__.py
│       ├── intent.py
│       └── nl2dxf.py
└── tests/
```

### 2.2 pyproject.toml

```toml
[project]
name = "nl2cad-core"
version = "0.2.0"
description = "NL2CAD — IFC/DXF parsing, DIN 277 areas, GAEB export, NLP intent"
requires-python = ">=3.11"

dependencies = [
    "ezdxf>=0.19",
]

[project.optional-dependencies]
ifc = ["ifcopenshell>=0.8"]
gaeb = ["lxml>=5.0"]
nlp = ["spacy>=3.7"]
all = ["nl2cad-core[ifc,gaeb,nlp]"]
dev = [
    "pytest>=8.0",
    "ruff>=0.5",
]

[tool.hatch.build.targets.wheel]
packages = ["src/nl2cad"]
```

### 2.3 Import-Pfad-Kompatibilität

**KRITISCH**: Bestehende Imports MÜSSEN weiter funktionieren:

```python
# VORHER (muss weiter funktionieren)
from nl2cad.core.models.ifc import IFCModel
from nl2cad.core.constants import FLUCHTWEG_KEYWORDS
from nl2cad.areas.din277 import DIN277Calculator
from nl2cad.gaeb.generator import GAEBGenerator

# Keine Änderung nötig — Code liegt jetzt nur in einem Package
```

### 2.4 Compat-Releases (alte Packages)

Für jedes alte Package eine letzte Version die auf nl2cad-core verweist:

```toml
# nl2cad-areas/pyproject.toml — v0.2.0 (Compat-Redirect)
[project]
name = "nl2cad-areas"
version = "0.2.0"
description = "DEPRECATED — use nl2cad-core>=0.2.0 instead"
classifiers = ["Development Status :: 7 - Inactive"]
dependencies = ["nl2cad-core>=0.2.0"]
```

### 2.5 Consumer-Migration

```diff
# risk-hub/requirements.txt
- nl2cad-core @ git+https://github.com/achimdehnert/nl2cad.git#subdirectory=packages/nl2cad-core
- nl2cad-areas @ git+https://github.com/achimdehnert/nl2cad.git#subdirectory=packages/nl2cad-areas
- nl2cad-gaeb @ git+https://github.com/achimdehnert/nl2cad.git#subdirectory=packages/nl2cad-gaeb
+ nl2cad-core[gaeb]>=0.2.0
```

```diff
# cad-hub/requirements.txt
- nl2cad-core[ifc]>=0.1.0,<1.0
- nl2cad-areas>=0.1.0,<1.0
- nl2cad-gaeb>=0.1.0,<1.0
- nl2cad-nlp>=0.1.0,<1.0
+ nl2cad-core[ifc,gaeb,nlp]>=0.2.0
```

### 2.6 Verifizierung Phase 2

```bash
# 1. nl2cad-core 0.2.0 lokal testen
cd nl2cad/packages/nl2cad-core
pip install -e ".[all]"
python -c "from nl2cad.core.models.ifc import IFCModel; print('core OK')"
python -c "from nl2cad.areas.din277 import DIN277Calculator; print('areas OK')"
python -c "from nl2cad.gaeb.generator import GAEBGenerator; print('gaeb OK')"
pytest tests/ -x

# 2. risk-hub mit neuem Package testen
cd /home/dehnert/github/risk-hub
pip install nl2cad-core[gaeb]>=0.2.0
pytest tests/ --ignore=tests/e2e -x

# 3. cad-hub mit neuem Package testen
cd /home/dehnert/github/cad-hub
pip install "nl2cad-core[ifc,gaeb,nlp]>=0.2.0"
pytest tests/ -x
```

**Rollback-Bedingung**: Wenn EINER der Consumer-Tests fehlschlägt → git+https beibehalten,
nl2cad-core 0.2.0 von PyPI entfernen (yank ist hier OK da neu).

### 2.7 Deprecation (erst nach 2 Wochen ohne Fehler)

```bash
# Erst NACH erfolgreicher Consumer-Migration + 2 Wochen Prod-Betrieb:
# Compat-Releases publishen für: nl2cad-areas, nl2cad-gaeb, nl2cad-nlp
# nl2cad und iil-nl2cadfw → Final Deprecation Release
```

---

## Phase 3: Platform Umbrella-Package (Woche 7–12) — Risiko: Mittel

### 3.1 Strategie: Umbrella statt Merge

**KEIN Code-Merge.** Import-Pfade bleiben stabil.
`iil-platform` ist ein Meta-Package das bestehende Packages bündelt.

### 3.2 Neues Package

```
platform/packages/iil-platform/
├── pyproject.toml
└── README.md
```

```toml
# platform/packages/iil-platform/pyproject.toml
[project]
name = "iil-platform"
version = "1.0.0"
description = "IIL Platform Foundation — Umbrella package for all platform infrastructure"
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

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 3.3 Consumer-Migration

```diff
# risk-hub/requirements.txt
- iil-platform-context>=0.5.0
- iil-django-module-shop>=0.2.0
- iil-django-tenancy>=0.1.0
+ iil-platform[shop]>=1.0.0
```

```diff
# billing-hub/requirements.txt
- iil-django-commons[cache] @ git+https://...
+ iil-platform>=1.0.0
```

```diff
# coach-hub/requirements.txt
- django-module-shop @ git+https://...#subdirectory=packages/django-module-shop
+ iil-platform[shop]>=1.0.0
```

### 3.4 Vorbedingung: Alle Sub-Packages auf PyPI

Aktuell werden einige Packages per `git+https://` installiert. Bevor `iil-platform`
funktioniert, MÜSSEN alle Sub-Packages auf PyPI sein:

| Package | PyPI Status | Aktion |
|---------|-------------|--------|
| iil-platform-context | Prüfen | Falls fehlt → Release 0.5.1 |
| iil-django-commons | 0.3.0 ✅ | Keine |
| iil-django-tenancy | Prüfen | Falls fehlt → Release 0.1.0 |
| iil-django-module-shop | Prüfen | Falls fehlt → Release 0.2.0 |
| iil-platform-notifications | Prüfen | Falls fehlt → Release 0.1.0 |

### 3.5 bfagent-interne Packages

Packages die NUR von bfagent/cad-hub genutzt werden und nicht per pip installiert
sind → bleiben wo sie sind, werden nicht migriert:

| Package | Aktion | Begründung |
|---------|--------|------------|
| iil-bfagent-core | Bleibt in platform/packages/ | Genutzt, aber intern |
| iil-bfagent-llm | Bleibt in platform/packages/ | Genutzt, aber intern |
| iil-chat-agent | Bleibt in platform/packages/ | bfagent + cad-hub vendor |
| iil-chat-logging | Prüfen: Consumer? Falls 0 → löschen | Evtl. Orphan |
| iil-creative-services | Bleibt in platform/packages/ | cad-hub vendor |

### 3.6 Verifizierung Phase 3

```bash
# 1. iil-platform lokal bauen
cd platform/packages/iil-platform
pip install -e ".[full]"
python -c "from platform_context import context; print('platform_context OK')"
python -c "from iil_commons.health import liveness_check; print('commons OK')"
python -c "from django_tenancy.managers import TenantManager; print('tenancy OK')"

# 2. Alle Consumer-Repos testen
for repo in risk-hub coach-hub billing-hub wedding-hub; do
    echo "=== $repo ==="
    cd /home/dehnert/github/$repo
    pip install -r requirements.txt
    pytest tests/ --ignore=tests/e2e -x
done
```

**Rollback**: Alte requirements.txt wiederherstellen (`git checkout requirements.txt`).

---

## Phase 4: Naming + Cleanup (Woche 13–14) — Risiko: Niedrig

### 4.1 riskfw Entscheidung

**Aus Review H2**: Nur umbenennen wenn riskfw perspektivisch von >1 Hub genutzt wird.
Falls nur risk-hub → in risk-hub/src/ integrieren (wie brandschutz-Migration).

**Option A** (Rename — wenn multi-Hub):
```toml
name = "iil-riskfw"
version = "0.2.0"
```
+ Compat-Release `riskfw==0.2.0` mit `dependencies = ["iil-riskfw>=0.2.0"]`

**Option B** (Inline — empfohlen bei 1 Consumer):
```bash
# Code nach risk-hub/src/riskfw/ kopieren
# requirements.txt: riskfw entfernen
# Gleiche Strategie wie brandschutz-Migration
```

### 4.2 git+https → PyPI Pins eliminieren

Alle verbleibenden `git+https://` Installs durch PyPI-Versionen ersetzen.
Vorbedingung: Alle Packages auf PyPI released.

### 4.3 INDEX.md aktualisieren

```
platform/docs/adr/INDEX.md
  → ADR-146 Status: "accepted"
  → ADR-027 Status: "superseded by ADR-146"
  → ADR-130 Status: "superseded by ADR-146" (falls content-store referenziert)
```

### 4.4 Package-Inventar erstellen

```
platform/docs/guides/package-inventory.md
  → Vollständiges Inventar aller aktiven Packages
  → Consumer-Matrix (wer nutzt was)
  → Naming-Konventionen (iil-* für pip, Ausnahme nl2cad-core)
```

---

## Timeline (korrigiert nach Review M4)

| Phase | Inhalt | Dauer | Deadline |
|-------|--------|-------|----------|
| 0 | ADR v2 + Housekeeping | 1 Tag | Sofort |
| 1 | Orphans entfernen | 1–2 Wochen | April 2026 |
| 2 | nl2cad Mono-Distribution | 3–4 Wochen | Mai 2026 |
| 3 | iil-platform Umbrella | 4–6 Wochen | Juni–Juli 2026 |
| 4 | Naming + Cleanup | 2 Wochen | Juli 2026 |
| | **Gesamt** | **~4 Monate** | **Q3/2026** |

---

## Risiko-Matrix (pro Phase)

| Phase | Risiko | Impact | Rollback |
|-------|--------|--------|----------|
| 1 | Null | Nur Orphans | git revert |
| 2 | Mittel | 2 Consumer (risk-hub, cad-hub) | git+https wiederherstellen |
| 3 | Mittel | 4 Consumer + PyPI-Publish nötig | Alte requirements.txt |
| 4 | Niedrig | 1 Package (riskfw) | pip install riskfw==0.1.0 |

---

## Erfolgskriterien (Definition of Done)

- [ ] 0 `git+https://` in allen Hub requirements.txt
- [ ] 0 Orphan-Packages (0-Consumer) auf PyPI aktiv (nur Inactive)
- [ ] Alle Hub-CIs grün (risk, cad, coach, billing, wedding, bfagent, writing, trading, pptx, learn)
- [ ] Import-Pfade unverändert (`platform_context`, `django_tenancy`, `iil_commons`, `nl2cad.*`)
- [ ] Keine `DeprecationWarning` in Prod-Logs nach 30 Tagen
- [ ] package-inventory.md in platform/docs/guides/ aktuell
- [ ] ADR-146 Status: accepted, implementation_status: implemented
