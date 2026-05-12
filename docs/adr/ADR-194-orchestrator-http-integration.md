# ADR-194: Adopt HTTP Transport for orchestrator_mcp

## Metadaten

| Attribut          | Wert                                                                 |
|-------------------|----------------------------------------------------------------------|
| **Status**        | Proposed                                                             |
| **Scope**         | platform                                                             |
| **Erstellt**      | 2026-05-12                                                           |
| **Autor**         | Achim Dehnert                                                        |
| **Reviewer**      | –                                                                    |
| **Supersedes**    | –                                                                    |
| **Superseded by** | –                                                                    |
| **Relates to**    | ADR-044 (MCP-Hub Architecture Consolidation), ADR-107 (Extended Agent Team), ADR-108 (Agent QA Cycle), ADR-112 (Agent Skill Registry), ADR-176 (MCP-Server SSOT), ADR-178 (LLM-Gateway Consolidation) |

## Repo-Zugehörigkeit

| Repo            | Rolle      | Betroffene Pfade / Komponenten                                |
|-----------------|------------|---------------------------------------------------------------|
| `platform`      | Primär     | `orchestrator_mcp/server.py`, `orchestrator_mcp/http_app.py` (neu), `orchestrator_mcp/transport/` (neu), `docs/mcp/SERVERS.md` |
| `dev-hub`       | Sekundär   | `mcp_config` / Workflow-Calls auf `https://orchestrator.…`    |
| `bfagent`       | Sekundär   | CI-Workflows die `analyze_task` / `verify_task` aufrufen      |
| `infra-deploy`  | Sekundär   | Reverse-Proxy-/Nginx-Config, TLS-Cert, Hetzner-Host           |

---

## Decision Drivers

- **Remote-Konsumenten**: CI/GitHub-Actions, Dashboards (Grafana per ADR-115/165) und entfernte Agents können den stdio-Server heute nicht erreichen — sie müssten ihn lokal spawnen, was in einem CI-Runner weder reproduzierbar noch performant ist.
- **Single-Instance-State**: `agent_memory`, `scan_repo` und `get_infra_context` (ADR-112) schreiben in das git-getrackte `AGENT_MEMORY.md` — parallele stdio-Subprozesse erzeugen Lock-Konflikte (`.agent_memory.lock`). Ein zentraler HTTP-Endpunkt serialisiert Zugriffe sauber.
- **Multi-Client-Support**: ADR-044 (MCP-Hub Consolidation) und ADR-176 (MCP-Server SSOT) sehen den Orchestrator als geteilten Service über alle 9 Hubs vor; stdio kann nur ein Parent-Prozess gleichzeitig sprechen.
- **MCP-Spec-Alignment**: MCP-Spec 2025-03-26 ersetzt SSE durch **Streamable HTTP** als offiziellen Remote-Transport — wir folgen dem Standard statt einer Eigenentwicklung.
- **Observability**: Ein HTTP-Endpoint liefert Latenzen, Status-Codes und Request-IDs out-of-the-box (ADR-115 Grafana-Dashboard), während stdio nur über stderr-Logs beobachtbar ist.

---

## 1. Context and Problem Statement

`orchestrator_mcp/server.py` läuft heute ausschließlich als stdio-JSON-RPC-MCP-Server (`python -m orchestrator_mcp.server`). Clients (Cascade/Windsurf, Claude Code, Cursor) starten ihn pro Session als Subprozess. Die in ADR-107/108/112 ergänzten Tools (`agent_team_status`, `agent_plan_task`, `analyze_task`, `evaluate_task`, `verify_task`, `agent_memory`, `scan_repo`, …) sollen aber **auch** aus Nicht-IDE-Kontexten erreichbar sein.

### 1.1 Ist-Zustand

| Aspekt                | Heute (stdio)                                | Bedarf                                    |
|-----------------------|----------------------------------------------|-------------------------------------------|
| Transport             | JSON-RPC 2.0 über stdin/stdout               | Zusätzlich JSON-RPC über HTTP             |
| Auth                  | implizit (lokaler Prozess)                   | Token (`X-API-Key`) + IP-Allowlist        |
| Konsumenten           | 1 IDE-Subprozess                             | n Clients (IDE, CI, Dashboards, Agents)   |
| Persistenz            | `AGENT_MEMORY.md` (git-tracked, file-lock)   | Serialisiert per Worker-Singleton         |
| Observability         | stderr-Log                                   | OpenTelemetry-kompatibel (ADR-115)        |
| Deployment            | gar nicht (Library)                          | Container hinter Cloudflare/Nginx         |

### 1.2 Warum jetzt

ADR-191 (iil-codeguard) und ADR-193 (Deployment-Audit) wollen `analyze_task`/`verify_task` aus GitHub-Actions aufrufen. ADR-115 (Grafana-Agent-Dashboard) braucht `agent_team_status` als HTTP-Datenquelle. Ohne HTTP-Transport müsste jeder Konsument Python + Repo-Checkout + Secrets bekommen — das skaliert nicht.

---

## 2. Considered Options

### Option A: FastAPI-Wrapper mit Streamable-HTTP-Transport (MCP-Spec 2025-03-26) ✅

Eigene ASGI-App (`orchestrator_mcp/http_app.py`) mit
- `POST /mcp` — MCP-Streamable-HTTP-Endpoint (JSON-RPC + optional SSE-Streaming)
- `GET /mcp` — SSE-Subscription für Server-Push (Session-Resumption)
- `GET /healthz` — Container-Healthcheck (ADR-021)
- `GET /readyz` — DB/Memory-Lock-Probe
- `GET /metrics` — Prometheus (ADR-115)

Die bestehende `_TOOLS`-Registry und `_handle_request` aus `server.py` werden in `orchestrator_mcp/transport/jsonrpc.py` extrahiert und sowohl vom stdio- als auch vom HTTP-Adapter benutzt — **eine** Wahrheit für die Tool-Definitionen.

**Pros:**
- MCP-Spec-konform, kompatibel mit Cursor/Claude Desktop/Windsurf Remote-MCP
- ASGI ermöglicht echte Concurrency und Streaming (Token-by-Token bei längeren Tools)
- FastAPI generiert automatisch OpenAPI für Nicht-MCP-Clients
- Wiederverwendung der existierenden stdio-Tool-Registry (Single Source of Truth)
- Healthcheck/Readiness passt in unsere docker-compose-Standards (ADR-056, ADR-021)

**Cons:**
- Zusätzliche Dependency (`fastapi`, `uvicorn`)
- Streamable-HTTP ist relativ neu — wenige Reference-Clients

### Option B: Reines REST-API (kein MCP-Wire-Format)

Pro Tool ein REST-Endpoint (`POST /v1/tools/agent_plan_task`).

**Pros:**
- Einfacher für Nicht-MCP-Clients (CI, Dashboards)
- Triviale Authentifizierung & Caching

**Cons:**
- Doppelte Tool-Definition (stdio-Schema vs. OpenAPI-Schema) → Drift-Risiko
- MCP-Clients (Cascade, Claude Desktop) müssten einen Bridge-Adapter bauen
- Verliert Streaming / Server-Push
- → **Abgelehnt weil:** Wir wollen MCP-Clients **ohne** Custom-Bridge anbinden.

### Option C: SSE-only (alte MCP-Spec, vor 2025-03-26)

**Pros:**
- Eine bestehende Python-Library (`mcp[sse]`) deckt das ab

**Cons:**
- SSE ist von der MCP-Spec deprecated; Streamable-HTTP ist der Nachfolger
- Reverse-Proxy-Stolperfallen (Pufferung, Timeout) sind höher als bei normalem POST
- → **Abgelehnt weil:** Wir würden Tech-Debt am Tag 1 einführen.

### Option D: gRPC

**Pros:**
- Strenge Typisierung, bidirektionales Streaming

**Cons:**
- Kein MCP-Client spricht gRPC; eigener Adapter zwingend
- HTTP-Reverse-Proxy-Setup (Cloudflare, Nginx) erfordert HTTP/2 end-to-end
- → **Abgelehnt weil:** Komplexität ohne Nutzen für unsere Konsumenten.

---

## 3. Decision Outcome

**Gewählte Option: Option A — FastAPI + Streamable-HTTP**

Wir extrahieren die Tool-Registry aus `server.py` in ein transport-neutrales Modul und bauen darauf zwei Adapter: den existierenden stdio-Adapter und einen neuen FastAPI-Adapter. Der HTTP-Server läuft als Container, ist über Cloudflare-Proxy (ADR-102) erreichbar und folgt unseren Deployment-Standards (ADR-021, ADR-056, ADR-166). Damit bekommen CI/Dashboards und Remote-MCP-Clients denselben Endpunkt ohne Code-Duplikation.

---

## 4. Implementation Details

### 4.1 Modul-Layout

```
orchestrator_mcp/
├── __init__.py
├── server.py              # stdio-Adapter (unverändertes Verhalten)
├── http_app.py            # NEU: FastAPI-Adapter
├── transport/
│   ├── __init__.py
│   ├── registry.py        # NEU: extrahiert aus server.py:_TOOLS
│   └── jsonrpc.py         # NEU: extrahiert aus server.py:_handle_request
├── tools.py               # unverändert
└── …
```

### 4.2 HTTP-Endpunkte

| Methode | Pfad        | Zweck                                                 |
|---------|-------------|-------------------------------------------------------|
| POST    | `/mcp`      | Streamable-HTTP JSON-RPC (initialize, tools/list, tools/call) |
| GET     | `/mcp`      | SSE-Stream für Session-Resumption (optional)          |
| POST    | `/v1/tools/{name}` | REST-Convenience (1:1 auf `tools/call` gemappt) |
| GET     | `/healthz`  | Liveness — gibt `{"status": "ok", "version": …}` zurück |
| GET     | `/readyz`   | Readiness — prüft `AGENT_MEMORY.md`-Lock + DB-Reach    |
| GET     | `/metrics`  | Prometheus-Exporter (Request-Rate, Tool-Latenz, Errors) |

### 4.3 Authentifizierung

- **Inbound**: `X-API-Key` Header gegen Liste aus `ORCHESTRATOR_API_KEYS` (env, SOPS-encrypted per ADR-045/159).
- **Service-to-Service**: zusätzlicher mTLS-Layer auf Cloudflare-Tunnel (ADR-102).
- **Rate-Limiting**: starlette-limiter, 60 req/min pro Key (default).

### 4.4 Concurrency & State

- Uvicorn `--workers 1` initial — wegen `AGENT_MEMORY.md` (file-locked). Skalierung über Worker-Anzahl erst nach Migration auf DB-backed Memory (Open Question OQ-2).
- Lese-Tools (`agent_team_status`, `get_infra_context`, `get_payment_context`) erhalten ein `Cache-Control: max-age=10` Layer.
- Schreib-Tools (`agent_memory upsert`, `scan_repo`) laufen durch eine `asyncio.Lock`-Queue.

### 4.5 Deployment-Skeleton

```yaml
# orchestrator_mcp/docker-compose.prod.yml (Auszug, ADR-021/056 konform)
services:
  orchestrator-http:
    image: ghcr.io/achimdehnert/orchestrator-http:${TAG}
    restart: unless-stopped
    env_file: .env.prod        # ADR-022
    mem_limit: 512m            # ADR-021
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=2).status==200 else 1)"]
      interval: 30s
      timeout: 3s
      retries: 3
    ports:
      - "127.0.0.1:8090:8000"  # ADR-164 Port-Strategie
```

Reverse-Proxy: Nginx (per ADR-166) terminiert TLS auf `orchestrator.platform.<domain>` und reicht an `127.0.0.1:8090` weiter.

### 4.6 Client-Onboarding

| Konsument        | Wie aufrufen                                                                 |
|------------------|------------------------------------------------------------------------------|
| Cascade/Windsurf | `mcp_config` mit `transport: http`, `url: https://orchestrator.…/mcp`         |
| Claude Desktop   | `mcpServers.orchestrator.transport: "http"`, `url: …`                         |
| GitHub Actions   | `curl -H "X-API-Key: $ORCH_KEY" -d @body.json https://orchestrator.…/v1/tools/analyze_task` |
| Grafana          | JSON-API-Datasource auf `/v1/tools/agent_team_status`                         |

---

## 5. Migration Tracking

| Repo / Service     | Phase                                            | Status        | Datum | Notizen |
|--------------------|--------------------------------------------------|---------------|-------|---------|
| `platform`         | 1. Extract `transport/registry.py` + `jsonrpc.py` | ⬜ Ausstehend | –     | rein refactor, kein Verhaltenswechsel |
| `platform`         | 2. `http_app.py` + Tests (stdio-Verhalten unverändert) | ⬜ Ausstehend | –     | – |
| `platform`         | 3. Dockerfile + `docker-compose.prod.yml`        | ⬜ Ausstehend | –     | Multi-Stage, USER app:1000 (ADR-056) |
| `infra-deploy`     | 4. Nginx-Vhost + Cloudflare-DNS                  | ⬜ Ausstehend | –     | TLS via certbot |
| `dev-hub`/`bfagent`| 5. `mcp_config` auf HTTP umstellen               | ⬜ Ausstehend | –     | stdio bleibt für lokale Dev |

---

## 6. Consequences

### 6.1 Good

- CI/Dashboards/Remote-Agents können Orchestrator-Tools ohne lokalen Python-Stack erreichen.
- Zentrale Stelle für Rate-Limiting, Auth, Observability — keine Eigenheit pro Konsument.
- Streamable-HTTP ermöglicht spätere Streaming-Tools (z. B. progressives `agent_plan_task`-Replay).
- Tool-Registry-Single-Source-of-Truth (stdio + HTTP benutzen dieselbe Definition).

### 6.2 Bad

- Zusätzlicher Container, Port, TLS-Cert und Nginx-Vhost zu betreiben.
- `AGENT_MEMORY.md` als File-Lock skaliert nicht horizontal — bis OQ-2 gelöst ist, bleiben wir bei `--workers 1`.
- FastAPI/Uvicorn vergrößern die Image-Size um ~30 MB.

### 6.3 Nicht in Scope

- Migration der Memory-Persistenz von Markdown auf Postgres (gesondertes ADR-Vorschlag).
- WebSocket-Support — Streamable-HTTP deckt unsere Use-Cases ab.
- Multi-Tenant-Isolierung pro API-Key (ADR-072) — erst wenn externe Konsumenten andocken.

---

## 7. Risks

| Risiko                                                | W'keit | Impact   | Mitigation |
|-------------------------------------------------------|--------|----------|-----------|
| `AGENT_MEMORY.md`-Lock-Konflikt unter Last            | Mittel | Mittel   | `--workers 1` + asyncio-Lock; Migration auf DB-backed Memory geplant |
| API-Key-Leak via Logs                                 | Niedrig| Hoch     | Headers im Log-Format maskieren; SOPS-encrypted Secrets (ADR-045) |
| Streamable-HTTP-Spec-Änderungen vor GA                | Niedrig| Mittel   | Spec-Version pinnen, Smoke-Test bei Library-Updates |
| Cloudflare-Tunnel-Ausfall macht Tool-Calls in CI rot  | Niedrig| Mittel   | stdio-Fallback bleibt, CI-Jobs retryen 3x mit Backoff |
| Dependency-Inflation (FastAPI/Uvicorn)                | Mittel | Niedrig  | Optional-Extra `pip install orchestrator-mcp[http]` |

---

## 8. Confirmation

1. **Contract-Tests** (ADR-155/184): `tests/orchestrator_mcp/test_http_parity.py` ruft jedes Tool einmal über stdio und einmal über HTTP auf und vergleicht die Antworten byte-genau.
2. **Healthcheck-Gate** (ADR-056): Deployment-Pipeline schlägt fehl, wenn `/healthz` 60 s nach Container-Start kein 200 OK liefert.
3. **REFLEX/codeguard-Audit** (ADR-191/193): `compose_security`-Check verifiziert, dass `docker-compose.prod.yml` des HTTP-Service alle Standards (env_file, mem_limit, healthcheck, restart-Policy) erfüllt.
4. **Drift-Detector** (ADR-059): staleness-Schwelle 12 Monate, geprüfte Pfade siehe Governance-Hinweise.

---

## 9. More Information

- MCP Spec — Streamable HTTP Transport: https://modelcontextprotocol.io/specification/2025-03-26/basic/transports
- ADR-044: MCP-Hub Architecture Consolidation — Hub-Single-Service-Pattern
- ADR-107/108/112: Quellen der heute exponierten Orchestrator-Tools
- ADR-176: MCP-Server SSOT — warum genau **ein** Orchestrator-Server
- ADR-021/056/166: Deployment-/Compose-/Nginx-Standards die der HTTP-Service erfüllen muss

---

## 10. Changelog

| Datum      | Autor          | Änderung                              |
|------------|----------------|---------------------------------------|
| 2026-05-12 | Achim Dehnert  | Initial: Status Proposed              |

---

## Open Questions

- **OQ-1**: Setzen wir den HTTP-Service auf den existierenden `orchestrator_mcp`-Container oder eigenen Service? → Empfehlung: eigener Container, gleiches Image, anderer Entrypoint (`uvicorn orchestrator_mcp.http_app:app`).
- **OQ-2**: Wann migrieren wir `AGENT_MEMORY.md` von Markdown-File auf Postgres? Solange File-Lock vorhanden ist, sind `--workers > 1` unmöglich.
- **OQ-3**: Brauchen wir per-Tool Authorization (z. B. `scan_repo` nur für CI-Key, nicht für Dashboard-Key)? → Vorschlag: RBAC erst wenn externe Konsumenten andocken.

---

<!--
  Drift-Detector (ADR-059):
  - staleness_months: 12
  - drift_check_paths:
      - orchestrator_mcp/http_app.py
      - orchestrator_mcp/transport/registry.py
      - orchestrator_mcp/transport/jsonrpc.py
  - supersedes_check: true
-->
