---
description: Alle Workflows auf einen Blick — Trigger-Matrix, Entscheidungsbaum, Agent-Einstieg
---

# Workflow Index — Platform Coding Agent System

> **Einstiegspunkt für jeden Agent.** Lese dieses Dokument wenn unklar ist, welcher Workflow passt.
> Dann `/agent-session-start` ausführen.

---

## Trigger-Matrix: Welcher Workflow für welche Situation?

| Situation | Workflow | Slash-Command |
|-----------|----------|---------------|
| Start jeder Session | Agent Session Start | `/agent-session-start` |
| Neues Feature implementieren | Agentic Coding | `/agentic-coding` |
| Bug in Produktion | Hotfix | `/hotfix` |
| PR reviewen / Kommentare adressieren | PR Review | `/pr-review` |
| Neues Repo komplett aufsetzen (Docker, CI/CD) | Repo Onboarding | `/onboard-repo` |
| GitHub-Infra in Repo verankern (Templates, Docs) | New GitHub Project | `/new-github-project` |
| ADR anlegen | ADR Creation | `/adr` |
| ADR reviewen | ADR Review | `/adr-review` |
| Use Case definieren | Use Case | `/use-case` |
| Governance vor Implementierung prüfen | Governance Check | `/governance-check` |
| **Repo/Package Vollständigkeit prüfen** | **Repo Health Check** | **`/repo-health-check`** |
| **Tests vor Package-Release prüfen** | **Testing Conventions** | **`/testing-conventions`** |
| **Cross-Repo Audit (Schwachstellen, Inkonsistenzen)** | **Platform Audit** | **`/platform-audit`** |
| Vor Production-Deploy | Deploy Check | `/deploy-check` |
| Deployen | Deploy | `/deploy` |
| DB-Backup | Backup | `/backup` |
| Windsurf-Verbindung tot | Windsurf Clean | `/windsurf-clean` |
| Tests einrichten (neues Repo) | Testing Setup | `/testing-setup` |
| Third-Party Stack upgraden (Outline, Authentik, Paperless) | Stack Upgrade | `/stack-upgrade` |
| WSL ↔ GitHub ↔ Server synchronisieren | Sync Repo | `/sync-repo` |
| **Vor Implementierung: Annahmen verifizieren** | **Pre-Code Contract Verification** | **`/pre-code`** |
| **Neues Django-App Scaffold** | **New Django App** | **`/new-django-app`** |
| **Pre-Release Frontend Test** | **Pre-Release Test** | **`/pre-release-test`** |
| **Automatisierter Frontend UI Test** | **Frontend UI Test** | **`/frontend-ui-test`** |
| **App auf Production deployen (full flow)** | **Ship** | **`/ship`** |
| **Lokale Docker-Umgebung starten** | **Run Local** | **`/run-local`** |
| **Production deployen (safety gates)** | **Run Prod** | **`/run-prod`** |
| **Staging deployen + Health Check** | **Run Staging** | **`/run-staging`** |
| **Dokumentation aktualisieren** | **Docu Update** | **`/docu-update`** |

---

## Entscheidungsbaum: Was tue ich als nächstes?

```
Neue Session startet
        │
        ▼
/agent-session-start  ← IMMER ZUERST
        │
        ├─ Aufgabe unklar? → Fragen stellen, dann:
        │
        ├─ Bug in Produktion (kritisch)?
        │       └─ /hotfix
        │
        ├─ Neues Repo aufsetzen?
        │       ├─ Technisch (Docker, CI/CD) → /onboard-repo
        │       └─ Docs/Templates (Issue Forms, ADR, UC) → /new-github-project
        │
        ├─ Feature / Refactoring / Task?
        │       ├─ complexity >= moderate → /pre-code, /governance-check, /agentic-coding
        │       └─ complexity trivial/simple → direkt implementieren (Service Layer!)
        │
        ├─ Architektur-Entscheidung nötig?
        │       └─ /adr  (BEVOR implementiert wird)
        │
        ├─ Use Case definieren?
        │       └─ /use-case
        │
        ├─ PR reviewen?
        │       └─ /pr-review
        │
        ├─ Unvollständige Angaben / fehlende Dateien gemeldet?
        │       └─ /repo-health-check
        │
        ├─ Vor Package-Release / nach Test-Failures?
        │       └─ /testing-conventions
        │
        ├─ Third-Party Stack upgraden?
        │       └─ /stack-upgrade  (Outline, Authentik, Paperless)
        │
        ├─ Repos synchronisieren (WSL / GitHub / Server)?
        │       └─ /sync-repo
        ├─ Vor Feature-Implementierung: Annahmen absichern?
        │       └─ /pre-code  (Contract Verification)
        ├─ Neues Django-App anlegen?
        │       └─ /new-django-app
        ├─ Frontend vor Release testen?
        │       └─ /pre-release-test
        │
        ├─ Gesamtüberblick / Schwachstellen-Analyse?
        │       └─ /platform-audit
        │
        ├─ Deployen?
        │       ├─ Pre-check → /deploy-check
        │       └─ Ausführen → /deploy
        │
        └─ Session endet? → AGENT_HANDOVER.md aktualisieren
```

---

## Workflow-Beschreibungen (Kurzform)

### `/agent-session-start`
Pflicht-Ritual. Lädt CORE_CONTEXT + AGENT_HANDOVER, klärt Aufgabe, prüft Git-Status, erstellt Arbeitsplan. **Niemals überspringen.**

### `/agentic-coding`
Vollständiger Coding-Flow: Governance → Task-Template → Planner → Router → Ausführung → Guardian → Quality → PR → Audit. Für complexity >= moderate.

### `/hotfix`
Schneller Produktions-Fix ohne Overhead. Gate 0 (Root-Cause-Pflicht), minimaler Fix, Regression-Test, sofort deployen. Nur für echte Produktionsfehler.

### `/pr-review`
Strukturiertes Code-Review nach Platform-Conventions. Checkliste: Architektur, Code-Qualität, Tests, Deployment. Kommentar-Format: [BLOCK]/[SUGGEST]/[QUESTION]/[NITS].

### `/onboard-repo`
Vollständiges technisches Onboarding: Projektstruktur, CI/CD, Docker, Health-Endpoints, Server-Infrastruktur, Nginx, SSL, Platform-Integration.

### `/new-github-project`
Dokumentations- und Template-Infrastruktur: Issue Forms (Bug/Feature/Task/UC), PR-Template, Labels, CORE_CONTEXT, AGENT_HANDOVER, ADR-Template, UC-Template, Perfect Prompt, Governance.

### `/adr` / `/adr-review`
ADR anlegen (MADR 4.0, Scope-Detection, Multi-Repo) oder reviewen (Checkliste: Kontext, Alternativen, Konsequenzen, Compliance).

### `/use-case`
Use Case nach RUP/UML-Standard: Steckbrief → Dok-Datei → GitHub Issue → Index. Für alle user-facing Features.

### `/governance-check`
Prüft vor Implementierung: Existiert Komponente bereits? LLM/DB/Zugriff korrekt (aifw, ORM, TextChoices)? HTMX-Detection-Typ (repo-spezifisch). ADR-Verletzungen scannen.

### `/repo-health-check`
Verbindlicher Vollständigkeits-Check für Repos/Packages. Profile: `python-package` + `django-app`. BLOCK-Items müssen alle grün sein. Maschinenausführbar: `tools/repo_health_check.py`. **Pflicht bei jedem neuen Package/Repo und wenn unvollständige Angaben gemeldet werden.**

### `/testing-conventions`
Prüft Test-Files auf die 3 häufigsten Fehler-Patterns vor Package-Release: T-01 `pytest.importorskip` für optionale Deps, T-02 `AsyncMock(side_effect=)` statt `wraps=`, T-03 `pytest.raises()` für Exception-Contracts. **Pflicht vor jedem `git tag vX.Y.Z`.**

### `/deploy-check`
Pre-Deploy Gate: Tests grün, CI grün, Migrations gecheckt, Env aktuell, Post-Deploy Health-Check.

### `/deploy`
Production-Deploy via GitHub Actions (infra-deploy). Read-ops via deployment-mcp, Write-ops IMMER via GitHub Actions.

### `/backup`
DB-Backup für beliebige App.

### `/windsurf-clean`
Stale Windsurf-Server-Prozesse killen wenn SSH-Reconnect fehlschlägt.

### `/testing-setup`
Test-Infrastruktur nach ADR-058: platform_context[testing], conftest, factories, pyproject.toml.

### `/stack-upgrade`
Standardisiertes Upgrade für Third-Party Docker-Stacks: Backup → Pull → Compose Update → Verify → Cleanup. Getestet mit Outline 0.82→1.6, anwendbar auf Authentik, Paperless.

### `/platform-audit`
Cross-Repo Schwachstellen-Analyse: Scannt ALLE 7 Repos + Infrastruktur. 5 Phasen: Repo-Scan → Architektur-Konsistenz → Infra-Health → Analyse → Report. Generiert priorisierten Audit-Report (CRITICAL/HIGH/MEDIUM/LOW), sichert in Outline, erstellt optional GitHub Issues. Empfohlen: 1× pro Woche.

### `/sync-repo`
3-Node-Sync: WSL ↔ GitHub ↔ Server konsistent halten. Vor und nach jeder Session ausführen wenn Code auf mehreren Nodes bearbeitet wurde.

---

## Workflow-Abhängigkeiten

```
/onboard-repo
    └─ ruft auf: /testing-setup (Step 1.6)
    └─ ruft auf: /repo-health-check (Step 1.0 — vor allem anderen)
    └─ ergänzt durch: /new-github-project (Docs/Templates)

/agentic-coding
    └─ Phase 0: /pre-code (Contract Verification)
    └─ Step 0: /governance-check
    └─ braucht: GitHub Issue-Nummer (= task_id für Audit-Calls)
    └─ bei Architektur-Entscheidung: /adr

/hotfix
    └─ schnellere Variante von: /agentic-coding
    └─ danach: /deploy (sofort)

/deploy
    └─ Gate davor: /deploy-check
    └─ bei Fehler: Rollback via deploy-rollback.yml

/new-github-project
    └─ ergänzt: /onboard-repo (nicht ersetzt)
    └─ braucht: /adr für ersten echten ADR

/stack-upgrade
    └─ ruft auf: /backup (Step 2)
    └─ danach: /knowledge-capture (Upgrade-Runbook)

/sync-repo
    └─ empfohlen: vor /agent-session-start wenn multi-node
    └─ empfohlen: nach /deploy wenn Server-Stand unklar

/platform-audit
    └─ nutzt: /repo-health-check (Checks pro Repo)
    └─ nutzt: deployment-mcp (Infra Health)
    └─ erzeugt: GitHub Issues (bei CRITICAL/HIGH)
    └─ speichert: Outline Konzept + platform/audits/
    └─ empfohlen: 1× pro Woche
```

---

## Rollen-Matrix: Welcher Agent für was?

| Rolle | Aufgaben | Primärer Workflow |
|-------|----------|-------------------|
| **Developer** | Features, Bugfixes, Tests | `/agentic-coding`, `/hotfix` |
| **Tech Lead** | ADRs, Architecture Reviews, Re-Engineering | `/adr`, `/adr-review`, `/pr-review` |
| **Planner** | Use Cases, Task-Decomposition | `/use-case`, `/agentic-coding` Step 2 |
| **Guardian** | Linting, Security, Quality | Eingebettet in `/agentic-coding` Step 6+7 |
| **Re-Engineer** | Rollback-Handling, Refactoring | `/agentic-coding` Step 4b |
| **Infra** | Onboarding, Deployment, Health Checks | `/onboard-repo`, `/new-github-project`, `/deploy`, `/repo-health-check` |
| **QA** | Test-Conventions, Release-Gates | `/testing-conventions`, `/repo-health-check` |

---

## Non-Negotiable Rules (immer, egal welcher Workflow)

```
1.  CORE_CONTEXT.md lesen BEVOR Code geändert wird
2.  Service Layer: views → services → models (nie überspringen)
3.  BigAutoField — niemals UUID als Primary Key (public_id = UUIDField für externe Refs erlaubt)
4.  Templates: src/templates/<app>/ (nicht per-app)
5.  Secrets: nur via decouple.config() / env_file
6.  Tests: test_should_* Naming, min. 1 per Feature
7.  Zero Breaking Changes: erst deprecaten
8.  AGENT_HANDOVER.md am Session-Ende aktualisieren
9.  Destructive Actions: IMMER zuerst fragen
10. MANDATORY: HEALTHCHECK in jedem Dockerfile (--interval=30s --timeout=10s --retries=3)
11. /repo-health-check IMMER vor erstem Publish oder Deploy eines neuen Repos
12. /testing-conventions IMMER vor git tag vX.Y.Z (Package-Release)
    → T-01: pytest.importorskip() für opt. Deps
    → T-02: AsyncMock(side_effect=) statt wraps=
    → T-03: pytest.raises() für Exception-Contracts
```

---

## Symlink-Policy (ADR-174)

**Regel: Symlink DEFAULT — Lokal NUR bei repo-spezifischem Inhalt.**

| Typ | Strategie | Beispiele |
|-----|-----------|-----------|
| **Platform-global** | Symlink → Änderung in `platform/` wirkt sofort überall | `agentic-coding.md`, `governance-check.md`, `pre-code.md`, `workflow-index.md`, `platform-audit.md`, `adr.md`, `hotfix.md`, `deploy.md` |
| **Repo-spezifisch** | Lokal → repo-eigene Befehle/Pfade/ADRs | `complete.md`, `agent-task.md`, `run-tests.md` |

**Neue Workflow-Datei anlegen:**
```bash
# 1. In platform/ erstellen
# 2. Symlink in Ziel-Repo:
ln -s ../../../platform/.windsurf/workflows/<name>.md .windsurf/workflows/<name>.md

# Verify: alle Symlinks im Repo prüfen
find .windsurf/workflows/ -type l -exec ls -la {} \;
```

**Aktueller Stand risk-hub:**
```
SYMLINK: agentic-coding.md, governance-check.md, pre-code.md,
         platform-audit.md, workflow-index.md
LOKAL:   complete.md, agent-task.md, run-tests.md,
         agent-session-start.md, session-start.md, session-ende.md
```

> Neue Workflows bei `/onboard-repo` immer als Symlink anlegen.
> Lokal-Entscheidung in `AGENT_HANDOVER.md` des Repos dokumentieren.

---

*Workflow Index v1.5 — Platform Coding Agent System | 2026-04-29*
*Alle Workflows: `${GITHUB_DIR:-$HOME/github}/platform/.windsurf/workflows/`*
