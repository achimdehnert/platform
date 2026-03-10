# ADR-115: Implementierungsplan — Grafana Agent Controlling Dashboard

**Version**: 1.0 (Post-Review)  
**Datum**: 2026-03-09  
**Blocker behoben**: B-01 (tenant_id), B-02 (deleted_at), B-03 (public_id), K-01 (RO-User), K-02 (async)

---

## Dateistruktur

```
llm_mcp/
├── llm_mcp_service/
│   ├── migrations/
│   │   └── 0042_llm_calls_and_pricing.py     # Phase 1
│   ├── models/
│   │   ├── __init__.py
│   │   ├── llm_call.py                        # Phase 1
│   │   └── model_pricing.py                   # Phase 1
│   ├── services/
│   │   ├── usage_logger.py                    # Phase 2
│   │   └── pricing_service.py                 # Phase 2
│   └── management/
│       └── commands/
│           └── setup_grafana_db_user.py        # Phase 3
├── docker-compose.llm-mcp.yml                 # Phase 3 (Grafana Service)
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── postgres.yml                    # Phase 3
    │   └── dashboards/
    │       ├── dashboard.yml                   # Phase 3
    │       └── agent_controlling.json          # Phase 4
    └── grafana.ini                             # Phase 3
```

---

## Phase 1: Datenmodell (Tag 1)

**Dateien**: `models/llm_call.py`, `models/model_pricing.py`, Migration

### 1.1 SQLAlchemy Models (llm_mcp ist FastAPI/SQLAlchemy)

→ Siehe `llm_call_model.py` und `model_pricing_model.py`

### 1.2 Migration

→ Alembic-Migration, idempotent via `IF NOT EXISTS`

---

## Phase 2: Usage Logger + Pricing Service (Tag 1-2)

**Dateien**: `services/usage_logger.py`, `services/pricing_service.py`

- Async, Fire-and-Forget via BackgroundTasks
- Preise aus DB, mit Cache (5 Minuten TTL)
- Kosten-Kalkulation zum Schreib-Zeitpunkt (historisch korrekt)

---

## Phase 3: Infrastruktur (Tag 2)

**Dateien**: `docker-compose.llm-mcp.yml`, `grafana/provisioning/datasources/postgres.yml`

- Grafana Container mit Read-Only PostgreSQL-User
- Dashboard-Provisioning via Volume-Mount
- `.env`-basierte Secrets

---

## Phase 4: Dashboard JSON (Tag 3)

**Datei**: `grafana/provisioning/dashboards/agent_controlling.json`

8 Panels entsprechend ADR-115 + ergänzt um p95-Latenz

---

## Implementierungsreihenfolge

```
Phase 1 → Phase 2 → Phase 3 → Phase 4
   ↓           ↓          ↓         ↓
Schema    Logger+Pricing  Infra   Dashboard
 (Blocker    (Kritisch    (RO-     (Panels)
  behoben)    behoben)    User)
```

---

## Umgebungsvariablen (.env Ergänzungen)

```bash
# Grafana
GRAFANA_ADMIN_PASSWORD=<sicheres-passwort>
GRAFANA_DB_PASSWORD=<ro-passwort-fuer-grafana-ro-user>

# Logging-Level für Usage Logger
LLM_USAGE_LOG_FAILURES=true  # Logging-Fehler in stderr schreiben
```

---

## Rollback-Plan

Da alle Änderungen additiv sind (neue Tabellen, neuer Container):

```bash
# Rollback Grafana:
docker-compose -f docker-compose.llm-mcp.yml stop grafana

# Rollback Schema:
# llm_calls und llm_model_pricing sind neue Tabellen → einfach droppen
# Keine bestehenden Tabellen verändert → nulles Risiko
```
