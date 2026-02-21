---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-034: CAD-Daten ETL-Pipeline + Chat-Agent als Platform-Service

| Metadata    | Value |
| ----------- | ----- |
| **Status**  | Proposed (Review v1: 2026-02-14) |
| **Date**    | 2026-02-14 |
| **Author**  | Achim Dehnert |
| **Reviewer** | Cascade (ADR Review v1) |
| **Related** | ADR-009 (Segment-System), ADR-010 (MCP-Governance), ADR-022 (Platform Consistency), ADR-029 (cad-hub Extraction) |
| **Packages** | `cad-services`, `creative-services`, `chat-agent` (neu) |

---

## 1. Context

### 1.1 Problem

cad-hub verarbeitet IFC/DXF-Dateien und speichert Gebäudedaten in PostgreSQL.
Nutzer wollen diese Daten per natürlicher Sprache abfragen:

> "Wie viele tragende Wände im 2. OG?"
> "Welche Räume im EG sind über 20m²?"
> "Zeige alle Fenster mit U-Wert über 1.3 W/m²K"

Gleichzeitig existiert in travel-beat ein `ConversationalTripAgent`, der das gleiche
Pattern implementiert (NL → LLM Tool-Use → Domain-Aktion → Antwort).

**Zwei getrennte Aspekte in einem ADR:**

| Aspekt | Scope | Sektion |
| ------ | ----- | ------- |
| IFC/DXF → PostgreSQL ETL | cad-hub spezifisch | §2 (ETL-Pipeline) |
| Chat-Agent Platform-Paket | Plattform-übergreifend | §3 (Chat-Agent) |

### 1.2 Betroffene Apps

| App | Rolle | Toolkit-Typ |
| --- | ----- | ----------- |
| cad-hub | Erste Read-Only-Anbindung | `CADToolkit` (queries gegen ETL-Daten) |
| travel-beat | Erste Read+Write-Anbindung | `TravelBeatToolkit` (Trip-Creation) |
| bfagent | Potentieller Consumer | `BookFactoryToolkit` (Kapitel-Queries) |
| weltenhub | Potentieller Consumer | `WeltenforgerToolkit` (Charakter-/Plot-Queries) |

---

## 2. ETL-Pipeline (cad-hub spezifisch)

### 2.1 Architektur

```
IFC/DXF-Datei
    │
    ▼
┌─────────────────────────────────────────┐
│  cad-services Pipeline                   │
│  ┌────────────┐  ┌───────────────────┐  │
│  │ IFC/DXF    │  │ QuantityEngine    │  │
│  │ Parser     ├──► (Rule-basiert)    │  │
│  └────────────┘  └────────┬──────────┘  │
│                           │              │
│  ┌────────────────────────▼──────────┐  │
│  │ CADParseResult (Pydantic)         │  │
│  │ → CADElement[]                     │  │
│  │   → properties, quantities,        │  │
│  │     materials, geometry            │  │
│  └────────────────────────┬──────────┘  │
└───────────────────────────┼──────────────┘
                            │
                            ▼
┌─────────────────────────────────────────┐
│  PostgreSQL (normalisiert, kein JSONB)   │
│                                          │
│  cadhub_project ── cadhub_cad_model      │
│       │                  │               │
│       │    ┌─────────────┼──────────┐    │
│       │    │             │          │    │
│  cadhub_floor    cadhub_room   cadhub_wall│
│       │          │       │          │    │
│  cadhub_window  cadhub_door  cadhub_slab │
│                                          │
│  cadhub_element_property (EAV)           │
│  cadhub_usage_category (DIN 277)         │
│  cadhub_property_definition (IFC PSet)   │
└─────────────────────────────────────────┘
```

### 2.2 Existierende Komponenten

| Komponente | Status | Pfad |
| ---------- | ------ | ---- |
| IFC-Parser | ✅ Implementiert | `cad_services/parsers/ifc_parser.py` |
| DXF-Parser | ✅ Implementiert | `cad_services/parsers/dxf_parser.py` |
| QuantityEngine | ✅ Implementiert | `cad_services/calculators/quantity_engine.py` |
| Pipeline | ✅ Implementiert (Pydantic-Output) | `cad_services/pipeline.py` |
| SQL-Schema (normalisiert) | ✅ 6 SQL-Dateien (Reference) | `cad_services/sql/001-006` |
| Pydantic-Modelle | ✅ Implementiert | `cad_services/models/` |
| RLS-Policies (Multi-Tenant) | ✅ SQL-Definition vorhanden | `sql/004_rls_policies.sql` |
| DB-Writer (Pipeline → PG) | ❌ Fehlt | — |
| Django ORM Models (cad-hub) | ⚠️ Vorhanden, aber inkonsistent mit SQL | `cad-hub/apps/ifc/models.py` |

### 2.3 Schema-Design-Entscheidungen

| Entscheidung | Begründung |
| ------------ | ---------- |
| Normalisierte Tabellen statt JSONB | SQL-Queries für Chat-Agent, Typ-Sicherheit, Indizierung |
| EAV für Properties (`cadhub_element_property`) | IFC hat 1000+ PropertySets, nicht vorab normalisierbar |
| DIN 277 als FK (`usage_category_id`) | Standardisierte Nutzungskategorien, Query-fähig |
| `is_load_bearing`, `is_external` direkt auf Wall | Häufige Filter, keine EAV-Indirection nötig |

### 2.4 ETL-Lücken für Chat-Agent-Anbindung

| Lücke | Beschreibung | Aufwand |
| ----- | ------------ | ------- |
| DB-Writer | Pipeline → PostgreSQL INSERT (aktuell nur Pydantic → return) | 1 Tag |
| View-Layer | SQL-Views für typische Chat-Queries (Aggregationen) | 0.5 Tag |
| Tenant-Filtering | `project.tenant_id` in allen Queries | 0.25 Tag |

---

## 3. Chat-Agent als Platform-Service

### 3.1 Architektur

```
┌──────────────────────────────────────────────┐
│           Chat UI (HTMX / WebSocket)          │
│  "Welche Räume im 2.OG sind über 20m²?"      │
└───────────────┬──────────────────────────────┘
                │
┌───────────────▼──────────────────────────────┐
│        ChatAgent  (platform/packages/)        │
│  ┌────────────────────────────────────────┐  │
│  │ LLM (creative-services) + Tool-Use    │  │
│  │ → LLM wählt Tool → ruft auf → antwortet│  │
│  └────────────┬───────────────────────────┘  │
│  ┌────────────▼───────────────────────────┐  │
│  │ SessionBackend (Redis/DB/InMemory)     │  │
│  └────────────────────────────────────────┘  │
└───────────────┬──────────────────────────────┘
                │ DomainToolkit Protocol
┌───────────────▼──────────────────────────────┐
│     App-spezifisches Toolkit                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ Tool A   │ │ Tool B   │ │ Tool C       │ │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘ │
│       └─────────────┼──────────────┘         │
│              App-Datenbank                    │
└──────────────────────────────────────────────┘
```

### 3.2 Design-Entscheidungen

| Entscheidung | Begründung |
| ------------ | ---------- |
| **Tool-Use statt IntentResolver** | LLM wählt Tools direkt; Multi-Turn natürlich, keine Intent-Vordefinition nötig |
| **DomainToolkit statt QueryEngine** | Toolkits enthalten Reads UND Writes (travel-beat: `create_trip`, `add_segment`) |
| **creative-services als LLM-Layer** | LLMClient, Registry, UsageTracker existieren; keine Parallelisierung |
| **SessionBackend als Protocol** | InMemory (Test), Redis (Production), DB (Audit) — App wählt |
| **AppConfig.ready() statt Decorator** | Django Import-Reihenfolge ist nicht garantiert |
| **Formatter per App** | CAD-Tabelle ≠ Trip-Zusammenfassung; LLM-Default für einfache Fälle |

### 3.3 Package-Struktur

```
platform/packages/chat-agent/
├── pyproject.toml                # Depends: creative-services, pydantic
├── src/chat_agent/
│   ├── __init__.py
│   ├── agent.py                  # ChatAgent — Tool-Use-Loop (Kern)
│   ├── session.py                # SessionBackend Protocol + 3 Implementierungen
│   ├── registry.py               # ToolkitRegistry — Apps registrieren DomainToolkits
│   ├── toolkit.py                # DomainToolkit ABC — tool_schemas + execute()
│   ├── models.py                 # Pydantic: ChatMessage, ToolResult, AgentContext
│   └── middleware.py             # Django Middleware (optional, setzt AgentContext)
└── tests/
```

### 3.4 Kern-Interface: `DomainToolkit`

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolResult(BaseModel):
    """Ergebnis eines Tool-Aufrufs."""

    model_config = ConfigDict(frozen=True)

    success: bool = Field(description="Whether the tool call succeeded")
    data: Any = Field(description="Result data (dict, list, str)")
    error: str | None = Field(default=None, description="Error message if failed")


class AgentContext(BaseModel):
    """Kontext für Tool-Ausführung."""

    model_config = ConfigDict(frozen=True)

    user: Any = Field(description="Authenticated user object")
    tenant_id: str | None = Field(default=None, description="Tenant ID for multi-tenancy")
    session_id: str = Field(description="Current chat session ID")


class DomainToolkit(ABC):
    """Abstraktion: Jede App definiert ihre Tools + Handler."""

    @property
    @abstractmethod
    def tool_schemas(self) -> list[dict]:
        """OpenAI-Format Tool-Definitionen."""
        ...

    @abstractmethod
    async def execute(
        self, tool_name: str, arguments: dict, ctx: AgentContext
    ) -> ToolResult:
        """Führe ein Tool aus. Dispatch zu App-spezifischem Handler."""
        ...

    def format_response(self, tool_results: list[ToolResult]) -> str | None:
        """Optional: App-spezifische Formatierung. None = LLM formuliert."""
        return None
```

### 3.5 Konkrete Toolkits

#### CADToolkit (cad-hub, read-only)

```python
class CADToolkit(DomainToolkit):
    """Abfragen gegen normalisierte CAD-Daten in PostgreSQL."""

    @property
    def tool_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_rooms",
                    "description": "Query rooms by floor, area, usage category",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "integer"},
                            "floor_name": {"type": "string", "description": "z.B. '2.OG', 'EG'"},
                            "min_area_m2": {"type": "number"},
                            "max_area_m2": {"type": "number"},
                            "usage_category": {"type": "string", "description": "DIN 277 Code"},
                        },
                        "required": ["project_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "query_walls",
                    "description": "Query walls by floor, load-bearing, external, material",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "integer"},
                            "floor_name": {"type": "string"},
                            "is_load_bearing": {"type": "boolean"},
                            "is_external": {"type": "boolean"},
                            "material": {"type": "string"},
                        },
                        "required": ["project_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "query_windows",
                    "description": "Query windows by floor, room, U-value threshold",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "integer"},
                            "floor_name": {"type": "string"},
                            "max_u_value": {"type": "number", "description": "W/m²K threshold"},
                            "min_u_value": {"type": "number"},
                        },
                        "required": ["project_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "aggregate_quantities",
                    "description": "Aggregate quantities: total area, volume, count by element type and floor",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "integer"},
                            "element_type": {
                                "type": "string",
                                "enum": ["room", "wall", "window", "door", "slab"],
                            },
                            "floor_name": {"type": "string"},
                            "group_by": {
                                "type": "string",
                                "enum": ["floor", "material", "usage_category", "type"],
                            },
                        },
                        "required": ["project_id", "element_type"],
                    },
                },
            },
        ]

    async def execute(
        self, tool_name: str, arguments: dict, ctx: AgentContext
    ) -> ToolResult:
        handlers = {
            "query_rooms": self._query_rooms,
            "query_walls": self._query_walls,
            "query_windows": self._query_windows,
            "aggregate_quantities": self._aggregate_quantities,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return ToolResult(success=False, data=None, error=f"Unknown tool: {tool_name}")
        return await handler(arguments, ctx)
```

#### TravelBeatToolkit (travel-beat, read+write)

```python
class TravelBeatToolkit(DomainToolkit):
    """Trip-Erstellung und -Verwaltung via Konversation."""

    @property
    def tool_schemas(self) -> list[dict]:
        return [
            # Read (existieren bereits)
            *EXISTING_TRIP_TOOLS,  # search_trips, get_trip_details, etc.
            # Write (neu, aus Counter-Review Addendum v3)
            CREATE_TRIP_TOOL,
            ADD_STOP_TOOL,
            ADD_TRANSPORT_TOOL,
            ADD_SEGMENT_TOOL,   # Aktivitäten/Szenen → TripSegment
            FINALIZE_TRIP_TOOL,
        ]

    async def execute(
        self, tool_name: str, arguments: dict, ctx: AgentContext
    ) -> ToolResult:
        return await TOOL_HANDLERS[tool_name](ctx.user, arguments)
```

### 3.6 Vergleich: CADToolkit vs. TravelBeatToolkit

| Aspekt | CADToolkit | TravelBeatToolkit |
| ------ | ---------- | ----------------- |
| Modus | Read-only | Read + Write |
| Tools | 4 Query-Tools | 5 Read + 5 Write |
| DB-Zugriff | Raw SQL (normalisiertes Schema) | Django ORM |
| Multi-Turn | Einfach (Rückfragen zu Filtern) | Komplex (Trip aufbauen über N Turns) |
| Tenant-Isolation | `project.tenant_id` in WHERE | `trip.user_id` Filter |
| Formatter | Tabellen-Format (Räume, Wände) | Trip-Zusammenfassung mit Stops |

**Dieser Vergleich validiert die Abstraktion:** Beide Toolkits haben fundamental verschiedene Domänen-Logik, nutzen aber den identischen Tool-Use-Loop, Session-Management und LLM-Integration.

### 3.7 ChatAgent Kern-Klasse

```python
@dataclass
class ChatAgent:
    """Domänenunabhängiger Tool-Use Agent.

    Extrahiert aus travel-beat ConversationalTripAgent,
    generalisiert für alle Apps.
    """

    toolkit: DomainToolkit
    session_backend: SessionBackend
    system_prompt: str
    max_rounds: int = 10
    action_code: str = "chat"

    async def chat(
        self, session_id: str, user_message: str, *, user: Any = None
    ) -> AgentResponse:
        session = await self.session_backend.load(session_id)
        if not session:
            session = ChatSession(
                id=session_id,
                messages=[{"role": "system", "content": self.system_prompt}],
            )

        session.messages.append({"role": "user", "content": user_message})

        for round_num in range(self.max_rounds):
            result = await completion(
                action_code=self.action_code,
                messages=session.messages,
                tools=self.toolkit.tool_schemas,
                tool_choice="auto",
                user=user,
            )

            if not result.has_tool_calls:
                session.messages.append(
                    {"role": "assistant", "content": result.content}
                )
                break

            session.messages.append(_build_assistant_msg(result))
            for tc in result.tool_calls:
                tool_result = await self.toolkit.execute(
                    tc.name, tc.arguments,
                    AgentContext(user=user, session_id=session_id),
                )
                session.messages.append(
                    _build_tool_result_msg(tc.id, tool_result)
                )

        await self.session_backend.save(session)
        return AgentResponse(content=result.content, rounds=round_num + 1)
```

### 3.8 App-Integration (Django)

```python
# cad-hub: apps/chat/apps.py
from django.apps import AppConfig

class ChatConfig(AppConfig):
    name = "apps.chat"

    def ready(self):
        from chat_agent import registry
        from .toolkit import CADToolkit
        registry.register("cad", CADToolkit())
```

```python
# cad-hub: apps/chat/views.py
from chat_agent import ChatAgent, RedisSessionBackend, registry

async def chat_view(request):
    agent = ChatAgent(
        toolkit=registry.get("cad"),
        session_backend=RedisSessionBackend(),
        system_prompt=CAD_SYSTEM_PROMPT,
        action_code="cad_chat",
    )
    response = await agent.chat(
        session_id=f"cad-{request.user.pk}",
        user_message=request.POST["message"],
        user=request.user,
    )
    return JsonResponse({"reply": response.content})
```

---

## 4. Auswirkungen auf existierenden Code

### 4.1 travel-beat `ConversationalTripAgent`

| Aspekt | Jetzt | Nach chat-agent Extraktion |
| ------ | ----- | -------------------------- |
| `trip_agent.py` | 120 Zeilen, Tool-Use-Loop + History | 15 Zeilen, Factory für `ChatAgent` |
| `tools.py` | Tool-Schemas + Handler | Wird zu `TravelBeatToolkit` |
| Session | `self.history` (in-memory list) | `RedisSessionBackend` |
| System-Prompt | Hardcoded in Modul | Parameter an `ChatAgent` |
| LLM-Config | `ACTION_CODE = "trip_planning"` | `action_code="trip_planning"` |

**Migration: Non-breaking.** Der existierende Agent wird zu einem Thin-Wrapper.

### 4.2 creative-services (ÄNDERUNG ERFORDERLICH)

> **Review-Finding F-02:** `LLMClient.generate(prompt, system_prompt)` hat kein Tool-Use.
> `chat-agent` benötigt eine Messages-API mit Tool-Use-Support.

**Erforderliche Erweiterung** (siehe §8, Entscheidung E-02):

```python
# creative_services/core/llm_client.py — NEUE Methode (Port von bfagent L1)
async def complete(
    self,
    messages: list[dict],
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
    **kwargs,
) -> CompletionResponse:
    """Messages-based completion with Tool-Use support.

    Nutzt anthropic/openai SDK (nicht httpx) für natives Tool-Use.
    Bestehende generate() bleibt unverändert (backward-compatible).
    """
    ...
```

Aufwand: ~2 Tage. Muss **vor Phase 1** (ChatAgent-Extraktion) abgeschlossen sein.

### 4.3 platform-context

`AgentContext` kann `platform_context.get_context()` für `tenant_id` nutzen:

```python
from platform_context import get_context

ctx = AgentContext(
    user=request.user,
    tenant_id=str(get_context().tenant_id),
    session_id=session_id,
)
```

---

## 5. Implementierungs-Roadmap

| Phase | Aufgabe | Aufwand | Status |
| ----- | ------- | ------- | ------ |
| -1 | **creative-services Tool-Use** (E-02): `LLMClient.complete(messages, tools)` | 2 Tage | **Blocker** |
| 0 | travel-beat Agent fertig ausbauen (create_trip, add_segment, finalize) | ~4 Tage | Pending |
| 0.5 | **Schema-Konsolidierung** (E-01): Django ORM ← cad-services SQL, RLS als RunSQL | 1.5 Tage | Blocked by E-01 Entscheidung |
| 1 | `ChatAgent` + `DomainToolkit` aus TripAgent extrahieren → `chat-agent` Package | 1 Tag | Blocked by Phase -1 + 0 |
| 2 | `SessionBackend` Protocol + InMemory + Redis | 0.5 Tag | Blocked by Phase 1 |
| 3 | `ToolkitRegistry` + Django AppConfig Integration | 0.5 Tag | Blocked by Phase 1 |
| 4a | cad-hub `CADToolkit` + DB-Writer für ETL-Pipeline | 2 Tage | Blocked by Phase 0.5 + 1 |
| 4b | bfagent `BookFactoryToolkit` (optional, Validierung) | 1 Tag | Optional |
| 5 | Tests + Docs + pyproject.toml | 1 Tag | Blocked by Phase 3 |
| | **Gesamt** | **~13.5 Tage** | |

### 5.1 Phasen-Abhängigkeiten

```text
Phase -1 (creative-services Tool-Use)
    │
    ▼
Phase 0 (travel-beat Agent)     Phase 0.5 (Schema-Konsolidierung)
    │                                │
    ▼                                │
Phase 1 (ChatAgent extrahieren) ◄────┘
    │
    ├──► Phase 2 (Session) + Phase 3 (Registry)
    │                                │
    ▼                                ▼
Phase 4a (CADToolkit)      Phase 4b (BookFactoryToolkit)
    │                                │
    └────────────────┬───────────────┘
                     ▼
               Phase 5 (Tests + Docs)
```

---

## 6. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
| ------ | ------------------ | ------ | ---------- |
| Premature Abstraction | Mittel | Hoch | Phase 0 zuerst; erst extrahieren wenn travel-beat funktioniert |
| creative-services vs. LiteLLM Divergenz | Hoch | Mittel | Entscheidung in Phase 1: ein LLM-Layer, nicht zwei |
| CAD-Queries zu komplex für Tool-Use | Niedrig | Mittel | SQL-Views als Abstraktionsschicht; LLM sieht einfache Tools |
| Session-Größe bei langen Konversationen | Mittel | Niedrig | TTL + Message-Pruning (älteste Messages entfernen) |
| Multi-Tenant Isolation | Hoch | Hoch | `AgentContext.tenant_id` in jedem Tool-Handler als WHERE-Clause |

---

## 7. Offene Fragen

1. **LLM-Client-Entscheidung:** `creative-services.LLMClient` oder `llm_service.completion()` (LiteLLM)?
   Empfehlung: `creative-services` — hat Registry, Tiers, UsageTracker.

2. **WebSocket vs. HTMX für Chat-UI:** WebSocket für Streaming, HTMX für einfache Request/Response?
   Empfehlung: HTMX für MVP (konsistent mit Platform-Pattern), WebSocket als Upgrade.

3. **Rate-Limiting:** Pro User, pro Tenant, oder pro App?
   Empfehlung: Pro User + Pro Tenant (wie travel-beat Upload: 20/h, 100/Tag).

---

*Proposed: 2026-02-14. §2 (ETL) stabil. §3 (Chat-Agent) pending Phase 0 travel-beat.*

---

## 8. Review v1 — Findings und Architektur-Entscheidungen

> Reviewer: Cascade, 2026-02-14
> Methodik: Codebase-Verifikation gegen tatsächlichen Code in `cad-hub`, `cad-services`,
> `creative-services`, `bfagent/apps/core/services/llm/`.

### 8.1 Architektur-Entscheidung E-01: Schema-Autorität

**Frage:** cad-hub Django ORM oder cad-services SQL als Schema-Autorität?

**Befund:** Es existieren zwei inkompatible Schemas für dieselbe Domäne:

| Aspekt | cad-services SQL (`002_cadhub_schema.sql`) | cad-hub Django ORM (`apps/ifc/models.py`) |
|--------|------------------------------------------|------------------------------------------|
| PK-Typ | `SERIAL INTEGER` | `UUID` |
| Tenant-FK | `INTEGER REFERENCES core_tenant(id)` | `UUIDField` (kein FK, kein Constraint) |
| Tenant-Tabelle | `core_tenant(id SERIAL, slug, plan_id)` | `Organization(id UUID, tenant_id UUID)` |
| Feld-Benennung | `area_m2`, `height_m`, `thickness_m` | `area`, `height`, `width` (keine Unit-Suffixe) |
| Property-Speicherung | EAV `cadhub_element_property` | `JSONField(properties)` pro Model |
| Constraints | CHECK, UNIQUE, FK mit ON DELETE | Keine DB-Level-Constraints |

**Entscheidung: HYBRID — Django ORM als Autorität, cad-services SQL als Design-Referenz.**

| Schritt | Aktion |
|---------|--------|
| 1 | Django-Models in `apps/ifc/models.py` anpassen: Felder umbenennen (`area` → `area_m2`), Constraints hinzufügen |
| 2 | CHECK-Constraints, Indizes via `Meta.constraints` und `Meta.indexes` |
| 3 | RLS-Policies als `RunSQL`-Migration innerhalb Django |
| 4 | EAV-Tabelle `cadhub_element_property` als `RunSQL`-Migration (oder Django-Model mit `GenericForeignKey`) |
| 5 | Stammdaten (Units, DIN 277) als `RunPython` Data-Migrations |
| 6 | `cad-services/sql/` → `platform/docs/reference/cad-schema/` (Archiv, nicht löschen) |

**Begründung:**
- cad-hub ist Django → `makemigrations`/`migrate` ist der natürliche Lifecycle
- cad-services SQL hat wertvolle Normalisierung → wird in Django-Migrations übernommen
- Ein einziger Schema-Lifecycle verhindert Drift zwischen SQL-Dateien und Django-Models
- `managed = False` wäre eine Alternative, aber verliert Django-Admin und Migrations-Versionierung

**Risiko:** MITTEL — Erfordert einmalige Migration der bestehenden Daten (falls vorhanden).

---

### 8.2 Architektur-Entscheidung E-02: creative-services Tool-Use

**Frage:** Wie bekommt `chat-agent` Tool-Use-Support?

**Befund:** `creative-services/core/llm_client.py` hat nur:
- `generate(prompt: str, system_prompt: str)` — kein `messages`, kein `tools`
- Raw httpx, kein SDK — Tool-Use-Parsing müsste manuell implementiert werden
- `LLMResponse` hat nur `content: str` — kein `tool_calls` Attribut

`bfagent/apps/core/services/llm/` (L1) hat bereits:
- `AnthropicClient._generate_structured_sdk()` — Tool-Use via Anthropic SDK
- `OpenAIClient._generate_structured_sdk()` — Tool-Use via OpenAI SDK
- Beide nutzen offizielle SDKs, nicht httpx

**Entscheidung: Option B — bfagent L1 nach creative-services portieren.**

| Aspekt | Detail |
|--------|--------|
| Neue Methode | `LLMClient.complete(messages, tools, tool_choice) → CompletionResponse` |
| SDK-Basis | `anthropic.Anthropic()` + `openai.OpenAI()` (statt httpx) |
| Backward-Compat | `generate(prompt)` bleibt unverändert |
| Return-Typ | `CompletionResponse(content, tool_calls, has_tool_calls, model, usage)` |
| Registry-Integration | `DynamicLLMClient` bekommt ebenfalls `complete()` |
| UsageTracker | Automatisches Tracking auch für `complete()` |

```python
# creative_services/core/llm_client.py — Neue Typen

@dataclass(frozen=True)
class ToolCall:
    """Einzelner Tool-Call aus LLM-Response."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class CompletionResponse:
    """Response von complete() mit optionalen Tool-Calls."""

    content: str | None
    tool_calls: list[ToolCall]
    model: str
    provider: LLMProvider
    usage: dict[str, Any]

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0
```

**Begründung:**
- bfagent L1 ist produktionsbewährt mit Tool-Use
- Kein neuer Client (kein LiteLLM), kein httpx-Workaround
- Registry + UsageTracker bleiben integriert
- `chat-agent` §3.7 `completion()` wird zu `creative_services.DynamicLLMClient.complete()`

**Aufwand:** ~2 Tage. **Blocker für Phase 1.**

---

### 8.3 Architektur-Entscheidung E-03: Tenant-Isolation

**Frage:** `TenantAwareManager` auf allen Models oder RLS als alleinige Isolation?

**Entscheidung: BEIDES — Defense in Depth.**

| Schicht | Rolle | Enforcement |
|---------|-------|-------------|
| RLS (PostgreSQL) | Sicherheitsnetz — verhindert Data Leaks auch bei vergessenen Filtern | DB-Level, nicht umgehbar |
| TenantAwareManager (Django) | Developer UX — macht Code lesbar und explizit | App-Level, kann umgangen werden |
| Middleware (Glue) | Setzt `SET LOCAL app.current_tenant_id` pro Request | HTTP-Request-Level |

**Begründung:**
- RLS allein: Django-Admin, Celery-Tasks, Management-Commands brechen ohne `SET LOCAL`
- Manager allein: Jeder vergessene `.for_tenant()` ist ein Data Leak
- Beides: RLS fängt vergessene Filter ab, Manager macht Code explizit

**Kritischer Glue-Code (fehlt im ADR, muss ergänzt werden):**

```python
# cad-hub: apps/core/middleware.py
from django.db import connection


class TenantRLSMiddleware:
    """Setzt PostgreSQL session variable für RLS-Policies.

    Muss NACH TenantMiddleware in MIDDLEWARE kommen.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        if tenant_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.current_tenant_id = %s",
                    [str(tenant_id)],
                )
        return self.get_response(request)
```

```python
# cad-hub: apps/core/decorators.py — Für Celery-Tasks
from functools import wraps
from django.db import connection


def with_tenant(tenant_id):
    """Decorator für Celery-Tasks: setzt RLS tenant_id."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.current_tenant_id = %s",
                    [str(tenant_id)],
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

**Risiko:** NIEDRIG — Additiver Change, kein bestehender Code bricht.

---

### 8.4 Architektur-Entscheidung E-04: UUID vs SERIAL INTEGER

**Frage:** cad-hub `IFCProject.id = UUID` — beibehalten oder zu SERIAL wechseln?

**Entscheidung: UUID beibehalten.**

| Aspekt | UUID | SERIAL |
|--------|------|--------|
| IFC-Kompatibilität | IFC GUIDs sind UUID-nah | Braucht extra `ifc_guid` Feld |
| IDOR-Schutz | Nicht erratbar (`/api/projects/abc-def/`) | Sequenziell (`/api/projects/1/`) |
| Multi-Tenant Merge | Kein Namespace-Konflikt | ID-Kollisionen bei DB-Merge |
| Performance (<100k Rows) | Vernachlässigbar | Minimal besser |
| Django-Ökosystem | Standard in neueren SaaS-Projekten | Legacy-Default |

**Konsequenzen:**
- cad-services SQL-Reference anpassen: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- Tool-Schemas (§3.5) anpassen: `"project_id": {"type": "string", "format": "uuid"}`
- `AgentContext.tenant_id` von `str | None` auf `UUID | None` ändern
- `ifc_guid VARCHAR(22)` als **separates Feld** beibehalten (IFC GUIDs sind Base64, keine Standard-UUIDs)

---

### 8.5 Weitere Review-Findings

| ID | Befund | Schwere | Empfehlung |
|----|--------|---------|------------|
| F-03 | EAV-Tabelle `cadhub_element_property` hat polymorphen FK ohne referenzielle Integrität | MITTEL | `AFTER DELETE` Trigger auf Element-Tabellen, oder separate Property-Tabellen pro Typ |
| F-05 | `cad-hub/apps/ifc/models_components.py` fehlt `import uuid` | NIEDRIG | 1-Zeiler Fix |
| F-06 | `TenantAwareManager` definiert aber keinem Model zugewiesen | NIEDRIG | Wird durch E-03 (Defense in Depth) gelöst |
| F-08 | `AgentContext.tenant_id: str` statt `UUID` | NIEDRIG | Wird durch E-04 gelöst: `UUID` oder `None` |
| F-10 | Kein Idempotenz-Konzept für ETL Re-Import | MITTEL | `file_hash VARCHAR(64)` + `UNIQUE(project_id, file_hash)` auf `cad_model` |
| F-11 | Session-TTL für Redis nicht spezifiziert | NIEDRIG | Default 24h TTL, konfigurierbar pro App |

---

### 8.6 Zusammenfassung Review-Status

| Blocker | Status | Lösung |
|---------|--------|--------|
| **F-01: Zwei inkompatible Schemas** | Entschieden (E-01) | Django ORM als Autorität, cad-services SQL als Reference |
| **F-02: creative-services hat kein Tool-Use** | Entschieden (E-02) | L1-Port nach creative-services, neue `complete()` Methode |

**ADR ist implementierbar nach Umsetzung von E-01 und E-02.**
§3.7 `ChatAgent.chat()` muss `completion()` durch `DynamicLLMClient.complete()` ersetzen.
