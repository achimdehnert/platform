# ADR-115: Grafana Agent Controlling Dashboard

## Status

Accepted

## Context

Das AI Engineering Squad (ADR-100) führt Tasks über 25 Repos aus und nutzt den LLM Gateway (ADR-114) für alle LLM-Calls. Bisher gibt es kein zentrales Controlling für:

- **Kosten**: Tatsächliche LLM-Token-Kosten pro Task, Repo, Model
- **Dauer**: Wie lange dauern Tasks und einzelne LLM-Calls?
- **Qualität**: Gate-Approval-Rate, Error-Rate, Retry-Häufigkeit
- **Model-Mix**: Welche Models werden wie häufig genutzt?
- **Trend**: Kosten-Entwicklung über Zeit (Budgetkontrolle)

Ohne dieses Controlling ist es schwer zu beurteilen ob das Agent-Team wirtschaftlich arbeitet und wo Optimierungspotential liegt.

## Decision

Wir implementieren ein **Grafana Controlling Dashboard** mit PostgreSQL als Datasource.

### Architektur

```
llm_mcp FastAPI
  → nach jedem LLM-Call: Usage in llm_calls Tabelle schreiben
  → OpenRouter gibt usage.prompt_tokens + completion_tokens zurück

PostgreSQL (orchestrator_mcp DB, neue Tabelle llm_calls)
  → Grafana direkte Datasource (kein extra API-Layer)

Grafana Container (mcp-hub Stack)
  → Port 3000 (intern, Nginx-Proxy optional)
  → Admin-Passwort via .env
  → Dashboard als JSON provisioned (kein manueller Setup)
```

### Datenmodell

```sql
CREATE TABLE llm_calls (
    id                BIGSERIAL PRIMARY KEY,
    task_id           TEXT,
    repo              TEXT,
    model             TEXT          NOT NULL,
    prompt_tokens     INTEGER       NOT NULL DEFAULT 0,
    completion_tokens INTEGER       NOT NULL DEFAULT 0,
    total_tokens      INTEGER       NOT NULL DEFAULT 0,
    cost_usd          NUMERIC(12,8) NOT NULL DEFAULT 0,
    duration_ms       INTEGER,
    source            TEXT,
    error             BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX llm_calls_created_at_idx ON llm_calls (created_at DESC);
CREATE INDEX llm_calls_repo_idx ON llm_calls (repo);
CREATE INDEX llm_calls_task_id_idx ON llm_calls (task_id);
```

### Kosten-Kalkulation

Preise als Konfiguration (OpenRouter-Preise, Stand 2026-03):

| Model | Input ($/1M Token) | Output ($/1M Token) |
|---|---|---|
| openai/gpt-4o | 2.50 | 10.00 |
| openai/gpt-4o-mini | 0.15 | 0.60 |
| anthropic/claude-3.5-sonnet | 3.00 | 15.00 |
| meta-llama/llama-3.1-70b | 0.52 | 0.75 |

### Grafana Dashboard Panels

1. **Total Kosten (heute / 7d / 30d)** — Stat Panel
2. **Kosten pro Tag** — Time Series
3. **Kosten pro Repo** — Bar Chart
4. **Token-Verbrauch pro Model** — Pie Chart
5. **Durchschnittliche Call-Dauer** — Gauge
6. **Error-Rate** — Stat Panel
7. **Top 10 teuerste Tasks** — Table
8. **Model-Mix über Zeit** — Stacked Bar

### Deployment

- Grafana als neuer Service in `docker-compose.llm-mcp.yml`
- Dashboard als JSON via Volume-Mount provisioniert (IaC)
- Kein manuelles Einrichten nach Deploy nötig

## Alternatives Considered

### dev-hub Django Dashboard

- **Pro**: Einheitliche Platform-UI, Custom Business-Logic
- **Contra**: Mehr Custom-Code für dasselbe, kein Alerting, keine Time-Series
- **Entscheidung**: Zu viel Aufwand für denselben Nutzen

### Prometheus + Grafana

- **Pro**: Industry-Standard für Metrics
- **Contra**: Prometheus braucht Pull-Endpoints in jedem Service, overkill für SQL-Daten
- **Entscheidung**: Direkte PostgreSQL-Datasource reicht

### Externe SaaS (Datadog, New Relic)

- **Pro**: Kein Eigenbetrieb
- **Contra**: Kosten, Datenschutz, Lock-in
- **Entscheidung**: Self-hosted bevorzugt

## Consequences

### Positiv

- Vollständige Kosten-Transparenz für alle 25 Repos
- Sofort-Alerting wenn Kosten-Threshold überschritten
- Historische Trend-Analyse
- Kein Extra-API-Layer nötig (PostgreSQL direkt)
- Dashboard als Code (Git-versioniert)

### Negativ / Risiken

- Grafana Container ~200MB RAM zusätzlich
- Preistabelle muss manuell aktualisiert werden bei OpenRouter Preisänderungen
- Qualitäts-Score (subjektiv) initial nicht automatisierbar

## Implementation

1. `llm_calls` Tabelle in orchestrator_mcp PostgreSQL
2. `llm_mcp_service/usage_logger.py` — Usage nach jedem Call in DB schreiben
3. `llm_mcp_service/pricing.py` — Kosten-Kalkulation pro Model
4. `docker-compose.llm-mcp.yml` — Grafana Service hinzufügen
5. `grafana/provisioning/` — Datasource + Dashboard JSON

## References

- ADR-100: Extended Agent Team + Deployment Agent
- ADR-112: Agent Skill Registry + Persistent Context
- ADR-113: pgvector Memory Store
- ADR-114: Discord IDE-like Communication Gateway + LLM Gateway
- [OpenRouter Pricing](https://openrouter.ai/models)
- [Grafana PostgreSQL Datasource](https://grafana.com/docs/grafana/latest/datasources/postgres/)
