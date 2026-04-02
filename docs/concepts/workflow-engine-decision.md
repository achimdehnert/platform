# Workflow Engine Decision Tree: Celery vs Temporal

**Status:** Active  
**Erstellt:** 2026-02-25  
**Bezug:** ADR-079 (Temporal Workflow Engine)  
**Gilt für:** Alle Repos im Platform-Ökosystem

---

## Entscheidungsbaum

```
Braucht der Task einen der folgenden Punkte?
│
├─ State über Session-/Restart-Grenzen hinweg? ──────── → TEMPORAL
├─ Human-in-the-Loop (Pause/Resume/Approval Gate)? ──── → TEMPORAL
├─ Cross-System-Workflow (App A → App B → App C)? ───── → TEMPORAL
├─ Crash Recovery mit automatischem Replay? ──────────── → TEMPORAL
├─ Laufzeit > 1h mit Checkpoints? ───────────────────── → TEMPORAL
│
├─ Periodischer Task (Schedule/Cron)? ───────────────── → CELERY BEAT
├─ Fire-and-forget (E-Mail, Webhook, Cleanup)? ──────── → CELERY
├─ Einfacher Background-Job (PDF, Export, Import)? ──── → CELERY
├─ Laufzeit < 30min ohne State-Bedarf? ──────────────── → CELERY
│
└─ Unklar? ──────────────────────────────────────────── → CELERY
    (Start einfach, migriere zu Temporal wenn nötig)
```

---

## Entscheidungsmatrix (Detail)

| Kriterium | Celery | Temporal | Gewichtung |
|-----------|--------|----------|------------|
| Fire-and-forget Tasks | ✅ Perfekt | Overkill | Häufigster Use Case |
| Periodic Tasks (Beat/Cron) | ✅ Nativ | ❌ Braucht Schedule-Activity | 7 von 9 Apps |
| State über Session-Grenzen | ❌ Redis verfällt (1h) | ✅ PostgreSQL persistent | Nur bfagent, mcp-hub |
| Human-in-the-Loop Gates | ❌ Nur Polling | ✅ `wait_condition()` nativ | Nur bfagent (ADR-066) |
| Cross-System Workflows | ❌ Nicht möglich | ✅ Saga-Pattern | bfagent → mcp-hub → deploy |
| Replay / Time-Travel Debug | ❌ Kein Replay | ✅ Vollständige History | Debug-Vorteil |
| Crash Recovery | ❌ State verloren | ✅ Auto-Replay | Kritisch für LLM-Workflows |
| Infra-Overhead | ✅ Redis (läuft) | ⚠️ +512MB RAM | Kosten-Faktor |
| Lernkurve | ✅ Bekannt | ⚠️ Determinismus-Regeln | Onboarding |
| Deployment-Komplexität | ✅ 1 Container | ⚠️ Server + UI + Worker + DB | Ops-Aufwand |

---

## App-Zuordnung (aktuell)

| App | Engine | Begründung |
|-----|--------|------------|
| **bfagent** | Celery *(→ Temporal wenn Gates nötig)* | LLM-Workflows >30min, Gate-Mechanismus geplant |
| **mcp-hub** | Kein Celery *(→ Temporal wenn Agent-Team-Workflows persistent)* | Session-übergreifende Workflows |
| **weltenhub** | Celery + Beat | Periodische Tasks, kein State-Bedarf |
| **travel-beat** | Celery + Beat | Periodische Tasks |
| **trading-hub** | Celery + Beat | Periodische Scans |
| **dev-hub** | Celery + Beat | Catalog-Sync |
| **coach-hub** | Celery + Beat | Standard Django-Tasks |
| **risk-hub** | Celery | Background-Jobs |
| **pptx-hub** | Celery | PDF/PPTX-Generierung |

---

## Koexistenz-Strategie

### Architektur

```
┌─────────────────────────────────────────────────┐
│                   Django App                     │
│                                                  │
│  views.py ─→ services.py ─┬─→ celery_task()     │
│                            │   (fire-and-forget)  │
│                            │                      │
│                            └─→ temporal_workflow() │
│                                (durable, stateful) │
└─────────────────────────────────────────────────┘
         │                        │
    ┌────▼────┐            ┌─────▼──────┐
    │  Redis  │            │  Temporal  │
    │ Broker  │            │  Server    │
    └────┬────┘            └─────┬──────┘
    ┌────▼────┐            ┌─────▼──────┐
    │ Celery  │            │  Temporal  │
    │ Worker  │            │  Worker    │
    └─────────┘            └────────────┘
```

### Regeln

1. **Default ist Celery** — bis ein konkreter Temporal-Trigger vorliegt
2. **Temporal-Trigger** (mindestens einer muss zutreffen):
   - State muss Session-/Restart-Grenzen überleben
   - Human-Approval-Gate im Workflow
   - Cross-System-Orchestrierung (>1 App)
   - Laufzeit >1h mit Checkpoint-Bedarf
3. **Kein Mix innerhalb eines Workflows** — ein Workflow ist entweder Celery ODER Temporal
4. **Celery Beat bleibt** — Temporal hat keinen nativen Scheduler
5. **Migration nur bei Bedarf** — nicht präventiv migrieren

---

## Temporal Deploy-Trigger

Temporal wird ERST deployed wenn:

- [ ] bfagent braucht echte Gate-2+ Approval (ADR-066)
- [ ] Cross-System-Workflow bfagent → mcp-hub ist produktiv nötig
- [ ] Agent-Team-Workflows (mcp-hub) müssen Restarts überleben

Bis dahin: **Celery für alles.**

---

## Infrastruktur-Bedarf (wenn Temporal deployt wird)

| Komponente | Image | RAM | Port |
|------------|-------|-----|------|
| temporal-server | `temporalio/auto-setup:latest` | ~256MB | 7233 (gRPC) |
| temporal-ui | `temporalio/ui:latest` | ~128MB | 8233 (HTTP) |
| temporal-db | `postgres:16-alpine` (shared oder dedicated) | ~128MB | 5432 |
| temporal-worker (je App) | App-Image mit `temporalio` | ~128MB | — |
| **Gesamt** | | **~640MB** | |

---

## ADR-079 Status-Korrektur

**ADR-079 markiert alle 6 Migrations-Phasen als ✅ Abgeschlossen.**  
**Realität (2026-02-25): Kein Temporal-Container deployed. Alle Apps nutzen Celery.**

Das ADR ist ein **Design-Dokument**, die Migration-Tracking-Tabelle spiegelt Planung wider, nicht den Ist-Zustand. Der ADR-Status sollte von `accepted` auf `proposed` korrigiert werden, oder die Migration-Tracking-Tabelle auf den tatsächlichen Status aktualisiert werden.

---

*Letzte Prüfung: 2026-02-25 — kein Temporal-Container auf Prod (88.198.191.108)*
