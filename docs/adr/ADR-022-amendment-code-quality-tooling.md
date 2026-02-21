---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-022 Amendment: Code Quality Tooling

| Metadata    | Value |
| ----------- | ----- |
| **Status**  | Proposed |
| **Date**    | 2026-02-13 |
| **Author**  | Achim Dehnert |
| **Amends**  | ADR-022 v3 (Platform Consistency Standard) |
| **Related** | ADR-010 (MCP Tool Governance), ADR-009 (Deployment Architecture) |
| **Origin**  | Odoo Standards Gap-Analyse, Phase 1 + 2 |

---

## 1. Context

ADR-022 v3 standardisiert **Infrastruktur** (Dockerfiles, Compose, Health-Endpoints,
CI/CD Workflows). Es fehlt die **Code-Quality-Schicht**: Linting, Formatting,
Commit-Konventionen, Security-Scanning und Developer-Tooling.

Eine Gap-Analyse gegen Odoo Git Guidelines und Community Best Practices ergab:

| Dimension | IST-Zustand | Problem |
| --------- | ----------- | ------- |
| Linting | Kein Standard | Jedes Repo eigener Stil oder gar keiner |
| Formatting | Kein Standard | Inkonsistente Einrückung, Zeilenlänge |
| Imports | Unsortiert | Keine Import-Gruppen-Trennung |
| Commit Messages | `feat:`, `fix:` (Conventional) | Kein Modulname, keine Enforcement |
| Security Scan | Nicht vorhanden | API-Keys können committed werden |
| Pre-commit | Nicht vorhanden | Qualität erst in CI sichtbar, nicht lokal |

### 1.1 Warum jetzt?

- ADR-010 definiert Governance-Standards für MCP-Tools — Code Quality ist das Fundament
- Odoo-Integration (ADR-029) erfordert einheitliche Standards über Framework-Grenzen
- 5+ Repos mit wachsendem Team brauchen automatische Konsistenz

---

## 2. Decision

Wir ergänzen ADR-022 um **6 verbindliche Code-Quality-Deliverables**, die als
kanonische Templates in `platform/docs/adr/inputs/` liegen:

| # | Deliverable | Datei | Zweck |
| - | ----------- | ----- | ----- |
| Q1 | Ruff Config | `pyproject-tooling.toml` | Linting + Formatting + Import-Sortierung |
| Q2 | Pre-Commit Hooks | `.pre-commit-config.yaml` | Lokale Enforcement vor Commit |
| Q3 | Commit Message Validator | `check-commit-msg.sh` | `[TAG] module: description` Format |
| Q4 | CI Quality Workflow | `_ci-quality.yml` | Reusable Workflow für PR-Checks |
| Q5 | Gitleaks Config | `.gitleaksignore` | Secret-Scan mit False-Positive-Liste |
| Q6 | Dev Setup Script | `setup-dev-env.sh` | Einmaliges Hook-Setup pro Entwickler |

### 2.1 Commit Message Standard

Format: `[TAG] module: kurze beschreibung`

```text
[FIX] travel-beat: prevent duplicate booking on race condition
[IMP] mcp-hub: add retry logic to llm_mcp tool calls
[MIG] bfagent: add genre FK replacing string field
[SEC] platform-core: add RLS policy for tenant isolation
```

**Erlaubte Tags** (14):

| Tag | Zweck | Tag | Zweck |
| --- | ----- | --- | ----- |
| `FIX` | Bug fix | `IMP` | Improvement |
| `REF` | Refactoring | `SEC` | Security |
| `MIG` | DB Migration | `ADR` | Architecture Decision |
| `MOV` | Move files | `REV` | Revert |
| `REL` | Release | `DOC` | Documentation |
| `TST` | Tests | `CI` | CI/CD |
| `MERGE` | Merge commit | `WIP` | Work in Progress (Feature-Branches only) |

**Regeln:**
- Header: 15-72 Zeichen (inkl. Tag + Modul)
- Modul: lowercase, Bindestriche erlaubt (`travel-beat`, `mcp-hub`)
- Beschreibung: beginnt mit Kleinbuchstabe (Ausnahme: Akronyme wie Django, RLS)
- Zweite Zeile: immer leer (Trenner zum Body)
- Merge/Revert-Messages von Git werden automatisch durchgelassen

**Herkunft:** Adaptiert von Odoo Git Guidelines, erweitert um `SEC`, `MIG`, `ADR`,
`DOC`, `TST`, `CI`, `WIP`.

### 2.2 Ruff Konfiguration

Ruff ersetzt: flake8, isort, black, pyupgrade, bandit (teilweise).

**Kern-Parameter:**

| Parameter | Wert | Begründung |
| --------- | ---- | ---------- |
| `line-length` | 120 | Django/Odoo-Community Standard |
| `target-version` | `py312` | Aktuelle Platform-Python-Version |
| `quote-style` | `double` | PEP 8 Empfehlung |

**Aktivierte Regel-Sets:**

| Prefix | Quelle | Prüft |
| ------ | ------ | ----- |
| `E`, `W` | pycodestyle | Einrückung, Whitespace |
| `F` | pyflakes | Unbenutzte Imports, undefined names |
| `I` | isort | Import-Sortierung (4 Gruppen) |
| `N` | pep8-naming | Class/function/variable Naming |
| `B` | flake8-bugbear | Bare except, mutable defaults |
| `SIM` | flake8-simplicity | Ternary, contextlib.suppress |
| `UP` | pyupgrade | Moderne Python-Syntax |
| `RUF` | Ruff-eigene | Unicode, mutable class vars |
| `S` | flake8-bandit | Security Patterns |
| `DJ` | flake8-django | Null on CharField, locals() in render |

**Import-Sortierung** (4-Gruppen-Regel):

```python
# Gruppe 1: Standard Library
from pathlib import Path

# Gruppe 2: Third-Party
from django.db import models
from pydantic import BaseModel

# Gruppe 3: Platform Packages
from mcp_governance.spec import ToolSpec

# Gruppe 4: Local App
from .models import Story
```

**Per-File-Ignores:**
- `*/migrations/*.py`: E501, N, RUF012 (auto-generiert)
- `*/tests/*.py`: S101, S105, S106 (assert + test fixtures)
- `*/management/commands/*.py`: T201 (print erlaubt)
- `**/settings/*.py`: F403, F405 (wildcard imports)

**Stable-File Preservation Rule:** Bestehende Packages mit abweichender Config
(z.B. `creative-services` mit `line-length=100`) werden NICHT automatisch
angepasst. Neue Packages nutzen die Standard-Werte. Migration bestehender
Packages erfolgt separat und koordiniert.

### 2.3 Pre-Commit Hook Chain

Ausführungsreihenfolge (wichtig):

| # | Hook | Stage | Auto-Fix? | Quelle |
| - | ---- | ----- | --------- | ------ |
| 1 | trailing-whitespace | pre-commit | Ja | pre-commit-hooks v6.0.0 |
| 2 | end-of-file-fixer | pre-commit | Ja | pre-commit-hooks |
| 3 | check-yaml/toml/json | pre-commit | Nein | pre-commit-hooks |
| 4 | check-added-large-files (500KB) | pre-commit | Nein | pre-commit-hooks |
| 5 | check-merge-conflict | pre-commit | Nein | pre-commit-hooks |
| 6 | no-commit-to-branch (main) | pre-commit | Nein | pre-commit-hooks |
| 7 | check-ast | pre-commit | Nein | pre-commit-hooks |
| 8 | debug-statements | pre-commit | Nein | pre-commit-hooks |
| 9 | gitleaks | pre-commit | Nein | gitleaks v8.22.1 |
| 10 | ruff-check --fix | pre-commit | Ja | ruff v0.15.0 |
| 11 | ruff-format | pre-commit | Ja | ruff v0.15.0 |
| 12 | validate-pyproject | pre-commit | Nein | validate-pyproject v0.23 |
| 13 | bf-commit-msg | commit-msg | Nein | Lokal (check-commit-msg.sh) |

### 2.4 CI Quality Workflow

Reusable Workflow `_ci-quality.yml` in `platform/.github/workflows/`:

```yaml
jobs:
  quality:
    uses: achimdehnert/platform/.github/workflows/_ci-quality.yml@main
    with:
      python_version: "3.12"
      ruff_version: "0.15.0"
      check_commits: true
    secrets: inherit
```

**3 Jobs:**
1. **Commit Messages** — Alle PR-Commits gegen Format prüfen (nur bei PRs)
2. **Ruff Lint & Format** — `ruff check --output-format=github` + `ruff format --check`
3. **Secret Detection** — Gitleaks Scan auf neue Commits

### 2.5 Security: Gitleaks

- Pre-commit: Scannt staged files vor jedem Commit
- CI: Scannt alle neuen Commits im PR
- `.gitleaksignore`: Nur dokumentierte False Positives
- Jeder Eintrag MUSS begründet sein (Kommentar)

---

## 3. Migration Plan

### Phase 1: Platform-Repo (Sofort)

1. `_ci-quality.yml` nach `platform/.github/workflows/` kopieren
2. `pyproject-tooling.toml` Sektionen in `platform/pyproject.toml` mergen
3. `.pre-commit-config.yaml` ins Platform-Root
4. `scripts/check-commit-msg.sh` + `scripts/setup-dev-env.sh` ins Platform-Root
5. `.gitleaksignore` ins Platform-Root
6. `setup-dev-env.sh` ausführen

### Phase 2: Pilot-Repos (1 Woche)

Reihenfolge nach Risiko (niedrigstes zuerst):

| # | Repo | Aufwand | Besonderheit |
| - | ---- | ------- | ------------ |
| 1 | travel-beat | 15 min | Bereits CI @v1, nur Quality-Job ergänzen |
| 2 | risk-hub | 15 min | Bereits CI @v1, nur Quality-Job ergänzen |
| 3 | weltenhub | 20 min | Hybrid CI, Quality-Job parallel einführen |
| 4 | bfagent | 30 min | Eigene Workflows, schrittweise migrieren |
| 5 | pptx-hub | 20 min | PyPI-fokussiert, Quality-Job ergänzen |

**Pro Repo:**
1. `.pre-commit-config.yaml` + `scripts/` + `.gitleaksignore` kopieren
2. Ruff-Sektionen in `pyproject.toml` mergen
3. CI Workflow: `_ci-quality.yml` als Job einbinden
4. `setup-dev-env.sh` ausführen
5. Initialen `ruff check --fix` + `ruff format` Commit machen

### Phase 3: Enforcement (2 Wochen)

1. Branch Protection: Quality-Jobs als Required Checks
2. Commit-Message-Check als Required Check in PRs
3. Ruff-Format-Check als Required Check
4. Dokumentation: `CONTRIBUTING.md` pro Repo aktualisieren

---

## 4. Rejected Alternatives

### A: Black + isort + flake8 (separat)

- 3 Tools, 3 Configs, 3 Versionen → Wartungsaufwand
- Ruff ist 10-100x schneller und vereint alle drei
- Ruff hat bessere IDE-Integration

### B: Conventional Commits (`feat:`, `fix:`)

- Kein Modulname → bei 7+ Repos unklar welches Modul betroffen
- Keine Tags für MIG, SEC, ADR → Platform-spezifische Bedürfnisse
- Odoo-Format ist bewährt und in der Python/Django-Community verbreitet

### C: Sofortige Migration aller bestehenden Dateien

- Würde massive Git-Blame-Pollution verursachen
- Stable-File Preservation Rule respektiert bestehenden Code
- Schrittweise Migration bei Gelegenheit (wenn Datei ohnehin geändert wird)

### D: mypy als Required Check

- Zu viele bestehende Type-Fehler in Legacy-Code
- Optional in `pyproject-tooling.toml` vorbereitet
- Schrittweise Einführung pro Modul empfohlen

---

## 5. Compliance-Checkliste (Erweiterung zu ADR-022 §8)

Zusätzlich zur bestehenden ADR-022 Checkliste:

```text
[ ] .pre-commit-config.yaml basiert auf inputs/.pre-commit-config.yaml
[ ] scripts/check-commit-msg.sh vorhanden und ausführbar
[ ] scripts/setup-dev-env.sh vorhanden und ausführbar
[ ] .gitleaksignore vorhanden
[ ] pyproject.toml enthält [tool.ruff] Sektionen aus inputs/pyproject-tooling.toml
[ ] CI Workflow bindet _ci-quality.yml ein
[ ] Ruff-Check und Ruff-Format laufen erfolgreich (ruff check . && ruff format --check .)
[ ] Alle Commits im PR folgen [TAG] module: description Format
```

---

## 6. Tool-Versionen

| Tool | Version | Update-Zyklus |
| ---- | ------- | ------------- |
| Ruff | 0.15.0 | `pre-commit autoupdate` monatlich |
| pre-commit-hooks | v6.0.0 | `pre-commit autoupdate` monatlich |
| Gitleaks | v8.22.1 | `pre-commit autoupdate` monatlich |
| validate-pyproject | v0.23 | `pre-commit autoupdate` monatlich |

Update-Commit: `[CI] platform: update pre-commit hook versions`

---

## 7. Consequences

### Positive

- **Einheitlicher Code-Stil** über alle Repos via Ruff
- **Automatische Enforcement** lokal (pre-commit) + CI (GitHub Actions)
- **Security-by-Default** durch Gitleaks vor jedem Commit
- **Aussagekräftige Git-History** durch strukturierte Commit Messages
- **Onboarding**: `setup-dev-env.sh` → fertig in 30 Sekunden
- **Synergie mit ADR-010**: ToolSpecs und Governance-Code folgen dem gleichen Standard
- **Keine manuelle Review-Arbeit** für Stil-Fragen

### Negative

- **Initialer Aufwand**: ~2h für alle 5 Repos (einmalig)
- **Lernkurve**: Commit-Message-Format erfordert Gewöhnung
- **False Positives**: Gitleaks kann Test-Fixtures flaggen → `.gitleaksignore`
- **Pre-commit Overhead**: ~2-5 Sekunden pro Commit (Ruff ist schnell)

### Neutral

- Bestehender Code wird NICHT automatisch reformatiert (Stable-File Rule)
- mypy bleibt optional (vorbereitet aber nicht enforced)
- `[WIP]` Commits nur auf Feature-Branches (kein Block auf main)

---

## 8. Changelog

| Datum | Änderung |
| ----- | -------- |
| 2026-02-13 | Initial: Amendment proposed based on Odoo Gap-Analyse |
