# ADR-034: CAD-Daten ETL-Pipeline + Chat-Agent als Platform-Service

| Metadata    | Value |
| ----------- | ----- |
| **Status**  | Proposed |
| **Date**    | 2026-02-14 |
| **Author**  | Achim Dehnert |
| **Related** | ADR-009 (Segment-System), ADR-010 (MCP-Governance), ADR-022 (Platform Consistency) |
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
| Pipeline | ✅ Implementiert | `cad_services/pipeline.py` |
| SQL-Schema (normalisiert) | ✅ 6 Migrations | `cad_services/sql/001-006` |
| Pydantic-Modelle | ✅ Implementiert | `cad_services/models/` |
| RLS-Policies (Multi-Tenant) | ✅ Implementiert | `sql/004_rls_policies.sql` |

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

### 4.2 creative-services

Keine Änderungen. `chat-agent` nutzt `creative-services.LLMClient` als Dependency.

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
| 0 | travel-beat Agent fertig ausbauen (create_trip, add_segment, finalize) | ~4 Tage | Pending |
| 1 | `ChatAgent` + `DomainToolkit` aus TripAgent extrahieren → `chat-agent` Package | 1 Tag | Blocked by Phase 0 |
| 2 | `SessionBackend` Protocol + InMemory + Redis | 0.5 Tag | Blocked by Phase 1 |
| 3 | `ToolkitRegistry` + Django AppConfig Integration | 0.5 Tag | Blocked by Phase 1 |
| 4a | cad-hub `CADToolkit` + DB-Writer für ETL-Pipeline | 2 Tage | Blocked by Phase 1 + §2 |
| 4b | bfagent `BookFactoryToolkit` (optional, Validierung) | 1 Tag | Optional |
| 5 | Tests + Docs + pyproject.toml | 1 Tag | Blocked by Phase 3 |
| | **Gesamt** | **~10 Tage** | |

### 5.1 Phasen-Abhängigkeiten

```
Phase 0 (travel-beat Agent)
    │
    ▼
Phase 1 (ChatAgent extrahieren) ──► Phase 2 (Session) + Phase 3 (Registry)
    │                                        │
    ▼                                        ▼
Phase 4a (CADToolkit)              Phase 4b (BookFactoryToolkit)
    │                                        │
    └────────────────┬───────────────────────┘
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
