# SPIKE: Tool Use via LLMClient — REVIDIERT

**Projekt:** Travel Beat / DriftTales  
**Datum:** 2026-02-13  
**Status:** Revidierte Analyse nach Entdeckung von `bfagent-llm` + `creative-services`  
**Dauer:** 0,5 Tage (4h) — deutlich reduziert gegenüber v1

---

## 0. Revision: Was hat sich geändert?

Mein erster Spike-Plan basierte **nur** auf dem Travel-Beat-Repo (`apps/ai_services/llm_client.py`). Die nachträgliche Analyse der zwei zusätzlichen Repos zeigt, dass **80% der benötigten Infrastruktur bereits existiert**:

| Komponente | Spike v1: "Fehlt, muss gebaut werden" | Tatsächlich: bereits vorhanden |
|---|---|---|
| Async LLM Client | ❌ `generate_text()` ist synchron | ✅ `AnthropicLLMAdapter` mit `AsyncAnthropic` |
| System-Prompt Handling | ❌ Bug G4 — System in User gepackt | ✅ Adapter trennt System korrekt |
| `**kwargs` Passthrough | ❌ `LlmRequest` hat keine `tools`-Felder | ✅ `complete(**kwargs)` leitet alles durch |
| Fallback-Chain | ❌ Müsste gebaut werden | ✅ `FallbackLLMAdapter` (Gateway → OpenAI → Anthropic) |
| Circuit Breaker | ❌ Müsste gebaut werden | ✅ `ResilientPromptService` mit per-Tier Breakers |
| Retry + Backoff | ❌ Müsste gebaut werden | ✅ `ResilientPromptService.DEFAULT_MAX_RETRIES=3` |
| Tier-Fallback | ❌ Müsste gebaut werden | ✅ `TierConfig` mit `fallback_tier` Chain |
| Protocol / Interface | ❌ Müsste definiert werden | ✅ `LLMClientProtocol` mit `complete()` |
| Cost-Tracking Basis | ❌ Müsste gebaut werden | ✅ `LLMResponse.tokens_in/out` + `raw_response` |
| Template Engine | ❌ Nicht betrachtet | ✅ `SecureTemplateEngine` (Jinja2 sandboxed) |

### Bewertung meiner ursprünglichen Optionen

| Option | Spike v1 Bewertung | Revidierte Bewertung |
|---|---|---|
| **A: `generate_text()` erweitern** | "Evolutionär, 4h" | ⚠️ **Falsche Schicht** — `generate_text()` ist ein Legacy-Wrapper mit sync `requests`. Das richtige Interface ist `bfagent-llm` |
| **B: `generate_with_tools()` parallel** | "Empfohlen, 6h" | ⚠️ **Redundant** — baut Infrastruktur nach, die in `bfagent-llm` schon existiert |
| **C: SDK direkt im Handler** | "Pragmatisch aber Schulden" | ⚠️ **Unnötig** — `AnthropicLLMAdapter` nutzt das SDK bereits korrekt |
| **D: `bfagent-llm` Adapter nutzen** | *(nicht betrachtet)* | ✅ **Richtige Lösung** — Details unten |

---

## 1. Ist-Zustand: Was existiert bereits

### 1.1 `bfagent-llm` Package (`packages/bfagent-llm/`)

```
packages/bfagent-llm/
├── src/bfagent_llm/
│   ├── __init__.py          # Exports: LLMClientProtocol, LLMResponse, Adapters
│   ├── adapters.py          # Gateway, OpenAI, Anthropic, Fallback Adapters
│   ├── service.py           # ResilientPromptService, CircuitBreaker, TierConfig
│   ├── engine.py            # SecureTemplateEngine (Jinja2 sandboxed)
│   └── facade.py            # PromptFramework Singleton
├── tests/
│   ├── test_service.py      # CircuitBreaker, Retry, Tier-Fallback Tests
│   └── ...
└── README.md
```

**Kern-Interface:**

```python
class LLMClientProtocol(Protocol):
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        **kwargs,              # ← SCHLÜSSEL: tools/tool_choice passen hier durch!
    ) -> LLMResponse: ...
```

**AnthropicLLMAdapter — der entscheidende Code:**

```python
class AnthropicLLMAdapter(LLMClientProtocol):
    async def complete(self, messages, model, max_tokens, temperature, **kwargs):
        client = self._get_client()  # AsyncAnthropic
        
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        chat_messages = [m for m in messages if m["role"] in ("user", "assistant")]
        
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=chat_messages,
            **kwargs,              # ← tools= und tool_choice= gehen hier durch!
        )
        
        # ⚠️ EINZIGER GAP: Nur content[0].text extrahiert
        content = response.content[0].text if response.content else ""
        
        return LLMResponse(
            content=content,       # ← Tool-Use Blocks gehen verloren
            model=response.model,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            raw_response=response.model_dump(),  # ← ABER: Alles im raw_response!
        )
```

### 1.2 `creative-services` Package (`packages/creative-services/`)

```python
# creative_services/core/llm_client.py
async def _generate_anthropic(self, prompt, system_prompt, **kwargs):
    payload = {
        "model": self.config.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": ...,
        "temperature": ...,
    }
    if system_prompt:
        payload["system"] = system_prompt      # ✅ Korrekt getrennt
    
    response = await self._client.post(url, headers=headers, json=payload)
```

### 1.3 `llm_mcp` Server (`llm_mcp/`)

```python
# llm_mcp/providers/anthropic_provider.py
async def call_anthropic(llm, messages, temperature, max_tokens):
    client = AsyncAnthropic(api_key=api_key)
    kwargs = {
        "model": llm["llm_name"],
        "messages": user_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system:
        kwargs["system"] = system             # ✅ Korrekt getrennt
    response = await client.messages.create(**kwargs)
```

---

## 2. Tatsächliche Gaps (nur 3 statt 9)

| # | Gap | Wo | Aufwand |
|---|-----|-----|---------|
| G1 | `AnthropicLLMAdapter` parst nur `content[0].text` — `tool_use` Blocks gehen verloren | `bfagent-llm/adapters.py` | **Klein** (15 Zeilen) |
| G2 | `LLMResponse` hat kein Feld für `stop_reason` oder `tool_calls` | `bfagent-llm/service.py` | **Klein** (extend oder subclass) |
| G3 | `ResilientPromptService.execute()` kennt kein Tool-Use-Loop-Pattern | `bfagent-llm/service.py` | **Nicht nötig** — Loop gehört in den Agent-Handler, nicht in den Service |

### Gaps die NICHT mehr existieren (waren in Spike v1):

| v1-Gap | Status | Grund |
|--------|--------|-------|
| G3: `prompt` ist `str` — kein `messages`-Array | ✅ Gelöst | `complete(messages=...)` |
| G4: System-Prompt in User gepackt | ✅ Gelöst | Adapter trennt korrekt |
| G7: BaseLLMHandler ist Single-Turn only | ✅ Gelöst | `complete()` nimmt volles `messages` Array |
| G9: OpenAI analog erweitern | ✅ Gelöst | `OpenAILLMAdapter` hat auch `**kwargs` |

---

## 3. Lösung: Option D — `bfagent-llm` erweitern (minimal)

### 3.1 Fix G1+G2: Response-Parsing erweitern

```python
# Änderung in packages/bfagent-llm/src/bfagent_llm/adapters.py
# AnthropicLLMAdapter.complete() — NUR die Response-Verarbeitung:

async def complete(self, messages, model, max_tokens, temperature, **kwargs):
    client = self._get_client()
    
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    chat_messages = [m for m in messages if m["role"] in ("user", "assistant")]
    
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=chat_messages,
        **kwargs,
    )
    
    # --- NEU: Alle Content-Blocks verarbeiten ---
    text_parts = []
    tool_calls = []
    
    for block in (response.content or []):
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append({
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    
    return LLMResponse(
        content="\n".join(text_parts),
        model=response.model,
        tokens_in=response.usage.input_tokens if response.usage else 0,
        tokens_out=response.usage.output_tokens if response.usage else 0,
        raw_response=response.model_dump(),
        # NEU:
        stop_reason=response.stop_reason,    # "end_turn" | "tool_use"
        tool_calls=tool_calls,               # Extrahierte Tool-Calls
        content_blocks=[b.model_dump() for b in (response.content or [])],
    )
```

### 3.2 Fix G2: `LLMResponse` erweitern

```python
# Änderung in packages/bfagent-llm/src/bfagent_llm/service.py

@dataclass
class LLMResponse:
    """Response from LLM call."""
    content: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    cost: Decimal = field(default_factory=lambda: Decimal("0"))
    raw_response: Optional[Dict[str, Any]] = None
    # --- NEU (optional, backward-compatible) ---
    stop_reason: Optional[str] = None              # "end_turn" | "tool_use" | "max_tokens"
    tool_calls: Optional[List[Dict[str, Any]]] = None     # Extrahierte Tool-Use Blocks
    content_blocks: Optional[List[Dict[str, Any]]] = None  # Alle raw content blocks
    
    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out
    
    @property
    def has_tool_calls(self) -> bool:
        return self.stop_reason == "tool_use" and bool(self.tool_calls)
```

**Backward-Kompatibilität:** Alle neuen Felder sind `Optional` mit `None` Default. Bestehende Caller (Story-Gen, Enrichment, etc.) sind nicht betroffen.

### 3.3 Agent-Handler in Travel Beat

```python
# apps/trips/agent/handler.py

from bfagent_llm import AnthropicLLMAdapter, LLMResponse

class ConversationalTripAgent:
    """
    Trip-Erstellung via natürliche Konversation.
    Nutzt bfagent-llm AnthropicLLMAdapter mit Tool Use.
    """
    
    MAX_TURNS = 20
    TOOLS = [...]  # create_trip, add_stop, add_transport, finalize_trip
    
    def __init__(self, user):
        self.user = user
        self.messages: list[dict] = []
        self.adapter = AnthropicLLMAdapter()  # Nutzt ANTHROPIC_API_KEY aus env
        self.trip = None
    
    async def process_message(self, user_input: str) -> dict:
        self.messages.append({"role": "user", "content": user_input})
        
        for _ in range(self.MAX_TURNS):
            response: LLMResponse = await self.adapter.complete(
                messages=[{"role": "system", "content": self._system_prompt()}]
                         + self.messages,
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0.6,
                tools=self.TOOLS,            # ← Durch **kwargs
                tool_choice={"type": "auto"},  # ← Durch **kwargs
            )
            
            # Assistant-Response in History (content_blocks sind serialisierbar)
            self.messages.append({
                "role": "assistant",
                "content": response.content_blocks,
            })
            
            if not response.has_tool_calls:
                return {"text": response.content, "done": False}
            
            # Tool Calls ausführen
            tool_results = []
            for tc in response.tool_calls:
                result = self._execute_tool(tc)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": result,
                })
            
            self.messages.append({"role": "user", "content": tool_results})
        
        return {"text": "Maximale Gesprächslänge erreicht.", "done": True}
```

---

## 4. Architektur-Vergleich: v1 vs. v2

### Spike v1 (überholt)

```
Travel Beat
├── apps/ai_services/llm_client.py    ← generate_text() (sync, requests)
│   ├── generate_with_tools()         ← NEU GEBAUT (redundant!)
│   └── ToolUseLlmRequest             ← NEU GEBAUT (redundant!)
├── apps/ai_services/tool_use.py      ← NEU GEBAUT (redundant!)
│   ├── ToolCall
│   └── ToolUseResponse
└── apps/trips/agent/handler.py
    └── ConversationalTripAgent
```

**Problem:** Baut Infrastruktur nach, die in `bfagent-llm` bereits existiert und getestet ist.

### Spike v2 (empfohlen)

```
packages/bfagent-llm/                  ← BESTEHENDES Package
├── adapters.py                        ← 15 Zeilen Response-Parsing erweitern
├── service.py                         ← 3 optionale Felder an LLMResponse
└── (rest unverändert)

Travel Beat
├── apps/ai_services/llm_client.py     ← UNVERÄNDERT (Legacy für Story-Gen)
└── apps/trips/agent/handler.py        ← NEU: nutzt bfagent-llm Adapter
    └── ConversationalTripAgent
```

**Vorteil:** Nutzt getestete Infrastruktur, minimale Änderungen, kein Parallel-Code.

---

## 5. Revidierter Spike-Plan (0,5 Tage)

### Phase 1: PoC mit bestehendem Adapter (1h)

```python
# spike/test_adapter_tool_use.py
"""
PoC: Tool Use via bestehendem AnthropicLLMAdapter.
Testet ob **kwargs korrekt durchgereicht werden.
"""
import asyncio
from bfagent_llm import AnthropicLLMAdapter

TOOLS = [
    {
        "name": "create_trip",
        "description": "Erstellt einen Trip.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "trip_type": {"type": "string",
                    "enum": ["city","beach","wellness","backpacking",
                             "business","family","adventure","cruise"]},
            },
            "required": ["destination"],
        },
    },
]

async def main():
    adapter = AnthropicLLMAdapter()
    
    # Test 1: Tool Use via **kwargs
    response = await adapter.complete(
        messages=[
            {"role": "system", "content": "Du bist ein Reise-Assistent."},
            {"role": "user", "content": "Ich will nach Rom im Juli."},
        ],
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        temperature=0.6,
        tools=TOOLS,
        tool_choice={"type": "auto"},
    )
    
    print(f"content: {response.content}")
    print(f"raw stop_reason: {response.raw_response.get('stop_reason')}")
    print(f"raw content blocks: {len(response.raw_response.get('content', []))}")
    
    # Prüfe ob tool_use im raw_response ist
    for block in response.raw_response.get("content", []):
        if block.get("type") == "tool_use":
            print(f"✅ TOOL CALL: {block['name']}({block['input']})")

asyncio.run(main())
```

**Zu beantwortende Fragen:**
- [x] `**kwargs` leitet `tools`/`tool_choice` korrekt durch? → Ja (SDK-Signatur bestätigt)
- [ ] `raw_response.model_dump()` enthält tool_use Blocks? → PoC verifiziert
- [ ] `stop_reason` ist im `raw_response` verfügbar? → PoC verifiziert
- [ ] `content_blocks` sind JSON-serialisierbar für Session? → PoC verifiziert

### Phase 2: LLMResponse erweitern + Adapter-Fix (1.5h)

1. `LLMResponse` um 3 optionale Felder erweitern (backward-compatible)
2. `AnthropicLLMAdapter.complete()` Response-Parsing anpassen (~15 Zeilen)
3. Unit-Tests für neue Felder

### Phase 3: Agent-Handler Sketch (1h)

Minimaler `ConversationalTripAgent` der den erweiterten Adapter nutzt:
- Tool-Definitionen für create_trip, add_stop, add_transport, finalize_trip
- Conversation-Loop mit MAX_TURNS
- Tool-Dispatch zu `trip_services`

### Phase 4: Dokumentation (0.5h)

- Spike-Ergebnis GO/NO-GO
- Änderungen an `bfagent-llm` dokumentieren
- Abhängigkeit Travel Beat → `bfagent-llm` klären

---

## 6. Revidierte Akzeptanzkriterien

| # | Kriterium | Methode |
|---|-----------|---------|
| A1 | `AnthropicLLMAdapter.complete()` mit `tools=` Param funktioniert | Phase 1 PoC |
| A2 | `LLMResponse.tool_calls` enthält extrahierte Tool-Calls | Unit-Test |
| A3 | `LLMResponse.content_blocks` sind JSON-serialisierbar | Assert `json.dumps()` |
| A4 | Bestehende Caller ohne `tools=` Param funktionieren weiterhin | Regression-Test |
| A5 | Tool-Result-Roundtrip komplett via Adapter | Phase 1 PoC |

---

## 7. Auswirkung auf Gesamttimeline

### Spike v1 Timeline (überholt)
```
Spike (1 Tag) → ADR (1 Tag) → Implementation (11 Tage) = 13 Tage
```

### Spike v2 Timeline (revidiert)
```
Spike (0.5 Tage) → ADR (0.5 Tage) → Implementation (7 Tage) = 8 Tage
```

**Einsparung: 5 Tage** weil:
- `generate_with_tools()` entfällt (Adapter existiert)
- `ToolUseLlmRequest` / `ToolUseResponse` entfällt (LLMResponse erweitern)
- Circuit Breaker / Retry / Fallback entfällt (ResilientPromptService)
- System-Prompt-Bug-Fix entfällt (Adapter trennt korrekt)

### Revidierte Implementation nach GO

```
Spike GO ──► ADR-027: Conversational Trip Agent (v2)
         ├── Phase 1: bfagent-llm Response-Erweiterung (0.5 Tage)
         ├── Phase 2: ConversationalTripAgent Handler (2 Tage)
         ├── Phase 3: Django View + HTMX Chat-UI (2 Tage)
         ├── Phase 4: Session-Persistierung + Rate-Limiting (1.5 Tage)
         └── Phase 5: Integration-Tests + Wizard-Koexistenz (1 Tag)
                                                    Total: ~7 Tage
```

---

## 8. Offene Entscheidungen

### E1: `bfagent-llm` als pip-Dependency in Travel Beat?

**Option A:** `pip install "bfagent-llm @ git+https://github.com/achimdehnert/platform.git#subdirectory=packages/bfagent-llm"`  
**Option B:** Code in `apps/ai_services/` kopieren (Vendor)  
**Option C:** Shared Python package im Docker-Build

→ **Empfehlung: Option A** — Package ist bereits als pip-installierbar konzipiert.

### E2: Legacy `generate_text()` in Travel Beat mittelfristig migrieren?

Der bestehende `apps/ai_services/llm_client.py` hat den System-Prompt-Bug (G4 aus v1) und ist synchron. Für Story-Generation, Enrichment, Review funktioniert er. Mittelfristig sollte Travel Beat komplett auf `bfagent-llm` Adapter migrieren.

→ **Empfehlung:** Jetzt nicht anfassen. Agent nutzt `bfagent-llm`, Legacy bleibt für bestehende Features. Migration als separates Ticket.

### E3: OpenAI Tool Use (function_call) Support?

`OpenAILLMAdapter` hat ebenfalls `**kwargs` Passthrough. OpenAI's `tools`-Parameter ist fast identisch mit Anthropic's. Könnte mit minimalem Aufwand analog erweitert werden.

→ **Empfehlung:** Im Spike nicht betrachten. Nach GO als Enhancement wenn OpenAI-Fallback gewünscht.

---

## 9. Selbstkritik: Was ich im ersten Spike falsch eingeschätzt habe

| Fehler | Ursache | Lesson Learned |
|--------|---------|----------------|
| 9 Gaps identifiziert, nur 3 sind real | Analyse nur auf Travel-Beat-Repo beschränkt | **Immer das gesamte Ökosystem betrachten** |
| `generate_with_tools()` als neue Funktion empfohlen | Bestehende `bfagent-llm` Adapter nicht bekannt | **Vor dem Bauen: existierende Packages prüfen** |
| 1 Tag Spike-Dauer geschätzt | Infrastruktur-Aufbau einkalkuliert, der nicht nötig ist | **Bestehende Investitionen nutzen** |
| Option C (SDK direkt) als "architektonische Schulden" bewertet | Nicht gesehen, dass SDK-Nutzung via Adapter bereits Pattern ist | **SDK-Nutzung in Adaptern ist das richtige Pattern** |
| System-Prompt-Bug als eigenen Fix eingeplant | Bug existiert nur in `llm_client.py`, nicht in `bfagent-llm` | **Adapter-Schicht löst das Problem bereits** |
