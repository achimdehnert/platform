# BF Agent Platform — Code Quality Tooling

> **Deliverable aus:** Odoo Standards Gap-Analyse (`odoo-standards-analyse.md`)
> **Phase:** 1 (Sofort-Maßnahmen) + 2 (CI-Integration)
> **Datum:** 2026-02-13
> **Status:** Review-Ready

---

## Übersicht

Dieses Paket implementiert die aus der Odoo-Analyse abgeleiteten Sofort-Maßnahmen
für Code-Qualität und Commit-Konventionen. Alle Dateien sind production-ready,
vollständig dokumentiert und können direkt ins Repository übernommen werden.

### Dateistruktur

```
deliverables/
├── README.md                           ← Diese Datei
├── .pre-commit-config.yaml             ← Zentrale Hook-Konfiguration
├── .gitleaksignore                     ← False-Positive-Liste für Secrets-Scan
├── pyproject-tooling.toml              ← Ruff + isort + pytest Config-Sektionen
├── scripts/
│   ├── check-commit-msg.sh             ← Commit-Message-Validator (Bash)
│   └── setup-dev-env.sh                ← Einmaliges Developer-Setup
└── .github/
    └── workflows/
        └── _ci-quality.yml             ← Reusable CI Workflow
```

### Mapping auf Analyse-Ergebnisse

| Analyse-Abschnitt | Deliverable | Enforcement |
|---|---|---|
| §2.2 Commit Message Standard | `check-commit-msg.sh` | pre-commit + CI |
| §2.3 Import-Ordering | `pyproject-tooling.toml` [isort] | ruff pre-commit |
| §2.4 Exception-Handling Policy | `pyproject-tooling.toml` [ruff.lint] | ruff B001/SIM105 |
| §4 Phase 1: Hook + CI | `.pre-commit-config.yaml` + `_ci-quality.yml` | Git + GitHub Actions |

---

## Installation (3 Schritte)

### 1. Dateien ins Repository kopieren

```bash
# Aus dem deliverables-Ordner ins Repo-Root
cp .pre-commit-config.yaml  /path/to/repo/
cp .gitleaksignore           /path/to/repo/
cp -r scripts/               /path/to/repo/scripts/
cp -r .github/               /path/to/repo/.github/

# pyproject-tooling.toml NICHT 1:1 kopieren — Sektionen mergen!
# Siehe Abschnitt "pyproject.toml Integration" unten.
```

### 2. pyproject.toml Integration

Die `pyproject-tooling.toml` enthält die Tool-Sektionen zum **Mergen**
in die bestehende `pyproject.toml`. Nicht als separate Datei verwenden.

```bash
# Manuell die folgenden Sektionen übertragen:
#   [tool.ruff]
#   [tool.ruff.format]
#   [tool.ruff.lint]
#   [tool.ruff.lint.per-file-ignores]
#   [tool.ruff.lint.isort]
#   [tool.pytest.ini_options]
#   [tool.mypy]  (optional)
```

**Hinweis zur Stable-File Preservation Rule:**
Bestehende Packages (z.B. `creative-services` mit `line-length=100`)
werden NICHT automatisch angepasst. Die neuen Werte gelten für neue
Packages. Migration bestehender Packages erfolgt separat und koordiniert.

### 3. Developer-Setup ausführen

```bash
cd /path/to/repo
chmod +x scripts/setup-dev-env.sh
./scripts/setup-dev-env.sh
```

Das Script installiert `pre-commit`, registriert alle Hooks und führt
einen initialen Testlauf durch.

---

## Commit-Message-Konvention

### Format

```
[TAG] modul: kurze beschreibung

Optionaler Body: Erkläre WARUM, nicht WAS.
Das Diff zeigt WAS geändert wurde.

Refs: ADR-009
Closes #123
```

### Erlaubte Tags

| Tag | Verwendung | Beispiel |
|---|---|---|
| `[FIX]` | Bug-Fix | `[FIX] travel-beat: prevent duplicate booking` |
| `[IMP]` | Verbesserung | `[IMP] mcp-hub: add retry logic` |
| `[REF]` | Refactoring | `[REF] creative-services: extract validator` |
| `[SEC]` | Security | `[SEC] platform-core: add RLS policy` |
| `[MIG]` | DB-Migration | `[MIG] bfagent: add genre FK` |
| `[ADR]` | Architecture Decision | `[ADR] platform: ADR-010 MCP Governance` |
| `[MOV]` | Dateien verschieben | `[MOV] bfagent: move to domain/` |
| `[REV]` | Revert | `[REV] travel-beat: revert booking flow` |
| `[REL]` | Release | `[REL] platform-core: v0.3.0` |
| `[DOC]` | Dokumentation | `[DOC] mcp-hub: add usage guide` |
| `[TST]` | Tests | `[TST] creative-services: add edge cases` |
| `[CI]` | CI/CD | `[CI] platform: add deploy workflow` |
| `[WIP]` | Work in Progress | Nur auf Feature-Branches! |

### Regeln

- Header: 15–72 Zeichen (inklusive Tag + Modul)
- Modul: lowercase, Bindestriche erlaubt (`travel-beat`, `mcp-hub`)
- Beschreibung: beginnt mit Kleinbuchstabe (Ausnahme: Akronyme)
- Zweite Zeile: immer leer (Trenner zum Body)
- Git-generierte Merge/Revert-Messages werden automatisch durchgelassen

---

## Hook-Übersicht

| Hook | Stage | Funktion | Auto-Fix? |
|---|---|---|---|
| trailing-whitespace | pre-commit | Whitespace entfernen | Ja |
| end-of-file-fixer | pre-commit | Newline am Dateiende | Ja |
| check-yaml/toml/json | pre-commit | Syntax-Validierung | Nein |
| check-added-large-files | pre-commit | Max 500 KB | Nein |
| no-commit-to-branch | pre-commit | Kein Push auf main | Nein |
| check-ast | pre-commit | Python Syntax | Nein |
| debug-statements | pre-commit | print/breakpoint finden | Nein |
| gitleaks | pre-commit | Secrets erkennen | Nein |
| ruff-check | pre-commit | Lint + Import-Sort | Ja (--fix) |
| ruff-format | pre-commit | Code-Formatierung | Ja |
| validate-pyproject | pre-commit | pyproject.toml Schema | Nein |
| bf-commit-msg | commit-msg | Message-Format | Nein |

---

## CI-Integration

Der Reusable Workflow `_ci-quality.yml` wird von App-Workflows aufgerufen:

```yaml
# In z.B. travel-beat/.github/workflows/ci.yml
jobs:
  quality:
    uses: achimdehnert/platform/.github/workflows/_ci-quality.yml@main
    with:
      python_version: "3.12"
      check_commits: true
    secrets: inherit
```

Er prüft:
1. Alle PR-Commits gegen das Commit-Message-Format
2. Ruff Lint mit GitHub-Annotations (inline im PR)
3. Ruff Format Check (Diff-Output bei Abweichungen)
4. Gitleaks Secret-Scan

---

## Versionen & Updates

| Tool | Version | Update-Befehl |
|---|---|---|
| pre-commit-hooks | v6.0.0 | `pre-commit autoupdate` |
| ruff-pre-commit | v0.15.0 | `pre-commit autoupdate` |
| gitleaks | v8.22.1 | `pre-commit autoupdate` |
| validate-pyproject | v0.23 | `pre-commit autoupdate` |

Empfehlung: `pre-commit autoupdate` monatlich ausführen und als
`[CI] platform: update pre-commit hook versions` committen.

---

## Review-Checkliste

- [ ] `.pre-commit-config.yaml` → Hook-Reihenfolge korrekt?
- [ ] `pyproject-tooling.toml` → Ruff-Regeln vollständig?
- [ ] `pyproject-tooling.toml` → `known-first-party` alle Platform-Packages?
- [ ] `check-commit-msg.sh` → Alle Tags enthalten?
- [ ] `check-commit-msg.sh` → Merge/Revert-Bypass funktioniert?
- [ ] `_ci-quality.yml` → Reusable Workflow Inputs korrekt?
- [ ] `.gitleaksignore` → Nur bekannte False Positives?
- [ ] `setup-dev-env.sh` → Funktioniert auf WSL + macOS?
