# ADR-007 Counter-Review: Conversational Trip Agent — Codebase Validation

> **Reviewer:** Senior Architecture Review (Counter-Review)
> **Datum:** 2026-02-14
> **Review-Typ:** Counter-Review gegen tatsächliche Codebase
> **Scope:** Validierung der 16 Befunde aus `travel-agent-adr-REVIEW.md` gegen den **implementierten Code** in `travel-beat/apps/trips/agent/`
> **Bewertung:** 🟠 TEILWEISE OBSOLET — 7 von 16 Befunden sind durch Implementierung bereits adressiert

---

## Methodik

Alle Befunde der ursprünglichen Review wurden gegen folgende Dateien im `travel-beat`-Repo geprüft:

| Datei | Zweck |
|-------|-------|
| `apps/trips/agent/trip_agent.py` | Agent-Loop mit LiteLLM |
| `apps/trips/agent/tools.py` | Tool-Definitionen (OpenAI-Format) |
| `apps/trips/agent/handlers.py` | Tool-Handler (DB-Operationen) |
| `apps/ai_services/llm_service.py` | Provider-agnostischer LLM-Service (LiteLLM) |
| `apps/ai_services/models.py` | DB-driven LLM-Config (LLMProvider, LLMModel, AIActionType, AIUsageLog) |
| `apps/trips/models/trip.py` | Trip, Stop, Transport Models |
| `apps/stories/models/story.py` | Story, Chapter Models |
| `apps/core/models.py` | Lookup-Tabellen (TripType, AccommodationType, etc.) |

---

## Befund-Revalidierung

### K1: Direkte `anthropic.Anthropic()` — ✅ BEREITS BEHOBEN

**Original-Befund:** Agent erstellt `self.client = anthropic.Anthropic()` direkt.

**Tatsächlicher Code:**

```python
# apps/trips/agent/trip_agent.py:117-124
result = await completion(
    action_code=ACTION_CODE,
    messages=self.history,
    tools=TRIP_TOOLS,
    tool_choice="auto",
    user=self.user,
    **overrides,
)
```

`completion()` ist `apps.ai_services.llm_service.completion()` — nutzt **LiteLLM** mit DB-gesteuerter Modellauswahl via `AIActionType`. Provider/Model-Wechsel erfordert nur DB-Änderung.

**Status:** 🟢 BEHOBEN — Kein Handlungsbedarf. Die Implementierung nutzt exakt das vom Review empfohlene Pattern: DB-driven Config → Provider-agnostischer Client → Usage-Logging.

**Verbleibendes Risiko:** Der `action_code = "trip_planning"` muss als `AIActionType` in der DB existieren. Fehlt der Eintrag, greift ein Hardcoded-Fallback auf `anthropic/claude-sonnet-4-20250514` (Zeile 134-146 in `llm_service.py`). Das ist akzeptabel als Graceful Degradation, sollte aber im Deployment-Runbook dokumentiert sein.

---

### K2: Falsche Model-Feldnamen — ✅ BEREITS BEHOBEN

**Original-Befund:** ADR-Code referenziert `Stop(location=...)`, `highlights`, kein `accommodation_type`.

**Tatsächlicher Code:**

```python
# apps/trips/agent/handlers.py:169-180
stop = Stop.objects.create(
    trip=trip,
    city=args["city"],
    country=args["country"],
    arrival_date=arrival,
    departure_date=departure,
    accommodation_type=args.get("accommodation_type", "hotel"),
    notes=args.get("notes", ""),
    order=max_order,
)
```

Tool-Schema in `tools.py` definiert korrekte Felder: `city`, `country`, `arrival_date`, `departure_date`, `accommodation_type` (mit korrektem Enum), `notes`.

**Status:** 🟢 BEHOBEN — Feldnamen stimmen exakt mit `Trip`/`Stop` Models überein.

---

### K3: `trip_type` Semantik-Konflikt — 🟡 TEILWEISE OFFEN (Neuer Befund)

**Original-Befund:** `trip_type` als Reise-Gruppierung vs. Reisekategorie.

**Tatsächlicher Code:** Das Semantik-Problem existiert **nicht** in der Implementierung — der Agent nutzt `trip_type` korrekt als Reisekategorie. Tool-Schema definiert:

```python
# apps/trips/agent/tools.py:31-42
"trip_type": {
    "type": "string",
    "enum": ["city", "beach", "wellness", "backpacking",
             "business", "family", "adventure", "cruise", "roadtrip"],
    "description": "Filter by trip type",
}
```

Das matcht `Trip.TripType.choices` exakt.

**NEUER Befund:** Es existiert eine **Doppeldefinition** von TripType:

| Ort | Typ | Werte |
|-----|-----|-------|
| `apps/trips/models/trip.py:14-23` | `Trip.TripType` (TextChoices) | 9 Werte (hardcoded) |
| `apps/core/models.py:268-373` | `TripType(LookupBase)` | 9 Werte (DB-driven) |

**Risiko:** Inkonsistenz bei Erweiterung. Wird ein neuer TripType via Admin in der Lookup-Tabelle angelegt, erkennt `Trip.TripType.choices` ihn nicht. Django validiert das CharField nicht gegen die DB-Tabelle.

**Empfehlung:**
1. `Trip.trip_type` als ForeignKey auf `core.TripType` migrieren, **ODER**
2. `core.TripType` Lookup-Tabelle entfernen und `Trip.TripType` TextChoices als Single Source of Truth beibehalten
3. Option 2 ist der pragmatische Weg (weniger Migration, Tools-Schema bleibt stabil)

**Aufwand:** 0.5 Tag (Migration + Tool-Schema-Update)

---

### K4: `self._current_user` undefined — ✅ BEREITS BEHOBEN

**Original-Befund:** `self._current_user` wird nirgends gesetzt.

**Tatsächlicher Code:**

```python
# apps/trips/agent/trip_agent.py:68-76
@dataclass
class ConversationalTripAgent:
    user: Any = None  # Explizites Dataclass-Feld
    history: List[Dict[str, Any]] = field(default_factory=list)
    max_rounds: int = MAX_TOOL_ROUNDS
```

User wird als Dataclass-Feld übergeben und an Tool-Handler weitergereicht:

```python
# apps/trips/agent/trip_agent.py:148-149
tool_result = await _execute_tool(
    self.user, tc
)
```

Handler empfangen `user` als ersten Parameter:

```python
# apps/trips/agent/handlers.py:133-134
async def handle_add_stop(
    user, args: Dict[str, Any]
) -> Dict[str, Any]:
```

**Status:** 🟢 BEHOBEN — User-Kontext wird sauber durchgereicht, nicht als mutable State.

---

### K5: Kein `@transaction.atomic` — 🟡 NIEDRIGER ALS BEWERTET

**Original-Befund:** Trip + Stops Erstellung ohne Transaktion.

**Tatsächlicher Code:** Der Agent hat **kein** `create_trip`-Tool. Es existieren nur:
- `search_trips` (read-only)
- `get_trip_details` (read-only)
- `add_stop` (einzelner Stop zu existierendem Trip)
- `suggest_activities` (kein DB-Write)
- `get_trip_stats` (read-only)

`add_stop` erstellt einen einzelnen `Stop` — kein Multi-Object-Create, daher ist `transaction.atomic` nicht zwingend erforderlich.

**Verbleibendes Risiko:** Wenn ein `create_trip`-Tool hinzugefügt wird (Trip + N Stops), **muss** `transaction.atomic` implementiert werden. Sollte als Invariante im Docstring des Handler-Moduls dokumentiert werden.

**Empfehlung:** Defensiv `transaction.atomic` trotzdem auf `handle_add_stop` setzen — kostet nichts, schützt bei zukünftiger Erweiterung:

```python
from django.db import transaction

async def handle_add_stop(user, args):
    def _create():
        with transaction.atomic():
            # ... existing code ...
    return await sync_to_async(_create)()
```

**Aufwand:** 15 Minuten

---

### K6: Tool Use Loop ohne Serialisierung — ✅ BEREITS BEHOBEN

**Original-Befund:** `ToolUseBlock`-Objekte nicht JSON-serialisierbar.

**Tatsächlicher Code:** Die Implementierung nutzt **LiteLLM** (OpenAI-Format), nicht das Anthropic SDK direkt. Tool-Calls werden als plain dicts serialisiert:

```python
# apps/trips/agent/trip_agent.py:181-203
def _build_assistant_tool_msg(result: LLMResult) -> Dict[str, Any]:
    tool_calls = []
    for tc in result.tool_calls:
        tool_calls.append({
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.name,
                "arguments": json.dumps(tc.arguments, ensure_ascii=False),
            },
        })
    return {
        "role": "assistant",
        "content": result.content or None,
        "tool_calls": tool_calls,
    }
```

`ToolCall` ist ein frozen Dataclass mit primitiven Typen — vollständig JSON-serialisierbar.

**Verbleibendes Risiko:** Die Conversation-History wird nur in-memory gehalten (`self.history`). Bei Worker-Crash ist der Kontext verloren. Für MVP akzeptabel, für Production sollte nach jedem Round ein Checkpoint in die DB geschrieben werden.

**Status:** 🟢 BEHOBEN (Serialisierung). 🟡 OFFEN (Persistence — aber nur für Production-Hardening relevant).

---

### K7: Keine Rate-Limiting — 🔴 NOCH OFFEN

**Original-Befund:** Keine Begrenzung für Conversations pro User.

**Tatsächlicher Code:** Kein Rate-Limiting implementiert. Der Agent ist ein Dataclass ohne Persistence — es gibt kein `AgentConversation`-Model, also auch keine Grundlage für DB-basiertes Counting.

**Risiko:** Gültig. Ein automatisierter Client kann beliebig viele `chat()`-Aufrufe machen.

**Empfehlung (minimaler Diff):**

```python
# In der View, die den Agent aufruft:
from django.core.cache import cache

def _check_rate_limit(user_id: int) -> bool:
    key = f"agent_rate:{user_id}:{timezone.now().date()}"
    count = cache.get(key, 0)
    if count >= settings.AGENT_MAX_DAILY_CHATS:
        return False
    cache.set(key, count + 1, timeout=86400)
    return True
```

Cache-basiert, kein neues Model nötig. `AGENT_MAX_DAILY_CHATS` in Settings (DB-driven via `django-constance` oder `.env`).

**Aufwand:** 0.5 Tag

---

### S1: `extracted_data` JSONField Overwrite — ⚪ NICHT ANWENDBAR

**Original-Befund:** `AgentConversation.extracted_data` wird unkontrolliert überschrieben.

**Tatsächlicher Code:** Es gibt **kein** `AgentConversation`-Model. Der Agent extrahiert keine Daten progressiv — er operiert direkt auf Trip/Stop-Models via Tool-Calls. Der LLM entscheidet wann er `add_stop` aufruft, die Daten werden sofort in die DB geschrieben.

**Status:** ⚪ GEGENSTANDSLOS — Das Review-Design mit progressiver Extraktion wurde nicht implementiert. Der aktuelle Ansatz (direkte DB-Writes via Tools) ist architektonisch sauberer.

---

### S2: Story-Settings fehlen im Agent-Flow — 🟡 DESIGN-ENTSCHEIDUNG (kein Bug)

**Original-Befund:** Agent überspringt Wizard Step 3 (Genre, Spice, Protagonist).

**Tatsächlicher Code:** Der Agent hat einen **anderen Scope** als im ADR beschrieben. Er ist ein Trip-Management-Agent, kein Trip-Creation-Wizard-Ersatz:

- **Agent-Tools:** search, detail, add_stop, suggest, stats
- **Kein** `create_trip`-Tool
- **Kein** Story-Generierungs-Trigger

Der Agent hilft beim **Planen und Bearbeiten** existierender Trips, nicht beim Erstellen neuer. Story-Generierung bleibt vollständig im Wizard-Flow.

**Status:** 🟢 KEIN PROBLEM — Der Agent und der Wizard sind komplementär, nicht konkurrierend.

**Falls `create_trip` hinzugefügt wird:** Empfehlung S2-B aus dem Original-Review ist korrekt — Agent erstellt Trip, Redirect auf Wizard Step 3 für Story-Settings.

---

### S3: `highlights` existiert nicht — ✅ BEREITS BEHOBEN

**Tatsächlicher Code:** Kein Verweis auf `highlights` irgendwo im Agent-Code. Tool-Schema nutzt `notes` korrekt.

**Status:** 🟢 BEHOBEN

---

### S4: HTMX Double-Submit — 🟡 NOCH OFFEN (aber niedrige Priorität)

**Befund ist gültig**, aber es gibt noch **keine HTMX-View** für den Agent. Der Agent ist derzeit nur als Python-Klasse implementiert, ohne View/Template-Integration. Wenn die View gebaut wird, muss `hx-disabled-elt` implementiert werden.

**Aufwand:** 15 Minuten (beim View-Bau)

---

### S5: Synchroner LLM-Call — ✅ BEREITS BEHOBEN

**Tatsächlicher Code:** Der Agent ist vollständig **async**:

```python
async def chat(self, user_message: str, **overrides) -> AgentResponse:
    ...
    result = await completion(...)
```

`llm_service.completion()` nutzt `litellm.acompletion()` — non-blocking.

**Status:** 🟢 BEHOBEN — Kein Risiko für Worker-Blocking.

---

### M1: Hardcodierter System-Prompt — 🟡 AKZEPTABEL FÜR MVP

**Tatsächlicher Code:** System-Prompt ist ein Python-String-Literal (14 Zeilen, klar und fokussiert). Für einen Trip-Management-Agent mit festem Scope ist das akzeptabel.

**Empfehlung:** DB-driven Prompt ist erst relevant wenn:
1. Mehrere Agent-Typen existieren (z.B. Story-Agent, Booking-Agent)
2. A/B-Testing von Prompts nötig ist
3. Nicht-technische User den Prompt anpassen sollen

**Status:** 🟡 TECH DEBT — Kein Blocker, aber bei Skalierung adressieren.

---

### M2: Kein raw_response Storage — 🟡 GÜLTIG (niedrig)

Die Agent-History wird nur in-memory gehalten. Für Debugging und Audit wäre eine Persistence-Schicht sinnvoll. Sollte zusammen mit K7 (Rate-Limiting) als `AgentSession`-Model implementiert werden.

---

### M3: Kein Monitoring — 🟢 TEILWEISE BEHOBEN

`llm_service.py` loggt **jeden** LLM-Call automatisch in `AIUsageLog`:

```python
# apps/ai_services/llm_service.py:149-171
async def _log_usage(config, result, user=None):
    AIUsageLog.objects.create(
        action_type_id=config.get("action_id"),
        model_used_id=config.get("model_id"),
        user=user,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=result.latency_ms,
        success=result.success,
        error_message=result.error,
    )
```

Prometheus-Metriken fehlen, aber DB-basiertes Usage-Tracking ist vorhanden.

---

### M4: Migration-Risiko — ⚪ NICHT ANWENDBAR

Es wurden **keine neuen Models** hinzugefügt. Der Agent nutzt existierende Models (`Trip`, `Stop`, `AIUsageLog`). Kein Migrationsrisiko.

---

## Korrigierte Befund-Zusammenfassung

| ID | Original | Revalidiert | Status | Aufwand |
|----|----------|-------------|--------|---------|
| K1 | 🔴 KRIT | 🟢 BEHOBEN | LiteLLM + DB-Config implementiert | — |
| K2 | 🔴 KRIT | 🟢 BEHOBEN | Korrekte Feldnamen in Handlers | — |
| K3 | 🔴 KRIT | 🟡 OFFEN | Doppeldefinition TripType (TextChoices + LookupBase) | 0.5 Tag |
| K4 | 🔴 KRIT | 🟢 BEHOBEN | User als Dataclass-Feld | — |
| K5 | 🔴 KRIT | 🟡 NIEDRIG | Kein Multi-Create, defensiv trotzdem fixen | 15 Min |
| K6 | 🔴 KRIT | 🟢 BEHOBEN | OpenAI-Format, JSON-serialisierbar | — |
| K7 | 🔴 KRIT | 🔴 OFFEN | Kein Rate-Limiting | 0.5 Tag |
| S1 | 🟠 SCHWER | ⚪ N/A | Kein AgentConversation-Model | — |
| S2 | 🟠 SCHWER | 🟢 KEIN PROBLEM | Agent ist Trip-Management, nicht Wizard-Ersatz | — |
| S3 | 🟠 SCHWER | 🟢 BEHOBEN | `notes` korrekt verwendet | — |
| S4 | 🟠 SCHWER | 🟡 OFFEN | Keine View existiert noch | 15 Min |
| S5 | 🟠 SCHWER | 🟢 BEHOBEN | Vollständig async | — |
| M1 | 🟡 MITTEL | 🟡 AKZEPTABEL | Hardcoded OK für MVP-Scope | — |
| M2 | 🟡 MITTEL | 🟡 GÜLTIG | Keine Session-Persistence | 1 Tag |
| M3 | 🟡 MITTEL | 🟢 TEILWEISE | AIUsageLog existiert, Prometheus fehlt | 0.5 Tag |
| M4 | 🟡 MITTEL | ⚪ N/A | Keine neuen Models | — |

---

## Neue Befunde (nicht im Original-Review)

### N1: 🟠 `handle_add_stop` — Fehlende Autorisierung bei Trip-Zugriff

**Befund:** `handle_add_stop` prüft `Trip.objects.get(id=trip_id, user=user)` — das ist korrekt. **Aber** `handle_suggest_activities` hat keinen User-Check und gibt `instruction`-Text zurück, der vom LLM interpretiert wird. Das ist kein direktes Sicherheitsrisiko (kein DB-Write), aber ein Prompt-Injection-Vektor: Ein manipulierter `city`-Parameter wird direkt in den Instruction-String interpoliert.

**Empfehlung:**

```python
# apps/trips/agent/handlers.py:204
city = args.get("city", "")[:100]  # Truncate
city = city.replace("{", "").replace("}", "")  # Strip template chars
```

**Aufwand:** 15 Minuten

### N2: 🟡 `sync_to_async` Wrapper-Pattern — Potentieller Deadlock

**Befund:** Alle Handler wrappen sync ORM-Calls in `sync_to_async`:

```python
trips = await sync_to_async(_search)()
```

Das ist korrekt für Django 5.x mit ASGI. **Aber:** `llm_service.py` hat einen `sync_completion()`-Wrapper mit `concurrent.futures.ThreadPoolExecutor` (Zeilen 310-330), der bei verschachtelten Event-Loops problematisch sein kann. Der Agent nutzt den async-Pfad direkt, also ist das derzeit kein Problem — sollte aber nicht als Einstiegspunkt verwendet werden.

### N3: 🟡 Fehlendes `create_trip`-Tool

**Befund:** Der Agent kann Trips suchen, Details anzeigen und Stops hinzufügen — aber nicht einen neuen Trip erstellen. Das begrenzt den Nutzen für Erstnutzer erheblich.

**Empfehlung:** `create_trip`-Tool mit:
- `transaction.atomic()` (K5-Empfehlung)
- Validierung aller Pflichtfelder (`name`, `origin`, `start_date`, `end_date`)
- Automatisches `trip_type`-Matching gegen `Trip.TripType.choices`

**Aufwand:** 0.5 Tag

---

## Gesamtbewertung

**Ursprüngliche Review:** 7 kritische, 5 schwere, 4 mittlere = 🔴 ÜBERARBEITUNG ERFORDERLICH

**Nach Codebase-Validierung:** 1 offener Kritischer (K7), 1 offener Mittlerer (K3), 3 neue niedrige Befunde = 🟢 GRUNDSÄTZLICH MERGE-FÄHIG mit Auflagen

### Verbleibendes Must-Do vor Go-Live

| Prio | Befund | Aufwand |
|------|--------|---------|
| 🔴 P0 | K7: Rate-Limiting (Cache-basiert) | 0.5 Tag |
| 🟡 P1 | K3: TripType Doppeldefinition bereinigen | 0.5 Tag |
| 🟡 P1 | N1: Input-Sanitization in suggest_activities | 15 Min |
| 🟡 P2 | K5: Defensiv `transaction.atomic` auf add_stop | 15 Min |

**Geschätzter Restaufwand:** ~1.5 Tage (statt 5-7 Tage im Original-Review)

---

## Architektur-Lob

Die Implementierung ist **architektonisch deutlich sauberer** als der ADR-Entwurf:

1. **LiteLLM statt SDK-Lock-in** — Provider-Swap via DB ohne Code-Änderung
2. **OpenAI-Format Tool-Schema** — Portabel, standardisiert, JSON-serialisierbar
3. **Async-First** — Kein Worker-Blocking
4. **Klarer Scope** — Agent ist Trip-Creation-Pfad (einer von drei), konvergiert mit Wizard/Upload
5. **Usage-Logging** — Automatisch via `AIUsageLog` für jeden Call
6. **User-Auth per Handler** — Saubere Durchreichung, kein mutable State

---

## ADDENDUM: Scope-Gap-Analyse — 3-Pfade-Architektur

> **Version:** v2 (2026-02-14, korrigiert nach Stakeholder-Feedback)
> **Anlass:** Weder Original-Review noch Counter-Review prüfen, ob die **funktionale Kernvorgabe** abgedeckt ist.

### Kernvorgabe

Der Agent ist **einer von drei parallelen Einstiegspfaden** zur Trip-Erstellung. Alle drei Pfade konvergieren am selben Punkt: Trip + Stops existieren in der DB. Danach geht es für alle Pfade identisch weiter (Story-Settings → Review → Generate).

### 3-Pfade-Architektur (Soll)

```
                    ┌─────────────────────────────┐
                    │     TRIP CREATION PHASE      │
                    │   (3 parallele Einstiege)    │
                    └─────────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ▼                    ▼                     ▼
   ┌─────────────────┐ ┌─────────────────┐  ┌─────────────────┐
   │  Pfad A: AGENT  │ │ Pfad B: WIZARD  │  │ Pfad C: UPLOAD  │
   │  (Konversation) │ │ (Manuell/Forms) │  │ (CSV/PDF/ICS)   │
   │                 │ │                  │  │                  │
   │  User erzählt   │ │ Step 1: Basics   │  │ Datei hochladen  │
   │  → Agent fragt  │ │ Step 1.5: Party  │  │ → AI-Parsing     │
   │  → Agent erstellt│ │ Step 2: Stops   │  │ → Bestätigung    │
   └────────┬────────┘ └────────┬─────────┘  └────────┬─────────┘
            │                    │                      │
            └────────────────────┼──────────────────────┘
                                 ▼
                    ┌─────────────────────────────┐
                    │  KONVERGENZPUNKT:            │
                    │  Trip + Stops in DB          │
                    │  (Status: DRAFT/READY)       │
                    └──────────────┬──────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │  GEMEINSAMER WEITERFLUSS     │
                    │  Step 3: Story-Preferences   │
                    │  Step 4: Review + Generate   │
                    │  → Enrichment (ADR-020/026)  │
                    │  → Story-Pipeline (ADR-025)  │
                    └─────────────────────────────┘
```

### Ist-Zustand der 3 Pfade

| Pfad | Status | Implementierung |
|------|--------|----------------|
| **B: Wizard** (Manuell) | ✅ Vollständig | `apps/trips/wizard.py` — Steps 1→1.5→2→3→4 |
| **C: Upload** (CSV/PDF) | ✅ Vollständig | `apps/trips/views_import.py` (ADR-016) — AI-Parsing, Rate-Limiting, Bestätigung |
| **A: Agent** (Konversation) | 🟠 Infrastruktur da, Funktion fehlt | `apps/trips/agent/` — Tool-Loop existiert, aber **kein `create_trip`-Tool** |

### Agent-Pfad: Was existiert vs. was fehlt

**Existierende Infrastruktur (solide):**

- `ConversationalTripAgent` mit async Tool-Use-Loop
- LiteLLM-basiert, DB-driven Config via `AIActionType`
- OpenAI-Format Tool-Schemas, JSON-serialisierbar
- Usage-Logging via `AIUsageLog`
- 5 Read/Add-Tools (`search_trips`, `get_trip_details`, `add_stop`, `suggest_activities`, `get_trip_stats`)

**Fehlende Creation-Tools für Kernvorgabe:**

| Tool | Zweck | Aufwand |
|------|-------|--------|
| `create_trip` | Trip anlegen (Name, Origin, Dates, TripType) in `transaction.atomic` | 0.5 Tag |
| `update_stop` | Existierenden Stop bearbeiten | 0.25 Tag |
| `add_transport` | Transport zwischen Stops anlegen | 0.5 Tag |
| `add_segment` | Aktivität/Szene zu einem Stop hinzufügen (→ `TripSegment`) | 0.75 Tag |
| `finalize_trip` | Status → READY, Return URL für Wizard Step 3 | 0.25 Tag |
| System-Prompt | Konversationsfluss inkl. proaktiver Aktivitäten-Abfrage | 0.5 Tag |
| Rate-Limiting (K7) | Cache-basiert, analog zu Upload-Pfad | 0.5 Tag |
| Tests | Unit + Integration | 0.5 Tag |

**Geschätzter Aufwand: ~4 Tage**

### Szenen- und Aktivitäten-Schicht (ADR-009 Segment-System)

Der Agent muss **nicht nur Stops erstellen**, sondern auch erfragen, **was an jedem Stop passieren soll**. Diese Aktivitäten, Unterkünfte und Erlebnisse sind die Szenen der späteren Story und werden als `TripSegment` gespeichert.

**Datenmodell-Mapping:**

```
Trip: "Wellnessreise Rom" (wellness)
├── Stop: Bozen (3 Tage)
│   ├── TripSegment: accommodation/hotel (Wellness-Hotel)
│   ├── TripSegment: activity/spa (Thermalbad)
│   └── TripSegment: activity/hiking (Dolomiten-Wanderung)
├── Stop: Verona (2 Tage)
│   ├── TripSegment: accommodation/hotel
│   ├── TripSegment: activity/museum (Arena, Julias Balkon)
│   └── TripSegment: activity/restaurant (Abendessen Piazza Erbe)
└── Stop: Rom (Endziel)
    └── TripSegment: ...
```

**Existierende Datenstruktur (`apps/trips/models/segments.py`):**

- `SegmentCategory` — Top-Level: `transport`, `accommodation`, `activity`
- `SegmentType` — Spezifisch: `museum`, `restaurant`, `spa`, `hotel`, `flight`, etc.
- `TripSegment` — Instanz verknüpft mit Trip + Stop, enthält:
  - `segment_data` (JSONField) — flexible Daten (Name, Details)
  - `story_notes` — Notizen für Story-Generierung
  - `emotional_tone` — "romantisch", "aufregend", "nachdenklich"
  - `duration_minutes` — Dauer der Aktivität
  - `reading_efficiency` — Wie viel der Zeit zum Lesen nutzbar ist (aus `SegmentType`)

**`add_segment`-Tool-Schema (Entwurf):**

```python
{
    "type": "function",
    "function": {
        "name": "add_segment",
        "description": (
            "Add an activity, accommodation, or experience to a stop. "
            "Each segment becomes a scene in the generated story."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "stop_id": {"type": "integer", "description": "Stop to add segment to"},
                "category": {
                    "type": "string",
                    "enum": ["activity", "accommodation"],
                    "description": "Segment category",
                },
                "type_slug": {
                    "type": "string",
                    "description": "Segment type: museum, restaurant, spa, hotel, hiking, ...",
                },
                "description": {"type": "string", "description": "What the traveler wants to do"},
                "duration_minutes": {"type": "integer", "description": "Estimated duration"},
                "emotional_tone": {
                    "type": "string",
                    "description": "Desired mood: romantisch, aufregend, nachdenklich, entspannt",
                },
            },
            "required": ["stop_id", "category", "type_slug", "description"],
        },
    },
}
```

**System-Prompt-Verhalten:** Der Agent muss **proaktiv** nach Aktivitäten fragen, wenn der User nur Orte nennt. Beispiel:

> User: "3 Tage Bozen, dann 2 Tage Verona"
> Agent: "Was möchtest du in Bozen erleben? Hast du bestimmte Aktivitäten geplant — Wandern, Wellness, Stadtbummel? Und in Verona hast du Museen und gutes Essen erwähnt — gibt es bestimmte Restaurants oder Sehenswürdigkeiten die du besuchen möchtest?"

### Konvergenz-Design

Entscheidend: Der Agent muss **nicht** Story-Settings, Enrichment oder Story-Generierung implementieren. Er erstellt Trip + Stops + Segmente und gibt ab:

```python
# Letzter Schritt des Agent-Pfads:
async def handle_finalize_trip(user, args):
    trip = Trip.objects.get(id=args["trip_id"], user=user)
    trip.status = Trip.Status.READY
    trip.save(update_fields=["status", "updated_at"])
    return {
        "success": True,
        "message": f"Reise '{trip.name}' bereit!",
        "next_url": f"/trips/{trip.pk}/edit/",
        "hint": "Story-Einstellungen können jetzt konfiguriert werden.",
    }
```

Der User wird dann auf die Trip-Edit-Seite geleitet, wo Wizard Steps 3+4 (Story-Preferences, Review+Generate) wie gewohnt ablaufen — identisch zu Pfad B (Wizard) und Pfad C (Upload). Die TripSegmente (Szenen) fließen automatisch in die Story-Generierung ein, weil der `PromptBuilder` bereits `TripSegment.get_prompt_context()` nutzt.

### Beispiel-Konversation (Soll-Zustand nach Implementierung)

```
User:  Ich möchte eine Wellnessreise nach Rom machen.
       Ein Stopp soll drei Tage in Bozen sein und zwei Tage in Verona.
       Dort möchte ich Museen besuchen und gut essen.

Agent: Super! Ich lege die Reise an.

       [create_trip] → Trip "Wellnessreise Rom" (wellness)
       [add_stop]    → Bozen, Italien (3 Tage)
       [add_stop]    → Verona, Italien (2 Tage)
       [add_stop]    → Rom, Italien (Endziel)

       Für Verona habe ich notiert: Museen und gutes Essen.

       [add_segment] → Verona: activity/museum "Museumsbesuche"
       [add_segment] → Verona: activity/restaurant "Kulinarische Erlebnisse"

       Was möchtest du in Bozen machen? Wellness, Wandern in den
       Dolomiten, Stadtbummel? Und wie lange planst du in Rom zu sein?

User:  In Bozen Wellness und eine Dolomiten-Wanderung.
       Rom dann 3 Tage mit Kolosseum und Vatikan.

Agent: [add_segment] → Bozen: activity/spa "Wellness/Thermalbad"
       [add_segment] → Bozen: activity/hiking "Dolomiten-Wanderung"
       [add_segment] → Rom: activity/sightseeing "Kolosseum"
       [add_segment] → Rom: activity/sightseeing "Vatikan"

       Perfekt! Deine Reise:
       • Bozen (3 Tage): Wellness + Dolomiten-Wanderung
       • Verona (2 Tage): Museen + kulinarische Erlebnisse
       • Rom (3 Tage): Kolosseum + Vatikan
       • 8 Tage gesamt, 6 geplante Aktivitäten

       Soll ich noch Unterkünfte oder Transporte zwischen den
       Stopps ergänzen, oder möchtest du mit den Story-Einstellungen
       weitermachen? [Link: /trips/42/edit/]
```

### Review-Defizit

Weder Original-Review noch Counter-Review v1 erkennen die **3-Pfade-Architektur** als Design-Prinzip:

- **Original-Review** prüft technische Bugs im ADR-Draft, versteht aber nicht, dass der Agent nur Trip-Erstellung verantwortet und danach an den existierenden Flow abgibt
- **Counter-Review v1** validiert die 16 Befunde gegen Code, stuft den Agent fälschlich als "Trip-Management-Assistent" ein — tatsächlich ist er als Trip-Creation-Pfad gedacht, nur mit unvollständiger Tool-Ausstattung
- **S2 im Original-Review** ("Story-Settings fehlen im Agent-Flow") ist kein Fehler — der Agent soll explizit **nicht** Story-Settings abfragen, sondern nach Trip-Erstellung an Steps 3+4 übergeben

### Zusammenfassung

| Aspekt | Bewertung |
|--------|-----------|
| Technische Infrastruktur (LiteLLM, async, DB-Config) | 🟢 Solide |
| Read-/Query-Tools (search, details, stats) | 🟢 Vollständig |
| Trip-Creation-Tools (create, transport, finalize) | 🔴 Fehlen |
| Szenen-/Aktivitäten-Layer (`add_segment` → `TripSegment`) | 🔴 Fehlt — kritisch für Story-Qualität |
| Proaktive Aktivitäten-Abfrage im System-Prompt | 🔴 Fehlt |
| Konvergenz mit existierendem Flow (Steps 3+4) | 🟢 Architektonisch klar, `TripSegment.get_prompt_context()` existiert |
| Rate-Limiting | 🔴 Fehlt (Pfad C hat es bereits: 20/h, 100/Tag) |
| Gesamtaufwand bis MVP | **~4 Tage** |

---

## ERGÄNZUNG: Chat-Agent als Platform-Service — Konzept-Review

> **Hinzugefügt:** 2026-02-14
> **Kontext:** Der Ansatz, das Agent-Pattern als `platform/packages/chat-agent/` zu abstrahieren, wird gegen den existierenden Code und die Platform-Architektur bewertet.

### Bewertung des Grundgedankens

**🟢 Strategisch richtig.** Das Muster "NL-Eingabe → Domänen-Aktion → Antwort" ist tatsächlich domänenunabhängig. Die vier Beispiele (cad-hub, bfagent, travel-beat, weltenhub) belegen das. Ein gemeinsames Package verhindert, dass jede App den Tool-Use-Loop, Session-Management und LLM-Integration neu implementiert.

### Kritische Punkte am vorgeschlagenen Design

#### 1. 🔴 IntentResolver vs. Tool-Use — Architektur-Entscheidung

Das vorgeschlagene Design basiert auf **Intent-Klassifikation**:

```
NL-Eingabe → IntentResolver (Pattern + LLM) → route to Handler → execute → format
```

Der existierende travel-beat Agent nutzt aber **LLM Tool-Use**:

```
NL-Eingabe → LLM (mit Tool-Definitionen) → LLM entscheidet Tool → execute → LLM formuliert
```

Das sind **zwei fundamental verschiedene Architekturen**:

| Aspekt | Intent-basiert (vorgeschlagen) | Tool-Use (existierend) |
|--------|-------------------------------|----------------------|
| Intent-Definition | App definiert Intents vorab | App definiert Tools, LLM wählt |
| Multi-Turn | Schwierig (Kontext-Tracking) | Natürlich (LLM hat History) |
| Multi-Tool pro Turn | Nicht vorgesehen | LLM ruft N Tools in einer Runde |
| Kosten pro Query | Niedrig (Pattern-Match first) | Höher (immer LLM-Call) |
| Flexibilität | Nur vordefinierte Intents | LLM kombiniert Tools kreativ |
| Fehlertoleranz | Fehlklassifikation = falscher Handler | LLM korrigiert sich selbst |

**Empfehlung:** Tool-Use als primäre Architektur, **nicht** Intent-Klassifikation. Gründe:

- travel-beat beweist, dass es funktioniert
- OpenAI-Format Tool-Schemas sind standardisiert und portabel
- Multi-Turn-Konversationen (wie Reise-Planung) brauchen keine Intent-Klassifikation
- LiteLLM oder creative-services `LLMClient` unterstützen Tool-Use nativ

Für einfache Queries ("Wie viele Wände im 2. OG?") kann ein **Hybrid** sinnvoll sein: Erst Pattern-Match für schnelle/billige Queries, Fallback auf LLM Tool-Use für komplexe.

#### 2. 🟠 "QueryEngine" impliziert Read-Only

Die Beispiel-Queries sind alle lesend:

- "Wie viele tragende Wände im 2. OG?"
- "Welche Kapitel haben noch keinen Entwurf?"
- "Zeige alle Stops in Italien mit weniger als 3 Fotos"

Aber der travel-beat Agent **schreibt** Daten: `create_trip`, `add_stop`, `add_segment`. Das ist kein Query, sondern ein **Command**.

**Empfehlung:** Umbenennung `QueryEngine` → `DomainToolkit`. Ein Toolkit enthält sowohl Queries (read) als auch Commands (write). Jede App registriert ein Toolkit:

```python
@register_toolkit("travel-beat")
class TravelBeatToolkit(DomainToolkit):
    """Trip-Planung und -Verwaltung."""
    
    tools = TRIP_TOOLS  # OpenAI-Format, bereits existierend
    
    async def execute(self, tool_name: str, args: dict, 
                      ctx: AgentContext) -> ToolResult:
        return await TOOL_HANDLERS[tool_name](ctx.user, args)
```

#### 3. 🟠 Overlap mit creative-services

`creative-services` bietet bereits:

- `LLMClient` — Provider-agnostischer LLM-Aufruf
- `LLMRegistry` — DB-driven Model-Konfiguration
- `DynamicLLMClient` — Tier-basierte Modellauswahl
- `UsageTracker` — Token/Cost-Tracking
- `BaseHandler` + `BaseContext` — Handler-Pattern

`chat-agent` sollte **auf** creative-services aufbauen, nicht parallelisieren:

```
creative-services        → LLM-Aufrufe, Usage-Tracking
    ↑
chat-agent               → Tool-Use-Loop, Session, Registry
    ↑
App-Toolkit (pro App)    → Tool-Definitionen + Handler
```

#### 4. 🟡 Session-Storage — 3 Backends nötig

Die Conversation-History muss irgendwo leben. Je nach App verschiedene Anforderungen:

| Backend | Use Case | Trade-Off |
|---------|----------|-----------|
| In-Memory | Dev, Spike | Verlust bei Restart |
| Redis | Multi-Worker, Production | Kein Audit-Trail |
| DB (`ChatSession`-Model) | Audit, GDPR, Debugging | Latenz, Migration pro App |

**Empfehlung:** Interface + 3 Implementierungen. Default: Redis für Production, In-Memory für Tests:

```python
class SessionBackend(Protocol):
    async def load(self, session_id: str) -> ChatSession | None: ...
    async def save(self, session: ChatSession) -> None: ...
    async def delete(self, session_id: str) -> None: ...

class RedisSessionBackend(SessionBackend): ...
class InMemorySessionBackend(SessionBackend): ...
class DjangoORMSessionBackend(SessionBackend): ...
```

#### 5. 🟡 `@register_engine` Decorator — Import-Timing-Problem

```python
@register_engine("cad")
class CADQueryEngine(QueryEngine): ...
```

Dieses Pattern erfordert, dass das Modul **importiert** wird, bevor die Registry abgefragt wird. In Django ist die Import-Reihenfolge nicht garantiert.

**Empfehlung:** Django `AppConfig.ready()` statt Decorator:

```python
# cad-hub: apps/query/apps.py
class QueryConfig(AppConfig):
    def ready(self):
        from chat_agent import registry
        from .toolkit import CADToolkit
        registry.register("cad", CADToolkit())
```

#### 6. 🟡 ResponseFormatter — Per App, nicht zentral

Eine CAD-Antwort (Tabelle mit Wänden, Maßen, Materialien) sieht fundamental anders aus als eine travel-beat-Antwort (Trip-Zusammenfassung mit Stops-Karte). Der Formatter gehört in die App, nicht ins Package.

**Empfehlung:** `DomainToolkit` definiert optional einen `format_response()` Hook. Default: LLM formuliert die Antwort als Text.

### Korrigierter Struktur-Vorschlag

```
platform/packages/chat-agent/
├── pyproject.toml                # Depends: creative-services, pydantic
├── src/chat_agent/
│   ├── __init__.py
│   ├── agent.py                  # ChatAgent — Tool-Use-Loop (Kern)
│   ├── session.py                # SessionBackend Protocol + Implementierungen
│   ├── registry.py               # ToolkitRegistry — Apps registrieren DomainToolkits
│   ├── toolkit.py                # DomainToolkit ABC — Tools + Handlers
│   ├── models.py                 # Pydantic: ChatMessage, ToolResult, AgentContext
│   └── middleware.py             # Django Middleware (optional, setzt AgentContext)
└── tests/
```

**Kern-Unterschiede zum Vorschlag:**

| Vorschlag | Korrektur | Begründung |
|-----------|-----------|------------|
| `service.py` (Orchestrator) | `agent.py` (Tool-Use-Loop) | Nicht Service-Layer, sondern Agent-Pattern |
| `intent.py` (IntentResolver) | **Entfällt** | LLM + Tools statt Intent-Klassifikation |
| `registry.py` (QueryEngineRegistry) | `registry.py` (ToolkitRegistry) | Toolkits statt Engines |
| `formatters.py` (zentral) | **Entfällt** (per App) | Jede App formatiert selbst |
| `models.py` (ChatSession) | `session.py` (Protocol + Backends) | Storage-agnostisch |

### Minimal Viable `ChatAgent` — Kern-Klasse

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
    action_code: str = "chat"  # Für LLM-Config / Usage-Tracking
    
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
            
            # Execute tools
            session.messages.append(_build_tool_msg(result))
            for tc in result.tool_calls:
                tool_result = await self.toolkit.execute(
                    tc.name, tc.arguments,
                    AgentContext(user=user, session=session),
                )
                session.messages.append(
                    _build_tool_result_msg(tc.id, tool_result)
                )
        
        await self.session_backend.save(session)
        return AgentResponse(content=result.content, rounds=round_num + 1)
```

**Vergleich mit existierendem `ConversationalTripAgent`:**

| Aspekt | TripAgent (jetzt) | ChatAgent (generalisiert) |
|--------|-------------------|--------------------------|
| Tools | Hardcoded `TRIP_TOOLS` | `toolkit.tool_schemas` (injected) |
| Handler | `_execute_tool()` mit if/elif | `toolkit.execute()` (polymorphe Dispatch) |
| History | `self.history` (in-memory list) | `session_backend.load/save()` |
| System-Prompt | Hardcoded String | Constructor-Parameter |
| LLM-Config | `ACTION_CODE = "trip_planning"` | `action_code` Parameter |

Der bestehende `ConversationalTripAgent` wird dann ein Thin-Wrapper:

```python
# apps/trips/agent/trip_agent.py (nach Refactoring)
from chat_agent import ChatAgent, RedisSessionBackend
from .toolkit import TravelBeatToolkit

def get_trip_agent(user) -> ChatAgent:
    return ChatAgent(
        toolkit=TravelBeatToolkit(),
        session_backend=RedisSessionBackend(),
        system_prompt=SYSTEM_PROMPT,
        action_code="trip_planning",
    )
```

### Implementierungs-Reihenfolge

| Phase | Aufgabe | Aufwand |
|-------|---------|--------|
| 0 | travel-beat Agent fertig ausbauen (create_trip, add_segment, etc.) | ~4 Tage |
| 1 | `ChatAgent` + `DomainToolkit` aus TripAgent extrahieren | 1 Tag |
| 2 | `SessionBackend` (InMemory + Redis) | 0.5 Tag |
| 3 | `ToolkitRegistry` + Django-Integration | 0.5 Tag |
| 4 | Zweite App anbinden (z.B. bfagent: "Welche Kapitel?") | 1 Tag |
| 5 | Tests + Docs | 1 Tag |
| | **Gesamt (nach Phase 0)** | **~4 Tage** |

**Wichtig:** Phase 0 zuerst. Nicht die Abstraktion vor der konkreten Implementierung bauen. Der travel-beat Agent muss **vollständig funktionieren** (alle Tools, Szenen-Erhebung, Konvergenz mit Wizard), bevor er zum generalisierten Package extrahiert wird. Sonst abstrahiert man die falschen Dinge.

### Risiken

| Risiko | Mitigation |
|--------|-----------|
| Premature Abstraction — Package bevor 2. App existiert | Phase 0+4 sequentiell, erst extrahieren wenn 2 Apps es nutzen |
| creative-services vs. llm_service.py Divergenz | Entscheidung: `chat-agent` nutzt `creative-services.LLMClient` ODER LiteLLM — nicht beides |
| Session-Migration bei Backend-Wechsel | Session-ID Format + TTL von Anfang an definieren |
| SegmentType-Lookup in add_segment erfordert DB-Zugriff | `DomainToolkit.execute()` hat vollen Django ORM Zugriff via `AgentContext` |

---

*Counter-Review + Addendum v3 + Platform-Service-Review abgeschlossen: 2026-02-14*
