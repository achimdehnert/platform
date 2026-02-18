# ADR-007 Review: Conversational Trip Agent

> **Reviewer:** Senior Architecture Review (Production-Critical)  
> **Datum:** 2026-02-13  
> **Review-Typ:** Blocking Review – Merge nicht freigeben  
> **Bewertung:** 🔴 ÜBERARBEITUNG ERFORDERLICH (7 kritische, 5 schwere, 4 mittlere Befunde)

---

## Zusammenfassung

Das Konzept ist strategisch korrekt. Die Umsetzung im ADR enthält jedoch **fundamentale Architekturverletzungen**, **falsche Model-Referenzen** und **fehlende Invarianten**, die in Produktion zu Dateninkonsistenz, Vendor-Lock-in und stillen Fehlern führen würden.

---

## KRITISCH (🔴 P0 – Blocker)

### K1: Direkte `anthropic.Anthropic()` Instanziierung – Architekturbruch

**Befund:**  
Der `TripAgentService` erstellt `self.client = anthropic.Anthropic()` direkt. Das umgeht vollständig die etablierte Abstraktionsschicht:

```
Existierend:  LLMConfig → LLMProvider → CreativeServicesClient → ServiceResult
ADR:          anthropic.Anthropic() → rohes Response-Parsing
```

Der gesamte bestehende Code nutzt `LLMConfig(provider=LLMProvider.ANTHROPIC, model=..., api_key=...)` und gibt `ServiceResult` zurück. Der ADR-Code ist ein Paralleluniversum.

**Risiko:**  
- Provider-Wechsel (z.B. auf Groq für "fast" Tasks) ist unmöglich
- Kein zentrales Token-Tracking, kein Billing-Hook
- API-Key-Handling an zwei Stellen (Settings + Environment)
- Circuit Breaker / Retry-Logik nicht angebunden
- Wenn `creative-services` Package aktiv ist, existieren zwei LLM-Pfade

**Empfehlung:**  
Agent MUSS durch `CreativeServicesClient` oder ein neues `TripAgentHandler` gehen, der `BaseLLMHandler`-Pattern folgt:

```python
class TripAgentHandler:
    """Follows established handler pattern."""
    
    def __init__(self, llm_id=None):
        self.llm_id = llm_id
    
    def get_llm(self):
        # LLM-Auswahl mit DB-Lookup + Fallback
        ...
    
    def execute(self, context: AgentContext) -> ServiceResult:
        # Multi-turn agent loop
        return ServiceResult(success=True, data=..., llm_used=..., tokens_used=...)
```

**Problem:** Tool Use ist ein Anthropic-spezifisches Feature. Bei Provider-Abstraktion entsteht ein Dilemma:

**Lösungsansatz:** `TripAgentHandler` deklariert `requires_tool_use = True` und der `LLMConfig`-Resolver wählt dafür ausschließlich Anthropic/OpenAI (die Tool Use unterstützen). Das ist kein Vendor-Lock-in, sondern Feature-Routing – analog zu `use_for: ["chapter_write"]` in `LLMConfig.PROVIDERS`.

---

### K2: Falsche Model-Feldnamen – Dateninkonsistenz

**Befund:**  
Der ADR-Code referenziert Felder die auf dem `Trip` / `Stop` Model **nicht existieren**:

| ADR verwendet | Tatsächliches Feld | Model |
|---|---|---|
| `trip_type='solo'` | `TripType.CITY`, `.WELLNESS`, etc. | `Trip` |
| `Stop(location=...)` | `Stop(city=..., country=...)` | `Stop` |
| `Stop(highlights='...')` | `Stop(notes=...)` – `highlights` existiert nicht | `Stop` |
| Kein `accommodation_type` | Pflichtfeld auf `Stop` | `Stop` |

Zusätzlich: Das `Trip`-Model hat **kein** `protagonist_name`, `protagonist_gender` – diese gehören zum `Story`-Model (Wizard Step 3). Der Agent setzt Story-Felder auf dem Trip, was falsch ist.

**Risiko:**  
Code kompiliert nicht. `IntegrityError` bei `Stop.objects.create()` wegen fehlendem `city`-Feld. Jeder Test schlägt fehl.

**Empfehlung:**  
Extraction Schema muss exakt den DB-Feldern entsprechen:

```python
class ExtractedStop(BaseModel):
    city: str
    country: str = ""
    arrival_date: Optional[date] = None
    departure_date: Optional[date] = None
    accommodation_type: str = "hotel"  # Default aus Stop.AccommodationType
    notes: str = ""
    order: int

class ExtractedTrip(BaseModel):
    origin: Optional[str] = None
    trip_type: Optional[str] = None  # Muss Trip.TripType.choices matchen!
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    stops: list[ExtractedStop] = Field(default_factory=list)
    # KEIN protagonist_name, protagonist_gender – gehört zu Story
```

---

### K3: `trip_type` Semantik-Konflikt

**Befund:**  
Im ADR wird `trip_type` als Reise-Gruppierung verwendet (`solo/couple/family/group`). Im tatsächlichen `Trip`-Model ist `trip_type` die **Reisekategorie** (`city/beach/wellness/backpacking/business/family/adventure/cruise`).

Der User sagt: "Wellnessreise mit Partner" – das sind **zwei verschiedene Informationen**:
- `trip_type = TripType.WELLNESS` (Kategorie)
- Reiseparty-Größe: 2 Personen (existiert noch gar nicht als Feld)

**Risiko:**  
Agent extrahiert "couple" und schreibt das in `trip_type`, wo nur `Trip.TripType.choices` valide ist. Django validiert das nicht auf DB-Ebene (CharField), aber alle Downstream-Logik (Story-Generierung, PromptBuilder) erwartet die korrekten Enum-Werte.

**Empfehlung:**  
1. Der Agent muss `trip_type` auf `Trip.TripType.choices` mappen
2. "Paar/Solo/Familie/Gruppe" ist ein separates Konzept – entweder neues Feld `party_type` via Migration oder in `user_notes` erfassen
3. System-Prompt muss die erlaubten `trip_type`-Werte explizit kennen (DB-driven, nicht hardcoded)

---

### K4: `self._current_user` – Stiller State auf Service-Instanz

**Befund:**  
In `_tool_create_trip()` referenziert der Code `self._current_user`, aber dieses Attribut wird **nirgends gesetzt**. Es gibt keinen Mechanismus, wie der User-Kontext in die Tool-Execution gelangt.

```python
def _tool_create_trip(self, data: dict) -> dict:
    trip = Trip.objects.create(
        user=self._current_user,  # ← UNDEFINED
        ...
    )
```

**Risiko:**  
`AttributeError` in Produktion. Kein Trip wird jemals erstellt.

**Empfehlung:**  
User-Kontext muss explizit durchgereicht werden, nicht als mutable State auf der Service-Klasse:

```python
def process_message(self, *, conversation: AgentConversation, user_message: str) -> dict:
    # User kommt aus conversation.user – nicht als Service-State
    ...

def _tool_create_trip(self, data: dict, *, user: User) -> dict:
    # User als expliziter Parameter
```

---

### K5: Kein `@transaction.atomic` bei Trip+Stops-Erstellung

**Befund:**  
`_tool_create_trip` erstellt einen `Trip` und danach in einer Schleife `Stop`-Objekte. Schlägt die Schleife bei Stop Nr. 3 fehl (z.B. Validierungsfehler), existiert ein Trip mit nur 2 Stops in der Datenbank.

**Risiko:**  
Partielle Trip-Erstellung. Daten-Invariante verletzt: Ein Trip mit weniger Stops als der User bestätigt hat. Kein Rollback-Mechanismus.

**Empfehlung:**

```python
from django.db import transaction

def _tool_create_trip(self, data: dict, *, user: User) -> dict:
    try:
        trip_data = ExtractedTrip.model_validate(data)
        
        with transaction.atomic():
            trip = Trip.objects.create(...)
            stops = [
                Stop(trip=trip, city=s.city, country=s.country, ...)
                for s in trip_data.stops
            ]
            Stop.objects.bulk_create(stops)
        
        return {'success': True, 'trip_id': trip.id}
    except Exception as e:
        ...
```

---

### K6: Tool Use Loop ohne Conversation-Serialisierung

**Befund:**  
`_agent_loop` baut intern eine `messages`-Liste auf, die bei jedem Tool-Use-Iteration erweitert wird. Diese erweiterte Liste wird aber **nicht in die DB persistiert**. Wenn der Prozess nach Tool-Call 2 von 3 abstürzt (Worker-Restart, Timeout), ist der gesamte Kontext verloren.

Zusätzlich: `response.content` (mit `ToolUseBlock`-Objekten) wird direkt in die Messages-Liste gesteckt. Diese Anthropic-SDK-Objekte sind nicht JSON-serialisierbar und können nicht in `AgentMessage.tool_calls` (JSONField) gespeichert werden.

**Risiko:**  
- Datenverlust bei Worker-Crash
- `TypeError: Object of type ToolUseBlock is not JSON serializable`
- Nicht-reproduzierbare Konversationsverläufe

**Empfehlung:**  
Tool-Calls müssen als serialisierbares Dict gespeichert werden:

```python
tool_calls_serializable = [
    {'id': b.id, 'name': b.name, 'input': b.input}
    for b in response.content if b.type == 'tool_use'
]
```

---

### K7: Keine Rate-Limiting / Abuse-Protection

**Befund:**  
Es gibt keine Begrenzung wie viele Konversationen ein User starten darf, und keine Kosten-Obergrenze pro User/Tag. `MAX_TURNS = 20` pro Conversation, aber ein User kann beliebig viele Conversations starten.

**Risiko:**  
Ein einzelner User kann durch Script-Automatisierung die API-Kosten explodieren lassen. Bei $0.08/Trip und 10.000 automatisierten Requests = $800.

**Empfehlung:**

```python
# In process_message(), vor API-Call:
daily_conversations = AgentConversation.objects.filter(
    user=conversation.user,
    created_at__date=timezone.now().date(),
).count()

if daily_conversations > settings.AGENT_MAX_DAILY_CONVERSATIONS:  # DB-driven!
    raise AgentRateLimitError("Tägliches Limit erreicht")
```

---

## SCHWER (🟠 P1 – Vor Go-Live fixen)

### S1: `AgentConversation.extracted_data` ist unkontrolliertes JSONField

**Befund:**  
`extracted_data = models.JSONField(default=dict)` speichert beliebiges JSON ohne Schema-Validierung auf DB-Ebene. Jeder Tool-Call überschreibt den gesamten Inhalt (`conversation.extracted_data = call.get('input', {})`), statt progressiv zu mergen.

**Risiko:**  
Ein fehlerhafter LLM-Response löscht alle bisherigen Extraktionen. Kein Audit-Trail was wann extrahiert wurde.

**Empfehlung:**  
Progressives Update mit Validierung:

```python
def _update_extracted_data(self, conversation, new_data: dict) -> None:
    validated = ExtractedTrip.model_validate(new_data)
    # Nur nicht-None Felder übernehmen (progressive Anreicherung)
    current = conversation.extracted_data or {}
    for key, value in validated.model_dump(exclude_none=True).items():
        if key == 'stops' and value:
            current['stops'] = value  # Stops immer komplett ersetzen
        elif value:
            current[key] = value
    conversation.extracted_data = current
```

---

### S2: Story-Settings (Genre, Spice, Protagonist) fehlen im Agent-Flow

**Befund:**  
Der Agent erfasst Route + Daten, aber der Wizard-Step 3 (Story-Einstellungen: Genre, Spice-Level, Protagonist, Trigger-Avoidance) wird komplett übersprungen. Diese Daten werden aber vom `PromptBuilder` und `StoryGenerator` zwingend benötigt.

**Risiko:**  
Trip wird erstellt, aber Story-Generierung schlägt fehl oder nutzt Defaults die der User nie bestätigt hat.

**Empfehlung:**  
Zwei Optionen:

**A)** Agent fragt auch Story-Settings ab (erhöht Conversation-Länge um ~2 Turns)  
**B)** Agent erstellt Trip → Redirect auf Wizard Step 3 (Story-Settings) → dann Step 4 (Review)  

Option B ist der bessere Trade-Off: Agent ersetzt Steps 1+2, Steps 3+4 bleiben.

---

### S3: `highlights` Feld existiert nicht auf Stop-Model

**Befund:**  
Der ADR erstellt `Stop(highlights=', '.join(stop_data.highlights))`. Das `Stop`-Model hat `notes` (TextField) und spezifische Felder wie `accommodation_type`, aber kein `highlights`-Feld.

**Risiko:**  
`TypeError` oder stilles Ignorieren durch Django (kwargs werden bei `create()` nicht automatisch validiert – sie werfen `TypeError: Stop() got an unexpected keyword argument 'highlights'`).

**Empfehlung:**  
Extrahierte Highlights → `Stop.notes` mappen. Oder als separates Feld per Migration hinzufügen, falls Highlights semantisch von Notes getrennt sein sollen.

---

### S4: HTMX View hat keine CSRF-Race-Condition Protection

**Befund:**  
Der `agent_message` View nutzt `require_POST` mit CSRF, aber es gibt keine Protection gegen Doppel-Submits (User klickt mehrfach schnell auf "Senden").

**Risiko:**  
Doppelte API-Calls, doppelte Token-Kosten, potenziell doppelte Trip-Erstellung wenn der User "Ja, erstellen" bestätigt und doppelt klickt.

**Empfehlung:**

```html
<!-- Frontend: Button disablen nach Submit -->
<button type="submit" class="btn btn-primary"
        hx-disabled-elt="this"
        hx-indicator="#loading">
```

```python
# Backend: Idempotency via Conversation-Status
def agent_message(request):
    ...
    if conversation.status != AgentConversation.Status.ACTIVE:
        return HttpResponse('')  # Silently ignore
```

---

### S5: Keine Celery-Integration für LLM-Calls

**Befund:**  
Der Agent-Loop läuft synchron im Django-Request-Cycle. Ein Tool-Use-Loop mit 3 Iterationen bedeutet 3 sequentielle API-Calls à 1-3 Sekunden = 3-9 Sekunden Antwortzeit. Bei Gunicorn mit `--timeout 30` ist das knapp.

**Risiko:**  
Gateway-Timeouts bei komplexen Konversationen. Blockierte Worker-Threads.

**Empfehlung:**  
Für MVP: Synchron ist akzeptabel mit `hx-indicator` Loading-State. Für Produktion: Celery-Task mit SSE/WebSocket-Push für die Antwort (analoges Pattern wie Story-Generierung).

---

## MITTEL (🟡 P2 – Sollte adressiert werden)

### M1: System-Prompt enthält hardcodierte Business-Logik

**Befund:**  
`SYSTEM_PROMPT` ist ein Python-String mit hardcodierten Regeln wie "MAXIMAL 3 Rückfragen" und "Pflichtfelder: mindestens 1 Stopp". Das widerspricht dem DB-driven Prinzip.

**Empfehlung:**  
System-Prompt sollte aus `PromptTemplate`-Model geladen werden, mindestens die variablen Teile (erlaubte TripTypes, Pflichtfelder, Max-Fragen).

---

### M2: `AgentMessage.content` speichert nur finalen Text

**Befund:**  
Bei Tool-Use enthält die Claude-Response sowohl Text als auch Tool-Use-Blocks. Der Code extrahiert nur `text`-Blocks. Wird der Agent-Loop bei einem Re-Play (z.B. nach Crash) aus der DB rekonstruiert, fehlen die Tool-Use-Blocks in der History.

**Empfehlung:**  
Separate Speicherung: `content` für User-sichtbaren Text, `raw_response` (JSONField) für vollständige Claude-Response inkl. Tool-Blocks.

---

### M3: Kein Monitoring / Alerting

**Befund:**  
Keine Prometheus-Metriken für Agent-Nutzung. Kein Alert bei hoher Fehlerrate oder ungewöhnlichen Token-Kosten.

**Empfehlung:**

```python
# Prometheus Counters (analoges Pattern zu ARCHITECTURE_OPTIMIZATIONS.md)
agent_conversations_total = Counter('agent_conversations_total', 'Total conversations', ['status'])
agent_tokens_total = Counter('agent_tokens_total', 'Total tokens consumed')
agent_errors_total = Counter('agent_errors_total', 'Total agent errors', ['error_type'])
agent_trip_creation_duration = Histogram('agent_trip_creation_seconds', 'Time to create trip via agent')
```

---

### M4: Migration-Risiko – Neue Models ohne Rollback-Plan

**Befund:**  
`AgentConversation` und `AgentMessage` werden als neue Models hinzugefügt. Das ist forward-sicher (additive Migration), aber es gibt keinen Plan für:
- Was passiert wenn das Feature abgeschaltet wird?
- Data-Retention: Wie lange werden Conversations gespeichert?
- GDPR: Conversations enthalten personenbezogene Daten

**Empfehlung:**

```python
class AgentConversation(models.Model):
    # ... existing fields ...
    
    # Data Retention
    expires_at = models.DateTimeField(
        help_text="Auto-delete nach 90 Tagen",
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['expires_at']),  # Für Cleanup-Job
        ]
```

---

## Befund-Zusammenfassung

| ID | Schwere | Befund | Aufwand Fix |
|----|---------|--------|------------|
| K1 | 🔴 KRIT | Direkter `anthropic.Anthropic()` statt LLMClient/Handler | 1-2 Tage |
| K2 | 🔴 KRIT | Falsche Model-Feldnamen (location vs city, highlights) | 0.5 Tag |
| K3 | 🔴 KRIT | `trip_type` Semantik-Konflikt (Kategorie vs Party) | 0.5 Tag |
| K4 | 🔴 KRIT | `self._current_user` undefined | 0.5 Tag |
| K5 | 🔴 KRIT | Kein `transaction.atomic` bei Trip+Stops | 0.5 Tag |
| K6 | 🔴 KRIT | Tool-Use-Blocks nicht serialisierbar | 0.5 Tag |
| K7 | 🔴 KRIT | Keine Rate-Limiting / Abuse-Protection | 1 Tag |
| S1 | 🟠 SCHWER | Unkontrolliertes JSONField-Overwrite | 0.5 Tag |
| S2 | 🟠 SCHWER | Story-Settings fehlen im Flow | 1 Tag |
| S3 | 🟠 SCHWER | `highlights` existiert nicht auf Stop | 0.5 Tag |
| S4 | 🟠 SCHWER | CSRF Race-Condition / Doppel-Submit | 0.5 Tag |
| S5 | 🟠 SCHWER | Synchroner LLM-Call im Request-Cycle | 1 Tag (P2) |
| M1 | 🟡 MITTEL | Hardcodierter System-Prompt | 0.5 Tag |
| M2 | 🟡 MITTEL | Kein raw_response Storage | 0.5 Tag |
| M3 | 🟡 MITTEL | Kein Monitoring | 0.5 Tag |
| M4 | 🟡 MITTEL | Migration ohne Retention-Plan | 0.5 Tag |

**Geschätzter Mehraufwand für Production-Ready:** +5-7 Tage (auf die 12 Tage im ADR drauf)

---

## Korrigierter Implementierungsplan

| Phase | Aufgabe | Tage |
|-------|---------|------|
| **0. Spike** | Tool-Use via LLMClient testen, Feasibility | 1 |
| **1. Foundation** | Models (korrigierte Felder), Migrations, Indexes, Retention | 1.5 |
| **2. Handler** | `TripAgentHandler` nach BaseHandler-Pattern + LLMConfig | 2 |
| **3. Service** | `TripAgentService` mit atomic, rate-limit, progressive extraction | 2 |
| **4. Frontend** | HTMX Chat + Double-Submit-Protection + Loading-States | 2 |
| **5. Integration** | Trip/Stop-Erstellung → Redirect auf Wizard Step 3 | 1 |
| **6. Resilience** | Circuit Breaker, Monitoring, Fallback-to-Wizard | 1.5 |
| **7. Testing** | Unit (Schemas, Extraction), Integration (Full Conversation), Edge Cases | 2 |
| | **Gesamt** | **~13-14 Tage** |

---

## Review-Entscheidung

**🔴 ÜBERARBEITUNG ERFORDERLICH**

Die 7 kritischen Befunde müssen vor erneuter Review adressiert werden. Das Konzept ist strategisch richtig, aber der Code im aktuellen Zustand ist nicht merge-fähig. Insbesondere K1 (LLMClient-Integration) und K2/K3 (Model-Feldnamen) sind fundamentale Korrekturen die das gesamte Service-Design beeinflussen.

**Nächste Schritte:**

1. **Spike (1 Tag):** Tool-Use durch `LLMConfig`/`CreativeServicesClient` testen – funktioniert die Abstraktion mit Multi-Turn + Tools?
2. ADR überarbeiten mit korrigierten Model-Referenzen
3. Entscheidung: Agent ersetzt Steps 1+2, Wizard Steps 3+4 bleiben (Empfehlung S2-B)
4. Erneute Review nach Überarbeitung

---

*Review abgeschlossen: 2026-02-13*
