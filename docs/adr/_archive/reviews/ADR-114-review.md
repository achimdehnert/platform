# ADR-114 Review: Discord als IDE-ähnliches Kommunikations-Gateway

**Review-Datum:** 2026-03-08  
**Reviewer:** Principal IT-Architekt  
**Status:** REVIEW COMPLETE — 4 BLOCKER, 3 KRITISCH, 5 HOCH, 6 MEDIUM

---

## 1. Review-Tabelle

### BLOCKER

| # | Befund | Severity | Datei / Stelle |
|---|--------|----------|----------------|
| B1 | **Kein Auth-Modell für destruktive Commands** — `/deploy`, `/approve`, `/reject` sind ohne Discord-Rollenprüfung implementiert. Jeder Server-Member kann Production deployen. | BLOCKER | `handlers.py` — alle cmd_* Funktionen |
| B2 | **`asyncio.run()` in ASGI-Kontext verboten** — Discord.py ist ein asyncio-Event-Loop. Wenn `llm_mcp`-Aufrufe via `asyncio.run()` gemacht werden, deadlockt der Bot. Muss `await httpx.AsyncClient` sein. | BLOCKER | Layer 2 `/chat` Handler |
| B3 | **Kein Rate-Limiting auf Discord-Commands** — Ein User kann `/chat` in Endlosschleife feuern → GPT-4o Token-Kosten unbegrenzt, DoS der `llm_mcp` Instanz. | BLOCKER | Fehlt komplett im ADR |
| B4 | **Discord Message Limit ignoriert** — Discord hat 2000 Zeichen Limit pro Nachricht. LLM-Antworten sind regelmäßig länger. Kein Truncate/Embed/Pagination-Konzept im ADR. | BLOCKER | Layer 2 Response-Handling |

### KRITISCH

| # | Befund | Severity | Datei / Stelle |
|---|--------|----------|----------------|
| K1 | **Secrets im System-Prompt** — ADR schlägt vor, ADR-Dateien + pgvector-Inhalte direkt in den System-Prompt zu laden. Wenn ADRs Credentials, API-Keys oder IP-Adressen enthalten (was sie oft tun), landen diese im GPT-4o Kontext und im Discord-Channel. | KRITISCH | Layer 2 System-Prompt-Bauweise |
| K2 | **`llm_mcp` ohne Idempotenz/Retry** — `/chat` Endpoint hat kein Request-Deduplication. Network-Fehler → User tippt nochmal → doppelte GitHub Issues, doppelte Deployments. | KRITISCH | Layer 2 + Layer 3 |
| K3 | **Cascade-Inbox Repo als Single Point of Failure** — Layer 3 funktioniert nur wenn Cascade IDE offen und die Session aktiv ist. Kein Timeout, kein Fallback, keine User-Benachrichtigung wenn Issue 24h unbeantwortet. | KRITISCH | Layer 3 Architektur |

### HOCH

| # | Befund | Severity | Datei / Stelle |
|---|--------|----------|----------------|
| H1 | **Kein Logging/Audit-Trail für LLM-Anfragen** — Wer hat `/chat` mit welchem Prompt aufgerufen? Kein Tracing, kein Correlation-ID. | HOCH | Layer 2 |
| H2 | **Context-Window Management fehlt** — "neueste ADRs + relevante Memories" ist kein Algorithmus. Wie viele ADRs? Token-Budget? Priorität? Ohne explizites Chunking wird der Kontext entweder zu groß (Error) oder zu klein (schlechte Qualität). | HOCH | Layer 2 System-Prompt |
| H3 | **Kein Health-Check für `llm_mcp`** — Discord `/health` prüft Server-Status, aber nicht ob der LLM-Endpoint erreichbar ist. Bot antwortet "healthy" obwohl Layer 2 down ist. | HOCH | Layer 1 `/health` |
| H4 | **GitHub Issue Pollution** — `/ask` legt Issues an. Ohne Label-Cleanup, State-Machine (open→closed) und Stale-Bot wird der Issue-Tracker innerhalb von Wochen unbrauchbar. | HOCH | Layer 3 |
| H5 | **Discord Thread nicht im pgvector gespeichert** — Jeder `/chat`-Aufruf ist stateless. Keine Konversations-History. User muss Kontext in jedem Message wiederholen. | HOCH | Layer 2 + pgvector |

### MEDIUM

| # | Befund | Severity |
|---|--------|----------|
| M1 | ADR nennt "< 50 LOC" für `llm_mcp` — unrealistisch für produktionsreifen Service mit Auth, Retry, Logging, Health. Eher 300-500 LOC. | MEDIUM |
| M2 | Kein Webhook-Signatur-Validierung dokumentiert. Discord sendet `X-Signature-Ed25519` — muss verifiziert werden bei HTTP-Interactions. | MEDIUM |
| M3 | `platform-context` MCP als ADR-Quelle — wenn MCP-Server down, ist Layer 2 blind. Lokaler ADR-Cache als Fallback fehlt. | MEDIUM |
| M4 | Kein Tenant-Kontext in Discord-Commands. Multi-Tenant-Plattform, aber Discord-Bot ist single-tenant. Wenn mehrere Projekte/Tenants: welcher Kontext wird geladen? | MEDIUM |
| M5 | Discord Embed-Formatierung fehlt. Nur plaintext Antworten wirken unprofessionell. Embeds mit Farb-Coding (Error=Rot, Success=Grün) gehören zum UX-Standard. | MEDIUM |
| M6 | Keine Dokumentation des Rollback-Plans wenn Layer 2 fehlerhafte Antworten gibt. | MEDIUM |

---

## 2. Architektur-Alternative: Besserer Ansatz

### Problem mit dem vorgeschlagenen Design:
`llm_mcp` als separater FastAPI-Service ist ein **unnötiger Hop** wenn auf `hetzner-prod` bereits Django + Celery läuft.

### Empfohlene Alternative: Celery-basierter LLM-Worker

```
Discord /chat
    → orchestrator_mcp (FastMCP, bereits vorhanden)
    → Celery Task: llm_chat.apply_async()
    → Worker: ADR-Loader + pgvector + OpenRouter
    → Result Backend (Redis)
    → Discord Notification via Webhook
```

**Trade-offs:**

| Aspekt | `llm_mcp` FastAPI | Celery Task (empfohlen) |
|--------|-------------------|------------------------|
| Komplexität | Extra Service, extra Deploy | Nutzt bestehende Infra |
| Latenz | ~2s (sync) | ~3-5s (async, aber non-blocking) |
| Skalierung | Eigener Container | Celery Worker skaliert mit |
| Fehlertoleranz | Kein built-in Retry | Celery Retry native |
| Monitoring | Extra Setup | Flower bereits vorhanden |
| Kosten | Extra Hetzner Instance | 0 (bestehende Worker) |

**Empfehlung:** Celery-Task für Layer 2. `llm_mcp` nur wenn Layer 2 auf separater Infra laufen muss (z.B. unterschiedliche API-Keys per Tenant).

---

## 3. Korrigierter ADR-Auszug (BLOCKER-Fixes)

### B1 Fix — Discord Role Guard Decorator

```python
# orchestrator_mcp/discord/guards.py
from functools import wraps
import discord
from discord import app_commands

ALLOWED_ROLES = {
    "deploy":  ["platform-admin", "devops"],
    "approve": ["platform-admin", "devops"],
    "reject":  ["platform-admin", "devops"],
    "task":    ["platform-admin", "devops", "developer"],
    "chat":    ["platform-admin", "devops", "developer"],
    "ask":     ["platform-admin", "devops", "developer"],
    "health":  [],  # alle
    "status":  [],  # alle
    "memory":  [],  # alle
}

def require_role(command_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            required = ALLOWED_ROLES.get(command_name, [])
            if not required:
                return await func(interaction, *args, **kwargs)
            user_roles = {r.name for r in interaction.user.roles}
            if not user_roles.intersection(required):
                await interaction.response.send_message(
                    f"⛔ Keine Berechtigung für `/{command_name}`. "
                    f"Erforderliche Rolle: `{', '.join(required)}`",
                    ephemeral=True,
                )
                return
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator
```

### B2 Fix — Async-safe HTTP Client

```python
# orchestrator_mcp/discord/handlers.py
import httpx

async def cmd_chat(interaction: discord.Interaction, message: str) -> None:
    await interaction.response.defer()  # Discord 3s Timeout umgehen
    async with httpx.AsyncClient(timeout=30.0) as client:  # KEIN asyncio.run()
        resp = await client.post(
            "http://llm-worker:8001/v1/chat",
            json={"message": message, "user_id": str(interaction.user.id)},
        )
    resp.raise_for_status()
    ...
```

### B3 Fix — Rate Limiting mit aiocache + Token Bucket

```python
# orchestrator_mcp/discord/rate_limit.py
import time
from collections import defaultdict
from typing import DefaultDict

_buckets: DefaultDict[str, dict] = defaultdict(
    lambda: {"tokens": 5.0, "last": time.monotonic()}
)
RATE = 1.0          # 1 Token/Sekunde refill
CAPACITY = 5.0      # max 5 burst

def check_rate_limit(user_id: str) -> bool:
    """True = erlaubt, False = gedrosselt"""
    now = time.monotonic()
    b = _buckets[user_id]
    elapsed = now - b["last"]
    b["tokens"] = min(CAPACITY, b["tokens"] + elapsed * RATE)
    b["last"] = now
    if b["tokens"] >= 1.0:
        b["tokens"] -= 1.0
        return True
    return False
```

### B4 Fix — Discord Message Chunker

```python
# orchestrator_mcp/discord/utils.py
import discord
from typing import AsyncGenerator

DISCORD_LIMIT = 1990  # 10 chars Puffer

async def send_chunked(
    interaction: discord.Interaction,
    text: str,
    title: str = "",
    color: int = 0x5865F2,
) -> None:
    """Sendet Embed + Continuation-Messages für lange Antworten."""
    if len(text) <= DISCORD_LIMIT:
        embed = discord.Embed(title=title, description=text, color=color)
        await interaction.followup.send(embed=embed)
        return

    chunks = [text[i:i+DISCORD_LIMIT] for i in range(0, len(text), DISCORD_LIMIT)]
    for idx, chunk in enumerate(chunks):
        title_str = f"{title} ({idx+1}/{len(chunks)})" if title else f"Teil {idx+1}/{len(chunks)}"
        embed = discord.Embed(title=title_str, description=chunk, color=color)
        await interaction.followup.send(embed=embed)
```
