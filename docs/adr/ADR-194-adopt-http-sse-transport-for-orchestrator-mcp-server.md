---
id: ADR-194
title: Adopt HTTP/SSE Transport for Orchestrator MCP Server
status: proposed
decision_date: 2026-05-10
valid_from: 2026-05-10T00:00:00Z
deciders:
  - Achim Dehnert
domains:
  - orchestrator
  - mcp
  - infrastructure
  - integration
rationale_summary: >-
  Expose the orchestrator MCP server over HTTP/SSE at
  https://orchestrator.iil.pet/sse so Claude Code sessions and CI jobs across
  hosts share one routing/memory/audit instance. Stdio-only locked us into a
  per-workstation process; HTTP/SSE is the standard MCP transport and
  integrates with the iil.pet proxy.
repo: mcp-hub
consumers:
  - dev-hub
  - bfagent
  - travel-beat
  - weltenhub
  - risk-hub
  - coach-hub
  - ttz-hub
  - meiki-hub
decision_drivers:
  - id: D-1
    weight: critical
    driver: >-
      Multi-client remote access to orchestrator capabilities (routing, memory,
      LLM calls, headless runs) from any Claude Code session
  - id: D-2
    weight: high
    driver: >-
      Standard MCP transport compatible with existing clients (Claude Code,
      Cascade) without bespoke adapters
  - id: D-3
    weight: high
    driver: >-
      Centralised observability and audit logging on a single orchestrator
      instance instead of per-workstation processes
  - id: D-4
    weight: medium
    driver: >-
      Auth and TLS handled at the iil.pet reverse proxy boundary, keeping the
      MCP server itself transport-agnostic
  - id: D-5
    weight: medium
    driver: >-
      Allow scheduled/automated jobs (cron, CI) to invoke orchestrator tools
      without local stdio binding
implementation_status: none
---

# ADR-194: Adopt HTTP/SSE Transport for Orchestrator MCP Server

| Metadaten | |
|-----------|---|
| **Status** | Proposed |
| **Datum** | 2026-05-10 |
| **Autor** | Achim Dehnert |
| **Repo** | mcp-hub (`orchestrator_mcp/`) |
| **Endpoint** | `https://orchestrator.iil.pet/sse` |
| **Consumers** | dev-hub, bfagent, travel-beat, weltenhub, risk-hub, coach-hub, ttz-hub, meiki-hub |

---

## Context

Der `orchestrator` MCP-Server (Routing, Memory, LLM-Calls, Headless Runs, Audit-Log) lief bisher
ausschließlich über **stdio**. Damit war jede Claude-Code-Session an einen lokal gestarteten
Orchestrator-Prozess gebunden. Mehrere Workstations (Dev `88.99.38.75`, Prod `88.198.191.108`,
lokale Notebooks) hielten parallele, voneinander isolierte Instanzen — mit getrennten Memory-
Stores, getrenntem Audit-Log und ohne gemeinsame Sicht auf Recurring-Errors.

Mit wachsender Anzahl Repos (achimdehnert, ttz-lif, meiki-lra) und der Einführung von Scheduled
Routines (`/schedule`, Cron-getriggerte Headless Runs) ist eine **zentrale, remote erreichbare
Orchestrator-Instanz** notwendig. CI-Runner und automatisierte Jobs haben kein stdio-Terminal,
können aber HTTP-Endpunkte ansprechen. Cascade und Claude Code unterstützen MCP über HTTP/SSE
nativ — eigene Adapter sind nicht nötig.

Die iil.pet-Infrastruktur (Reverse-Proxy, TLS-Termination, Auth-Header) ist bereits etabliert
und wird für `dev-hub.iil.pet` und andere Services genutzt. Ein zusätzlicher Endpoint
`orchestrator.iil.pet/sse` fügt sich ohne neue Infrastrukturkomponenten ein.

## Decision

Wir betreiben den Orchestrator-MCP-Server **primär über HTTP/SSE** unter
`https://orchestrator.iil.pet/sse`. Die stdio-Transport-Variante bleibt für lokale Entwicklung
und Tests erhalten, ist aber nicht mehr der Standard für produktive Sessions. Auth und TLS
terminieren am iil.pet-Reverse-Proxy; der MCP-Server selbst bleibt transport-agnostisch und
kennt keine Auth-Logik. Alle Consumer-Repos (dev-hub, bfagent, travel-beat, weltenhub,
risk-hub, coach-hub, ttz-hub, meiki-hub) konfigurieren den Orchestrator-MCP-Eintrag auf den
HTTP/SSE-Endpoint.

## Consequences

**Positiv**
- Eine zentrale Memory-/Audit-Instanz für alle Sessions und Hosts (D-1, D-3).
- Scheduled Routines und CI-Jobs können Orchestrator-Tools aufrufen (D-5).
- Keine bespoke-Adapter — Standard-MCP-Clients funktionieren out-of-the-box (D-2).
- Auth-/TLS-Komplexität bleibt im Proxy, MCP-Server bleibt schlank (D-4).
- Horizontal skalierbar: bei Bedarf mehrere Worker hinter dem Proxy.

**Negativ**
- Single Point of Failure: Ausfall von `orchestrator.iil.pet` legt alle Sessions lahm — Monitoring + Fallback auf stdio nötig.
- Latenz pro Tool-Call steigt gegenüber stdio (Netzwerk-Roundtrip, typ. 20–80 ms).
- SSE-Verbindungen müssen Reverse-Proxy-Timeouts überleben (nginx `proxy_read_timeout`).
- Auth am Proxy heißt: ein kompromittierter Header → voller Tool-Zugriff. Rotations-Policy nötig.

## Alternatives considered

- **Stdio-only beibehalten** — verworfen: blockiert Multi-Host-Nutzung, CI und Scheduled Routines (D-1, D-5).
- **WebSocket-Transport** — verworfen: SSE ist der MCP-Standard für Server→Client-Streams; WebSocket bietet hier keinen Mehrwert und erhöht Proxy-Komplexität.
- **Pro-Repo eigene MCP-Instanz** — verworfen: dupliziert Memory und Audit-Log, widerspricht D-3.
- **gRPC** — verworfen: nicht im MCP-Standard, würde Custom-Clients erfordern (D-2).

## Implementation Notes

- Endpoint: `https://orchestrator.iil.pet/sse`
- Server-Repo: `mcp-hub/orchestrator_mcp/`
- Consumer-Konfig: `~/.claude/settings.json` → `mcpServers.orchestrator` mit `transport: "sse"`
- Health-Check: `GET https://orchestrator.iil.pet/health` (separat vom SSE-Stream)
- Audit-Log: zentral in der Orchestrator-Instanz, nicht mehr pro Workstation
