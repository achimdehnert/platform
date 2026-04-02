# ADR-115 Review: Grafana Agent Controlling Dashboard

**Reviewer**: Principal IT-Architekt  
**Datum**: 2026-03-09  
**ADR**: ADR-115 — Grafana Agent Controlling Dashboard  
**Gesamturteil**: ⚠️ **BEDINGT FREIGEGEBEN** — 3 Blocker + 2 Kritisch vor Implementierung zu beheben

---

## 1. Review-Tabelle

| # | Befund | Severity | Bereich |
|---|--------|----------|---------|
| B-01 | `llm_calls`-Tabelle fehlt `tenant_id` — Platform-Standard-Verletzung | **BLOCKER** | Datenmodell |
| B-02 | Kein `deleted_at` Soft-Delete auf `llm_calls` — Platform-Standard-Verletzung | **BLOCKER** | Datenmodell |
| B-03 | Kein `public_id` UUID-Feld — Platform-Standard (BigAutoField PK + public_id) | **BLOCKER** | Datenmodell |
| K-01 | Grafana direkter Read/Write-Zugang zur Produktions-DB — keine Read-Only-Trennung | **KRITISCH** | Security |
| K-02 | `usage_logger.py` schreibt synchron in FastAPI — blockiert LLM-Call-Response | **KRITISCH** | Performance |
| H-01 | Preistabelle hardcodiert in `pricing.py` — kein DB-backed Admin-UI | **HOCH** | Betrieb |
| H-02 | Kein `error_message TEXT` — booleaner Error-Flag unzureichend für Debugging | **HOCH** | Observability |
| H-03 | Kein Data-Retention-Konzept — `llm_calls` wächst unbegrenzt | **HOCH** | Betrieb |
| H-04 | Keine Latenz-Perzentile (p95/p99) — Durchschnitt allein ist irreführend | **HOCH** | Dashboard |
| M-01 | Kein `call_type` Feld (chat/embedding/rerank) — verhindert spätere Erweiterung | **MEDIUM** | Datenmodell |
| M-02 | Kein `request_id` für Korrelation mit externem Tracing | **MEDIUM** | Observability |
| M-03 | Grafana-Container fehlt `restart: unless-stopped` + Health-Check | **MEDIUM** | Deployment |
| M-04 | Kein Alerting-Rule-Provisioning im ADR beschrieben | **MEDIUM** | Operations |
| M-05 | `source`-Feld ohne ENUM-Constraint — Freitext führt zu inkonsistenten Werten | **MEDIUM** | Datenmodell |

---

## 2. Detailbefunde mit Korrekturen

### B-01: Fehlendes `tenant_id` — BLOCKER

**Problem**: Die `llm_calls`-Tabelle hat kein `tenant_id`. Platform-Standard schreibt `tenant_id = BigIntegerField(db_index=True)` auf allen User-Data-Modellen vor. Ohne dieses Feld ist Multi-Tenant-Isolation nicht möglich und DSGVO Art. 32 verletzt.

**Korrektur**:
```sql
ALTER TABLE llm_calls ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 0;
CREATE INDEX llm_calls_tenant_id_idx ON llm_calls (tenant_id);
```

**Im finalen Schema** (siehe Implementierungsplan):
```sql
tenant_id   BIGINT       NOT NULL,
```

---

### B-02: Fehlendes Soft-Delete — BLOCKER

**Problem**: Kein `deleted_at TIMESTAMPTZ` auf der Tabelle. Platform-Standard verlangt Soft-Delete auf allen User-Data-Modellen.

**Hinweis**: Für Audit-Log-ähnliche Tabellen (`llm_calls` ist append-only) kann Soft-Delete als `is_active`-Flag mit Policy-basierter Retention implementiert werden — aber das Feld muss vorhanden sein.

**Korrektur**:
```sql
deleted_at  TIMESTAMPTZ  NULL,  -- Soft-Delete: Platform-Standard
```

---

### B-03: Fehlendes `public_id` — BLOCKER

**Problem**: Platform-Standard schreibt `BigAutoField PK + public_id UUIDField` vor. Für externe Referenzen (API-Responses, Discord-Nachrichten, Dashboard-Links) muss eine opake ID verfügbar sein.

**Korrektur**:
```sql
id          BIGSERIAL    PRIMARY KEY,
public_id   UUID         NOT NULL DEFAULT gen_random_uuid(),
```

---

### K-01: Grafana Read/Write-Datenbankzugang — KRITISCH

**Problem**: Das ADR beschreibt Grafana als "direkte Datasource" ohne Einschränkung. Grafana bekommt damit denselben DB-User wie die Applikation — mit Schreibrechten. Ein kompromittiertes Grafana-Dashboard könnte Produktionsdaten modifizieren oder löschen.

**Korrektur**: Separater Read-Only PostgreSQL-User für Grafana:
```sql
-- In Migration / Deployment-Script ausführen
CREATE USER grafana_ro WITH PASSWORD '${GRAFANA_DB_PASSWORD}';
GRANT CONNECT ON DATABASE orchestrator_mcp TO grafana_ro;
GRANT USAGE ON SCHEMA public TO grafana_ro;
GRANT SELECT ON llm_calls TO grafana_ro;
-- Zukünftige Tabellen automatisch abdecken:
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO grafana_ro;
```

**In `grafana/provisioning/datasources/postgres.yml`**:
```yaml
datasources:
  - name: PostgreSQL
    type: postgres
    url: ${POSTGRES_HOST}:5432
    user: grafana_ro  # Read-Only User!
    secureJsonData:
      password: ${GRAFANA_DB_PASSWORD}
```

---

### K-02: Synchrones DB-Write in FastAPI — KRITISCH

**Problem**: `usage_logger.py` schreibt synchron nach jedem LLM-Call. Bei DB-Latenz oder -Ausfall blockiert das den API-Response. LLM-Calls dauern ohnehin 1–30 Sekunden — das Logging darf nicht die Antwortzeit erhöhen oder im Fehlerfall den Call zum Scheitern bringen.

**Korrekte Lösung — Fire-and-Forget mit asyncio**:
```python
# usage_logger.py
import asyncio
import logging
from contextlib import suppress

logger = logging.getLogger(__name__)

async def log_llm_call_async(session: AsyncSession, record: LlmCallRecord) -> None:
    """Non-blocking: Fehler werden geloggt, nie propagiert."""
    try:
        await session.execute(insert(LlmCall).values(**record.model_dump()))
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_call logging failed (non-critical): %s", exc)

def log_llm_call_background(record: LlmCallRecord) -> None:
    """FastAPI BackgroundTask-kompatible Variante."""
    # Wird als BackgroundTask registriert, nie awaited im Request-Handler
    asyncio.create_task(_safe_log(record))

async def _safe_log(record: LlmCallRecord) -> None:
    async with get_async_session() as session:
        with suppress(Exception):
            await session.execute(insert(LlmCall).values(**record.model_dump()))
            await session.commit()
```

**In FastAPI-Route**:
```python
from fastapi import BackgroundTasks

@router.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    result = await llm_gateway.call(request)
    background_tasks.add_task(log_llm_call_background, build_record(request, result))
    return result  # Sofortige Response, Logging im Hintergrund
```

---

### H-01: Hardcodierte Preistabelle — HOCH

**Problem**: OpenRouter ändert Preise regelmäßig. Eine hardcodierte `pricing.py` erfordert Code-Deployment für jede Preisänderung. Zudem fehlt eine Historisierung (welche Preise galten zum Zeitpunkt des Calls?).

**Empfehlung**: `ModelPricing`-Tabelle in PostgreSQL mit Gültigkeitszeitraum:
```sql
CREATE TABLE llm_model_pricing (
    id              BIGSERIAL PRIMARY KEY,
    public_id       UUID NOT NULL DEFAULT gen_random_uuid(),
    model           TEXT NOT NULL,
    input_per_1m    NUMERIC(12,8) NOT NULL,
    output_per_1m   NUMERIC(12,8) NOT NULL,
    valid_from      TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_until     TIMESTAMPTZ NULL,  -- NULL = aktuell gültig
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ NULL
);
CREATE UNIQUE INDEX llm_model_pricing_current_idx 
    ON llm_model_pricing (model) WHERE valid_until IS NULL AND deleted_at IS NULL;
```

Die Kosten werden beim Schreiben des `llm_calls`-Records kalkuliert und gespeichert — nicht zur Query-Zeit. Das ermöglicht präzises historisches Reporting auch nach Preisänderungen.

---

### H-02: Fehlender `error_message` — HOCH

**Problem**: `error BOOLEAN` allein erlaubt keine Fehleranalyse. Welcher Fehler trat auf? Rate-Limit? Timeout? Upstream-Fehler?

**Korrektur**:
```sql
error           BOOLEAN      NOT NULL DEFAULT FALSE,
error_code      TEXT         NULL,    -- 'rate_limit', 'timeout', 'upstream_error', etc.
error_message   TEXT         NULL,    -- Rohe Fehlermeldung (truncated auf 1000 Zeichen)
```

---

### H-03: Kein Data-Retention-Konzept — HOCH

**Problem**: `llm_calls` wächst ohne Begrenzung. Bei 100 Calls/Tag sind das 36.500 Rows/Jahr — überschaubar. Bei Agent-Tasks mit 1000 Calls/Tag: 365.000 Rows/Jahr. Ohne Retention-Policy gibt es nach 2 Jahren Betrieb Performance-Degradation.

**Empfehlung**: PostgreSQL-Partitionierung nach `created_at` (monatlich) + pg_partman für automatisches Lifecycle-Management:
```sql
-- Alternativ: Simples Cleanup-Skript via Celery Beat
-- Für initiale Implementierung ausreichend:
DELETE FROM llm_calls 
WHERE created_at < NOW() - INTERVAL '90 days' 
  AND deleted_at IS NOT NULL;
```

Oder TimescaleDB-Hypertable wenn Volumen > 1M Rows/Tag zu erwarten (overkill für aktuellen Use-Case).

---

## 3. Architektur-Alternativen

### Alternative A: OpenTelemetry + Grafana (empfohlen für Skalierung)

```
llm_mcp FastAPI
  → OTEL SDK (strukturierte Spans mit Attributes)
  → OTEL Collector (im mcp-hub Stack)
  → Grafana Tempo (Traces) + PostgreSQL (Business-Daten)
  → Grafana unified Dashboard
```

**Pro**: Industry-Standard, portabel, kombiniert Traces + Metrics + Logs  
**Contra**: ~3x mehr Infrastruktur, steile Lernkurve  
**Empfehlung**: Für aktuellen Use-Case Overkill. ADR-115-Ansatz ist richtig — aber mit den genannten Fixes.

### Alternative B: Django Admin + Chart.js (bereits im Stack)

```
llm_mcp → llm_calls Tabelle
  → bfagent-core Django-App mit Admin-View
  → Chart.js in Django Templates (HTMX-Refresh)
```

**Pro**: Kein neuer Infrastruktur-Baustein, einheitliche Auth  
**Contra**: Kein Alerting, kein Time-Series-UX, hoher Custom-Code-Aufwand  
**Empfehlung**: Als Ergänzung zu Grafana für operationale CRUD-Views (Preistabelle, Modell-Config).

### Alternative C (empfohlen als Ergänzung): Dual-Layer

```
Grafana: Ops-Dashboard (Kosten-Trend, Error-Rate, Model-Mix)
Django Admin: Business-Config (Preistabelle, Tenant-Limits, Alerts)
```

Das Beste aus beiden Welten — Grafana für Visualisierung, Django für Konfiguration.

---

## 4. Gesamtbewertung

| Kriterium | Bewertung |
|-----------|-----------|
| Architektur-Entscheidung (Grafana + PostgreSQL) | ✅ Richtig |
| Datenmodell | ❌ 3 Blocker (tenant_id, deleted_at, public_id) |
| Security | ⚠️ Read-Only-User fehlt |
| Performance | ⚠️ Synchrones Logging muss async werden |
| Betrieb | ⚠️ Retention + Preistabelle überdenken |
| Dashboard-Design | ✅ Panels sind sinnvoll, p95/p99 ergänzen |

**Empfehlung**: Blocker B-01 bis B-03 und Kritisch K-01/K-02 beheben, dann freigeben.  
Implementierungsplan in `ADR-115-implementation-plan.md`.
