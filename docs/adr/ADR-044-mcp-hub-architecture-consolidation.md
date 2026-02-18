# ADR-044: MCP-Hub Architecture Consolidation

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-18 |
| **Author** | Achim Dehnert |
| **Reviewers** | ADR Board |
| **Supersedes** | — |
| **Related** | ADR-042 (Dev Environment), ADR-009 (Deployment Architecture) |
| **Based on** | mcp-hub-adr-review.md (Critical Review 2026-02-18) |

---

## 1. Context

### 1.1 Problem Statement

Das `mcp-hub` Repository enthält MCP-Server für verschiedene Domänen. Eine
kritische Codeanalyse (mcp-hub-adr-review.md) identifizierte 7 Problembereiche
mit Schweregrad P0–P3. Die vorliegende ADR verifiziert jeden Befund gegen
den tatsächlichen Codestand, korrigiert veraltete Bewertungen und definiert
die konsolidierte Architekturentscheidung.

### 1.2 Ist-Zustand (verifiziert 2026-02-18)

**Aktive Server (6):**

| Server | MCP-Ansatz | Entry Point | Lifecycle | Pydantic-Models |
|--------|-----------|-------------|-----------|------------------|
| `deployment_mcp` | Raw MCP SDK | `mcp.server.stdio_server` | Kein Lifespan | Ja (Settings) |
| `travel_mcp` | **FastMCP** | `mcp.run()` | **lifespan()** ✅ | Ja |
| `illustration_mcp` | **FastMCP** | `mcp.run()` | Keiner | Ja |
| `ifc_mcp` | Raw MCP SDK | `stdio_server` | **lifespan()** ✅ | Ja |
| `llm_mcp` | Raw MCP SDK + DIY Main | `asyncio.run()` | Keiner | Nein |
| `orchestrator_mcp` | Raw MCP SDK | `stdio_server` | Keiner | Nein |

**Archivierte Server (12 in `_archive/`):**

`bfagent_mcp`, `bfagent_sqlite_mcp`, `book_writing_mcp`, `analytics_mcp`,
`german_tax_mcp`, `cad_mcp`, `dlm_mcp`, `mcp_core`, `mcp_runner_ui`,
`physicals_mcp`, `research_mcp`, `ui_hub`

### 1.3 Bewertung des Original-Reviews

Das Review-Dokument identifiziert reale Defekte, **überschätzt jedoch die
Dringlichkeit erheblich**, weil 5 von 7 ADRs primär archivierte Server
adressieren:

| Review-ADR | Betroffener Code | Status | Korrigierte Priorität |
|------------|-----------------|--------|----------------------|
| ADR-001: SimpleMCPServer → FastMCP | `_archive/bfagent_mcp` | **ARCHIVIERT** | ~~P0~~ → Erledigt |
| ADR-002: MetaPrompter eliminieren | `_archive/bfagent_mcp` | **ARCHIVIERT** | ~~P2~~ → Erledigt |
| ADR-003: Architektur vereinheitlichen | Aktive Server | **OFFEN** | P2 → **P2** ✅ |
| ADR-004: Sicherheitsdefizite | Gemischt | **TEILWEISE** | P0/P1 → **P1** |
| ADR-005: SQLite Timeout unsicher | `_archive/bfagent_sqlite_mcp` | **ARCHIVIERT** | ~~P2~~ → Erledigt |
| ADR-006: Server-Template | Aktive Server | **OFFEN** | P3 → **P2** |
| ADR-007: Singleton-Lifecycle | Aktive Server | **OFFEN** | P2 → **P2** ✅ |

**Fazit:** 3 von 7 Befunden sind durch Archivierung bereits gelöst. Die
verbleibenden 4 Befunde betreffen aktive Server und werden in dieser ADR
als konsolidierte Maßnahmen definiert.

---

## 2. Verifizierte Befunde (nur aktive Server)

### 2.1 Architektur-Divergenz — 3 verschiedene Ansätze in 6 Servern

**Befund bestätigt.** Die aktiven Server nutzen drei verschiedene Ansätze:

| Ansatz | Server | Boilerplate | Protokoll-Compliance |
|--------|--------|-------------|---------------------|
| FastMCP | `travel_mcp`, `illustration_mcp` | ~5 Zeilen | Automatisch ✅ |
| Raw MCP SDK | `deployment_mcp`, `ifc_mcp`, `orchestrator_mcp` | ~50–100 Zeilen | Manuell, korrekt |
| **DIY Main Loop** | `llm_mcp` | ~120 Zeilen | **Defekt** ❌ |

`llm_mcp/__main__.py` (Zeile 595) enthält denselben DIY-JSON-RPC-Loop wie
das archivierte `bfagent_mcp`:

```python
# llm_mcp/__main__.py:595
"error": {"code": -32603, "message": f"Internal error: {str(e)}"}
```

Zusätzlich: Kein Support für `notifications/initialized` (Notification wird
als Error beantwortet), kein `ping`, kein Graceful Shutdown.

**Bewertung:** `llm_mcp` ist der letzte Server mit DIY-Protokollstack und
muss migriert werden.

### 2.2 Singleton-Lifecycle ohne Cleanup

**Befund bestätigt in 3 aktiven Servern:**

| Server | Client | `close()` vorhanden | Wird aufgerufen |
|--------|--------|---------------------|------------------|
| `deployment_mcp` | `HetznerClient` | Ja | **Nein** ❌ |
| `deployment_mcp` | `DNSClient` | Ja | **Nein** ❌ |
| `travel_mcp` | `AmadeusClient` | Nein | — |
| `ifc_mcp` | Database Connection | Ja | **Ja** ✅ |

`deployment_mcp` erstellt `httpx.AsyncClient` Instanzen lazy, hat korrekte
`close()` Methoden, aber keinen Lifespan-Hook der diese aufruft. Bei
langlebigen Sessions akkumulieren offene HTTP/2-Connections.

`travel_mcp` hat einen Lifespan-Hook für Provider-Initialisierung, aber
der `AmadeusClient` Singleton hat keinen `close()`-Pfad.

### 2.3 Error-Message-Leaking

**Befund bestätigt in 2 aktiven Servern:**

- `llm_mcp/__main__.py:595` — `f"Internal error: {str(e)}"` an Client
- `llm_mcp/http_gateway.py:179` — `error=str(e)` in Response
- `orchestrator_mcp/local_tools.py` — `"error": str(exc)` in mehreren Funktionen

`deployment_mcp`, `travel_mcp`, `illustration_mcp`, `ifc_mcp` sind sauber.

### 2.4 Sicherheitsdefizite — Residual

**Hardcoded Pfade und Log-Dateien:** Nur in `_archive/`. Aktive Server sauber.

**Aber:** `_archive/` ist weiterhin Teil der Git-History. Ein
`git filter-repo` auf die gesamte History wurde nicht durchgeführt.
Die Dateien sind über `git log` und alte Commits auffindbar.

**Aktuell exponierte Informationen:**

- Benutzername (`achim`) in 8+ Dateipfaden
- `mcp_server.log` mit Request-Payloads (versioniert)
- MCP-Konfigurationspfade

**Bewertung:** Da das Repository privat ist, ist das Risiko gering.
Bei einem Public-Push oder Fork wären diese Daten exponiert. Die
Archivierung allein reicht nicht — Git-History muss bereinigt werden.

---

## 3. Decision

### 3.1 Alle aktiven Server auf FastMCP standardisieren

Migrationspriorität:

| Priorität | Server | Aufwand | Begründung |
|-----------|--------|---------|------------|
| **P1** | `llm_mcp` | 2–3h | DIY-Protokollstack, Error-Leaking, kein Shutdown |
| **P2** | `orchestrator_mcp` | 2–3h | Manuelles `inputSchema`, Error-Leaking |
| **P3** | `deployment_mcp` | 4–6h | Funktional korrekt, aber ~100 Zeilen Boilerplate |
| **P3** | `ifc_mcp` | 3–4h | Hat Lifespan, funktional korrekt |

`travel_mcp` und `illustration_mcp` sind bereits auf FastMCP ✅.

### 3.2 Verbindliches Server-Template (basierend auf `travel_mcp`)

```text
<server_name>/
├── src/<server_name>/
│   ├── __init__.py           # __version__
│   ├── __main__.py           # python -m <server_name> → mcp.run()
│   ├── server.py             # FastMCP instance + @mcp.tool()
│   ├── settings.py           # pydantic-settings, env-basiert
│   ├── models.py             # Pydantic Input/Output-Modelle
│   └── clients/              # Externe API-Clients (optional)
├── tests/
│   ├── conftest.py
│   └── test_tools.py
├── pyproject.toml            # hatchling, ruff, pytest
├── README.md
└── CHANGELOG.md
```

**Regeln:**

- `FastMCP` als einziger MCP-Protokollstack
- `pydantic-settings` für Konfiguration (12-Factor)
- `pyproject.toml` mit `hatchling` Build-Backend
- `src/` Layout (kein Flat Layout)
- Mindest-Testabdeckung 80% für Tool-Funktionen
- Keine Dateien im Package-Root (keine `QUICK_TEST.py`, `DIRECT_TEST.py`)
- Keine absoluten Pfade, keine Log-Dateien im Repository

### 3.3 Lifecycle-Hooks für alle Clients

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(server):
    # Initialize
    hetzner = HetznerClient()
    dns = DNSClient()
    server.state["hetzner"] = hetzner
    server.state["dns"] = dns
    try:
        yield
    finally:
        await hetzner.close()
        await dns.close()

mcp = FastMCP(name="deployment-mcp", lifespan=lifespan)
```

Alle Clients mit HTTP-Sessions oder DB-Connections MÜSSEN über
Lifecycle-Hooks verwaltet werden.

### 3.4 Error-Sanitisierung (Standard für alle Server)

```python
import logging

logger = logging.getLogger(__name__)

@mcp.tool()
async def my_tool(params: MyInput) -> str:
    try:
        return await _execute(params)
    except Exception as e:
        logger.exception("Tool execution failed")
        return "Interner Fehler. Details im Server-Log."
```

Keine Exception-Messages, Stack-Traces oder Dateipfade an den Client.

### 3.5 Git-History-Bereinigung

```bash
# Einmalig ausführen nach Backup:
pip install git-filter-repo
git filter-repo --path _archive/ --invert-paths
```

**Alternativ** (weniger invasiv): `.gitignore` für `_archive/` und
Akzeptanz, dass die History Altlasten enthält. Bei einem Repository,
das privat bleibt, ist dies vertretbar.

---

## 4. Rejected Alternatives

### 4.1 Raw MCP SDK beibehalten

Abgelehnt. 3 Server nutzen es noch, aber der Overhead (manuelle
`inputSchema`-Dicts, manuelles Tool-Routing) ist nicht gerechtfertigt.
FastMCP generiert das Schema aus Pydantic-Modellen, ist getestet, und
wird von 4+ Servern bereits erfolgreich eingesetzt.

### 4.2 Archivierte Server reparieren statt archivieren

Abgelehnt. Die Archivierung war die korrekte Entscheidung. Die
Funktionalität der archivierten Server wurde entweder:

- In die Django-Apps integriert (bfagent, book_writing)
- Durch spezialisierte aktive Server ersetzt (deployment_mcp, ifc_mcp)
- Nicht mehr benötigt (analytics_mcp, german_tax_mcp)

### 4.3 Monolithischer MCP-Server

Abgelehnt. Ein einzelner Server für alle Domänen widerspricht dem
Single-Responsibility-Prinzip und macht unabhängige Deployments
unmöglich.

---

## 5. Implementation Plan

### Phase 1: Kritische Fixes (Woche 1)

| # | Maßnahme | Server | Aufwand |
|---|----------|--------|----------|
| 1 | `llm_mcp` → FastMCP migrieren | llm_mcp | 2–3h |
| 2 | Error-Sanitisierung in `llm_mcp` | llm_mcp | 30min |
| 3 | Error-Sanitisierung in `orchestrator_mcp` | orchestrator_mcp | 30min |
| 4 | `.gitignore` für `*.log` prüfen | Alle | 10min |

### Phase 2: Lifecycle + Standardisierung (Woche 2–3)

| # | Maßnahme | Server | Aufwand |
|---|----------|--------|----------|
| 5 | Lifespan-Hook für HetznerClient/DNSClient | deployment_mcp | 1h |
| 6 | Lifespan-Hook für AmadeusClient | travel_mcp | 1h |
| 7 | `orchestrator_mcp` → FastMCP | orchestrator_mcp | 2–3h |
| 8 | Server-Template dokumentieren | docs/ | 1h |

### Phase 3: Vollständige Konsolidierung (Woche 4–6)

| # | Maßnahme | Server | Aufwand |
|---|----------|--------|----------|
| 9 | `deployment_mcp` → FastMCP | deployment_mcp | 4–6h |
| 10 | `ifc_mcp` → FastMCP | ifc_mcp | 3–4h |
| 11 | Git-History evaluieren | Repository | 1h |
| 12 | `_archive/` in separates Repository oder Branch | Repository | 1h |

---

## 6. Risks and Mitigations

| Risiko | Schweregrad | Mitigation |
|--------|-------------|------------|
| FastMCP-Migration bricht bestehende Clients | HOCH | Kein Schema-Breaking-Change — Tool-Namen und Parameter bleiben identisch |
| `deployment_mcp` Migration blockiert Deployments | HOCH | Phase 3 — erst nach stabilem Template. Parallel-Betrieb während Migration |
| Lifespan-Hooks vergessen | MITTEL | CI-Check: Jeder Client mit `close()` muss in einem Lifespan registriert sein |
| Git-History-Bereinigung zerstört Referenzen | MITTEL | Nur bei Public-Push nötig. Privates Repo: Risiko akzeptabel |

---

## 7. Success Metrics

| Metrik | Baseline (heute) | Ziel |
|--------|-------------------|------|
| Server auf FastMCP | 2 / 6 (33%) | 6 / 6 (100%) |
| Server mit Lifespan-Hook | 2 / 6 (33%) | 6 / 6 (100%) |
| Server mit Error-Sanitisierung | 4 / 6 (67%) | 6 / 6 (100%) |
| Manuelle `inputSchema`-Dicts | ~80 (llm + orchestrator) | 0 |
| Boilerplate-Zeilen für Protokoll | ~400 | ~30 |

---

## 8. Dependencies

| Package | Version | Zweck |
|---------|---------|-------|
| `fastmcp` | >=2.0.0 | Einheitlicher MCP-Protokollstack |
| `pydantic-settings` | >=2.0.0 | Umgebungsvariablen-basierte Konfiguration |
| `hatchling` | >=1.18.0 | Build-Backend |
| `pytest` + `pytest-asyncio` | >=8.0 / >=0.23 | Tool-Level Tests |

---

## 9. Appendix: Verifizierungsprotokoll

### A1: Dateien gelesen und verifiziert

| Datei | Befund |
|-------|--------|
| `_archive/bfagent_mcp/__main__.py` (290 Zeilen) | SimpleMCPServer, blockierendes I/O, Notification-Error, Error-Leaking — alles bestätigt. **ARCHIVIERT.** |
| `_archive/bfagent_mcp/metaprompter/intent.py` (225 Zeilen) | 40+ Regex-Patterns, deutsch-spezifisch, UNKNOWN-Fallback — bestätigt. **ARCHIVIERT.** |
| `_archive/bfagent_mcp/mcp_server.log` (15 Zeilen) | Versionierte Log-Datei mit Payloads — bestätigt. **ARCHIVIERT.** |
| `_archive/bfagent_sqlite_mcp/server.py:265-315` | Timeout mit `thread.daemon=True`, Connection-Leak bei Timeout — bestätigt. **ARCHIVIERT.** |
| `_archive/bfagent_sqlite_mcp/domain_tools.py` | 11x `f"SELECT * FROM [{table}]"` — f-String SQL bestätigt. **ARCHIVIERT.** |
| `_archive/bfagent_mcp/` (8 Dateien) | Hardcoded `C:\Users\achim\` Pfade — bestätigt. **ARCHIVIERT.** |
| `deployment_mcp/clients/hetzner_client.py` | Lazy `httpx.AsyncClient`, `close()` vorhanden, nicht in Lifespan — **OFFEN** |
| `deployment_mcp/clients/dns_client.py` | Identisches Pattern — **OFFEN** |
| `travel_mcp/server.py` | FastMCP + Lifespan ✅ — Referenz-Implementierung |
| `travel_mcp/shared/amadeus_client.py` | `__new__` Singleton, kein `close()` — **OFFEN** |
| `illustration_mcp/server.py` | FastMCP + Pydantic ✅ — kein Lifespan |
| `llm_mcp/server.py` + `__main__.py` | Raw MCP SDK + DIY Main Loop, Error-Leaking — **OFFEN** |
| `orchestrator_mcp/server.py` | Raw MCP SDK, manuelle Schemas — **OFFEN** |
| `ifc_mcp/presentation/server.py` | Raw MCP SDK + Lifespan für DB ✅ |

### A2: Grep-Ergebnisse

- `C:\Users\achim` — 23 Treffer, **alle in `_archive/`** (aktive Server sauber)
- `Internal error` — 1 Treffer in aktivem Code (`llm_mcp/__main__.py:595`)
- Singleton-Patterns — 3 aktive Server betroffen (deployment, travel, ifc)

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-18 | Achim Dehnert | Initial — basierend auf mcp-hub-adr-review.md mit Verifikation gegen aktuellen Codestand |
