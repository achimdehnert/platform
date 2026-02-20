---
id: ADR-054
title: "Deployment Pre-Flight Validation & platform-context als Managed Package"
status: draft
date: 2026-02-20
author: Achim Dehnert
scope: platform
repo: platform
tags: [deployment, ci-cd, platform-context, pre-flight, dx, onboarding]
relates_to: ADR-021, ADR-022, ADR-042, ADR-045, ADR-053
---

# ADR-054: Deployment Pre-Flight Validation & platform-context als Managed Package

## Metadata

| Feld | Wert |
|------|------|
| **Status** | Draft |
| **Scope** | platform |
| **Repo** | platform |
| **Erstellt** | 2026-02-20 |
| **Relates to** | ADR-021, ADR-022, ADR-042, ADR-045, ADR-053 |

## Context

Empirische Analyse der Trading-Hub Deployment-Session (20.02.2026) ergab **9 Workflow-Runs
für 1 erfolgreiches Deployment** — Ersterfolgquote: 0%. Gesamtzeitverlust: ~43 Minuten.

### Fehlerverteilung nach Kategorie

```
PERMISSION (allowed_actions: local_only)  ████████████████████  56% (5/9)
BUILD (fehlende Cross-Repo-Dependencies)  ████████             22% (2/9)
WORKFLOW (Reusable + normale Jobs gemischt) ████████           22% (2/9)
```

### Identifizierte Fehlerklassen

| Klasse | Symptom | Root Cause |
|--------|---------|------------|
| **A: PERMISSION** | `startup_failure`, 0 Jobs, keine Logs | `allowed_actions: local_only` im GitHub Repo — wird nie vor dem ersten Run geprüft |
| **B: DEPENDENCY** | `ModuleNotFoundError` im Test-Step | `platform_context` nicht im CI verfügbar (absoluter lokaler Pfad in `pyproject.toml`); `bfagent-core` im Dockerfile referenziert obwohl nicht im Repo |
| **C: WORKFLOW** | `startup_failure` trotz valider YAML | Reusable Workflows + normale Jobs gemischt; `inputs.*` bei Push-Trigger undefined |
| **D: DRIFT** | `502 Bad Gateway`, Backup-Fehler | Nginx `proxy_pass 127.0.0.1` statt `46.225.113.1`; fehlende `.env.prod`-Variablen |

### Systemische Schwachstellen

Das bestehende `deploy-remote.sh` validiert Server-seitige Voraussetzungen (Compose-File,
Env-File, Docker-Daemon), aber **keine GitHub-seitigen Voraussetzungen** vor dem ersten Run.
Es gibt keinen Onboarding-Prozess für neue Apps — jedes neue Repo reproduziert dieselben
Fehlerklassen manuell.

`platform_context` ist ein shared Package, das alle Apps brauchen, aber:
- Nicht als PyPI/GHCR-Package publiziert
- Im CI nicht verfügbar (absoluter Dev-Server-Pfad)
- Wird per `wheels/`-Kopier-Pattern vendored — bricht bei jedem neuen Repo

## Decision

### M1: Reusable Pre-Flight Workflow (`_preflight-check.yml`)

Ein neuer `workflow_call`-Workflow wird als Pflicht-`needs:`-Dependency vor allen
Deploy-Workflows eingefügt. Er prüft vor dem ersten Run:

```yaml
checks:
  github:
    - allowed_actions != "local_only"  # via GitHub API
    - required secrets vorhanden (HETZNER_HOST, HETZNER_SSH_KEY, GHCR_TOKEN)
    - workflow file syntaktisch valide (actionlint)
  docker:
    - Dockerfile existiert am angegebenen Pfad
    - Keine COPY-Referenzen auf nicht-existierende Verzeichnisse
    - Image-Name in Compose matcht Build-Output
  server:
    - SSH-Verbindung zum Deploy-Server möglich
    - deploy_path existiert (/opt/<app>/)
    - .env.prod vorhanden und enthält Pflichtfelder
    - Nginx proxy_pass auf 46.225.113.1 (nicht 127.0.0.1)
  dependencies:
    - Keine absoluten lokalen Pfade in pyproject.toml/requirements.txt
    - Keine Cross-Repo COPY-Referenzen im Dockerfile
```

**Integration:** Als erster Job in `_deploy-hetzner.yml` via `needs: [preflight]`.

### M2: App-Onboarding-Checkliste als GitHub Issue Template

`/.github/ISSUE_TEMPLATE/new-app-onboarding.yml` mit Pflicht-Checkboxen für alle
Deployment-Voraussetzungen — verhindert Wiederholung der Fehlerklassen A und D.

### M3: Inline-Workflow-Templates statt Reusable Workflows für neue Apps

Composite Actions für wiederverwendbare Steps (gleiche Permissions wie aufrufender Workflow).
Reusable Workflows nur bei identischen Owner-Permissions oder öffentlichen Repos.

### M4: `platform_context` als Managed Package (GHCR)

`platform_context` wird als versioniertes Package über GHCR publiziert:

```bash
# Statt wheels/ in jedem Repo:
pip install platform-context==0.2.0 \
  --extra-index-url https://ghcr.io/achimdehnert/platform
```

- Eigene CI-Pipeline in `platform`-Repo: Test → Build → Publish zu GHCR
- Alle Consumer-Repos: `wheels/`-Block im Dockerfile entfernen
- Semantic Versioning mit `PLATFORM_CONTEXT_VERSION` in `.env.prod`

## Consequences

### Positive
- Pre-Flight verhindert ~78% aller bisherigen Fehlversuche **vor dem ersten Run**
- Ersterfolgquote steigt von 0% auf >85% (Ziel)
- `platform_context` als echtes Package: einheitlicher Upgrade-Pfad, kein Wheel-Rebuild
- `_preflight-check.yml` ist selbst Reusable → einmalige Pflege für alle 11 Repos
- Onboarding-Checkliste macht Voraussetzungen explizit und prüfbar

### Negative
- M4 erfordert Breaking Change in Dockerfiles aller 11 Repos (koordinierter Rollout)
- GHCR-Auth für `pip install` in Docker Build-Phase nötig (Build-ARG `GHCR_TOKEN`)
- Pre-Flight erhöht Workflow-Laufzeit um ~60s pro Deploy
- `allowed_actions`-Check benötigt PAT mit `repo`-Scope im CI

## Alternatives Considered

| Alternative | Pro | Contra | Entscheidung |
|------------|-----|--------|-------------|
| Nur README-Checkliste | Null Aufwand | Wird nicht befolgt, löst nichts | Abgelehnt |
| `wheels/` beibehalten + bessere Doku | Kein Breaking Change | Fehler wiederholt sich bei jedem neuen Repo | Abgelehnt |
| `platform_context` via PyPI (public) | Einfachste Installation | Proprietärer Code öffentlich | Abgelehnt |
| Pre-Flight nur in `deploy-remote.sh` | Server-nah | Zu spät — Image muss bereits gebaut sein | Abgelehnt |
| Self-Hosted Runner (M7) | Kein SSH/SCP nötig, Cache | Runner-Wartung, Security-Isolation | Zurückgestellt (P3) |
| GitOps mit ArgoCD/Flux (M8) | Audit-Trail, Auto-Rollback | Hoher Initialaufwand, lohnt erst ab >10 Apps | Zurückgestellt (Q3/Q4) |

## Implementation

### Sprint 1 (P0, 1-2 Tage)
- [ ] M1: `_preflight-check.yml` erstellen mit GitHub API Permission Check (`allowed_actions`)
- [ ] M1: Secrets-Existenz-Check (presence, nicht Wert) für HETZNER_HOST, HETZNER_SSH_KEY, GHCR_TOKEN
- [ ] M1: Dockerfile-Lint-Regel: kein `/tmp/wheels/`-Pattern, keine Cross-Repo COPY-Referenzen
- [ ] M1: SSH-Probe + `.env.prod` Pflichtfeld-Check (POSTGRES_USER, IMAGE_TAG, etc.)
- [ ] M1: Nginx `proxy_pass`-Validierung: `46.225.113.1` statt `127.0.0.1`
- [ ] M1: `_deploy-hetzner.yml` um `needs: [preflight]` ergänzen
- [ ] M2: `.github/ISSUE_TEMPLATE/new-app-onboarding.yml` erstellen

### Sprint 2 (P1, 1-2 Wochen)
- [ ] M3: Inline-Workflow-Template als Copy-Paste-Vorlage in `docs/workflow-templates/`
- [ ] M4: CI-Pipeline für `platform_context` → GHCR Publish mit Semantic Versioning
- [ ] M4: Alle 11 Repo-Dockerfiles: `wheels/`-Block entfernen, GHCR-pip-install ergänzen
- [ ] M4: `PLATFORM_CONTEXT_VERSION` in alle `.env.prod` + Compose-Files

### Sprint 3 (P2, Backlog)
- [ ] M5: Deployment-Metriken-Dashboard (GitHub Actions API → PostgreSQL → Django)
- [ ] M6: Self-Healing Pipeline Integration (`hetzner_auto_healer.py` als `continue-on-error` Step)

### Validierung
- [ ] Neues Repo von Scratch deployen — max. 2 Runs bis Erfolg
- [ ] Ersterfolgquote über 4 Wochen messen → Ziel >85%
- [ ] MTTR messen → Ziel <10 Minuten

## Priorisierte Roadmap

| Prio | Maßnahme | Aufwand | Impact | Abhängigkeit |
|------|----------|---------|--------|--------------|
| P0 | M1: Pre-Flight-Validierung | 4h | Eliminiert Klasse A+D komplett | — |
| P0 | M2: Onboarding-Checkliste | 1h | Verhindert Wiederholung | — |
| P1 | M3: Inline-Workflow-Templates | 8h | Eliminiert Klasse C | — |
| P1 | M4: platform_context als Package | 4h | Eliminiert Klasse B | — |
| P2 | M5: Metriken-Dashboard | 16h | Feedback-Loop | deployment_mcp |
| P2 | M6: Self-Healing Integration | 8h | Reduziert MTTR | hetzner_auto_healer.py |
| P3 | M7: Self-Hosted Runner | 16h | Performance + Kosten | Hetzner Dev-Server |
| P3 | M8: GitOps Evaluierung | 8h | Skalierbarkeit | — |

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-20 | Achim Dehnert | Initial Draft — promoted aus Concept #5 (DevHub) |
