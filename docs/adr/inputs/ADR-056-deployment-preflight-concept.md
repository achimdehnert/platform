# Deployment Workflow Analyse & Optimierungskonzept

**Projekt:** BF Agent Platform — CI/CD Pipeline  
**Auslöser:** Trading-Hub Deployment-Session (20.02.2026)  
**Autor:** Achim Dehnert / Claude  
**Status:** ENTWURF → ADR-056

---

## 1. Zusammenfassung

Eine Deployment-Session für `trading-hub` hat **7 aufeinanderfolgende `startup_failure`-Runs** produziert, bevor der Workflow überhaupt starten konnte, gefolgt von weiteren Fehlern bei Tests und Docker Build. Die Root-Cause-Analyse zeigt ein systemisches Problem: Die Platform-weite Deployment-Architektur (ADR-009 v2, Reusable Workflows) hat **strukturelle Schwächen**, die bei jedem neuen App-Onboarding dieselben Fehlerklassen reproduzieren.

Dieses Konzept definiert konkrete Maßnahmen, um die **Ersterfolgquote** von Deployments von derzeit ~15% auf >85% zu heben.

---

## 2. Fehleranalyse der Trading-Hub Session

### 2.1 Chronologischer Fehlerverlauf

| # | Commit | Fehler | Kategorie | Zeitverlust |
|---|--------|--------|-----------|-------------|
| 1 | c71f3fe | `startup_failure` | PERMISSION | ~5 min |
| 2 | 115a5c4 | `startup_failure` | PERMISSION | ~5 min |
| 3 | cc58e06 | `startup_failure` | PERMISSION | ~5 min |
| 4 | 9b0a0d0 | `startup_failure` | PERMISSION | ~5 min |
| 5 | 7001b96 | `startup_failure` | PERMISSION | ~5 min |
| 6 | 7001b96 | `startup_failure` (nach Permissions-Fix) | PERMISSION→OK | ~2 min |
| 7 | 7001b96 | Tests fehlgeschlagen (`platform_context`) | BUILD | ~8 min |
| 8 | e86ce42 | Docker Build fehlgeschlagen (`bfagent-core`) | BUILD | ~8 min |
| 9 | cd64d3f | Tests OK, Build OK → Deploy pending | — | — |

**Gesamtzeitverlust:** ~43 Minuten + Iterationszeit für Diagnose und Fixes.

### 2.2 Identifizierte Fehlerklassen

#### Klasse A: Repository-Konfiguration (5 von 9 Fehlern)

**Root Cause:** `allowed_actions: local_only` im GitHub Repository.  
**Auswirkung:** Jeder Workflow mit externen Actions schlägt mit `startup_failure` fehl — ohne Logs, ohne Jobs, ohne Fehlermeldung.

#### Klasse B: Fehlende Cross-Repo-Dependencies (2 von 9 Fehlern)

1. `platform_context` nicht im CI verfügbar (absoluter lokaler Pfad in `pyproject.toml`)
2. `packages/bfagent-core` im Dockerfile referenziert — existiert nicht im trading-hub Repo

#### Klasse C: Workflow-Design (2 von 9 Fehlern)

1. Reusable Workflows + normale Jobs gemischt (`needs:` Anti-Pattern)
2. `inputs.*` bei Push-Trigger → `startup_failure` weil `inputs` undefined

#### Klasse D: Infrastructure-Drift

- Nginx `proxy_pass` auf falsche IP
- Fehlende `.env.prod`-Variable
- Docker-Compose Image-Pfad-Mismatch

### 2.3 Fehlerverteilung

```
PERMISSION    56% (5/9)
BUILD         22% (2/9)
WORKFLOW      22% (2/9)
```

---

## 3. Systemische Schwachstellen

- Kein Onboarding-Prozess für neue Apps
- Reusable Workflows ohne Input-Validierung
- `platform_context` nicht als Package publiziert
- Keine Pre-Flight-Checks, keine Deployment-Metriken

---

## 4. Optimierungskonzept (→ ADR-056)

### P0 (Sofort)
- M1: Pre-Flight-Validierungs-Script (`validate-deployment-readiness.sh`)
- M2: App-Onboarding-Checkliste als GitHub Issue Template

### P1 (Sprint 2-3)
- M3: Inline-Workflow-Templates statt Reusable Workflows für neue Apps
- M4: `platform_context` als PyPI-Package

### P2 (Mittelfristig)
- M5: Deployment-Metriken-Dashboard
- M6: Self-Healing Pipeline Integration

### P3 (Quartal)
- M7: Self-Hosted Runner auf Dev-Server
- M8: GitOps-Evaluierung (ArgoCD/Flux)

---

## 5. Offene Fragen (für ADR-056 zu entscheiden)

1. Reusable Workflows komplett ablösen oder nur für neue Apps Inline-Templates?
2. Self-Hosted Runner: gemeinsam oder dediziert pro App?
3. `platform_context` Publishing: GitHub Packages oder PyPI-Mirror?
4. Metriken-Retention: wie lange?
