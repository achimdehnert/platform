---
description: Alle Workflows auf einen Blick — Trigger-Matrix, Entscheidungsbaum, Agent-Einstieg
mode: read-only
---

# Workflow Index — Platform Coding Agent System

> **Einstiegspunkt für jeden Agent.** Lese dieses Dokument wenn unklar ist, welcher Workflow passt.
> Dann `/session-start` ausführen (kanonischer Einstieg, ADR-233-konform).
>
> **Vollständigkeit ist erzwungen:** `tools/check_workflow_index.py` (CI, `tools-tests.yml`)
> prüft, dass **jeder** Skill aus `.windsurf/workflows/*.md` hier auftaucht oder bewusst
> auf der Allowlist steht. Neuer Skill ⇒ Zeile hier ergänzen, sonst rot.

---

## Trigger-Matrix: Welcher Workflow für welche Situation?

### Session-Lifecycle

| Situation | Slash-Command |
|-----------|---------------|
| **Session starten** (kanonisch, ADR-233-Worktree, Modell-Tier) | `/session-start` |
| Session beenden — Wissen sichern, Memory, committen/pushen | `/session-ende` |
| Session-Retrospektive (geerdet, adversarial → `docs/retros/`) | `/session-retro` |
| Session-Wissen in Outline sichern (Lessons, Runbooks) | `/knowledge-capture` |
| Repo-Reference-Doku generieren/syncen (README/CHANGELOG/API) | `/session-docu` |
| Task abschließen — Pflicht-Gate vor "COMPLETE" | `/complete` |
| Die 3 sinnvollsten nächsten Schritte fürs Repo | `/next` |
| Handoff fortsetzen / offene Issues weiterbearbeiten | `/issues-abarbeiten` |

### Coding-Flow

| Situation | Slash-Command |
|-----------|---------------|
| Neues Feature (complexity ≥ moderate) — voller Flow | `/agentic-coding` |
| Vor Implementierung: Annahmen/Contracts verifizieren | `/pre-code` |
| Governance vor Implementierung prüfen | `/governance-check` |
| Task headless planen → Issue → dann implementieren | `/claude-orchestrator` |
| Bug in Produktion — schneller Fix mit Safety Gates | `/hotfix` |
| Aufgabe an höheres Modell-Tier eskalieren | `/escalate` |
| Aus kurzer Anweisung einen lückenlosen Prompt bauen | `/prompt` |

### Review

| Situation | Slash-Command |
|-----------|---------------|
| PR reviewen / Kommentare adressieren | `/pr-review` |
| Automatisierter PR-Review gegen ADRs/Ruff/Bandit (ADR-100) | `/agent-review` |
| Alle Workflows reviewen + optimieren (Agent-Stabilität) | `/workflow-review` |

### ADR & Governance

| Situation | Slash-Command |
|-----------|---------------|
| ADR anlegen (MADR 4.0, Scope-Detection, pgvector) | `/adr` |
| ADR reviewen (Platform-Checkliste) | `/adr-review` |
| ADR Health Audit (Schema, Staleness, Freshness, Redundancy) | `/adr-health` |
| ADR-Fleet-Audit (Inventar, Cross-Repo-Konsistenz, Backlog — alle Repos) | `/adr-fleet-audit` |
| ADR adversarial challengen (Konflikte, Right-Sizing) | `/adr-challenger` |
| Kanonischen ADR zu einem Thema disambiguieren | `/adr-curator` |
| ADR-Zweitmeinung an externes LLM übergeben | `/adr-handoff-extern` |
| Use Case definieren (RUP/UML) | `/use-case` |
| Problem → entscheidungsreifes Konzept (T1/T2/T3) | `/konzept` |

### Repo-Onboarding & Setup

| Situation | Slash-Command |
|-----------|---------------|
| Repo technisch onboarden (Docker, CI/CD, DB, Nginx) | `/onboard-repo` |
| GitHub-Infra verankern (Issue Templates, ADR, Docs) | `/new-github-project` |
| Third-Party-Stack onboarden (Outline, Authentik, …) | `/onboard-stack` |
| Test-Infrastruktur einrichten (iil-testkit, ADR-058) | `/testing-setup` |
| project-facts.md aus platform-SSoT ins Repo pushen | `/sync-project-facts` |

### Repo-Optimierung & Qualität

| Situation | Slash-Command |
|-----------|---------------|
| Repo tief optimieren (Tech-Debt, Tests, LLM-Readiness) | `/repo-optimize` |
| Repo-UI/UX optimieren (Design-System, Klickdummy) | `/repo-ux-opt` |
| Readiness-Gate (Version aktiv + laufzeit-bereit) | `/repo-ready` |
| Repo/Package Vollständigkeit prüfen (Quality Gate) | `/repo-health-check` |
| Cross-Repo Audit (Schwachstellen, Inkonsistenzen) | `/platform-audit` |
| CI-Health-Konvergenz-Programm (ADR-209) | `/ci-green-program` |

### Testing

| Situation | Slash-Command |
|-----------|---------------|
| Kompletter Test-Run fürs Repo (Lint, Check, pytest) | `/teste-repo` |
| Test-Conventions prüfen vor Package-Release (T-01/02/03) | `/testing-conventions` |
| Pre-Release Frontend-Test (repo-agnostisch, kanonisch) | `/pre-release-test` |
| Frontend-UI-Test — **writing-hub-Spezialfall** (repo-hardcoded) | `/frontend-ui-test` |

### Deploy & Produktion

| Situation | Slash-Command |
|-----------|---------------|
| **App auf Prod deployen (Standard-Pfad)** | `/ship` |
| App auf Staging deployen (Dev Desktop) | `/ship-staging` |
| Prod-Deploy manueller Notfall-Handpfad (docker compose) | `/run-prod` |
| Lokale Docker-Umgebung starten + Health | `/run-local` |
| Staging deployen + verifizieren | `/run-staging` |
| Pre-Deploy-Verifikations-Checkliste | `/deploy-check` |
| Fehlgeschlagenes Deployment zurückrollen | `/rollback` |
| Prod-Incident triagieren → Route zu Fix/Rollback | `/incident` |

### Infra & Betrieb

| Situation | Slash-Command |
|-----------|---------------|
| Health aller deployten Services prüfen | `/infra-health` |
| Single-Pane-Infra-Übersicht (Ports, Drift) | `/infra-overview` |
| Host-Ressourcen sicher zurückgewinnen (Disk/Docker) | `/infra-cleanup` |
| Nginx-Configs auditieren (IPv6, SSL, Header) | `/nginx-check` |
| docker-compose.prod.yml gegen ADR-021 auditieren | `/compose-audit` |
| Config-Drift zwischen repos.json/ports.yaml/Server | `/drift-check` |
| DB-Backup für beliebige App | `/backup` |
| Uptime-Monitoring einrichten (Betterstack) | `/uptime-monitoring` |
| Stale Windsurf-Server-Prozesse killen | `/windsurf-clean` |
| GitHub-PAT erneuern (alle 3 Stellen + MCP-Restart) | `/refresh-github-token` |
| WSL ↔ GitHub ↔ Server synchronisieren | `/sync-repo` |

### Releases & Packages

| Situation | Slash-Command |
|-----------|---------------|
| Python-Package auf PyPI publizieren | `/release` |
| Third-Party-Stack upgraden (Outline, Authentik, …) | `/stack-upgrade` |

### Issues, Ideen & Queues

| Situation | Slash-Command |
|-----------|---------------|
| Offene Issues eines Repos / cross-repo triagieren + abarbeiten | `/issues-offen` |
| Auto-Issues (labels:auto) über Nacht abarbeiten | `/process-agent-queue` |
| Outline-Inbox: rohe Ideen erkennen + Template füllen | `/idea-intake` |
| Cascade-Aufträge aus Outline abarbeiten (Triage) | `/cascade-auftraege` |

### Dokumentation & Assets

| Situation | Slash-Command |
|-----------|---------------|
| README + CHANGELOG + Outline fürs aktuelle Repo | `/docu-update` |
| Reference-Docs fürs aktive Repo generieren | `/docu-repo-active` |
| Reference-Docs für ALLE Repos generieren | `/docu-repo-all` |
| Markdown → PDF (Design-Switcher meiki/iil/ttz) | `/create-pdf` |
| E-Mail mit Anhängen über Maschinen-SMTP versenden | `/send-mail` |

### Klickdummy & Secrets

| Situation | Slash-Command |
|-----------|---------------|
| Codebase → KD-Kandidaten + brownfield/greenfield-Entscheidung (read-only) | `/kd-scout` |
| Neuen Klickdummy anlegen (ADR-211 Cookbook) | `/klickdummy` |
| Gebauten KD verifizieren + UX-Kritik (Playwright + Subagent, ADR-251) | `/kd-review` |
| Cross-Repo-Klickdummy-Suche (pgvector) | `/klickdummy-search` |
| KD-Specs → pgvector upserten (Schreib-Konsument, KONZ-risk-hub-008) | `/klickdummy-pgvector-sync` |
| Secrets verwalten (rotieren, prüfen, anlegen) | `/secrets` |

### ⛔ Deprecated (nicht mehr als Einstieg verwenden)

| Alt-Skill | Kanonischer Ersatz |
|-----------|--------------------|
| `/agent-session-start` | `/session-start` (ADR-233-konform) |
| `/deploy` | `/ship` (Standard) · `/run-prod` (Notfall) |
| `/onboarding-new-repo` | `/onboard-repo` |

---

## Entscheidungsbaum: Was tue ich als nächstes?

```
Neue Session startet
        │
        ▼
/session-start  ← IMMER ZUERST (ADR-233-Worktree, Modell-Tier)
        │
        ├─ Aufgabe unklar? → Fragen stellen, ggf. /prompt für sauberen Auftrag
        │
        ├─ Bug in Produktion (kritisch)?
        │       └─ /incident → /hotfix oder /rollback
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
        │       └─ /adr  (BEVOR implementiert wird); Health-Check → /adr-health
        │
        ├─ Use Case / Konzept?
        │       └─ /use-case  bzw.  /konzept
        │
        ├─ PR reviewen?
        │       └─ /pr-review  (automatisiert: /agent-review)
        │
        ├─ Repo optimieren?
        │       ├─ breit (Tech-Debt/Tests) → /repo-optimize
        │       ├─ UI/UX → /repo-ux-opt
        │       ├─ nur nächste Schritte → /next
        │       └─ Quality-Gate vor Publish/Deploy → /repo-health-check
        │
        ├─ Testen?
        │       ├─ voller Test-Run → /teste-repo
        │       ├─ vor Package-Release → /testing-conventions
        │       └─ Frontend vor Freigabe → /pre-release-test
        │
        ├─ Gesamtüberblick / Schwachstellen-Analyse?
        │       └─ /platform-audit
        │
        ├─ Deployen?
        │       ├─ Pre-check → /deploy-check
        │       ├─ Standard → /ship   (Staging: /ship-staging)
        │       ├─ Notfall-Handpfad → /run-prod
        │       └─ Fehlgeschlagen → /rollback
        │
        └─ Session endet? → /session-ende (+ /knowledge-capture, /session-retro)
```

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
    └─ danach: /ship (nach Freigabe, kanonischer Prod-Deploy)

/ship
    └─ Gate davor: /deploy-check
    └─ Notfall-Alternative: /run-prod
    └─ bei Fehler: /rollback

/incident
    └─ routet zu: /hotfix, /rollback oder Stop

/stack-upgrade
    └─ ruft auf: /backup (Step 2)
    └─ danach: /knowledge-capture (Upgrade-Runbook)

/sync-repo
    └─ empfohlen: vor /session-start wenn multi-node
    └─ empfohlen: nach /ship wenn Server-Stand unklar

/platform-audit
    └─ nutzt: /repo-health-check (Checks pro Repo)
    └─ erzeugt: GitHub Issues (bei CRITICAL/HIGH)
    └─ empfohlen: 1× pro Woche
```

---

## Rollen-Matrix: Welcher Agent für was?

| Rolle | Aufgaben | Primärer Workflow |
|-------|----------|-------------------|
| **Developer** | Features, Bugfixes, Tests | `/agentic-coding`, `/hotfix` |
| **Tech Lead** | ADRs, Architecture Reviews, Re-Engineering | `/adr`, `/adr-review`, `/pr-review` |
| **Planner** | Use Cases, Konzepte, Task-Decomposition | `/use-case`, `/konzept`, `/agentic-coding` |
| **Guardian** | Linting, Security, Quality | eingebettet in `/agentic-coding`, `/agent-review` |
| **Infra** | Onboarding, Deployment, Health Checks | `/onboard-repo`, `/ship`, `/infra-health` |
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
13. Prod-Deploy braucht IMMER Freigabe (autonomy-gates Gate 2) — auch bei Routine
14. Branch Protection: qm-gate als required status check in main (ADR-174, alle Repos)
```

---

## Skill-Distribution (ADR-230, cc-skill-dist)

**SSoT ist diese Quelle:** `.windsurf/workflows/*.md` in `platform` (branch-stabil, `origin/main`).
Von hier werden die Live-Kopien deterministisch **generiert** — kein Handkopieren, keine Symlinks:

| Schritt | Werkzeug | Zweck |
|---------|----------|-------|
| Generieren | `tools/cc-skill-dist/generate.py` | `.windsurf/workflows/*.md` → flach nach `~/.claude/commands/` (CC-Slash-Commands), jede Kopie mit MANAGED-Footer (source_commit, content_hash) + `manifest.json`. Atomar (tmp→rename), deterministisch. |
| Drift prüfen | `tools/cc-skill-dist/doctor.py` | Read-only Diff Quelle ↔ Live-Ziel: stale Kopien, dangling Links, fehlende/zusätzliche Skills, **DRIFT-SCORE**. SUGGEST-Lint für `mcp<n>_`-Legacy-Tokens (nicht im Score). |
| Vollständigkeit | `tools/check_workflow_index.py` | Jeder Skill muss in **diesem** Index stehen (oder Allowlist) — CI-Gate in `tools-tests.yml`. |

> **Redistribution nach Merge** (`~/.claude/commands/` aktualisieren) läuft aktuell **manuell**
> via `generate.py --allow-live`; die Post-Merge-Automatik (CI-Job auf `push:main`, paths
> `.windsurf/workflows/**`, mit erzwungenem Dry-Run-Beweis gemäß Gate `autonomous-no-human-review`)
> ist noch offen (#901).
>
> Interne System-Prompt-Workflows (Frontmatter `distribute: false`, z. B. die
> `adr-handoff-extern-reviewer*`-Personas) werden **nicht** als Slash-Command verteilt und
> sind daher auch von der Index-Pflicht ausgenommen (Allowlist in `check_workflow_index.py`).

Governance: **ADR-230** (Coding nur über Claude Code; Windsurf = nur generiertes Review-Subset).

---

*Workflow Index v2.0 — Platform Coding Agent System | 2026-07-04*
*Alle Workflows: `${GITHUB_DIR:-$HOME/github}/platform/.windsurf/workflows/`*
