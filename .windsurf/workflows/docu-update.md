---
description: Dokumentation aktualisieren — README + CHANGELOG + Outline für aktuelles Repo (Layer B)
---

# /docu-update

> **Ergänzt** `/docu-repo-active` (Layer A: Reference-Docs) und `/session-docu` (DIATAXIS-Audit).
> Fokus: Layer B — menschenlesbare Deliverables für externe Reviews, Product Owner, neue Team-Mitglieder.
> Trigger: vor externem Review, nach Release, nach neuen Modulen/Commands.

---

## Scope bestimmen

```bash
REPO_NAME=$(basename $(git rev-parse --show-toplevel 2>/dev/null))
REPO_PATH=$(git rev-parse --show-toplevel 2>/dev/null)
echo "Repo: $REPO_NAME @ $REPO_PATH"
```

Repo-Klasse (ADR-163) ermitteln:
- **Tier 1** (Full Django App): hat `apps/`, `manage.py`, UC-Docs
- **Tier 2** (Light Django App): hat `apps/` oder `manage.py`, keine UC-Docs
- **Tier 3** (Package/Infra): hat `pyproject.toml`, kein `manage.py`

---

## Phase 0: Ist-Stand erfassen

```bash
# Version
grep -r '__version__\|^version' "$REPO_PATH/pyproject.toml" 2>/dev/null | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1

# Module / Struktur
ls "$REPO_PATH/reflex/"*.py 2>/dev/null || ls "$REPO_PATH/src/"**/*.py 2>/dev/null || ls "$REPO_PATH/"apps/ 2>/dev/null | head -10

# Letzte Commits
git log --oneline -10

# Tests
python -m pytest tests/ --collect-only -q 2>/dev/null | tail -3
```

→ Notiere: `VERSION`, `TIER`, `LAST_CHANGES`, `TEST_COUNT`

---

## Phase 1: README.md — Qualitäts-Checkliste

Prüfe diese Punkte für das jeweilige Tier:

### Alle Tiers
- [ ] **Version** korrekt (= `__version__` in Code / `pyproject.toml`)
- [ ] **Zweck** klar beschrieben (1-2 Sätze)
- [ ] **Installation** vollständig (alle extras/pip-Optionen)
- [ ] **Keine Phantom-Commands** — alle CLI-Commands müssen in `__main__.py` existieren
- [ ] **Architektur-Block** vollständig (alle Module/Apps)

### Tier 1 + 2 (Django Apps)
- [ ] **Deployment** beschrieben (Server, Port, Docker)
- [ ] **Konfiguration** (`reflex.yaml`, `.env`) dokumentiert
- [ ] **Screenshot** oder UI-Beschreibung vorhanden

### Tier 3 (Packages)
- [ ] **API-Beispiele** im README (Quick Start)
- [ ] **Dependencies-Tabelle** aktuell (alle extras)
- [ ] **Outline-Links** in Documentation-Tabelle

Falls Korrekturen nötig → README.md editieren.

---

## Phase 2: CHANGELOG.md — Inhalt prüfen

```bash
head -20 "$REPO_PATH/CHANGELOG.md"
```

Prüfe:
- [ ] Datei vorhanden (falls nicht: erstellen mit `# Changelog\n\nFormat: Keep a Changelog`)
- [ ] Mindestens ein Eintrag `[X.Y.Z] — YYYY-MM-DD` vorhanden (nicht leer)
- [ ] Letzter Eintrag deckt letzte commits ab?
- [ ] Kein `[Unreleased]` wenn Version released

Falls leer oder veraltet → Eintrag ergänzen basierend auf `git log --oneline -20`.

---

## Phase 3: Outline-Eintrag prüfen + anlegen/updaten

### Tier 3 (Packages) — Funktionsbeschreibung

Suche ob bereits ein Eintrag existiert:
```
mcp3_search_knowledge(query: "<REPO_NAME> Funktionsbeschreibung")
```

Falls nicht vorhanden → `mcp3_create_concept()` mit:
- Überblick + Zweck
- Modul-Tabelle (alle .py Dateien mit Klassen)
- Installation (extras)
- Dependencies
- Test-Coverage

### Tier 1 (Django Apps) — Hub-Dokumentation

Suche ob bereits ein Eintrag existiert:
```
mcp3_search_knowledge(query: "<REPO_NAME> Hub Dokumentation Setup")
```

Falls nicht vorhanden → `mcp3_create_runbook()` mit:
- Lokales Setup
- Deployment
- Konfiguration
- Wichtige URLs

### Alle Tiers — Platform-Übersicht updaten

→ `mcp3_update_document(document_id: "432db075-9b4d-4222-9223-36c57452fc26", ...)`
  Status für dieses Repo von ❌ auf ✅ setzen.

---

## Phase 4: Für externe Reviews — Review Package

Falls ein externer Review angefragt ist:

Prüfe ob ein Review Package existiert:
```
mcp3_search_knowledge(query: "<REPO_NAME> Review Package Deliverable")
```

Falls nicht → `mcp3_create_concept()` nach Vorlage von iil-reflex:
→ [iil-reflex Review Package](https://knowledge.iil.pet/doc/iil-reflex-review-package-deliverable-aBPs3xOqHG)

Das Review Package enthält:
- Kurzübersicht (Version, Tests, Lizenz)
- Dokumenten-Navigator (Links für verschiedene Reviewer-Typen)
- Modul/Feature-Übersicht
- Qualitäts-Metriken
- Bekannte Einschränkungen

---

## Phase 5: Commit + Push

```bash
git add README.md CHANGELOG.md
git diff --cached --stat
git commit -m "docs(<REPO_NAME>): update README + CHANGELOG to v<VERSION>"
git push
```

---

## Checkliste (muss alles grün sein vor Review)

| # | Check | Tier |
|---|-------|------|
| 1 | README.md Version = Code-Version | alle |
| 2 | README.md keine Phantom-Commands/Features | alle |
| 3 | README.md Architektur vollständig | alle |
| 4 | README.md Dependencies aktuell | alle |
| 5 | CHANGELOG.md hat mindestens 1 Eintrag | alle |
| 6 | Outline-Eintrag vorhanden | Tier 1+3 |
| 7 | Platform-Übersicht aktualisiert | alle |
| 8 | Review Package vorhanden | wenn Review |
| 9 | git status clean, gepusht | alle |

---

## Trigger-Matrix

| Ereignis | /docu-update nötig? |
|---|---|
| Externer Review angefragt | ✅ sofort |
| `version` erhöht | ✅ |
| Neue `.py` Datei / neues Modul | ✅ |
| Neues CLI-Command | ✅ |
| Neuer `[extra]` in pyproject.toml | ✅ |
| Bug-Fix ohne API-Änderung | ❌ |
| session-ende ohne Code-Änderung | ❌ |

---

## Ergänzende Workflows

| Workflow | Wann zusätzlich | Was |
|----------|----------------|-----|
| `/docu-repo-active` | nach Code-Änderungen | models/api/config Reference-Docs generieren |
| `/session-docu` | 1x/Monat | DIATAXIS Health Score, Docstring-Coverage |

---

## Platform-Übersicht (Outline)

[Platform Repo-Übersicht](https://knowledge.iil.pet/doc/platform-repo-ubersicht-alle-repos-tier-doku-status-ZERnrvmfvS)
[Platform Doku-Governance Konzept](https://knowledge.iil.pet/doc/platform-doku-governance-konzept-fur-alle-40-repos-zQ15xhbQnd)
[Referenz-Implementierung: iil-reflex Review Package](https://knowledge.iil.pet/doc/iil-reflex-review-package-deliverable-aBPs3xOqHG)
