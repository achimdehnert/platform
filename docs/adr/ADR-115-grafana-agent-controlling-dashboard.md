# ADR-115: Grafana Agent Controlling Dashboard

## Status

Accepted — Post-Review v1.3.0 (2026-03-09)

> **Review-Ergebnis**: 3 Blocker (B-01/02/03) + 2 Kritisch (K-01/K-02) wurden behoben.
> Alle Korrekturen sind in `mcp-hub` v1.3.0 implementiert und deployed.

## Context

Das AI Engineering Squad (ADR-100) führt Tasks über 25 Repos aus und nutzt den LLM Gateway
(ADR-114) für alle LLM-Calls. Bisher gibt es kein zentrales Controlling für:

- **Kosten**: Tatsächliche LLM-Token-Kosten pro Task, Repo, Model
- **Dauer**: Wie lange dauern Tasks und einzelne LLM-Calls?
- **Qualität**: Gate-Approval-Rate, Error-Rate, Retry-Häufigkeit
- **Model-Mix**: Welche Models werden wie häufig genutzt?
- **Trend**: Kosten-Entwicklung über Zeit (Budgetkontrolle)

## Decision

Wir implementieren ein **Grafana Controlling Dashboard** mit PostgreSQL als Datasource.

### Architektur

```
llm_mcp FastAPI (v1.3.0)
  → nach jedem LLM-Call: BackgroundTask → UsageLogger.log(record)  [K-02 Fix]
  → Preise aus llm_model_pricing DB-Tabelle mit 5min Cache          [H-01 Fix]
  → Kosten zum Call-Zeitpunkt kalkuliert (historisch korrekt)

PostgreSQL (orchestrator_mcp DB)
  ├── llm_calls          — Audit-Log aller LLM-Calls
  └── llm_model_pricing  — Historisierte Preis-Tabelle

Grafana Container (mcp-hub Stack)
  → Port 3000 intern, Nginx-Proxy: devhub.iil.pet/grafana/
  → Read-Only User grafana_ro (K-01 Fix)
  → Dashboard als JSON provisioniert (IaC, kein manueller Setup)
```

### Datenmodell (Post-Review — alle Blocker behoben)

```sql
-- B-01: tenant_id, B-02: deleted_at, B-03: public_id ergänzt
CREATE TABLE llm_calls (
    id                BIGSERIAL       PRIMARY KEY,
    public_id         UUID            NOT NULL DEFAULT gen_random_uuid(),  -- B-03
    tenant_id         BIGINT          NOT NULL DEFAULT 0,                  -- B-01
    task_id           TEXT,
    repo              TEXT,
    source            TEXT,           -- 'discord_chat' | 'discord_ask' | 'mcp_tool'
    call_type         TEXT            NOT NULL DEFAULT 'chat',             -- M-01
    request_id        TEXT,                                                -- M-02
    model             TEXT            NOT NULL,
    prompt_tokens     INTEGER         NOT NULL DEFAULT 0,
    completion_tokens INTEGER         NOT NULL DEFAULT 0,
    total_tokens      INTEGER         NOT NULL DEFAULT 0,
    cost_usd          NUMERIC(12,8)   NOT NULL DEFAULT 0,
    duration_ms       INTEGER,
    latency_p95_ms    INTEGER,
    error             BOOLEAN         NOT NULL DEFAULT FALSE,
    error_code        TEXT,           -- 'rate_limit' | 'timeout' | ...  -- H-02
    error_message     TEXT,           -- Rohe Fehlermeldung, max. 1000 Zeichen
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ                                          -- B-02
);

-- Historisierte Preise (H-01 Fix: nicht mehr hardcodiert)
CREATE TABLE llm_model_pricing (
    id                BIGSERIAL       PRIMARY KEY,
    public_id         UUID            NOT NULL DEFAULT gen_random_uuid(),
    model             TEXT            NOT NULL,
    provider          TEXT,
    input_per_1m_usd  NUMERIC(12,8)   NOT NULL,
    output_per_1m_usd NUMERIC(12,8)   NOT NULL,
    valid_from        TIMESTAMPTZ     NOT NULL DEFAULT now(),
    valid_until       TIMESTAMPTZ,    -- NULL = aktuell gültig
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ
);
-- Partial-Unique: nur ein aktueller Preis pro Modell
CREATE UNIQUE INDEX uq_llm_model_pricing_current
    ON llm_model_pricing (model)
    WHERE valid_until IS NULL AND deleted_at IS NULL;
```

### Kosten-Kalkulation (DB-backed, historisch korrekt)

Preise in `llm_model_pricing` Tabelle (Stand 2026-03):

| Model | Input ($/1M Token) | Output ($/1M Token) |
|---|---|---|
| openai/gpt-4o | 2.50 | 10.00 |
| openai/gpt-4o-mini | 0.15 | 0.60 |
| anthropic/claude-3.5-sonnet | 3.00 | 15.00 |
| anthropic/claude-opus-4 | 15.00 | 75.00 |
| meta-llama/llama-3.1-70b-instruct | 0.52 | 0.75 |
| google/gemini-2.0-flash-001 | 0.10 | 0.40 |

**Preis-Update ohne Code-Deployment**: neuen Eintrag in `llm_model_pricing` mit
`valid_from = jetzt` → bisheriger Preis erhält `valid_until = jetzt` → historische
Daten bleiben korrekt.

### Sicherheit: Read-Only Grafana DB-User (K-01 Fix)

```sql
CREATE USER grafana_ro WITH PASSWORD '${GRAFANA_DB_PASSWORD}';
GRANT CONNECT ON DATABASE orchestrator_mcp TO grafana_ro;
GRANT USAGE ON SCHEMA public TO grafana_ro;
GRANT SELECT ON llm_calls TO grafana_ro;
GRANT SELECT ON llm_model_pricing TO grafana_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO grafana_ro;
```

Setup via `grafana/scripts/setup_grafana_ro_user.sh`.

### Non-blocking Logging (K-02 Fix)

```python
# In FastAPI-Route — sofortige Response, Logging im Hintergrund
background_tasks.add_task(UsageLogger.log, record)
return result  # Keine Blockierung durch DB-Write
```

`UsageLogger.log()` ist als FastAPI `BackgroundTask` implementiert.
Fehler werden geloggt, nie propagiert.

### Grafana Dashboard Panels (10 Panels)

1. **Gesamtkosten** (Zeitraum-Filter) — Stat mit Thresholds
2. **Calls gesamt** — Stat
3. **Error-Rate** — Stat (grün/gelb/rot)
4. **Ø Latenz** — Stat
5. **Kosten pro Tag** — Time Series
6. **Token-Verbrauch pro Modell** — Pie Chart
7. **Kosten pro Repository** — Bar Chart (Top 20)
8. **Model-Mix über Zeit** — Stacked Time Series
9. **Top 10 teuerste Tasks** — Table
10. **Latenz p50/p95/p99** — Time Series (H-04 Fix)

Dashboard-Variablen: `$repo`, `$model` (multi-select, inkl. All).

### Deployment

```
llm_mcp_service/
  models/llm_call.py          — SQLAlchemy Model (Platform-Standards)
  models/model_pricing.py     — Historisierte Preistabelle
  services/pricing_service.py — DB-Preisabfrage mit 5min Cache
  services/usage_logger.py    — Fire-and-Forget BackgroundTask
  migrations/0042_*.py        — Alembic-Migration (idempotent)

grafana/
  provisioning/datasources/postgres.yml  — grafana_ro User
  provisioning/dashboards/agent_controlling.json
  scripts/setup_grafana_ro_user.sh

docker-compose.llm-mcp.yml — Grafana + llm_mcp Services
```

## Review-Befunde und Korrekturen

| # | Befund | Severity | Status |
|---|--------|----------|--------|
| B-01 | `tenant_id` fehlte | BLOCKER | ✅ Behoben |
| B-02 | `deleted_at` fehlte | BLOCKER | ✅ Behoben |
| B-03 | `public_id` fehlte | BLOCKER | ✅ Behoben |
| K-01 | Grafana ohne RO-User | KRITISCH | ✅ Behoben |
| K-02 | Synchrones Logging | KRITISCH | ✅ Behoben |
| H-01 | Hardcodierte Preise | HOCH | ✅ Behoben |
| H-02 | Kein `error_message` | HOCH | ✅ Behoben |
| H-04 | Keine p95/p99-Latenz | HOCH | ✅ Behoben |
| H-03 | Kein Retention-Konzept | HOCH | ⏳ Backlog |
| M-01 | Kein `call_type` | MEDIUM | ✅ Behoben |
| M-02 | Kein `request_id` | MEDIUM | ✅ Behoben |
| M-03 | Grafana-Container Healthcheck | MEDIUM | ✅ Behoben |
| M-04 | Alerting-Rule-Provisioning | MEDIUM | ⏳ Backlog |
| M-05 | `source`-Feld ohne Enum | MEDIUM | ⏳ Backlog |

## Alternatives Considered

### dev-hub Django Dashboard

- **Contra**: Mehr Custom-Code, kein Alerting, keine Time-Series
- **Entscheidung**: Grafana als Ergänzung für Ops-Monitoring, Django Admin für Preis-Konfiguration

### Prometheus + Grafana

- **Contra**: Prometheus braucht Pull-Endpoints in jedem Service, overkill für SQL-Daten
- **Entscheidung**: Direkte PostgreSQL-Datasource reicht

### OpenTelemetry + Grafana Tempo

- **Pro**: Industry-Standard, kombiniert Traces + Metrics + Logs
- **Contra**: ~3x mehr Infrastruktur, steile Lernkurve für aktuellen Use-Case
- **Entscheidung**: Für zukünftige Skalierung evaluieren (>10k Calls/Tag)

## Consequences

### Positiv

- Vollständige Kosten-Transparenz für alle 25 Repos
- Provider-Wechsel ohne Code-Deployment (nur Preistabelle updaten)
- Historisch korrekte Kosten-Kalkulation (Zeitraum-Preise)
- Security: Grafana-Kompromittierung kann keine Produktionsdaten verändern
- p95/p99 Latenz-Monitoring für SLA-Überwachung

### Negativ / Risiken

- Grafana Container ~200MB RAM zusätzlich
- Retention-Policy noch nicht implementiert (H-03 Backlog)
- Qualitäts-Score (subjektiv) initial nicht automatisierbar

## References

- ADR-100: Extended Agent Team + Deployment Agent
- ADR-114: Discord IDE-like Communication Gateway + LLM Gateway
- ADR-115-review.md: Principal IT-Architekt Review (2026-03-09)
- ADR-116: Dynamic Model Router (Nutzung der llm_model_pricing Tabelle)
- [OpenRouter Pricing](https://openrouter.ai/models)
- [Grafana PostgreSQL Datasource](https://grafana.com/docs/grafana/latest/datasources/postgres/)
