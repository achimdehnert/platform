# REVIEW: Spike Tool Use via LLMClient v2

**Reviewer:** Cascade (AI Architect Review)
**Datum:** 2026-02-13
**Spike:** `docs/adr/inputs/spike-tool-use-via-llmclient-v2.md`
**Projekt:** Travel Beat / DriftTales
**Verdict:** GO mit Korrekturen (3 Blocker, 2 Warnings, 1 Upgrade)

---

## Executive Summary

Der Spike ist **strategisch richtig** (bestehende Infrastruktur nutzen statt neu bauen),
aber die **taktischen Annahmen über den Code sind in 3 kritischen Punkten falsch**.
Zusätzlich wurde eine dritte, reifere LLM-Schicht komplett übersehen, die den
empfohlenen Lösungsweg fundamental ändert.

**Revidierter Aufwand:** 1-1.5 Tage (statt 0.5 Tage Spike-Schätzung)

---

## 0. Entdeckung: Drei LLM-Schichten in bfagent

Der Spike analysierte nur eine von drei existierenden LLM-Schichten:

| # | Schicht | Pfad | SDK? | Async? | Tool Use? | Caller |
|---|---------|------|------|--------|-----------|--------|
| L1 | **Core LLM Service** | `apps/core/services/llm/` | ✅ `anthropic.Anthropic` | ❌ Sync | ✅ Structured Output via tools | **60+** |
| L2 | **Prompt Framework** | `apps/core/services/prompt_framework/` | ❌ raw httpx | ✅ Async | ❌ | **~4** |
| L3 | **Travel-Beat Legacy** | `travel-beat/apps/ai_services/llm_client.py` | ❌ raw requests | ❌ Sync | ❌ | travel-beat |

**Der Spike analysierte nur L2** und beschrieb es fälschlich als `packages/bfagent-llm/`.
**L1 wurde komplett übersehen** — obwohl L1 bereits SDK-basiertes Tool Use implementiert hat.

### L1: Core LLM Service — Detail

```
apps/core/services/llm/
├── __init__.py          # Factory: get_client(), get_anthropic_client()
├── base.py              # BaseLLMClient ABC
├── models.py            # LLMRequest, LLMResponse, TokenUsage, LLMConfig
├── anthropic_client.py  # AnthropicClient (SDK + HTTP Fallback)
├── openai_client.py     # OpenAIClient
├── exceptions.py        # Typed Exceptions (Rate Limit, Auth, Timeout, etc.)
├── utils.py             # CostTracker, Token Estimation
└── tests/
```

**Schlüssel-Code in `AnthropicClient` (bereits implementiert):**

```python
# apps/core/services/llm/anthropic_client.py, Zeile 97-108
try:
    from anthropic import Anthropic
    self._client = Anthropic(api_key=self.config.api_key)
    self._use_sdk = True    # ← SDK bereits aktiv!
except ImportError:
    self._client = None
    self._use_sdk = False   # ← HTTP-Fallback
```

**Bereits vorhandenes Tool Use (für Structured Output):**

```python
# apps/core/services/llm/anthropic_client.py, Zeile 184-201
def _generate_structured_sdk(self, request, kwargs, start_time):
    tool = {
        "name": "generate_response",
        "description": f"Generate {schema.__name__}",
        "input_schema": schema.model_json_schema(),
    }
    kwargs["tools"] = [tool]
    kwargs["tool_choice"] = {"type": "tool", "name": "generate_response"}
    response = self._client.messages.create(**kwargs)
    # ... extracts tool_use block from response.content
```

**Bewertung:** L1 hat bereits SDK + Tool Use + `finish_reason` + typed Exceptions.
Der Spike hätte L1 als Basis wählen sollen statt L2.

---

## BLOCKER 1: Package `bfagent-llm` existiert nicht

**Befund:** Der Spike referenziert durchgehend `packages/bfagent-llm/src/bfagent_llm/`
(§1.1, §3, §4, §5) und Imports wie `from bfagent_llm import AnthropicLLMAdapter`.

**Tatsächlich:**

| Spike-Referenz | Tatsächlicher Pfad |
|----------------|-------------------|
| `packages/bfagent-llm/adapters.py` | `apps/core/services/prompt_framework/adapters.py` |
| `packages/bfagent-llm/service.py` | `apps/core/services/prompt_framework/service.py` |
| `from bfagent_llm import ...` | `from apps.core.services.prompt_framework import ...` |

Das `packages/`-Verzeichnis enthält nur leere MCP-Stubs (bfagent_mcp, deployment_mcp, etc.).

**Risiko:** KRITISCH — Alle Imports, pip-install-Empfehlungen (§8 E1) und
Architekturdiagramme (§4) basieren auf nicht-existentem Package.

**Empfehlung:** Alle Referenzen korrigieren. Dependency-Strategie (§8 E1) komplett
überarbeiten — `pip install bfagent-llm @ git+...` funktioniert nicht.

---

## BLOCKER 2: `**kwargs` werden NICHT an die API weitergeleitet

**Befund:** Der Spike behauptet `tools` und `tool_choice` passieren via `**kwargs` durch.

**Tatsächlicher Code** (`prompt_framework/adapters.py`, Zeile 340-358):

```python
payload = {
    "model": model,
    "messages": filtered_messages,
    "max_tokens": max_tokens,
    "temperature": temperature,
}
if system_prompt:
    payload["system"] = system_prompt

# ← KEIN **kwargs in payload! tools/tool_choice werden IGNORIERT
async with httpx.AsyncClient(timeout=self.timeout) as client:
    response = await client.post(
        f"{self.base_url}/messages", headers=headers, json=payload,
    )
```

`**kwargs` wird im Funktions-Signature akzeptiert aber **nirgendwo** in den
Payload oder API-Call eingespeist.

**Risiko:** KRITISCH — Die Kernprämisse des Spikes ("80% existiert schon") ist falsch.

---

## BLOCKER 3: Adapter nutzt raw httpx, nicht Anthropic SDK

**Befund:** Der Spike zeigt SDK-Objekte (`response.content[0].text`,
`response.model_dump()`, `block.type`, `block.id`). Der tatsächliche Code
nutzt `httpx.AsyncClient` mit manuellem JSON-Parsing. Der Response ist ein
`dict`, kein Pydantic-Model.

**Aber:** Das `anthropic` SDK ist bereits im bfagent venv installiert (verifiziert via
`pip show`). L1 (`AnthropicClient`) nutzt es bereits produktiv.

---

## WARNING 1: `ResilientPromptService` leitet keine `**kwargs` weiter

`_execute_with_retry()` ruft `self.llm_client.complete()` ohne `**kwargs` auf
(Zeile 461-469). Wenn der Agent Resilience (Retry, Circuit Breaker) nutzen soll,
muss dies erweitert werden.

---

## WARNING 2: Travel-Beat Anthropic System-Prompt-Bug bestätigt

`llm_client.py` Zeile 450-461: System-Prompt wird in User-Content gepackt statt
als separates `system` Feld. Spike-Empfehlung "jetzt nicht anfassen" ist korrekt,
sollte aber als Bug-Ticket getrackt werden.

---

## SDK-Migration: Tiefenanalyse (Weg B)

### Ist-Zustand: Wer nutzt `raw_response`?

| Caller | Zugriff auf `raw_response` | Typ |
|--------|---------------------------|-----|
| `prompt_framework/adapters.py` (4x) | Setzt es als `data` (JSON dict) | LLMResponse.raw_response |
| `services/llm/anthropic_client.py` SDK | Setzt `{"id": response.id}` (minimal) | LLMResponse.raw_response |
| `services/llm/anthropic_client.py` HTTP | Setzt `data` (full JSON dict) | LLMResponse.raw_response |
| `writing_hub/handlers/*.py` | Nutzt als String (eigene Variable, NICHT LLMResponse-Feld) | str |
| `chapter_generate_handler.py` | Nutzt als LLM-Text-String | str |
| `task_extraction.py` | Nutzt als String | str |
| `style_lab_service.py` | Nutzt als String | str |

**Ergebnis:** `LLMResponse.raw_response` wird von **keinem Caller** als dict
gelesen oder geparst. Die meisten "raw_response"-Zugriffe im Code sind eigene
String-Variablen, nicht das LLMResponse-Feld.

### Breaking-Change-Risiko bei SDK-Migration

| Szenario | Risiko | Begründung |
|----------|--------|------------|
| L2 Adapter → SDK | **MINIMAL** | Nur ~4 Caller, keiner liest `raw_response` |
| L1 AnthropicClient SDK | **KEIN** | Nutzt SDK bereits, `raw_response={"id": response.id}` |
| `model_dump()` statt JSON dict | **MINIMAL** | Gleiche Struktur, kein Caller parst es |

### Empfehlung: Nicht L2 migrieren — L1 erweitern

**Statt** den L2 Prompt-Framework-Adapter auf SDK zu migrieren, sollte der
Trip Agent **L1 (`AnthropicClient`) direkt nutzen** und um Async erweitern:

| Aspekt | L2 migrieren (Spike-Vorschlag) | L1 erweitern (Empfehlung) |
|--------|-------------------------------|---------------------------|
| SDK | Neu einbauen | Bereits vorhanden |
| Tool Use | Neu einbauen | Pattern existiert (`_generate_structured_sdk`) |
| Async | Vorhanden | **NEU: `AsyncAnthropic` hinzufügen** |
| Caller-Basis | ~4 Caller | 60+ Caller profitieren |
| Typed Exceptions | Fehlt in L2 | Bereits vorhanden |
| Cost Tracking | Via ResilientPromptService | Via CostTracker (utils.py) |
| Resilience | ResilientPromptService | **NEU: Optional Retry-Decorator** |

### Konkreter Vorschlag: L1 Async-Erweiterung

```python
# apps/core/services/llm/anthropic_client.py — Erweiterung

class AnthropicClient(BaseLLMClient):
    # ... bestehender Code ...

    def _init_async_client(self) -> None:
        """Initialize async Anthropic client (lazy)."""
        if not hasattr(self, '_async_client'):
            from anthropic import AsyncAnthropic
            self._async_client = AsyncAnthropic(api_key=self.config.api_key)

    async def async_generate(
        self,
        prompt: str,
        system_prompt: str = None,
        tools: list = None,
        tool_choice: dict = None,
        **kwargs,
    ) -> LLMResponse:
        """Async generation with optional tool use."""
        self._init_async_client()
        start_time = time.perf_counter()

        messages = []
        if system_prompt:
            # System prompt handled separately by Anthropic
            pass
        messages.append({"role": "user", "content": prompt})

        api_kwargs = {
            "model": self.config.effective_model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.default_max_tokens),
        }
        if system_prompt:
            api_kwargs["system"] = system_prompt
        if kwargs.get("temperature") is not None:
            api_kwargs["temperature"] = kwargs["temperature"]
        if tools:
            api_kwargs["tools"] = tools
        if tool_choice:
            api_kwargs["tool_choice"] = tool_choice

        response = await self._async_client.messages.create(**api_kwargs)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract content blocks
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        usage = TokenUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )

        result = LLMResponse.success_response(
            content="\n".join(text_parts),
            usage=usage,
            model=response.model,
            finish_reason=response.stop_reason,
            latency_ms=latency_ms,
            raw_response=response.model_dump(),
        )
        # Attach tool_calls and content_blocks for agent loop
        result.tool_calls = tool_calls
        result.content_blocks = [b.model_dump() for b in response.content]
        return result

    async def async_complete(
        self,
        messages: list,
        tools: list = None,
        tool_choice: dict = None,
        **kwargs,
    ) -> LLMResponse:
        """Async completion with full message array (for multi-turn agent)."""
        self._init_async_client()
        start_time = time.perf_counter()

        # Extract system from messages
        system_prompt = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                chat_messages.append(msg)

        api_kwargs = {
            "model": kwargs.get("model", self.config.effective_model),
            "messages": chat_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.default_max_tokens),
        }
        if system_prompt:
            api_kwargs["system"] = system_prompt
        if kwargs.get("temperature") is not None:
            api_kwargs["temperature"] = kwargs["temperature"]
        if tools:
            api_kwargs["tools"] = tools
        if tool_choice:
            api_kwargs["tool_choice"] = tool_choice

        response = await self._async_client.messages.create(**api_kwargs)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        usage = TokenUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )

        result = LLMResponse.success_response(
            content="\n".join(text_parts),
            usage=usage,
            model=response.model,
            finish_reason=response.stop_reason,
            latency_ms=latency_ms,
            raw_response=response.model_dump(),
        )
        result.tool_calls = tool_calls
        result.content_blocks = [b.model_dump() for b in response.content]
        return result
```

**LLMResponse-Erweiterung** (backward-compatible):

```python
# apps/core/services/llm/models.py — 3 optionale Felder ergänzen

@dataclass
class LLMResponse:
    success: bool
    content: Optional[str] = None
    structured_output: Optional[Any] = None
    usage: Optional[TokenUsage] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    latency_ms: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # --- NEU (optional, backward-compatible) ---
    tool_calls: Optional[List[Dict[str, Any]]] = None
    content_blocks: Optional[List[Dict[str, Any]]] = None

    @property
    def has_tool_calls(self) -> bool:
        return self.finish_reason == "tool_use" and bool(self.tool_calls)
```

---

## Revidierte Gap-Analyse (basierend auf L1)

| # | Gap | Aufwand | Begründung |
|---|-----|---------|------------|
| G1 | `async_complete()` Methode auf `AnthropicClient` | ~40 Zeilen | SDK vorhanden, Pattern von `_generate_sdk` kopierbar |
| G2 | `LLMResponse` + 2 optionale Felder (`tool_calls`, `content_blocks`) | ~5 Zeilen | Backward-compatible |
| G3 | `has_tool_calls` Property | ~3 Zeilen | Convenience |
| G4 | Agent-Handler in travel-beat | ~60 Zeilen | `ConversationalTripAgent` nutzt `async_complete()` |

**Total: ~110 Zeilen neuer Code, 0 Breaking Changes, 0 neue Dependencies.**

---

## Revidierter PoC (Phase 1)

```python
# spike/test_l1_tool_use.py
"""
PoC: Tool Use via AnthropicClient (Layer 1).
Verifiziert async_complete() mit tools/tool_choice.
"""
import asyncio
import os
import sys

# Django Setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django; django.setup()

from apps.core.services.llm import get_anthropic_client

TOOLS = [
    {
        "name": "create_trip",
        "description": "Erstellt einen Trip.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "trip_type": {"type": "string",
                    "enum": ["city","beach","adventure"]},
            },
            "required": ["destination"],
        },
    },
]

async def main():
    client = get_anthropic_client()

    response = await client.async_complete(
        messages=[
            {"role": "system", "content": "Du bist ein Reise-Assistent."},
            {"role": "user", "content": "Ich will nach Rom im Juli."},
        ],
        tools=TOOLS,
        tool_choice={"type": "auto"},
    )

    print(f"success: {response.success}")
    print(f"finish_reason: {response.finish_reason}")
    print(f"has_tool_calls: {response.has_tool_calls}")
    print(f"tool_calls: {response.tool_calls}")
    print(f"content: {response.content[:200] if response.content else 'None'}")
    print(f"tokens: {response.usage.total_tokens if response.usage else 'N/A'}")

asyncio.run(main())
```

**Akzeptanzkriterien (revidiert):**

| # | Kriterium | Methode |
|---|-----------|---------|
| A1 | `async_complete()` mit `tools=` funktioniert | PoC |
| A2 | `response.tool_calls` enthält extrahierte Calls | Assert |
| A3 | `response.content_blocks` sind JSON-serialisierbar | `json.dumps()` |
| A4 | Bestehende sync-Caller unverändert funktional | Regression via pytest |
| A5 | `response.has_tool_calls` korrekt bei `stop_reason == "tool_use"` | Unit-Test |
| A6 | Multi-Turn Conversation (content_blocks als Assistant-Message) | PoC Round 2 |

---

## Dependency-Strategie für Travel Beat

Da `packages/bfagent-llm/` nicht existiert, muss Travel Beat anders an den
LLM-Client kommen:

| Option | Bewertung |
|--------|-----------|
| A: bfagent als pip-Dependency | ❌ bfagent ist kein Package, ist eine Django-App |
| B: Code nach travel-beat kopieren (Vendor) | ⚠️ Funktioniert, aber Drift-Risiko |
| C: `apps/core/services/llm/` als eigenes Package extrahieren | ✅ **Empfohlen** — `platform-llm` o.ä. |
| D: Shared Git Subtree | ⚠️ Komplex, fehleranfällig |
| E: Direkt `anthropic` SDK in travel-beat | ✅ **Pragmatisch** — kein bfagent-Code nötig |

**Empfehlung:** **Option E** für den Spike, **Option C** mittelfristig.

Für den Trip Agent braucht travel-beat nur:
1. `anthropic` (pip install)
2. ~40 Zeilen async Wrapper (lokal in `apps/trips/agent/llm.py`)
3. Kein Import aus bfagent nötig

Die Patterns aus L1 dienen als Referenz, der Agent-Handler nutzt das
Anthropic SDK direkt — was architektonisch sauber ist, da der Agent
framework-spezifische Features (multi-turn, tool_use loop) braucht die
ein generischer Client nicht bieten sollte.

---

## Zusammenfassung: Korrigierte Entscheidungsmatrix

| Entscheidung | Spike v2 | Korrigiert |
|--------------|----------|------------|
| Basis-Package | `packages/bfagent-llm/` (existiert nicht) | `apps/core/services/llm/` (L1) als Referenz |
| SDK | "existiert in Adapter" (falsch) | Existiert in L1 AnthropicClient |
| kwargs-Forwarding | "funktioniert" (falsch) | Muss gebaut werden (in L1 oder direkt) |
| Aufwand | 0.5 Tage | 1-1.5 Tage |
| Breaking Changes | "keine" | Tatsächlich keine (verifiziert) |
| Dependency travel-beat → bfagent | pip install bfagent-llm | anthropic SDK direkt + lokaler Wrapper |

---

## Changelog

| Datum | Änderung |
|-------|---------|
| 2026-02-13 | Initial Review: 3 Blocker, 2 Warnings |
| 2026-02-13 | SDK-Tiefenanalyse: L1 Entdeckung, raw_response Breaking-Change = MINIMAL, PoC korrigiert |
