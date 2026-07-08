---
id: ADR-256
title: "Migrate Orchestrator MCP transport from HTTP/SSE to stateless Streamable HTTP"
status: accepted
decision_date: 2026-06-23
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [achimdehnert]
domains: [orchestrator, mcp, infrastructure, integration]
supersedes: []
amends: [ADR-224]
depends_on: []
related: [ADR-101, ADR-224, ADR-238]
implementation_status: partial
tags: [orchestrator, mcp, transport, streamable-http, sse, stateless, resilience, deploy-resilience]
scope:
  include_paths:
    - "docs/adr/ADR-256-*"
---

# ADR-256: Orchestrator-MCP-Transport von HTTP/SSE auf stateless Streamable HTTP migrieren

> **Nummern-Hinweis:** 256 = nächste freie Nummer zum Draft-Zeitpunkt; final zur Merge-Zeit allokiert (ADR-228).

| Metadaten | |
|-----------|---|
| **Status** | Accepted |
| **Datum** | 2026-06-23 |
| **Autor** | Achim Dehnert |
| **Repo** | mcp-hub (`orchestrator_mcp/`) |
| **Amends** | ADR-224 (HTTP/SSE-Transport — Kernentscheidung bleibt, Mechanismus geändert) |
| **Treiber** | Issue mcp-hub#128 |

> **Review-Hinweis (2026-07-02, gelöst):** ADR-224 (das dieses ADR amendet) war zum
> Review-Zeitpunkt noch `proposed`. Auflösung: **ADR-224 wurde am 2026-07-02 akzeptiert**
> (Variante (a)) — es trägt nun als akzeptierte Entscheidung den remote-HTTP-Kern, dieses
> ADR-256-Amendment greift damit sauber auf dessen Mechanismus.

---

## Context and Problem Statement

ADR-224 hat den Orchestrator-MCP von stdio auf einen **zentralen, remote erreichbaren HTTP-Transport**
unter `https://orchestrator.iil.pet` gehoben — konkret über **HTTP/SSE** (`GET /sse` + `POST /messages/`).
Die *remote-HTTP*-Entscheidung ist weiterhin richtig (eine Memory-/Audit-Instanz, CI/Scheduled-Zugriff,
Standard-MCP-Clients). Geändert werden soll nur der **Transport-Mechanismus**.

Der SSE-Transport (`mcp.server.sse.SseServerTransport`) hat eine strukturelle Fragilität, die am
2026-06-23 produktiv zuschlug (Issue #128, beim `adr-handoff-extern --auto`-Pilot, G3):

- Eine MCP-Session ist an den **lebenden `GET /sse`-Stream** gebunden; sie lebt im **per-Prozess-Speicher**
  und wird beim Stream-Close aus dem Dict entfernt (`orchestrator_mcp/server.py:2051`, `connect_sse`-CM).
- **Jeder Container-Recreate leert diesen Store.** Belegt: Deploy mcp-hub#127 erzeugte den Container um
  06:38Z neu (`RestartCount=0`, `startedAt=06:38`); ein seit 05:13Z verbundener Client POSTete danach
  ~7,5 h auf die tote Pre-06:38-Session → **HTTP 404 „Could not find session"** bei jedem Call.
- `/mcp`-Reconnect und ein Session-Resume halfen nicht (gleiche `sessionId`, kein Kaltstart); der
  Claude-Code-Client re-handshaket nach Server-Recreate nicht (Upstream-Verhalten, nicht in unserem Repo).

**Verifiziert (read-only Diagnose, alle cheapest checks):** Dienst oben (`livez 200`), nginx korrekt für SSE
(`proxy_buffering off`, `http_version 1.1`, `Connection ''`, `read_timeout 300s`), `GET /sse` authed → 200,
**POST `/messages/` bei lebendem Stream → 202**. Server und Proxy sind also korrekt; die Ursache ist die
SSE-Session-an-Connection-Bindung + per-Prozess-Store, nicht Flapping/nginx/Auth.

**Wichtige Eigenschaft:** Der Orchestrator nutzt **kein Server→Client-Push** (keine `send_notification`/
Progress/Streaming; Client-Log: „server did not declare channel capability"). Er ist ein reiner
**Request/Response-Tool-Server** — die einzige Fähigkeit, für die SSE überhaupt nötig wäre, wird nicht gebraucht.

## Decision Drivers

- **Deploy-Resilienz:** Ein Container-Recreate darf keine verbundenen Clients kappen (Root-Cause #128).
- **Kein ungenutztes Feature bezahlen:** Der Server nutzt keinen Server→Client-Push — die einzige Fähigkeit, für die SSE nötig wäre, wird nicht gebraucht.
- **Kleiner, reversibler Blast-Radius:** Nur 2 externe Consumer-Einträge + wenige in-repo-Caller; additive Migration mit Rollback muss möglich bleiben.
- **Horizontale Skalierbarkeit:** Der per-Prozess-Session-Store verbietet heute >1 uvicorn-Worker.
- **ADR-224-Kernentscheidung bewahren:** remote-HTTP hinter iil.pet-Proxy + Zwei-Schlüssel-Bearer-Gate bleiben unverändert; nur der Mechanismus wechselt.

## Decision

Wir migrieren den Orchestrator-MCP-Transport auf **Streamable HTTP im stateless-Modus**
(`mcp.server.streamable_http.StreamableHTTPServerTransport`, stateless/`json_response`, mcp ≥ 1.28 —
im Prod-Container als verfügbar verifiziert). Ein einzelner Endpoint `https://orchestrator.iil.pet/mcp`
ersetzt `GET /sse` + `POST /messages/`.

- **Stateless** heißt: keine serverseitige Session → **kein Session-State, den ein Deploy/Recreate kappen kann**.
  Jeder Tool-Call ist ein unabhängiger, Bearer-gegateter HTTP-Request/Response.
- Die ADR-224-Kernentscheidung bleibt: zentraler remote-Orchestrator hinter dem iil.pet-Proxy,
  transport-agnostischer Server, Bearer-Gate (`_BearerGuardedASGI`, `ORCHESTRATOR_MCP_API_KEY` strikt).

**Migration — additiv & reversibel (kleiner Blast-Radius):**
1. `/mcp` (stateless Streamable HTTP) **zusätzlich** mounten; `/sse` + `/messages/` bleiben vorerst bestehen.
2. Consumer auf `/mcp` umstellen und je verifizieren — extern nur **2 Einträge** in `~/.claude.json`
   (`type: http`, `url: …/mcp`); intern: Discord-Bot + Headless-Runs in mcp-hub.
3. `/sse` + `/messages/` entfernen, sobald nichts mehr darauf zeigt (Consumer-Inventur als Gate).

Rollback = `/sse` bleibt bis Schritt 3 erhalten; jederzeit Rückbau auf SSE möglich.

## Umsetzungsstand (2026-07-05)

`implementation_status: partial` — Kernentscheidung (Deploy-Resilienz gegen #128) ist erreicht,
nur die Altlast-Entfernung (Schritt 3) steht noch aus:

- **Schritt 1 — erledigt:** `/mcp` (stateless Streamable HTTP, `StreamableHTTPSessionManager`)
  ist gemountet und **prod-live verifiziert** — `POST https://orchestrator.iil.pet/mcp/` mit Bearer
  liefert ein volles MCP-`initialize`-Result (HTTP 200, `orchestrator-mcp v1.28.1`). (mcp-hub #165,
  Commit `b4c0afc`.)
- **Schritt 2 — erledigt:** externe Consumer auf `/mcp` umgestellt — beide `~/.claude.json`-Einträge
  (`type: http`, `url: …/mcp/`) sowie das kanonische Template `mcp-hub/docs/claude-settings-template.json`
  (mcp-hub #166). Keine internen Hardcode-`/sse`-Caller gefunden (Discord/Headless nutzen keinen
  fixen `/sse`-URL). Damit ist die Wurzel von **#128 getilgt** (Issue via #166 geschlossen).
- **Schritt 3 — offen (bewusst gegated):** `/sse` + `/messages/` bleiben, bis eine Consumer-Inventur
  bestätigt, dass nichts mehr darauf zeigt. Erst danach → `implementation_status: complete`.

## Consequences

**Positiv**
- Deploys/Container-Recreates kappen **keine** Clients mehr — die Ursache von #128 ist strukturell getilgt.
- Robust gegen Proxy-Timeouts und Client-Stream-Drops (kein dauerhaft gehaltener Long-Stream).
- Ein Endpoint statt zwei; nginx braucht keine SSE-Sonderkonfig mehr.
- **Stateless ⇒ horizontal skalierbar:** mehrere uvicorn-Worker/Replicas werden möglich (heute verbietet
  der per-Prozess-Store >1 Worker).

**Negativ / Trade-offs**
- **Kein Server→Client-Push** mehr (heute nicht genutzt). Falls je nötig → stateful + Event-Store als
  künftiges Amendment (s. Alternative C).
- Consumer müssen die Config umstellen — klein, aber ein Cutover (2 CC-Einträge + in-repo-Caller).
- SSE-Clients, die nicht wechseln, brechen → daher die additive Phase mit Inventur-Gate.

**Neutral**
- Das Zwei-Schlüssel-Bearer-Modell (RUN-Key REST / MCP-Key Transport) wird unverändert auf `/mcp` angewandt.
- **Berührt die ADR-075-Posture nicht:** Der Transport-Wechsel ändert nichts an der read/write-Natur der
  Tools — Write-Ops (deploy/migrate/backup) laufen weiterhin über GitHub Actions, nicht über MCP; MCP-Tools
  bleiben read-only bzw. tragen die bestehenden Deprecation-Warnungen. Hier wechselt nur der Transport-Kanal.

## Alternatives considered

| # | Alternative | Verworfen, weil |
|---|---|---|
| A | **SSE behalten** (Status quo) | tilgt die Deploy-Wipe-Ursache nicht; Client-Re-Handshake ist Upstream |
| B | **SSE-Session off-process persistieren** | **infeasible** — die Session *ist* das lebende Stream-Paar, nicht serialisierbar |
| C | **Streamable HTTP stateful + Event-Store** (Redis/DB) | Komplexität + neue Dep ohne aktuellen Nutzen (kein Server-Push/Resumability nötig); bleibt der Amendment-Pfad, falls künftig gebraucht |
| D | **Nur client-seitig fixen** (CC re-handshake) | nicht in unserem Repo (Claude Code upstream); behebt die strukturelle Server-Fragilität nicht |

## Implementation Notes

- Server: `StreamableHTTPServerTransport` **stateless** unter `/mcp` mounten; davor das bestehende
  `_BearerGuardedASGI` (strikt `ORCHESTRATOR_MCP_API_KEY`).
- Consumer-Config: `~/.claude.json` → `mcpServers.orchestrator` = `{ "type": "http", "url": "https://orchestrator.iil.pet/mcp", "headers": { "Authorization": "Bearer …" } }`.
- nginx: `/mcp` als normaler `proxy_pass` (keine SSE-Sonderbehandlung nötig).
- Health-/Readiness-Endpunkte (`/livez/`, `/healthz/`, `/readyz/`) unverändert.

## Validation Criteria

- `workflow_execute(dry_run=true)` aus einer **frischen** und aus einer **mehrtägig-alten** CC-Session
  liefert resolved routing statt 404.
- Nach einem orchestrator-Deploy (Container-Recreate) arbeiten **bestehende** Clients ohne Reconnect/Neustart weiter.
- ≥3 aufeinanderfolgende Tool-Calls **über einen Deploy hinweg** ohne 404.
- Rollback erprobt: bricht ein Consumer auf `/mcp`, bleibt `/sse` bis zur Stabilisierung erreichbar.

## Risks

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R-1 | Consumer übersieht den Cutover → bricht | additive Phase, `/sse` bleibt bis alle migriert; Consumer-Inventur als Removal-Gate |
| R-2 | Künftiger Bedarf an Server→Client-Push | dann stateful + Event-Store als Amendment (Alternative C) |
| R-3 | mcp-lib Streamable-HTTP-Verhalten/Version-Drift | gegen mcp 1.28 (verifiziert vorhanden) implementieren + Transport-Tests; Pin beachten |

## Glossar

| Begriff | Bedeutung |
|---|---|
| **ASGI** | Die Python-Schnittstelle zwischen Webserver und Anwendung, über die der Transport eingebunden ist (hier mit einem Auth-Wächter davor). |
| **Bearer-Token** | Ein Geheimnis im `Authorization`-Header, mit dem sich ein Client beim Server ausweist. |
| **MCP** | Model Context Protocol — der Standard, über den Werkzeuge (Tools) einem KI-Client angeboten werden. Der Orchestrator ist ein solcher MCP-Server. |
| **per-Prozess-Store** | Die Sitzungen lagen im Speicher genau eines Server-Prozesses — wird der Prozess ersetzt (Deploy), sind alle Sitzungen weg. Genau das verursachte #128. |
| **Recreate (Container)** | Beim Deploy wird der Container nicht nur neu gestartet, sondern **neu erstellt** — ein frischer Prozess ohne die alten In-Memory-Sitzungen. |
| **Session (Sitzung)** | Ein serverseitig gemerkter Gesprächsfaden mit einem Client. Beim alten SSE-Transport lebte sie nur im Arbeitsspeicher *eines* Prozesses. |
| **SSE (Server-Sent Events)** | Eine Technik, bei der der Server eine **dauerhaft offene** Verbindung hält, um dem Client laufend Nachrichten zu schicken. Der bisherige Transport — fragil, weil die Sitzung an diese offene Verbindung gebunden ist. |
| **Stateless (zustandslos)** | Der Server merkt sich zwischen zwei Aufrufen **nichts** — jeder Aufruf ist in sich vollständig. Folge: ein Neustart/Deploy kann keine „Sitzung" verlieren, weil es keine gibt. |
| **Streamable HTTP** | Der modernere MCP-Transport: normale HTTP-Anfrage/Antwort pro Aufruf, ohne dauerhaft gehaltene Verbindung. |
| **Transport** | Der Übertragungsweg, über den Client und Server MCP-Nachrichten austauschen (z. B. stdio lokal, oder HTTP über das Netz). |

## Referenzen

- Issue **mcp-hub#128** (Symptom, vollständige read-only Diagnose, 202-Beweis, Client-Log-Korrelation).
- Amendet **ADR-224** (HTTP/SSE-Transport — Kernentscheidung remote-HTTP bleibt).
- `orchestrator_mcp/server.py:2041-2060` (SSE-Wiring), `:2148-2191` (`_BearerGuardedASGI`), `:2332-2374` (Lifespan + Routes).
