---
status: "accepted"
date: 2026-02-24
decision-makers: [Achim Dehnert]
consulted: []
informed: []
amends: ["ADR-021-unified-deployment-pattern.md"]
supersedes: []
related: ["ADR-021-unified-deployment-pattern.md", "ADR-056-deployment-preflight-and-pipeline-hardening.md"]
implementation_status: implemented
---

# Amendment: Docker HEALTHCHECK ausschließlich in docker-compose.prod.yml (amends ADR-021)

---

## Context and Problem Statement

ADR-021 §2.3 schreibt vor: `HEALTHCHECK Required in Dockerfile`. Diese Konvention hat im
coach-hub Incident (2026-02) zu einem **Restart-Loop** geführt:

- `HEALTHCHECK` im Dockerfile gilt für **alle Container**, die aus demselben Image erzeugt werden
- coach-hub nutzt ein einziges Image für `web`, `worker` und `beat`
- `worker` und `beat` haben keinen HTTP-Server → `curl localhost:8000/livez/` schlägt fehl
- Docker markiert alle Container als `unhealthy` → `restart: unless-stopped` → Restart-Loop

**Root Cause**: Ein Dockerfile-HEALTHCHECK ist image-global, nicht service-spezifisch.

---

## Decision Drivers

- **Sicherheit**: Kein ungeplanter Restart-Loop bei Multi-Process-Images
- **Korrektheit**: Healthcheck-Logik muss pro Service unterschiedlich sein (web vs. worker vs. beat)
- **Konsistenz**: Alle Repos sollen dasselbe Pattern verwenden
- **Rückwärtskompatibilität**: Bestehende Repos mit separaten Images sind nicht betroffen

---

## Considered Options

### Option 1 — HEALTHCHECK nur in `docker-compose.prod.yml` pro Service (gewählt)

Kein `HEALTHCHECK` im Dockerfile. Stattdessen pro-Service-Definition in `docker-compose.prod.yml`:

```yaml
services:
  web:
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://localhost:8000/livez/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    healthcheck:
      test: ["CMD-SHELL", "pidof python3.12 || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3

  beat:
    healthcheck:
      test: ["CMD-SHELL", "pidof python3.12 || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
```

**Pro:**
- Service-spezifisch — web, worker, beat haben unterschiedliche Healthchecks
- Kein Restart-Loop bei Multi-Process-Images
- Dockerfile bleibt sauber und wiederverwendbar

**Contra:**
- `docker inspect <container>` zeigt keinen Healthcheck für Images ohne Dockerfile-HEALTHCHECK
- Erfordert, dass alle compose.prod.yml-Dateien aktualisiert werden

### Option 2 — HEALTHCHECK im Dockerfile beibehalten (ADR-021 Status quo)

**Pro:** Kein Änderungsaufwand

**Contra:**
- Verursacht Restart-Loops bei Multi-Process-Images (coach-hub Incident)
- Nicht korrigierbar ohne separate Images pro Service

**Verworfen**: Fundamentaler Design-Fehler bei Single-Image / Multi-Process Architektur.

### Option 3 — Separate Dockerfiles pro Service (web/worker/beat)

**Pro:** Maximale Isolation

**Contra:**
- Dreifacher Build-Aufwand, dreifacher Image-Push
- Inkonsistent mit aktueller Platform-Praxis (ein Image pro Repo)

**Verworfen**: Zu hoher Ops-Overhead für den Gewinn.

---

## Decision Outcome

**Gewählt: Option 1** — `HEALTHCHECK` ausschließlich in `docker-compose.prod.yml`, nie im Dockerfile.

### Positive Consequences

- Kein Restart-Loop bei Single-Image / Multi-Process Architektur
- Healthcheck-Logik explizit und service-spezifisch sichtbar in compose
- Dockerfile bleibt image-unabhängig und wiederverwendbar

### Negative Consequences

- Bestehende Dockerfiles mit `HEALTHCHECK` müssen bei nächster Gelegenheit bereinigt werden
- `docker inspect` auf Image-Ebene zeigt keinen Healthcheck — akzeptabel, da compose ihn definiert

---

## Implementation Details

### Pflicht-Patterns

**Dockerfile** — kein HEALTHCHECK:
```dockerfile
# KEIN HEALTHCHECK — wird pro-Service in docker-compose.prod.yml definiert
FROM python:3.12-slim
...
USER appuser
CMD ["gunicorn", "config.wsgi:application"]
```

**docker-compose.prod.yml** — pro Service:
```yaml
services:
  web:
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://localhost:8000/livez/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  worker:
    healthcheck:
      test: ["CMD-SHELL", "pidof python3.12 || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s

  beat:
    healthcheck:
      test: ["CMD-SHELL", "pidof python3.12 || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s
```

### Worker/Beat Healthcheck-Begründung

- `celery inspect ping` schlägt fehl wenn der Broker (Redis) kurz nicht erreichbar ist → unnötige Restarts
- `pidof python` schlägt fehl — Debian/Ubuntu slim-Images benennen den Binary versioniert: `python3.12`
- `pidof python3.12` prüft nur ob der Prozess läuft — robust und broker-unabhängig

### Confirmation

- Neues ADR wird bei Review geprüft: Check 3.4 in `adr-review-checklist.md` v2.0
- Guardian-Check: `grep -r "^HEALTHCHECK" docker/` schlägt Alarm wenn HEALTHCHECK im Dockerfile gefunden
- Bestehende Repos: beim nächsten Deploy-Incident oder Review bereinigen (kein Force-Rollout)

---

## Amendments to ADR-021

Die folgenden Zeilen in ADR-021 §2.3 (Docker Conventions Table) gelten als ersetzt:

| Alt (ADR-021) | Neu (dieses Amendment) |
|---------------|----------------------|
| `HEALTHCHECK \| Required in Dockerfile \| python -c "import urllib..."` | `HEALTHCHECK \| Verboten im Dockerfile \| Pro-Service in docker-compose.prod.yml` |
| `Docker HEALTHCHECK \| Built into Dockerfile \| 30s` | `Docker HEALTHCHECK \| Per-Service in docker-compose.prod.yml \| 30s` |

---

## Migration Tracking

| Repo | Status | Priorität |
|------|--------|-----------|
| coach-hub | ✅ done (2026-02, Incident-Fix) | — |
| bfagent | ⬜ pending — bei nächstem Review | low |
| travel-beat | ⬜ pending — bei nächstem Review | low |
| risk-hub | ⬜ pending — bei nächstem Review | low |
| cad-hub | ⬜ pending — bei nächstem Review | low |
| trading-hub | ⬜ pending — bei nächstem Review | low |
| pptx-hub | ⬜ pending — bei nächstem Review | low |
| dev-hub | ⬜ pending — bei nächstem Review | low |

> **Kein Force-Rollout** — Bereinigung bei nächster geplanter Änderung am jeweiligen Repo.

---

## Drift-Detector Governance Note

```yaml
paths:
  - "*/Dockerfile"
  - "*/docker-compose.prod.yml"
drift_check_paths:
  - docker/app/Dockerfile
staleness_months: 24
supersedes_check: false
gate: NOTIFY
```
